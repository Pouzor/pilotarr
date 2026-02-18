from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

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


class ServiceConfigurationBase(BaseModel):
    service_name: ServiceType
    url: str
    api_key: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool = True

    @field_validator("api_key", "username", "password")
    @classmethod
    def validate_credentials(cls, v, info):
        """Valide que soit api_key soit username/password est fourni"""
        return v


class ServiceConfigurationCreate(ServiceConfigurationBase):
    """Schéma pour créer un service"""

    @field_validator("service_name")
    @classmethod
    def validate_service_credentials(cls, v, info):
        """Valide les credentials selon le type de service"""
        data = info.data
        service_name = v

        # Services qui utilisent API key
        if service_name in [ServiceType.RADARR, ServiceType.SONARR, ServiceType.JELLYFIN, ServiceType.JELLYSEERR]:
            if not data.get("api_key"):
                raise ValueError(f"{service_name.value} needs api_key")

        # Services qui utilisent username/password
        elif service_name == ServiceType.QBITTORRENT:
            if not data.get("username") or not data.get("password"):
                raise ValueError("qBittorrent needs username and password")

        return v


class ServiceConfigurationUpdate(BaseModel):
    url: str | None = None
    api_key: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None


class ServiceConfigurationResponse(ServiceConfigurationBase):
    id: str
    last_tested_at: datetime | None = None
    test_status: str | None = None
    test_message: str | None = None
    created_at: datetime
    updated_at: datetime

    # Ne pas exposer le password dans les réponses
    password: str | None = Field(None, exclude=True)

    class Config:
        from_attributes = True


# Dashboard Statistics Schemas
class DashboardStatisticResponse(BaseModel):
    id: str
    stat_type: StatType
    total_count: int
    details: dict[str, Any]
    last_synced: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Monitoring Schemas
class MonitoringSeasonInfo(BaseModel):
    number: int
    episodes: int
    monitored: int
    available: int
    is_monitored: bool


class MonitoringItemResponse(BaseModel):
    id: str
    title: str
    year: int
    service: str
    monitoring_status: str
    availability_status: str
    quality_profile: str
    last_updated: datetime
    file_size: str
    image_url: str
    seasons: list[MonitoringSeasonInfo] = []
    download_history: list = []


# Season & Episode Schemas
class SeasonResponse(BaseModel):
    id: str
    season_number: int
    monitored: bool
    episode_count: int
    episode_file_count: int
    size_on_disk: int

    class Config:
        from_attributes = True


class EpisodeResponse(BaseModel):
    id: str
    season_number: int
    episode_number: int
    title: str | None = None
    overview: str | None = None
    air_date: date | None = None
    monitored: bool
    has_file: bool
    downloaded: bool
    file_size: int | None = None
    quality_profile: str | None = None

    class Config:
        from_attributes = True


class EpisodeDetailResponse(BaseModel):
    episode_number: int
    title: str | None = None
    air_date: date | None = None
    monitored: bool
    has_file: bool
    download_status: str  # "downloaded" | "missing"
    file_size_str: str | None = None  # e.g. "2.1 GB"
    quality_profile: str | None = None

    class Config:
        from_attributes = True


class SeasonWithEpisodesResponse(BaseModel):
    season_number: int
    is_monitored: bool
    episode_count: int
    episode_file_count: int
    total_episode_count: int
    episodes: list[EpisodeDetailResponse] = []


# Library Item Schemas
class LibraryItemResponse(BaseModel):
    id: str
    title: str
    year: int
    media_type: MediaType
    image_url: str
    image_alt: str
    quality: str
    rating: str | None = None
    description: str | None = None
    added_date: datetime | None = None
    size: str
    torrent_info: list[dict[str, Any]] = []
    torrent_count: int = 0
    nb_media: int = 0
    created_at: datetime

    @field_validator("torrent_count", mode="before")
    @classmethod
    def compute_torrent_count(cls, v, info):
        """Compute torrent_count from torrent_info list length"""
        if v and v > 0:
            return v
        torrent_info = info.data.get("torrent_info")
        if torrent_info and isinstance(torrent_info, list):
            return len(torrent_info)
        return 0

    class Config:
        from_attributes = True


# Calendar Event Schemas
class CalendarEventResponse(BaseModel):
    id: str
    title: str
    media_type: MediaType
    release_date: date
    episode: str | None = None
    image_url: str
    image_alt: str
    status: CalendarStatus
    created_at: datetime

    class Config:
        from_attributes = True


# Jellyseerr Request Schemas
class JellyseerrRequestResponse(BaseModel):
    id: str
    jellyseerr_id: int
    title: str
    media_type: MediaType
    year: int
    image_url: str
    image_alt: str
    status: RequestStatus
    priority: RequestPriority
    requested_by: str
    requested_by_avatar: str | None = None
    requested_by_user_id: int | None = None
    requested_date: str
    quality: str
    description: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class JellyseerrRequestAction(BaseModel):
    request_id: str
    action: str = Field(..., pattern="^(approve|decline)$")


# Sync Metadata Schemas
class SyncMetadataResponse(BaseModel):
    id: str
    service_name: ServiceType
    last_sync_time: datetime | None = None
    sync_status: SyncStatus
    error_message: str | None = None
    next_sync_time: datetime | None = None
    sync_duration_ms: int | None = None
    records_synced: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Dashboard Response
