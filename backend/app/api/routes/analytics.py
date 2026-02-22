"""
Routes API pour les analytics et webhooks
"""

import hmac
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
)
from app.core.config import settings
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
        # Vérifier le secret webhook si configuré
        webhook_secret = settings.WEBHOOK_SECRET
        if webhook_secret:
            request_secret = request.headers.get("X-Webhook-Secret", "")
            if not hmac.compare_digest(request_secret, webhook_secret):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Secret webhook invalide")

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
            jellyfin_url = jellyfin_service.url.rstrip("/") if jellyfin_service else None
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
