from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import LibraryItemResponse
from app.db import get_db
from app.models import LibraryItem
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
