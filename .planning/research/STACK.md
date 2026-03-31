# Technology Stack: Docker Containerization & Production Deployment

**Project:** NextFlow -- Universal Agent Platform
**Milestone:** v1.1 Docker Deployment Readiness
**Researched:** 2026-03-31

## Scope

This document covers ONLY the new stack additions needed for containerizing the existing NextFlow application services and configuring production deployment. The existing application stack (FastAPI 0.135, React 19, Vite 7, PostgreSQL 16, Redis 7, MinIO, LangGraph 1.1) is validated and not re-researched.

**Existing state:** Docker Compose runs infrastructure only (PostgreSQL, Redis, MinIO). No app services are containerized. No Dockerfiles exist. No Nginx config exists.

---

## Recommended Stack

### Base Images

| Image | Version | Purpose | Why | Confidence |
|-------|---------|---------|-----|------------|
| python | 3.12-slim (bookworm) | Backend runtime base | glibc-based, compatible with all Python packages (asyncpg, cryptography, psycopg). Alpine uses musl which breaks pre-built wheels for asyncpg and cryptography, forcing source compilation that inflates build time 10x and image size. Slim is ~50MB vs Alpine's ~20MB but saves hours of build debugging. Pin to `3.12-slim-bookworm` for reproducibility. | HIGH |
| node | 22-alpine | Frontend build stage | Build-only image (not shipped). Alpine is fine for Node.js because npm packages distribute pre-built binaries for both glibc and musl. Smaller download (~180MB vs ~350MB for node:22-slim). Only runs `npm ci && npm run build`, so compatibility risk is near-zero. | HIGH |
| nginx | 1.27-alpine | Reverse proxy + static file server | Reverse proxy for FastAPI backend, static file host for React SPA, WebSocket upgrade routing. Alpine variant is ~25MB. Nginx on Alpine has no compatibility concerns (no Python or Node.js involved). Pin 1.27 minor line (stable mainline as of March 2026). | HIGH |
| pgvector/pgvector | pg16 | PostgreSQL + pgvector extension | Already in use. No change needed. pgvector bundled, avoids separate extension install. | HIGH |
| redis | 7-alpine | Cache + session + pub/sub broker | Already in use. No change needed. | HIGH |
| minio/minio | latest | S3-compatible object storage | Already in use. No change needed. | HIGH |

### Production Server (Backend)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Gunicorn | 23.x | Process manager for Uvicorn workers | Gunicorn provides: (1) multi-worker process management with `uvicorn.workers.UvicornWorker` class, (2) automatic worker restart on crash, (3) graceful reload via HUP signal, (4) `max_requests` to prevent memory leaks in long-running async processes. A single Uvicorn process cannot utilize multiple CPU cores. | HIGH |
| uvicorn[standard] | 0.34+ | ASGI server (worker class) | Already a dependency. The `[standard]` extras include `uvloop` (faster event loop) and `httptools` (faster HTTP parsing). Used as Gunicorn worker class, not standalone. | HIGH |

### Supporting Libraries -- Containerization

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| gunicorn | 23.x | WSGI/ASGI process manager | Production backend. `gunicorn -k uvicorn.workers.UvicornWorker`. NOT for development. | HIGH |
| docker | 7.x (existing) | Docker SDK for Python | Already installed for skill sandbox. Used inside backend container via Docker socket mount. | HIGH |

### Docker Compose Additions

| Service | Image/Build | Purpose | Why Separate Service | Confidence |
|---------|-------------|---------|---------------------|------------|
| backend | build from `backend/Dockerfile` | FastAPI application | Containerized app service. Needs Docker socket mount for skill sandbox. | HIGH |
| frontend | build from `frontend/Dockerfile` | Nginx serving React SPA + reverse proxy | Two-stage: Node.js builds SPA, Nginx serves it and proxies API/WS to backend. Single external port (80/443). | HIGH |

---

## Dockerfile Patterns

### Backend Dockerfile: Multi-Stage Build

The backend Dockerfile has three stages:

1. **Builder stage** -- Install Python dependencies into a virtual environment
2. **Runtime stage** -- Copy venv + app code, minimal image
3. **Security hardening** -- Non-root user, minimal permissions

**Key design decisions:**

