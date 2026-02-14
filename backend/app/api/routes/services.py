from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import ServiceConfigurationCreate, ServiceConfigurationResponse, ServiceConfigurationUpdate
from app.db import get_db
from app.models import ServiceConfiguration, ServiceType
from app.services import JellyfinConnector, JellyseerrConnector, RadarrConnector, SonarrConnector

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("/", response_model=list[ServiceConfigurationResponse])
async def get_all_services(db: Session = Depends(get_db)):
    """Récupérer toutes les configurations de services"""
    services = db.query(ServiceConfiguration).all()
    return services


@router.get("/{service_name}", response_model=ServiceConfigurationResponse)
async def get_service(service_name: ServiceType, db: Session = Depends(get_db)):
    """Récupérer une configuration de service spécifique"""
    service = db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == service_name).first()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service {service_name} non trouvé")

    return service


@router.post("/", response_model=ServiceConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def create_service(service_data: ServiceConfigurationCreate, db: Session = Depends(get_db)):
    """Créer une nouvelle configuration de service"""
    # Vérifier si le service existe déjà
    existing = (
        db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == service_data.service_name).first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Service {service_data.service_name} existe déjà"
        )

    # Créer le service
    service = ServiceConfiguration(**service_data.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)

    return service


@router.put("/{service_name}", response_model=ServiceConfigurationResponse)
async def update_service(
    service_name: ServiceType, service_data: ServiceConfigurationUpdate, db: Session = Depends(get_db)
):
    """Mettre à jour une configuration de service"""
    service = db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == service_name).first()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service {service_name} non trouvé")

    # Mettre à jour les champs fournis
    update_data = service_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)

    db.commit()
    db.refresh(service)

    return service


@router.delete("/{service_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_name: ServiceType, db: Session = Depends(get_db)):
    """Supprimer une configuration de service"""
    service = db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == service_name).first()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service {service_name} non trouvé")

    db.delete(service)
    db.commit()

    return None


@router.post("/{service_name}/test")
async def test_service_connection(service_name: ServiceType, db: Session = Depends(get_db)):
    """Tester la connexion à un service"""
    service = db.query(ServiceConfiguration).filter(ServiceConfiguration.service_name == service_name).first()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Service {service_name} non trouvé")

    # Créer le bon connecteur selon le type
    connector_map = {
        ServiceType.RADARR: RadarrConnector,
        ServiceType.SONARR: SonarrConnector,
        ServiceType.JELLYFIN: JellyfinConnector,
        ServiceType.JELLYSEERR: JellyseerrConnector,
    }

    connector_class = connector_map.get(service_name)
    if not connector_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Type de service non supporté: {service_name}"
        )

    # Passer le port au connecteur si disponible
    connector = connector_class(base_url=service.url, api_key=service.api_key, port=service.port)

    try:
        success, message = await connector.test_connection()

        # Mettre à jour le statut du test
        service.last_tested_at = datetime.now()
        service.test_status = "success" if success else "failed"
        service.test_message = message
        db.commit()

        return {"success": success, "message": message, "tested_at": service.last_tested_at}
    finally:
        await connector.close()
