# Architecture Patterns: Docker Containerization & Production Deployment

**Domain:** Containerizing the existing NextFlow Agent Platform
**Researched:** 2026-03-31
**Confidence:** HIGH (based on code analysis of existing system + well-established Docker/Nginx patterns)

## Recommended Architecture

The containerized deployment adds three new services to the existing docker-compose infrastructure (postgres, redis, minio): a **backend** container, a **frontend-nginx** container, and an **nginx** reverse proxy. The reverse proxy is the single entry point, routing API calls to the backend, WebSocket upgrades to the backend, and static file requests to the frontend container. The backend container mounts the Docker socket so the existing SkillSandbox can continue spawning sibling skill containers on the host.

```
                          External Traffic (port 80/443)
                                    |
                            +-------v--------+
                            |  nginx-proxy   |
                            |  (reverse proxy|
                            |   + static     |
                            |   files)       |
                            +---+--------+---+
                                |        |
                 /api/v1/*      |        |  /ws/*
                 /health        |        |
                                |        |
                         +------v--+   +-v-----------+
                         | frontend|   |  backend     |
                         | (static |   |  (FastAPI     |
                         |  files) |   |   uvicorn)   |
                         +---------+   +------+-------+
                                              |
                      +---------------+-------+--------+-----------+
                      |               |                |           |
                +-----v-----+  +-----v-----+  +-------v---+ +----v----+
                | postgres  |  |   redis   |  |   minio   | | Docker  |
                | (pgvector)|  |   (7)     |  |           | | socket  |
                +-----------+  +-----------+  +-----------+ | (host)  |
                                                            +----+----+
                                                                 |
                                                           +-----v------+
                                                           | Skill      |
                                                           | containers |
                                                           | (sandbox)  |
                                                           +------------+
```

### Unified Nginx Variant (Recommended)

Rather than two separate Nginx containers (one for frontend static files, one for proxy), a single Nginx container serves both roles. The frontend build artifacts are copied into the Nginx image at build time. This reduces operational overhead, eliminates one network hop, and simplifies the compose file.

```
docker-compose.yml services:

  postgres       -- existing, unchanged
  redis          -- existing, unchanged
  minio          -- existing, unchanged
  backend        -- NEW: FastAPI + uvicorn in container
  nginx          -- NEW: single entry point (static files + reverse proxy)
```

### Component Boundaries

| Component | Status | Responsibility | Communicates With |
|-----------|--------|---------------|-------------------|
| **nginx** | NEW | Reverse proxy, static file serving, WebSocket upgrade, SSL termination | backend (proxy_pass), serves frontend static files directly |
| **backend** | NEW container | FastAPI application (auth, agent engine, REST API, WebSocket endpoint) | postgres, redis, minio, Docker socket (skill sandbox) |
| **frontend (build stage)** | NEW | React SPA build, produces static files for Nginx | Build artifact only (not a runtime service) |
| **postgres** | EXISTING (modified) | Relational data, LangGraph checkpointer | backend (internal network) |
| **redis** | EXISTING (modified) | Cache, session store, pub/sub for cross-worker WS | backend (internal network) |
| **minio** | EXISTING (modified) | Skill packages, document storage | backend (internal network) |
| **Skill containers** | EXISTING behavior | Sandboxed skill execution | Spawned by backend via Docker socket |

### Data Flow (Containerized)

```
Browser request
      |
      v
nginx:80 (single entry point)
      |
      +--- GET /api/v1/* ---> proxy_pass http://backend:8000/api/v1/*
      |
      +--- GET /health ----> proxy_pass http://backend:8000/health
      |
      +--- WS /ws/chat ----> proxy_pass http://backend:8000/ws/chat (upgrade headers)
      |
      +--- GET /* ----------> serve /usr/share/nginx/html/index.html (SPA fallback)
      |                         /assets/* --> cached static files
      |
      v
Response to browser
```

