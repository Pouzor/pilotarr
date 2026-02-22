from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, auth, dashboard, jellyseerr, library, monitoring, services, sync, torrents
from app.core.config import settings
from app.core.security import get_current_user
from app.db import SessionLocal, check_db_connection, init_db
from app.db_migrations import create_analytics_tables
from app.schedulers.analytics_scheduler import analytics_scheduler
from app.schedulers.scheduler import app_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    print(f"🚀 Démarrage de {settings.APP_NAME} v{settings.APP_VERSION}")

    if check_db_connection():
        print("✅ Connexion à la base de données OK")
        init_db()
        print("✅ Tables initialisées")
        create_analytics_tables()
        print("✅ Migrations appliquées")

        # Seed default user if it doesn't exist
        from app.services.auth_service import init_default_user

        db = SessionLocal()
        try:
            init_default_user(db)
        finally:
            db.close()
    else:
        print("❌ Échec de connexion à la base de données")

    # Start scheduler (sync every 15 minutes)
    app_scheduler.start(interval_minutes=15)
    analytics_scheduler.start()

    yield

    # Shutdown
    print("🛑 Arrêt de l'application...")
    app_scheduler.stop()
    analytics_scheduler.stop()


# Start FastAPI
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, debug=settings.DEBUG, lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Remove in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth.router)
app.include_router(analytics.public_router, prefix="/api")  # webhook only (?apiKey=)

# JWT-protected routes
app.include_router(services.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(dashboard.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(jellyseerr.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(sync.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(library.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(monitoring.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(torrents.router, dependencies=[Depends(get_current_user)])


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "scheduler": "active" if app_scheduler.is_running else "inactive",
        "analytics_scheduler": "active" if analytics_scheduler.running else "inactive",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = check_db_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "scheduler": "running" if app_scheduler.is_running else "stopped",
        "analytics_scheduler": "running" if analytics_scheduler.running else "stopped",
    }
