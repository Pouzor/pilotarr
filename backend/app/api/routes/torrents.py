"""
Routes pour gérer les torrents (qBittorrent)
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db import get_db
from app.models.models import LibraryItemTorrent, ServiceConfiguration
from app.services.connector_factory import create_connector
from app.services.torrent_enrichment_service import TorrentEnrichmentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/torrents", tags=["torrents"])


@router.get("/all")
async def list_all_torrents(db: Session = Depends(get_db), _: str = Depends(verify_api_key)) -> dict[str, Any]:
    """
    Returns all torrents from the active torrent client plus global transfer stats.

    Response shape:
        {
            "client": "qbittorrent",
            "transfer": { "dl_speed": int, "ul_speed": int, "connection_status": str },
            "torrents": [ { ...client-agnostic schema... } ]
        }
    """
    qbt_service = (
        db.query(ServiceConfiguration)
        .filter(ServiceConfiguration.service_name == "qbittorrent", ServiceConfiguration.is_active.is_(True))
        .first()
    )

    if not qbt_service:
        raise HTTPException(status_code=404, detail="qBittorrent service not configured")

    connector = create_connector(qbt_service)
    try:
        authenticated = await connector.login()
        if not authenticated:
            raise HTTPException(status_code=503, detail="Could not authenticate with qBittorrent")

        torrents, transfer = await asyncio.gather(
            connector.get_all_torrents(),
            connector.get_transfer_info(),
        )

        return {
            "client": "qbittorrent",
            "transfer": transfer,
            "torrents": torrents,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching all torrents: {e}")
        raise HTTPException(status_code=503, detail=f"qBittorrent unreachable: {e}") from e
    finally:
        await connector.close()


@router.get("/{torrent_hash}")
async def get_torrent_info(
    torrent_hash: str, db: Session = Depends(get_db), _: str = Depends(verify_api_key)
) -> dict[str, Any]:
    """
    Récupère les informations d'un torrent depuis qBittorrent

    Args:
        torrent_hash: Hash du torrent

    Returns:
        Informations du torrent
    """
    # Récupérer la config qBittorrent
    qbt_service = (
        db.query(ServiceConfiguration)
        .filter(ServiceConfiguration.service_name == "qbittorrent", ServiceConfiguration.is_active.is_(True))
        .first()
    )

    if not qbt_service:
        raise HTTPException(status_code=404, detail="Service qBittorrent non configuré")

    try:
        # Créer le connector
        connector = create_connector(qbt_service)

        # Récupérer les infos
        torrent_info = await connector.get_torrent_info(torrent_hash)

        # Fermer la session
        await connector.close()

        if not torrent_info:
            raise HTTPException(status_code=404, detail=f"Torrent {torrent_hash} non trouvé")

        return torrent_info

    except Exception as e:
        logger.error(f"Erreur lors de la récupération du torrent {torrent_hash}: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du torrent") from e


@router.get("/item/{library_item_id}")
async def get_item_torrents(
    library_item_id: str, db: Session = Depends(get_db), _: str = Depends(verify_api_key)
) -> list[dict[str, Any]]:
    """
    Get all torrent rows for a library item (for media detail page).

    Returns:
        List of torrent info dicts with episode/season metadata
    """
    rows = (
        db.query(LibraryItemTorrent)
        .filter(LibraryItemTorrent.library_item_id == library_item_id)
        .order_by(LibraryItemTorrent.season_number, LibraryItemTorrent.episode_id)
        .all()
    )

    return [
        {
            "hash": row.torrent_hash,
            "episode_id": row.episode_id,
            "season_number": row.season_number,
            "is_season_pack": row.is_season_pack,
            **(row.torrent_info or {}),
        }
        for row in rows
    ]


@router.post("/enrich")
async def enrich_library_items(
    limit: int | None = None, db: Session = Depends(get_db), _: str = Depends(verify_api_key)
) -> dict[str, Any]:
    """
    Enrichit les library_items avec les données qBittorrent

    Args:
        limit: Nombre maximum d'items à traiter (optionnel)

    Returns:
        Statistiques de l'enrichissement
    """
    service = TorrentEnrichmentService(db)
    stats = await service.enrich_all_items(limit=limit)
    return stats


@router.post("/enrich/recent")
async def enrich_recent_items(
    days: int = 7, db: Session = Depends(get_db), _: str = Depends(verify_api_key)
) -> dict[str, Any]:
    """
    Enrichit les items récents avec les données qBittorrent

    Args:
        days: Nombre de jours en arrière (défaut: 7)

    Returns:
        Statistiques de l'enrichissement
    """
    service = TorrentEnrichmentService(db)
    stats = await service.enrich_recent_items(days=days)
    return stats
