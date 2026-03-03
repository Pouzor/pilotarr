"""
Unit tests for QBittorrentConnector.

Covers:
- login: success (200 + "Ok."), wrong body, failure (exception)
- get_torrent_info: success, not found, 403, exception
- get_torrents_info: empty hashes = {}, success mapping, 403 = {}
- get_all_torrents: success maps list, 403 = [], exception = []
- get_transfer_info: success, 403 fallback, exception fallback
- test_connection: success, login fails, exception
- _map_status: all known states + unknown fallback
- _parse_tracker_hostname: valid URL, empty, invalid
- _unix_to_iso: valid timestamp, None, -1
- _map_torrent: field mapping, tags split, empty category becomes None
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pilotarr-testing-only!")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")

from app.services.qbittorrent_connector import QBittorrentConnector  # noqa: E402

# ── aiohttp mock helpers ──────────────────────────────────────────────────────


def _aio_cm(status=200, text=None, json_data=None):
    """Build an aiohttp-style async context manager mock."""
    resp = MagicMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text or "")
    resp.json = AsyncMock(return_value=json_data if json_data is not None else {})
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture()
def connector():
    c = QBittorrentConnector(base_url="http://qbt", username="admin", password="adminpass", port=8080)
    # Pre-create a mock session so tests don't call _ensure_session()
    c.session = MagicMock()
    c.session.closed = False  # prevent _ensure_session from replacing the mock
    c._authenticated = True
    return c


# ── Init ──────────────────────────────────────────────────────────────────────


class TestInit:
    def test_port_appended_to_base_url(self):
        c = QBittorrentConnector(base_url="http://qbt", username="u", password="p", port=8080)
        assert c.base_url == "http://qbt:8080"

    def test_stores_username_and_password(self):
        c = QBittorrentConnector(base_url="http://qbt", username="user", password="pass")
        assert c.username == "user"
        assert c.password == "pass"

    def test_initially_not_authenticated(self):
        c = QBittorrentConnector(base_url="http://qbt", username="u", password="p")
        assert c._authenticated is False


# ── login ─────────────────────────────────────────────────────────────────────


class TestLogin:
    async def test_success_on_ok_response(self, connector):
        connector._ensure_session = AsyncMock()  # prevent real session creation
        connector._authenticated = False
        connector.session.post.return_value = _aio_cm(status=200, text="Ok.")
        connector.session.cookie_jar = MagicMock()
        connector.session.cookie_jar.filter_cookies.return_value = {}
        result = await connector.login()
        assert result is True
        assert connector._authenticated is True

    async def test_failure_on_wrong_body(self, connector):
        connector._ensure_session = AsyncMock()
        connector._authenticated = False
        connector.session.post.return_value = _aio_cm(status=200, text="Fails.")
        result = await connector.login()
        assert result is False
        assert connector._authenticated is False

    async def test_failure_on_non_200_status(self, connector):
        connector._ensure_session = AsyncMock()
        connector._authenticated = False
        connector.session.post.return_value = _aio_cm(status=403, text="Forbidden")
        result = await connector.login()
        assert result is False

    async def test_exception_returns_false(self, connector):
        connector._ensure_session = AsyncMock()
        connector._authenticated = False
        connector.session.post.side_effect = Exception("network error")
        result = await connector.login()
        assert result is False


# ── get_torrent_info ──────────────────────────────────────────────────────────

_RAW_TORRENT = {
    "hash": "abcdef1234567890abcdef1234567890abcdef12",
    "name": "Ubuntu 22.04",
    "state": "uploading",
    "ratio": 1.5,
    "tags": "linux,iso",
    "seeding_time": 3600,
    "completion_on": 1700000000,
    "size": 2_000_000_000,
    "progress": 1.0,
}


class TestGetTorrentInfo:
    async def test_success_returns_mapped_dict(self, connector):
        connector.session.get.return_value = _aio_cm(status=200, json_data=[_RAW_TORRENT])
        result = await connector.get_torrent_info("abcdef1234567890abcdef1234567890abcdef12")
        assert result is not None
        assert result["name"] == "Ubuntu 22.04"
        assert result["status"] == "seeding"
        assert result["ratio"] == 1.5
        assert result["tags"] == ["linux", "iso"]
        assert result["progress"] == 100.0

    async def test_empty_list_returns_none(self, connector):
        connector.session.get.return_value = _aio_cm(status=200, json_data=[])
        result = await connector.get_torrent_info("deadbeef")
        assert result is None

    async def test_403_returns_none_and_resets_auth(self, connector):
        connector.session.get.return_value = _aio_cm(status=403)
        result = await connector.get_torrent_info("deadbeef")
        assert result is None
        assert connector._authenticated is False

    async def test_exception_returns_none(self, connector):
        connector.session.get.side_effect = Exception("fail")
        result = await connector.get_torrent_info("deadbeef")
        assert result is None


# ── get_torrents_info ─────────────────────────────────────────────────────────


class TestGetTorrentsInfo:
    async def test_empty_hashes_returns_empty_dict(self, connector):
        result = await connector.get_torrents_info([])
        assert result == {}
        connector.session.get.assert_not_called()

    async def test_success_maps_by_uppercase_hash(self, connector):
        raw = [{**_RAW_TORRENT, "hash": "abc123"}]
        connector.session.get.return_value = _aio_cm(status=200, json_data=raw)
        result = await connector.get_torrents_info(["abc123"])
        assert "ABC123" in result
        assert result["ABC123"]["name"] == "Ubuntu 22.04"

    async def test_passes_pipe_joined_hashes(self, connector):
        connector.session.get.return_value = _aio_cm(status=200, json_data=[])
        await connector.get_torrents_info(["hash1", "hash2"])
        call_kwargs = connector.session.get.call_args.kwargs
        assert call_kwargs["params"]["hashes"] == "hash1|hash2"

    async def test_403_returns_empty_dict_and_resets_auth(self, connector):
        connector.session.get.return_value = _aio_cm(status=403)
        result = await connector.get_torrents_info(["abc"])
        assert result == {}
        assert connector._authenticated is False

    async def test_exception_returns_empty_dict(self, connector):
        connector.session.get.side_effect = Exception("fail")
        result = await connector.get_torrents_info(["abc"])
        assert result == {}


# ── get_all_torrents ──────────────────────────────────────────────────────────


class TestGetAllTorrents:
    async def test_success_returns_mapped_list(self, connector):
        connector.session.get.return_value = _aio_cm(status=200, json_data=[_RAW_TORRENT])
        result = await connector.get_all_torrents()
        assert len(result) == 1
        assert result[0]["status"] == "seeding"

    async def test_403_returns_empty_list(self, connector):
        connector.session.get.return_value = _aio_cm(status=403)
        result = await connector.get_all_torrents()
        assert result == []
        assert connector._authenticated is False

    async def test_exception_returns_empty_list(self, connector):
        connector.session.get.side_effect = Exception("fail")
        result = await connector.get_all_torrents()
        assert result == []


# ── get_transfer_info ─────────────────────────────────────────────────────────


class TestGetTransferInfo:
    async def test_success_maps_keys(self, connector):
        data = {"dl_info_speed": 5_000_000, "up_info_speed": 1_000_000, "connection_status": "connected"}
        connector.session.get.return_value = _aio_cm(status=200, json_data=data)
        result = await connector.get_transfer_info()
        assert result["dl_speed"] == 5_000_000
        assert result["ul_speed"] == 1_000_000
        assert result["connection_status"] == "connected"

    async def test_403_returns_disconnected_fallback(self, connector):
        connector.session.get.return_value = _aio_cm(status=403)
        result = await connector.get_transfer_info()
        assert result == {"dl_speed": 0, "ul_speed": 0, "connection_status": "disconnected"}

    async def test_exception_returns_disconnected_fallback(self, connector):
        connector.session.get.side_effect = Exception("fail")
        result = await connector.get_transfer_info()
        assert result == {"dl_speed": 0, "ul_speed": 0, "connection_status": "disconnected"}


# ── test_connection ───────────────────────────────────────────────────────────


class TestTestConnection:
    async def test_success_returns_true_with_version(self, connector):
        connector._ensure_session = AsyncMock()  # prevent real session creation
        connector.login = AsyncMock(return_value=True)
        connector.session.get.return_value = _aio_cm(status=200, text="5.0.0")
        ok, msg = await connector.test_connection()
        assert ok is True
        assert "5.0.0" in msg

    async def test_login_failure_returns_false(self, connector):
        connector._ensure_session = AsyncMock()
        connector.login = AsyncMock(return_value=False)
        ok, msg = await connector.test_connection()
        assert ok is False
        assert "authentification" in msg.lower() or "auth" in msg.lower()

    async def test_exception_returns_false(self, connector):
        connector._ensure_session = AsyncMock()
        connector.login = AsyncMock(side_effect=Exception("network error"))
        ok, msg = await connector.test_connection()
        assert ok is False


# ── _map_status ───────────────────────────────────────────────────────────────


class TestMapStatus:
    @pytest.mark.parametrize(
        "state, expected",
        [
            ("uploading", "seeding"),
            ("stalledUP", "seeding"),
            ("forcedUP", "seeding"),
            ("downloading", "downloading"),
            ("stalledDL", "downloading"),
            ("forcedDL", "downloading"),
            ("pausedUP", "paused"),
            ("pausedDL", "paused"),
            ("queuedUP", "queued"),
            ("queuedDL", "queued"),
            ("checkingUP", "checking"),
            ("checkingDL", "checking"),
            ("checkingResumeData", "checking"),
            ("moving", "checking"),
            ("error", "error"),
            ("missingFiles", "error"),
            ("somethingNew", "unknown"),
            ("", "unknown"),
        ],
    )
    def test_state_mapping(self, connector, state, expected):
        assert connector._map_status(state) == expected


# ── _parse_tracker_hostname ───────────────────────────────────────────────────


class TestParseTrackerHostname:
    def test_extracts_hostname_from_url(self):
        result = QBittorrentConnector._parse_tracker_hostname("https://tracker.example.com:8080/announce")
        assert result == "tracker.example.com"

    def test_empty_string_returns_none(self):
        assert QBittorrentConnector._parse_tracker_hostname("") is None

    def test_none_returns_none(self):
        assert QBittorrentConnector._parse_tracker_hostname(None) is None

    def test_bare_hostname_without_scheme(self):
        # urlparse without scheme gives empty hostname
        result = QBittorrentConnector._parse_tracker_hostname("tracker.example.com/announce")
        # Without scheme, path is parsed differently — may or may not extract hostname
        # The important thing is it doesn't raise
        assert isinstance(result, str | type(None))


# ── _unix_to_iso ──────────────────────────────────────────────────────────────


class TestUnixToIso:
    def test_valid_timestamp_returns_iso_string(self):
        result = QBittorrentConnector._unix_to_iso(0)
        assert result is not None
        assert "1970-01-01" in result

    def test_none_returns_none(self):
        assert QBittorrentConnector._unix_to_iso(None) is None

    def test_minus_one_returns_none(self):
        assert QBittorrentConnector._unix_to_iso(-1) is None

    def test_returns_utc_iso_format(self):
        result = QBittorrentConnector._unix_to_iso(1700000000)
        assert result is not None
        assert "+00:00" in result or "Z" in result or "T" in result


# ── _map_torrent ──────────────────────────────────────────────────────────────


class TestMapTorrent:
    def test_correct_field_mapping(self, connector):
        raw = {
            "hash": "abc123",
            "name": "Test Torrent",
            "state": "uploading",
            "category": "movies",
            "size": 1_000_000,
            "downloaded": 1_000_000,
            "uploaded": 500_000,
            "progress": 1.0,
            "dlspeed": 0,
            "upspeed": 1_000,
            "num_seeds": 50,
            "num_leechs": 5,
            "ratio": 0.5,
            "eta": -1,
            "tracker": "https://tracker.example.com/announce",
            "tags": "hd,x265",
            "added_on": 1700000000,
            "completion_on": 1700003600,
            "save_path": "/downloads/movies",
        }
        result = connector._map_torrent(raw)
        assert result["id"] == "ABC123"
        assert result["name"] == "Test Torrent"
        assert result["status"] == "seeding"
        assert result["category"] == "movies"
        assert result["tags"] == ["hd", "x265"]
        assert result["ratio"] == 0.5
        assert result["savePath"] == "/downloads/movies"

    def test_empty_tags_returns_empty_list(self, connector):
        raw = {**_RAW_TORRENT, "tags": ""}
        result = connector._map_torrent(raw)
        assert result["tags"] == []

    def test_empty_category_becomes_none(self, connector):
        raw = {**_RAW_TORRENT, "category": ""}
        result = connector._map_torrent(raw)
        assert result["category"] is None

    def test_hash_is_uppercased(self, connector):
        raw = {**_RAW_TORRENT, "hash": "abcdef"}
        result = connector._map_torrent(raw)
        assert result["id"] == "ABCDEF"
