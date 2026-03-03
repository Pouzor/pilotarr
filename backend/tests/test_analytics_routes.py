"""Integration tests for analytics routes (webhook + protected GET endpoints)."""

import json
from datetime import date, datetime, timedelta

import pytest

from app.models.enums import DeviceType, MediaType, SessionStatus

# ── Shared helpers ─────────────────────────────────────────────────────────────

VALID_MEDIA_ID = "a" * 32  # 32 hex chars
VALID_USER_ID = "b" * 32
WEBHOOK_URL = "/api/analytics/webhook/playback?apiKey=test-api-key"


def _play_payload(
    event="Play",
    media_id=VALID_MEDIA_ID,
    user_id=VALID_USER_ID,
    item_type="Movie",
    name="Inception",
    year=2010,
    play_method="DirectPlay",
    height=1080,
    run_time_ticks=86400_000_000,  # 8640 s
    series_id=None,
    series_name=None,
):
    item = {
        "Id": media_id,
        "Name": name,
        "Type": item_type,
        "ProductionYear": year,
        "RunTimeTicks": run_time_ticks,
        "MediaStreams": [{"Type": "Video", "Height": height, "Codec": "h264", "VideoRange": "SDR"}],
        "ImageTags": {"Primary": "img"},
    }
    if item_type == "Episode":
        item["ParentIndexNumber"] = 1
        item["IndexNumber"] = 1
        if series_id:
            item["SeriesId"] = series_id
        if series_name:
            item["SeriesName"] = series_name

    return {
        "Event": event,
        "Item": item,
        "User": {"Id": user_id, "Name": "alice"},
        "Session": {
            "DeviceName": "Desktop",
            "Client": "Jellyfin Web",
            "PlayState": {"PlayMethod": play_method, "PositionTicks": 0},
        },
    }


def _stop_payload(media_id=VALID_MEDIA_ID, user_id=VALID_USER_ID, position_ticks=27_000_000_000):
    """position_ticks of 27_000_000_000 = 2700 s watched (75% of 3600s)."""
    p = _play_payload("Stop", media_id=media_id, user_id=user_id)
    p["Session"]["PlayState"]["PositionTicks"] = position_ticks
    return p


def _post_webhook(client, payload):
    headers = {"Content-Type": "application/json"}
    return client.post(WEBHOOK_URL, content=json.dumps(payload), headers=headers)


# ── Webhook: Play ──────────────────────────────────────────────────────────────


class TestWebhookPlay:
    def test_play_event_creates_session(self, client):
        r = _post_webhook(client, _play_payload())
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert body["event"] == "playback.start"
        assert "session_id" in body

    def test_play_episode_creates_tv_session(self, client):
        payload = _play_payload(
            item_type="Episode",
            series_id="c" * 32,
            series_name="Breaking Bad",
        )
        r = _post_webhook(client, payload)
        assert r.status_code == 200
        assert r.json()["status"] == "success"

    def test_play_matches_movie_library_item_by_jellyfin_id(self, client, db, make_library_item):
        make_library_item(title="Inception", year=2010, media_type=MediaType.MOVIE, jellyfin_id=VALID_MEDIA_ID)
        r = _post_webhook(client, _play_payload())
        assert r.status_code == 200

    def test_play_matches_movie_by_title_and_year_fallback(self, client, db, make_library_item):
        make_library_item(title="Inception", year=2010, media_type=MediaType.MOVIE)
        r = _post_webhook(client, _play_payload())
        assert r.status_code == 200

    def test_play_matches_tv_by_series_name_fallback(self, client, db, make_library_item):
        make_library_item(title="Breaking Bad", media_type=MediaType.TV)
        payload = _play_payload(item_type="Episode", series_name="Breaking Bad")
        r = _post_webhook(client, payload)
        assert r.status_code == 200

    def test_play_learns_jellyfin_id_when_matched_by_title(self, client, db, make_library_item):
        movie = make_library_item(title="Inception", year=2010, media_type=MediaType.MOVIE)
        assert movie.jellyfin_id is None

        _post_webhook(client, _play_payload(name="Inception", year=2010))

        db.refresh(movie)
        assert movie.jellyfin_id == VALID_MEDIA_ID

    def test_play_transcoded_session(self, client):
        payload = _play_payload(play_method="Transcode")
        r = _post_webhook(client, payload)
        assert r.status_code == 200

    def test_play_4k_hdr_video(self, client):
        payload = _play_payload(height=2160)
        payload["Item"]["MediaStreams"][0]["VideoRange"] = "HDR"
        r = _post_webhook(client, payload)
        assert r.status_code == 200


