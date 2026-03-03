"""
Unit tests for JellyseerrConnector.

Covers:
- test_connection: success and failure
- get_requests: single page, pagination, stops when total reached, exception
- get_media_details: movie vs tv endpoint, exception returns {}
- approve_request: posts to correct endpoint
- decline_request: posts to correct endpoint
- get_statistics: counts by status, exception returns {}
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

from app.services.jellyseerr_connector import JellyseerrConnector  # noqa: E402


def _make_response(data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    mock.content = b"content"
    return mock


def _make_empty_response():
    """POST response with no body (e.g. approve/decline)."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {}
    mock.raise_for_status = MagicMock()
    mock.content = b""
    return mock


@pytest.fixture()
def connector():
    return JellyseerrConnector(base_url="http://jellyseerr", api_key="test-key", port=5055)


# ── Init ──────────────────────────────────────────────────────────────────────


class TestInit:
    def test_api_key_in_headers(self, connector):
        headers = connector._get_headers()
        assert headers["X-Api-Key"] == "test-key"

    def test_port_appended_to_base_url(self):
        c = JellyseerrConnector(base_url="http://jellyseerr", api_key="key", port=5055)
        assert c.base_url == "http://jellyseerr:5055"


# ── test_connection ───────────────────────────────────────────────────────────


class TestTestConnection:
    async def test_success_returns_true_with_version(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"version": "1.8.0"}))
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "1.8.0" in msg

    async def test_missing_version_shows_unknown(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({}))
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "unknown" in msg

    async def test_failure_returns_false(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        ok, msg = await connector.test_connection()
        assert ok is False
        assert "Erreur" in msg


# ── get_requests ──────────────────────────────────────────────────────────────

_REQUEST_1 = {"id": 1, "status": 1, "type": "movie"}
_REQUEST_2 = {"id": 2, "status": 2, "type": "tv"}
_REQUEST_3 = {"id": 3, "status": 3, "type": "movie"}


class TestGetRequests:
    async def test_returns_all_single_page(self, connector):
        payload = {
            "results": [_REQUEST_1, _REQUEST_2],
            "pageInfo": {"results": 2, "pages": 1},
        }
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_requests()
        assert len(result) == 2

    async def test_paginates_until_total_reached(self, connector):
        # First page returns 2 results, total is 3
        page1 = {"results": [_REQUEST_1, _REQUEST_2], "pageInfo": {"results": 3}}
        # Second page returns the remaining 1
        page2 = {"results": [_REQUEST_3], "pageInfo": {"results": 3}}
        connector.client.get = AsyncMock(side_effect=[_make_response(page1), _make_response(page2)])
        result = await connector.get_requests(limit=2)
        assert len(result) == 3

    async def test_stops_when_results_empty(self, connector):
        payload = {"results": [], "pageInfo": {"results": 0}}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_requests()
        assert result == []

    async def test_passes_status_filter_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"results": [], "pageInfo": {"results": 0}}))
        await connector.get_requests(status="pending")
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["filter"] == "pending"

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_requests()
        assert result == []


# ── get_media_details ─────────────────────────────────────────────────────────


class TestGetMediaDetails:
    async def test_movie_hits_movie_endpoint(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"id": 550, "title": "Fight Club"}))
        result = await connector.get_media_details(550, "movie")
        assert result["title"] == "Fight Club"
        called_url = connector.client.get.call_args.args[0]
        assert "/movie/550" in called_url

    async def test_tv_hits_tv_endpoint(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"id": 1396, "name": "Breaking Bad"}))
        await connector.get_media_details(1396, "tv")
        called_url = connector.client.get.call_args.args[0]
        assert "/tv/1396" in called_url

    async def test_exception_returns_empty_dict(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_media_details(1, "movie")
        assert result == {}


# ── approve_request ───────────────────────────────────────────────────────────


class TestApproveRequest:
    async def test_posts_to_correct_endpoint(self, connector):
        connector.client.post = AsyncMock(return_value=_make_empty_response())
        await connector.approve_request(42)
        called_url = connector.client.post.call_args.args[0]
        assert "/api/v1/request/42/approve" in called_url

    async def test_propagates_http_error(self, connector):
        connector.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("403", request=MagicMock(), response=MagicMock())
        )
        with pytest.raises(httpx.HTTPStatusError):
            await connector.approve_request(99)


# ── decline_request ───────────────────────────────────────────────────────────


class TestDeclineRequest:
    async def test_posts_to_correct_endpoint(self, connector):
        connector.client.post = AsyncMock(return_value=_make_empty_response())
        await connector.decline_request(7)
        called_url = connector.client.post.call_args.args[0]
        assert "/api/v1/request/7/decline" in called_url

    async def test_propagates_http_error(self, connector):
        connector.client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("403", request=MagicMock(), response=MagicMock())
        )
        with pytest.raises(httpx.HTTPStatusError):
            await connector.decline_request(99)


# ── get_statistics ────────────────────────────────────────────────────────────


class TestGetStatistics:
    _REQUESTS = [
        {"id": 1, "status": 1},  # pending
        {"id": 2, "status": 1},  # pending
        {"id": 3, "status": 2},  # approved
        {"id": 4, "status": 3},  # declined
        {"id": 5, "status": 4},  # failed → counted as declined
        {"id": 6, "status": 2},  # approved
    ]

    async def test_counts_by_status(self, connector):
        connector.get_requests = AsyncMock(return_value=self._REQUESTS)
        result = await connector.get_statistics()
        assert result["total"] == 6
        assert result["pending"] == 2
        assert result["approved"] == 2
        assert result["declined"] == 2  # status 3 + status 4

    async def test_empty_requests_returns_zeros(self, connector):
        connector.get_requests = AsyncMock(return_value=[])
        result = await connector.get_statistics()
        assert result == {"total": 0, "pending": 0, "approved": 0, "declined": 0}

    async def test_exception_returns_empty_dict(self, connector):
        connector.get_requests = AsyncMock(side_effect=Exception("fail"))
        result = await connector.get_statistics()
        assert result == {}
