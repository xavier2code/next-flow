---
phase: 08-backend-containerization
plan: 01
subsystem: backend
tags: [docker, containerization, production, gunicorn]
dependency_graph:
  requires: [v1.0-complete]
  provides: [nextflow-backend-docker-image]
  affects: [backend]
tech_stack:
  added: [gunicorn-25.3.0, python:3.12-slim-bookworm-docker-image]
  patterns: [multi-stage-docker-build, uv-sync-frozen, non-root-container, healthcheck]
key_files:
  created:
    - backend/Dockerfile
    - backend/.dockerignore
    - backend/gunicorn.conf.py
    - backend/entrypoint.sh
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - python:3.12-slim-bookworm over Alpine for asyncpg/cryptography wheel compatibility
  - uv sync --frozen for reproducible Docker builds from existing uv.lock
  - Gunicorn + UvicornWorker for production process management with graceful shutdown
  - Multi-stage build to exclude build tools from final runtime image
metrics:
  duration: 58m
  completed: 2026-03-31
  tasks: 5
  files_created: 4
  files_modified: 2
---

# Phase 08 Plan 01: Backend Dockerfile and .dockerignore Summary

Multi-stage Docker build packaging FastAPI backend with Gunicorn+UvicornWorker, non-root user, automatic Alembic migrations, and HEALTHCHECK against /api/v1/health.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add gunicorn dependency to pyproject.toml | 4d5ec69 | backend/pyproject.toml, backend/uv.lock |
| 2 | Create backend/.dockerignore | e2e42e8 | backend/.dockerignore |
| 3 | Create backend/gunicorn.conf.py | ecb8528 | backend/gunicorn.conf.py |
| 4 | Create backend/entrypoint.sh | 02ec825 | backend/entrypoint.sh |
| 5 | Create backend/Dockerfile and verify the build | 4d21ee4 | backend/Dockerfile |

## Key Decisions

1. **python:3.12-slim-bookworm**: Chosen over Alpine because asyncpg, psycopg, and cryptography lack musl wheels, requiring compilation from source on Alpine which increases build time and image complexity.
2. **uv sync --frozen**: Uses the existing uv.lock for exact version pinning. Reproducible builds with no floating dependencies.
3. **Gunicorn + UvicornWorker**: Production process manager handling multi-worker concurrency, graceful shutdown (120s timeout), and memory leak prevention (max_requests=5000 with jitter).
4. **Multi-stage build**: Builder stage installs all dependencies via uv. Runtime stage only receives the .venv and application code. Final image is 521MB.
5. **Non-root user (nextflow, UID 999)**: Security hardening. Application writes only to /app/data.

## Verification Results

- Docker image `nextflow-backend` builds successfully (521MB)
- Container runs as `uid=999(nextflow)` (non-root)
- Gunicorn 25.3.0 installed and importable
- Alembic 1.18.4 available for migration execution
- HEALTHCHECK configured: `curl -f http://localhost:8000/api/v1/health` with 30s interval, 10s timeout, 30s start-period, 3 retries
- .dockerignore excludes .venv, __pycache__, .env, .pytest_cache, .git

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

All files verified present. All 5 commits verified in git history.
