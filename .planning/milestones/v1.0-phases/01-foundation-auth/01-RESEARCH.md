# Phase 1: Foundation & Auth - Research

**Researched:** 2026-03-28
**Domain:** FastAPI project skeleton, SQLAlchemy async ORM, PostgreSQL schema design, Redis integration, JWT authentication, structured logging
**Confidence:** HIGH

## Summary

Phase 1 establishes the entire backend foundation for NextFlow: project structure, database schema, Redis integration, JWT authentication, and configuration management. This phase has no external dependencies beyond Docker containers for PostgreSQL and Redis, both of which are provided via `docker-compose.yml`.

The core technical challenge is getting three infrastructure pieces (FastAPI async skeleton, SQLAlchemy 2.0 async with PostgreSQL, Redis async client) working together with a clean layered architecture that all subsequent phases can build upon. The auth system uses JWT access/refresh tokens with rotation, following patterns now recommended by the official FastAPI documentation.

**Critical discovery during research:** The CONTEXT.md specifies `python-jose` for JWT and `passlib` for password hashing (decision D-15). Both libraries are now effectively unmaintained. The official FastAPI documentation has switched to **PyJWT** and **pwdlib[argon2]**. This research recommends overriding D-15 to use the current best practice. See Open Questions section.

**Primary recommendation:** Use FastAPI 0.135.x with PyJWT + pwdlib[argon2] for auth, SQLAlchemy 2.0 async with asyncpg, Alembic for migrations, pydantic-settings for config, and structlog for logging. Follow the official FastAPI OAuth2/JWT tutorial pattern as the auth reference implementation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Modular layered structure -- `backend/app/api/` (routes), `backend/app/core/` (config, security), `backend/app/models/` (SQLAlchemy), `backend/app/schemas/` (Pydantic), `backend/app/services/` (business logic), `backend/app/db/` (session, migrations)
- **D-02:** Alembic for database migrations -- standard for SQLAlchemy, supports auto-generation
- **D-03:** Python 3.11+ with uv/poetry for dependency management
- **D-04:** Frontend scaffold as separate `frontend/` directory (Vite + React + TypeScript + shadcn/ui + Zustand)
- **D-05:** SQLAlchemy 2.0 async with `AsyncSession` and `create_async_engine` -- async-native for FastAPI
- **D-06:** PostgreSQL with asyncpg driver
- **D-07:** Core tables: `users`, `conversations`, `agents`, `skills`, `mcp_servers`, `tools` (with specific column definitions)
- **D-08:** UUID primary keys for all tables
- **D-09:** Include `tenant_id` nullable column on all tables (design for future multi-tenancy, not enforced in v1)
- **D-10:** Redis for session storage, rate limiting, and short-term cache
- **D-11:** Use `redis.asyncio` for async Redis client
- **D-12:** Key naming convention: `nextflow:{domain}:{key}`
- **D-13:** JWT access tokens (short-lived, 15 min) + refresh tokens (longer-lived, 7 days)
- **D-14:** Bearer token in Authorization header -- frontend stores in memory (not localStorage), refreshes proactively before expiry
- **D-15:** python-jose for JWT encoding/decoding, passlib with bcrypt for password hashing
- **D-16:** Refresh token rotation -- new refresh token issued on each refresh, old one invalidated
- **D-17:** Password requirements: minimum 8 characters, no complexity rules (follow NIST guidelines)
- **D-18:** Standard REST auth endpoints: POST /auth/register, POST /auth/login, POST /auth/refresh, POST /auth/logout
- **D-19:** Pydantic Settings (`pydantic-settings`) with `.env` file support
- **D-20:** Settings model: database URL, Redis URL, JWT secret/key, LLM API keys, CORS origins, log level
- **D-21:** Structured logging with `structlog` -- JSON output in production, human-readable in dev
- **D-22:** Global exception handlers on FastAPI app -- consistent JSON error response format

### Claude's Discretion
- Exact Alembic migration file names and order
- Docker Compose service definitions for PostgreSQL, Redis, MinIO
- Health check endpoint implementation details
- CORS middleware configuration specifics
- Logging format details

