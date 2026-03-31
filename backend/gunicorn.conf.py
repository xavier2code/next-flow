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