- Use `python:3.12-slim-bookworm` (NOT Alpine) as runtime base. The `asyncpg`, `psycopg[binary]`, `cryptography`, and `pwdlib[argon2]` packages all ship pre-built wheels for glibc. On Alpine (musl), these compile from source, inflating build time from ~60s to ~10min and requiring `-dev` packages (`gcc`, `musl-dev`, `libffi-dev`, `postgresql-dev`).
- Use `pip install` with `--no-cache-dir` and copy `pyproject.toml` before source code for Docker layer caching. Dependency install layer only rebuilds when `pyproject.toml` changes.
- Create a non-root user (`nextflow`) with UID 1000. The backend does not need root. The Docker SDK (`docker.from_env()`) communicates via the Docker socket, which is group-accessible.
- Do NOT use `uv` for this project. The backend uses `pyproject.toml` with `[dependency-groups]`, and `uv`'s lockfile would add a new build dependency and lock-in for marginal speed gain in CI. `pip` is sufficient for a single-service build.
- Gunicorn with 2-4 Uvicorn workers (configurable via `WEB_CONCURRENCY` env var). Not `--preload` (causes issues with SQLAlchemy async engines and Redis connections created in lifespan).
- Expose port 8000 (internal). Nginx handles external traffic.
- Health check via `/health` endpoint (already exists in the codebase, checks Redis connectivity).
- The Docker socket (`/var/run/docker.sock`) must be mounted for `SkillSandbox` to create skill containers. This is a security trade-off -- the backend can manage sibling containers.

**Pattern:**

```dockerfile
# ---- Stage 1: Builder ----
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies (needed for psycopg[binary], asyncpg, argon2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency spec first for layer caching
COPY pyproject.toml ./

# Create venv and install dependencies
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN pip install --no-cache-dir ".[dev]" || pip install --no-cache-dir .

# ---- Stage 2: Runtime ----
FROM python:3.12-slim-bookworm AS runtime

# Install runtime dependencies only (no -dev packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r nextflow && useradd -r -g nextflow -d /app -s /sbin/nologin nextflow

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=nextflow:nextflow . .

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER nextflow

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "120", \
     "--max-requests", "5000", \
     "--max-requests-jitter", "500", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Frontend Dockerfile: Multi-Stage Build (Node -> Nginx)

The frontend Dockerfile has three stages:

1. **Builder stage** -- Node.js installs dependencies and builds the Vite SPA
2. **Nginx stage** -- Copies built assets from builder, adds Nginx config
3. Runs as non-root on port 80

**Key design decisions:**

- Use `node:22-alpine` for the build stage. Node.js on Alpine works fine because npm packages ship pre-built musl binaries. Build stage is discarded, so image size does not matter.
- Use `nginx:1.27-alpine` for the runtime. Nginx on Alpine is battle-tested and ~25MB.
- The Vite build output goes to `/usr/share/nginx/html`. Nginx serves static files directly.
- The Nginx config is baked into the image (not mounted). This makes the image self-contained. Config changes require image rebuild, which is correct for production.
- The frontend already uses relative API paths (`/api/v1/...` in `api-client.ts`, `/ws/chat` in `use-websocket.ts`). The WebSocket URL uses `window.location.host` for protocol detection. No environment variable injection needed at build time -- Nginx handles routing.
- Do NOT use `VITE_API_URL` or any build-time env vars. The frontend is deployed behind the same Nginx that proxies the backend. Relative paths work. Build once, deploy anywhere.

**Pattern:**

```dockerfile
# ---- Stage 1: Build React SPA ----
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency files first for layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Nginx + SPA + Reverse Proxy ----
FROM nginx:1.27-alpine

# Copy built SPA assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/nextflow.conf /etc/nginx/conf.d/default.conf

# Remove default Nginx config (already replaced by copy above)
RUN rm -f /etc/nginx/conf.d/default.conf.bak

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

Nginx serves three roles in a single container:

1. **Static file server** for the React SPA (`/usr/share/nginx/html`)
2. **Reverse proxy** for REST API calls (`/api/v1/*` -> `backend:8000`)
3. **WebSocket proxy** for streaming (`/ws/*` -> `backend:8000`)

**Key design decisions for Nginx config:**

