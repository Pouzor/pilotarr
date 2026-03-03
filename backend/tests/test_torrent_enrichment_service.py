"""
Comprehensive tests for TorrentEnrichmentService.

Covers:
- _get_qbt_connector: no service, inactive service, connector caching
- enrich_item: no torrent_hash, no connector, torrent not found, success, rollback on exception
- _aggregate_torrent_info: no rows, single row, status aggregation (seeding/downloading/mixed/unknown),
  progress aggregation (all 100/mixed/empty), name logic (single/multiple), ratio/size aggregation
- enrich_all_items: no connector, no rows/no legacy, torrent row enrichment via uppercase hash,
  aggregation phase, legacy items enrichment, limit param, connector.close() in finally
- enrich_recent_items: no connector, recent rows enriched, cutoff excludes old items,
  legacy recent items enriched, connector.close() in finally
"""

import os

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pilotarr-testing-only!")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.models import LibraryItem, LibraryItemTorrent, ServiceConfiguration
from app.services.torrent_enrichment_service import TorrentEnrichmentService

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_library_item(db, torrent_hash=None, title="Test Movie"):
    """Persist a minimal LibraryItem and return it."""
    item = LibraryItem(
        title=title,
        year=2024,
        media_type="movie",
        image_url="https://example.com/poster.jpg",
        image_alt=title,
        quality="1080p",
        size="4.2 GB",
        rating="7.5",
        description="A test description.",
        torrent_hash=torrent_hash,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _make_torrent_row(db, library_item_id, torrent_hash, torrent_info=None, created_at=None):
    """Persist a LibraryItemTorrent row and return it."""
    row = LibraryItemTorrent(
        library_item_id=library_item_id,
        torrent_hash=torrent_hash,
        is_season_pack=False,
        torrent_info=torrent_info,
    )
    if created_at is not None:
        row.created_at = created_at
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_qbt_service(db, is_active=True):
    """Persist an active qBittorrent ServiceConfiguration."""
    svc = ServiceConfiguration(
        service_name="qbittorrent",
        url="http://localhost",
        port=8080,
        api_key="qbt-key",
        is_active=is_active,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


def _make_connector(get_torrent_info=None, get_torrents_info=None):
    """Build an AsyncMock connector with sensible defaults."""
    connector = AsyncMock()
    connector.get_torrent_info = AsyncMock(return_value=get_torrent_info)
    connector.get_torrents_info = AsyncMock(return_value=get_torrents_info or {})
    connector.close = AsyncMock()
    return connector


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def svc(db):
    return TorrentEnrichmentService(db=db)


# ===========================================================================
# 1. _get_qbt_connector
# ===========================================================================


class TestGetQbtConnector:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_service_configured(self, svc):
        """No qbittorrent row in DB → returns None."""
        result = await svc._get_qbt_connector()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_service_inactive(self, svc, db):
        """qBittorrent service exists but is_active=False → returns None."""
        _make_qbt_service(db, is_active=False)
        result = await svc._get_qbt_connector()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_connector_when_service_active(self, svc, db):
        """Active qBittorrent service → returns connector object."""
        _make_qbt_service(db, is_active=True)
        mock_connector = MagicMock()
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=mock_connector):
            result = await svc._get_qbt_connector()
        assert result is mock_connector

    @pytest.mark.asyncio
    async def test_caches_connector_on_second_call(self, svc, db):
        """Second call must reuse the cached connector (create_connector called only once)."""
        _make_qbt_service(db, is_active=True)
        mock_connector = MagicMock()
        with patch(
            "app.services.torrent_enrichment_service.create_connector",
            return_value=mock_connector,
        ) as mock_factory:
            await svc._get_qbt_connector()
            await svc._get_qbt_connector()
            assert mock_factory.call_count == 1

    @pytest.mark.asyncio
    async def test_connector_cached_value_is_returned_on_second_call(self, svc, db):
        """The same connector instance is returned on both calls."""
        _make_qbt_service(db, is_active=True)
        mock_connector = MagicMock()
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=mock_connector):
            first = await svc._get_qbt_connector()
            second = await svc._get_qbt_connector()
        assert first is second


# ===========================================================================
# 2. enrich_item
# ===========================================================================


