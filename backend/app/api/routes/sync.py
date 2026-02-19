from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.api.schemas import SyncMetadataResponse
from app.db import SessionLocal, get_db
from app.models import SyncMetadata
from app.schedulers.sync_service import SyncService
from app.services.jellyfin_streams_service import JellyfinStreamsService

router = APIRouter(prefix="/sync", tags=["Synchronization"])


@router.post("/trigger")
async def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Déclencher manuellement une synchronisation complète"""

    async def run_sync():
        sync_service = SyncService(db)
        await sync_service.sync_all()

    background_tasks.add_task(run_sync)

    return {"message": "Synchronisation lancée en arrière-plan", "status": "started"}


@router.post("/trigger/sonarr-episodes")
async def trigger_sonarr_episodes_sync(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    series_limit: int = 5,
):
    """Déclencher la synchronisation des épisodes Sonarr"""

    async def run_episodes_sync():
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            print("=" * 80)
            print("🚀 EPISODES SYNC STARTED (Background)")
            print(f"🚀 Parameters: full_sync={full_sync}, series_limit={series_limit}")
            print("=" * 80)

            sync_service = SyncService(db)
            result = await sync_service.sync_sonarr_episodes(full_sync=full_sync, series_limit=series_limit)
            print(f"📊 Episodes sync completed: {result}")
        except Exception as e:
            print(f"❌ Error in episodes sync: {e}")
            import traceback

            traceback.print_exc()
        finally:
            db.close()

    background_tasks.add_task(run_episodes_sync)

    return {
        "message": f"Synchronisation épisodes lancée (full_sync={full_sync}, limit={series_limit})",
        "status": "started",
    }


@router.post("/trigger/jellyfin-streams")
async def trigger_jellyfin_streams_sync(background_tasks: BackgroundTasks):
    """Déclencher la synchronisation des MediaStreams Jellyfin (sous-titres, audio)"""

    async def run_streams_sync():
        db = SessionLocal()
        try:
            service = JellyfinStreamsService(db)
            result = await service.sync_all()
            print(f"📊 Streams sync completed: {result}")
        except Exception as e:
            print(f"❌ Error in streams sync: {e}")
        finally:
            db.close()

    background_tasks.add_task(run_streams_sync)

    return {"message": "Synchronisation MediaStreams Jellyfin lancée en arrière-plan", "status": "started"}


@router.post("/trigger/{service_name}")
async def trigger_service_sync(service_name: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Déclencher la synchronisation d'un service spécifique"""

    async def run_service_sync():
        sync_service = SyncService(db)

        if service_name == "radarr":
            await sync_service.sync_radarr()
        elif service_name == "sonarr":
            await sync_service.sync_sonarr()
        elif service_name == "jellyfin":
            await sync_service.sync_jellyfin()
        elif service_name == "jellyseerr":
            await sync_service.sync_jellyseerr()

    background_tasks.add_task(run_service_sync)

    return {"message": f"Synchronisation {service_name} lancée", "status": "started"}


@router.post("/debug/test-episodes")
async def debug_test_episodes():
    """Simple test endpoint to verify routing works"""
    print("=" * 80)
    print("🧪 DEBUG TEST ENDPOINT CALLED")
    print("=" * 80)
    return {"message": "Test endpoint called successfully", "timestamp": "2026-02-16"}


@router.get("/debug/check-methods")
async def debug_check_methods():
    """Debug: vérifier que les méthodes existent"""

    from app.schedulers.sync_service import SyncService

    methods = [m for m in dir(SyncService) if not m.startswith("_")]
    episodes_methods = [m for m in methods if "episode" in m.lower() or "season" in m.lower()]

    return {
        "all_methods": methods,
        "episodes_season_methods": episodes_methods,
        "sync_sonarr_episodes_exists": hasattr(SyncService, "sync_sonarr_episodes"),
        "sync_sonarr_seasons_exists": hasattr(SyncService, "sync_sonarr_seasons"),
    }


@router.get("/status", response_model=list[SyncMetadataResponse])
async def get_sync_status(db: Session = Depends(get_db)):
    """Récupérer le statut des dernières synchronisations"""
    sync_metadata = db.query(SyncMetadata).all()
    return sync_metadata
