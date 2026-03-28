import redis.asyncio as aioredis
from fastapi import Request

KEY_PREFIX = "nextflow"


def get_redis(request: Request) -> aioredis.Redis:
    """Get the Redis client from application state.

    The Redis connection pool is initialized during app lifespan startup
    and stored on app.state.redis.
    """
    return request.app.state.redis
