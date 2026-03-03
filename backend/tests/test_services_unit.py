"""
Unit tests for pure business logic — no DB, no HTTP.

Covers:
- auth_service: password hashing, JWT encode/decode
- SonarrConnector._extract_hash
- QBittorrentConnector._unix_to_iso
"""

import os

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pilotarr-testing-only!")
os.environ.setdefault("API_KEY", "test-api-key")

from app.services.auth_service import (  # noqa: E402
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.services.qbittorrent_connector import QBittorrentConnector  # noqa: E402
from app.services.sonarr_connector import SonarrConnector  # noqa: E402

# ── Password helpers ──────────────────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = hash_password("correcthorsebattery")
        assert verify_password("correcthorsebattery", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correcthorsebattery")
        assert verify_password("wrongpassword", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses random salt — same plaintext → different hashes."""
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2
        # but both verify correctly
        assert verify_password("samepassword", h1) is True
        assert verify_password("samepassword", h2) is True


# ── JWT helpers ───────────────────────────────────────────────────────────────


class TestJWT:
    def test_encode_decode_roundtrip(self):
        token = create_access_token("alice")
        username = decode_access_token(token)
        assert username == "alice"

    def test_decode_invalid_token_returns_none(self):
        assert decode_access_token("not.a.valid.token") is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token("alice")
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None

    def test_different_users_get_different_tokens(self):
        t1 = create_access_token("alice")
        t2 = create_access_token("bob")
        assert t1 != t2
        assert decode_access_token(t1) == "alice"
        assert decode_access_token(t2) == "bob"


# ── SonarrConnector._extract_hash ────────────────────────────────────────────


class TestExtractHash:
    """Test the _extract_hash instance method via a minimal connector stub."""

    @pytest.fixture()
    def connector(self):
        return SonarrConnector(base_url="http://localhost", api_key="key")

    def test_qbittorrent_prefixed_format(self, connector):
        result = connector._extract_hash("qBittorrent-abc123def456abc123def456abc123def456abc1")
        assert result == "ABC123DEF456ABC123DEF456ABC123DEF456ABC1"

    def test_bare_40_char_hex(self, connector):
        raw = "a" * 40
        result = connector._extract_hash(raw)
        assert result == raw.upper()

    def test_returns_none_for_empty_string(self, connector):
        assert connector._extract_hash("") is None

    def test_returns_none_for_short_string(self, connector):
        assert connector._extract_hash("tooshort") is None

    def test_returns_none_for_non_hex(self, connector):
        assert connector._extract_hash("z" * 40) is None

    def test_result_is_uppercase(self, connector):
        raw = "abcdef1234567890abcdef1234567890abcdef12"
        result = connector._extract_hash(raw)
        assert result == raw.upper()


# ── QBittorrentConnector._unix_to_iso ────────────────────────────────────────


class TestUnixToIso:
    def test_valid_timestamp(self):
        result = QBittorrentConnector._unix_to_iso(0)
        assert result == "1970-01-01T00:00:00+00:00"

    def test_recent_timestamp(self):
        result = QBittorrentConnector._unix_to_iso(1_700_000_000)
        assert result is not None
        assert "2023" in result

    def test_none_returns_none(self):
        assert QBittorrentConnector._unix_to_iso(None) is None

    def test_minus_one_returns_none(self):
        """qBittorrent uses -1 for 'not set'."""
        assert QBittorrentConnector._unix_to_iso(-1) is None

    def test_result_is_iso_string(self):
        result = QBittorrentConnector._unix_to_iso(1_000_000_000)
        assert isinstance(result, str)
        assert "T" in result
        assert "+" in result or "Z" in result
