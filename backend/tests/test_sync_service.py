"""
Unit/integration tests for SyncService.

Covers:
- get_active_service: returns active config, ignores inactive
- _upsert_torrent: insert once, idempotent on duplicate
- update_sync_metadata: create new entry, update existing
- _format_time_ago: all time buckets (days, hours, minutes, just now)
- sync_radarr: no service, new movie inserted, existing movie updated, calendar events
- sync_sonarr: no service, new series inserted, existing updated, calendar events
- sync_sonarr_seasons: no service, seasons created and updated
- sync_sonarr_episodes: no service, no series, episodes created and updated
- sync_monitored_items: aggregates Radarr+Sonarr stats into DashboardStatistic
- sync_jellyfin: no service, creates user/movie/tv dashboard stats
- sync_jellyseerr: no service, adds requests, updates existing, deletes stale
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pilotarr-testing-only!")
os.environ.setdefault("API_KEY", "test-api-key")

from app.models import (  # noqa: E402
    CalendarEvent,
    DashboardStatistic,
    Episode,
    JellyseerrRequest,
    LibraryItem,
    LibraryItemTorrent,
    MediaType,
    Season,
    ServiceConfiguration,
    ServiceType,
    StatType,
    SyncMetadata,
    SyncStatus,
)
from app.schedulers.sync_service import SyncService  # noqa: E402


@pytest.fixture()
def sync(db):
    return SyncService(db=db)


def _make_svc(db, service_type, is_active=True):
    svc = ServiceConfiguration(
        service_name=service_type,
        url="http://localhost",
        port=7878,
        api_key="key",
        is_active=is_active,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


# ── get_active_service ────────────────────────────────────────────────────────


class TestGetActiveService:
    def test_returns_active_service(self, sync, db):
        _make_svc(db, ServiceType.RADARR, is_active=True)
        svc = sync.get_active_service(ServiceType.RADARR)
        assert svc is not None
        assert svc.service_name == ServiceType.RADARR

    def test_returns_none_when_inactive(self, sync, db):
        _make_svc(db, ServiceType.RADARR, is_active=False)
        svc = sync.get_active_service(ServiceType.RADARR)
        assert svc is None

    def test_returns_none_when_not_configured(self, sync):
        svc = sync.get_active_service(ServiceType.RADARR)
        assert svc is None


# ── _upsert_torrent ───────────────────────────────────────────────────────────


class TestUpsertTorrent:
    def test_inserts_new_torrent(self, sync, db, make_library_item):
        item = make_library_item()
        sync._upsert_torrent(item.id, "a" * 40)
        db.commit()
        row = db.query(LibraryItemTorrent).filter_by(library_item_id=item.id).first()
        assert row is not None
        assert row.torrent_hash == "a" * 40

    def test_idempotent_on_duplicate(self, sync, db, make_library_item):
        item = make_library_item()
        sync._upsert_torrent(item.id, "b" * 40)
        db.commit()
        sync._upsert_torrent(item.id, "b" * 40)
        db.commit()
        count = db.query(LibraryItemTorrent).filter_by(library_item_id=item.id).count()
        assert count == 1

    def test_different_hashes_both_inserted(self, sync, db, make_library_item):
        item = make_library_item()
        sync._upsert_torrent(item.id, "a" * 40)
        sync._upsert_torrent(item.id, "b" * 40)
        db.commit()
        count = db.query(LibraryItemTorrent).filter_by(library_item_id=item.id).count()
        assert count == 2

    def test_stores_episode_and_season_metadata(self, sync, db, make_library_item):
        item = make_library_item()
        sync._upsert_torrent(item.id, "c" * 40, episode_id=5, season_number=2, is_season_pack=True)
        db.commit()
        row = db.query(LibraryItemTorrent).filter_by(library_item_id=item.id).first()
        assert row.episode_id == 5
        assert row.season_number == 2
        assert row.is_season_pack is True


# ── update_sync_metadata ──────────────────────────────────────────────────────


class TestUpdateSyncMetadata:
    def test_creates_new_entry(self, sync, db):
        sync.update_sync_metadata(ServiceType.RADARR, SyncStatus.SUCCESS, records=5, duration_ms=100)
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.RADARR).first()
        assert meta is not None
        assert meta.sync_status == SyncStatus.SUCCESS
        assert meta.records_synced == 5
        assert meta.sync_duration_ms == 100

    def test_updates_existing_entry(self, sync, db):
        sync.update_sync_metadata(ServiceType.RADARR, SyncStatus.SUCCESS, records=1)
        sync.update_sync_metadata(ServiceType.RADARR, SyncStatus.FAILED, records=0, error="boom")
        metas = db.query(SyncMetadata).filter_by(service_name=ServiceType.RADARR).all()
        assert len(metas) == 1
        assert metas[0].sync_status == SyncStatus.FAILED
        assert metas[0].error_message == "boom"

    def test_sets_next_sync_time(self, sync, db):
        before = datetime.now(UTC).replace(tzinfo=None)
        sync.update_sync_metadata(ServiceType.SONARR, SyncStatus.SUCCESS)
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.SONARR).first()
        # SQLite stores naive datetimes; strip tz for comparison
        next_sync = meta.next_sync_time
        if next_sync.tzinfo is not None:
            next_sync = next_sync.replace(tzinfo=None)
        assert next_sync > before


# ── _format_time_ago ──────────────────────────────────────────────────────────


class TestFormatTimeAgo:
    def test_just_now(self, sync):
        dt = datetime.now(UTC) - timedelta(seconds=30)
        assert sync._format_time_ago(dt) == "just now"

    def test_minutes(self, sync):
        dt = datetime.now(UTC) - timedelta(minutes=5)
        result = sync._format_time_ago(dt)
        assert "minute" in result
        assert "5" in result

    def test_one_minute_singular(self, sync):
        dt = datetime.now(UTC) - timedelta(minutes=1)
        result = sync._format_time_ago(dt)
        assert result == "1 minute ago"

    def test_hours(self, sync):
        dt = datetime.now(UTC) - timedelta(hours=3)
        result = sync._format_time_ago(dt)
        assert "3 hour" in result

    def test_one_hour_singular(self, sync):
        dt = datetime.now(UTC) - timedelta(hours=1)
        assert sync._format_time_ago(dt) == "1 hour ago"

    def test_days(self, sync):
        dt = datetime.now(UTC) - timedelta(days=4)
        result = sync._format_time_ago(dt)
        assert "4 day" in result

    def test_one_day_singular(self, sync):
        dt = datetime.now(UTC) - timedelta(days=1)
        assert sync._format_time_ago(dt) == "1 day ago"

    def test_naive_datetime_handled(self, sync):
        dt = datetime.utcnow() - timedelta(hours=2)  # naive
        result = sync._format_time_ago(dt)
        assert "hour" in result


# ── sync_radarr ───────────────────────────────────────────────────────────────

_RADARR_MOVIE = {
    "id": 1,
    "title": "Inception",
    "year": 2010,
    "overview": "A mind-bending thriller.",
    "added": "2024-01-10T00:00:00Z",
    "sizeOnDisk": 4_294_967_296,
    "hasFile": True,
    "monitored": True,
    "qualityProfileId": 1,
    "images": [{"coverType": "poster", "remoteUrl": "http://example.com/poster.jpg"}],
    "movieFile": {
        "path": "/movies/Inception/Inception.mkv",
        "quality": {"quality": {"name": "Bluray-1080p"}},
    },
    "ratings": {"imdb": {"value": 8.8}},
}

_RADARR_CALENDAR_EVENT = {
    "title": "Dune Part 3",
    "physicalRelease": "2025-06-01T00:00:00Z",
    "images": [{"coverType": "poster", "remoteUrl": "http://example.com/dune.jpg"}],
}


def _mock_radarr_connector(movies=None, calendar=None, quality_profiles=None, hash_map=None):
    m = AsyncMock()
    m.get_movies = AsyncMock(return_value=movies if movies is not None else [_RADARR_MOVIE])
    m.get_quality_profiles = AsyncMock(return_value=quality_profiles or {1: "HD-1080p"})
    m.get_movie_history_map = AsyncMock(return_value=hash_map or {1: "a" * 40})
    m.get_calendar = AsyncMock(return_value=calendar if calendar is not None else [_RADARR_CALENDAR_EVENT])
    m.get_statistics = AsyncMock(
        return_value={"monitored_movies": 2, "total_movies": 3, "downloaded_movies": 2, "missing_movies": 0}
    )
    m.close = AsyncMock()
    return m


class TestSyncRadarr:
    async def test_no_service_returns_failure(self, sync):
        result = await sync.sync_radarr()
        assert result["success"] is False

    async def test_creates_new_movie_in_db(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=_mock_radarr_connector()):
            result = await sync.sync_radarr()
        assert result["success"] is True
        assert result["movies_added"] == 1
        item = db.query(LibraryItem).filter_by(title="Inception").first()
        assert item is not None
        assert item.media_type == MediaType.MOVIE
        assert item.year == 2010

    async def test_resolves_quality_from_file(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=_mock_radarr_connector()):
            await sync.sync_radarr()
        item = db.query(LibraryItem).filter_by(title="Inception").first()
        assert item.quality == "Bluray-1080p"

    async def test_stores_torrent_hash(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=_mock_radarr_connector()):
            await sync.sync_radarr()
        item = db.query(LibraryItem).filter_by(title="Inception").first()
        torrent = db.query(LibraryItemTorrent).filter_by(library_item_id=item.id).first()
        assert torrent is not None

    async def test_updates_existing_movie(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.RADARR)
        make_library_item(title="Inception", year=2010, media_type=MediaType.MOVIE, quality="720p")
        mock = _mock_radarr_connector()
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=mock):
            result = await sync.sync_radarr()
        assert result["movies_added"] == 0  # not added again
        item = db.query(LibraryItem).filter_by(title="Inception").first()
        assert item.nb_media == 1  # updated

    async def test_creates_calendar_event(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=_mock_radarr_connector()):
            result = await sync.sync_radarr()
        assert result["calendar_events"] == 1
        cal = db.query(CalendarEvent).filter_by(title="Dune Part 3").first()
        assert cal is not None
        assert cal.media_type == MediaType.MOVIE

    async def test_calendar_event_deduplication(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        mock = _mock_radarr_connector()
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=mock):
            await sync.sync_radarr()
            await sync.sync_radarr()
        count = db.query(CalendarEvent).filter_by(title="Dune Part 3").count()
        assert count == 1

    async def test_skips_calendar_event_without_release_date(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        event = {"title": "No Date Movie", "images": []}
        mock = _mock_radarr_connector(calendar=[event])
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=mock):
            result = await sync.sync_radarr()
        assert result["calendar_events"] == 0

    async def test_writes_sync_metadata_on_success(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=_mock_radarr_connector()):
            await sync.sync_radarr()
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.RADARR).first()
        assert meta.sync_status == SyncStatus.SUCCESS

    async def test_writes_sync_metadata_on_failure(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        mock = _mock_radarr_connector()
        mock.get_movies = AsyncMock(side_effect=Exception("API down"))
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=mock):
            result = await sync.sync_radarr()
        assert result["success"] is False
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.RADARR).first()
        assert meta.sync_status == SyncStatus.FAILED


# ── sync_sonarr ───────────────────────────────────────────────────────────────

_SONARR_SERIES = {
    "id": 10,
    "title": "Breaking Bad",
    "year": 2008,
    "overview": "A chemistry teacher goes bad.",
    "added": "2024-01-05T00:00:00Z",
    "qualityProfileId": 1,
    "path": "/series/BreakingBad",
    "images": [{"coverType": "poster", "remoteUrl": "http://example.com/bb.jpg"}],
    "statistics": {"episodeFileCount": 62, "sizeOnDisk": 10_737_418_240},
    "ratings": {"value": 9.5},
    "seasons": [
        {
            "seasonNumber": 1,
            "monitored": True,
            "statistics": {"episodeCount": 7, "episodeFileCount": 7, "totalEpisodeCount": 7, "sizeOnDisk": 0},
        }
    ],
}

_SONARR_CALENDAR_EVENT = {
    "airDate": "2024-06-01",
    "seasonNumber": 2,
    "episodeNumber": 1,
    "title": "Seven Thirty-Seven",
    "series": {
        "title": "Breaking Bad",
        "images": [{"coverType": "poster", "remoteUrl": "http://example.com/bb.jpg"}],
    },
}


def _mock_sonarr_connector(series=None, calendar=None, quality_profiles=None, torrents_map=None):
    m = AsyncMock()
    m.get_series = AsyncMock(return_value=series if series is not None else [_SONARR_SERIES])
    m.get_quality_profiles = AsyncMock(return_value=quality_profiles or {1: "HD-1080p"})
    m.get_series_torrents_map = AsyncMock(return_value=torrents_map if torrents_map is not None else {})
    m.get_calendar = AsyncMock(return_value=calendar if calendar is not None else [_SONARR_CALENDAR_EVENT])
    m.get_statistics = AsyncMock(
        return_value={"monitored_series": 3, "total_series": 5, "downloaded_episodes": 100, "missing_episodes": 10}
    )
    m.get_episodes_by_series = AsyncMock(return_value=[])
    m.get_episode_files_by_series = AsyncMock(return_value=[])
    m.close = AsyncMock()
    return m


class TestSyncSonarr:
    async def test_no_service_returns_failure(self, sync):
        result = await sync.sync_sonarr()
        assert result["success"] is False

    async def test_creates_new_series_in_db(self, sync, db):
        _make_svc(db, ServiceType.SONARR)
        mock = _mock_sonarr_connector()
        # sync_sonarr_seasons also needs the connector — patch it at module level
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr()
        assert result["success"] is True
        assert result["series_added"] == 1
        item = db.query(LibraryItem).filter_by(title="Breaking Bad").first()
        assert item is not None
        assert item.media_type == MediaType.TV
        assert item.year == 2008

    async def test_does_not_duplicate_existing_series(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.SONARR)
        make_library_item(title="Breaking Bad", year=2008, media_type=MediaType.TV)
        mock = _mock_sonarr_connector()
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr()
        assert result["series_added"] == 0
        count = db.query(LibraryItem).filter_by(title="Breaking Bad").count()
        assert count == 1

    async def test_creates_calendar_event(self, sync, db):
        _make_svc(db, ServiceType.SONARR)
        mock = _mock_sonarr_connector()
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr()
        assert result["calendar_events"] == 1
        cal = db.query(CalendarEvent).filter_by(media_type=MediaType.TV).first()
        assert cal is not None
        assert cal.title == "Breaking Bad"
        assert "S02E01" in cal.episode

    async def test_skips_calendar_event_without_air_date(self, sync, db):
        _make_svc(db, ServiceType.SONARR)
        event = {"airDate": None, "seasonNumber": 1, "episodeNumber": 1, "title": "No Air", "series": {}}
        mock = _mock_sonarr_connector(calendar=[event])
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr()
        assert result["calendar_events"] == 0

    async def test_writes_sync_metadata_on_success(self, sync, db):
        _make_svc(db, ServiceType.SONARR)
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=_mock_sonarr_connector()):
            await sync.sync_sonarr()
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.SONARR).first()
        assert meta.sync_status == SyncStatus.SUCCESS


# ── sync_sonarr_seasons ───────────────────────────────────────────────────────


class TestSyncSonarrSeasons:
    async def test_no_service_returns_failure(self, sync):
        result = await sync.sync_sonarr_seasons()
        assert result["success"] is False

    async def test_creates_seasons_for_tv_item(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.SONARR)
        make_library_item(title="Breaking Bad", year=2008, media_type=MediaType.TV)
        mock = _mock_sonarr_connector()
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_seasons()
        assert result["success"] is True
        assert result["seasons_synced"] >= 1
        season = db.query(Season).first()
        assert season is not None
        assert season.season_number == 1

    async def test_updates_existing_season(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.SONARR)
        item = make_library_item(title="Breaking Bad", year=2008, media_type=MediaType.TV)
        existing_season = Season(
            library_item_id=item.id,
            sonarr_series_id=10,
            season_number=1,
            monitored=False,
            episode_count=0,
        )
        db.add(existing_season)
        db.commit()
        mock = _mock_sonarr_connector()
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_seasons()
        assert result["seasons_updated"] >= 1
        db.refresh(existing_season)
        assert existing_season.episode_count == 7

    async def test_skips_series_not_in_db(self, sync, db):
        _make_svc(db, ServiceType.SONARR)
        # DB has no TV items — sonarr returns a series but nothing to match against
        mock = _mock_sonarr_connector()
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_seasons()
        assert result["success"] is True
        assert result["seasons_synced"] == 0


# ── sync_sonarr_episodes ──────────────────────────────────────────────────────

_SONARR_EPISODE = {
    "id": 101,
    "seasonNumber": 1,
    "episodeNumber": 1,
    "title": "Pilot",
    "overview": "Walter White starts cooking.",
    "airDate": "2008-01-20",
    "monitored": True,
    "hasFile": True,
    "episodeFileId": 5,
    "absoluteEpisodeNumber": 1,
}

_SONARR_EPISODE_FILE = {
    "id": 5,
    "size": 1_073_741_824,
    "relativePath": "Season 01/bb.s01e01.mkv",
    "quality": {"quality": {"name": "Bluray-1080p"}},
}


class TestSyncSonarrEpisodes:
    async def test_no_service_returns_failure(self, sync):
        result = await sync.sync_sonarr_episodes()
        assert result["success"] is False

    async def test_no_series_in_db_returns_early(self, sync, db):
        _make_svc(db, ServiceType.SONARR)
        mock = _mock_sonarr_connector()
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_episodes()
        assert result["success"] is True
        assert result["episodes_synced"] == 0
        assert result["series_processed"] == 0

    async def test_creates_episodes_for_matching_series(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.SONARR)
        make_library_item(title="Breaking Bad", year=2008, media_type=MediaType.TV)
        mock = _mock_sonarr_connector()
        mock.get_episodes_by_series = AsyncMock(return_value=[_SONARR_EPISODE])
        mock.get_episode_files_by_series = AsyncMock(return_value=[_SONARR_EPISODE_FILE])
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_episodes()
        assert result["success"] is True
        assert result["episodes_synced"] == 1
        ep = db.query(Episode).filter_by(sonarr_episode_id=101).first()
        assert ep is not None
        assert ep.title == "Pilot"
        assert ep.has_file is True
        assert ep.quality_profile == "Bluray-1080p"

    async def test_updates_existing_episode(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.SONARR)
        item = make_library_item(title="Breaking Bad", year=2008, media_type=MediaType.TV)
        season = Season(library_item_id=item.id, sonarr_series_id=10, season_number=1)
        db.add(season)
        db.flush()
        existing_ep = Episode(
            season_id=season.id,
            library_item_id=item.id,
            sonarr_episode_id=101,
            sonarr_series_id=10,
            season_number=1,
            episode_number=1,
            title="Old Title",
            monitored=True,
            has_file=False,
            downloaded=False,
        )
        db.add(existing_ep)
        db.commit()
        mock = _mock_sonarr_connector()
        mock.get_episodes_by_series = AsyncMock(return_value=[_SONARR_EPISODE])
        mock.get_episode_files_by_series = AsyncMock(return_value=[_SONARR_EPISODE_FILE])
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_episodes()
        assert result["episodes_updated"] == 1
        db.refresh(existing_ep)
        assert existing_ep.title == "Pilot"
        assert existing_ep.has_file is True

    async def test_skips_episode_missing_season_or_number(self, sync, db, make_library_item):
        _make_svc(db, ServiceType.SONARR)
        make_library_item(title="Breaking Bad", year=2008, media_type=MediaType.TV)
        bad_episode = {**_SONARR_EPISODE, "seasonNumber": None}
        mock = _mock_sonarr_connector()
        mock.get_episodes_by_series = AsyncMock(return_value=[bad_episode])
        mock.get_episode_files_by_series = AsyncMock(return_value=[])
        with patch("app.schedulers.sync_service.SonarrConnector", return_value=mock):
            result = await sync.sync_sonarr_episodes()
        assert result["episodes_synced"] == 0


# ── sync_monitored_items ──────────────────────────────────────────────────────


class TestSyncMonitoredItems:
    def _radarr_mock(self):
        m = AsyncMock()
        m.get_statistics = AsyncMock(
            return_value={"monitored_movies": 10, "total_movies": 12, "downloaded_movies": 8, "missing_movies": 2}
        )
        m.close = AsyncMock()
        return m

    def _sonarr_mock(self):
        m = AsyncMock()
        m.get_statistics = AsyncMock(
            return_value={"monitored_series": 5, "total_series": 7, "downloaded_episodes": 50, "missing_episodes": 5}
        )
        m.close = AsyncMock()
        return m

    async def test_aggregates_radarr_and_sonarr_stats(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        _make_svc(db, ServiceType.SONARR)
        with (
            patch("app.schedulers.sync_service.RadarrConnector", return_value=self._radarr_mock()),
            patch("app.schedulers.sync_service.SonarrConnector", return_value=self._sonarr_mock()),
        ):
            result = await sync.sync_monitored_items()
        assert result["success"] is True
        assert result["monitored"] == 15  # 10 + 5

    async def test_creates_dashboard_statistic(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        _make_svc(db, ServiceType.SONARR)
        with (
            patch("app.schedulers.sync_service.RadarrConnector", return_value=self._radarr_mock()),
            patch("app.schedulers.sync_service.SonarrConnector", return_value=self._sonarr_mock()),
        ):
            await sync.sync_monitored_items()
        stat = db.query(DashboardStatistic).filter_by(stat_type=StatType.MONITORED_ITEMS).first()
        assert stat is not None
        assert stat.total_count == 15
        assert stat.details["downloaded"] == 58  # 8 + 50

    async def test_works_when_only_radarr_configured(self, sync, db):
        _make_svc(db, ServiceType.RADARR)
        with patch("app.schedulers.sync_service.RadarrConnector", return_value=self._radarr_mock()):
            result = await sync.sync_monitored_items()
        assert result["success"] is True
        assert result["monitored"] == 10

    async def test_works_when_no_services_configured(self, sync, db):
        result = await sync.sync_monitored_items()
        assert result["success"] is True
        assert result["monitored"] == 0


# ── sync_jellyfin ─────────────────────────────────────────────────────────────


def _mock_jellyfin_connector():
    m = AsyncMock()
    m.get_users = AsyncMock(return_value=[{"Policy": {"IsDisabled": False}}, {"Policy": {"IsDisabled": True}}])
    m.get_library_items = AsyncMock(return_value={"movies": 50, "tv": 20})
    m.get_total_watch_time = AsyncMock(return_value={"total_hours": 200})
    m.get_movies_details = AsyncMock(return_value={"total_movies": 50, "total_hours": 300})
    m.get_tv_shows_details = AsyncMock(return_value={"total_series": 20, "total_episodes": 400, "total_hours": 600})
    m.close = AsyncMock()
    return m


class TestSyncJellyfin:
    async def test_no_service_returns_failure(self, sync):
        result = await sync.sync_jellyfin()
        assert result["success"] is False

    async def test_creates_user_dashboard_stat(self, sync, db):
        _make_svc(db, ServiceType.JELLYFIN)
        with patch("app.schedulers.sync_service.JellyfinConnector", return_value=_mock_jellyfin_connector()):
            result = await sync.sync_jellyfin()
        assert result["success"] is True
        assert result["users"] == 2
        stat = db.query(DashboardStatistic).filter_by(stat_type=StatType.USERS).first()
        assert stat.total_count == 2
        assert stat.details["active_users"] == 1

    async def test_creates_movie_dashboard_stat(self, sync, db):
        _make_svc(db, ServiceType.JELLYFIN)
        with patch("app.schedulers.sync_service.JellyfinConnector", return_value=_mock_jellyfin_connector()):
            await sync.sync_jellyfin()
        stat = db.query(DashboardStatistic).filter_by(stat_type=StatType.MOVIES).first()
        assert stat.total_count == 50
        assert stat.details["total_hours"] == 300

    async def test_creates_tv_dashboard_stat(self, sync, db):
        _make_svc(db, ServiceType.JELLYFIN)
        with patch("app.schedulers.sync_service.JellyfinConnector", return_value=_mock_jellyfin_connector()):
            await sync.sync_jellyfin()
        stat = db.query(DashboardStatistic).filter_by(stat_type=StatType.TV_SHOWS).first()
        assert stat.total_count == 20
        assert stat.details["total_episodes"] == 400

    async def test_writes_sync_metadata(self, sync, db):
        _make_svc(db, ServiceType.JELLYFIN)
        with patch("app.schedulers.sync_service.JellyfinConnector", return_value=_mock_jellyfin_connector()):
            await sync.sync_jellyfin()
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.JELLYFIN).first()
        assert meta.sync_status == SyncStatus.SUCCESS

    async def test_error_returns_failure_and_marks_failed(self, sync, db):
        _make_svc(db, ServiceType.JELLYFIN)
        mock = _mock_jellyfin_connector()
        mock.get_users = AsyncMock(side_effect=Exception("timeout"))
        with patch("app.schedulers.sync_service.JellyfinConnector", return_value=mock):
            result = await sync.sync_jellyfin()
        assert result["success"] is False
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.JELLYFIN).first()
        assert meta.sync_status == SyncStatus.FAILED


# ── sync_jellyseerr ───────────────────────────────────────────────────────────

_JS_REQUEST = {
    "id": 1,
    "type": "movie",
    "status": 2,
    "is4k": False,
    "createdAt": "2024-01-10T12:00:00Z",
    "media": {"tmdbId": 27205},
    "requestedBy": {"displayName": "Alice", "avatar": "http://example.com/alice.jpg", "id": 10},
}

_JS_MEDIA_DETAILS = {
    "title": "Inception",
    "releaseDate": "2010-07-16",
    "overview": "A mind-bending thriller.",
    "posterPath": "/poster.jpg",
}


def _mock_jellyseerr_connector(requests=None, connection_ok=True):
    m = AsyncMock()
    m.test_connection = AsyncMock(return_value=(connection_ok, "OK"))
    m.get_requests = AsyncMock(return_value=requests if requests is not None else [_JS_REQUEST])
    m.get_media_details = AsyncMock(return_value=_JS_MEDIA_DETAILS)
    m.close = AsyncMock()
    return m


class TestSyncJellyseerr:
    async def test_no_service_returns_failure(self, sync):
        result = await sync.sync_jellyseerr()
        assert result["success"] is False

    async def test_creates_new_request(self, sync, db):
        _make_svc(db, ServiceType.JELLYSEERR)
        with patch("app.schedulers.sync_service.JellyseerrConnector", return_value=_mock_jellyseerr_connector()):
            result = await sync.sync_jellyseerr()
        assert result["success"] is True
        assert result["requests_added"] == 1
        req = db.query(JellyseerrRequest).filter_by(jellyseerr_id=1).first()
        assert req is not None
        assert req.title == "Inception"
        assert req.requested_by == "Alice"

    async def test_updates_existing_request(self, sync, db):
        _make_svc(db, ServiceType.JELLYSEERR)
        from app.models import RequestPriority, RequestStatus

        existing = JellyseerrRequest(
            jellyseerr_id=1,
            title="Old Title",
            media_type=MediaType.MOVIE,
            year=2010,
            image_url="",
            image_alt="",
            status=RequestStatus.PENDING,
            priority=RequestPriority.MEDIUM,
            requested_by="Bob",
            requested_date="Unknown",
            quality="1080p",
        )
        db.add(existing)
        db.commit()
        with patch("app.schedulers.sync_service.JellyseerrConnector", return_value=_mock_jellyseerr_connector()):
            result = await sync.sync_jellyseerr()
        assert result["requests_updated"] == 1
        db.refresh(existing)
        assert existing.title == "Inception"
        assert existing.requested_by == "Alice"

    async def test_deletes_stale_requests(self, sync, db):
        _make_svc(db, ServiceType.JELLYSEERR)
        from app.models import RequestPriority, RequestStatus

        stale = JellyseerrRequest(
            jellyseerr_id=999,  # not in API response
            title="Stale",
            media_type=MediaType.MOVIE,
            year=2000,
            image_url="",
            image_alt="",
            status=RequestStatus.PENDING,
            priority=RequestPriority.MEDIUM,
            requested_by="Ghost",
            requested_date="Unknown",
            quality="1080p",
        )
        db.add(stale)
        db.commit()
        with patch("app.schedulers.sync_service.JellyseerrConnector", return_value=_mock_jellyseerr_connector()):
            result = await sync.sync_jellyseerr()
        assert result["requests_deleted"] == 1
        assert db.query(JellyseerrRequest).filter_by(jellyseerr_id=999).first() is None

    async def test_deletes_all_when_api_returns_empty(self, sync, db):
        _make_svc(db, ServiceType.JELLYSEERR)
        from app.models import RequestPriority, RequestStatus

        for i in range(3):
            db.add(
                JellyseerrRequest(
                    jellyseerr_id=i,
                    title=f"Movie {i}",
                    media_type=MediaType.MOVIE,
                    year=2020,
                    image_url="",
                    image_alt="",
                    status=RequestStatus.PENDING,
                    priority=RequestPriority.MEDIUM,
                    requested_by="User",
                    requested_date="Unknown",
                    quality="1080p",
                )
            )
        db.commit()
        mock = _mock_jellyseerr_connector(requests=[])
        with patch("app.schedulers.sync_service.JellyseerrConnector", return_value=mock):
            result = await sync.sync_jellyseerr()
        assert result["requests_deleted"] == 3
        assert db.query(JellyseerrRequest).count() == 0

    async def test_connection_failure_returns_failure(self, sync, db):
        _make_svc(db, ServiceType.JELLYSEERR)
        mock = _mock_jellyseerr_connector(connection_ok=False)
        mock.test_connection = AsyncMock(return_value=(False, "refused"))
        with patch("app.schedulers.sync_service.JellyseerrConnector", return_value=mock):
            result = await sync.sync_jellyseerr()
        assert result["success"] is False
        meta = db.query(SyncMetadata).filter_by(service_name=ServiceType.JELLYSEERR).first()
        assert meta.sync_status == SyncStatus.FAILED