- `proxy_http_version 1.1` is required for WebSocket upgrade.
- `proxy_set_header Upgrade` and `Connection "upgrade"` are required for WebSocket handshake.
- `proxy_read_timeout 86400s` prevents Nginx from closing long-lived WebSocket connections. The default 60s timeout would kill idle chat connections.
- `proxy_buffering off` for `/ws/*` ensures streaming events are forwarded immediately, not batched.
- SPA fallback: `try_files $uri $uri/ /index.html` for client-side routing (React Router).
- Static asset caching: `location /assets/` with `expires 1y` for Vite-hashed filenames.
- Do NOT configure SSL in Nginx for this milestone. SSL termination should happen at a load balancer or external reverse proxy in production. This Nginx handles HTTP only within the Docker network.
- The `client_max_body_size 50m` is needed for skill package uploads via the MCP/Skills API.
- Gzip compression for API responses and static files reduces bandwidth.

**Pattern (`nextflow.conf`):**

```nginx
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 50m;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;

    # --- API reverse proxy ---
    location /api/v1/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # --- WebSocket proxy ---
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_buffering off;
    }

    # --- Static assets with long cache (Vite hashed filenames) ---
    location /assets/ {
        root /usr/share/nginx/html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # --- SPA fallback ---
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # --- Health check endpoint (Nginx-level) ---
    location /nginx-health {
        access_log off;
        return 200 "ok";
        add_header Content-Type text/plain;
    }
}
```

### Docker Compose: Production Configuration

The production `docker-compose.yml` extends the existing infrastructure-only compose with app services.

**Key design decisions:**

- **Service dependencies with health checks**: `backend` depends on `postgres` and `redis` being healthy (not just started). `frontend` (nginx) depends on `backend` being healthy. This ensures ordered startup.
- **No port exposure for backend**: Backend only exposes port 8000 within the Docker network. Nginx (frontend service) is the single external entry point on port 80.
- **Docker socket mount**: The backend service mounts `/var/run/docker.sock` for `SkillSandbox` to manage sibling containers. This is scoped to the docker group, not root. This is a deliberate security trade-off: skill sandbox functionality requires container management capability.
- **Named volumes for data persistence**: PostgreSQL data, Redis data, MinIO data persist across `docker-compose down && up`.
- **Restart policy**: `unless-stopped` for all services. Not `always` (which restarts after `docker stop`).
- **Resource limits**: Memory limits prevent runaway containers. Backend gets 1GB (LangGraph + LLM calls can be memory-intensive). Nginx gets 128MB. PostgreSQL gets 512MB.
- **Environment variables**: Injected via `.env` file (already in use). Production overrides via `.env.production` or environment variable injection from the orchestrator.
- **Network**: All services on a shared bridge network (`nextflow-net`). No host networking.
- **Alembic migrations**: Run as a one-shot container before the backend starts: `docker compose run --rm backend alembic upgrade head`. Do NOT bake migrations into the backend startup (migration failures should be explicit, not silent).

**Pattern:**

```yaml
services:
  # ---- Infrastructure (existing) ----
  postgres:
    image: pgvector/pgvector:pg16
    container_name: nextflow-postgres
    environment:
      POSTGRES_USER: nextflow
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-nextflow}
      POSTGRES_DB: nextflow
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nextflow"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nextflow-net

  redis:
    image: redis:7-alpine
    container_name: nextflow-redis
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - nextflow-net

  minio:
    image: minio/minio:latest
    container_name: nextflow-minio
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-nextflow}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-nextflow123}
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
      - nextflow-net

  # ---- Application Services (new) ----
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: nextflow-backend
    env_file:
      - ./backend/.env
    environment:
      DATABASE_URL: postgresql+asyncpg://nextflow:${POSTGRES_PASSWORD:-nextflow}@postgres:5432/nextflow
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      CORS_ORIGINS: '["http://localhost","http://localhost:80"]'
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
    networks:
      - nextflow-net

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: nextflow-frontend
    ports:
      - "${FRONTEND_PORT:-80}:80"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/nginx-health"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 128M
    networks:
      - nextflow-net

volumes:
  postgres_data:
  redis_data:
  minio_data:

networks:
  nextflow-net:
    driver: bridge
```

### Development Docker Compose

Keep the existing `docker-compose.yml` (infrastructure only) for local development. Rename to `docker-compose.dev.yml` or use Docker Compose profiles.

**Pattern:**
- `docker-compose.yml` -- Production (all services, including app)
- `docker-compose.override.yml` -- Development overrides (expose backend port 8000, frontend port 5173, no resource limits)
- OR: Docker Compose profiles (`--profile dev` vs `--profile prod`)

