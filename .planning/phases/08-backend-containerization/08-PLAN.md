---
phase: 08-backend-containerization
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/pyproject.toml
  - backend/uv.lock
  - backend/Dockerfile
  - backend/.dockerignore
  - backend/entrypoint.sh
  - backend/gunicorn.conf.py
autonomous: true
requirements:
  - BACK-01
  - BACK-02
  - BACK-03
  - BACK-04
  - BACK-05
  - BACK-06

must_haves:
  truths:
    - "`docker build -t nextflow-backend ./backend` succeeds and the resulting image runs the FastAPI application on port 8000"
    - "The backend container starts with a non-root user (nextflow) and Alembic migrations execute automatically before Uvicorn accepts requests"
    - "`docker inspect` shows the container's HEALTHCHECK hitting `/api/v1/health` with correct intervals"
    - "Gunicorn with UvicornWorker manages processes with graceful shutdown support (graceful_timeout=120s)"
    - "`.dockerignore` prevents `.venv`, `__pycache__`, `.env`, `.pytest_cache`, and `.git` from entering the build context"
  artifacts:
    - path: "backend/Dockerfile"
      provides: "Multi-stage Docker build with python:3.12-slim-bookworm base, uv sync, non-root user, HEALTHCHECK"
      min_lines: 50
    - path: "backend/.dockerignore"
      provides: "Build context exclusions for sensitive and unnecessary files"
      min_lines: 10
    - path: "backend/gunicorn.conf.py"
      provides: "Gunicorn process configuration (UvicornWorker, timeouts, max_requests)"
      min_lines: 20
    - path: "backend/entrypoint.sh"
      provides: "Container entrypoint: runs Alembic migrations then exec's Gunicorn"
      min_lines: 8
    - path: "backend/pyproject.toml"
      provides: "Updated dependencies including gunicorn"
      contains: "gunicorn"
  key_links:
    - from: "backend/Dockerfile"
      to: "backend/entrypoint.sh"
      via: "ENTRYPOINT instruction"
      pattern: "ENTRYPOINT \\[\"./entrypoint.sh\"\\]"
    - from: "backend/Dockerfile"
      to: "backend/gunicorn.conf.py"
      via: "COPY and gunicorn -c reference"
      pattern: "gunicorn\\.conf\\.py"
    - from: "backend/entrypoint.sh"
      to: "backend/gunicorn.conf.py"
      via: "exec gunicorn -c gunicorn.conf.py"
      pattern: "gunicorn.*-c.*gunicorn\\.conf\\.py"
    - from: "backend/Dockerfile"
      to: "/api/v1/health"
      via: "HEALTHCHECK CMD curl"
      pattern: "curl -f http://localhost:8000/api/v1/health"
    - from: "backend/Dockerfile"
      to: "backend/pyproject.toml"
      via: "uv sync --frozen reads lockfile derived from pyproject.toml"
      pattern: "uv sync --frozen"
---

# Plan 08-01: Backend Dockerfile and .dockerignore

<objective>
Package the FastAPI backend into a production-ready Docker container with multi-stage build, non-root user, automatic database migrations, and health monitoring.

Purpose: The FastAPI backend currently runs locally via `uvicorn app.main:app`. No Dockerfile exists. This plan creates all artifacts needed for a production-grade backend container image.

Output: Working Dockerfile, .dockerignore, gunicorn.conf.py, entrypoint.sh, and updated pyproject.toml with gunicorn dependency. Image builds successfully and passes verification.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

Key decisions from research:
- Use `python:3.12-slim-bookworm` (NOT Alpine) -- asyncpg, psycopg, cryptography lack musl wheels
- Use `uv sync --frozen` for reproducible builds (the project has `uv.lock`)
- Use Gunicorn + UvicornWorker for production process management (graceful shutdown, memory leak prevention via max_requests)
- Non-root user (`nextflow`, UID 1000) for security
- HEALTHCHECK hitting `/api/v1/health` (existing endpoint in `backend/app/api/v1/health.py`)

