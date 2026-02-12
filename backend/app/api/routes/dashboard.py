from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import (
    CalendarEventResponse,
    DashboardResponse,
    DashboardStatisticResponse,
    JellyseerrRequestResponse,
    LibraryItemResponse,
)
from app.db import get_db
from app.models import CalendarEvent, DashboardStatistic, JellyseerrRequest, LibraryItem
from app.models.enums import ItemSortBy

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

TORRENT_INFO_ALLOWED_KEYS = {"seeding_time", "ratio", "size", "download_date", "status"}


def _build_torrent_info_array(item: LibraryItem) -> list[dict]:
    """Build torrent_info array from the torrents relationship, stripping unwanted keys."""
    result = []
    for t in item.torrents:
        if not t.torrent_info:
            continue
        result.append({k: v for k, v in t.torrent_info.items() if k in TORRENT_INFO_ALLOWED_KEYS})
    return result


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    recent_items_limit: int = Query(default=6, ge=1, le=50),
    calendar_days: int = Query(default=7, ge=1, le=30),
    recent_requests_limit: int = Query(default=4, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Récupérer toutes les données du dashboard

    Args:
        recent_items_limit: Nombre d'items récents à afficher
        calendar_days: Nombre de jours de calendrier
        recent_requests_limit: Nombre de requêtes récentes
    """
    # Statistiques globales
    statistics = db.query(DashboardStatistic).all()

    # Items récents
    recent_items_query = (
        db.query(LibraryItem)
        .options(selectinload(LibraryItem.torrents))
        .order_by(LibraryItem.created_at.desc())
        .limit(recent_items_limit)
        .all()
    )
    recent_items = []
    for item in recent_items_query:
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
        recent_items.append(data)

    # Événements du calendrier (prochains jours)
    today = datetime.now().date()
    future_date = today + timedelta(days=calendar_days)
    calendar_events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.release_date >= today)
        .filter(CalendarEvent.release_date <= future_date)
        .order_by(CalendarEvent.release_date.asc())
        .all()
    )

    # Requêtes récentes
    recent_requests = (
        db.query(JellyseerrRequest).order_by(JellyseerrRequest.created_at.desc()).limit(recent_requests_limit).all()
    )

    return {
        "statistics": statistics,
        "recent_items": recent_items,
        "calendar_events": calendar_events,
        "recent_requests": recent_requests,
    }


@router.get("/statistics", response_model=list[DashboardStatisticResponse])
async def get_statistics(db: Session = Depends(get_db)):
    """Récupérer uniquement les statistiques"""
    statistics = db.query(DashboardStatistic).all()
    return statistics


@router.get("/recent-items", response_model=list[LibraryItemResponse])
async def get_recent_items(
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

    items = db.query(LibraryItem).options(selectinload(LibraryItem.torrents)).order_by(sort_clause).limit(limit).all()

    # Override torrent_info with array from relationship at serialization time
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


@router.get("/calendar", response_model=list[CalendarEventResponse])
async def get_calendar(days: int = Query(default=30, ge=1, le=90), db: Session = Depends(get_db)):
    """Récupérer le calendrier des sorties à venir"""
    today = datetime.now().date()
    future_date = today + timedelta(days=days)

    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.release_date >= today)
        .filter(CalendarEvent.release_date <= future_date)
        .order_by(CalendarEvent.release_date.asc())
        .all()
    )

    return events


@router.get("/requests", response_model=list[JellyseerrRequestResponse])
async def get_requests(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    """Récupérer les requêtes Jellyseerr"""
    requests = db.query(JellyseerrRequest).order_by(JellyseerrRequest.created_at.desc()).limit(limit).all()
    return requests
