"""
Unit tests for SonarrConnector.

Covers:
- test_connection: success and failure
- get_series: returns list, exception returns []
- get_quality_profiles: id→name mapping, skips incomplete, exception returns {}
- get_series_by_id: returns dict, empty response = {}, exception = {}
- get_episodes_by_series: returns list, exception returns []
- get_episode_files_by_series: returns list, exception returns []
- get_calendar: passes date params, exception returns []
- get_recent_additions: filters by cutoff, sorted most-recent-first, skips no-date, invalid date skipped, exception
- get_history: returns records, exception returns []
- get_series_history_map: delegates to get_series_torrents_map, first hash
- get_series_torrents_map: unique hashes, season pack detection (2+ episodes per hash)
- _extract_hash: all formats and edge cases
- monitor_episode: success, failure
- search_episode: success, failure
- get_statistics: correct counts, exception returns {}
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

from app.services.sonarr_connector import SonarrConnector  # noqa: E402


def _make_response(data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


@pytest.fixture()
def connector():
    return SonarrConnector(base_url="http://sonarr", api_key="test-key", port=8989)


# ── Init ──────────────────────────────────────────────────────────────────────


class TestInit:
    def test_port_appended_to_base_url(self):
        c = SonarrConnector(base_url="http://sonarr", api_key="key", port=8989)
        assert c.base_url == "http://sonarr:8989"

    def test_api_key_in_headers(self, connector):
        headers = connector._get_headers()
        assert headers["X-Api-Key"] == "test-key"


# ── test_connection ───────────────────────────────────────────────────────────


class TestTestConnection:
    async def test_success_returns_true_with_version(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"version": "4.0.8"}))
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "4.0.8" in msg

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


# ── get_series ────────────────────────────────────────────────────────────────


class TestGetSeries:
    async def test_returns_series_list(self, connector):
        payload = [{"id": 1, "title": "Breaking Bad"}, {"id": 2, "title": "The Wire"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_series()
        assert len(result) == 2
        assert result[0]["title"] == "Breaking Bad"

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_series()
        assert result == []


# ── get_quality_profiles ──────────────────────────────────────────────────────


class TestGetQualityProfiles:
    async def test_returns_id_name_mapping(self, connector):
        payload = [{"id": 1, "name": "HD-1080p"}, {"id": 2, "name": "Any"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_quality_profiles()
        assert result == {1: "HD-1080p", 2: "Any"}

    async def test_skips_profiles_without_id_or_name(self, connector):
        payload = [{"id": 1, "name": "Valid"}, {"id": 2}, {"name": "No ID"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_quality_profiles()
        assert result == {1: "Valid"}

    async def test_exception_returns_empty_dict(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_quality_profiles()
        assert result == {}


# ── get_series_by_id ──────────────────────────────────────────────────────────


class TestGetSeriesById:
    async def test_returns_series_dict(self, connector):
        payload = {"id": 5, "title": "The Sopranos", "seasons": []}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_series_by_id(5)
        assert result["title"] == "The Sopranos"

    async def test_empty_response_returns_empty_dict(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({}))
        result = await connector.get_series_by_id(99)
        assert result == {}

    async def test_exception_returns_empty_dict(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_series_by_id(1)
        assert result == {}


# ── get_episodes_by_series ────────────────────────────────────────────────────


class TestGetEpisodesBySeries:
    async def test_returns_episode_list(self, connector):
        payload = [{"id": 101, "title": "Pilot"}, {"id": 102, "title": "EP2"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_episodes_by_series(1)
        assert len(result) == 2

    async def test_passes_series_id_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([]))
        await connector.get_episodes_by_series(42)
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["seriesId"] == 42

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_episodes_by_series(1)
        assert result == []


# ── get_episode_files_by_series ───────────────────────────────────────────────


class TestGetEpisodeFilesBySeries:
    async def test_returns_file_list(self, connector):
        payload = [{"id": 1, "quality": {"quality": {"name": "WEBDL-1080p"}}}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_episode_files_by_series(1)
        assert len(result) == 1

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_episode_files_by_series(1)
        assert result == []


# ── get_calendar ──────────────────────────────────────────────────────────────


class TestGetCalendar:
    async def test_returns_episode_list(self, connector):
        payload = [{"id": 1, "title": "S01E01", "airDate": "2024-03-01"}]
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_calendar()
        assert len(result) == 1

    async def test_passes_date_range_params(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([]))
        await connector.get_calendar(days_ahead=14, days_behind=7)
        call_params = connector.client.get.call_args.kwargs["params"]
        assert "start" in call_params
        assert "end" in call_params

    async def test_includes_series_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response([]))
        await connector.get_calendar()
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["includeSeries"] == "true"

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_calendar()
        assert result == []


# ── get_recent_additions ──────────────────────────────────────────────────────


def _make_series(title: str, days_ago: float) -> dict:
    added = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {"id": hash(title), "title": title, "added": added, "monitored": True}


class TestGetRecentAdditions:
    async def test_filters_by_cutoff(self, connector):
        series = [_make_series("New Show", 1), _make_series("Old Show", 30)]
        connector.get_series = AsyncMock(return_value=series)
        result = await connector.get_recent_additions(days=7)
        assert len(result) == 1
        assert result[0]["title"] == "New Show"

    async def test_sorted_most_recent_first(self, connector):
        s1 = _make_series("Earlier", days_ago=5)
        s2 = _make_series("Latest", days_ago=1)
        connector.get_series = AsyncMock(return_value=[s1, s2])
        result = await connector.get_recent_additions(days=7)
        assert result[0]["title"] == "Latest"

    async def test_series_without_added_field_skipped(self, connector):
        series = [{"id": 1, "title": "No Date", "monitored": True}]
        connector.get_series = AsyncMock(return_value=series)
        result = await connector.get_recent_additions(days=7)
        assert result == []

    async def test_invalid_date_format_skipped(self, connector):
        series = [{"id": 1, "title": "Bad Date", "added": "not-a-date"}]
        connector.get_series = AsyncMock(return_value=series)
        result = await connector.get_recent_additions(days=7)
        assert result == []

    async def test_exception_returns_empty_list(self, connector):
        connector.get_series = AsyncMock(side_effect=Exception("fail"))
        result = await connector.get_recent_additions()
        assert result == []


# ── get_history ───────────────────────────────────────────────────────────────


class TestGetHistory:
    async def test_returns_records(self, connector):
        payload = {"records": [{"id": 1, "seriesId": 10, "downloadId": "a" * 40}]}
        connector.client.get = AsyncMock(return_value=_make_response(payload))
        result = await connector.get_history(page_size=10)
        assert len(result) == 1
        assert result[0]["seriesId"] == 10

    async def test_empty_records_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"records": []}))
        result = await connector.get_history()
        assert result == []

    async def test_passes_event_type_param(self, connector):
        connector.client.get = AsyncMock(return_value=_make_response({"records": []}))
        await connector.get_history()
        call_params = connector.client.get.call_args.kwargs["params"]
        assert call_params["eventType"] == 3  # Downloaded

    async def test_exception_returns_empty_list(self, connector):
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.get_history()
        assert result == []


# ── get_series_history_map ────────────────────────────────────────────────────


class TestGetSeriesHistoryMap:
    async def test_returns_first_hash_per_series(self, connector):
        hash_a = "a" * 40
        hash_b = "b" * 40
        torrents_map = {
            1: [{"hash": hash_a.upper(), "episode_id": 101, "season_number": 1, "is_season_pack": False}],
            2: [{"hash": hash_b.upper(), "episode_id": 201, "season_number": 1, "is_season_pack": False}],
        }
        connector.get_series_torrents_map = AsyncMock(return_value=torrents_map)
        result = await connector.get_series_history_map()
        assert result[1] == hash_a.upper()
        assert result[2] == hash_b.upper()


# ── get_series_torrents_map ───────────────────────────────────────────────────


class TestGetSeriesTorrentsMap:
    async def test_maps_single_hash_to_series(self, connector):
        hash_val = "a" * 40
        records = [{"seriesId": 10, "downloadId": hash_val, "episodeId": 101, "seasonNumber": 1}]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_series_torrents_map()
        assert 10 in result
        assert result[10][0]["hash"] == hash_val.upper()

    async def test_season_pack_detected_when_hash_covers_multiple_episodes(self, connector):
        hash_val = "b" * 40
        records = [
            {"seriesId": 1, "downloadId": hash_val, "episodeId": 101, "seasonNumber": 1},
            {"seriesId": 1, "downloadId": hash_val, "episodeId": 102, "seasonNumber": 1},
        ]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_series_torrents_map()
        entry = result[1][0]
        assert entry["is_season_pack"] is True
        assert entry["episode_id"] is None

    async def test_single_episode_hash_not_marked_as_season_pack(self, connector):
        hash_val = "c" * 40
        records = [{"seriesId": 1, "downloadId": hash_val, "episodeId": 101, "seasonNumber": 1}]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_series_torrents_map()
        assert result[1][0]["is_season_pack"] is False

    async def test_skips_records_without_series_id(self, connector):
        records = [{"downloadId": "a" * 40, "episodeId": 1}]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_series_torrents_map()
        assert result == {}

    async def test_skips_records_without_download_id(self, connector):
        records = [{"seriesId": 1, "episodeId": 1}]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_series_torrents_map()
        assert result == {}

    async def test_deduplicates_same_hash_per_series(self, connector):
        hash_val = "d" * 40
        records = [
            {"seriesId": 1, "downloadId": hash_val, "episodeId": 101, "seasonNumber": 1},
            {"seriesId": 1, "downloadId": hash_val, "episodeId": 101, "seasonNumber": 1},
        ]
        connector.get_history = AsyncMock(return_value=records)
        result = await connector.get_series_torrents_map()
        # Same hash should only appear once per series
        assert len(result[1]) == 1


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

    def test_returns_none_for_none(self, connector):
        assert connector._extract_hash(None) is None

    def test_returns_none_for_empty_string(self, connector):
        assert connector._extract_hash("") is None

    def test_returns_none_for_short_string(self, connector):
        assert connector._extract_hash("tooshort") is None

    def test_prefix_part_is_discarded(self, connector):
        hash_part = "a" * 40
        result = connector._extract_hash(f"Sonarr-{hash_part}")
        assert result == hash_part.upper()


# ── monitor_episode ───────────────────────────────────────────────────────────


class TestMonitorEpisode:
    async def test_success_returns_true(self, connector):
        connector.client.put = AsyncMock(return_value=_make_response({}))
        result = await connector.monitor_episode(101)
        assert result is True

    async def test_puts_correct_payload(self, connector):
        connector.client.put = AsyncMock(return_value=_make_response({}))
        await connector.monitor_episode(101)
        payload = connector.client.put.call_args.kwargs["json"]
        assert payload["episodeIds"] == [101]
        assert payload["monitored"] is True

    async def test_exception_returns_false(self, connector):
        connector.client.put = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.monitor_episode(101)
        assert result is False


# ── search_episode ────────────────────────────────────────────────────────────


class TestSearchEpisode:
    async def test_success_returns_true(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 1}))
        result = await connector.search_episode(101)
        assert result is True

    async def test_posts_correct_command(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 1}))
        await connector.search_episode(101)
        payload = connector.client.post.call_args.kwargs["json"]
        assert payload["name"] == "EpisodeSearch"
        assert payload["episodeIds"] == [101]

    async def test_exception_returns_false(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.search_episode(101)
        assert result is False


# ── get_statistics ────────────────────────────────────────────────────────────


class TestGetStatistics:
    _SERIES = [
        {
            "id": 1,
            "title": "A",
            "monitored": True,
            "statistics": {"episodeCount": 13, "episodeFileCount": 13},
        },
        {
            "id": 2,
            "title": "B",
            "monitored": True,
            "statistics": {"episodeCount": 6, "episodeFileCount": 3},
        },
        {
            "id": 3,
            "title": "C",
            "monitored": False,
            "statistics": {"episodeCount": 10, "episodeFileCount": 10},
        },
    ]

    async def test_counts_are_correct(self, connector):
        connector.get_series = AsyncMock(return_value=self._SERIES)
        result = await connector.get_statistics()
        assert result["total_series"] == 3
        assert result["monitored_series"] == 2
        assert result["total_episodes"] == 29
        assert result["downloaded_episodes"] == 26
        assert result["missing_episodes"] == 3

    async def test_empty_library_returns_zeros(self, connector):
        connector.get_series = AsyncMock(return_value=[])
        result = await connector.get_statistics()
        assert result == {
            "total_series": 0,
            "monitored_series": 0,
            "total_episodes": 0,
            "downloaded_episodes": 0,
            "missing_episodes": 0,
        }

    async def test_exception_returns_empty_dict(self, connector):
        connector.get_series = AsyncMock(side_effect=Exception("fail"))
        result = await connector.get_statistics()
        assert result == {}


# ── refresh_series ────────────────────────────────────────────────────────────


class TestRefreshSeries:
    async def test_success_returns_true(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 1}))
        result = await connector.refresh_series(5)
        assert result is True

    async def test_posts_correct_command(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 1}))
        await connector.refresh_series(5)
        payload = connector.client.post.call_args.kwargs["json"]
        assert payload["name"] == "RefreshSeries"
        assert payload["seriesId"] == 5

    async def test_exception_returns_false(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.refresh_series(5)
        assert result is False


# ── rescan_series ─────────────────────────────────────────────────────────────


class TestRescanSeries:
    async def test_success_returns_true(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 2}))
        result = await connector.rescan_series(5)
        assert result is True

    async def test_posts_correct_command(self, connector):
        connector.client.post = AsyncMock(return_value=_make_response({"id": 2}))
        await connector.rescan_series(5)
        payload = connector.client.post.call_args.kwargs["json"]
        assert payload["name"] == "RescanSeries"
        assert payload["seriesId"] == 5

    async def test_exception_returns_false(self, connector):
        connector.client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        result = await connector.rescan_series(5)
        assert result is False
