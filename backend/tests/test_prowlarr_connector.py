"""
Unit tests for ProwlarrConnector.

Covers:
- test_connection: success and failure
- get_indexers: returns list, handles exception
- get_indexer_stats: returns stats, handles exception
- get_indexers_with_stats: merges correctly, falls back to empty stats
- toggle_indexer: success and failure
- get_history: field mapping, indexer name lookup, categories parsing
- search: result mapping, exception handling
- grab: success and failure
"""

import os
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pilotarr-testing-only!")
os.environ.setdefault("API_KEY", "test-api-key")

from app.services.prowlarr_connector import ProwlarrConnector  # noqa: E402


def _make_response(data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture()
def connector():
    return ProwlarrConnector(base_url="http://prowlarr", api_key="test-key", port=9696)


# ── Init ──────────────────────────────────────────────────────────────────────


class TestInit:
    def test_port_appended_to_base_url(self):
        c = ProwlarrConnector(base_url="http://prowlarr", api_key="key", port=9696)
        assert c.base_url == "http://prowlarr:9696"

    def test_port_not_duplicated_when_already_in_url(self):
        c = ProwlarrConnector(base_url="http://prowlarr:9696", api_key="key", port=9696)
        assert c.base_url == "http://prowlarr:9696"

    def test_api_key_in_headers(self, connector):
        headers = connector._get_headers()
        assert headers["X-Api-Key"] == "test-key"
        assert headers["Content-Type"] == "application/json"


# ── test_connection ───────────────────────────────────────────────────────────


class TestTestConnection:
    async def test_success_returns_true_with_version(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"version": "1.2.3"}))
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "1.2.3" in msg

    async def test_failure_returns_false(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        ok, msg = await connector.test_connection()
        assert ok is False
        assert "Connection error" in msg


# ── get_indexers ──────────────────────────────────────────────────────────────


class TestGetIndexers:
    async def test_returns_list(self, connector):
        payload = [{"id": 1, "name": "NZBgeek"}, {"id": 2, "name": "TPB"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_indexers()
        assert len(result) == 2
        assert result[0]["name"] == "NZBgeek"

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_indexers()
        assert result == []


# ── get_indexer_stats ─────────────────────────────────────────────────────────


class TestGetIndexerStats:
    async def test_returns_indexers_list(self, connector):
        payload = {"indexers": [{"indexerId": 1, "numberOfQueries": 42}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_indexer_stats()
        assert len(result) == 1
        assert result[0]["numberOfQueries"] == 42

    async def test_missing_key_returns_empty(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({}))
        result = await connector.get_indexer_stats()
        assert result == []

    async def test_exception_returns_empty(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_indexer_stats()
        assert result == []


# ── get_indexers_with_stats ───────────────────────────────────────────────────


_INDEXER = {
    "id": 1,
    "name": "NZBgeek",
    "enable": True,
    "protocol": "usenet",
    "privacy": "private",
    "capabilities": {"categories": [{"name": "Movies"}, {"name": "TV"}]},
}
_STATS = {
    "indexerId": 1,
    "numberOfQueries": 100,
    "numberOfFailedQueries": 5,
    "numberOfGrabs": 20,
    "numberOfFailedGrabs": 1,
    "averageResponseTime": 350,
}


class TestGetIndexersWithStats:
    async def test_merges_stats_by_indexer_id(self, connector):
        connector.get_indexers = AsyncMock(return_value=[_INDEXER])
        connector.get_indexer_stats = AsyncMock(return_value=[_STATS])
        result = await connector.get_indexers_with_stats()
        assert len(result) == 1
        item = result[0]
        assert item["id"] == 1
        assert item["name"] == "NZBgeek"
        assert item["stats"]["numberOfQueries"] == 100
        assert item["stats"]["averageResponseTime"] == 350
        assert item["capabilities"]["categories"] == ["Movies", "TV"]

    async def test_falls_back_to_zero_stats_when_no_match(self, connector):
        connector.get_indexers = AsyncMock(return_value=[_INDEXER])
        connector.get_indexer_stats = AsyncMock(return_value=[])
        result = await connector.get_indexers_with_stats()
        stats = result[0]["stats"]
        assert stats["numberOfQueries"] == 0
        assert stats["numberOfGrabs"] == 0
        assert stats["averageResponseTime"] == 0

    async def test_empty_indexers_returns_empty_list(self, connector):
        connector.get_indexers = AsyncMock(return_value=[])
        connector.get_indexer_stats = AsyncMock(return_value=[])
        result = await connector.get_indexers_with_stats()
        assert result == []

    async def test_multiple_indexers_mapped_independently(self, connector):
        indexers = [
            {**_INDEXER, "id": 1, "name": "A"},
            {**_INDEXER, "id": 2, "name": "B"},
        ]
        stats = [
            {**_STATS, "indexerId": 1, "numberOfQueries": 10},
            {**_STATS, "indexerId": 2, "numberOfQueries": 20},
        ]
        connector.get_indexers = AsyncMock(return_value=indexers)
        connector.get_indexer_stats = AsyncMock(return_value=stats)
        result = await connector.get_indexers_with_stats()
        assert result[0]["stats"]["numberOfQueries"] == 10
        assert result[1]["stats"]["numberOfQueries"] == 20


# ── toggle_indexer ────────────────────────────────────────────────────────────


class TestToggleIndexer:
    async def test_success_returns_true(self, connector):
        existing = {"id": 1, "name": "TPB", "enable": False}
        connector.client.get = AsyncMock(return_value=_make_response(existing))
        connector.client.put = AsyncMock(return_value=_make_response({"id": 1, "enable": True}))
        result = await connector.toggle_indexer(1, enable=True)
        assert result is True

    async def test_puts_correct_enable_value(self, connector):
        existing = {"id": 1, "enable": True}
        connector.client.get = AsyncMock(return_value=_make_response(existing))
        connector.client.put = AsyncMock(return_value=_make_response(existing))
        await connector.toggle_indexer(1, enable=False)
        payload = connector.client.put.call_args.kwargs["json"]
        assert payload["enable"] is False

    async def test_http_error_returns_false(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.toggle_indexer(99, enable=True)
        assert result is False


# ── get_history ───────────────────────────────────────────────────────────────


_RAW_RECORD = {
    "id": 10,
    "date": "2024-01-15T10:00:00Z",
    "indexerId": 1,
    "eventType": "grabRelease",
    "successful": True,
    "data": {
        "query": "Breaking Bad",
        "categories": "5000, 5030",
        "source": "Sonarr",
    },
}
_INDEXERS = [{"id": 1, "name": "NZBgeek"}]


class TestGetHistory:
    async def test_returns_mapped_history_item(self, connector):
        connector.get_indexers = AsyncMock(return_value=_INDEXERS)
        connector.client.get = AsyncMock(return_value=_make_response({"records": [_RAW_RECORD]}))
        result = await connector.get_history(page_size=5)
        assert len(result) == 1
        item = result[0]
        assert item["id"] == 10
        assert item["date"] == "2024-01-15T10:00:00Z"
        assert item["indexer"] == "NZBgeek"
        assert item["query"] == "Breaking Bad"
        assert item["eventType"] == "grabRelease"
        assert item["successful"] is True
        assert item["source"] == "Sonarr"

    async def test_categories_split_and_stripped(self, connector):
        record = {**_RAW_RECORD, "data": {"categories": " 5000 , 5030 , 2000 "}}
        connector.get_indexers = AsyncMock(return_value=_INDEXERS)
        connector.client.get = AsyncMock(return_value=_make_response({"records": [record]}))
        result = await connector.get_history()
        assert result[0]["categories"] == ["5000", "5030", "2000"]

    async def test_unknown_indexer_id_uses_hash_fallback(self, connector):
        connector.get_indexers = AsyncMock(return_value=[])
        connector.client.get = AsyncMock(return_value=_make_response({"records": [_RAW_RECORD]}))
        result = await connector.get_history()
        assert result[0]["indexer"] == "#1"

    async def test_null_indexer_id_gives_empty_string(self, connector):
        record = {**_RAW_RECORD, "indexerId": None}
        connector.get_indexers = AsyncMock(return_value=_INDEXERS)
        connector.client.get = AsyncMock(return_value=_make_response({"records": [record]}))
        result = await connector.get_history()
        assert result[0]["indexer"] == ""

    async def test_empty_records_returns_empty_list(self, connector):
        connector.get_indexers = AsyncMock(return_value=_INDEXERS)
        connector.client.get = AsyncMock(return_value=_make_response({"records": []}))
        result = await connector.get_history()
        assert result == []

    async def test_exception_returns_empty_list(self, connector):
        connector.get_indexers = AsyncMock(return_value=_INDEXERS)
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_history()
        assert result == []


# ── search ────────────────────────────────────────────────────────────────────


_RAW_SEARCH_RESULT = {
    "guid": "magnet:?xt=urn:btih:abc",
    "title": "Breaking Bad S01E01",
    "indexer": "NZBgeek",
    "indexerId": 1,
    "size": 1_500_000_000,
    "seeders": 42,
    "leechers": 5,
    "protocol": "torrent",
    "publishDate": "2024-01-10T00:00:00Z",
    "categories": [{"name": "TV"}, {"name": "HD"}],
    "downloadUrl": "http://nzbgeek.com/download/abc",
    "magnetUrl": "magnet:?xt=urn:btih:abc",
}


class TestSearch:
    async def test_returns_mapped_results(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([_RAW_SEARCH_RESULT]))
        result = await connector.search("Breaking Bad")
        assert len(result) == 1
        item = result[0]
        assert item["guid"] == "magnet:?xt=urn:btih:abc"
        assert item["title"] == "Breaking Bad S01E01"
        assert item["seeders"] == 42
        assert item["leechers"] == 5
        assert item["categories"] == ["TV", "HD"]
        assert item["downloadUrl"] == "http://nzbgeek.com/download/abc"
        assert item["magnetUrl"] == "magnet:?xt=urn:btih:abc"

    async def test_empty_results_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([]))
        result = await connector.search("nothing")
        assert result == []

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.search("anything")
        assert result == []

    async def test_passes_query_and_type_as_params(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([]))
        await connector.search("Inception", search_type="movie")
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["query"] == "Inception"
        assert call_params["type"] == "movie"


# ── grab ──────────────────────────────────────────────────────────────────────


class TestGrab:
    async def test_success_returns_true(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({}))
        result = await connector.grab("magnet:?xt=urn:btih:abc", indexer_id=1)
        assert result is True

    async def test_failure_returns_false(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.grab("magnet:?xt=urn:btih:abc", indexer_id=1)
        assert result is False

    async def test_posts_correct_payload(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({}))
        await connector.grab("some-guid", indexer_id=7)
        payload = connector.client.post.call_args.kwargs["json"]
        assert payload["guid"] == "some-guid"
        assert payload["indexerId"] == 7