### Deferred Ideas (OUT OF SCOPE)
- RBAC role enforcement logic -- Phase 2+ (create roles table now, enforce in later phases)
- Celery task queue setup -- Phase 3+ (Redis broker configured now, Celery workers later)
- MinIO object storage setup -- Phase 6 (Skill System)
- API gateway / load balancer configuration -- production deployment concern
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | User can sign up with email and password | PyJWT + pwdlib[argon2] pattern from FastAPI official docs. Pydantic schemas for registration request/response. SQLAlchemy User model with hashed_password field. |
| AUTH-02 | User can log in and receive JWT token with refresh mechanism | JWT access token (15 min) + refresh token (7 days) with rotation. Token stored in-memory on frontend. Standard auth endpoints pattern. |
| AUTH-03 | User session persists across browser refresh via token refresh | Refresh token rotation (D-16), proactive refresh before expiry (D-14). Redis for refresh token storage and validation. |
| AUTH-04 | FastAPI project skeleton with config management, logging, and error handling | Modular layered structure (D-01). pydantic-settings (D-19/D-20). structlog (D-21). Global exception handlers (D-22). |
| AUTH-05 | PostgreSQL schema for users, conversations, agents, skills, mcp_servers, tools | SQLAlchemy 2.0 async models (D-05/D-07). UUID PKs (D-08). tenant_id columns (D-09). Alembic migrations (D-02). |
| AUTH-06 | Redis setup for session store and cache | redis.asyncio (D-11). Key naming convention (D-12). Docker Compose service. Connection verification. |
</phase_requirements>

## Standard Stack

### Core (Phase 1 Required)
| Library | Version | Purpose | Why Standard | Confidence |
|---------|---------|---------|--------------|------------|
| FastAPI | 0.135.2 | API framework, routing, middleware | Async-native, Pydantic v2 validation, auto OpenAPI docs. v0.135.x adds Starlette 1.0 support. | HIGH |
| PyJWT | 2.12.1 | JWT encoding/decoding | **Overrides D-15.** Official FastAPI docs now recommend PyJWT over python-jose (which is unmaintained). Actively maintained, focused JWT library. | HIGH |
| pwdlib[argon2] | 0.2.1 | Password hashing | **Overrides D-15.** Official FastAPI docs now recommend pwdlib over passlib (which is unmaintained). Uses Argon2id, the PHC winner. | HIGH |
| SQLAlchemy | 2.0.48 | Async ORM | Async support via `sqlalchemy[asyncio]` + asyncpg. Declarative models with Mapped column annotations. | HIGH |
| asyncpg | 0.31.0 | Async PostgreSQL driver | Direct async DB access. Faster than psycopg2 for concurrent queries. Required by SQLAlchemy async. | HIGH |
| Alembic | 1.16.5 | Database migrations | Standard for SQLAlchemy projects. Auto-generates migration scripts from model changes. | HIGH |
| pydantic-settings | 2.11.0 | Configuration management | `BaseSettings` with `.env` file support. Separate package from pydantic since v2. | HIGH |
| structlog | 25.5.0 | Structured logging | JSON-formatted logs for production, human-readable in dev. Correlation IDs, request tracing. | HIGH |
| redis | 7.0.1 | Async Redis client | `redis.asyncio` for cache, session store. aioredis merged into redis-py. | HIGH |
| uvicorn[standard] | 0.39.0 | ASGI server | FastAPI runtime. `--workers` for multi-process. Standard production setup. | HIGH |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1 | Async HTTP client (for testing) | Test client for FastAPI endpoints. Supports async in tests. | HIGH |
| pytest | 8.4.2 | Test framework | All backend tests. Async support via pytest-asyncio. | HIGH |
| pytest-asyncio | 1.2.0 | Async test support | Required for testing async FastAPI endpoints and SQLAlchemy sessions. | HIGH |
| argon2-cffi | 25.1.0 | Argon2 password hashing backend | Used by pwdlib[argon2]. Winner of Password Hashing Competition. | HIGH |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose | python-jose has JWS/JWE/JWK support but is unmaintained since 2022. PyJWT is actively maintained and sufficient for JWT-only use. Only consider python-jose if JWE encryption is needed. |
| pwdlib[argon2] | passlib[bcrypt] | passlib is unmaintained and breaks with bcrypt >= 4.1. pwdlib is the FastAPI official recommendation. Argon2id is the PHC winner over bcrypt. |
| pwdlib[argon2] | bcrypt direct | Using bcrypt directly is simpler but pwdlib provides a cleaner abstraction and supports migration from other hash formats. |

