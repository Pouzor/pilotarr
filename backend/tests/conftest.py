"""
Shared pytest fixtures for Pilotarr backend tests.

Strategy:
- SQLite in-memory replaces MySQL — no Docker required.
- get_db dependency is overridden per-test with a fresh session.
- get_current_user is overridden with a fixture user (no JWT round-trip needed
  for protected routes, unless we're specifically testing auth).
- The lifespan schedulers and MySQL health-check are patched out.
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── Set required env vars BEFORE any app import ──────────────────────────────
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pilotarr-testing-only!")
os.environ.setdefault("API_KEY", "test-api-key")

# ── App imports (after env vars are set) ─────────────────────────────────────
from app.core.security import get_current_user  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import (  # noqa: E402
    DeviceType,
    MediaType,
    PlaybackMethod,
    ServiceType,
    SessionStatus,
    VideoQuality,
)
from app.models.models import (  # noqa: E402
    DailyAnalytic,
    DeviceStatistic,
    Episode,
    LibraryItem,
    PlaybackSession,
    Season,
    ServerMetric,
    ServiceConfiguration,
    User,
)
from app.services.auth_service import create_access_token, hash_password  # noqa: E402

# ── SQLite in-memory engine ───────────────────────────────────────────────────
SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Core DB fixture ───────────────────────────────────────────────────────────


@pytest.fixture()
def db():
    """Fresh SQLite session per test; tables created and dropped around each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ── TestClient fixture ────────────────────────────────────────────────────────


