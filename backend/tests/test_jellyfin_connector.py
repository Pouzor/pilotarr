"""
Unit tests for JellyfinConnector.

Covers:
- test_connection: success and failure
- get_users: returns list, exception returns []
- get_library_items: key mapping, exception returns {}
- get_recent_items: passes params, returns Items list, exception returns []
- get_playback_stats: counts active/total users, exception returns {}
- get_total_watch_time: tick conversion, null result, no plugin case, exception
- get_movies_details: tick conversion, uses TotalRecordCount, exception
- get_tv_shows_details: two API calls, computes totals, exception
- get_series_id_by_title: returns first match, empty = None, exception = None
- get_episodes_with_streams: returns Items, exception returns []
- get_movies_with_streams: returns Items, exception returns []
- get_series_with_path: returns Items, exception returns []
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
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")

from app.services.jellyfin_connector import JellyfinConnector  # noqa: E402


def _make_response(data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture()
def connector():
    return JellyfinConnector(base_url="http://jellyfin", api_key="test-token")


# ── Init ──────────────────────────────────────────────────────────────────────


class TestInit:
    def test_emby_token_header(self, connector):
        headers = connector._get_headers()
        assert headers["X-Emby-Token"] == "test-token"

    def test_base_headers_included(self, connector):
        headers = connector._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"


# ── test_connection ───────────────────────────────────────────────────────────


class TestTestConnection:
    async def test_success_returns_true_with_version(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Version": "10.9.0"}))
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "10.9.0" in msg

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


# ── get_users ─────────────────────────────────────────────────────────────────


class TestGetUsers:
    async def test_returns_user_list(self, connector):
        payload = [{"Id": "u1", "Name": "Alice"}, {"Id": "u2", "Name": "Bob"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_users()
        assert len(result) == 2
        assert result[0]["Name"] == "Alice"

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_users()
        assert result == []


# ── get_library_items ─────────────────────────────────────────────────────────


class TestGetLibraryItems:
    async def test_maps_counts_correctly(self, connector):
        payload = {
            "MovieCount": 120,
            "SeriesCount": 30,
            "EpisodeCount": 900,
            "AlbumCount": 0,
            "SongCount": 0,
        }
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_library_items()
        assert result["movies"] == 120
        assert result["series"] == 30
        assert result["episodes"] == 900

    async def test_missing_keys_default_to_zero(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({}))
        result = await connector.get_library_items()
        assert result["movies"] == 0
        assert result["series"] == 0

    async def test_exception_returns_empty_dict(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_library_items()
        assert result == {}


# ── get_recent_items ──────────────────────────────────────────────────────────


class TestGetRecentItems:
    async def test_returns_items_list(self, connector):
        payload = {"Items": [{"Id": "i1", "Name": "Dune"}, {"Id": "i2", "Name": "Inception"}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_recent_items(limit=5)
        assert len(result) == 2
        assert result[0]["Name"] == "Dune"

    async def test_passes_limit_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Items": []}))
        await connector.get_recent_items(limit=42)
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["Limit"] == 42

    async def test_passes_sort_and_types_params(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Items": []}))
        await connector.get_recent_items()
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["SortBy"] == "DateCreated"
        assert "Movie" in call_params["IncludeItemTypes"]

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_recent_items()
        assert result == []


# ── get_playback_stats ────────────────────────────────────────────────────────


class TestGetPlaybackStats:
    async def test_counts_total_and_active_users(self, connector):
        users = [
            {"Policy": {"IsDisabled": False}},
            {"Policy": {"IsDisabled": True}},
            {"Policy": {"IsDisabled": False}},
        ]
        connector.get_users = AsyncMock(return_value=users)
        result = await connector.get_playback_stats(days=7)
        assert result["total_users"] == 3
        assert result["active_users"] == 2
        assert result["period_days"] == 7

    async def test_no_disabled_field_counts_as_active(self, connector):
        users = [{"Policy": {}}, {"Policy": {}}]
        connector.get_users = AsyncMock(return_value=users)
        result = await connector.get_playback_stats()
        assert result["active_users"] == 2

    async def test_exception_returns_empty_dict(self, connector):
        connector.get_users = AsyncMock(side_effect=Exception("fail"))
        result = await connector.get_playback_stats()
        assert result == {}


# ── get_total_watch_time ──────────────────────────────────────────────────────


class TestGetTotalWatchTime:
    async def test_converts_seconds_to_hours(self, connector):
        payload = {"results": [[7200]], "columns": ["TotalSeconds"]}
        connector.client.post = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_total_watch_time(days=30)
        assert result["total_seconds"] == 7200
        assert result["total_hours"] == 2.0
        assert result["period_days"] == 30

    async def test_null_result_returns_zero(self, connector):
        payload = {"results": [[None]], "columns": ["TotalSeconds"]}
        connector.client.post = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_total_watch_time()
        assert result["total_seconds"] == 0
        assert result["total_hours"] == 0

    async def test_empty_results_returns_zero(self, connector):
        payload = {"results": [], "columns": ["TotalSeconds"]}
        connector.client.post = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_total_watch_time()
        assert result["total_seconds"] == 0

    async def test_exception_returns_zero_defaults(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_total_watch_time(days=14)
        assert result == {"total_hours": 0, "total_seconds": 0, "period_days": 14}


# ── get_movies_details ────────────────────────────────────────────────────────

# 1 second = 10_000_000 ticks; 3600 seconds = 1 hour
_ONE_HOUR_TICKS = 3600 * 10_000_000


class TestGetMoviesDetails:
    async def test_converts_ticks_to_hours(self, connector):
        movies = [{"RunTimeTicks": _ONE_HOUR_TICKS}, {"RunTimeTicks": _ONE_HOUR_TICKS}]
        payload = {"Items": movies, "TotalRecordCount": 2}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_movies_details()
        assert result["total_movies"] == 2
        assert result["total_hours"] == 2

    async def test_uses_total_record_count_not_items_length(self, connector):
        # API may return paginated subset but TotalRecordCount reflects full library
        payload = {"Items": [{"RunTimeTicks": 0}], "TotalRecordCount": 500}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_movies_details()
        assert result["total_movies"] == 500

    async def test_missing_ticks_treated_as_zero(self, connector):
        payload = {"Items": [{"Id": "m1"}, {"Id": "m2"}], "TotalRecordCount": 2}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_movies_details()
        assert result["total_hours"] == 0

    async def test_exception_returns_zero_defaults(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_movies_details()
        assert result == {"total_movies": 0, "total_hours": 0}


# ── get_tv_shows_details ──────────────────────────────────────────────────────


class TestGetTvShowsDetails:
    async def test_correct_totals_from_two_calls(self, connector):
        # First call: episodes; second call: series
        episodes_payload = {"Items": [{"RunTimeTicks": _ONE_HOUR_TICKS}] * 10, "TotalRecordCount": 200}
        series_payload = {"TotalRecordCount": 25}

        connector.client.get = AsyncMock(
            side_effect=[
                _make_response(episodes_payload),
                _make_response(series_payload),
            ]
        )
        result = await connector.get_tv_shows_details()
        assert result["total_episodes"] == 200
        assert result["total_series"] == 25
        assert result["total_hours"] == 10  # 10 items × 1h each

    async def test_exception_returns_zero_defaults(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_tv_shows_details()
        assert result == {"total_series": 0, "total_episodes": 0, "total_hours": 0}


# ── get_series_id_by_title ────────────────────────────────────────────────────


class TestGetSeriesIdByTitle:
    async def test_returns_first_item_id(self, connector):
        payload = {"Items": [{"Id": "series-abc", "Name": "Breaking Bad"}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_series_id_by_title("Breaking Bad")
        assert result == "series-abc"

    async def test_empty_items_returns_none(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Items": []}))
        result = await connector.get_series_id_by_title("Unknown Show")
        assert result is None

    async def test_exception_returns_none(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_series_id_by_title("Anything")
        assert result is None

    async def test_passes_search_term_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Items": []}))
        await connector.get_series_id_by_title("The Wire")
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["SearchTerm"] == "The Wire"
        assert call_params["IncludeItemTypes"] == "Series"


# ── get_episodes_with_streams ─────────────────────────────────────────────────


class TestGetEpisodesWithStreams:
    async def test_returns_items(self, connector):
        payload = {"Items": [{"Id": "ep1", "MediaStreams": []}, {"Id": "ep2", "MediaStreams": []}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_episodes_with_streams("series-xyz")
        assert len(result) == 2

    async def test_passes_series_id_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Items": []}))
        await connector.get_episodes_with_streams("sid-42")
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["SeriesId"] == "sid-42"
        assert "MediaStreams" in call_params["Fields"]

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_episodes_with_streams("sid")
        assert result == []


# ── get_movies_with_streams ───────────────────────────────────────────────────


class TestGetMoviesWithStreams:
    async def test_returns_items(self, connector):
        payload = {"Items": [{"Id": "m1", "MediaStreams": []}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_movies_with_streams()
        assert len(result) == 1

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_movies_with_streams()
        assert result == []


# ── get_series_with_path ──────────────────────────────────────────────────────


class TestGetSeriesWithPath:
    async def test_returns_items(self, connector):
        payload = {"Items": [{"Id": "s1", "Path": "/media/shows/Breaking Bad"}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_series_with_path()
        assert len(result) == 1
        assert result[0]["Path"] == "/media/shows/Breaking Bad"

    async def test_passes_correct_params(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"Items": []}))
        await connector.get_series_with_path()
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["IncludeItemTypes"] == "Series"
        assert "Path" in call_params["Fields"]

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_series_with_path()
        assert result == []