**Installation:**
```bash
# Core framework
pip install "fastapi>=0.135.0,<0.136.0" "uvicorn[standard]>=0.34.0"
pip install "sqlalchemy[asyncio]>=2.0.0" asyncpg alembic
pip install redis pydantic-settings structlog

# Authentication (overrides D-15 -- see Open Questions)
pip install "pyjwt[crypto]>=2.10.0" "pwdlib[argon2]>=0.2.0"

# Testing
pip install pytest pytest-asyncio httpx
```

**Version verification (2026-03-28):**
```
fastapi       0.135.2  (PyPI confirmed via WebSearch)
pyjwt         2.12.1   (pip index)
pwdlib        0.2.1    (pip index)
sqlalchemy    2.0.48   (pip index)
asyncpg       0.31.0   (pip index)
alembic       1.16.5   (pip index)
pydantic-settings 2.11.0 (pip index)
structlog     25.5.0   (pip index)
redis         7.0.1    (pip index)
uvicorn       0.39.0   (pip index)
pytest        8.4.2    (pip index)
pytest-asyncio 1.2.0   (pip index)
httpx         0.28.1   (pip index)
argon2-cffi   25.1.0   (pip index)
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, lifespan, middleware
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py          # Shared dependencies (get_db, get_current_user)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py    # Aggregated v1 router
│   │       ├── auth.py      # POST /auth/register, /login, /refresh, /logout
│   │       └── health.py    # GET /health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings via pydantic-settings
│   │   ├── security.py      # JWT encode/decode, password hashing
│   │   └── logging.py       # structlog configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py       # async engine, AsyncSession factory
│   │   └── base.py          # Declarative base, common mixins
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── agent.py
│   │   ├── skill.py
│   │   ├── mcp_server.py
│   │   └── tool.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py          # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── user.py          # UserResponse, UserCreate
│   │   └── error.py         # ErrorResponse
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py  # Auth business logic
│       └── user_service.py  # User CRUD
├── alembic/
│   ├── env.py
│   └── versions/
├── alembic.ini
├── pyproject.toml
├── requirements.txt
└── Dockerfile
```

### Pattern 1: FastAPI App Factory with Lifespan
**What:** Use FastAPI's `lifespan` context manager to initialize and teardown resources (DB engine, Redis pool) at startup/shutdown.
**When to use:** Every FastAPI application -- this replaces the deprecated `on_event("startup")` / `on_event("shutdown")`.
**Example:**
```python
# Source: FastAPI official docs - Advanced User Guide / Lifespan
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.session import engine, async_session_factory
from app.core.config import settings
import redis.asyncio as aioredis

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True
    )
    yield
    # Shutdown
    await app.state.redis.close()
    await engine.dispose()

app = FastAPI(
    title="NextFlow API",
    version="0.1.0",
    lifespan=lifespan,
)
```

### Pattern 2: AsyncSession Dependency Injection
**What:** Use FastAPI's `Depends()` to inject an async SQLAlchemy session into each route handler. Each request gets its own session with automatic commit/rollback.
**When to use:** Every route that accesses the database.
**Example:**
```python
# Source: SQLAlchemy 2.0 docs + FastAPI patterns
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# In routes:
@router.post("/auth/register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    ...
```

### Pattern 3: JWT Auth with PyJWT (Official FastAPI Pattern)
**What:** Use PyJWT to encode/decode JWT tokens. OAuth2PasswordBearer for token extraction. Dependency chain for current user resolution.
**When to use:** All protected endpoints.
**Example:**
```python
# Source: FastAPI official docs - OAuth2 with JWT
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = await user_service.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user
```

### Pattern 4: SQLAlchemy 2.0 Declarative Models with Mapped Annotations
**What:** Use `Mapped[type]` column annotations for type-safe ORM models. UUID primary keys. Timestamp mixin for created_at/updated_at.
**When to use:** All database models.
**Example:**
```python
# Source: SQLAlchemy 2.0 documentation
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(20), default="user")
    tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)
```