Existing health endpoint at `backend/app/api/v1/health.py` returns `{"status": "healthy", "redis": "connected"}`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add gunicorn dependency to pyproject.toml</name>
  <files>backend/pyproject.toml, backend/uv.lock</files>
  <action>
Add `"gunicorn>=23.0.0"` to the `dependencies` array in `backend/pyproject.toml`, after the existing `"uvicorn[standard]>=0.34.0"` line. The new line must read:

```toml
    "gunicorn>=23.0.0",
```

After editing, run `cd /Users/xavier/Projects/github/tmp/next-flow/backend && uv lock` to update `uv.lock` with the gunicorn resolution.
  </action>
  <verify>
    <automated>cd /Users/xavier/Projects/github/tmp/next-flow/backend && grep -q "gunicorn>=23.0.0" pyproject.toml && grep -q 'name = "gunicorn"' uv.lock && uv sync --frozen</automated>
  </verify>
  <done>
- `backend/pyproject.toml` contains `"gunicorn>=23.0.0"` in the `dependencies` array
- `backend/uv.lock` contains a `[[package]]` entry with `name = "gunicorn"`
- `uv sync --frozen` exits 0
  </done>
</task>

<task type="auto">
  <name>Task 2: Create backend/.dockerignore</name>
  <files>backend/.dockerignore</files>
  <action>
Create file `backend/.dockerignore` with the following exact content:

```
.venv
venv
__pycache__
*.pyc
*.pyo
.env
.git
.gitignore
.pytest_cache
.mypy_cache
.ruff_cache
*.egg-info
tests/
```
  </action>
  <verify>
    <automated>cd /Users/xavier/Projects/github/tmp/next-flow && test -f backend/.dockerignore && grep -qE "^\\.venv$" backend/.dockerignore && grep -qE "^__pycache__$" backend/.dockerignore && grep -qE "^\\.env$" backend/.dockerignore && grep -qE "^\\.pytest_cache$" backend/.dockerignore && grep -qE "^\\.git$" backend/.dockerignore</automated>
  </verify>
  <done>
- File `backend/.dockerignore` exists
- File contains lines: `.venv`, `__pycache__`, `.env`, `.pytest_cache`, `.git`
- File does NOT contain lines: `alembic/`, `alembic.ini`, `app/`, `pyproject.toml` (these must enter the build)
  </done>
</task>

<task type="auto">
  <name>Task 3: Create backend/gunicorn.conf.py</name>
  <files>backend/gunicorn.conf.py</files>
  <action>
Create file `backend/gunicorn.conf.py` with the following exact content. This file configures Gunicorn using Python (preferred over CLI flags for readability and maintainability):

```python
"""Gunicorn configuration for NextFlow backend.

Uses uvicorn.workers.UvicornWorker for ASGI support.
Key settings:
- workers: configurable via WEB_CONCURRENCY env var, default 4
- timeout/graceful_timeout: 120s to accommodate long agent workflows
- max_requests: restart workers periodically to prevent memory leaks
"""

import multiprocessing
import os

# Worker class for ASGI (FastAPI)
worker_class = "uvicorn.workers.UvicornWorker"

# Number of workers: override with WEB_CONCURRENCY env var
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 8)))

# Bind address
bind = "0.0.0.0:8000"

# Timeouts (long to accommodate agent workflows with tool calls)
timeout = 120
graceful_timeout = 120
keepalive = 5

# Memory leak prevention: restart workers periodically
max_requests = 5000
max_requests_jitter = 500

# Logging to stdout (Docker captures stdout)
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

Note: Both `import os` and `import multiprocessing` are required. The `os` import must be present because `os.environ.get` is used for the WEB_CONCURRENCY override.
  </action>
  <verify>
    <automated>cd /Users/xavier/Projects/github/tmp/next-flow && test -f backend/gunicorn.conf.py && grep -q 'worker_class = "uvicorn.workers.UvicornWorker"' backend/gunicorn.conf.py && grep -q "max_requests = 5000" backend/gunicorn.conf.py && grep -q "graceful_timeout = 120" backend/gunicorn.conf.py && grep -q "import os" backend/gunicorn.conf.py</automated>
  </verify>
  <done>
- File `backend/gunicorn.conf.py` exists
- File contains `worker_class = "uvicorn.workers.UvicornWorker"`
- File contains `max_requests = 5000`
- File contains `graceful_timeout = 120`
- File contains `import os` at the top
  </done>
</task>

<task type="auto">
  <name>Task 4: Create backend/entrypoint.sh</name>
  <files>backend/entrypoint.sh</files>
  <action>
Create file `backend/entrypoint.sh` with the following exact content. This script runs Alembic migrations before starting Gunicorn with Uvicorn workers:

```bash
#!/bin/bash
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting Gunicorn with Uvicorn workers..."
exec gunicorn app.main:app \
    -c gunicorn.conf.py