**WebSocket upgrade flow (critical detail):**
```
Browser sends: Upgrade: websocket, Connection: Upgrade
      |
      v
nginx receives /ws/chat?token=xxx
      |
      v
nginx config:
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_read_timeout 86400s;   # 24h -- prevents Nginx from closing idle WS
  proxy_buffering off;
      |
      v
backend:8000 receives WebSocket handshake
      |
      v
FastAPI /ws/chat endpoint: validate JWT, accept, register in ConnectionManager
      |
      v
Long-lived bidirectional connection through Nginx
```

**Skill sandbox flow (Docker socket mount):**
```
Backend container starts with -v /var/run/docker.sock:/var/run/docker.sock
      |
      v
SkillSandbox uses docker.from_env() -> connects to host Docker daemon
      |
      v
Skill containers are siblings of the backend container (not children)
      |
      v
Skill containers join the same Docker network (nextflow_default) for DNS resolution
      |
      v
Backend accesses skill container via http://nextflow-skill-{name}:8080
```

## Patterns to Follow

### Pattern 1: Multi-Stage Backend Dockerfile with uv

**What:** Use a two-stage build. The builder stage installs dependencies using `uv` (matching the existing `uv.lock`). The runtime stage copies only the installed packages and application code.

**When:** Backend Dockerfile.

**Rationale:** The project uses `uv` with `uv.lock` for dependency management (not pip/requirements.txt). The Dockerfile must work with this toolchain.

```dockerfile
# ---- Stage 1: Builder ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy lockfile and project definition first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Install the project itself into the venv
RUN uv sync --frozen --no-dev

# ---- Stage 2: Runtime ----
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/app ./app
COPY --from=builder /app/alembic ./alembic
COPY --from=builder /app/alembic.ini ./

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import httpx; httpx.get('http://localhost:8000/health')"] || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--ws-ping-interval", "20", "--ws-ping-timeout", "20"]
```

**Key decisions:**
- `uv sync --frozen` respects the lockfile exactly (no floating versions)
- `--no-dev` excludes pytest and dev dependencies from production image
- Non-root user (`appuser`) for security -- but see Pattern 5 for Docker socket constraint
- HEALTHCHECK uses `httpx` (already in dependencies) rather than `curl` (not in slim image)
- `PYTHONUNBUFFERED=1` ensures logs appear immediately (not buffered)
- Uvicorn ping/pong args match the existing comment in `main.py` line 244

### Pattern 2: Multi-Stage Frontend Dockerfile with Nginx

**What:** Build the React SPA in a Node.js stage, then copy only the dist output into an Nginx image. The Nginx config handles SPA routing (try_files fallback) and proxies API/WebSocket to the backend.

**When:** Frontend Dockerfile.

