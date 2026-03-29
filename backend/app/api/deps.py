"""Single import point for all route dependencies."""

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.services.tool_registry import ToolRegistry
from app.services.user_service import get_by_id

__all__ = ["get_db", "get_redis", "get_current_user", "get_tool_registry"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current authenticated user from the Authorization header."""
    from app.core.exceptions import UnauthorizedException

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type")
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException(message="Invalid token")
    user = await get_by_id(db, user_id)
    if user is None:
        raise UnauthorizedException(message="User not found")
    return user


def get_tool_registry(request: Request) -> ToolRegistry:
    """Retrieve the ToolRegistry instance from application state."""
    return request.app.state.tool_registry
