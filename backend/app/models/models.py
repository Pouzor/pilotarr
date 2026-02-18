import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base
from app.models.enums import (
    CalendarStatus,
    DeviceType,
    MediaType,
    PlaybackMethod,
    RequestPriority,
    RequestStatus,
    ServiceType,
    SessionStatus,
    StatType,
    SyncStatus,
    VideoQuality,
)


def generate_uuid():
    """Génère un UUID au format string"""
    return str(uuid.uuid4())


# Table 1: Service Configurations
class ServiceConfiguration(Base):
    __tablename__ = "service_configurations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_name = Column(String(50), unique=True, nullable=False, index=True)
    url = Column(Text, nullable=False)
    api_key = Column(Text, nullable=True)
    port = Column(Integer)
    username = Column(Text, nullable=True)
    password = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    last_tested_at = Column(DateTime(timezone=True))
    test_status = Column(Text)
    test_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Table 2: Dashboard Statistics
class DashboardStatistic(Base):
    __tablename__ = "dashboard_statistics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    stat_type = Column(SQLEnum(StatType), unique=True, nullable=False, index=True)
    total_count = Column(Integer, default=0)
    details = Column(JSON, default={})
    last_synced = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Table 3: Sync Metadata
class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_name = Column(SQLEnum(ServiceType), nullable=False, index=True)
    last_sync_time = Column(DateTime(timezone=True))
    sync_status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING, index=True)
    error_message = Column(Text)
    next_sync_time = Column(DateTime(timezone=True), index=True)
    sync_duration_ms = Column(Integer)
    records_synced = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Table 4: Library Items
class LibraryItem(Base):
    __tablename__ = "library_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False, index=True)
    image_url = Column(Text, nullable=False)
    image_alt = Column(Text, nullable=False)
    quality = Column(Text, nullable=False)
    rating = Column(Text)
    description = Column(Text)
    added_date = Column(DateTime(timezone=True), nullable=True)
    size = Column(Text, nullable=False)
    torrent_hash = Column(String(255), nullable=True, index=True)
    torrent_info = Column(JSON, nullable=True)
    nb_media = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    torrents = relationship("LibraryItemTorrent", back_populates="library_item", lazy="select")
    seasons = relationship("Season", back_populates="library_item", lazy="select")


# Table 4b: Library Item Torrents (junction table for multi-torrent support)
class LibraryItemTorrent(Base):
    __tablename__ = "library_item_torrents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    library_item_id = Column(String(36), ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, index=True)
    torrent_hash = Column(String(255), nullable=False, index=True)
    episode_id = Column(Integer, nullable=True)
    season_number = Column(Integer, nullable=True)
    is_season_pack = Column(Boolean, default=False)
    torrent_info = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    library_item = relationship("LibraryItem", back_populates="torrents")

    __table_args__ = (UniqueConstraint("library_item_id", "torrent_hash", name="uq_item_torrent_hash"),)