The simplest approach: the existing `docker-compose.yml` becomes the production file. A `docker-compose.override.yml` is auto-merged by Docker Compose when present, and adds development-only ports and settings. Developers add `.override.yml` to `.gitignore` for local customization.

### .dockerignore Files

**Backend `.dockerignore`:**
```
__pycache__
*.pyc
*.pyo
.git
.env
.venv
venv
*.egg-info
.pytest_cache
.mypy_cache
.ruff_cache
tests/
alembic/versions/
*.md
```

**Frontend `.dockerignore`:**
```
node_modules
dist
.git
.env*
*.md
```

### Multi-Environment Configuration

**Pattern: `.env.example` + `.env` (gitignored)**

The backend already uses `pydantic-settings` with `.env` file support. The container environment overrides critical URLs:

| Variable | Development | Production (Docker) | Override Method |
|----------|-------------|---------------------|-----------------|
| `DATABASE_URL` | `localhost:5432` | `postgres:5432` | `environment:` in compose |
| `REDIS_URL` | `localhost:6380/0` | `redis:6379/0` | `environment:` in compose |
| `MINIO_ENDPOINT` | `localhost:9000` | `minio:9000` | `environment:` in compose |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | `["http://localhost"]` | `environment:` in compose |
| `JWT_SECRET_KEY` | `change-me` | Generated per-env | `.env` file |
| `OPENAI_API_KEY` | User's key | Production key | `.env` file (gitignored) |

The `.env` file supplies secrets and API keys. The `environment:` block in compose supplies Docker-network-aware URLs. Pydantic-settings loads `.env` first, then environment variables override. This is the correct precedence for Docker.

---

## Alternatives Considered

### Reverse Proxy

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **Nginx** | Traefik | Traefik is excellent for dynamic service discovery but adds complexity for a 2-service setup. Nginx config is a single file anyone can read. Traefik's auto-discovery and labels are overkill when there are exactly two backend services (static files + API). |
| **Nginx** | Caddy | Caddy has automatic HTTPS via Let's Encrypt, which is compelling. However, NextFlow v1.1 targets Docker deployment behind a load balancer or reverse proxy that handles TLS. Adding Caddy's automatic TLS inside the container creates a layered TLS complexity. Revisit for standalone deployments. |
| **Nginx** | HAProxy | HAProxy is a TCP/HTTP load balancer, not a static file server. Would need a separate file server for the SPA. Nginx handles both in one process. |
| **Nginx** | Caddy (inside container) | Same as above. Caddy's auto-HTTPS is useful for direct internet exposure, but the architecture assumes an external TLS terminator. |

### Process Manager

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **Gunicorn + UvicornWorker** | Uvicorn standalone | Single-process. Cannot utilize multiple CPU cores. No automatic crash recovery. No graceful reload. Acceptable for development, not production. |
| **Gunicorn + UvicornWorker** | Docker-native scaling (`deploy.replicas`) | Docker Compose replicas share the same network and port. Without a process manager, each replica needs a unique port or a separate load balancer. Gunicorn handles worker management within a single container simply. |
| **Gunicorn + UvicornWorker** | Supervisord | Supervisord is a general-purpose process manager. Gunicorn is purpose-built for Python WSGI/ASGI workers with Uvicorn integration. Supervisord would be an extra dependency with no benefit. |

### Python Base Image

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **python:3.12-slim-bookworm** | python:3.12-alpine | Alpine uses musl libc. The `asyncpg`, `psycopg[binary]`, `cryptography`, and `pwdlib[argon2]` packages have no pre-built musl wheels. Compilation from source requires `gcc`, `musl-dev`, `libffi-dev`, `postgresql-dev`, increasing build time 5-10x and adding build tools to the image (or complex multi-stage cleanup). The ~30MB size savings does not justify the build complexity and compatibility risk. |
| **python:3.12-slim-bookworm** | python:3.12 (full) | Full image is ~1GB vs ~50MB for slim. Includes build tools, apt package cache, and unnecessary system libraries. No benefit for production. |
| **python:3.12-slim-bookworm** | distroless/python3 | Distroless has no shell, which means no `docker exec` for debugging, no `curl` for health checks, and no ability to run Alembic migrations as a one-shot command. The security benefit (no shell for attacker) is offset by the operational pain. |
| **python:3.12-slim-bookworm** | chainguard/python | Chainguard images are security-hardened and rootless by default. Worth evaluating for v2, but adds a new base image vendor dependency and may have package compatibility quirks. |