```

Then make it executable: `chmod +x backend/entrypoint.sh`

The `exec` form is critical: it replaces the shell process with Gunicorn, so SIGTERM is received by Gunicorn directly (not the shell wrapper). Gunicorn then propagates SIGTERM to workers which complete in-flight requests within `graceful_timeout` (120s) before shutting down.
  </action>
  <verify>
    <automated>cd /Users/xavier/Projects/github/tmp/next-flow && test -x backend/entrypoint.sh && grep -q "set -e" backend/entrypoint.sh && grep -q "alembic upgrade head" backend/entrypoint.sh && grep -q "exec gunicorn app.main:app" backend/entrypoint.sh && grep -q "\-c gunicorn.conf.py" backend/entrypoint.sh</automated>
  </verify>
  <done>
- File `backend/entrypoint.sh` exists and has executable permission (`-rwxr-xr-x`)
- File contains `set -e`
- File contains `alembic upgrade head`
- File contains `exec gunicorn app.main:app`
- File contains `-c gunicorn.conf.py`
  </done>
</task>

<task type="auto">
  <name>Task 5: Create backend/Dockerfile and verify the build</name>
  <files>backend/Dockerfile</files>
  <action>
Create file `backend/Dockerfile` with the following exact content. This is a multi-stage build using `uv` for dependency installation (matching the existing `uv.lock`):

```dockerfile
# ---- Stage 1: Builder ----
# Install Python dependencies using uv (matching existing uv.lock)
FROM python:3.12-slim-bookworm AS builder

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency specs first for Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
# --frozen: exact versions from lockfile, no floating
# --no-dev: exclude pytest and dev dependencies
# --no-install-project: only install dependencies, not the project itself
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code and config
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY gunicorn.conf.py ./
COPY entrypoint.sh ./

# Install the project itself into the venv (so `app` package is importable)
RUN uv sync --frozen --no-dev

# ---- Stage 2: Runtime ----
FROM python:3.12-slim-bookworm

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r nextflow && useradd -r -g nextflow -d /app -s /sbin/nologin nextflow

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code from builder
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./
COPY --from=builder /app/gunicorn.conf.py ./
COPY --from=builder /app/entrypoint.sh ./

# Ensure entrypoint is executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create directory for any runtime writes, owned by nextflow user
RUN mkdir -p /app/data && chown nextflow:nextflow /app/data

USER nextflow

EXPOSE 8000

