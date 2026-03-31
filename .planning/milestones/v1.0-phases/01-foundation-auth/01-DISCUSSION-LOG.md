# Phase 1: Foundation & Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 01-foundation-auth
**Areas discussed:** Project Structure, Database Schema, Authentication, Configuration

---

## Project Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Modular layered (api/core/models/schemas/services/db) | Clear separation of concerns, scalable | ✓ |
| Flat structure | All files in single app directory | |
| Domain-driven modules | Group by feature (auth/, conversations/, etc.) | |

**User's choice:** Modular layered (auto — recommended default)
**Notes:** Aligns with user's architecture document Section 4.2 layered design

---

## Database Schema

| Option | Description | Selected |
|--------|-------------|----------|
| SQLAlchemy 2.0 async with UUID PKs | Modern async ORM, UUID avoids enumeration | ✓ |
| SQLAlchemy 2.0 async with integer PKs | Simpler, standard | |
| Tortoise ORM | Django-like async ORM | |
| SQLModel | Pydantic+SQLAlchemy hybrid | |

**User's choice:** SQLAlchemy 2.0 async with UUID PKs (auto — recommended)
**Notes:** SQLAlchemy is the standard for FastAPI projects, async is required for non-blocking I/O

---

## Authentication

| Option | Description | Selected |
|--------|-------------|----------|
| JWT access + refresh token rotation | Stateless, scalable, standard for SPAs | ✓ |
| Session-based (server-side) | Simpler but requires sticky sessions | |
| OAuth 2.0 + PKCE only | Redirect flow, more complex | |

**User's choice:** JWT access + refresh token rotation (auto — recommended)
**Notes:** Per user's design document Section 8.1, JWT + RBAC is specified

---

## Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic Settings with .env | Type-safe config, env file support | ✓ |
| python-dotenv + os.environ | Simpler, less structured | |
| Dynaconf | Feature-rich but overkill | |

**User's choice:** Pydantic Settings with .env (auto — recommended)
**Notes:** Standard pattern for FastAPI, provides validation and type safety

---

## Claude's Discretion

- Exact Alembic migration file names and order
- Docker Compose service definitions
- Health check endpoint details
- CORS middleware configuration
- Logging format details

## Deferred Ideas

- RBAC enforcement logic — later phases
- Celery worker setup — Phase 3+
- MinIO setup — Phase 6
- API gateway — production deployment
