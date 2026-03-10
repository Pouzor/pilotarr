from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import (
    EpisodeDetailResponse,
    EpisodeResponse,
    LibraryItemResponse,
    SeasonResponse,
    SeasonWithEpisodesResponse,
    WatchedUpdateRequest,
)
from app.db import get_db
from app.models import Episode, LibraryItem, MediaType, Season
from app.models.enums import ItemSortBy
from app.models.models import PlaybackSession, ServiceConfiguration
from app.services.connector_factory import create_connector

router = APIRouter(prefix="/library", tags=["Library"])

TORRENT_INFO_ALLOWED_KEYS = {"seeding_time", "ratio", "size", "download_date", "status"}


def _build_torrent_info_array(item: LibraryItem) -> list[dict]:
    """Build torrent_info array from the torrents relationship, stripping unwanted keys."""
    result = []
    for t in item.torrents:
        if not t.torrent_info:
            continue
        result.append({k: v for k, v in t.torrent_info.items() if k in TORRENT_INFO_ALLOWED_KEYS})
    return result


@router.patch("/{id}/seasons/{season_number}/episodes/{episode_number}/watched")
async def set_episode_watched(
    id: str,
    season_number: int,
    episode_number: int,
    body: WatchedUpdateRequest,
    db: Session = Depends(get_db),
):
    item = db.query(LibraryItem).filter(LibraryItem.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")
    ep = (
        db.query(Episode)
        .filter(
            Episode.library_item_id == id,
            Episode.season_number == season_number,
            Episode.episode_number == episode_number,
        )
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    ep.watched = body.watched
    db.commit()
    return {"watched": ep.watched}


@router.patch("/{id}/seasons/{season_number}/watched")
async def set_season_watched(
    id: str,
    season_number: int,
    body: WatchedUpdateRequest,
    db: Session = Depends(get_db),
):
    item = db.query(LibraryItem).filter(LibraryItem.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")
    episodes = (
        db.query(Episode)
        .filter(
            Episode.library_item_id == id,
            Episode.season_number == season_number,
        )
        .all()
    )
    for ep in episodes:
        ep.watched = body.watched
    db.commit()
    return {"watched": body.watched, "updated": len(episodes)}


@router.get("/", response_model=list[LibraryItemResponse])
async def get_library(
    limit: int | None = Query(default=None, ge=1),
    sort_by: ItemSortBy = Query(default=ItemSortBy.ADDED_DATE),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    """Récupérer les items récemment ajoutés"""
    # Sort still uses the pre-aggregated torrent_info JSON column for ratio
    sort_mapping = {
        ItemSortBy.ADDED_DATE: LibraryItem.created_at,
        ItemSortBy.TITLE: LibraryItem.title,
        ItemSortBy.SIZE: LibraryItem.size,
        ItemSortBy.RATIO: func.json_extract(LibraryItem.torrent_info, "$.ratio"),
    }

    sort_column = sort_mapping[sort_by]

    if sort_order == "asc":
        sort_clause = sort_column.asc()
    else:
        sort_clause = sort_column.desc()

    query = (
        db.query(LibraryItem)
        .where(LibraryItem.size != 0)
        .options(selectinload(LibraryItem.torrents))
        .order_by(sort_clause)
    )
    items = query.limit(limit).all() if limit else query.all()

    # Batch-fetch watched episode counts for all TV items (avoids N+1)
    item_ids = [item.id for item in items]
    watched_counts: dict[str, int] = {}
    if item_ids:
        rows = (
            db.query(Episode.library_item_id, func.count(Episode.id))
            .filter(Episode.library_item_id.in_(item_ids), Episode.watched.is_(True))
            .group_by(Episode.library_item_id)
            .all()
        )
        watched_counts = {row[0]: row[1] for row in rows}

    results = []
    for item in items:
        if item.media_type == MediaType.TV:
            watched_count = watched_counts.get(item.id, 0)
        else:
            watched_count = 1 if item.watched else 0
        data = {
            "id": item.id,
            "title": item.title,
            "year": item.year,
            "media_type": item.media_type,
            "image_url": item.image_url,
            "image_alt": item.image_alt,
            "quality": item.quality,
            "rating": item.rating,
            "description": item.description,
            "added_date": item.added_date,
            "size": item.size,
            "nb_media": item.nb_media,
            "watched": item.watched,
            "watched_count": watched_count,
            "media_streams": item.media_streams,
            "created_at": item.created_at,
            "torrent_info": _build_torrent_info_array(item),
        }
        results.append(data)

    return results


@router.get("/{id}", response_model=LibraryItemResponse)
async def get_library_item(
    id: str,
    db: Session = Depends(get_db),
):
    item = (
        db.query(LibraryItem)
        .where(LibraryItem.id == id, LibraryItem.size != 0)
        .options(selectinload(LibraryItem.torrents))
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")

    # Count views from PlaybackSession
    if item.media_type == MediaType.TV:
        # Distinct episodes watched
        view_count = (
            db.query(func.count(func.distinct(PlaybackSession.episode_info)))
            .filter(PlaybackSession.library_item_id == id, PlaybackSession.is_active.is_(False))
            .scalar()
            or 0
        )
    else:
        # Number of completed sessions for movies
        view_count = (
            db.query(func.count(PlaybackSession.id))
            .filter(PlaybackSession.library_item_id == id, PlaybackSession.is_active.is_(False))
            .scalar()
            or 0
        )

    sonarr_series_id = None
    if item.media_type == MediaType.TV:
        first_season = db.query(Season).filter(Season.library_item_id == id).first()
        if first_season:
            sonarr_series_id = first_season.sonarr_series_id

    data = {
        "id": item.id,
        "title": item.title,
        "year": item.year,
        "media_type": item.media_type,
        "image_url": item.image_url,
        "image_alt": item.image_alt,
        "quality": item.quality,
        "rating": item.rating,
        "description": item.description,
        "added_date": item.added_date,
        "size": item.size,
        "nb_media": item.nb_media,
        "view_count": view_count,
        "watched": item.watched,
        "media_streams": item.media_streams,
        "created_at": item.created_at,
        "torrent_info": _build_torrent_info_array(item),
        "jellyfin_id": item.jellyfin_id,
        "sonarr_series_id": sonarr_series_id,
    }

    return data


@router.get("/{id}/seasons", response_model=list[SeasonResponse])
async def get_series_seasons(id: str, db: Session = Depends(get_db)):
    """Get all seasons for a TV series"""
    item = db.query(LibraryItem).filter(LibraryItem.id == id).first()

    if not item or item.media_type != MediaType.TV:
        raise HTTPException(status_code=404, detail="TV series not found")

    seasons = db.query(Season).filter(Season.library_item_id == id).order_by(Season.season_number).all()

    return seasons


@router.get("/{id}/seasons/{season_number}/episodes", response_model=list[EpisodeResponse])
async def get_season_episodes(id: str, season_number: int, db: Session = Depends(get_db)):
    """Get all episodes for a specific season"""
    season = db.query(Season).filter(Season.library_item_id == id, Season.season_number == season_number).first()

    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    episodes = db.query(Episode).filter(Episode.season_id == season.id).order_by(Episode.episode_number).all()

    return episodes


def _format_bytes(size: int | None) -> str | None:
    if not size:
        return None
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units[:-1]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


@router.get("/{id}/seasons-with-episodes", response_model=list[SeasonWithEpisodesResponse])
async def get_seasons_with_episodes(id: str, db: Session = Depends(get_db)):
    """All seasons with embedded episodes — single request for the detail page."""
    item = db.query(LibraryItem).filter(LibraryItem.id == id).first()
    if not item or item.media_type != MediaType.TV:
        raise HTTPException(status_code=404, detail="TV series not found")

    seasons = (
        db.query(Season)
        .filter(Season.library_item_id == id)
        .options(selectinload(Season.episodes))
        .order_by(Season.season_number)
        .all()
    )

    result = []
    for season in seasons:
        eps = sorted(season.episodes, key=lambda e: e.episode_number)
        result.append(
            SeasonWithEpisodesResponse(
                season_number=season.season_number,
                is_monitored=season.monitored,
                episode_count=season.episode_count,
                episode_file_count=season.episode_file_count,
                total_episode_count=season.total_episode_count,
                episodes=[
                    EpisodeDetailResponse(
                        episode_number=ep.episode_number,
                        sonarr_episode_id=ep.sonarr_episode_id,
                        title=ep.title,
                        air_date=ep.air_date,
                        monitored=ep.monitored,
                        has_file=ep.has_file,
                        download_status="downloaded" if ep.has_file else "missing",
                        file_size_str=_format_bytes(ep.file_size),
                        quality_profile=ep.quality_profile,
                        media_streams=ep.media_streams,
                        watched=ep.watched,
                    )
                    for ep in eps
                ],
            )
        )

    return result


def _get_sonarr_connector(db: Session):
    """Helper: return an active SonarrConnector or raise 503."""
    service = (
        db.query(ServiceConfiguration)
        .filter(ServiceConfiguration.service_name == "sonarr", ServiceConfiguration.is_active.is_(True))
        .first()
    )
    if not service:
        raise HTTPException(status_code=503, detail="Sonarr service not configured")
    return create_connector(service)


def _get_radarr_connector(db: Session):
    """Helper: return an active RadarrConnector or raise 503."""
    service = (
        db.query(ServiceConfiguration)
        .filter(ServiceConfiguration.service_name == "radarr", ServiceConfiguration.is_active.is_(True))
        .first()
    )
    if not service:
        raise HTTPException(status_code=503, detail="Radarr service not configured")
    return create_connector(service)


@router.post("/{id}/refresh")
async def refresh_media(id: str, db: Session = Depends(get_db)):
    """Trigger RefreshSeries+RescanSeries (TV) or RefreshMovie+RescanMovie (movie) in Sonarr/Radarr."""
    item = db.query(LibraryItem).filter(LibraryItem.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Library item not found")

    if item.media_type == MediaType.TV:
        first_season = db.query(Season).filter(Season.library_item_id == id).first()
        if not first_season:
            raise HTTPException(status_code=404, detail="No season found for series")
        connector = _get_sonarr_connector(db)
        try:
            await connector.refresh_series(first_season.sonarr_series_id)
            await connector.rescan_series(first_season.sonarr_series_id)
        finally:
            await connector.close()
        return {"refreshing": True, "message": "Refresh and scan started in Sonarr"}
    else:
        connector = _get_radarr_connector(db)
        try:
            movie_id = await connector.find_movie_id_by_title(item.title)
            if not movie_id:
                raise HTTPException(status_code=404, detail=f"Movie '{item.title}' not found in Radarr")
            await connector.refresh_movie(movie_id)
            await connector.rescan_movie(movie_id)
        finally:
            await connector.close()
        return {"refreshing": True, "message": "Refresh and scan started in Radarr"}


@router.post("/{id}/seasons/{season_number}/episodes/{episode_number}/monitor")
async def monitor_episode(
    id: str,
    season_number: int,
    episode_number: int,
    db: Session = Depends(get_db),
):
    """Monitor an unmonitored episode in Sonarr and update the local DB."""
    ep = (
        db.query(Episode)
        .filter(
            Episode.library_item_id == id,
            Episode.season_number == season_number,
            Episode.episode_number == episode_number,
        )
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    connector = _get_sonarr_connector(db)
    try:
        ok = await connector.monitor_episode(ep.sonarr_episode_id)
        if not ok:
            raise HTTPException(status_code=502, detail="Sonarr monitor request failed")
        ep.monitored = True
        db.commit()
        return {"monitored": True}
    finally:
        await connector.close()


@router.post("/{id}/seasons/{season_number}/episodes/{episode_number}/search")
async def search_episode(
    id: str,
    season_number: int,
    episode_number: int,
    db: Session = Depends(get_db),
):
    """Trigger an episode search in Sonarr."""
    ep = (
        db.query(Episode)
        .filter(
            Episode.library_item_id == id,
            Episode.season_number == season_number,
            Episode.episode_number == episode_number,
        )
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    connector = _get_sonarr_connector(db)
    try:
        ok = await connector.search_episode(ep.sonarr_episode_id)
        if not ok:
            raise HTTPException(status_code=502, detail="Sonarr search request failed")
        return {"searching": True}
    finally:
        await connector.close()