### Node.js Base Image (Build Stage Only)

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **node:22-alpine** | node:22-slim | Build stage only -- image is discarded. Alpine is smaller and faster to pull. Node.js packages work fine on Alpine. |
| **node:22-alpine** | node:22 (full) | 1GB+ for a build-only stage. No benefit. |

## Anti-Recommendations

| Technology | Why Avoid | What to Use Instead |
|------------|-----------|-------------------|
| **Alpine for Python runtime** | musl libc breaks pre-built wheels for asyncpg, psycopg, cryptography. Build time 5-10x longer. Hidden runtime issues (threading behavior differs under musl). | `python:3.12-slim-bookworm` -- glibc, compatible, fast builds. |
| **Distroless for backend** | No shell means no health checks, no `docker exec` debugging, no Alembic migration commands. Operational pain outweighs security benefit for v1.1. | `python:3.12-slim-bookworm` with non-root user. |
| **Root user in containers** | Container escape exploits gain root on host if user is root inside container. Defense-in-depth requires non-root. | `USER nextflow` with UID 1000 in both Dockerfiles. |
| **Build-time env vars for frontend** | `VITE_API_URL` baked into the JS bundle means different images for different environments. Breaks "build once, deploy anywhere." | Relative paths (`/api/v1/...`) + Nginx routing. Build once. |
| **SSL in Nginx container** | TLS should terminate at the load balancer / ingress controller, not inside the application container. Double TLS adds latency and certificate management complexity. | HTTP inside Docker network. TLS at the edge (load balancer, Cloudflare, AWS ALB). |
| **`docker-compose up` for production** | Docker Compose is acceptable for single-host deployment but is not a production orchestrator. No auto-scaling, no rolling updates, no service mesh. | Docker Compose for v1.1 MVP. Plan Kubernetes migration for scale. |
| **`uv` for package management** | The project uses `pip` with `pyproject.toml`. Adding `uv` introduces a new tool dependency, lockfile format, and potential incompatibility with `pyproject.toml` `[dependency-groups]`. The build speed gain (30s vs 5s) is not worth the tooling risk for a single service. | `pip` with `--no-cache-dir` and multi-stage build. |
| **`--preload` in Gunicorn** | Preloading the app before forking workers shares memory but breaks SQLAlchemy async engines (connections created before fork are shared across workers, causing connection pool corruption). The backend's `lifespan` handler creates Redis, checkpointer, store, and MCP connections per-worker. | Default lazy loading. Each worker initializes independently via FastAPI lifespan. |

---

## New Dependencies

### Backend (add to pyproject.toml)

```toml
# Production server
"gunicorn>=23.0.0",
```

Gunicorn is the only new Python dependency. Everything else is already installed.

### Frontend (no new dependencies)

No new npm packages needed. The existing `npm run build` produces the SPA. Nginx serves it.

### Infrastructure (no new images)

No new Docker services. The existing PostgreSQL, Redis, and MinIO containers continue as-is. The two new build contexts (backend/Dockerfile, frontend/Dockerfile) use existing base images.

---

## Security Considerations

| Concern | Mitigation | Priority |
|---------|------------|----------|
| **Docker socket exposure** | Backend mounts `/var/run/docker.sock:ro` (read-only). The Docker SDK only needs to create/manage containers, not modify the daemon. Consider Docker socket proxy ( Tecnativa/docker-socket-proxy) for v2 to restrict API access. | Critical |
| **Non-root containers** | Both Dockerfiles create and use a non-root user (`nextflow`). No process runs as root inside the container. | Critical |
| **Secret management** | `.env` file is gitignored. Production secrets injected via environment variables, not baked into images. | Critical |
| **Image vulnerability scanning** | Use `docker scout` or Trivy in CI to scan images for CVEs before pushing to registry. | High |
| **Network isolation** | All services on `nextflow-net` bridge network. Backend and infrastructure are not exposed to the host. Only Nginx (port 80) is externally accessible. | High |
| **Resource limits** | Memory limits prevent OOM from affecting other containers. Backend: 1GB, Nginx: 128MB, PostgreSQL: 512MB. | Medium |
| **Health checks** | All services have health checks. Docker Compose restarts unhealthy containers. | Medium |

