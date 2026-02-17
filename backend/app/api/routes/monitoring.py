from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import MonitoringItemResponse, MonitoringSeasonInfo
from app.db import get_db
from app.models import Episode, LibraryItem, LibraryItemTorrent
from app.models.enums import MediaType

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def _compute_monitoring_status(item: LibraryItem) -> str:
    if item.media_type == MediaType.TV:
        if any(s.monitored for s in item.seasons):
            return "monitored"
        return "unmonitored"
    return "monitored"


def _compute_availability_status(item: LibraryItem) -> str:
    if item.media_type == MediaType.TV:
        monitored_seasons = [s for s in item.seasons if s.monitored]
        if not monitored_seasons:
            return "missing"
        total_needed = sum(s.episode_count for s in monitored_seasons)
        total_available = sum(s.episode_file_count for s in monitored_seasons)
        if total_needed > 0 and total_available >= total_needed:
            return "available"
        return "missing"
    return "available" if item.nb_media > 0 else "missing"


def _build_tv_download_history(episodes: list) -> list[dict]:
    """Last 5 downloaded episodes, sorted by dateAdded in episode_file_info."""
    with_dates = []
    for ep in episodes:
        fi = ep.episode_file_info or {}
        date_added = fi.get("dateAdded", "")
        if date_added:
            with_dates.append((ep, date_added))

    with_dates.sort(key=lambda x: x[1], reverse=True)

    result = []
    for ep, date_added in with_dates[:5]:
        fi = ep.episode_file_info or {}
        quality = ep.quality_profile or ""
        if not quality:
            q = fi.get("quality", {})
            if isinstance(q, dict):
                quality = q.get("quality", {}).get("name", "") or ""
        action = f"Downloaded S{ep.season_number:02d}E{ep.episode_number:02d}"
        if ep.title:
            action += f" – {ep.title}"
        result.append({"date": date_added[:10], "action": action, "quality": quality})

    return result


def _build_movie_download_history(torrents: list, fallback_quality: str) -> list[dict]:
    """Last 5 downloads from torrent_info, sorted by download_date."""
    with_dates = []
    for t in torrents:
        ti = t.torrent_info or {}
        download_date = ti.get("download_date", "")
        if download_date:
            with_dates.append((ti, download_date))

    with_dates.sort(key=lambda x: x[1], reverse=True)

    result = []
    for ti, download_date in with_dates[:5]:
        status = ti.get("status", "")
        action = "Downloaded" if status.lower() in ("seeding", "completed", "") else status
        # download_date may be a Unix timestamp (int) or an ISO string
        if isinstance(download_date, int):
            date_str = datetime.fromtimestamp(download_date, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            date_str = str(download_date)[:10]
        result.append({"date": date_str, "action": action, "quality": fallback_quality})

    return result


@router.get("/items", response_model=list[MonitoringItemResponse])
async def get_monitoring_items(db: Session = Depends(get_db)):
    """Get all library items with monitoring, availability status, and download history."""
    items = db.query(LibraryItem).options(selectinload(LibraryItem.seasons)).order_by(LibraryItem.title).all()

    # Bulk-load downloaded episodes for all TV shows
    tv_ids = [item.id for item in items if item.media_type == MediaType.TV]
    movie_ids = [item.id for item in items if item.media_type == MediaType.MOVIE]

    episodes_by_item: dict[str, list] = {}
    if tv_ids:
        downloaded = (
            db.query(Episode)
            .filter(
                Episode.library_item_id.in_(tv_ids),
                Episode.has_file == True,  # noqa: E712
                Episode.episode_file_info.isnot(None),
            )
            .all()
        )
        for ep in downloaded:
            episodes_by_item.setdefault(ep.library_item_id, []).append(ep)

    torrents_by_item: dict[str, list] = {}
    if movie_ids:
        torrents = db.query(LibraryItemTorrent).filter(LibraryItemTorrent.library_item_id.in_(movie_ids)).all()
        for t in torrents:
            torrents_by_item.setdefault(t.library_item_id, []).append(t)

    result = []
    for item in items:
        seasons_sorted = sorted(item.seasons, key=lambda s: s.season_number)
        season_infos = [
            MonitoringSeasonInfo(
                number=s.season_number,
                episodes=s.total_episode_count,
                monitored=s.episode_count,
                available=s.episode_file_count,
                is_monitored=s.monitored,
            )
            for s in seasons_sorted
        ]

        service = "sonarr" if item.media_type == MediaType.TV else "radarr"

        if item.media_type == MediaType.TV:
            download_history = _build_tv_download_history(episodes_by_item.get(item.id, []))
        else:
            download_history = _build_movie_download_history(torrents_by_item.get(item.id, []), item.quality)

        result.append(
            MonitoringItemResponse(
                id=item.id,
                title=item.title,
                year=item.year,
                service=service,
                monitoring_status=_compute_monitoring_status(item),
                availability_status=_compute_availability_status(item),
                quality_profile=item.quality,
                last_updated=item.updated_at,
                file_size=item.size,
                image_url=item.image_url,
                seasons=season_infos,
                download_history=download_history,
            )
        )

    return result