@pytest.fixture()
def client(db):
    """
    TestClient with:
    - get_db overridden to use the in-memory SQLite session.
    - lifespan patched (no MySQL check, no scheduler start).
    - get_current_user NOT overridden here — use `auth_client` for that.
    """

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    with (
        patch("app.main.check_db_connection", return_value=False),
        patch("app.main.app_scheduler"),
        patch("app.main.analytics_scheduler"),
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def auth_client(client, db):
    """
    TestClient where get_current_user returns a real User from the test DB.
    Use this for all JWT-protected routes.
    """
    user = User(
        username="testuser",
        hashed_password=hash_password("testpass"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# ── Auth helpers ──────────────────────────────────────────────────────────────


@pytest.fixture()
def auth_headers(db):
    """
    Return Bearer headers built from a real JWT for 'testuser'.
    Useful when you need an actual token (e.g., testing the auth routes themselves).
    """
    user = User(
        username="testuser",
        hashed_password=hash_password("testpass"),
        is_active=True,
    )
    db.add(user)
    db.commit()

    token = create_access_token("testuser")
    return {"Authorization": f"Bearer {token}"}


# ── Data factories ────────────────────────────────────────────────────────────


@pytest.fixture()
def make_library_item(db):
    """Factory: create and persist a LibraryItem."""

    def _make(
        title="Test Movie",
        year=2024,
        media_type=MediaType.MOVIE,
        quality="1080p",
        size="4.2 GB",
        rating="7.5",
        description="A test description.",
        jellyfin_id=None,
        nb_media=1,
        watched=False,
    ):
        item = LibraryItem(
            title=title,
            year=year,
            media_type=media_type,
            image_url="https://example.com/poster.jpg",
            image_alt=title,
            quality=quality,
            size=size,
            rating=rating,
            description=description,
            jellyfin_id=jellyfin_id,
            nb_media=nb_media,
            watched=watched,
            created_at=datetime(2025, 1, 15, 10, 0, 0),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    return _make


@pytest.fixture()
def make_service_config(db):
    """Factory: create and persist a ServiceConfiguration."""

    def _make(
        service_name=ServiceType.SONARR,
        url="http://localhost",
        port=8989,
        api_key="test-api-key",
        is_active=True,
    ):
        svc = ServiceConfiguration(
            service_name=service_name,
            url=url,
            port=port,
            api_key=api_key,
            is_active=is_active,
        )
        db.add(svc)
        db.commit()
        db.refresh(svc)
        return svc

    return _make


@pytest.fixture()
def make_tv_show(db, make_library_item):
    """Factory: create a TV LibraryItem with one Season and two Episodes."""

    def _make(title="Test Show", sonarr_series_id=42):
        show = make_library_item(title=title, media_type=MediaType.TV, size="10 GB")

        season = Season(
            library_item_id=show.id,
            sonarr_series_id=sonarr_series_id,
            season_number=1,
            monitored=True,
            episode_count=2,
            episode_file_count=1,
            total_episode_count=2,
        )
        db.add(season)
        db.flush()

        ep1 = Episode(
            season_id=season.id,
            library_item_id=show.id,
            sonarr_episode_id=101,
            sonarr_series_id=sonarr_series_id,
            season_number=1,
            episode_number=1,
            title="Pilot",
            monitored=True,
            has_file=True,
            downloaded=True,
            watched=False,
        )
        ep2 = Episode(
            season_id=season.id,
            library_item_id=show.id,
            sonarr_episode_id=102,
            sonarr_series_id=sonarr_series_id,
            season_number=1,
            episode_number=2,
            title="Episode 2",
            monitored=False,
            has_file=False,
            downloaded=False,
            watched=False,
        )
        db.add_all([ep1, ep2])
        db.commit()
        db.refresh(show)
        return show, season, [ep1, ep2]

    return _make


@pytest.fixture()
def make_playback_session(db):
    """Factory: create and persist a PlaybackSession."""

    def _make(
        media_id="media_abc",
        media_title="Test Movie",
        media_type=MediaType.MOVIE,
        episode_info=None,
        user_id="user_abc",
        user_name="testuser",
        device_type=DeviceType.WEB_BROWSER,
        device_name="Desktop",
        client_name="Jellyfin Web",
        video_quality=VideoQuality.FULL_HD,
        playback_method=PlaybackMethod.DIRECT_PLAY,
        video_codec_source="h264",
        video_codec_target=None,
        transcoding_progress=0,
        transcoding_speed=None,
        duration_seconds=3600,
        watched_seconds=0,
        status=SessionStatus.ACTIVE,
        is_active=True,
        library_item_id=None,
        start_time=None,
        end_time=None,
    ):
        if start_time is None:
            start_time = datetime.utcnow()
        session = PlaybackSession(
            media_id=media_id,
            media_title=media_title,
            media_type=media_type,
            episode_info=episode_info,
            user_id=user_id,
            user_name=user_name,
            device_type=device_type,
            device_name=device_name,
            client_name=client_name,
            video_quality=video_quality,
            playback_method=playback_method,
            video_codec_source=video_codec_source,
            video_codec_target=video_codec_target,
            transcoding_progress=transcoding_progress,
            transcoding_speed=transcoding_speed,
            duration_seconds=duration_seconds,
            watched_seconds=watched_seconds,
            status=status,
            is_active=is_active,
            library_item_id=library_item_id,
            start_time=start_time,
            end_time=end_time,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    return _make


@pytest.fixture()
def make_daily_analytic(db):
    """Factory: create and persist a DailyAnalytic."""

    def _make(
        stat_date=None,
        total_plays=1,
        hours_watched=1.0,
        unique_users=1,
        unique_media=1,
        movies_played=1,
        tv_episodes_played=0,
        direct_play_count=1,
        transcoded_count=0,
    ):
        from datetime import date as date_type

        if stat_date is None:
            stat_date = date_type.today()
        analytic = DailyAnalytic(
            date=stat_date,
            total_plays=total_plays,
            hours_watched=hours_watched,
            unique_users=unique_users,
            unique_media=unique_media,
            movies_played=movies_played,
            tv_episodes_played=tv_episodes_played,
            direct_play_count=direct_play_count,
            transcoded_count=transcoded_count,
        )
        db.add(analytic)
        db.commit()
        db.refresh(analytic)
        return analytic

    return _make


@pytest.fixture()
def make_server_metric(db):
    """Factory: create and persist a ServerMetric."""

    def _make(
        cpu_usage_percent=25.0,
        memory_usage_gb=8.0,
        memory_total_gb=16.0,
        storage_used_tb=2.0,
        storage_total_tb=10.0,
        bandwidth_mbps=50.0,
        cpu_status="success",
        memory_status="success",
        storage_status="success",
        bandwidth_status="success",
        active_sessions_count=0,
        active_transcoding_count=0,
    ):
        metric = ServerMetric(
            cpu_usage_percent=cpu_usage_percent,
            memory_usage_gb=memory_usage_gb,
            memory_total_gb=memory_total_gb,
            storage_used_tb=storage_used_tb,
            storage_total_tb=storage_total_tb,
            bandwidth_mbps=bandwidth_mbps,
            cpu_status=cpu_status,
            memory_status=memory_status,
            storage_status=storage_status,
            bandwidth_status=bandwidth_status,
            active_sessions_count=active_sessions_count,
            active_transcoding_count=active_transcoding_count,
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric

    return _make


@pytest.fixture()
def make_device_statistic(db):
    """Factory: create and persist a DeviceStatistic."""

    def _make(
        device_type=DeviceType.WEB_BROWSER,
        period_start=None,
        period_end=None,
        session_count=1,
        total_duration_seconds=3600,
        unique_users=1,
    ):
        from datetime import date as date_type

        today = date_type.today()
        stat = DeviceStatistic(
            device_type=device_type,
            period_start=period_start or today,
            period_end=period_end or today,
            session_count=session_count,
            total_duration_seconds=total_duration_seconds,
            unique_users=unique_users,
        )
        db.add(stat)
        db.commit()
        db.refresh(stat)
        return stat

    return _make
