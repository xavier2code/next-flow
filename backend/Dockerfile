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

# Remove __pycache__ directories created during build
RUN find /app/app /app/alembic -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Ensure entrypoint is executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
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
