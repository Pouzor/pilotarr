"""
Service de gestion des analytics et des sessions de lecture
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.enums import DeviceType, MediaType, PlaybackMethod, SessionStatus, VideoQuality
from app.models.models import DailyAnalytic, DeviceStatistic, PlaybackSession

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service pour gérer les analytics de lecture"""

    @staticmethod
    def map_device_type(client_name: str, device_name: str) -> DeviceType:
        """Détermine le type d'appareil basé sur le client et le device name"""
        client_lower = client_name.lower() if client_name else ""
        device_lower = device_name.lower() if device_name else ""

        # Web browsers
        if any(browser in client_lower for browser in ["chrome", "firefox", "safari", "edge", "web"]):
            return DeviceType.WEB_BROWSER

        # Mobile apps
        if any(
            mobile in client_lower or mobile in device_lower
            for mobile in ["android", "ios", "iphone", "ipad", "mobile"]
        ):
            return DeviceType.MOBILE_APP

        # Streaming devices (avant Smart TV pour éviter les doublons)
        if any(stream in device_lower for stream in ["chromecast", "roku", "fire stick", "firestick"]):
            return DeviceType.STREAMING_DEVICE

        # Smart TVs
        if any(tv in device_lower for tv in ["tv", "fire tv", "apple tv"]):
            return DeviceType.SMART_TV

        # Desktop apps
        if any(desktop in client_lower for desktop in ["windows", "macos", "linux", "desktop"]):
            return DeviceType.DESKTOP_APP

        # Game consoles
        if any(console in device_lower for console in ["xbox", "playstation", "ps4", "ps5"]):
            return DeviceType.GAME_CONSOLE

        return DeviceType.OTHER

    @staticmethod
    def map_video_quality(quality_str: str | None) -> VideoQuality:
        """Convertit une chaîne de qualité en enum VideoQuality"""
        if not quality_str:
            return VideoQuality.UNKNOWN

        quality_lower = quality_str.lower()

        if "4k" in quality_lower and "hdr" in quality_lower:
            return VideoQuality.FOUR_K_HDR
        elif "4k" in quality_lower or "2160p" in quality_lower:
            return VideoQuality.FOUR_K
        elif "1080p" in quality_lower or "full hd" in quality_lower:
            return VideoQuality.FULL_HD
        elif "720p" in quality_lower or "hd" in quality_lower:
            return VideoQuality.HD
        elif "480p" in quality_lower:
            return VideoQuality.SD
        elif "360p" in quality_lower:
            return VideoQuality.LOW

        return VideoQuality.UNKNOWN

    @staticmethod
    def map_playback_method(is_transcoding: bool, is_direct_playing: bool) -> PlaybackMethod:
        """Détermine la méthode de lecture"""
        if is_transcoding:
            return PlaybackMethod.TRANSCODED
        elif is_direct_playing:
            return PlaybackMethod.DIRECT_PLAY
        else:
            return PlaybackMethod.DIRECT_STREAM

    @staticmethod
    def start_session(db: Session, session_data: dict[str, Any]) -> PlaybackSession:
        """
        Démarre une nouvelle session de lecture

        Args:
            db: Session SQLAlchemy
            session_data: Données de la session depuis le webhook
        """
        try:
            # Mapper les types
            device_type = AnalyticsService.map_device_type(
                session_data.get("client_name", ""), session_data.get("device_name", "")
            )

            video_quality = AnalyticsService.map_video_quality(session_data.get("video_quality"))

            playback_method = AnalyticsService.map_playback_method(
                session_data.get("is_transcoding", False), session_data.get("is_direct_playing", True)
            )

            # Créer la session
            session = PlaybackSession(
                media_id=session_data.get("media_id"),
                media_title=session_data.get("media_title"),
                media_type=MediaType(session_data.get("media_type", "movie")),
                media_year=session_data.get("media_year"),
                episode_info=session_data.get("episode_info"),
                poster_url=session_data.get("poster_url"),
                library_item_id=session_data.get("library_item_id"),
                user_id=session_data.get("user_id"),
                user_name=session_data.get("user_name"),
                device_type=device_type,
                device_name=session_data.get("device_name"),
                client_name=session_data.get("client_name"),
                video_quality=video_quality,
                playback_method=playback_method,
                transcoding_progress=session_data.get("transcoding_progress", 0),
                transcoding_speed=session_data.get("transcoding_speed"),
                video_codec_source=session_data.get("video_codec_source"),
                video_codec_target=session_data.get("video_codec_target"),
                start_time=datetime.now(UTC),
                duration_seconds=session_data.get("duration_seconds"),
                watched_seconds=0,
                status=SessionStatus.ACTIVE,
                is_active=True,
            )

            db.add(session)
            db.commit()
            db.refresh(session)

            logger.info(f"✅ Session créée : {session.id} - {session.media_title}")
            return session

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de la création de session : {e}")
            raise

    @staticmethod
    def stop_session(
        db: Session, media_id: str, user_id: str, watched_seconds: int | None = None
    ) -> PlaybackSession | None:
        """
        Arrête une session de lecture active

        Args:
            db: Session SQLAlchemy
            media_id: ID du média
            user_id: ID de l'utilisateur
            watched_seconds: Durée regardée (optionnel)
        """
        try:
            # Trouver la session active
            session = (
                db.query(PlaybackSession)
                .filter(
                    PlaybackSession.media_id == media_id,
                    PlaybackSession.user_id == user_id,
                    PlaybackSession.is_active,
                )
                .order_by(desc(PlaybackSession.start_time))
                .first()
            )

            if not session:
                logger.warning(f"⚠️  Aucune session active trouvée pour media_id={media_id}, user_id={user_id}")
                return None

            # Mettre à jour la session
            session.end_time = datetime.now(UTC)
            session.status = SessionStatus.STOPPED
            session.is_active = False

            if watched_seconds and watched_seconds > 0:
                session.watched_seconds = watched_seconds
            else:
                # Fallback : calculer la durée à partir du temps écoulé
                elapsed = int((session.end_time - session.start_time).total_seconds())
                # Plafonner au maximum à la durée du média si connue
                if session.duration_seconds and elapsed > session.duration_seconds:
                    elapsed = session.duration_seconds
                session.watched_seconds = elapsed

            db.commit()
            db.refresh(session)

            logger.info(f"✅ Session arrêtée : {session.id} - {session.media_title}")

            # Mettre à jour les statistiques
            AnalyticsService.update_daily_analytics(db, session)

            return session

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de l'arrêt de session : {e}")
            raise

    @staticmethod
    def pause_session(db: Session, media_id: str, user_id: str) -> PlaybackSession | None:
        """Met en pause une session active"""
        try:
            session = (
                db.query(PlaybackSession)
                .filter(
                    PlaybackSession.media_id == media_id,
                    PlaybackSession.user_id == user_id,
                    PlaybackSession.is_active,
                )
                .order_by(desc(PlaybackSession.start_time))
                .first()
            )

            if session:
                session.status = SessionStatus.PAUSED
                db.commit()
                db.refresh(session)
                logger.info(f"⏸️  Session en pause : {session.id}")

            return session

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de la pause : {e}")
            raise

    @staticmethod
    def resume_session(db: Session, media_id: str, user_id: str) -> PlaybackSession | None:
        """Reprend une session en pause"""
        try:
            session = (
                db.query(PlaybackSession)
                .filter(
                    PlaybackSession.media_id == media_id,
                    PlaybackSession.user_id == user_id,
                    PlaybackSession.is_active,
                )
                .order_by(desc(PlaybackSession.start_time))
                .first()
            )

            if session:
                session.status = SessionStatus.ACTIVE
                db.commit()
                db.refresh(session)
                logger.info(f"▶️  Session reprise : {session.id}")

            return session

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de la reprise : {e}")
            raise

    @staticmethod
    def update_daily_analytics(db: Session, session: PlaybackSession):
        """Met à jour les analytics quotidiennes"""
        try:
            session_date = session.start_time.date()

            # Récupérer ou créer les analytics du jour
            daily_stat = db.query(DailyAnalytic).filter(DailyAnalytic.date == session_date).first()

            if not daily_stat:
                daily_stat = DailyAnalytic(
                    date=session_date,
                    total_plays=0,
                    hours_watched=0.0,
                    unique_users=0,
                    unique_media=0,
                    movies_played=0,
                    tv_episodes_played=0,
                    direct_play_count=0,
                    transcoded_count=0,
                )
                db.add(daily_stat)

            # Mettre à jour les compteurs
            daily_stat.total_plays += 1
            daily_stat.hours_watched += session.watched_seconds / 3600.0  # Convertir en heures

            if session.media_type == MediaType.MOVIE:
                daily_stat.movies_played += 1
            elif session.media_type == MediaType.TV:
                daily_stat.tv_episodes_played += 1

            if session.playback_method == PlaybackMethod.DIRECT_PLAY:
                daily_stat.direct_play_count += 1
            elif session.playback_method == PlaybackMethod.TRANSCODED:
                daily_stat.transcoded_count += 1

            # Calculer les utilisateurs et médias uniques du jour
            unique_users = (
                db.query(func.count(func.distinct(PlaybackSession.user_id)))
                .filter(func.date(PlaybackSession.start_time) == session_date)
                .scalar()
            )
            daily_stat.unique_users = unique_users

            unique_media = (
                db.query(func.count(func.distinct(PlaybackSession.media_id)))
                .filter(func.date(PlaybackSession.start_time) == session_date)
                .scalar()
            )
            daily_stat.unique_media = unique_media

            db.commit()
            logger.info(f"📅 Analytics quotidiennes mises à jour : {session_date}")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de la mise à jour des analytics quotidiennes : {e}")

    @staticmethod
    def get_active_sessions(db: Session) -> list[PlaybackSession]:
        """Récupère toutes les sessions actives"""
        return (
            db.query(PlaybackSession).filter(PlaybackSession.is_active).order_by(desc(PlaybackSession.start_time)).all()
        )

    @staticmethod
    def cleanup_orphan_sessions(db: Session, timeout_hours: int = 24):
        """
        Nettoie les sessions orphelines (actives depuis trop longtemps)

        Args:
            db: Session DB
            timeout_hours: Nombre d'heures après lesquelles une session est considérée orpheline
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=timeout_hours)

            # Trouver les sessions actives trop anciennes
            orphan_sessions = (
                db.query(PlaybackSession)
                .filter(PlaybackSession.is_active, PlaybackSession.start_time < cutoff_time)
                .all()
            )

            count = 0
            for session in orphan_sessions:
                session.is_active = False
                session.status = SessionStatus.STOPPED
                session.end_time = datetime.now(UTC)

                # Ne pas estimer watched_seconds pour les sessions orphelines
                # pour éviter de corrompre les données analytics

                count += 1

            db.commit()

            if count > 0:
                logger.info(f"🧹 {count} sessions orphelines nettoyées")

            return count

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors du nettoyage des sessions orphelines : {e}")
            return 0

    @staticmethod
    def update_device_statistics(db: Session, target_date: date | None = None):
        """
        Met à jour les statistiques par appareil pour une date donnée

        Args:
            db: Session DB
            target_date: Date cible (par défaut : hier)
        """
        try:
            if not target_date:
                target_date = (datetime.now(UTC) - timedelta(days=1)).date()

            # Pour chaque type d'appareil
            for device_type in DeviceType:
                # Compter les sessions
                sessions = (
                    db.query(PlaybackSession)
                    .filter(
                        func.date(PlaybackSession.start_time) == target_date, PlaybackSession.device_type == device_type
                    )
                    .all()
                )

                if not sessions:
                    continue

                session_count = len(sessions)
                total_duration = sum([s.watched_seconds for s in sessions])
                unique_users = len(set([s.user_id for s in sessions]))

                # Vérifier si l'enregistrement existe
                device_stat = (
                    db.query(DeviceStatistic)
                    .filter(
                        DeviceStatistic.device_type == device_type,
                        DeviceStatistic.period_start == target_date,
                        DeviceStatistic.period_end == target_date,
                    )
                    .first()
                )

                if device_stat:
                    # Mettre à jour
                    device_stat.session_count = session_count
                    device_stat.total_duration_seconds = total_duration
                    device_stat.unique_users = unique_users
                else:
                    # Créer
                    device_stat = DeviceStatistic(
                        device_type=device_type,
                        period_start=target_date,
                        period_end=target_date,
                        session_count=session_count,
                        total_duration_seconds=total_duration,
                        unique_users=unique_users,
                    )
                    db.add(device_stat)

            db.commit()
            logger.info(f"📊 Statistiques par appareil mises à jour pour {target_date}")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Erreur lors de la mise à jour des device statistics : {e}")