# ── Webhook: Stop ──────────────────────────────────────────────────────────────


class TestWebhookStop:
    def test_stop_event_closes_session(self, client):
        _post_webhook(client, _play_payload())
        r = _post_webhook(client, _stop_payload())
        assert r.status_code == 200
        assert r.json()["status"] == "success"
        assert r.json()["event"] == "playback.stop"

    def test_stop_without_active_session_returns_no_active(self, client):
        r = _post_webhook(client, _stop_payload())
        assert r.status_code == 200
        assert r.json()["status"] == "no_active_session"


# ── Webhook: Pause / Resume ────────────────────────────────────────────────────


class TestWebhookPauseResume:
    def test_pause_event(self, client):
        _post_webhook(client, _play_payload())
        pause = _play_payload("Pause")
        r = _post_webhook(client, pause)
        assert r.status_code == 200
        assert r.json()["event"] == "playback.pause"

    def test_pause_without_session_returns_no_active(self, client):
        r = _post_webhook(client, _play_payload("Pause"))
        assert r.status_code == 200
        assert r.json()["status"] == "no_active_session"

    def test_resume_event(self, client):
        _post_webhook(client, _play_payload())
        _post_webhook(client, _play_payload("Pause"))
        r = _post_webhook(client, _play_payload("Resume"))
        assert r.status_code == 200
        assert r.json()["event"] == "playback.unpause"

    def test_unsupported_event_is_ignored(self, client):
        payload = _play_payload("ScrobbleItem")
        r = _post_webhook(client, payload)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"


# ── Webhook: Auth & Validation errors ─────────────────────────────────────────