### Pattern 5: Refresh Token Storage in Redis with Rotation
**What:** Store refresh tokens in Redis with TTL matching token expiry. On refresh, delete old token and create new one. This prevents replay attacks.
**When to use:** Token refresh endpoint.
**Example:**
```python
# Store refresh token in Redis
async def store_refresh_token(redis: aioredis.Redis, user_id: str, token: str, ttl: int):
    key = f"nextflow:refresh_token:{user_id}:{hash(token)}"
    await redis.setex(key, ttl, token)

async def validate_and_rotate_refresh_token(
    redis: aioredis.Redis, user_id: str, old_token: str
) -> bool:
    key = f"nextflow:refresh_token:{user_id}:{hash(old_token)}"
    stored = await redis.get(key)
    if stored is None:
        return False  # Token already used or expired
    await redis.delete(key)  # Invalidate old token (rotation)
    return True
```

### Pattern 6: pydantic-settings Configuration
**What:** Use `pydantic_settings.BaseSettings` with `.env` file support for all configuration. Single settings instance cached as a module-level variable.
**When to use:** Application configuration everywhere.
**Example:**
```python
# Source: pydantic-settings official docs + FastAPI advanced settings guide
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://nextflow:nextflow@localhost:5432/nextflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # App
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

settings = Settings()
```

### Anti-Patterns to Avoid
- **Sync ORM in async framework:** Never use synchronous SQLAlchemy `Session` in FastAPI. Always use `AsyncSession`. This blocks the event loop and kills performance under load (Pitfall 12 from PITFALLS.md).
- **JWT secret in source code:** Never hardcode the JWT secret. Use pydantic-settings to load from environment variables or `.env` files.
- **Storing JWT in localStorage:** The frontend must store tokens in memory only (D-14). localStorage is vulnerable to XSS attacks.
- **Monolithic settings model:** Keep settings focused. Do not load LLM API keys or other secrets into the frontend bundle.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | pwdlib[argon2] | Argon2id has specific parameter requirements (memory, time, parallelism). pwdlib handles this correctly. |
| JWT encoding/decoding | Custom token implementation | PyJWT | JWT has specific header/payload/signature structure. PyJWT handles all algorithms, expiry, and verification. |
| Database migrations | Manual SQL scripts | Alembic | Alembic auto-generates migrations from model diffs, handles upgrade/downgrade, and tracks applied migrations. |
| Configuration management | Custom .env parser | pydantic-settings | Handles type coercion, validation, environment variable overrides, and nested settings. |
| CORS handling | Custom middleware | FastAPI CORSMiddleware | Built-in middleware handles preflight requests, header whitelisting, and origin matching. |
| Request validation | Manual validation code | Pydantic BaseModel | Automatic type validation, error messages, and OpenAPI schema generation. |
| Async Redis client | Custom connection pool | redis.asyncio | Built-in connection pooling, retry logic, pub/sub support. aioredis is merged into redis-py. |

**Key insight:** The FastAPI + SQLAlchemy 2.0 + Pydantic v2 ecosystem is mature and cohesive. Every piece mentioned above has production-grade documentation and community validation. There is no reason to build custom solutions for any of these concerns.

## Common Pitfalls

### Pitfall 1: Using Unmaintained Auth Libraries (D-15 Override Required)
**What goes wrong:** `python-jose` (D-15) is effectively unmaintained since 2022. `passlib` has not received meaningful updates and breaks with `bcrypt >= 4.1` (the `about` attribute was removed). Using these libraries introduces security risks and compatibility issues.
**Why it happens:** Both libraries were the standard recommendation in older FastAPI tutorials. Many project templates and documentation still reference them.
**How to avoid:** Use **PyJWT** for JWT and **pwdlib[argon2]** for password hashing, as recommended by the current official FastAPI documentation. These are actively maintained and follow current security best practices.
**Warning signs:** `AttributeError: module 'bcrypt' has no attribute 'about'` when using passlib with modern bcrypt. Missing security patches in python-jose.

### Pitfall 2: JWT Token Refresh Race Condition (PITFALLS.md #15)
**What goes wrong:** When an access token expires, multiple concurrent requests may each trigger a refresh simultaneously. The first refresh succeeds, but subsequent ones fail because the old refresh token has already been used (rotation invalidates it). This causes some requests to return 401 errors, and the WebSocket connection may drop.
**Why it happens:** No mutex or deduplication mechanism on the frontend. Each tab or concurrent request independently detects expiry and attempts refresh.
**How to avoid:** (1) Refresh proactively before expiry (e.g., at 80% of token lifetime). (2) Implement a refresh mutex on the frontend -- only one refresh request at a time, with other requests queuing behind it. (3) Use the `type` claim in JWT to distinguish access vs refresh tokens.
**Warning signs:** Intermittent 401 errors when multiple tabs are open. Users logged out after background tab triggers refresh.