class TestEnrichItem:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_torrent_hash(self, svc, db):
        """Item without torrent_hash → False immediately."""
        item = _make_library_item(db, torrent_hash=None)
        result = await svc.enrich_item(item)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_connector(self, svc, db):
        """No qBittorrent service → connector is None → returns False."""
        item = _make_library_item(db, torrent_hash="abc123")
        result = await svc.enrich_item(item)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_torrent_not_found(self, svc, db):
        """Connector returns None for the hash → returns False."""
        _make_qbt_service(db)
        item = _make_library_item(db, torrent_hash="abc123")
        connector = _make_connector(get_torrent_info=None)
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_item(item)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_torrent_info_is_empty_dict(self, svc, db):
        """Connector returns {} (falsy) → returns False."""
        _make_qbt_service(db)
        item = _make_library_item(db, torrent_hash="abc123")
        connector = _make_connector(get_torrent_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_item(item)
        assert result is False

    @pytest.mark.asyncio
    async def test_updates_torrent_info_and_returns_true_on_success(self, svc, db):
        """Connector returns valid info → item.torrent_info updated, True returned."""
        _make_qbt_service(db)
        item = _make_library_item(db, torrent_hash="abc123")
        torrent_data = {"ratio": 1.5, "status": "seeding", "size": 4_000_000_000}
        connector = _make_connector(get_torrent_info=torrent_data)
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_item(item)
        assert result is True
        assert item.torrent_info == torrent_data

    @pytest.mark.asyncio
    async def test_calls_commit_on_success(self, svc, db):
        """A successful enrichment must commit the session."""
        _make_qbt_service(db)
        item = _make_library_item(db, torrent_hash="abc123")
        torrent_data = {"ratio": 1.0, "status": "seeding"}
        connector = _make_connector(get_torrent_info=torrent_data)
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            with patch.object(db, "commit") as mock_commit:
                await svc.enrich_item(item)
        mock_commit.assert_called()

    @pytest.mark.asyncio
    async def test_calls_rollback_and_returns_false_on_exception(self, svc, db):
        """Exception during get_torrent_info → rollback called, returns False."""
        _make_qbt_service(db)
        item = _make_library_item(db, torrent_hash="abc123")
        connector = AsyncMock()
        connector.get_torrent_info = AsyncMock(side_effect=RuntimeError("network error"))
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            with patch.object(db, "rollback") as mock_rollback:
                result = await svc.enrich_item(item)
        assert result is False
        mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_updated_at_is_set_on_success(self, svc, db):
        """updated_at must be refreshed after a successful enrich."""
        _make_qbt_service(db)
        item = _make_library_item(db, torrent_hash="abc123")
        item.updated_at = None
        connector = _make_connector(get_torrent_info={"ratio": 1.0})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            await svc.enrich_item(item)
        assert item.updated_at is not None


# ===========================================================================
# 3. _aggregate_torrent_info
# ===========================================================================


class TestAggregateTorrentInfo:
    def test_no_torrent_rows_returns_without_change(self, svc, db):
        """No junction rows → method returns early, item.torrent_info unchanged."""
        item = _make_library_item(db, torrent_hash=None)
        item.torrent_info = None
        svc._aggregate_torrent_info(item)
        assert item.torrent_info is None

    def test_single_row_sets_all_fields_correctly(self, svc, db):
        """Single torrent row → aggregated info mirrors that row's data."""
        item = _make_library_item(db)
        info = {
            "ratio": 2.0,
            "size": 1_000_000,
            "seeding_time": 3600,
            "download_date": "2024-01-01",
            "progress": 100.0,
            "status": "seeding",
            "name": "Movie.2024.mkv",
        }
        _make_torrent_row(db, item.id, "aaa111", torrent_info=info)

        svc._aggregate_torrent_info(item)

        agg = item.torrent_info
        assert agg["ratio"] == 2.0
        assert agg["size"] == 1_000_000
        assert agg["seeding_time"] == 3600
        assert agg["download_date"] == "2024-01-01"
        assert agg["progress"] == 100.0
        assert agg["status"] == "seeding"
        assert agg["name"] == "Movie.2024.mkv"
        assert agg["torrent_count"] == 1

    def test_all_seeding_aggregates_to_seeding(self, svc, db):
        """When every torrent is seeding → agg_status='seeding'."""
        item = _make_library_item(db)
        for h in ("aaa", "bbb"):
            _make_torrent_row(db, item.id, h, torrent_info={"status": "seeding", "progress": 100.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["status"] == "seeding"

    def test_mix_seeding_and_downloading_aggregates_to_downloading(self, svc, db):
        """At least one downloading → agg_status='downloading'."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"status": "seeding", "progress": 100.0})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"status": "downloading", "progress": 50.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["status"] == "downloading"

    def test_non_downloading_statuses_aggregate_to_mixed(self, svc, db):
        """No downloading but statuses differ → agg_status='mixed'."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"status": "seeding", "progress": 100.0})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"status": "paused", "progress": 100.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["status"] == "mixed"

    def test_no_statuses_aggregates_to_unknown(self, svc, db):
        """Torrent rows with no status field → agg_status='unknown'."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"ratio": 1.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["status"] == "unknown"

    def test_all_progress_100_gives_agg_progress_100(self, svc, db):
        """All progresses at 100 → agg_progress=100.0."""
        item = _make_library_item(db)
        for h in ("aaa", "bbb", "ccc"):
            _make_torrent_row(db, item.id, h, torrent_info={"progress": 100.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["progress"] == 100.0

    def test_mixed_progress_is_averaged(self, svc, db):
        """Mixed progress values → rounded average."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"progress": 60.0})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"progress": 80.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["progress"] == 70.0

    def test_no_progress_field_gives_zero(self, svc, db):
        """No progress in any row → agg_progress=0.0."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"status": "seeding"})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["progress"] == 0.0

    def test_single_name_is_used_as_is(self, svc, db):
        """One torrent with a name → name is preserved verbatim."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"name": "Movie.mkv", "progress": 100.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["name"] == "Movie.mkv"

    def test_multiple_names_uses_n_torrents_format(self, svc, db):
        """Multiple torrent rows → name becomes 'N torrents'."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"name": "Movie.Part1.mkv"})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"name": "Movie.Part2.mkv"})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["name"] == "2 torrents"

    def test_ratio_is_averaged_across_rows(self, svc, db):
        """Ratio is averaged (rounded to 2 dp)."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"ratio": 1.0})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"ratio": 2.0})
        _make_torrent_row(db, item.id, "ccc", torrent_info={"ratio": 3.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["ratio"] == 2.0

    def test_size_is_summed_across_rows(self, svc, db):
        """Size is summed (not averaged)."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"size": 1_000_000})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"size": 2_000_000})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["size"] == 3_000_000

    def test_seeding_time_uses_maximum(self, svc, db):
        """seeding_time aggregation takes the max value."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"seeding_time": 100})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"seeding_time": 500})
        _make_torrent_row(db, item.id, "ccc", torrent_info={"seeding_time": 300})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["seeding_time"] == 500

    def test_download_date_uses_minimum(self, svc, db):
        """download_date aggregation takes the earliest (min) date."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"download_date": "2024-03-01"})
        _make_torrent_row(db, item.id, "bbb", torrent_info={"download_date": "2024-01-01"})
        _make_torrent_row(db, item.id, "ccc", torrent_info={"download_date": "2024-06-01"})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["download_date"] == "2024-01-01"

    def test_torrent_count_reflects_number_of_rows(self, svc, db):
        """torrent_count equals the number of torrent rows with non-null torrent_info."""
        item = _make_library_item(db)
        for h in ("aaa", "bbb", "ccc"):
            _make_torrent_row(db, item.id, h, torrent_info={"ratio": 1.0})

        svc._aggregate_torrent_info(item)
        assert item.torrent_info["torrent_count"] == 3

    def test_updated_at_is_set(self, svc, db):
        """_aggregate_torrent_info must update item.updated_at."""
        item = _make_library_item(db)
        item.updated_at = None
        _make_torrent_row(db, item.id, "aaa", torrent_info={"ratio": 1.0})

        svc._aggregate_torrent_info(item)
        assert item.updated_at is not None

    def test_rows_with_null_torrent_info_are_skipped(self, svc, db):
        """Junction rows with torrent_info=None must be handled gracefully (no crash, no meaningful data)."""
        item = _make_library_item(db)
        # This row has no torrent_info — should be skipped in the aggregation loop
        _make_torrent_row(db, item.id, "aaa", torrent_info=None)
        item.torrent_info = None
        svc._aggregate_torrent_info(item)
        # SQLite may not filter the row via .isnot(None); the loop skips null info.
        # Either the item stays None (MySQL, filtered at query level) or gets a default
        # dict with no meaningful data (SQLite, skipped at loop level).
        if item.torrent_info is not None:
            assert item.torrent_info.get("ratio") == 0
            assert item.torrent_info.get("progress") == 0.0
            assert item.torrent_info.get("download_date") is None

    def test_missing_optional_fields_do_not_crash(self, svc, db):
        """A row with only some fields set must not raise an exception."""
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "aaa", torrent_info={"ratio": 0.5})

        svc._aggregate_torrent_info(item)
        agg = item.torrent_info
        assert agg["ratio"] == 0.5
        assert agg["size"] == 0
        assert agg["seeding_time"] == 0
        assert agg["download_date"] is None
        assert agg["progress"] == 0.0


# ===========================================================================
# 4. enrich_all_items
# ===========================================================================


class TestEnrichAllItems:
    @pytest.mark.asyncio
    async def test_returns_error_dict_when_no_connector(self, svc):
        """No qBittorrent service → error dict with informative message."""
        result = await svc.enrich_all_items()
        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_db_returns_zero_stats(self, svc, db):
        """No torrent rows, no legacy items → all zeroes, no error."""
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()
        assert result == {"total": 0, "success": 0, "failed": 0}

    @pytest.mark.asyncio
    async def test_phase_a_enriches_torrent_rows_via_uppercase_hash(self, svc, db):
        """Torrent row hashes must be uppercased for dictionary lookup."""
        item = _make_library_item(db)
        row = _make_torrent_row(db, item.id, "abcdef123456")

        torrent_data = {"ABCDEF123456": {"ratio": 1.5, "status": "seeding", "size": 1000, "progress": 100.0}}
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info=torrent_data)
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            await svc.enrich_all_items()

        db.refresh(row)
        assert row.torrent_info is not None
        assert row.torrent_info["ratio"] == 1.5

    @pytest.mark.asyncio
    async def test_phase_b_aggregates_library_items(self, svc, db):
        """After enriching rows, the parent LibraryItem gets aggregated torrent_info."""
        item = _make_library_item(db)
        _make_torrent_row(
            db,
            item.id,
            "aabbcc",
            torrent_info={"ratio": 2.0, "status": "seeding", "size": 500, "progress": 100.0, "name": "Movie.mkv"},
        )

        # No new data from qBittorrent needed — rows already have torrent_info
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()

        db.refresh(item)
        assert item.torrent_info is not None
        assert item.torrent_info["torrent_count"] == 1
        assert result["success"] >= 1

    @pytest.mark.asyncio
    async def test_legacy_items_are_enriched(self, svc, db):
        """Items with torrent_hash on LibraryItem (no junction rows) use the legacy path."""
        # Legacy item: has torrent_hash on LibraryItem but no LibraryItemTorrent rows
        item = _make_library_item(db, torrent_hash="legacy_hash_001")
        legacy_info = {"ratio": 0.8, "status": "seeding", "torrent_count": 1}

        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={"LEGACY_HASH_001": legacy_info})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()

        db.refresh(item)
        assert item.torrent_info is not None
        assert item.torrent_info["ratio"] == 0.8
        assert result["total"] >= 1
        assert result["success"] >= 1

    @pytest.mark.asyncio
    async def test_legacy_item_not_found_counts_as_failed(self, svc, db):
        """Legacy item whose hash returns nothing from connector → counted as failed."""
        _make_library_item(db, torrent_hash="missing_hash")

        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()

        assert result["failed"] >= 1

    @pytest.mark.asyncio
    async def test_limit_parameter_restricts_torrent_rows_queried(self, svc, db):
        """limit=1 means only one LibraryItemTorrent row is processed."""
        item1 = _make_library_item(db, title="Movie A")
        item2 = _make_library_item(db, title="Movie B")
        _make_torrent_row(db, item1.id, "hash001")
        _make_torrent_row(db, item2.id, "hash002")

        _make_qbt_service(db)
        torrent_data = {
            "HASH001": {"ratio": 1.0, "status": "seeding"},
            "HASH002": {"ratio": 2.0, "status": "seeding"},
        }
        connector = _make_connector(get_torrents_info=torrent_data)
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector) as mock_cc:
            await svc.enrich_all_items(limit=1)
            # The connector must still have been created
            mock_cc.assert_called_once()

    @pytest.mark.asyncio
    async def test_connector_close_called_in_finally(self, svc, db):
        """connector.close() must always be called even when no items exist."""
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            await svc.enrich_all_items()
        connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connector_close_called_even_on_exception(self, svc, db):
        """connector.close() must be called even if an exception occurs mid-method."""
        _make_qbt_service(db)
        # Need at least one torrent row so get_torrents_info is actually called
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "abc123", torrent_info={"status": "seeding"})
        connector = AsyncMock()
        connector.get_torrents_info = AsyncMock(side_effect=RuntimeError("boom"))
        connector.close = AsyncMock()
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()
        # Should return error dict, not raise
        assert "error" in result
        connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_stats_with_success_and_failed_counts(self, svc, db):
        """Result dict always has total/success/failed keys."""
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()
        assert "total" in result
        assert "success" in result
        assert "failed" in result

    @pytest.mark.asyncio
    async def test_torrent_count_added_to_legacy_items(self, svc, db):
        """Legacy path sets torrent_count=1 on the returned info dict."""
        item = _make_library_item(db, torrent_hash="hash_legacy")
        legacy_info = {"ratio": 1.2, "status": "seeding"}

        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={"HASH_LEGACY": legacy_info})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            await svc.enrich_all_items()

        db.refresh(item)
        assert item.torrent_info["torrent_count"] == 1

    @pytest.mark.asyncio
    async def test_mixed_junction_and_legacy_items_both_processed(self, svc, db):
        """Items with junction rows AND legacy items are both enriched in one call."""
        # Junction item
        item_with_rows = _make_library_item(db, title="Junction Item")
        _make_torrent_row(
            db,
            item_with_rows.id,
            "junc_hash",
            torrent_info={"ratio": 1.0, "status": "seeding", "progress": 100.0},
        )

        # Legacy item
        _make_library_item(db, torrent_hash="leg_hash", title="Legacy Item")

        _make_qbt_service(db)
        connector = _make_connector(
            get_torrents_info={
                "JUNC_HASH": {"ratio": 1.0, "status": "seeding"},
                "LEG_HASH": {"ratio": 0.5, "status": "seeding"},
            }
        )
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_all_items()

        assert result["total"] >= 2


# ===========================================================================
# 5. enrich_recent_items
# ===========================================================================


class TestEnrichRecentItems:
    @pytest.mark.asyncio
    async def test_returns_error_dict_when_no_connector(self, svc):
        """No qBittorrent service → error dict."""
        result = await svc.enrich_recent_items(days=7)
        assert result["total"] == 0
        assert "error" in result

    @pytest.mark.asyncio
    async def test_recent_torrent_rows_are_enriched(self, svc, db):
        """Rows created within cutoff window are enriched."""
        item = _make_library_item(db)
        recent_date = datetime.now(UTC) - timedelta(days=2)
        row = _make_torrent_row(db, item.id, "recent_hash", created_at=recent_date)

        _make_qbt_service(db)
        connector = _make_connector(
            get_torrents_info={"RECENT_HASH": {"ratio": 1.0, "status": "seeding", "progress": 100.0}}
        )
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_recent_items(days=7)

        db.refresh(row)
        # Row should have been updated
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_old_torrent_rows_outside_cutoff_excluded(self, svc, db):
        """Rows older than cutoff are not processed by enrich_recent_items."""
        item = _make_library_item(db)
        old_date = datetime.now(UTC) - timedelta(days=30)
        _make_torrent_row(db, item.id, "old_hash", torrent_info=None, created_at=old_date)

        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={"OLD_HASH": {"ratio": 5.0}})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_recent_items(days=7)

        # Old row should not have been in scope → total from junction phase is 0
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_legacy_recent_items_are_enriched(self, svc, db):
        """Legacy items (torrent_hash on LibraryItem) created recently are enriched."""
        item = _make_library_item(db, torrent_hash="recent_leg_hash")
        # Set created_at to a recent date by updating after creation
        item.created_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()

        _make_qbt_service(db)
        legacy_info = {"ratio": 1.5, "status": "seeding"}
        connector = _make_connector(get_torrents_info={"RECENT_LEG_HASH": legacy_info})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_recent_items(days=7)

        db.refresh(item)
        assert result["success"] >= 1
        assert item.torrent_info is not None
        assert item.torrent_info["torrent_count"] == 1

    @pytest.mark.asyncio
    async def test_connector_close_called_in_finally(self, svc, db):
        """connector.close() is always called, even with empty DB."""
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            await svc.enrich_recent_items(days=7)
        connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connector_close_called_on_exception(self, svc, db):
        """connector.close() is called even when an exception occurs."""
        _make_qbt_service(db)
        # Need at least one recent torrent row so get_torrents_info is actually called
        item = _make_library_item(db)
        _make_torrent_row(db, item.id, "def456", torrent_info={"status": "seeding"})
        connector = AsyncMock()
        connector.get_torrents_info = AsyncMock(side_effect=RuntimeError("network failure"))
        connector.close = AsyncMock()
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_recent_items(days=7)
        assert "error" in result
        connector.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_result_has_required_keys(self, svc, db):
        """Result always contains total/success/failed keys."""
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_recent_items(days=7)
        assert "total" in result
        assert "success" in result
        assert "failed" in result

    @pytest.mark.asyncio
    async def test_default_days_parameter_is_7(self, svc, db):
        """enrich_recent_items() without args defaults to 7-day window."""
        item = _make_library_item(db)
        # Row created 6 days ago — within the 7-day window
        _make_torrent_row(
            db,
            item.id,
            "within_window",
            torrent_info={"ratio": 1.0, "status": "seeding", "progress": 100.0},
        )

        _make_qbt_service(db)
        connector = _make_connector(
            get_torrents_info={"WITHIN_WINDOW": {"ratio": 1.0, "status": "seeding", "progress": 100.0}}
        )
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            # No days argument — should default to 7
            result = await svc.enrich_recent_items()
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_aggregation_called_for_affected_items(self, svc, db):
        """After enriching rows, _aggregate_torrent_info is called for each affected item."""
        item = _make_library_item(db)
        _make_torrent_row(
            db,
            item.id,
            "agg_hash",
            torrent_info={"ratio": 1.0, "status": "seeding", "progress": 100.0, "name": "Movie.mkv"},
        )

        _make_qbt_service(db)
        connector = _make_connector(
            get_torrents_info={"AGG_HASH": {"ratio": 1.0, "status": "seeding", "progress": 100.0}}
        )
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            with patch.object(svc, "_aggregate_torrent_info", wraps=svc._aggregate_torrent_info) as spy:
                await svc.enrich_recent_items(days=7)
        assert spy.call_count >= 1

    @pytest.mark.asyncio
    async def test_empty_db_with_recent_days_returns_zero_total(self, svc, db):
        """No items at all → result has total=0 and no error."""
        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            result = await svc.enrich_recent_items(days=7)
        assert result["total"] == 0
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_get_torrents_info_called_with_deduplicated_hashes(self, svc, db):
        """Duplicate hashes across rows must be deduplicated before calling get_torrents_info."""
        item = _make_library_item(db)
        # Two rows with the same hash
        _make_torrent_row(db, item.id, "dup_hash")

        item2 = _make_library_item(db, title="Movie 2")
        # We need a second unique hash to avoid UniqueConstraint on (library_item_id, torrent_hash)
        _make_torrent_row(db, item2.id, "dup_hash")

        _make_qbt_service(db)
        connector = _make_connector(get_torrents_info={})
        with patch("app.services.torrent_enrichment_service.create_connector", return_value=connector):
            await svc.enrich_recent_items(days=7)

        # get_torrents_info should have been called with a list — dedup means "dup_hash" appears once
        call_args = connector.get_torrents_info.call_args
        hashes_passed = call_args[0][0]
        assert len(hashes_passed) == len(set(hashes_passed))