class TestWebhookErrors:
    def test_wrong_api_key_returns_401(self, client):
        r = client.post(
            "/api/analytics/webhook/playback?apiKey=bad-key",
            content=json.dumps(_play_payload()),
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 401

    def test_missing_media_id_returns_400(self, client):
        payload = _play_payload()
        del payload["Item"]["Id"]
        r = _post_webhook(client, payload)
        assert r.status_code == 400

    def test_missing_user_id_returns_400(self, client):
        payload = _play_payload()
        del payload["User"]["Id"]
        r = _post_webhook(client, payload)
        assert r.status_code == 400

    def test_invalid_media_id_format_returns_400(self, client):
        payload = _play_payload(media_id="not-valid!!")
        r = _post_webhook(client, payload)
        assert r.status_code == 400

    def test_oversized_payload_returns_413(self, client):
        big_body = "x" * (1_048_576 + 1)
        r = client.post(WEBHOOK_URL, content=big_body, headers={"Content-Type": "application/json"})
        assert r.status_code == 413


# ── GET /analytics/usage ───────────────────────────────────────────────────────


class TestGetUsageAnalytics:
    def test_returns_empty_list_when_no_data(self, auth_client):
        r = auth_client.get("/api/analytics/usage")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_daily_analytics_in_range(self, auth_client, db, make_daily_analytic):
        today = date.today()
        make_daily_analytic(stat_date=today, total_plays=5, hours_watched=3.0)

        r = auth_client.get(f"/api/analytics/usage?start_date={today}&end_date={today}")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["total_plays"] == 5
        assert data[0]["hours_watched"] == pytest.approx(3.0)

    def test_excludes_data_outside_range(self, auth_client, db, make_daily_analytic):
        today = date.today()
        yesterday = today - timedelta(days=1)
        make_daily_analytic(stat_date=yesterday)

        r = auth_client.get(f"/api/analytics/usage?start_date={today}&end_date={today}")
        assert r.status_code == 200
        assert r.json() == []

    def test_default_range_is_7_days(self, auth_client, db, make_daily_analytic):
        today = date.today()
        make_daily_analytic(stat_date=today)
        make_daily_analytic(stat_date=today - timedelta(days=30))

        r = auth_client.get("/api/analytics/usage")
        assert r.status_code == 200
        assert len(r.json()) == 1  # only today's record is in default 7-day window


# ── GET /analytics/media ───────────────────────────────────────────────────────


class TestGetMediaAnalytics:
    def test_returns_empty_list_when_no_sessions(self, auth_client):
        r = auth_client.get("/api/analytics/media")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_media_with_play_count(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="m1", media_title="Inception", is_active=False, status=SessionStatus.STOPPED)
        make_playback_session(media_id="m1", media_title="Inception", is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/media")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["plays"] == 2

    def test_sort_by_plays(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="m1", media_title="A", is_active=False, status=SessionStatus.STOPPED)
        make_playback_session(media_id="m1", is_active=False, status=SessionStatus.STOPPED)
        make_playback_session(media_id="m2", media_title="B", is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/media?sort_by=plays&order=desc")
        assert r.status_code == 200
        data = r.json()
        assert data[0]["plays"] >= data[-1]["plays"]

    def test_limit_parameter(self, auth_client, db, make_playback_session):
        for i in range(5):
            make_playback_session(media_id=f"m{i}", is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/media?limit=3")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_duration_formatted(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="m1", watched_seconds=7320, is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/media")
        assert r.status_code == 200
        assert "h" in r.json()[0]["duration"]


# ── GET /analytics/sessions/active ────────────────────────────────────────────


class TestGetActiveSessions:
    def test_returns_empty_when_no_active_sessions(self, auth_client):
        r = auth_client.get("/api/analytics/sessions/active")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_active_sessions_only(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="active", is_active=True)
        make_playback_session(media_id="stopped", is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/sessions/active")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["media_title"] == "Test Movie"

    def test_response_contains_expected_fields(self, auth_client, db, make_playback_session):
        make_playback_session(
            media_id="s1",
            is_active=True,
            transcoding_progress=45,
            transcoding_speed=1.5,
        )
        r = auth_client.get("/api/analytics/sessions/active")
        assert r.status_code == 200
        item = r.json()[0]
        assert "media_title" in item
        assert "user_name" in item
        assert "device_type" in item
        assert item["progress"] == 45
        assert item["speed"] == pytest.approx(1.5)


# ── GET /analytics/devices ─────────────────────────────────────────────────────


class TestGetDeviceBreakdown:
    def test_returns_empty_when_no_sessions(self, auth_client):
        r = auth_client.get("/api/analytics/devices")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_device_breakdown_with_percentages(self, auth_client, db, make_playback_session):
        make_playback_session(device_type=DeviceType.WEB_BROWSER)
        make_playback_session(device_type=DeviceType.WEB_BROWSER)
        make_playback_session(device_type=DeviceType.MOBILE_APP)

        r = auth_client.get("/api/analytics/devices")
        assert r.status_code == 200
        data = r.json()
        total_pct = sum(d["percentage"] for d in data)
        assert total_pct == pytest.approx(100.0)

    def test_percentage_calculation(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="a", device_type=DeviceType.WEB_BROWSER)
        make_playback_session(media_id="b", device_type=DeviceType.MOBILE_APP)

        r = auth_client.get("/api/analytics/devices")
        assert r.status_code == 200
        data = {d["device_type"]: d["percentage"] for d in r.json()}
        assert data["web_browser"] == pytest.approx(50.0)
        assert data["mobile_app"] == pytest.approx(50.0)


# ── GET /analytics/server-metrics ─────────────────────────────────────────────


class TestGetServerMetrics:
    def test_returns_none_when_no_metrics(self, auth_client):
        r = auth_client.get("/api/analytics/server-metrics")
        assert r.status_code == 200
        assert r.json() is None

    def test_returns_latest_metric(self, auth_client, db, make_server_metric):
        make_server_metric(cpu_usage_percent=42.0, memory_usage_gb=10.0)

        r = auth_client.get("/api/analytics/server-metrics")
        assert r.status_code == 200
        data = r.json()
        assert data is not None
        assert data["cpu_usage_percent"] == pytest.approx(42.0)
        assert data["memory_usage_gb"] == pytest.approx(10.0)

    def test_includes_active_sessions_in_response(self, auth_client, db, make_server_metric, make_playback_session):
        make_server_metric()
        make_playback_session(is_active=True)

        r = auth_client.get("/api/analytics/server-metrics")
        assert r.status_code == 200
        assert len(r.json()["active_sessions"]) == 1

    def test_cpu_status_in_response(self, auth_client, db, make_server_metric):
        make_server_metric(cpu_status="warning")

        r = auth_client.get("/api/analytics/server-metrics")
        assert r.json()["cpu_status"] == "warning"


# ── GET /analytics/users ───────────────────────────────────────────────────────


class TestGetUserLeaderboard:
    def test_returns_empty_when_no_sessions(self, auth_client):
        r = auth_client.get("/api/analytics/users")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_users_ranked_by_hours(self, auth_client, db, make_playback_session):
        make_playback_session(user_name="alice", watched_seconds=7200, is_active=False, status=SessionStatus.STOPPED)
        make_playback_session(user_name="bob", watched_seconds=3600, is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/users")
        assert r.status_code == 200
        data = r.json()
        assert data[0]["user_name"] == "alice"
        assert data[1]["user_name"] == "bob"
        assert data[0]["hours_watched"] == pytest.approx(2.0)

    def test_excludes_active_sessions(self, auth_client, db, make_playback_session):
        make_playback_session(user_name="active_user", is_active=True)

        r = auth_client.get("/api/analytics/users")
        assert r.status_code == 200
        assert r.json() == []

    def test_limit_parameter(self, auth_client, db, make_playback_session):
        for i in range(5):
            make_playback_session(
                media_id=f"m{i}",
                user_name=f"user{i}",
                watched_seconds=100 * (5 - i),
                is_active=False,
                status=SessionStatus.STOPPED,
            )
        r = auth_client.get("/api/analytics/users?limit=3")
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_movie_and_episode_counts(self, auth_client, db, make_playback_session):
        make_playback_session(
            user_name="alice", media_type=MediaType.MOVIE, is_active=False, status=SessionStatus.STOPPED
        )
        make_playback_session(
            user_name="alice", media_type=MediaType.TV, is_active=False, status=SessionStatus.STOPPED, media_id="b"
        )

        r = auth_client.get("/api/analytics/users")
        assert r.status_code == 200
        alice = r.json()[0]
        assert alice["movies_count"] == 1
        assert alice["episodes_count"] == 1


# ── GET /analytics/sessions ────────────────────────────────────────────────────


class TestGetSessions:
    def test_returns_empty_when_no_sessions(self, auth_client):
        r = auth_client.get("/api/analytics/sessions")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_stopped_sessions(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="s1", is_active=False, status=SessionStatus.STOPPED)

        r = auth_client.get("/api/analytics/sessions")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_excludes_active_sessions(self, auth_client, db, make_playback_session):
        make_playback_session(media_id="active", is_active=True)

        r = auth_client.get("/api/analytics/sessions")
        assert r.status_code == 200
        assert r.json() == []

    def test_date_range_filter(self, auth_client, db, make_playback_session):
        today = datetime.utcnow()
        old = today - timedelta(days=60)

        make_playback_session(media_id="recent", start_time=today, is_active=False, status=SessionStatus.STOPPED)
        make_playback_session(media_id="old", start_time=old, is_active=False, status=SessionStatus.STOPPED)

        start = (today - timedelta(days=1)).date().isoformat()
        end = today.date().isoformat()
        r = auth_client.get(f"/api/analytics/sessions?start={start}&end={end}")
        assert r.status_code == 200
        ids = [s["media_id"] for s in r.json()]
        assert "recent" in ids
        assert "old" not in ids

    def test_deduplicates_by_title_episode_user_day(self, auth_client, db, make_playback_session):
        today = datetime.utcnow()

        # Same title + episode + user + day → keep the one with more watched_seconds
        make_playback_session(
            media_id="s1",
            media_title="Show",
            episode_info="S01E01",
            user_name="alice",
            watched_seconds=100,
            start_time=today,
            is_active=False,
            status=SessionStatus.STOPPED,
        )
        make_playback_session(
            media_id="s2",
            media_title="Show",
            episode_info="S01E01",
            user_name="alice",
            watched_seconds=900,  # more watched
            start_time=today,
            is_active=False,
            status=SessionStatus.STOPPED,
        )

        r = auth_client.get("/api/analytics/sessions")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["watched_seconds"] == 900
