"""Auth REST endpoints: register, login, refresh, logout, me.

Implements AUTH-01 (registration), AUTH-02 (login + JWT), AUTH-03 (refresh).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.api.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user with email and password (AUTH-01)."""
    user = await AuthService.register(db, data)
    return UserResponse.model_validate(user)


@router.post("/login")
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Authenticate and return JWT access + refresh tokens (AUTH-02)."""
    return await AuthService.login(db, redis, data)


@router.post("/refresh")
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """Rotate refresh token and issue a new token pair (AUTH-03)."""
    return await AuthService.refresh(db, redis, data)


@router.post("/logout")
async def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    """Invalidate the given refresh token."""
    await AuthService.logout(redis, str(current_user.id), data.refresh_token)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
