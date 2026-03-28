from __future__ import annotations

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.redis import KEY_PREFIX
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.user_service import create_user, get_by_email, get_by_id


def _refresh_token_key(user_id: str, jti: str) -> str:
    """Build the Redis key for a stored refresh token."""
    return f"{KEY_PREFIX}:refresh_token:{user_id}:{jti}"


def _refresh_ttl_seconds() -> int:
    """Return TTL in seconds matching the configured refresh token expiry."""
    return settings.refresh_token_expire_days * 24 * 60 * 60


class AuthService:
    """Business logic for registration, login, token refresh, and logout."""

    @staticmethod
    async def register(db: AsyncSession, data: RegisterRequest) -> "User":
        """Register a new user.

        Raises ConflictException if the email is already taken.
        """
        existing = await get_by_email(db, data.email)
        if existing is not None:
            raise ConflictException(message="EMAIL_EXISTS")

        hashed = hash_password(data.password)
        user = await create_user(
            db,
            email=data.email,
            hashed_password=hashed,
            display_name=data.display_name,
        )
        return user

    @staticmethod
    async def login(
        db: AsyncSession,
        redis: aioredis.Redis,
        data: LoginRequest,
    ) -> TokenResponse:
        """Authenticate a user and return a token pair.

        Uses DUMMY_HASH for timing-attack protection when the user does not
        exist (Pitfall 6).
        """
        user = await get_by_email(db, data.email)
        stored_hash = user.hashed_password if user else DUMMY_HASH

        if not verify_password(data.password, stored_hash) or user is None:
            raise UnauthorizedException(message="Invalid credentials")

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        # Decode only to extract jti -- we just created it so it is valid.
        payload = decode_token(refresh_token)
        key = _refresh_token_key(str(user.id), payload["jti"])
        await redis.setex(key, _refresh_ttl_seconds(), refresh_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    async def refresh(
        db: AsyncSession,
        redis: aioredis.Redis,
        data: RefreshRequest,
    ) -> TokenResponse:
        """Rotate a refresh token: validate the old one, issue a new pair.

        Raises UnauthorizedException if the token is invalid, expired, or
        has already been used (rotation).
        """
        try:
            payload = decode_token(data.refresh_token)
        except UnauthorizedException:
            raise UnauthorizedException(message="Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedException(message="Invalid token type")

        user_id = payload.get("sub")
        jti = payload.get("jti")
        if not user_id or not jti:
            raise UnauthorizedException(message="Invalid refresh token")

        # Check that the token is still stored in Redis (not already rotated).
        key = _refresh_token_key(user_id, jti)
        stored = await redis.get(key)
        if stored is None:
            raise UnauthorizedException(message="Refresh token has been revoked")

        # Invalidate the old refresh token (rotation per D-16).
        await redis.delete(key)

        # Verify the user still exists.
        user = await get_by_id(db, user_id)
        if user is None:
            raise UnauthorizedException(message="User not found")

        # Issue a new token pair.
        new_access = create_access_token(str(user.id))
        new_refresh = create_refresh_token(str(user.id))

        new_payload = decode_token(new_refresh)
        new_key = _refresh_token_key(str(user.id), new_payload["jti"])
        await redis.setex(new_key, _refresh_ttl_seconds(), new_refresh)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
        )

    @staticmethod
    async def logout(
        redis: aioredis.Redis,
        user_id: str,
        refresh_token: str | None = None,
    ) -> None:
        """Invalidate the given refresh token (if provided) in Redis."""
        if refresh_token is None:
            return

        try:
            payload = decode_token(refresh_token)
        except UnauthorizedException:
            return

        jti = payload.get("jti")
        if jti is None:
            return

        key = _refresh_token_key(user_id, jti)
        await redis.delete(key)
