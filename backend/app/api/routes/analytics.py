"""
Routes API pour les analytics et webhooks
"""

import json
import logging
import re
import traceback
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, asc, case, desc, func
from sqlalchemy.orm import Session

from app.api.schemas import (
    ActiveSessionItem,
    DeviceBreakdownItem,
    MediaPlaybackAnalyticsItem,
    PlaybackSessionResponse,
    ServerPerformanceResponse,
    UsageAnalyticsResponse,
    UserLeaderboardItem,
)
from app.core.security import verify_webhook_api_key
from app.db import get_db
from app.models.enums import MediaType, PlaybackMethod, ServiceType, SessionStatus
from app.models.models import (
    DailyAnalytic,
    LibraryItem,
    PlaybackSession,
    ServerMetric,
    ServiceConfiguration,
)
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])
public_router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Pattern Jellyfin ID (hex 32 chars)
_JELLYFIN_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{1,64}$")


def _truncate(value: str | None, max_length: int = 255) -> str | None:
    """Tronque une chaîne à une longueur maximale"""
    if value is None:
        return None
    return value[:max_length]


# ============================================
# WEBHOOK ENDPOINT (PUBLIC)
# ============================================


@public_router.post("/webhook/playback", status_code=status.HTTP_200_OK)
async def receive_playback_webhook(
    request: Request,
    db: Session = Depends(get_db),
    _: str = Depends(verify_webhook_api_key),
):
    """
    Endpoint pour recevoir les webhooks de lecture depuis Jellyfin

    Événements supportés :
    - Play : Début de lecture
    - Stop : Fin de lecture
    - Pause : Mise en pause
    - Resume : Reprise de lecture
    """
    try:
        # Valider la taille du payload (max 1 Mo)
        body = await request.body()
        if len(body) > 1_048_576:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload trop volumineux")

        # Récupérer le payload
        payload = json.loads(body)

        # Extraire les données principales
        event_type_raw = payload.get("Event")
        item = payload.get("Item", {})
        user = payload.get("User", {})
        session_info = payload.get("Session", {})
        play_state = session_info.get("PlayState", {})

        # Mapping des événements
        event_mapping = {
            "Play": "playback.start",
            "Stop": "playback.stop",
            "Pause": "playback.pause",
            "Resume": "playback.unpause",
        }

        event_type = event_mapping.get(event_type_raw)

        if not event_type:
            logger.warning(f"⚠️  Type d'événement non supporté : {event_type_raw}")
            return {"status": "ignored", "event": event_type_raw}

        logger.info(f"📥 Webhook reçu : {event_type} - {item.get('Name', 'Unknown')}")

        # Extraction et validation des IDs
        media_id = item.get("Id")
        user_id = user.get("Id")

        if not media_id or not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item.Id et User.Id sont requis")

        if not _JELLYFIN_ID_PATTERN.match(str(media_id)) or not _JELLYFIN_ID_PATTERN.match(str(user_id)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format d'ID invalide")

        # Traitement selon le type d'événement
        if event_type == "playback.start":
            # Déterminer le type de média
            item_type = item.get("Type", "Movie")
            media_type = "tv" if item_type == "Episode" else "movie"

            # Info épisode si série
            episode_info = None
            if item_type == "Episode":
                season = item.get("ParentIndexNumber", 0)
                episode = item.get("IndexNumber", 0)
                episode_info = f"S{season:02d}E{episode:02d}"

            # Extraire la qualité vidéo depuis les MediaStreams
            media_streams = item.get("MediaStreams", [])
            video_stream = next((s for s in media_streams if s.get("Type") == "Video"), {})
            video_height = video_stream.get("Height", 0)

            # Mapper la qualité (vérifier HDR pour 2160p)
            video_range = video_stream.get("VideoRange", "")
            if video_height >= 2160:
                video_quality = "FOUR_K_HDR" if video_range and video_range.upper() == "HDR" else "FOUR_K"
            else:
                quality_map = {1080: "FULL_HD", 720: "HD", 480: "SD"}
                video_quality = quality_map.get(video_height, "UNKNOWN")

            # Codec vidéo source
            video_codec_source = video_stream.get("Codec", "unknown")

            # Déterminer si c'est du transcodage
            play_method = play_state.get("PlayMethod", "DirectPlay")
            is_transcoding = play_method == "Transcode"
            is_direct_playing = play_method == "DirectPlay"

            # Codec cible si transcodage
            video_codec_target = None
            if is_transcoding:
                video_codec_target = "h264"  # Par défaut pour le transcodage

            # Durée en secondes
            run_time_ticks = item.get("RunTimeTicks", 0)
            duration_seconds = run_time_ticks // 10000000 if run_time_ticks else None

            # Déterminer le type d'appareil
            device_name = session_info.get("DeviceName", "Unknown")
            client_name = session_info.get("Client", "Unknown")

            # URL du poster : Utiliser l'URL de Jellyfin depuis la base de données
            poster_url = None
            jellyfin_service = (
                db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == ServiceType.JELLYFIN).first()
            )
            if jellyfin_service:
                _jf_base = jellyfin_service.url.rstrip("/")
                _jf_port = jellyfin_service.port
                if _jf_port and f":{_jf_port}" not in _jf_base:
                    _jf_base = f"{_jf_base}:{_jf_port}"
                jellyfin_url = _jf_base
            else:
                jellyfin_url = None
            if item.get("ImageTags", {}).get("Primary") and jellyfin_url:
                poster_url = f"{jellyfin_url}/Items/{media_id}/Images/Primary"

            session_data = {
                "media_id": media_id,
                "media_title": _truncate(item.get("Name", "Unknown")),
                "media_type": media_type,
                "media_year": item.get("ProductionYear"),
                "episode_info": _truncate(episode_info, 20),
                "poster_url": _truncate(poster_url, 500),
                "user_id": user_id,
                "user_name": _truncate(user.get("Name", "Unknown")),
                "device_name": _truncate(device_name),
                "client_name": _truncate(client_name),
                "video_quality": video_quality,
                "is_transcoding": is_transcoding,
                "is_direct_playing": is_direct_playing,
                "transcoding_progress": 0,
                "transcoding_speed": None,
                "video_codec_source": _truncate(video_codec_source, 50),
                "video_codec_target": _truncate(video_codec_target, 50),
                "duration_seconds": duration_seconds,
            }

            # Recherche du LibraryItem correspondant
            library_item = None
            if media_type == "movie":
                # Primary: match by stored Jellyfin ID
                library_item = (
                    db.query(LibraryItem)
                    .filter(
                        LibraryItem.jellyfin_id == media_id,
                        LibraryItem.media_type == MediaType.MOVIE,
                    )
                    .first()
                )
                if not library_item:
                    # Fallback: case-insensitive title + year
                    movie_name = item.get("Name", "")
                    movie_year = item.get("ProductionYear")
                    library_item = (
                        db.query(LibraryItem)
                        .filter(
                            func.lower(LibraryItem.title) == movie_name.lower(),
                            LibraryItem.media_type == MediaType.MOVIE,
                            LibraryItem.year == movie_year,
                        )
                        .first()
                    )
                if not library_item:
                    # Year-relaxed fallback: case-insensitive title only
                    library_item = (
                        db.query(LibraryItem)
                        .filter(
                            func.lower(LibraryItem.title) == movie_name.lower(),
                            LibraryItem.media_type == MediaType.MOVIE,
                        )
                        .first()
                    )
            elif media_type == "tv":
                series_id = item.get("SeriesId")
                series_name = item.get("SeriesName")
                # Primary: match by stored Jellyfin series ID
                if series_id:
                    library_item = (
                        db.query(LibraryItem)
                        .filter(
                            LibraryItem.jellyfin_id == series_id,
                            LibraryItem.media_type == MediaType.TV,
                        )
                        .first()
                    )
                if not library_item and series_name:
                    # Fallback: case-insensitive series name
                    library_item = (
                        db.query(LibraryItem)
                        .filter(
                            func.lower(LibraryItem.title) == series_name.lower(),
                            LibraryItem.media_type == MediaType.TV,
                        )
                        .first()
                    )

            if library_item:
                session_data["library_item_id"] = library_item.id
                # Learn Jellyfin ID from webhook so future matches use the fast path
                if not library_item.jellyfin_id:
                    if media_type == "movie":
                        library_item.jellyfin_id = media_id
                    elif media_type == "tv":
                        jf_series_id = item.get("SeriesId")
                        if jf_series_id:
                            library_item.jellyfin_id = jf_series_id
                    db.flush()

            playback_session = AnalyticsService.start_session(db, session_data)
            logger.info(f"✅ Session créée : {playback_session.id} - {playback_session.media_title}")
            return {"status": "success", "session_id": playback_session.id, "event": event_type}

        elif event_type == "playback.stop":
            # Position de lecture en secondes
            playback_position_ticks = play_state.get("PositionTicks", 0)
            watched_seconds = playback_position_ticks // 10000000 if playback_position_ticks else 0

            playback_session = AnalyticsService.stop_session(db, media_id, user_id, watched_seconds)

            if playback_session:
                logger.info(
                    f"✅ Session arrêtée : {playback_session.id} - {playback_session.media_title} ({watched_seconds}s)"
                )
                return {"status": "success", "session_id": playback_session.id, "event": event_type}
            else:
                logger.warning(f"⚠️  Aucune session active trouvée pour media_id={media_id}, user_id={user_id}")
                return {"status": "no_active_session", "event": event_type}

        elif event_type == "playback.pause":
            playback_session = AnalyticsService.pause_session(db, media_id, user_id)
            if playback_session:
                logger.info(f"⏸️  Session mise en pause : {playback_session.id}")
                return {"status": "success", "session_id": playback_session.id, "event": event_type}
            return {"status": "no_active_session", "event": event_type}

        elif event_type == "playback.unpause":
            playback_session = AnalyticsService.resume_session(db, media_id, user_id)
            if playback_session:
                logger.info(f"▶️  Session reprise : {playback_session.id}")
                return {"status": "success", "session_id": playback_session.id, "event": event_type}
            return {"status": "no_active_session", "event": event_type}

        else:
            logger.warning(f"⚠️  Événement non supporté : {event_type}")
            return {"status": "ignored", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors du traitement du webhook : {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur"
        ) from e


# ============================================
# ANALYTICS ENDPOINTS (PROTÉGÉS PAR API KEY)
# ============================================


@router.get("/usage", response_model=list[UsageAnalyticsResponse])
async def get_usage_analytics(
    start_date: date | None = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    📊 VUE 1 : Usage Analytics - Graphique temporel

    Retourne les métriques quotidiennes (hours watched, total plays)
    Par défaut : 7 derniers jours
    """
    try:
        # Par défaut : 7 derniers jours
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        # Récupérer les analytics quotidiennes
        daily_stats = (
            db.query(DailyAnalytic)
            .filter(and_(DailyAnalytic.date >= start_date, DailyAnalytic.date <= end_date))
            .order_by(DailyAnalytic.date)
            .all()
        )

        return [
            UsageAnalyticsResponse(date=stat.date, hours_watched=stat.hours_watched, total_plays=stat.total_plays)
            for stat in daily_stats
        ]

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des usage analytics : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur"
        ) from e


@router.get("/media", response_model=list[MediaPlaybackAnalyticsItem])
async def get_media_playback_analytics(
    limit: int = Query(50, ge=1, le=100, description="Nombre de résultats"),
    sort_by: Literal["plays", "duration", "last_played"] = Query(
        "last_played", description="Tri par : plays, duration, last_played"
    ),
    order: Literal["asc", "desc"] = Query("desc", description="Ordre : asc ou desc"),
    db: Session = Depends(get_db),
):
    try:
        from collections import defaultdict

        order_fn = desc if order == "desc" else asc

        total_plays_col = func.count(PlaybackSession.id)
        total_watched_col = func.coalesce(func.sum(PlaybackSession.watched_seconds), 0)
        last_played_col = func.max(PlaybackSession.end_time)

        sort_col_map = {
            "plays": total_plays_col,
            "duration": total_watched_col,
            "last_played": last_played_col,
        }
        sort_col = sort_col_map.get(sort_by, total_plays_col)

        rows = (
            db.query(
                PlaybackSession.media_id,
                func.max(PlaybackSession.media_title).label("media_title"),
                func.max(PlaybackSession.media_type).label("media_type"),
                func.max(PlaybackSession.episode_info).label("episode_info"),
                func.max(PlaybackSession.poster_url).label("poster_url"),
                func.max(LibraryItem.title).label("series_name"),
                total_plays_col.label("total_plays"),
                total_watched_col.label("total_watched_seconds"),
                func.sum(case((PlaybackSession.playback_method == PlaybackMethod.DIRECT_PLAY, 1), else_=0)).label(
                    "direct_play_count"
                ),
                func.sum(case((PlaybackSession.playback_method == PlaybackMethod.TRANSCODED, 1), else_=0)).label(
                    "transcoded_count"
                ),
                last_played_col.label("last_played_at"),
            )
            .outerjoin(LibraryItem, PlaybackSession.library_item_id == LibraryItem.id)
            .group_by(PlaybackSession.media_id)
            .order_by(order_fn(sort_col))
            .limit(limit)
            .all()
        )

        # Derive most-used quality per media_id via a second grouped query
        media_ids = [row.media_id for row in rows]
        quality_map: dict[str, str] = {}
        if media_ids:
            quality_rows = (
                db.query(
                    PlaybackSession.media_id,
                    PlaybackSession.video_quality,
                    func.count(PlaybackSession.id).label("cnt"),
                )
                .filter(
                    PlaybackSession.media_id.in_(media_ids),
                    PlaybackSession.status == SessionStatus.STOPPED,
                )
                .group_by(PlaybackSession.media_id, PlaybackSession.video_quality)
                .all()
            )
            quality_counts: dict[str, dict] = defaultdict(dict)
            for qr in quality_rows:
                quality_counts[qr.media_id][qr.video_quality] = qr.cnt
            for mid, counts in quality_counts.items():
                best = max(counts, key=counts.__getitem__)
                quality_map[mid] = best.value if hasattr(best, "value") else str(best)

        results = []
        for row in rows:
            total_secs = row.total_watched_seconds or 0
            hours = total_secs // 3600
            minutes = (total_secs % 3600) // 60
            duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

            direct = row.direct_play_count or 0
            transcoded = row.transcoded_count or 0
            status_str = "Direct" if direct >= transcoded else "Transcoded"

            results.append(
                MediaPlaybackAnalyticsItem(
                    media_title=row.media_title,
                    media_type=row.media_type,
                    episode_info=row.episode_info,
                    series_name=row.series_name,
                    plays=row.total_plays,
                    duration=duration_str,
                    quality=quality_map.get(row.media_id, "Unknown"),
                    status=status_str,
                    poster_url=row.poster_url,
                    last_played_at=row.last_played_at,
                )
            )

        return results

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des media analytics : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur"
        ) from e


@router.get("/sessions/active", response_model=list[ActiveSessionItem])
async def get_active_sessions(db: Session = Depends(get_db)):
    """
    📊 VUE 3 : Sessions actives en temps réel

    Retourne les sessions de lecture en cours
    """
    try:
        sessions = AnalyticsService.get_active_sessions(db)

        return [
            ActiveSessionItem(
                media_title=s.media_title,
                user_name=s.user_name,
                quality_from=s.video_codec_source or "Unknown",
                quality_to=s.video_codec_target or s.video_quality.value,
                progress=s.transcoding_progress,
                speed=s.transcoding_speed or 1.0,
                device_type=s.device_type,
            )
            for s in sessions
        ]

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des sessions actives : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur"
        ) from e


@router.get("/devices", response_model=list[DeviceBreakdownItem])
async def get_device_breakdown(
    period_days: int = Query(7, ge=1, le=365, description="Période en jours"),
    db: Session = Depends(get_db),
):
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        device_stats = (
            db.query(PlaybackSession.device_type, func.count(PlaybackSession.id).label("session_count"))
            .filter(
                and_(
                    func.date(PlaybackSession.start_time) >= start_date,
                    func.date(PlaybackSession.start_time) <= end_date,
                )
            )
            .group_by(PlaybackSession.device_type)
            .all()
        )

        # Calculer le total pour les pourcentages
        total_sessions = sum([stat.session_count for stat in device_stats])

        if total_sessions == 0:
            return []

        # Formater les résultats
        return [
            DeviceBreakdownItem(
                device_type=stat.device_type,
                session_count=stat.session_count,
                percentage=round((stat.session_count / total_sessions) * 100, 1),
            )
            for stat in device_stats
        ]

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération du device breakdown : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur"
        ) from e


@router.get("/server-metrics", response_model=ServerPerformanceResponse | None)
async def get_server_metrics(db: Session = Depends(get_db)):
    try:
        # Récupérer la dernière métrique serveur
        latest_metric = db.query(ServerMetric).order_by(desc(ServerMetric.recorded_at)).first()

        if not latest_metric:
            # Si aucune métrique, retourner des valeurs par défaut
            return None

        # Récupérer les sessions actives
        active_sessions = AnalyticsService.get_active_sessions(db)

        # Formater les sessions actives
        active_session_items = [
            ActiveSessionItem(
                media_title=s.media_title,
                user_name=s.user_name,
                quality_from=s.video_codec_source or "Unknown",
                quality_to=s.video_codec_target or s.video_quality.value,
                progress=s.transcoding_progress,
                speed=s.transcoding_speed or 1.0,
                device_type=s.device_type,
            )
            for s in active_sessions
        ]

        return ServerPerformanceResponse(
            cpu_usage_percent=latest_metric.cpu_usage_percent or 0.0,
            cpu_status=latest_metric.cpu_status or "success",
            memory_usage_gb=latest_metric.memory_usage_gb or 0.0,
            memory_total_gb=latest_metric.memory_total_gb or 16.0,
            memory_status=latest_metric.memory_status or "success",
            storage_used_tb=latest_metric.storage_used_tb or 0.0,
            storage_total_tb=latest_metric.storage_total_tb or 10.0,
            storage_status=latest_metric.storage_status or "success",
            bandwidth_mbps=latest_metric.bandwidth_mbps or 0.0,
            bandwidth_status=latest_metric.bandwidth_status or "error",
            active_sessions=active_session_items,
            active_transcoding_count=latest_metric.active_transcoding_count,
        )

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération des server metrics : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur"
        ) from e


@router.get("/users", response_model=list[UserLeaderboardItem])
async def get_user_leaderboard(
    limit: int = Query(10, ge=1, le=50, description="Number of users to return"),
    db: Session = Depends(get_db),
):
    """
    📊 User Leaderboard — ranked by total hours watched.
    Derived entirely from PlaybackSession history.
    """
    try:
        from collections import defaultdict

        rows = (
            db.query(
                PlaybackSession.user_name,
                func.count(PlaybackSession.id).label("total_plays"),
                func.coalesce(func.sum(PlaybackSession.watched_seconds), 0).label("total_seconds"),
                func.sum(case((PlaybackSession.media_type == MediaType.MOVIE, 1), else_=0)).label("movies_count"),
                func.sum(case((PlaybackSession.media_type == MediaType.TV, 1), else_=0)).label("episodes_count"),
                func.max(PlaybackSession.start_time).label("last_seen"),
            )
            .filter(PlaybackSession.is_active.is_(False))
            .group_by(PlaybackSession.user_name)
            .order_by(desc(func.coalesce(func.sum(PlaybackSession.watched_seconds), 0)))
            .limit(limit)
            .all()
        )

        # Resolve favorite device per user via a second query
        user_names = [r.user_name for r in rows]
        device_map: dict[str, str] = {}
        if user_names:
            device_rows = (
                db.query(
                    PlaybackSession.user_name,
                    PlaybackSession.device_type,
                    func.count(PlaybackSession.id).label("cnt"),
                )
                .filter(PlaybackSession.user_name.in_(user_names))
                .group_by(PlaybackSession.user_name, PlaybackSession.device_type)
                .all()
            )
            counts: dict[str, dict] = defaultdict(dict)
            for dr in device_rows:
                counts[dr.user_name][dr.device_type] = dr.cnt
            for uname, dcounts in counts.items():
                best = max(dcounts, key=dcounts.__getitem__)
                device_map[uname] = best.value if hasattr(best, "value") else str(best)

        return [
            UserLeaderboardItem(
                user_name=row.user_name,
                total_plays=row.total_plays,
                hours_watched=round((row.total_seconds or 0) / 3600, 1),
                movies_count=row.movies_count or 0,
                episodes_count=row.episodes_count or 0,
                favorite_device=device_map.get(row.user_name),
                last_seen=row.last_seen,
            )
            for row in rows
        ]

    except Exception as e:
        logger.error(f"❌ Error fetching user leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/sessions", response_model=list[PlaybackSessionResponse])
async def get_sessions(
    start: date | None = Query(default=None, description="Start date YYYY-MM-DD"),
    end: date | None = Query(default=None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Récupérer les sessions de lecture pour une plage de dates (dédupliquées par épisode/spectateur/jour)"""
    today = date.today()
    start_date = start or (today - timedelta(days=30))
    end_date = end or today

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    sessions = (
        db.query(PlaybackSession)
        .filter(
            PlaybackSession.start_time >= start_dt,
            PlaybackSession.start_time <= end_dt,
            PlaybackSession.is_active.is_(False),
        )
        .order_by(PlaybackSession.start_time.desc())
        .all()
    )

    # Deduplicate: keep the session with the most watched_seconds per
    # (media_title, episode_info, user_name, calendar_day)
    seen: dict[tuple, PlaybackSession] = {}
    for s in sessions:
        key = (s.media_title, s.episode_info, s.user_name, s.start_time.date())
        existing = seen.get(key)
        if existing is None or (s.watched_seconds or 0) > (existing.watched_seconds or 0):
            seen[key] = s

    return list(seen.values())


@router.get("/genres")
async def get_genre_stats(db: Session = Depends(get_db)):
    """
    🎭 Genre statistics — top 10 genres for movies and TV shows separately.
    Aggregated from the genres field populated during Sonarr/Radarr sync.
    """
    from collections import Counter

    from app.api.schemas import GenreStatItem, GenreStatsResponse

    rows = db.query(LibraryItem.media_type, LibraryItem.genres).all()

    movie_counter: Counter = Counter()
    tv_counter: Counter = Counter()

    for media_type, genres in rows:
        if not genres:
            continue
        for genre in genres:
            if genre:
                if media_type == MediaType.MOVIE:
                    movie_counter[genre] += 1
                else:
                    tv_counter[genre] += 1

    return GenreStatsResponse(
        movies=[GenreStatItem(genre=g, count=c) for g, c in movie_counter.most_common(10)],
        tv=[GenreStatItem(genre=g, count=c) for g, c in tv_counter.most_common(10)],
    )


@router.get("/users/{username}", response_model=None)
async def get_user_detail(username: str, db: Session = Depends(get_db)):
    """
    👤 Full per-user analytics derived from PlaybackSession history.
    Returns overview, genres (watch-based), devices, playback methods,
    top titles, recent sessions and 30-day activity.
    """
    from collections import Counter, defaultdict
    from datetime import timezone

    from app.api.schemas import (
        UserActivityDay,
        UserDetailOverview,
        UserDetailResponse,
        UserDeviceItem,
        UserGenreItem,
        UserPlaybackMethods,
        UserRecentSession,
        UserTopTitle,
    )

    sessions = (
        db.query(PlaybackSession)
        .filter(PlaybackSession.user_name == username, PlaybackSession.is_active.is_(False))
        .order_by(PlaybackSession.start_time.desc())
        .all()
    )

    if not sessions:
        raise HTTPException(status_code=404, detail="User not found or no playback history")

    total_plays = len(sessions)
    total_seconds = sum(s.watched_seconds or 0 for s in sessions)
    movies_count = sum(1 for s in sessions if s.media_type == MediaType.MOVIE)
    episodes_count = sum(1 for s in sessions if s.media_type == MediaType.TV)
    last_seen = max((s.start_time for s in sessions), default=None)

    # --- Favorite device ---
    device_counter: Counter = Counter()
    for s in sessions:
        if s.device_type:
            key = s.device_type.value if hasattr(s.device_type, "value") else str(s.device_type)
            device_counter[key] += 1

    favorite_device = device_counter.most_common(1)[0][0] if device_counter else None

    # --- Device breakdown ---
    devices = [
        {"device_type": dt, "count": cnt, "percentage": round(cnt / total_plays * 100, 1)}
        for dt, cnt in device_counter.most_common()
    ]

    # --- Playback methods ---
    direct = sum(
        1
        for s in sessions
        if s.playback_method
        and (
            s.playback_method == PlaybackMethod.DIRECT_PLAY
            or (hasattr(s.playback_method, "value") and "direct" in s.playback_method.value.lower())
        )
    )
    transcoded = total_plays - direct

    # --- Genre breakdown (watch-based via library_item join) ---
    library_item_ids = list({s.library_item_id for s in sessions if s.library_item_id})
    genre_counter: Counter = Counter()
    if library_item_ids:
        items = db.query(LibraryItem.id, LibraryItem.genres).filter(LibraryItem.id.in_(library_item_ids)).all()
        genres_by_id = {item.id: item.genres or [] for item in items}
        for s in sessions:
            if s.library_item_id:
                for genre in genres_by_id.get(s.library_item_id, []):
                    if genre:
                        genre_counter[genre] += 1

    genres = [{"genre": g, "count": c} for g, c in genre_counter.most_common(10)]

    # --- Top titles ---
    title_map: dict[str, dict] = defaultdict(lambda: {"plays": 0, "media_type": "", "poster_url": None})
    for s in sessions:
        entry = title_map[s.media_title]
        entry["plays"] += 1
        entry["media_type"] = s.media_type.value if hasattr(s.media_type, "value") else str(s.media_type)
        if s.poster_url and not entry["poster_url"]:
            entry["poster_url"] = s.poster_url

    top_titles = sorted(
        [{"title": k, **v} for k, v in title_map.items()],
        key=lambda x: x["plays"],
        reverse=True,
    )[:10]

    # --- Recent sessions (last 20) ---
    recent_sessions = [
        {
            "media_title": s.media_title,
            "media_type": s.media_type.value if hasattr(s.media_type, "value") else str(s.media_type),
            "episode_info": s.episode_info,
            "watched_seconds": s.watched_seconds or 0,
            "start_time": s.start_time.isoformat(),
            "device_type": s.device_type.value if hasattr(s.device_type, "value") else str(s.device_type or ""),
            "playback_method": s.playback_method.value
            if hasattr(s.playback_method, "value")
            else str(s.playback_method or ""),
        }
        for s in sessions[:20]
    ]

    # --- 30-day activity ---
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()
    day_counter: Counter = Counter()
    cutoff = today - timedelta(days=29)
    for s in sessions:
        day = s.start_time.date()
        if day >= cutoff:
            day_counter[day] += 1

    activity_by_day = [
        {"date": (today - timedelta(days=i)).isoformat(), "plays": day_counter.get(today - timedelta(days=i), 0)}
        for i in range(29, -1, -1)
    ]

    return UserDetailResponse(
        user_name=username,
        overview=UserDetailOverview(
            total_plays=total_plays,
            hours_watched=round(total_seconds / 3600, 1),
            movies_count=movies_count,
            episodes_count=episodes_count,
            last_seen=last_seen,
            favorite_device=favorite_device,
        ),
        genres=[UserGenreItem(**g) for g in genres],
        devices=[UserDeviceItem(**d) for d in devices],
        playback_methods=UserPlaybackMethods(direct=direct, transcoded=transcoded),
        top_titles=[UserTopTitle(**t) for t in top_titles],
        recent_sessions=[UserRecentSession(**r) for r in recent_sessions],
        activity_by_day=[UserActivityDay(**a) for a in activity_by_day],
    )
