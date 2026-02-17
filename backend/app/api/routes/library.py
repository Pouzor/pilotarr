from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import (
    EpisodeDetailResponse,
    EpisodeResponse,
    LibraryItemResponse,
    SeasonResponse,
    SeasonWithEpisodesResponse,
)
from app.db import get_db
from app.models import Episode, LibraryItem, MediaType, Season
from app.models.enums import ItemSortBy

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


@router.get("/", response_model=list[LibraryItemResponse])
async def get_library(
    limit: int = Query(default=20, ge=1, le=100),
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

    items = (
        db.query(LibraryItem)
        .where(LibraryItem.size != 0)
        .options(selectinload(LibraryItem.torrents))
        .order_by(sort_clause)
        .limit(limit)
        .all()
    )

    results = []
    for item in items:
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
        "created_at": item.created_at,
        "torrent_info": _build_torrent_info_array(item),
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
                        title=ep.title,
                        air_date=ep.air_date,
                        monitored=ep.monitored,
                        has_file=ep.has_file,
                        download_status="downloaded" if ep.has_file else "missing",
                        file_size_str=_format_bytes(ep.file_size),
                        quality_profile=ep.quality_profile,
                    )
                    for ep in eps
                ],
            )
        )

    return result