# Health check: hit existing /api/v1/health endpoint (checks Redis connectivity)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=30s \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Use entrypoint script: runs Alembic migrations, then exec's Gunicorn
ENTRYPOINT ["./entrypoint.sh"]
```

Key design decisions:
1. **Multi-stage build**: Builder installs deps via `uv sync --frozen`. Runtime only has the venv + app code. No build tools in final image.
2. **`uv sync --frozen`**: Respects `uv.lock` exactly. Reproducible builds.
3. **`python:3.12-slim-bookworm`**: glibc-based, compatible with asyncpg/psycopg/cryptography pre-built wheels.
4. **Non-root user `nextflow`**: Security hardening. App only writes to `/app/data`.
5. **HEALTHCHECK**: Hits `/api/v1/health` which checks Redis connectivity (existing endpoint).
6. **`start-period: 30s`**: Gives the backend time to initialize (MCP connections, checkpointer, memory service) before health checks start.
7. **`curl` in runtime**: Needed for HEALTHCHECK. `libpq5` needed for asyncpg at runtime.
8. **No CMD**: The ENTRYPOINT script handles everything (migrations + gunicorn start).
9. **Gunicorn handles graceful shutdown**: SIGTERM -> workers finish in-flight requests within `graceful_timeout` (120s).

After creating the Dockerfile, build and verify the image:

```bash
cd /Users/xavier/Projects/github/tmp/next-flow
docker build -t nextflow-backend ./backend
```

Verify the image properties:

```bash
# Verify the image was created
docker images nextflow-backend

# Verify non-root user (should show UID or "nextflow")
docker run --rm nextflow-backend id

# Verify gunicorn is installed
docker run --rm nextflow-backend python -c "import gunicorn; print(gunicorn.__version__)"

# Verify alembic is available
docker run --rm nextflow-backend alembic --version
```
  </action>
  <verify>
    <automated>cd /Users/xavier/Projects/github/tmp/next-flow && test -f backend/Dockerfile && grep -q "FROM python:3.12-slim-bookworm AS builder" backend/Dockerfile && grep -q "uv sync --frozen --no-dev --no-install-project" backend/Dockerfile && grep -q "groupadd -r nextflow" backend/Dockerfile && grep -q "USER nextflow" backend/Dockerfile && grep -q "HEALTHCHECK" backend/Dockerfile && grep -q 'curl -f http://localhost:8000/api/v1/health' backend/Dockerfile && grep -q 'ENTRYPOINT \["./entrypoint.sh"\]' backend/Dockerfile && docker build -t nextflow-backend ./backend && docker run --rm nextflow-backend id | grep -q nextflow && docker run --rm nextflow-backend python -c "import gunicorn"</automated>
  </verify>
  <done>
- File `backend/Dockerfile` exists with multi-stage build (builder + runtime)
- Image builds successfully: `docker build -t nextflow-backend ./backend` exits 0
- Non-root user: `docker run --rm nextflow-backend id` output contains `nextflow` (not `root`)
- Gunicorn installed: `docker run --rm nextflow-backend python -c "import gunicorn"` exits 0
- Alembic available: `docker run --rm nextflow-backend alembic --version` exits 0
- Dockerfile contains HEALTHCHECK, USER nextflow, EXPOSE 8000, ENTRYPOINT
- Dockerfile does NOT contain `FROM python:3.12-alpine` or `--preload`
  </done>
</task>

</tasks>

<verification>
1. `docker build -t nextflow-backend ./backend` exits 0
2. `docker run --rm nextflow-backend id` shows `nextflow` user
3. `docker run --rm nextflow-backend python -c "import gunicorn"` exits 0
4. `docker inspect --format='{{json .Config.Healthcheck}}' nextflow-backend` shows health check hitting `/api/v1/health`
5. All required files exist: Dockerfile, .dockerignore, gunicorn.conf.py, entrypoint.sh
</verification>

<success_criteria>
- Docker image `nextflow-backend` builds from a multi-stage Dockerfile using `python:3.12-slim-bookworm`
- Image runs as non-root user `nextflow` with HEALTHCHECK configured against `/api/v1/health`
- Entrypoint runs Alembic migrations then exec's Gunicorn with UvicornWorker
- `.dockerignore` excludes `.venv`, `__pycache__`, `.env`, `.pytest_cache`, `.git`
- Gunicorn configured with graceful_timeout=120s, max_requests=5000, worker_class=UvicornWorker
</success_criteria>

<output>
After completion, create `.planning/phases/08-backend-containerization/08-01-SUMMARY.md`
</output>
