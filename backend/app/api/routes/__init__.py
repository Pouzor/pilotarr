# Routes Package
"""
Initialisation des routes API
"""

from app.api.routes import analytics, dashboard, jellyseerr, library, services, sync

__all__ = ["dashboard", "services", "sync", "jellyseerr", "analytics", "library"]
