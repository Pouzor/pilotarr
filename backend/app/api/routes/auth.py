"""
Auth routes — login, me, change-password, logout.

All endpoints live under /api/auth.
- POST /api/auth/login          — public
- POST /api/auth/logout         — public
- GET  /api/auth/me             — cookie required
- POST /api/auth/change-password — cookie required
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    UserResponse,
)
from app.core.config import settings
from app.core.security import get_current_user
from app.db import get_db
from app.models.models import User
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=UserResponse)
async def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate and set an httpOnly session cookie."""
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(user.username)
    response.set_cookie(
        key="pilotarr_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )
    return UserResponse(username=user.username, is_active=user.is_active)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(key="pilotarr_token", httponly=True, samesite="lax")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserResponse(username=current_user.username, is_active=current_user.is_active)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the password for the authenticated user."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must be at least 8 characters",
        )
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    logger.info("Password changed for user '%s'", current_user.username)