---

## Gunicorn Configuration Details

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `worker_class` | `uvicorn.workers.UvicornWorker` | ASGI support for FastAPI + WebSocket |
| `workers` | `4` (default, overridable via `WEB_CONCURRENCY`) | 2x CPU cores + 1 on 2-core machine. Async workers handle many connections each, so 4 is sufficient. |
| `bind` | `0.0.0.0:8000` | Internal port, Nginx proxies to it |
| `timeout` | `120` | Agent workflow can take 60-90s for complex tool calls. Default 30s would kill workers. |
| `graceful_timeout` | `120` | Time for in-flight requests to complete during shutdown. Matches timeout. |
| `max_requests` | `5000` | Restart workers periodically to prevent memory leaks from LangGraph checkpoint accumulation. |
| `max_requests_jitter` | `500` | Stagger worker restarts so all workers do not restart simultaneously. |
| `access_logfile` | `-` (stdout) | Docker collects stdout as logs. |
| `error_logfile` | `-` (stdout) | Same. |

---

## Migration Strategy

**Current state -> Target state:**

1. Add `gunicorn` to `pyproject.toml` dependencies
2. Create `backend/Dockerfile` (multi-stage, non-root)
3. Create `backend/.dockerignore`
4. Create `frontend/Dockerfile` (multi-stage Node -> Nginx)
5. Create `frontend/.dockerignore`
6. Create `frontend/nginx/nginx.conf` (main config)
7. Create `frontend/nginx/nextflow.conf` (server block)
8. Update `docker-compose.yml` to add `backend` and `frontend` services
9. Create `.env.production.example` template
10. Test: `docker compose up --build`
11. Verify: health checks pass, API accessible via Nginx, WebSocket streaming works, SPA loads

**What does NOT change:**
- Development workflow (local FastAPI + Vite dev server with proxy) stays the same
- Existing `docker-compose.yml` infrastructure services are preserved in-place
- Backend code (no changes needed for containerization)
- Frontend code (relative paths already work behind Nginx)

---

## Sources

- Python Docker official image: https://hub.docker.com/_/python -- `python:3.12-slim-bookworm` tag exists, Debian Bookworm based (HIGH confidence -- official Docker Hub)
- Nginx Docker official image: https://hub.docker.com/_/nginx -- `nginx:1.27-alpine` tag, stable mainline branch (HIGH confidence -- official Docker Hub)
- Node.js Docker official image: https://hub.docker.com/_/node -- `node:22-alpine` tag, LTS line (HIGH confidence -- official Docker Hub)
- Gunicorn Uvicorn workers: https://docs.gunicorn.org/en/stable/settings.html#worker-class -- `uvicorn.workers.UvicornWorker` documented (HIGH confidence -- official Gunicorn docs)
- FastAPI deployment docs: https://fastapi.tiangolo.com/deployment/docker/ -- recommends Gunicorn + UvicornWorker pattern (HIGH confidence -- official FastAPI docs)
- Nginx WebSocket proxying: https://nginx.org/en/docs/http/websocket.html -- `proxy_http_version 1.1` + Upgrade headers required (HIGH confidence -- official Nginx docs)
- Docker Compose healthcheck: https://docs.docker.com/compose/compose-file/05-services/#healthcheck (HIGH confidence -- official Docker docs)
- Docker security best practices: https://docs.docker.com/build/building/best-practices/ -- non-root user, multi-stage builds, .dockerignore (HIGH confidence -- official Docker docs)
- Pydantic Settings env precedence: https://docs.pydantic.dev/latest/concepts/pydantic_settings/ -- env vars override .env file values (HIGH confidence -- official Pydantic docs)
- Existing codebase analysis: `backend/app/core/config.py`, `backend/app/main.py`, `frontend/src/lib/api-client.ts`, `frontend/src/hooks/use-websocket.ts`, `frontend/vite.config.ts` (HIGH confidence -- direct source code review)
- Existing docker-compose.yml: `/docker-compose.yml` -- infrastructure services with health checks (HIGH confidence -- direct file review)
- Backend pyproject.toml: `/backend/pyproject.toml` -- dependency specs (HIGH confidence -- direct file review)

---

*Stack research for: NextFlow v1.1 Docker Containerization & Production Deployment*
*Researched: 2026-03-31*
