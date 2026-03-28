from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


# ---------------------------------------------------------------------------
# Test database engine (uses the same Postgres but creates/drops tables per session)
# ---------------------------------------------------------------------------
test_engine = create_async_engine(settings.database_url, echo=False)
TestSessionFactory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_database():
    """Create all tables once per test session, drop them when done."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh database session that rolls back after each test."""
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide a Redis client on db=1, flushed after each test."""
    r = aioredis.from_url(
        settings.redis_url.replace("/0", "/1"),
        decode_responses=True,
    )
    yield r
    await r.flushdb()
    await r.close()


@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession,
    test_redis: aioredis.Redis,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient wired to the FastAPI app with overridden deps."""

    async def _override_get_db():
        yield db_session

    def _override_get_redis():
        return test_redis

    app.dependency_overrides[get_db] = _override_get_db
    from app.db.redis import get_redis

    app.dependency_overrides[get_redis] = _override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(async_client: AsyncClient) -> dict:
    """Create a test user via the registration endpoint and return its JSON data."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "securepassword123",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 201
    return response.json()