# Table 4c: Seasons (TV Show seasons)
class Season(Base):
    __tablename__ = "seasons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    library_item_id = Column(String(36), ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sonarr identifiers
    sonarr_series_id = Column(Integer, nullable=False, index=True)
    season_number = Column(Integer, nullable=False, index=True)

    # Status & Statistics (from Sonarr)
    monitored = Column(Boolean, default=True, index=True)
    episode_count = Column(Integer, default=0)
    episode_file_count = Column(Integer, default=0)  # Downloaded episodes
    total_episode_count = Column(Integer, default=0)
    size_on_disk = Column(BigInteger, default=0)
    statistics = Column(JSON, nullable=True)  # Full Sonarr statistics

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    library_item = relationship("LibraryItem", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season", cascade="all, delete-orphan", lazy="select")

    __table_args__ = (
        UniqueConstraint("library_item_id", "season_number", name="uq_item_season_number"),
        Index("idx_season_series_number", "sonarr_series_id", "season_number"),
    )


# Table 4d: Episodes (TV Show episodes)
class Episode(Base):
    __tablename__ = "episodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    season_id = Column(String(36), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True)
    library_item_id = Column(String(36), ForeignKey("library_items.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sonarr identifiers
    sonarr_episode_id = Column(Integer, unique=True, nullable=False, index=True)
    sonarr_series_id = Column(Integer, nullable=False, index=True)
    sonarr_episode_file_id = Column(Integer, nullable=True, index=True)

    # Episode identifiers
    season_number = Column(Integer, nullable=False, index=True)  # Denormalized
    episode_number = Column(Integer, nullable=False, index=True)
    absolute_episode_number = Column(Integer, nullable=True)

    # Metadata
    title = Column(Text, nullable=True)
    overview = Column(Text, nullable=True)
    air_date = Column(Date, nullable=True, index=True)
    air_date_utc = Column(DateTime(timezone=True), nullable=True)

    # Status flags
    monitored = Column(Boolean, default=True, index=True)
    has_file = Column(Boolean, default=False, index=True)
    downloaded = Column(Boolean, default=False, index=True)

    # File details (when downloaded)
    file_size = Column(BigInteger, nullable=True)
    quality_profile = Column(String(100), nullable=True)
    relative_path = Column(Text, nullable=True)
    episode_file_info = Column(JSON, nullable=True)  # Full episodeFile object

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    season = relationship("Season", back_populates="episodes")
    library_item = relationship("LibraryItem")

    __table_args__ = (
        UniqueConstraint("sonarr_series_id", "season_number", "episode_number", name="uq_series_season_episode"),
        Index("idx_episode_air_date", "air_date", "monitored"),
        Index("idx_episode_series_season", "sonarr_series_id", "season_number"),
    )


# Table 5: Calendar Events
class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(Text, nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False)
    release_date = Column(Date, nullable=False, index=True)
    episode = Column(Text)
    image_url = Column(Text, nullable=False)
    image_alt = Column(Text, nullable=False)
    status = Column(SQLEnum(CalendarStatus), nullable=False, default=CalendarStatus.MONITORED, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Table 6: Jellyseerr Requests
class JellyseerrRequest(Base):
    __tablename__ = "jellyseerr_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    jellyseerr_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False)
    year = Column(Integer, nullable=False)
    image_url = Column(Text, nullable=False)
    image_alt = Column(Text, nullable=False)
    status = Column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING, index=True)
    priority = Column(SQLEnum(RequestPriority), nullable=False, default=RequestPriority.MEDIUM, index=True)
    requested_by = Column(Text, nullable=False)
    requested_by_avatar = Column(Text, nullable=True)
    requested_by_user_id = Column(Integer, nullable=True)
    requested_date = Column(Text, nullable=False)
    quality = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Table 7: Playback Sessions
class PlaybackSession(Base):
    """Sessions de lecture des médias"""

    __tablename__ = "playback_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Informations du média
    media_id = Column(String(255), nullable=False, index=True)  # ID du média dans Jellyfin
    media_title = Column(Text, nullable=False)
    media_type = Column(SQLEnum(MediaType), nullable=False, index=True)
    media_year = Column(Integer)
    episode_info = Column(Text)  # Ex: "S04E09" pour les séries
    poster_url = Column(Text)
    library_item_id = Column(String(36), nullable=True, index=True)

    # Informations utilisateur
    user_id = Column(String(255), nullable=False, index=True)  # ID utilisateur Jellyfin
    user_name = Column(Text, nullable=False)

    # Informations de la session
    device_type = Column(SQLEnum(DeviceType), nullable=False, default=DeviceType.OTHER, index=True)
    device_name = Column(Text)  # Ex: "Chrome on Windows", "iPhone 14"
    client_name = Column(Text)  # Ex: "Jellyfin Web", "Jellyfin Mobile"

    # Qualité et lecture
    video_quality = Column(SQLEnum(VideoQuality), nullable=False, default=VideoQuality.UNKNOWN)
    playback_method = Column(SQLEnum(PlaybackMethod), nullable=False, default=PlaybackMethod.DIRECT_PLAY, index=True)

    # Transcodage
    transcoding_progress = Column(Integer, default=0)  # 0-100
    transcoding_speed = Column(Float)  # Ex: 1.2x
    video_codec_source = Column(String(50))  # Ex: "hevc", "h264"
    video_codec_target = Column(String(50))  # Ex: "h264"

    # Timestamps
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Durée et progression
    duration_seconds = Column(Integer)  # Durée totale du média
    watched_seconds = Column(Integer, default=0)  # Durée réellement regardée

    # Statut
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Indexes composites pour les requêtes d'analytics
    __table_args__ = (
        Index("idx_session_active_start", "is_active", "start_time"),
        Index("idx_session_media_start", "media_id", "start_time"),
        Index("idx_session_user_start", "user_id", "start_time"),
        Index("idx_session_device_start", "device_type", "start_time"),
    )


# Table 8: Device Statistics (Agrégation par type d'appareil)
class DeviceStatistic(Base):
    """Statistiques agrégées par type d'appareil sur une période"""

    __tablename__ = "device_statistics"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Type d'appareil
    device_type = Column(SQLEnum(DeviceType), nullable=False, index=True)

    # Période
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)

    # Statistiques
    session_count = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)

    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Contrainte d'unicité : un seul enregistrement par device_type + période
    __table_args__ = (Index("idx_device_period", "device_type", "period_start", "period_end", unique=True),)


# Table 10: Daily Analytics (Agrégation quotidienne)
class DailyAnalytic(Base):
    """Statistiques agrégées par jour pour les graphiques temporels"""

    __tablename__ = "daily_analytics"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Date
    date = Column(Date, unique=True, nullable=False, index=True)

    # Métriques globales
    total_plays = Column(Integer, default=0)
    hours_watched = Column(Float, default=0.0)  # En heures
    unique_users = Column(Integer, default=0)
    unique_media = Column(Integer, default=0)

    # Par type de média
    movies_played = Column(Integer, default=0)
    tv_episodes_played = Column(Integer, default=0)

    # Par méthode de lecture
    direct_play_count = Column(Integer, default=0)
    transcoded_count = Column(Integer, default=0)

    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Table 11: Server Metrics (Métriques serveur en temps réel)
class ServerMetric(Base):
    """Métriques du serveur (CPU, RAM, etc.) - Snapshots réguliers"""

    __tablename__ = "server_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Métriques système
    cpu_usage_percent = Column(Float)
    memory_usage_gb = Column(Float)
    memory_total_gb = Column(Float)
    storage_used_tb = Column(Float)
    storage_total_tb = Column(Float)
    bandwidth_mbps = Column(Float)

    # Statuts
    cpu_status = Column(String(20))  # "success", "warning", "error"
    memory_status = Column(String(20))
    bandwidth_status = Column(String(20))
    storage_status = Column(String(20))

    # Sessions actives
    active_sessions_count = Column(Integer, default=0)
    active_transcoding_count = Column(Integer, default=0)

    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
