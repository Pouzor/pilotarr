"""
Unit tests for RadarrConnector.

Covers:
- test_connection: success and failure
- get_movies: returns list, handles exception
- get_calendar: date params, exception handling
- get_recent_additions: date filtering, sorting, invalid dates ignored
- get_history: returns records, handles exception
- get_movie_history_map: builds {movieId: hash} map
- _extract_hash: all formats and edge cases
- get_quality_profiles: mapping, exception handling
- get_statistics: correct counts, exception handling
"""

import os
from datetime import UTC, datetime, timedelta
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

from app.services.radarr_connector import RadarrConnector  # noqa: E402


def _make_response(data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture()
def connector():
    return RadarrConnector(base_url="http://radarr", api_key="test-key", port=7878)


# ── Init ──────────────────────────────────────────────────────────────────────


class TestInit:
    def test_port_appended_to_base_url(self):
        c = RadarrConnector(base_url="http://radarr", api_key="key", port=7878)
        assert c.base_url == "http://radarr:7878"

    def test_api_key_in_headers(self, connector):
        headers = connector._get_headers()
        assert headers["X-Api-Key"] == "test-key"


# ── test_connection ───────────────────────────────────────────────────────────


class TestTestConnection:
    async def test_success_returns_true_with_version(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"version": "5.1.0"}))
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "5.1.0" in msg

    async def test_failure_returns_false(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        ok, msg = await connector.test_connection()
        assert ok is False
        assert "Erreur" in msg


# ── get_movies ────────────────────────────────────────────────────────────────


class TestGetMovies:
    async def test_returns_movie_list(self, connector):
        payload = [{"id": 1, "title": "Inception"}, {"id": 2, "title": "The Matrix"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_movies()
        assert len(result) == 2
        assert result[0]["title"] == "Inception"

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_movies()
        assert result == []


# ── get_calendar ──────────────────────────────────────────────────────────────


class TestGetCalendar:
    async def test_returns_calendar_list(self, connector):
        payload = [{"id": 1, "title": "New Movie", "inCinemas": "2024-02-01"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_calendar()
        assert len(result) == 1
        assert result[0]["title"] == "New Movie"

    async def test_passes_date_params(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([]))
        await connector.get_calendar(days_ahead=14, days_behind=7)
        call_params = connector.client.get.call_args.kwargs["params"]
        assert "start" in call_params
        assert "end" in call_params

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_calendar()
        assert result == []


# ── get_recent_additions ──────────────────────────────────────────────────────


class TestGetRecentAdditions:
    def _recent_movie(self, title, days_ago=1):
        added = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
        return {"id": 1, "title": title, "added": added, "hasFile": True, "monitored": True}

    def _old_movie(self, title):
        added = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        return {"id": 2, "title": title, "added": added, "hasFile": True, "monitored": True}

    async def test_filters_by_days(self, connector):
        movies = [self._recent_movie("New"), self._old_movie("Old")]
        connector.get_movies = AsyncMock(return_value=movies)
        result = await connector.get_recent_additions(days=7)
        assert len(result) == 1
        assert result[0]["title"] == "New"

    async def test_sorted_most_recent_first(self, connector):
        m1 = self._recent_movie("Earlier", days_ago=3)
        m2 = self._recent_movie("Latest", days_ago=1)
        connector.get_movies = AsyncMock(return_value=[m1, m2])
        result = await connector.get_recent_additions(days=7)
        assert result[0]["title"] == "Latest"

    async def test_movies_without_added_field_are_skipped(self, connector):
        movie = {"id": 1, "title": "No Date", "hasFile": True, "monitored": True}
        connector.get_movies = AsyncMock(return_value=[movie])
        result = await connector.get_recent_additions(days=7)
        assert result == []

    async def test_invalid_date_format_is_skipped(self, connector):
        movie = {"id": 1, "title": "Bad Date", "added": "not-a-date"}
        connector.get_movies = AsyncMock(return_value=[movie])
        result = await connector.get_recent_additions(days=7)
        assert result == []

    async def test_exception_returns_empty_list(self, connector):
        connector.get_movies = AsyncMock(side_effect=Exception("fail"))
        result = await connector.get_recent_additions()
        assert result == []


# ── get_history ───────────────────────────────────────────────────────────────


class TestGetHistory:
    async def test_returns_records(self, connector):
        payload = {"records": [{"id": 1, "movieId": 10, "downloadId": "abc123"}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_history(page_size=10)
        assert len(result) == 1
        assert result[0]["movieId"] == 10

    async def test_empty_records_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"records": []}))
        result = await connector.get_history()
        assert result == []

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_history()
        assert result == []


# ── get_movie_history_map ─────────────────────────────────────────────────────


class TestGetMovieHistoryMap:
    async def test_builds_movie_hash_map(self, connector):
        records = [
            {"movieId": 1, "downloadId": "qBittorrent-" + "a" * 40},
            {"movieId": 2, "downloadId": "b" * 40},
        ]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_movie_history_map()
        assert 1 in result
        assert 2 in result
        assert result[1] == "A" * 40
        assert result[2] == "B" * 40

    async def test_skips_records_without_valid_hash(self, connector):
        records = [
            {"movieId": 1, "downloadId": "invalid"},
            {"movieId": 2, "downloadId": ""},
        ]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_movie_history_map()
        assert result == {}

    async def test_skips_records_without_movie_id(self, connector):
        records = [{"downloadId": "a" * 40}]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_movie_history_map()
        assert result == {}

    async def test_later_record_overwrites_earlier_for_same_movie(self, connector):
        hash1 = "a" * 40
        hash2 = "b" * 40
        records = [
            {"movieId": 1, "downloadId": hash1},
            {"movieId": 1, "downloadId": hash2},
        ]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_movie_history_map()
        # Last one wins
        assert result[1] == hash2.upper()


# ── _extract_hash ─────────────────────────────────────────────────────────────


class TestExtractHash:
    def test_qbittorrent_prefixed_format(self, connector):
        result = connector._extract_hash("qBittorrent-" + "a" * 40)
        assert result == "A" * 40

    def test_bare_40_char_hex(self, connector):
        raw = "a" * 40
        assert connector._extract_hash(raw) == raw.upper()

    def test_uppercase_hex_accepted(self, connector):
        raw = "A" * 40
        assert connector._extract_hash(raw) == raw

    def test_returns_none_for_empty_string(self, connector):
        assert connector._extract_hash("") is None

    def test_returns_none_for_none(self, connector):
        assert connector._extract_hash(None) is None

    def test_returns_none_for_short_string(self, connector):
        assert connector._extract_hash("tooshort") is None

    def test_returns_none_for_non_hex_40_chars(self, connector):
        assert connector._extract_hash("z" * 40) is None

    def test_result_is_always_uppercase(self, connector):
        raw = "abcdef1234567890abcdef1234567890abcdef12"
        result = connector._extract_hash(raw)
        assert result == raw.upper()

    def test_prefix_part_is_discarded(self, connector):
        hash_part = "a" * 40
        result = connector._extract_hash(f"Radarr-{hash_part}")
        assert result == hash_part.upper()


# ── get_quality_profiles ──────────────────────────────────────────────────────


class TestGetQualityProfiles:
    async def test_returns_id_name_mapping(self, connector):
        payload = [{"id": 1, "name": "HD-1080p"}, {"id": 2, "name": "4K"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_quality_profiles()
        assert result == {1: "HD-1080p", 2: "4K"}

    async def test_skips_profiles_without_id_or_name(self, connector):
        payload = [{"id": 1, "name": "Valid"}, {"id": 2}, {"name": "No ID"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_quality_profiles()
        assert result == {1: "Valid"}

    async def test_exception_returns_empty_dict(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_quality_profiles()
        assert result == {}


# ── get_statistics ────────────────────────────────────────────────────────────


class TestGetStatistics:
    _MOVIES = [
        {"id": 1, "title": "A", "monitored": True, "hasFile": True},
        {"id": 2, "title": "B", "monitored": True, "hasFile": False},
        {"id": 3, "title": "C", "monitored": False, "hasFile": True},
        {"id": 4, "title": "D", "monitored": False, "hasFile": False},
    ]

    async def test_counts_are_correct(self, connector):
        connector.get_movies = AsyncMock(return_value=self._MOVIES)
        result = await connector.get_statistics()
        assert result["total_movies"] == 4
        assert result["monitored_movies"] == 2
        assert result["downloaded_movies"] == 2
        assert result["missing_movies"] == 0  # monitored=2, downloaded=2

    async def test_missing_movies_is_monitored_minus_downloaded(self, connector):
        movies = [
            {"id": 1, "monitored": True, "hasFile": False},
            {"id": 2, "monitored": True, "hasFile": False},
            {"id": 3, "monitored": True, "hasFile": True},
        ]
        connector.get_movies = AsyncMock(return_value=movies)
        result = await connector.get_statistics()
        assert result["missing_movies"] == 2

    async def test_empty_library_returns_zeros(self, connector):
        connector.get_movies = AsyncMock(return_value=[])
        result = await connector.get_statistics()
        assert result == {
            "total_movies": 0,
            "monitored_movies": 0,
            "downloaded_movies": 0,
            "missing_movies": 0,
        }

    async def test_exception_returns_empty_dict(self, connector):
        connector.get_movies = AsyncMock(side_effect=Exception("fail"))
        result = await connector.get_statistics()
        assert result == {}


# ── find_movie_id_by_title ────────────────────────────────────────────────────


class TestFindMovieIdByTitle:
    async def test_returns_id_for_matching_title(self, connector):
        connector.get_movies = AsyncMock(
            return_value=[
                {"id": 1, "title": "Inception"},
                {"id": 2, "title": "The Matrix"},
            ]
        )
        result = await connector.find_movie_id_by_title("Inception")
        assert result == 1

    async def test_case_insensitive_match(self, connector):
        connector.get_movies = AsyncMock(return_value=[{"id": 3, "title": "Interstellar"}])
        result = await connector.find_movie_id_by_title("interstellar")
        assert result == 3

    async def test_returns_none_when_not_found(self, connector):
        connector.get_movies = AsyncMock(return_value=[{"id": 1, "title": "Inception"}])
        result = await connector.find_movie_id_by_title("Unknown Movie")
        assert result is None

    async def test_exception_returns_none(self, connector):
        connector.get_movies = AsyncMock(side_effect=Exception("fail"))
        result = await connector.find_movie_id_by_title("Inception")
        assert result is None


# ── refresh_movie ─────────────────────────────────────────────────────────────


class TestRefreshMovie:
    async def test_success_returns_true(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 1}))
        result = await connector.refresh_movie(10)
        assert result is True

    async def test_posts_correct_command(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 1}))
        await connector.refresh_movie(10)
        payload = connector.client.post.call_args.kwargs["json"]
        assert payload["name"] == "RefreshMovie"
        assert payload["movieIds"] == [10]

    async def test_exception_returns_false(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.refresh_movie(10)
        assert result is False


# ── rescan_movie ──────────────────────────────────────────────────────────────


class TestRescanMovie:
    async def test_success_returns_true(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 2}))
        result = await connector.rescan_movie(10)
        assert result is True

    async def test_posts_correct_command(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 2}))
        await connector.rescan_movie(10)
        payload = connector.client.post.call_args.kwargs["json"]
        assert payload["name"] == "RescanMovie"
        assert payload["movieIds"] == [10]

    async def test_exception_returns_false(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.rescan_movie(10)
        assert result is False
