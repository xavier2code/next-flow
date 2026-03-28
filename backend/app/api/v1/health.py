from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import redis.asyncio as aioredis

from app.api.deps import get_redis

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
async def health_check(
    redis: aioredis.Redis = Depends(get_redis),
) -> JSONResponse:
    """Health check endpoint that verifies Redis connectivity."""
    try:
        await redis.ping()
        return JSONResponse(
            status_code=200,
            content={"status": "healthy", "redis": "connected"},
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "redis": "disconnected"},
        )
