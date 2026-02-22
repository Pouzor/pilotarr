from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# ---------------------------------------------------------------------------
# Webhook: ?apiKey=xxx query parameter (machine-to-machine, Jellyfin webhook)
# ---------------------------------------------------------------------------


async def verify_webhook_api_key(api_key: str = Query(..., alias="apiKey")):
    """Check that ?apiKey= query parameter matches the configured key."""
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")
    return api_key


# ---------------------------------------------------------------------------
# Bearer JWT for all user-facing routes
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """
    Validate a Bearer JWT and return the corresponding User ORM object.

    Import is deferred to avoid circular dependency between security ↔ auth_service ↔ models.
    """
    from app.db import SessionLocal
    from app.services.auth_service import decode_access_token, get_user_by_username

    token = credentials.credentials
    username = decode_access_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db = SessionLocal()
    try:
        user = get_user_by_username(db, username)
    finally:
        db.close()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
