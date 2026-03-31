# Phase 1: Foundation & Auth - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Running backend skeleton with persistent storage, caching, and user authentication. This phase sets up the project structure, database schemas, Redis integration, and JWT-based auth system that all subsequent phases build upon. Requirements AUTH-01 through AUTH-06.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** Modular layered structure — `backend/app/api/` (routes), `backend/app/core/` (config, security), `backend/app/models/` (SQLAlchemy), `backend/app/schemas/` (Pydantic), `backend/app/services/` (business logic), `backend/app/db/` (session, migrations)
- **D-02:** Alembic for database migrations — standard for SQLAlchemy, supports auto-generation
- **D-03:** Python 3.11+ with uv/poetry for dependency management
- **D-04:** Frontend scaffold as separate `frontend/` directory (Vite + React + TypeScript + shadcn/ui + Zustand)

### Database Schema
- **D-05:** SQLAlchemy 2.0 async with `AsyncSession` and `create_async_engine` — async-native for FastAPI
- **D-06:** PostgreSQL with asyncpg driver
- **D-07:** Core tables: `users` (id, email, hashed_password, display_name, avatar_url, role, created_at, updated_at), `conversations` (id, user_id, title, created_at, updated_at), `agents` (id, user_id, name, system_prompt, model_config JSON, created_at), `skills` (id, name, description, manifest JSON, status, created_at), `mcp_servers` (id, name, url, transport_type, config JSON, status, created_at), `tools` (id, name, source_type, source_id, schema JSON, created_at)
- **D-08:** UUID primary keys for all tables — avoids ID enumeration, compatible with distributed systems
- **D-09:** Include `tenant_id` nullable column on all tables (design for future multi-tenancy, not enforced in v1)

### Redis Setup
- **D-10:** Redis for session storage, rate limiting, and short-term cache
- **D-11:** Use `redis.asyncio` (aioredis merged into redis-py) for async Redis client
- **D-12:** Key naming convention: `nextflow:{domain}:{key}` (e.g., `nextflow:session:{user_id}`)

### Authentication
- **D-13:** JWT access tokens (short-lived, 15 min) + refresh tokens (longer-lived, 7 days)
- **D-14:** Bearer token in Authorization header — frontend stores in memory (not localStorage), refreshes proactively before expiry
- **D-15:** python-jose for JWT encoding/decoding, passlib with bcrypt for password hashing
- **D-16:** Refresh token rotation — new refresh token issued on each refresh, old one invalidated
- **D-17:** Password requirements: minimum 8 characters, no complexity rules (follow NIST guidelines)
- **D-18:** Standard REST auth endpoints: POST /auth/register, POST /auth/login, POST /auth/refresh, POST /auth/logout

### Configuration
- **D-19:** Pydantic Settings (`pydantic-settings`) with `.env` file support
- **D-20:** Settings model: database URL, Redis URL, JWT secret/key, LLM API keys, CORS origins, log level

### Logging & Error Handling
- **D-21:** Structured logging with `structlog` — JSON output in production, human-readable in dev
- **D-22:** Global exception handlers on FastAPI app — validation errors, auth errors, internal errors all return consistent JSON error response format: `{"error": {"code": "ERROR_CODE", "message": "description"}}`

### Claude's Discretion
- Exact Alembic migration file names and order
- Docker Compose service definitions for PostgreSQL, Redis, MinIO
- Health check endpoint implementation details
- CORS middleware configuration specifics
- Logging format details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows, build order (Phase 1 details)
- `.planning/research/STACK.md` — Technology recommendations with versions and rationale
- `.planning/research/PITFALLS.md` — Pitfall 12 (FastAPI sync blocking), Pitfall 15 (JWT refresh race condition)
- `.planning/PROJECT.md` — Constraints, key decisions, tech stack specifications
- `.planning/REQUIREMENTS.md` — AUTH-01 through AUTH-06 acceptance criteria

### Technology Docs (verify versions during research)
- FastAPI documentation — project structure, dependency injection, middleware patterns
- SQLAlchemy 2.0 async documentation — async session, declarative models
- Alembic documentation — migration setup and auto-generation
- Pydantic Settings documentation — environment configuration

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project

### Established Patterns
- None — this phase establishes patterns for all subsequent phases

### Integration Points
- Database models created here will be extended by Phase 2 (Agent Engine adds AgentState checkpoint tables), Phase 4 (Memory adds vector collections), Phase 5 (MCP adds server/tool records), Phase 6 (Skills adds skill/tool records)
- Auth middleware protects all future API endpoints
- Redis client is reused by Phase 4 (short-term memory) and Phase 3 (WebSocket session management)
- Project structure conventions set here guide all future phases

</code_context>

<specifics>
## Specific Ideas

- Design follows architecture from user's provided design document (Section 4: Backend Architecture)
- Tech stack locked per PROJECT.md constraints: FastAPI, PostgreSQL, Redis, Celery+Redis
- Follow layered design: Interface → Application → Core Service → Infrastructure
- JWT + RBAC auth as specified in user's design document Section 8.1

</specifics>

<deferred>
## Deferred Ideas

- RBAC role enforcement logic — Phase 2+ (create roles table now, enforce in later phases)
- Celery task queue setup — Phase 3+ (Redis broker configured now, Celery workers later)
- MinIO object storage setup — Phase 6 (Skill System)
- API gateway / load balancer configuration — production deployment concern

</deferred>

---
*Phase: 01-foundation-auth*
*Context gathered: 2026-03-28*