```dockerfile
# ---- Stage 1: Build ----
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build    # outputs to /app/dist

# ---- Stage 2: Nginx with static files + reverse proxy ----
FROM nginx:1.27-alpine

# Remove default Nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx config (handles both static files and proxy)
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Key decisions:**
- Node 22 Alpine matches the CLAUDE.md stack (Node 22 LTS)
- `npm ci` uses the lockfile for reproducible builds (faster and stricter than `npm install`)
- Final image is ~25MB (Nginx Alpine + static files only, no Node.js)
- Separate `nginx.conf` file allows easy customization without rebuilding

### Pattern 3: Nginx Configuration for FastAPI + WebSocket + SPA

**What:** A single Nginx server block that routes `/api/v1/*` and `/ws/*` to the backend, serves static files for the React SPA, and handles SPA client-side routing fallback.

**When:** Nginx config file.

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name _;

    # ---- Gzip compression ----
    gzip on;
    gzip_types text/plain text/css application/json application/javascript
               text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 256;

    # ---- API reverse proxy ----
    location /api/v1/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # For streaming responses (agent events)
        proxy_buffering off;

        # Allow large file uploads (skill packages)
        client_max_body_size 100M;
    }

    # ---- Health check endpoint ----
    location /health {
        proxy_pass http://backend;
        proxy_set_header Host $host;
    }

    # ---- OpenAPI docs (optional, can be disabled in production) ----
    location /docs {
        proxy_pass http://backend;
    }
    location /openapi.json {
        proxy_pass http://backend;
    }

    # ---- WebSocket proxy ----
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;

        # Critical: WebSocket upgrade headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Long timeouts for persistent WebSocket connections
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;

        # No buffering for real-time streaming
        proxy_buffering off;
    }

    # ---- Static assets (aggressive cache) ----
    location /assets/ {
        root /usr/share/nginx/html;
        expires 1y;
        add_header Cache-Control "public, immutable";

        # Vite outputs hashed filenames: [name]-[hash].[ext]
        # These are safe to cache aggressively
    }

    # ---- SPA fallback (all other routes -> index.html) ----
    location / {
        root /usr/share/nginx/html;
        index index.html;

        # No-cache for index.html (contains hashed asset references that may change)
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";

        try_files $uri $uri/ /index.html;
    }
}
```

**Why this configuration works with the existing codebase:**

1. The frontend `api-client.ts` uses relative paths (`/api/v1/auth/login`, etc.) -- these work behind any proxy without configuration changes because the Nginx routes them to the backend.

2. The frontend `use-websocket.ts` constructs WebSocket URLs dynamically from `window.location.protocol` and `window.location.host` -- Nginx's WebSocket proxy makes `/ws/chat` resolve correctly without any frontend code changes.

3. The backend CORS config (`cors_origins: ["http://localhost:5173"]`) will need updating to include the production origin, but in the containerized setup, the browser talks to Nginx (same origin), so CORS is not actually exercised between browser and backend. CORS only matters in development mode.

### Pattern 4: Production docker-compose.yml with Dependency Ordering

**What:** Extend the existing docker-compose.yml with backend and nginx services. Use healthcheck-based dependencies so services start in the correct order.

**When:** Production docker-compose.yml.

```yaml
services:
  # ---- Infrastructure (existing, ports modified) ----

  postgres:
    image: pgvector/pgvector:pg16
    container_name: nextflow-postgres
    # Remove port exposure in production (only internal access)
    # expose:
    #   - "5432"
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-nextflow}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}
      POSTGRES_DB: ${POSTGRES_DB:-nextflow}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-nextflow}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nextflow

  redis:
    image: redis:7-alpine
    container_name: nextflow-redis
    # Remove port exposure in production
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD:-}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nextflow

  minio:
    image: minio/minio:latest
    container_name: nextflow-minio
    # Remove port exposure in production (or keep for admin console)
    ports:
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-nextflow}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD required}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nextflow

  # ---- Application (new) ----

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nextflow-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-nextflow}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-nextflow}
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER:-nextflow}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      MINIO_SECURE: "false"
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:?JWT_SECRET_KEY required}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
      CORS_ORIGINS: ${CORS_ORIGINS:-[]}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    volumes:
      # Docker socket for skill sandbox (sibling containers)
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped
    networks:
      - nextflow
    # Note: no ports exposed -- all traffic goes through nginx

  nginx:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      # nginx.conf is in the frontend/nginx/ directory
    container_name: nextflow-nginx
    depends_on:
      backend:
        condition: service_started
    ports:
      - "${NGINX_PORT:-80}:80"
    restart: unless-stopped
    networks:
      - nextflow

volumes:
  postgres_data:
  redis_data:
  minio_data:

networks:
  nextflow:
    driver: bridge
```

**Dependency ordering rationale:**

```
postgres (healthy) ──+
redis (healthy)    ──+──> backend (started) ──> nginx (started)
minio (healthy)    ──+
```

1. **postgres, redis, minio** start in parallel (no dependencies between them)
2. **backend** waits for all three to be healthy (condition: service_healthy)
3. **nginx** waits for backend to start (condition: service_started -- not healthy, because nginx should start even if backend is temporarily unhealthy; Nginx will return 502 until backend is ready)

**Service startup sequence at `docker-compose up`:**
```
T+0s   : postgres, redis, minio start
T+2-5s : postgres, redis, minio pass healthchecks
T+5s   : backend starts (depends_on conditions met)
T+5s   : nginx starts (parallel with backend, only needs service_started)
T+10s  : backend passes its own healthcheck
T+10s  : nginx begins successfully proxying to backend
```

### Pattern 5: Docker Socket Mount for Skill Sandbox

**What:** The backend container mounts `/var/run/docker.sock` from the host so the existing `SkillSandbox` class can continue using `docker.from_env()` to spawn skill containers as siblings.

**When:** Always (required for skill system to function).

**How it works with the existing code:**

The `SkillSandbox` class (in `backend/app/services/skill/sandbox.py`) calls `docker.from_env()`. Inside a container, this connects to the Docker daemon via the mounted socket. The spawned skill containers are **siblings** of the backend container, not children -- they run on the host Docker daemon directly.

**Security implications:**
- Mounting the Docker socket grants the backend container near-root access to the host. This is an accepted trade-off for the skill sandbox feature.
- The skill containers already use security hardening (`cap_drop ALL`, `no-new-privileges`, `read_only`, `user 1000:1000`, `pids_limit`, `mem_limit`).

**Network connectivity for skill containers:**
- Skill containers must join the `nextflow` Docker network so the backend can reach them via `http://nextflow-skill-{name}:8080`.
- The `SkillSandbox.start_service_container()` method creates containers with `network_mode="bridge"` (default). In the containerized deployment, these containers need to be connected to the `nextflow` network explicitly.
- This requires a modification to `SkillSandbox` to pass `network="nextflow"` when creating containers in a containerized environment.

```python
# Modification needed in sandbox.py:
container = self._docker.containers.run(
    image="nextflow-skill-base:latest",
    # ... existing params ...
    network="nextflow",  # ADD: join the compose network
    # ... rest unchanged ...
)
```

**Alternative (no code change):** Use the `DOCKER_SOCKET` environment variable and rely on Docker Compose's default network. When `docker-compose up` creates the `nextflow_default` network, containers created via the socket are not automatically added to it. The code change is the cleaner approach.

### Pattern 6: Development docker-compose.dev.yml (Infrastructure Only)

**What:** A separate compose file for development that only starts infrastructure services (postgres, redis, minio). The developer runs backend and frontend locally.

**When:** Development workflow.

```yaml
# docker-compose.dev.yml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: nextflow-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: nextflow
      POSTGRES_PASSWORD: nextflow
      POSTGRES_DB: nextflow
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nextflow"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: nextflow-redis
    ports:
      - "6380:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: nextflow-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: nextflow
      MINIO_ROOT_PASSWORD: nextflow123
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

**Usage:**
```bash
# Development: infrastructure only, run backend/frontend locally
docker compose -f docker-compose.dev.yml up -d

# Production: everything containerized
docker compose up -d
```

This preserves the existing developer workflow exactly as-is. The existing `docker-compose.yml` is the development file (renamed to `docker-compose.dev.yml`). The new production `docker-compose.yml` adds backend + nginx services.

### Pattern 7: Environment Variable Strategy

**What:** The existing `Settings` class in `backend/app/core/config.py` uses `pydantic-settings` with `.env` file support. In containers, environment variables are passed via docker-compose `environment:` section, which overrides `.env` file defaults.

**When:** Configuration management.

**Key changes to defaults for containerized deployment:**

| Variable | Local Default | Container Value | Reason |
|----------|--------------|-----------------|--------|
| `database_url` | `localhost:5432` | `postgres:5432` | Docker internal DNS |
| `redis_url` | `localhost:6380` | `redis:6379` | Docker internal DNS, standard port |
| `minio_endpoint` | `localhost:9000` | `minio:9000` | Docker internal DNS |
| `cors_origins` | `["http://localhost:5173"]` | `[]` (empty) | Nginx is same-origin; no CORS needed |
| `ollama_base_url` | `http://localhost:11434` | `http://host.docker.internal:11434` | Access host Ollama from container |

**Frontend environment:** No changes needed. The frontend already uses relative URLs (`/api/v1/*`, `/ws/chat`) which resolve to the Nginx origin automatically.

**Template file:**
```bash
# .env.example
POSTGRES_PASSWORD=change-me-in-production
MINIO_ROOT_PASSWORD=change-me-in-production
JWT_SECRET_KEY=change-me-in-production
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://host.docker.internal:11434
LOG_LEVEL=INFO
NGINX_PORT=80
MINIO_CONSOLE_PORT=9001
```

### Pattern 8: Database Migration at Container Startup

**What:** Run Alembic migrations before the FastAPI application starts. Use an entrypoint script that runs migrations then exec's uvicorn.

**When:** Backend container startup.

```bash
#!/bin/bash
# backend/entrypoint.sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ws-ping-interval 20 \
    --ws-ping-timeout 20
```

**Why not a separate migration container:** Running migrations in the same container as the application avoids race conditions with multiple backend replicas and keeps the compose file simple. The `exec` ensures the uvicorn process receives signals (SIGTERM for graceful shutdown).

**Important:** The existing `alembic/env.py` reads `settings.database_url` from pydantic-settings, which reads from the `DATABASE_URL` environment variable. In the container, this is set to `postgres:5432` (the Docker network hostname). No code changes needed.

### Pattern 9: Volume Strategy

**What:** Persistent data (database, Redis, MinIO) uses named Docker volumes. Application containers are stateless and ephemeral.

**When:** All environments.

| Data | Volume | Type | Backup Strategy |
|------|--------|------|-----------------|
| PostgreSQL data | `postgres_data` | Named volume | `pg_dump` via cron or backup container |
| Redis data | `redis_data` | Named volume | AOF persistence (Redis config). Data is cache-grade (safe to lose) |
| MinIO data | `minio_data` | Named volume | `mc mirror` to S3 or backup volume |
| Backend application | None | Stateless | Rebuilt from image on deploy |
| Frontend static files | None | Baked into image | Rebuilt from image on deploy |
| Skill packages | In MinIO volume | Via MinIO | Covered by MinIO backup |

**Redis persistence note:** Add `command: redis-server --appendonly yes` to the Redis service configuration for durability across restarts. The current config uses the default (no persistence), which means Redis data (session cache, short-term memory) is lost on restart. This is acceptable for v1 but should be enabled for production.

### Pattern 10: Nginx SPA Routing with Vite Hashed Assets

**What:** Vite produces hashed asset filenames (e.g., `assets/index-AbCd1234.js`). Nginx caches these aggressively with `expires 1y; immutable`. The `index.html` is served with `no-cache` so browsers always fetch the latest version with updated asset references.

**When:** Frontend serving.

**Why this works:** The existing `vite.config.ts` already configures the Vite build. Vite 7 automatically generates hashed filenames for JS/CSS in production builds. The `try_files $uri $uri/ /index.html` directive handles React Router client-side routing (the app uses `react-router` per `package.json`).

## Anti-Patterns to Avoid

### Anti-Pattern 1: Exposing Backend Port Directly

**What:** Publishing the backend's port 8000 to the host alongside the Nginx port 80.
**Why bad:** Bypasses Nginx's rate limiting, SSL termination, and security headers. Users (or misconfigured frontend code) could hit the backend directly, circumventing proxy protections.
**Instead:** Backend has no `ports:` section in production compose. All traffic flows through Nginx.

### Anti-Pattern 2: Two Separate Nginx Containers

**What:** One Nginx container for frontend static files, another Nginx (or different reverse proxy) for API/WebSocket routing.
**Why bad:** Adds latency (extra network hop from frontend-Nginx to backend-Nginx), doubles configuration surface, complicates SSL certificate management, and adds a container with minimal benefit.
**Instead:** Single Nginx container handles both static files and reverse proxy. This is the standard pattern for SPA + API deployments.

### Anti-Pattern 3: Embedding Frontend in Backend Container

**What:** Serving frontend static files from FastAPI using `StaticFiles` mount.
**Why bad:** Couples frontend and backend build cycles. Frontend changes require backend rebuild. FastAPI is not optimized for static file serving. Cannot scale frontend and backend independently.
**Instead:** Separate Dockerfiles. Frontend builds into Nginx image. Backend stays pure Python.

### Anti-Pattern 4: Docker-in-Docker for Skill Sandbox

**What:** Running a Docker daemon inside the backend container (`--privileged` with `docker:dind`).
**Why bad:** Security nightmare (privileged mode), complex networking (nested Docker), poor performance, difficult to debug. The skill containers would be grandchildren of the host daemon.
**Instead:** Mount the host Docker socket. Skill containers are siblings of the backend on the host daemon. This is simpler, more secure (no privileged mode), and uses the existing `docker.from_env()` code unchanged.

### Anti-Pattern 5: Hardcoded URLs in Frontend

**What:** Setting `VITE_API_URL` or `VITE_WS_URL` to `http://backend:8000` at build time.
**Why bad:** Container hostnames (`backend`) are internal DNS names not resolvable from the browser. Would require different builds for local development vs containerized deployment.
**Instead:** The existing frontend code already uses relative URLs (`/api/v1/*`, `ws://${window.location.host}/ws/chat`). This works identically in both development (Vite proxy) and production (Nginx proxy). No frontend code changes needed.

### Anti-Pattern 6: Using `latest` Tag for Skill Base Image

**What:** The `SkillSandbox` references `nextflow-skill-base:latest`.
**Why bad:** `latest` is a floating tag. Different hosts may have different versions. Builds are not reproducible.
**Instead:** Pin the skill base image tag (e.g., `nextflow-skill-base:1.0.0`). This is existing behavior and should be addressed in a future skill versioning milestone, not this containerization milestone.

## Integration Points with Existing Architecture

### New Components

| Component | Files to Create | Purpose |
|-----------|----------------|---------|
| Backend Dockerfile | `backend/Dockerfile` | Multi-stage build for FastAPI |
| Backend entrypoint | `backend/entrypoint.sh` | Run Alembic migrations + start uvicorn |
| Backend .dockerignore | `backend/.dockerignore` | Exclude `__pycache__`, `.env`, tests, venv |
| Frontend Dockerfile | `frontend/Dockerfile` | Multi-stage build: Node -> Nginx |
| Frontend .dockerignore | `frontend/.dockerignore` | Exclude `node_modules`, `dist`, `.env` |
| Nginx config | `frontend/nginx/nginx.conf` | Reverse proxy + static file serving |
| Production compose | `docker-compose.yml` (replace existing) | Full stack with backend + nginx |
| Dev compose | `docker-compose.dev.yml` | Infrastructure only (current compose content) |
| Env template | `.env.example` | Documented configuration template |
| Deploy docs | (optional) | Production deployment guide |

### Modified Components

| Component | File | Change | Why |
|-----------|------|--------|-----|
| SkillSandbox | `backend/app/services/skill/sandbox.py` | Add `network` parameter to container creation | Skill containers must join compose network for DNS resolution |
| CORS config | `backend/app/core/config.py` | Change `cors_origins` default | Not strictly needed (same-origin via Nginx), but the default should not hardcode `localhost:5173` for production |
| Redis port | `docker-compose.yml` | Change `6380:6379` to `6379:6379` | The non-standard port 6380 was for local dev to avoid conflict with system Redis. In containers, use standard port. Only applies to dev compose. |

### Unchanged Components

| Component | Why No Change Needed |
|-----------|---------------------|
| Frontend `api-client.ts` | Uses relative URLs (`/api/v1/*`) -- works behind any proxy |
| Frontend `use-websocket.ts` | Uses `window.location.host` -- resolves to Nginx origin |
| Backend `main.py` | Application code is environment-agnostic; config via env vars |
| Backend `config.py` | Pydantic-settings reads env vars, works in containers |
| Backend `alembic/env.py` | Reads `settings.database_url` from env, no code change |
| Backend `session.py` | Engine configured from `settings.database_url`, no code change |
| Backend `health.py` | `/health` endpoint works as-is for container healthchecks |
| All backend services | No code changes needed (auth, agent engine, MCP, memory) |

## Build Order (Dependency-Aware)

Based on the analysis, the containerization milestone should proceed in this order:

```
Phase 1: Preserve existing workflow (no risk of breakage)
  1.1 Rename existing docker-compose.yml to docker-compose.dev.yml
  1.2 Verify docker-compose.dev.yml works identically to current setup
  1.3 Create .env.example

Phase 2: Backend containerization (backend must work standalone first)
  2.1 Create backend/.dockerignore
  2.2 Create backend/Dockerfile (multi-stage with uv)
  2.3 Create backend/entrypoint.sh (Alembic migrations + uvicorn)
  2.4 Test: docker build + run backend container with dev infrastructure
  2.5 Modify SkillSandbox sandbox.py to accept network parameter

Phase 3: Frontend containerization + Nginx (needs working backend)
  3.1 Create frontend/.dockerignore
  3.2 Create frontend/nginx/nginx.conf
  3.3 Create frontend/Dockerfile (multi-stage: Node build + Nginx)
  3.4 Test: docker build frontend, verify static files served correctly

Phase 4: Production docker-compose.yml (integration)
  4.1 Create new docker-compose.yml (all services + networking)
  4.2 Test: docker-compose up (full stack)
  4.3 Test: WebSocket streaming through Nginx
  4.4 Test: Skill sandbox (Docker socket mount + network)
  4.5 Test: Backend healthcheck + service dependency ordering

Phase 5: Hardening and documentation
  5.1 Resource limits (mem_limit, cpus) for each service
  5.2 Restart policies
  5.3 Production deployment guide
  5.4 SSL/TLS configuration notes (for future HTTPS setup)
```

**Ordering rationale:**
- Phase 1 first because renaming the compose file is zero-risk and ensures developers can continue working
- Phase 2 before Phase 3 because the frontend Nginx config needs a running backend to test proxy rules
- Phase 4 integrates everything and validates the full stack
- Phase 5 is polish that doesn't block the "it works" milestone

## Scalability Considerations

| Concern | Single Host (v1) | Multi-Host (v2+) |
|---------|-------------------|-------------------|
| **Backend replicas** | Single container, sufficient for MVP | `docker-compose up --scale backend=3` with Nginx load balancing. WebSocket sessions need sticky sessions or Redis pub/sub (already implemented) |
| **Nginx** | Single container | Redundant Nginx with keepalived VIP, or cloud load balancer |
| **PostgreSQL** | Single container, named volume | External managed DB (RDS/CloudSQL) or Postgres replicas |
| **Skill sandbox** | Docker socket mount on same host | Kubernetes-based sandbox with dedicated worker nodes |
| **Static files** | Baked into Nginx image | CDN (CloudFront, Cloudflare) for static assets, Nginx for API only |
| **SSL/TLS** | Not in v1 scope | Nginx with certbot/Let's Encrypt or cloud-managed certificates |

## Sources

- Existing codebase analysis: `docker-compose.yml`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/services/skill/sandbox.py`, `frontend/vite.config.ts`, `frontend/src/lib/api-client.ts`, `frontend/src/hooks/use-websocket.ts` (HIGH confidence -- direct code analysis)
- Docker multi-stage build patterns: Docker official documentation (HIGH confidence -- well-established patterns)
- Nginx WebSocket proxy: Nginx official documentation, `proxy_set_header Upgrade` + `Connection "upgrade"` pattern (HIGH confidence -- standard configuration)
- Nginx SPA routing: `try_files $uri $uri/ /index.html` pattern for client-side routing (HIGH confidence -- standard practice)
- Docker socket mount for sibling containers: Docker documentation, widely used in CI/CD and sandbox patterns (HIGH confidence)
- `uv` Docker integration: `ghcr.io/astral-sh/uv` image and `uv sync` documentation (HIGH confidence -- official Astral documentation)
- Vite hashed asset output: Vite documentation for production builds (HIGH confidence)