### Pitfall 3: Sync Blocking in Async Endpoints (PITFALLS.md #12)
**What goes wrong:** Calling synchronous methods (e.g., `session.execute()` without `await`) inside `async def` FastAPI endpoints blocks the event loop. Under concurrent load, all async request handlers stall.
**Why it happens:** Forgetting `await` on async methods, or using sync-only libraries inside async handlers.
**How to avoid:** Always use `await` with async SQLAlchemy methods. Use `await session.execute()`, `await session.commit()`, etc. If a sync-only library must be used, wrap it in `asyncio.to_thread()`.
**Warning signs:** Request latency increases linearly with concurrent users. Event loop blocking visible in profiling.

### Pitfall 4: SQLAlchemy AsyncSession Not Properly Scoped
**What goes wrong:** Sharing a single `AsyncSession` across requests, or not closing sessions after use. This leads to stale data, connection leaks, and "session is closed" errors.
**Why it happens:** Misunderstanding SQLAlchemy session lifecycle in async context. Not using dependency injection properly.
**How to avoid:** Each request gets its own session via `Depends(get_db)`. Use `async with async_session_factory() as session:` pattern. Ensure commit/rollback in the dependency, not in individual routes.
**Warning signs:** Stale reads, connection pool exhaustion, `DetachedInstanceError`.

### Pitfall 5: Alembic Async Migration Configuration
**What goes wrong:** Alembic's `env.py` uses synchronous database operations by default. With asyncpg, migrations fail because the sync driver is not installed.
**Why it happens:** Alembic does not auto-configure for async. The `env.py` must be manually configured to use `run_async_migrations`.
**How to avoid:** Configure `alembic/env.py` with `connectable = create_async_engine(url)` and use `asyncio.run(do_run_migrations())` pattern. See Alembic async cookbook.
**Warning signs:** `ImportError: No module named 'psycopg2'` during `alembic upgrade head`.

### Pitfall 6: Missing Timing Attack Protection on Login
**What goes wrong:** Login endpoint responds faster for non-existent users than for existing users with wrong passwords, allowing user enumeration.
**Why it happens:** The endpoint returns early when the user is not found, skipping the password hash verification step.
**How to avoid:** Always run `verify_password` even for non-existent users, using a dummy hash. This is shown in the official FastAPI OAuth2 tutorial: `DUMMY_HASH = password_hash.hash("dummypassword")`.
**Warning signs:** Login response time varies based on whether the username exists.

### Pitfall 7: Python Version Mismatch
**What goes wrong:** Developing with Python 3.9 (system default on macOS) when the project targets 3.12+. Syntax like `str | None`, `match/case`, and some type hints are unavailable in 3.9.
**Why it happens:** macOS ships with Python 3.9. Without explicit version management, developers use the system Python.
**How to avoid:** Use `uv` or `pyenv` to manage Python 3.12+. Pin the version in `pyproject.toml` (`requires-python = ">=3.12"`). Add a CI check for Python version.
**Warning signs:** `SyntaxError` on union type syntax (`X | Y`), `TypeError` on new 3.10+ features.

## Code Examples

Verified patterns from official sources:

### JWT Token Creation and Verification (PyJWT)
```python
# Source: FastAPI official docs - OAuth2 with JWT
# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError

def create_access_token(data: dict, secret_key: str, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm="HS256")

def decode_token(token: str, secret_key: str) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Password Hashing (pwdlib with Argon2)
```python
# Source: FastAPI official docs - OAuth2 with JWT
# https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
DUMMY_HASH = password_hash.hash("dummypassword")

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
```

### SQLAlchemy Async Engine and Session Factory
```python
# Source: SQLAlchemy 2.0 docs - Async Session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### Redis Async Client Setup
```python
# Source: redis-py documentation
import redis.asyncio as aioredis
from app.core.config import settings

async def create_redis_pool() -> aioredis.Redis:
    return aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )
```

