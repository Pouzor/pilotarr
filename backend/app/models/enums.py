import enum


class ServiceType(str, enum.Enum):
    JELLYFIN = "jellyfin"
    JELLYSEERR = "jellyseerr"
    SONARR = "sonarr"
    RADARR = "radarr"
    QBITTORRENT = "qbittorrent"
    PROWLARR = "prowlarr"


class StatType(str, enum.Enum):
    USERS = "users"
    MOVIES = "movies"
    TV_SHOWS = "tv_shows"
    MONITORED_ITEMS = "monitored_items"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class MediaType(str, enum.Enum):
    MOVIE = "movie"
    TV = "tv"


class RequestPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CalendarStatus(str, enum.Enum):
    MONITORED = "monitored"
    DOWNLOADING = "downloading"
    AVAILABLE = "available"


class DeviceType(str, enum.Enum):
    WEB_BROWSER = "web_browser"
    MOBILE_APP = "mobile_app"
    SMART_TV = "smart_tv"
    DESKTOP_APP = "desktop_app"
    GAME_CONSOLE = "game_console"
    STREAMING_DEVICE = "streaming_device"
    OTHER = "other"


class PlaybackMethod(str, enum.Enum):
    DIRECT_PLAY = "direct_play"
    DIRECT_STREAM = "direct_stream"
    TRANSCODED = "transcoded"


class VideoQuality(str, enum.Enum):
    FOUR_K_HDR = "4k_hdr"
    FOUR_K = "4k"
    FULL_HD = "1080p"
    HD = "720p"
    SD = "480p"
    LOW = "360p"
    UNKNOWN = "unknown"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    BUFFERING = "buffering"


class RequestStatus(int, enum.Enum):
    PENDING = 1
    APPROVED = 2
    DECLINED = 3
    AVAILABLE = 4  # Seer status 5 — media fully available in library


class ItemSortBy(str, enum.Enum):
    ADDED_DATE = "added_date"
    TITLE = "title"
    SIZE = "size"
    RATIO = "ratio"
