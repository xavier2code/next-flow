from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

ALGORITHM = settings.jwt_algorithm

password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypasswordfortimingattackprotection")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return password_hash.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """Create a JWT access token with the given subject (user ID).

    Includes a 'type' claim set to 'access' and an expiry based on settings.
    """
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "type": "access",
        "exp": expires,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token with the given subject (user ID).

    Includes a 'type' claim set to 'refresh', a unique JTI, and an expiry
    based on settings.
    """
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expires,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Raises UnauthorizedException if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[ALGORITHM]
        )
        return payload
    except InvalidTokenError as exc:
        raise UnauthorizedException(message="Invalid or expired token") from exc