### Global Exception Handlers
```python
# Source: FastAPI docs - Custom Exception Handlers
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose | PyJWT | FastAPI docs switched ~2025 | python-jose is unmaintained. PyJWT is actively maintained. |
| passlib[bcrypt] | pwdlib[argon2] | FastAPI docs switched ~2025 | passlib is unmaintained, breaks with bcrypt >= 4.1. Argon2id is PHC winner. |
| `on_event("startup")` | `lifespan` context manager | FastAPI 0.100+ | `on_event` is deprecated. Lifespan is the official pattern. |
| Sync SQLAlchemy Session | AsyncSession with asyncpg | SQLAlchemy 2.0 (2023) | Required for async FastAPI. Different query patterns. |
| `tailwind.config.js` | CSS-native `@theme` | TailwindCSS 4.x | Not relevant for Phase 1, but note for frontend scaffold. |
| aioredis (separate package) | redis.asyncio (merged) | redis-py 4.2+ | `redis.asyncio` is the async interface. No separate install needed. |

**Deprecated/outdated:**
- `python-jose`: Unmaintained since ~2022. FastAPI docs now use PyJWT. Do NOT use despite D-15.
- `passlib`: Unmaintained, breaks with modern bcrypt. FastAPI docs now use pwdlib. Do NOT use despite D-15.
- `on_event("startup"/"shutdown")`: Deprecated in FastAPI. Use `lifespan` context manager instead.
- Sync SQLAlchemy `Session`: Do not use with FastAPI async endpoints. Use `AsyncSession`.

## Open Questions

1. **D-15 Override: python-jose/passlib vs PyJWT/pwdlib**
   - What we know: `python-jose` is unmaintained (last meaningful release ~2022). `passlib` is unmaintained and breaks with `bcrypt >= 4.1`. The **official FastAPI documentation** now recommends PyJWT + pwdlib[argon2]. This is the current community consensus (confirmed by FastAPI GitHub Discussions #11345, #9587).
   - What's unclear: Whether the user is aware of this change and whether D-15 was specified intentionally or based on outdated documentation.
   - Recommendation: **Override D-15. Use PyJWT + pwdlib[argon2].** This is what the official FastAPI documentation recommends as of 2026. The old libraries are security liabilities. The planner should proceed with PyJWT + pwdlib and note the override.

2. **Python Version on Development Machine**
   - What we know: The local machine runs Python 3.9.6 (macOS system Python). The project requires 3.12+ (D-03, and LangGraph requires >= 3.10). Python 3.12 features like `str | None` union syntax and `match/case` will fail on 3.9.
   - What's unclear: Whether `uv` or `pyenv` is installed for version management.
   - Recommendation: The planner should include a task to set up Python 3.12+ via `uv` or `pyenv` before any backend code is written. Pin `requires-python = ">=3.12"` in `pyproject.toml`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Backend runtime | PARTIAL | 3.9.6 system, needs install | Use uv/pyenv to install 3.12 |
| Node.js 22 LTS | Frontend scaffold | Available | 25.8.1 (newer than needed) | -- |
| npm | Frontend tooling | Available | 11.12.0 | -- |
| Docker | PostgreSQL, Redis containers | Available | 29.3.1 | -- |
| PostgreSQL | Primary database | Via Docker | docker-compose | -- |
| Redis | Cache, session store | Via Docker | docker-compose | -- |
| uv/pyenv | Python version management | Not checked | -- | Install uv for version management |

**Missing dependencies with no fallback:**
- Python 3.12+ is NOT available at system level. Must install via `uv` or `pyenv` before backend work begins. This is a blocking dependency for task 1.

**Missing dependencies with fallback:**
- PostgreSQL and Redis are not running locally, but Docker Compose will provide them. The plan must include a task to create `docker-compose.yml` and run `docker compose up -d` before any database-dependent code.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio 1.2.0 |
| Config file | `pyproject.toml [tool.pytest.ini_options]` -- to be created |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | User registration with email/password | unit | `pytest tests/test_auth.py::test_register_success -x` | Wave 0 |
| AUTH-01 | Duplicate email registration fails | unit | `pytest tests/test_auth.py::test_register_duplicate_email -x` | Wave 0 |
| AUTH-01 | Password shorter than 8 chars rejected | unit | `pytest tests/test_auth.py::test_register_short_password -x` | Wave 0 |
| AUTH-02 | Login returns JWT access + refresh tokens | unit | `pytest tests/test_auth.py::test_login_success -x` | Wave 0 |
| AUTH-02 | Wrong password returns 401 | unit | `pytest tests/test_auth.py::test_login_wrong_password -x` | Wave 0 |
| AUTH-03 | Refresh token returns new access token | unit | `pytest tests/test_auth.py::test_refresh_token -x` | Wave 0 |
| AUTH-03 | Used refresh token is invalidated (rotation) | unit | `pytest tests/test_auth.py::test_refresh_token_rotation -x` | Wave 0 |
| AUTH-04 | Health check returns 200 | integration | `pytest tests/test_health.py::test_health_check -x` | Wave 0 |
| AUTH-04 | Error responses follow consistent format | unit | `pytest tests/test_error_handling.py -x` | Wave 0 |
| AUTH-05 | Database models create tables correctly | integration | `pytest tests/test_models.py -x` | Wave 0 |
| AUTH-06 | Redis set/get works | integration | `pytest tests/test_redis.py::test_redis_connection -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/__init__.py` -- test package marker
- [ ] `backend/tests/conftest.py` -- shared fixtures (async test client, test DB session, test Redis)
- [ ] `backend/tests/test_auth.py` -- covers AUTH-01, AUTH-02, AUTH-03
- [ ] `backend/tests/test_health.py` -- covers AUTH-04 (health check)
- [ ] `backend/tests/test_error_handling.py` -- covers AUTH-04 (error format)
- [ ] `backend/tests/test_models.py` -- covers AUTH-05 (schema)
- [ ] `backend/tests/test_redis.py` -- covers AUTH-06 (Redis)
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` -- if none detected