class DashboardResponse(BaseModel):
    statistics: list[DashboardStatisticResponse]
    recent_items: list[LibraryItemResponse]
    calendar_events: list[CalendarEventResponse]
    recent_requests: list[JellyseerrRequestResponse]


# Playback Session Schemas
class PlaybackSessionResponse(BaseModel):
    id: str
    media_id: str
    media_title: str
    media_type: MediaType
    media_year: int | None = None
    episode_info: str | None = None
    poster_url: str | None = None
    library_item_id: str | None = None
    user_id: str
    user_name: str
    device_type: DeviceType
    device_name: str | None = None
    client_name: str | None = None
    video_quality: VideoQuality
    playback_method: PlaybackMethod
    transcoding_progress: int = 0
    transcoding_speed: float | None = None
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: int | None = None
    watched_seconds: int = 0
    status: SessionStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Webhook Payload Schemas
class WebhookPlaybackData(BaseModel):
    """Schéma pour les données du webhook de lecture"""

    media_id: str = Field(..., description="ID du média (Jellyfin/Plex)")
    media_title: str = Field(..., description="Titre du média")
    media_type: str = Field(default="movie", description="Type: movie ou tv")
    media_year: int | None = None
    episode_info: str | None = Field(None, description="Info épisode (ex: S04E09)")
    poster_url: str | None = None
    user_id: str = Field(..., description="ID de l'utilisateur")
    user_name: str = Field(..., description="Nom de l'utilisateur")
    device_name: str | None = None
    client_name: str | None = Field(None, description="Nom du client (ex: Jellyfin Web)")
    video_quality: str | None = Field(None, description="Qualité vidéo (ex: 1080p, 4K)")
    is_transcoding: bool = False
    is_direct_playing: bool = True
    transcoding_progress: int | None = 0
    transcoding_speed: float | None = None
    video_codec_source: str | None = None
    video_codec_target: str | None = None
    duration_seconds: int | None = None
    watched_seconds: int | None = None


class WebhookPayload(BaseModel):
    """Schéma principal du webhook"""

    event: str = Field(..., description="Type d'événement: playback.start, playback.stop, etc.")
    data: WebhookPlaybackData


# Media Statistics Schemas
class MediaStatisticResponse(BaseModel):
    """Schéma de réponse pour les statistiques d'un média"""

    id: str
    media_id: str
    media_title: str
    media_type: MediaType
    media_year: int | None = None
    poster_url: str | None = None
    total_plays: int
    total_duration_seconds: int
    total_watched_seconds: int
    unique_users: int
    most_used_quality: VideoQuality | None = None
    direct_play_count: int
    transcoded_count: int
    last_played_at: datetime | None = None
    first_played_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Device Statistics Schemas
class DeviceStatisticResponse(BaseModel):
    """Schéma de réponse pour les statistiques par appareil"""

    id: str
    device_type: DeviceType
    period_start: date
    period_end: date
    session_count: int
    total_duration_seconds: int
    unique_users: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Daily Analytics Schemas
class DailyAnalyticResponse(BaseModel):
    """Schéma de réponse pour les analytics quotidiennes"""

    id: str
    date: date
    total_plays: int
    hours_watched: float
    unique_users: int
    unique_media: int
    movies_played: int
    tv_episodes_played: int
    direct_play_count: int
    transcoded_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Server Metrics Schemas
class ServerMetricResponse(BaseModel):
    """Schéma de réponse pour les métriques serveur"""

    id: str
    cpu_usage_percent: float | None = None
    memory_usage_gb: float | None = None
    memory_total_gb: float | None = None
    storage_used_tb: float | None = None
    storage_total_tb: float | None = None
    bandwidth_mbps: float | None = None
    cpu_status: str | None = None
    memory_status: str | None = None
    bandwidth_status: str | None = None
    storage_status: str | None = None
    active_sessions_count: int = 0
    active_transcoding_count: int = 0
    recorded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Analytics Dashboard Schemas
class UsageAnalyticsResponse(BaseModel):
    """Schéma pour le graphique Usage Analytics (Vue 1)"""

    date: date
    hours_watched: float
    total_plays: int


class MediaPlaybackAnalyticsItem(BaseModel):
    """Schéma pour un élément du tableau Media Playback Analytics (Vue 2)"""

    media_title: str
    media_type: MediaType
    plays: int
    duration: str  # Format: "2h 28m"
    quality: str
    status: str  # "Direct" ou "Transcoded"
    poster_url: str | None = None
    last_played_at: datetime | None = None


class ActiveSessionItem(BaseModel):
    """Schéma pour une session active (Vue 3)"""

    media_title: str
    user_name: str
    quality_from: str
    quality_to: str
    progress: int  # 0-100
    speed: float  # Ex: 1.2x
    device_type: DeviceType


class DeviceBreakdownItem(BaseModel):
    """Schéma pour la répartition par appareil (Vue 3)"""

    device_type: DeviceType
    session_count: int
    percentage: float


class ServerPerformanceResponse(BaseModel):
    """Schéma pour les métriques serveur (Vue 3)"""

    cpu_usage_percent: float
    cpu_status: str
    memory_usage_gb: float
    memory_total_gb: float
    memory_status: str
    storage_used_tb: float
    storage_total_tb: float
    storage_status: str
    bandwidth_mbps: float
    bandwidth_status: str
    active_sessions: list[ActiveSessionItem]
    active_transcoding_count: int
