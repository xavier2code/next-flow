# Feature Research

**Domain:** Docker containerization and production deployment for FastAPI + React Agent platform (v1.1 milestone)
**Researched:** 2026-03-31
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in a "Docker-ready" product. Missing these = deployment feels broken or amateurish.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Backend Dockerfile (multi-stage) | Every Python service ships with a Dockerfile. Single-stage builds are a red flag for production readiness. | LOW | Python 3.12-slim builder stage, python:3.12-slim runtime. Use `uv` for installs since project already has uv.lock. Copy dependencies via `--prefix=/install`. |
| Frontend Dockerfile (multi-stage) | React apps are built to static files. A Dockerfile that runs `npm run build` then serves via Nginx is the industry standard. | LOW | Stage 1: node:22-alpine, `npm ci`, `npm run build`. Stage 2: nginx:alpine, copy dist/ to /usr/share/nginx/html. |
| Nginx reverse proxy (unified entry point) | Production deployments never expose backend ports directly. A single port 80/443 entry point with path-based routing is expected. | MEDIUM | Three location blocks: `/` (SPA static files), `/api/v1/` (proxy to backend:8000), `/ws/` (WebSocket proxy to backend:8000). Requires `proxy_http_version 1.1` and `Upgrade`/`Connection` headers for WebSocket. |
| Nginx SPA fallback routing | React Router client-side routes return 404 on refresh without `try_files $uri $uri/ /index.html`. This is the number one SPA-in-Docker mistake. | LOW | Single line in nginx.conf, but catastrophic if missing. Every client-side route (login, chat, settings) breaks on page refresh. |
| Nginx WebSocket proxy | NextFlow's core value is streaming agent responses via WebSocket at `/ws/chat`. If WebSocket does not connect through Nginx, the product is fundamentally broken. | MEDIUM | Requires specific headers: `Upgrade $http_upgrade`, `Connection "upgrade"`, `proxy_http_version 1.1`. Timeout must be high (`proxy_read_timeout 86400s`) to avoid disconnects during long agent runs. |
| Production docker-compose.yml | The milestone goal is literally "`docker-compose up` brings up the entire stack". Without this, the milestone fails. | MEDIUM | Must include: backend, frontend (nginx), postgres, redis, minio. Service dependencies with health checks. Restart policies. Resource limits optional for P1. |
| Development docker-compose separation | Developers need hot-reload, bind mounts, and debug tools. Production needs none of those. Mixing them causes pain on both sides. | LOW | Keep existing docker-compose.yml as infrastructure-only (dev). Create docker-compose.prod.yml for full-stack production. Alternatively, rename existing to docker-compose.dev.yml. |
| Health check endpoint for backend | Docker, Kubernetes, and load balancers all need to know if the service is alive. Without it, orchestrators cannot manage the container. | LOW | Already exists at `/api/v1/health` (checks Redis, returns 200 or 503). Add Docker HEALTHCHECK instruction. Use Python `urllib` to avoid installing curl in slim image. |
| Environment variable management (.env templates) | Operators need to know what to configure. `.env.example` with all variables documented is the minimum for any deployable product. | LOW | Backend already has `.env.example`. Need production-specific template with Docker-internal hostnames (postgres, redis, minio instead of localhost). |
| .dockerignore files | Builds that copy `.venv/`, `node_modules/`, or `.git/` into the Docker context are slow and bloated. This signals carelessness. | LOW | Backend: exclude `.venv`, `__pycache__`, `.env`, `.pytest_cache`. Frontend: exclude `node_modules`, `dist`. Two small files, significant build speed impact. |
| Non-root user in containers | Running as root inside containers is a security anti-pattern. Orchestration platforms and security scanners flag it immediately. | LOW | `RUN groupadd -r appuser && useradd -r -g appuser appuser` then `USER appuser` in both Dockerfiles. Backend needs writable `/app` directory. Nginx alpine already runs as non-root with minor config. |
| Graceful shutdown | `docker stop` sends SIGTERM. Uvicorn must finish in-flight requests before exiting, especially WebSocket connections mid-stream. | MEDIUM | Use CMD exec form (not shell form) so uvicorn is PID 1 and receives signals. Set `--graceful-timeout` on uvicorn. Set `stop_grace_period: 30s` in docker-compose. FastAPI lifespan already handles cleanup in main.py. |
| Alembic migration on startup | Database schema must match code version. If migrations are manual, operators will forget and the app will crash on schema mismatch. | MEDIUM | Entrypoint script runs `alembic upgrade head` before uvicorn starts. Requires PostgreSQL to be healthy first (depends_on with condition). |

### Differentiators (Competitive Advantage)

