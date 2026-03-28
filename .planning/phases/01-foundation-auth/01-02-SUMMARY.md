---
phase: 01-foundation-auth
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, asyncpg, postgresql, uuid, orm, migrations]

# Dependency graph
requires:
  - phase: 01-01
    provides: FastAPI app skeleton with async SQLAlchemy engine and session factory
provides:
  - Six SQLAlchemy 2.0 async models (users, conversations, agents, skills, mcp_servers, tools)
  - DeclarativeBase with TimestampMixin and TenantMixin for all models
  - Alembic async migration system with initial migration creating all tables
  - All tables created and verified in PostgreSQL
affects: [01-03, 02-agent-engine, 03-communication, 04-memory, 05-mcp-integration, 06-skill-system]

# Tech tracking
tech-stack:
  added: [sqlalchemy 2.0, alembic 1.16.5, asyncpg 0.31.0]
  patterns: [sqlalchemy-2.0-mapped-annotations, uuid-primary-keys, timestamp-mixin, tenant-mixin, alembic-async-migrations]

key-files:
  created:
    - backend/app/db/base.py
    - backend/app/models/__init__.py
    - backend/app/models/user.py
    - backend/app/models/conversation.py
    - backend/app/models/agent.py
    - backend/app/models/skill.py
    - backend/app/models/mcp_server.py
    - backend/app/models/tool.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/script.py.mako
    - backend/alembic/versions/2026_03_28_1528-1bdd250c71a4_create_initial_tables.py
  modified: []

key-decisions:
  - "Used async_engine_from_config with NullPool in Alembic env.py for clean migration connections"
  - "Alembic env.py imports from app.models (triggers all model registrations with Base.metadata)"

patterns-established:
  - "Model pattern: Every model inherits TimestampMixin + TenantMixin + Base, uses Mapped[type] annotations, UUID PK with uuid.uuid4 default"
  - "Migration pattern: Async Alembic with asyncio.run(), env.py reads database_url from pydantic-settings"
  - "Foreign key pattern: conversations.user_id and agents.user_id reference users.id with indexed FK columns"

requirements-completed: [AUTH-05]

# Metrics
duration: 8min
completed: 2026-03-28
---

# Phase 1 Plan 02: Database Models & Alembic Migrations Summary

**SQLAlchemy 2.0 async models for all six core tables with UUID PKs, timestamp/tenant mixins, and Alembic async migration system that creates tables in PostgreSQL**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-28T15:22:39Z
- **Completed:** 2026-03-28T15:30:44Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- All six SQLAlchemy models defined with correct columns per D-07, UUID PKs per D-08, tenant_id per D-09
- Alembic configured for async migrations with asyncpg (avoids Pitfall 5 from RESEARCH.md)
- Initial migration auto-generated and applied successfully -- all tables verified in PostgreSQL
- DeclarativeBase with reusable TimestampMixin and TenantMixin for future model additions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create declarative base, timestamp mixin, and all six SQLAlchemy models** - `fea87dc` (feat)
2. **Task 2: Configure Alembic for async migrations and create initial migration** - `de8fc26` (feat)

## Files Created/Modified
- `backend/app/db/base.py` - DeclarativeBase, TimestampMixin (created_at, updated_at), TenantMixin (tenant_id)
- `backend/app/models/__init__.py` - Central import point for all models (enables Alembic auto-generation)
- `backend/app/models/user.py` - User model with email (unique, indexed), hashed_password, display_name, avatar_url, role
- `backend/app/models/conversation.py` - Conversation model with user_id FK, title, is_archived
- `backend/app/models/agent.py` - Agent model with user_id FK, name, system_prompt, model_config (JSON)
- `backend/app/models/skill.py` - Skill model with name (unique), description, manifest (JSON), status
- `backend/app/models/mcp_server.py` - MCPServer model with name, url, transport_type, config (JSON), status
- `backend/app/models/tool.py` - Tool model with name, source_type, source_id, schema (JSON)
- `backend/alembic.ini` - Alembic configuration with UTC timezone, async-compatible settings
- `backend/alembic/env.py` - Async Alembic environment using async_engine_from_config + asyncio.run()
- `backend/alembic/script.py.mako` - Standard Alembic migration template
- `backend/alembic/versions/.gitkeep` - Placeholder for versions directory
- `backend/alembic/versions/2026_03_28_1528-1bdd250c71a4_create_initial_tables.py` - Initial migration creating all six tables

## Decisions Made
- **async_engine_from_config with NullPool**: Used Alembic's `async_engine_from_config` helper with `poolclass=pool.NullPool` for clean migration connections that don't hold pool connections
- **env.py reads settings from pydantic-settings**: Database URL comes from `app.core.config.settings` via `config.set_main_option`, keeping all configuration in one place

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - Docker Compose provides all infrastructure. Alembic migrations applied automatically.

## Next Phase Readiness
- All six database tables created and verified in PostgreSQL
- SQLAlchemy models ready for use in Plan 03 (auth service, user CRUD, JWT endpoints)
- User model has email and hashed_password fields ready for auth integration
- Alembic migration system ready for future schema changes (add columns, new tables)
- conversations, agents, skills, mcp_servers, tools tables ready for their respective phases

## Self-Check: PASSED

- All 13 created files verified present on disk
- Both task commits verified in git log (fea87dc, de8fc26)

---
*Phase: 01-foundation-auth*
*Completed: 2026-03-28*