## Sources

### Primary (HIGH confidence)
- FastAPI official docs - OAuth2 with JWT: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ -- verified PyJWT + pwdlib[argon2] as current recommendation (fetched 2026-03-28)
- FastAPI official docs - Settings: https://fastapi.tiangolo.com/advanced/settings/ -- pydantic-settings configuration pattern
- PyPI - FastAPI: https://pypi.org/project/fastapi/ -- v0.135.2 confirmed (WebSearch 2026-03-28)
- PyPI - SQLAlchemy: https://pypi.org/project/sqlalchemy/ -- v2.0.48 (pip index 2026-03-28)
- PyPI - PyJWT: https://pypi.org/project/pyjwt/ -- v2.12.1 (pip index 2026-03-28)
- PyPI - pwdlib: https://pypi.org/project/pwdlib/ -- v0.2.1 (pip index 2026-03-28)
- PyPI - redis: https://pypi.org/project/redis/ -- v7.0.1 (pip index 2026-03-28)
- .planning/research/ARCHITECTURE.md -- component boundaries, build order
- .planning/research/PITFALLS.md -- Pitfall 12 (sync blocking), Pitfall 15 (JWT refresh race)

### Secondary (MEDIUM confidence)
- FastAPI GitHub Discussion #11345 -- "Time to Abandon python-jose Recommendation in Favour of PyJWT" (community consensus)
- FastAPI GitHub Discussion #9587 -- "Why python-jose is still recommended in the documentation" (historical context)
- Reddit r/FastAPI -- "Which JWT Library Do You Use for FastAPI and Why?" (community patterns)
- WorkOS 2026 Guide -- "Building Authentication in Python Web Applications" (recommends python-jose but acknowledges PyJWT trend)

### Tertiary (LOW confidence)
- Various blog posts on passlib/pwdlib migration patterns -- flagged for validation during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against PyPI on 2026-03-28
- Architecture: HIGH -- follows official FastAPI + SQLAlchemy 2.0 patterns documented in canonical references
- Pitfalls: HIGH -- python-jose/passlib unmaintained status confirmed by multiple sources including official FastAPI docs switch; JWT refresh race condition is well-documented
- Auth pattern: HIGH -- based on official FastAPI OAuth2/JWT tutorial (fetched and verified 2026-03-28)

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable ecosystem, 30-day window is conservative)

---

*Research for: Phase 1 - Foundation & Auth*
*NextFlow -- Universal Agent Platform*