Features that elevate the deployment from "it works" to "production-grade". Not strictly required for the milestone, but signal quality and operational maturity.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Gzip compression in Nginx | Reduces static asset transfer by 60-80%. Faster page loads, lower bandwidth costs. | LOW | Add `gzip on; gzip_types text/css application/javascript application/json image/svg+xml;` to nginx.conf. Nginx alpine has gzip module built in. |
| Static asset long-term caching | Vite produces content-hashed filenames (e.g., `main.a1b2c3.js`). These can be cached for a year with zero staleness risk. | LOW | Nginx location block for hashed assets gets `Cache-Control: public, max-age=31536000, immutable`. index.html gets `no-cache`. Works with Vite's default filename hashing. |
| Security headers in Nginx | X-Frame-Options, X-Content-Type-Options, Content-Security-Policy. Security-conscious enterprises check for these in audits. | LOW | Add `add_header` directives in nginx.conf. Five minutes of work, significant compliance value. |
| Docker health check ordering with `condition` | Services that depend on PostgreSQL failing because Postgres is "up" but not "ready" is a common Docker pain point. Health-check-based `depends_on` fixes this. | LOW | Already partially done in existing compose (postgres, redis, minio have healthchecks). Backend service should use `depends_on: postgres: { condition: service_healthy }`. Ensures Alembic does not run before DB is accepting connections. |
| Resource limits (deploy.resources) | Unbounded containers can OOM-kill the host. Setting memory/CPU limits per service prevents noisy neighbor problems in shared environments. | LOW | `deploy.resources.limits.memory: 512M` for backend, `256M` for Nginx, `1G` for PostgreSQL. Low effort, high safety value. |
| Readiness vs liveness health endpoints | Kubernetes and sophisticated load balancers distinguish "process is alive" (liveness) from "can serve traffic" (readiness). Separate endpoints enable zero-downtime deploys. | MEDIUM | Current `/api/v1/health` checks Redis. Add `/api/v1/ready` that checks Redis + PostgreSQL + MinIO. Liveness stays lightweight (just process check via /health). |
| Nginx access logging with structured format | Structured access logs (JSON) integrate with centralized logging systems (ELK, Loki, CloudWatch). | LOW | Configure Nginx `log_format` with JSON output. Low effort, high operational value when debugging production issues. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good for Docker deployments but create problems. Documented to prevent scope creep.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Alpine-based Python images | "Smaller images -- alpine is 5MB vs slim's 150MB" | Alpine uses musl libc instead of glibc. Many Python packages (numpy, cryptography, psycopg) lack musl wheels and must compile from source, making builds slower and images larger. The size savings evaporate. | Use `python:3.12-slim` (Debian-based, glibc, pre-built wheels). Image is larger but builds faster and runs reliably. |
| Docker-in-Docker (DinD) for skill sandbox | "Security isolation -- do not mount the host Docker socket" | DinD is complex, fragile, and itself a security concern. It requires privileged mode, has storage driver issues, and makes debugging extremely hard. The Docker team explicitly discourages it. | Mount Docker socket read-only (`/var/run/docker.sock:ro`). Skill sandbox containers already run with security hardening (cap_drop ALL, no-new-privileges, read-only fs). The risk is bounded and documented. |
| Single combined Dockerfile for frontend+backend | "Simpler -- one Dockerfile, one container" | Couples build lifecycles. Frontend JS changes trigger full Python rebuild. Backend Python changes trigger npm install. Violates separation of concerns. Debugging is harder. Independent scaling is impossible. | Separate Dockerfiles for backend and frontend. Nginx container serves frontend static files and proxies to backend. |
| SSL/TLS termination in Nginx container (for this milestone) | "HTTPS in Docker" | Certificate management (Let's Encrypt, renewal, cert storage) adds significant complexity. For the milestone scope, TLS should be handled by an external load balancer or reverse proxy (cloud provider, Traefik, Caddy). | Handle TLS at the infrastructure layer (cloud LB, Traefik, Caddy). Nginx listens on HTTP internally. Document how to add TLS externally. |
| Docker Compose Watch for production | "Auto-sync files into running containers" | Watch is a development feature. Production containers should be immutable. Hot-patching production containers leads to configuration drift and unreproducible states. | Use Watch only in `docker-compose.override.yml` (dev). Production uses baked-in code with no bind mounts. |
| Gunicorn + Uvicorn workers | "Production WSGI best practice" | Gunicorn is a WSGI server. Using it with Uvicorn workers adds a process manager but complicates signal handling and adds overhead. For the MVP scale, Uvicorn with `--workers` is sufficient. Gunicorn adds value only at more than 10 workers. | Use `uvicorn app.main:app --workers 4` directly. Revisit Gunicorn if horizontal scaling beyond single-machine is needed. |
| Docker secrets (Docker Swarm) | "Secure secret management" | Docker secrets require Swarm mode, which adds operational complexity. For a `docker-compose up` deployment, environment variables with `.env` files are sufficient. | Use `.env` files with restrictive file permissions. For Kubernetes, use K8s Secrets. Document that Swarm secrets are a future option. |
| Kubernetes manifests in this milestone | "Production = Kubernetes" | K8s manifests are a separate deliverable with significant complexity (Ingress, Services, Deployments, PVCs, ConfigMaps, Secrets). The milestone goal is `docker-compose up`, not Kubernetes. | Scope K8s manifests for v1.2. Current milestone focuses on Docker Compose production readiness. K8s can consume the same Docker images built here. |
| Docker image vulnerability scanning | "Security scanning in CI" | Worthwhile but belongs in CI/CD pipeline, not in the Docker deployment milestone. Adds CI tooling scope (Trivy, Snyk, Docker Scout) that is separate from making `docker-compose up` work. | Add to CI pipeline as a follow-up task. The Dockerfiles built here will be what gets scanned. |

## Feature Dependencies

```
Backend Dockerfile
    +--requires--> .dockerignore (backend)
    +--requires--> Health check endpoint (already exists: /api/v1/health)
    +--requires--> Entrypoint script (Alembic migration + uvicorn startup)
    +--uses--> uv package manager (uv.lock already exists in project)

Frontend Dockerfile
    +--requires--> .dockerignore (frontend)
    +--requires--> Vite build produces dist/ (verified working, 938KB bundle)
    +--feeds--> Nginx container (dist/ output copied to Nginx image)

Nginx Configuration
    +--requires--> Frontend Dockerfile (needs dist/ output)
    +--requires--> Backend Dockerfile (needs backend service to proxy to)
    +--requires--> WebSocket route knowledge (/ws/chat endpoint)

Production docker-compose
    +--requires--> Backend Dockerfile
    +--requires--> Frontend+Nginx Dockerfile (single container approach)
    +--requires--> Existing infrastructure services (postgres, redis, minio)
    +--requires--> Docker socket mount (for skill sandbox via docker.from_env())
    +--requires--> .env template for production

Alembic migration on startup
    +--requires--> Backend Dockerfile (entrypoint script)
    +--requires--> PostgreSQL connectivity (depends_on with service_healthy)
    +--enhances--> Production reliability (schema always matches code)

Docker socket mount
    +--required_by--> Skill sandbox (docker.from_env() in SkillSandbox class)
    +--conflicts--> Strict container isolation (documented trade-off)

Dev/Prod compose separation
    +--requires--> Production docker-compose (new file)
    +--preserves--> Existing docker-compose.yml as dev infrastructure
```

### Dependency Notes

- **Production compose requires all Dockerfiles and Nginx config:** This is the integration layer. It must be built after individual components are tested. It should be the last thing assembled.
- **Docker socket mount is required for skill sandbox:** `docker.from_env()` in `backend/app/services/skill/sandbox.py` needs access to the host Docker daemon. This is non-negotiable for the existing skill system. Read-only mount limits (but does not eliminate) the attack surface.
- **Alembic migration on startup requires PostgreSQL to be ready:** Must use `depends_on: postgres: { condition: service_healthy }` to ensure DB is accepting connections before migration runs. The existing postgres health check (`pg_isready`) handles this.
- **Dev/Prod separation depends on production compose:** The existing docker-compose.yml is dev-only (infrastructure services). The new production compose adds app services on top. No conflict -- they serve different purposes.
- **Frontend Dockerfile output feeds Nginx:** Two viable approaches: (1) multi-stage build in a single Dockerfile that includes Nginx (simpler, recommended), or (2) separate Nginx container that copies frontend dist from a builder stage. Approach 1 results in one container for frontend+Nginx, which is simpler for operators.
- **Graceful shutdown ties to existing lifespan:** The backend main.py already has a comprehensive lifespan context manager that handles cleanup (skill manager, MCP manager, pubsub, checkpointer, store, redis, engine). Docker SIGTERM triggers this via uvicorn. No code changes needed -- just correct CMD form and stop_grace_period.

## MVP Definition

### Launch With (v1.1 -- Docker Deployment Milestone)

Minimum viable Docker deployment -- `docker compose up` brings up the entire NextFlow stack ready to use.

- [ ] Backend Dockerfile -- multi-stage (uv install + runtime), non-root user, HEALTHCHECK instruction, entrypoint script. Essential: this is the backend container.
- [ ] Frontend+Nginx Dockerfile -- multi-stage (node build to nginx serve), includes Nginx config. Essential: this serves the frontend.
- [ ] Nginx configuration -- SPA fallback, gzip, API proxy `/api/v1/` to backend, WebSocket proxy `/ws/` to backend with upgrade headers. Essential: without this the frontend cannot communicate with the backend.
- [ ] Production docker-compose.yml -- all services (backend, frontend-nginx, postgres, redis, minio) with health checks, restart policies, service dependencies (condition: service_healthy). Essential: this IS the milestone.
- [ ] Development compose separation -- existing docker-compose.yml stays as dev infrastructure. New compose file for production. Essential: prevents dev/prod confusion.
- [ ] .env.example for production -- template with Docker-internal hostnames (postgres, redis, minio), documented variables, security warnings for secrets. Essential: operators need to know what to configure.
- [ ] .dockerignore files -- exclude unnecessary files from build context for both backend and frontend. Essential: build speed and image size.
- [ ] Alembic migration on startup -- entrypoint script runs `alembic upgrade head` before uvicorn. Essential: schema must match code version on every deploy.
- [ ] Docker socket mount -- documented in compose for skill sandbox (read-only). Essential: skill system is a core feature that depends on Docker API access.

### Add After Validation (v1.x)

- [ ] Readiness vs liveness health endpoints -- add `/api/v1/ready` for deep dependency checks. Trigger: Kubernetes migration or zero-downtime deploy requirements.
- [ ] Gzip compression in Nginx -- performance optimization for static assets. Trigger: page load speed benchmarking.
- [ ] Static asset caching headers -- leverage Vite content hashing for immutable caching. Trigger: production traffic analysis.
- [ ] Security headers (CSP, X-Frame-Options, X-Content-Type-Options) -- compliance requirement. Trigger: security audit or enterprise customer request.
- [ ] Resource limits in compose -- `deploy.resources.limits` per service. Trigger: production deployment or multi-tenant hosting.
- [ ] Structured Nginx access logs -- JSON format for log aggregation. Trigger: centralized logging integration.

### Future Consideration (v2+)

- [ ] Kubernetes manifests (Deployments, Services, Ingress, PVCs) -- different orchestration layer, same Docker images.
- [ ] TLS termination -- Let's Encrypt with cert-manager in K8s or Caddy as reverse proxy.
- [ ] Docker image vulnerability scanning (Trivy, Snyk) in CI pipeline.
- [ ] Docker Compose profiles for optional services (Qdrant when RAG is added, Celery workers when enabled).
- [ ] Horizontal scaling -- multiple backend replicas with Redis pub/sub for WebSocket fan-out.
- [ ] Image publishing to container registry (GHCR, ECR).
- [ ] Init containers for migration (K8s pattern instead of entrypoint script).

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Backend Dockerfile (multi-stage, non-root, health check) | HIGH | LOW | P1 |
| Frontend+Nginx Dockerfile (multi-stage) | HIGH | LOW | P1 |
| Nginx config (SPA fallback + API proxy + WebSocket) | HIGH | MEDIUM | P1 |
| Production docker-compose.yml | HIGH | MEDIUM | P1 |
| .env.example for production | HIGH | LOW | P1 |
| .dockerignore files | MEDIUM | LOW | P1 |
| Dev/prod compose separation | HIGH | LOW | P1 |
| Alembic migration on startup | HIGH | MEDIUM | P1 |
| Docker socket mount (skill sandbox) | HIGH | LOW | P1 |
| Health check in Dockerfile | MEDIUM | LOW | P1 |
| Non-root user in containers | MEDIUM | LOW | P1 |
| Graceful shutdown (stop_grace_period + CMD exec form) | MEDIUM | LOW | P1 |
| Gzip compression in Nginx | LOW | LOW | P2 |
| Static asset caching headers | LOW | LOW | P2 |
| Security headers in Nginx | MEDIUM | LOW | P2 |
| Resource limits in compose | MEDIUM | LOW | P2 |
| Readiness vs liveness endpoints | LOW | MEDIUM | P2 |
| Structured Nginx access logs | LOW | LOW | P2 |

**Priority key:**
- P1: Must have for launch -- the milestone goal is `docker-compose up` for full stack
- P2: Should have, add when possible -- quality-of-life and production hardening improvements

## NextFlow-Specific Architecture Constraints

### Docker Socket Requirement

The skill sandbox system (`SkillSandbox` class in `backend/app/services/skill/sandbox.py`) uses `docker.from_env()` to create and manage sibling containers. This is a hard constraint that affects the production Docker setup:

1. **The backend container MUST have access to the Docker daemon socket.**
2. **Implementation:** Mount `/var/run/docker.sock:/var/run/docker.sock` in the backend service (read-only recommended).
3. **Security implication:** The backend process can create containers on the host Docker daemon. This is mitigated by:
   - Running backend as non-root user (limits socket access to Docker group membership)
   - Skill containers already use security hardening (cap_drop ALL, no-new-privileges, read-only fs, pids_limit)
   - Read-only socket mount (`:ro`) prevents the backend from modifying the Docker daemon configuration
4. **Alternative (future):** Docker-in-Docker (DinD), Podman socket, or Kaniko. Not recommended for v1.1 due to complexity.

### Uv Package Manager

The backend uses `uv` for dependency management (uv.lock exists, pyproject.toml is the source of truth). The Dockerfile should use `uv` for faster, more reliable installs:

```
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
```

This is faster than `pip install` and produces reproducible builds via the lockfile. The uv binary can be copied from the official uv Docker image.

### Existing Health Check Endpoint

The backend already has `/api/v1/health` (in `backend/app/api/v1/health.py`) which checks Redis connectivity. Returns 200 with `{"status": "healthy", "redis": "connected"}` or 503 with `{"status": "degraded", "redis": "disconnected"}`.

For Docker HEALTHCHECK, use Python's built-in `urllib` (no curl needed in slim image):
```
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"
```

### Vite Dev Proxy Already Configured

The frontend's `vite.config.ts` already proxies `/api/v1` to `localhost:8000` and `/ws` to `ws://localhost:8000`. In production, Nginx replaces this proxy function. The Vite proxy config is only used during `npm run dev` and has no effect in the production Docker build.

### Environment Variable Hostname Changes

Moving from development to Docker Compose internal networking changes hostnames:
- `localhost:5432` becomes `postgres:5432` (Docker network DNS)
- `localhost:6380` becomes `redis:6379` (Docker network, standard port not remapped)
- `localhost:9000` becomes `minio:9000` (Docker network DNS)
- `localhost:11434` becomes host Docker IP or `host.docker.internal:11434` (for Ollama on host)

The production `.env.example` must use Docker-internal hostnames. CORS origins must change from `http://localhost:5173` to the Nginx entry point (e.g., `http://localhost` or the production domain).

### Existing Docker Compose Infrastructure

The current `docker-compose.yml` defines three infrastructure services: postgres (pgvector:pg16), redis (7-alpine), and minio (latest). All three have health checks configured. The production compose should extend this with application services (backend, frontend-nginx) while keeping the infrastructure definitions. The cleanest approach is a separate compose file that includes everything.

## Sources

- FastAPI Docker deployment guide: https://fastapi.tiangolo.com/deployment/docker/ (HIGH confidence -- official FastAPI docs, well-established patterns)
- Nginx WebSocket proxy documentation: https://nginx.org/en/docs/http/websocket.html (HIGH confidence -- official Nginx docs)
- Docker multi-stage build documentation: https://docs.docker.com/build/building/multi-stage/ (HIGH confidence -- official Docker docs)
- Docker Compose production best practices: https://docs.docker.com/compose/production/ (HIGH confidence -- official Docker docs)
- Uv Docker integration guide: https://docs.astral.sh/uv/guides/integration/docker/ (HIGH confidence -- official uv docs)
- NextFlow PROJECT.md: `.planning/PROJECT.md` -- project definition and milestone goals (HIGH confidence)
- NextFlow backend main.py: `backend/app/main.py` -- lifespan, startup/shutdown, middleware (HIGH confidence -- direct source)
- NextFlow backend config.py: `backend/app/core/config.py` -- all environment variables and defaults (HIGH confidence -- direct source)
- NextFlow existing docker-compose.yml: root `docker-compose.yml` -- infrastructure services (HIGH confidence -- direct source)
- SkillSandbox docker.from_env() usage: `backend/app/services/skill/sandbox.py:39` (HIGH confidence -- direct source)
- Health endpoint: `backend/app/api/v1/health.py` (HIGH confidence -- direct source)
- Frontend vite.config.ts: proxy configuration (HIGH confidence -- direct source)

Note: Web search and web fetch tools were rate-limited during this research session (reset 2026-04-16). All findings are based on well-established Docker/FastAPI/Nginx patterns from official documentation and direct codebase analysis. Confidence is HIGH because this domain (containerizing Python+JS apps) is mature with stable, well-documented best practices.

---
*Feature research for: Docker containerization and production deployment (v1.1 milestone)*
*Researched: 2026-03-31*
