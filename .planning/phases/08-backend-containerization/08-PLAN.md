---
wave: 1
depends_on: none
files_modified:
  - backend/pyproject.toml
  - backend/uv.lock
  - backend/Dockerfile
  - backend/.dockerignore
  - backend/entrypoint.sh
  - backend/gunicorn.conf.py
requirements:
  - BACK-01
  - BACK-02
  - BACK-03
  - BACK-04
  - BACK-05
  - BACK-06
autonomous: true
---

# Plan 08-01: Backend Dockerfile and .dockerignore

## Context

The FastAPI backend currently runs locally via `uvicorn app.main:app`. The project uses `uv` with `uv.lock` for dependency management. No Dockerfile exists yet. This plan creates the production-ready backend container image.

**Key decisions from research:**
- Use `python:3.12-slim-bookworm` (NOT Alpine) -- asyncpg, psycopg, cryptography lack musl wheels
- Use `uv sync --frozen` for reproducible builds (the project has `uv.lock`)
- Use Gunicorn + UvicornWorker for production process management (graceful shutdown, memory leak prevention via max_requests)
- Non-root user (`nextflow`, UID 1000) for security
- HEALTHCHECK hitting `/api/v1/health` (existing endpoint in `backend/app/api/v1/health.py`)

## Tasks

### Task 1: Add gunicorn dependency to pyproject.toml

**read_first:**
- `backend/pyproject.toml`

**action:**
Add `"gunicorn>=23.0.0"` to the `dependencies` array in `backend/pyproject.toml`, after the existing `"uvicorn[standard]>=0.34.0"` line. The new line must read:

```toml
    "gunicorn>=23.0.0",
```

After editing, run `cd /Users/xavier/Projects/github/tmp/next-flow/backend && uv lock` to update `uv.lock` with the gunicorn resolution.

**acceptance_criteria:**
- `backend/pyproject.toml` contains `"gunicorn>=23.0.0"` in the `dependencies` array
- `backend/uv.lock` contains a `[[package]]` entry with `name = "gunicorn"`
- Command `cd /Users/xavier/Projects/github/tmp/next-flow/backend && uv sync --frozen` exits 0

---

### Task 2: Create backend/.dockerignore

**read_first:**
- (no files to read -- this is a new file)

**action:**
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

**acceptance_criteria:**
- File `backend/.dockerignore` exists
- File contains lines: `.venv`, `__pycache__`, `.env`, `.pytest_cache`, `.git`
- File does NOT contain lines: `alembic/`, `alembic.ini`, `app/`, `pyproject.toml` (these must enter the build)

---

### Task 3: Create backend/gunicorn.conf.py

**read_first:**
- `backend/pyproject.toml` (confirm gunicorn dependency)
- `backend/app/main.py` (understand the app factory)

**action:**
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

# Worker class for ASGI (FastAPI)
worker_class = "uvicorn.workers.UvicornWorker"

# Number of workers: override with WEB_CONCURRENCY env var
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 8)))  # noqa: F821

# Bind address
bind = "0.0.0.0:8000"

# Timeouts (long to accommodate agent workflows with tool calls)
timeout = 120
graceful_timeout = 120
keepalive = 5

# Memory leak prevention: restart workers after N requests
max_requests = 5000
max_requests_jitter = 500

# Logging to stdout (Docker captures stdout)
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Uvicorn-specific settings passed via env vars
# These are read by UvicornWorker internally
```

Note: the `os` import is used but not imported at the top -- fix this by adding `import os` at the top of the file. The complete file is:

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

**acceptance_criteria:**
- File `backend/gunicorn.conf.py` exists
- File contains `worker_class = "uvicorn.workers.UvicornWorker"`
- File contains `max_requests = 5000`
- File contains `graceful_timeout = 120`
- File contains `import os` at the top

---

### Task 4: Create backend/entrypoint.sh

**read_first:**
- `backend/alembic/env.py` (confirms alembic reads DATABASE_URL from settings)
- `backend/alembic.ini` (confirms script_location = alembic)

**action:**
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

**acceptance_criteria:**
- File `backend/entrypoint.sh` exists and has executable permission (`-rwxr-xr-x`)
- File contains `set -e`
- File contains `alembic upgrade head`
- File contains `exec gunicorn app.main:app`
- File contains `-c gunicorn.conf.py`

---

### Task 5: Create backend/Dockerfile

**read_first:**
- `backend/pyproject.toml` (dependencies to install)
- `backend/uv.lock` (exists, confirms uv lockfile)
- `backend/entrypoint.sh` (understand the entrypoint)
- `backend/gunicorn.conf.py` (understand the gunicorn config)
- `backend/.dockerignore` (understand what is excluded)
- `backend/app/api/v1/health.py` (health endpoint at /api/v1/health)

**action:**
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

**acceptance_criteria:**
- File `backend/Dockerfile` exists
- File contains `FROM python:3.12-slim-bookworm AS builder`
- File contains `FROM python:3.12-slim-bookworm` (runtime stage)
- File contains `COPY --from=ghcr.io/astral-sh/uv:latest`
- File contains `uv sync --frozen --no-dev --no-install-project`
- File contains `groupadd -r nextflow`
- File contains `USER nextflow`
- File contains `HEALTHCHECK`
- File contains `CMD curl -f http://localhost:8000/api/v1/health`
- File contains `ENTRYPOINT ["./entrypoint.sh"]`
- File contains `EXPOSE 8000`
- File does NOT contain `FROM python:3.12-alpine` (must be bookworm)
- File does NOT contain `--preload` (breaks async SQLAlchemy engines)

---

### Task 6: Verify Docker build succeeds

**read_first:**
- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/entrypoint.sh`

**action:**
Run the Docker build command to verify the image builds successfully:

```bash
cd /Users/xavier/Projects/github/tmp/next-flow
docker build -t nextflow-backend ./backend
```

After the build succeeds, verify the image properties:

```bash
# Verify the image was created
docker images nextflow-backend

# Verify non-root user (should show UID 1000 or "nextflow")
docker run --rm nextflow-backend id

# Verify gunicorn is installed
docker run --rm nextflow-backend python -c "import gunicorn; print(gunicorn.__version__)"

# Verify alembic is available
docker run --rm nextflow-backend alembic --version
```

**acceptance_criteria:**
- `docker build -t nextflow-backend ./backend` exits 0
- `docker run --rm nextflow-backend id` output contains `nextflow` (not `root`)
- `docker run --rm nextflow-backend python -c "import gunicorn"` exits 0
- `docker run --rm nextflow-backend alembic --version` exits 0
