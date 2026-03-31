#!/bin/bash
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting Gunicorn with Uvicorn workers..."
exec gunicorn app.main:app \
    -c gunicorn.conf.py
