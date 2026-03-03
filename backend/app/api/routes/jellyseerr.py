import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import JellyseerrRequest, RequestStatus, ServiceConfiguration, ServiceType
from app.services import JellyseerrConnector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jellyseerr", tags=["Jellyseerr"])


@router.post("/requests/{request_id}/approve")
async def approve_request(request_id: str, db: Session = Depends(get_db)):
    """Approuver une requête Jellyseerr"""
    # Récupérer la config Jellyseerr
    service = db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == ServiceType.JELLYSEERR).first()

    if not service or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service Jellyseerr non configuré ou inactif"
        )

    # Vérifier que la requête existe en DB
    request = db.query(JellyseerrRequest).filter(JellyseerrRequest.id == request_id).first()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requête non trouvée")

    # Appeler l'API Jellyseerr avec l'ID externe
    connector = JellyseerrConnector(base_url=service.url, api_key=service.api_key)

    try:
        await connector.approve_request(request.jellyseerr_id)

        # Mettre à jour le statut en DB
        request.status = RequestStatus.APPROVED
        db.commit()

        return {"success": True, "message": "Requête approuvée avec succès"}
    except Exception as e:
        logger.error("Error approving request %s: %s", request_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de l'approbation de la requête"
        ) from e
    finally:
        await connector.close()


@router.post("/requests/{request_id}/decline")
async def decline_request(request_id: str, db: Session = Depends(get_db)):
    """Refuser une requête Jellyseerr"""
    service = db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == ServiceType.JELLYSEERR).first()

    if not service or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service Jellyseerr non configuré ou inactif"
        )

    request = db.query(JellyseerrRequest).filter(JellyseerrRequest.id == request_id).first()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requête non trouvée")

    connector = JellyseerrConnector(base_url=service.url, api_key=service.api_key)

    try:
        await connector.decline_request(request.jellyseerr_id)

        # Mettre à jour le statut en DB
        request.status = RequestStatus.DECLINED
        db.commit()

        return {"success": True, "message": "Requête refusée avec succès"}
    except Exception as e:
        logger.error("Error declining request %s: %s", request_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors du refus de la requête"
        ) from e
    finally:
        await connector.close()
