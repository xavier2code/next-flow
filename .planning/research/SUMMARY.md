# Project Research Summary

**Project:** NextFlow -- Universal Agent Platform (v1.1 Docker Deployment Milestone)
**Domain:** Containerization and production deployment of an existing FastAPI + React + LangGraph agent platform
**Researched:** 2026-03-31
**Confidence:** HIGH

## Executive Summary

NextFlow is a production-grade agent platform (FastAPI + React + LangGraph + MCP) that currently runs its infrastructure services (PostgreSQL, Redis, MinIO) via Docker Compose but executes the application itself locally. The v1.1 milestone goal is straightforward: `docker-compose up` brings up the entire stack, ready to use. This is a containerization and deployment milestone, not a greenfield architecture exercise. The application code is stable and battle-tested -- the research is exclusively about packaging it correctly behind Nginx with proper dependency ordering, health checks, and security hardening.

The recommended approach is a single Nginx container that serves the React SPA static files and reverse-proxies API/WebSocket traffic to the backend container. This is the industry-standard pattern for SPA + API deployments and requires zero frontend code changes because the existing codebase already uses relative URLs for API calls and dynamic WebSocket URL construction. The backend uses a multi-stage Dockerfile with a non-root user, health checks, and Gunicorn managing Uvicorn workers for production-grade process management. A critical architectural constraint is the Docker socket mount -- the existing `SkillSandbox` class uses `docker.from_env()` to spawn sibling containers, so the backend must mount `/var/run/docker.sock` (read-only) and skill containers must join the compose network for DNS resolution.

The main risks are: (1) WebSocket proxying through Nginx requires specific header configuration (`Upgrade`, `Connection`, `proxy_http_version 1.1`) and long timeouts (`86400s`) -- missing any of these breaks the core streaming feature; (2) service startup ordering must use health-check-based dependencies (`condition: service_healthy`) to prevent the backend from starting before PostgreSQL accepts connections; (3) the skill sandbox network configuration needs a small code change in `sandbox.py` to pass `network="nextflow"` so skill containers can resolve backend DNS. All three risks have well-documented, proven solutions in the research.

## Key Findings

### Recommended Stack

The containerization milestone adds only two new Docker images and one new Python dependency to the existing stack. The research confirms that `python:3.12-slim-bookworm` (not Alpine) is the correct backend base because `asyncpg`, `psycopg[binary]`, `cryptography`, and `pwdlib[argon2]` all lack musl wheels, making Alpine builds 5-10x slower and more fragile. The frontend build stage uses `node:22-alpine` (build-only, discarded), and the runtime is `nginx:1.27-alpine` serving both static files and reverse proxy. Gunicorn is added as the production process manager for Uvicorn workers.

**Core technologies added:**
- **python:3.12-slim-bookworm**: Backend runtime base -- glibc compatibility with all Python packages, avoids Alpine musl compilation issues
- **nginx:1.27-alpine**: Reverse proxy + static file server -- single entry point for API proxy, WebSocket upgrade, and SPA hosting
- **node:22-alpine**: Frontend build stage -- discarded after build, Alpine works fine for Node.js
- **Gunicorn 23.x + UvicornWorker**: Production ASGI process manager -- multi-worker, graceful restart, memory leak prevention via `max_requests`

**One new dependency:** `gunicorn>=23.0.0` in `pyproject.toml`. Everything else is already installed.

### Expected Features

**Must have (table stakes -- the milestone definition):**
- Backend Dockerfile (multi-stage, non-root, health check, entrypoint) -- containerizes the FastAPI application
- Frontend+Nginx Dockerfile (multi-stage: Node build to Nginx serve) -- serves React SPA and proxies API/WS
- Nginx configuration (SPA fallback, API proxy, WebSocket proxy with upgrade headers) -- the critical integration layer
- Production docker-compose.yml (all services, health-check dependencies, restart policies) -- the milestone deliverable
- Dev/prod compose separation -- existing compose becomes `docker-compose.dev.yml`, new compose is production
- `.env.example` for production -- Docker-internal hostnames, documented variables
- `.dockerignore` files -- build speed and image size
- Alembic migration on startup -- schema matches code version on every deploy
- Docker socket mount -- required by `SkillSandbox` for skill container management

**Should have (differentiators -- production hardening):**
- Gzip compression in Nginx -- 60-80% static asset transfer reduction
- Static asset long-term caching -- leverages Vite content-hashed filenames
- Security headers (X-Frame-Options, X-Content-Type-Options) -- compliance value
- Resource limits per service -- prevents noisy neighbor problems
- Readiness vs liveness health endpoints -- enables zero-downtime deploys

**Defer (v2+):**
- Kubernetes manifests -- same Docker images, different orchestration
- SSL/TLS termination in container -- handle at infrastructure layer
- Docker image vulnerability scanning in CI -- separate pipeline concern
- Horizontal scaling (multiple backend replicas) -- needs Redis pub/sub WebSocket fan-out

### Architecture Approach

The architecture adds a unified Nginx container as the single external entry point (port 80). Internally, Nginx routes `/api/v1/*` and `/ws/*` to the backend container (port 8000, internal only), and serves React SPA static files from `/usr/share/nginx/html`. The backend container mounts the Docker socket read-only for skill sandbox functionality. All services communicate over a shared bridge network (`nextflow-net`). Service startup uses health-check-based ordering: infrastructure services start first, backend waits for all three to be healthy, Nginx starts in parallel with backend.

**Major components:**
1. **Nginx (frontend container)** -- Serves React SPA, reverse-proxies API and WebSocket to backend, handles SPA routing fallback, gzip compression, static asset caching
2. **Backend container** -- FastAPI + Gunicorn/Uvicorn workers, non-root user, health check endpoint, Alembic migration entrypoint, Docker socket mount
3. **Infrastructure services** -- PostgreSQL (pgvector), Redis, MinIO (existing, unchanged except network configuration)
4. **Skill sandbox (Docker socket)** -- Sibling containers spawned via host Docker daemon, need `network="nextflow"` parameter added

### Critical Pitfalls

1. **WebSocket proxy misconfiguration** -- Missing `proxy_http_version 1.1`, `Upgrade`, or `Connection "upgrade"` headers in Nginx breaks streaming (the core product feature). Use the exact Nginx WebSocket proxy pattern documented in ARCHITECTURE.md with `proxy_read_timeout 86400s`.

2. **Backend starting before PostgreSQL is ready** -- `depends_on` without `condition: service_healthy` causes Alembic migration failure on startup. Use health-check-based dependencies in docker-compose.yml.

3. **Skill sandbox network isolation** -- Skill containers spawned via Docker socket are on the default bridge network and cannot resolve backend DNS. Requires adding `network="nextflow"` to `SkillSandbox.start_service_container()` in `sandbox.py`.

4. **Alpine for Python runtime** -- musl libc breaks pre-built wheels for asyncpg, psycopg, cryptography. Use `python:3.12-slim-bookworm` for the backend. Alpine is fine for Node.js build stage and Nginx.

5. **Build-time environment variables in frontend** -- `VITE_API_URL` baked into JS bundle requires different images per environment. The existing frontend already uses relative URLs -- no build-time env vars needed.

## Implications for Roadmap

Based on the research, the containerization milestone should be structured as five phases following the dependency chain: preserve existing workflow first, then containerize backend (it must work standalone), then frontend+Nginx (needs backend to test proxy), then integrate via docker-compose, then harden.

### Phase 1: Preserve Development Workflow
**Rationale:** Zero-risk first step. Rename existing docker-compose.yml to docker-compose.dev.yml and verify developers can continue working identically. Prevents any breakage during transition.
**Delivers:** Separated dev/production compose files, `.env.example` template
**Addresses:** Dev/prod compose separation feature
**Avoids:** Developer workflow disruption

### Phase 2: Backend Containerization
**Rationale:** Backend must be containerized and working standalone before frontend/Nginx can be tested against it. The backend is the harder containerization problem (Python dependencies, Docker socket, Alembic migrations, Gunicorn configuration).
**Delivers:** Backend Dockerfile, `.dockerignore`, `entrypoint.sh`, SkillSandbox network fix
**Uses:** `python:3.12-slim-bookworm`, Gunicorn + UvicornWorker, `uv sync --frozen` with multi-stage build
**Implements:** Backend container with non-root user, health check, migration entrypoint
**Avoids:** Alpine Python image (musl wheel issues), `--preload` flag (breaks async SQLAlchemy engines)

### Phase 3: Frontend + Nginx Containerization
**Rationale:** Frontend Dockerfile depends on backend being testable (Nginx proxy needs a backend to proxy to). The Nginx configuration is the most critical integration point -- it must handle SPA routing, API proxying, and WebSocket upgrades correctly.
**Delivers:** Frontend Dockerfile, `.dockerignore`, Nginx configuration (nginx.conf + nextflow.conf)
**Uses:** `node:22-alpine` (build), `nginx:1.27-alpine` (runtime)
**Implements:** Unified Nginx container serving SPA + reverse proxy + WebSocket proxy
**Avoids:** Build-time env vars (frontend uses relative URLs), two separate Nginx containers, embedding frontend in backend

### Phase 4: Production Docker Compose Integration
**Rationale:** The integration phase. Combines all containerized services into a single docker-compose.yml with health-check-based dependency ordering, resource limits, and restart policies. This IS the milestone deliverable.
**Delivers:** Production docker-compose.yml with full stack, verified `docker-compose up` workflow
**Uses:** All Dockerfiles from Phase 2 and 3, named volumes for data persistence, bridge network
**Implements:** Service dependency chain (infra -> backend -> nginx), Docker socket mount for skill sandbox
**Avoids:** Exposing backend port directly (all traffic through Nginx), hardcoded URLs

### Phase 5: Production Hardening
**Rationale:** Polish that doesn't block the "it works" milestone but elevates quality. Gzip, caching headers, security headers, resource limits, structured logging.
**Delivers:** Production-grade Nginx configuration, resource limits, deployment documentation
**Avoids:** Premature optimization (these are quality improvements, not functional requirements)

### Phase Ordering Rationale

- **Phase 1 must come first** because renaming the compose file is zero-risk and ensures no developer is blocked if later phases encounter issues.
- **Phase 2 before Phase 3** because the Nginx proxy configuration in the frontend container needs a running backend to test against -- you cannot verify proxy rules without a backend.
- **Phase 4 is integration** because it requires all Dockerfiles and configs to exist before the full stack can be composed.
- **Phase 5 is last** because hardening does not block the milestone goal (`docker-compose up` working).

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** SkillSandbox `network` parameter change -- needs verification that skill containers can resolve backend DNS on the compose network and that the existing sandbox security constraints (cap_drop, no-new-privileges, read-only fs) are not affected
- **Phase 3:** WebSocket proxy end-to-end verification -- the Nginx config pattern is well-documented, but verifying token-by-token streaming through Nginx requires live testing against the actual backend WebSocket handler
- **Phase 4:** Alembic migration in container startup -- needs testing with the specific migration chain in the project to ensure no migration ordering issues

Phases with standard patterns (skip research-phase):
- **Phase 1:** Renaming files and creating `.env.example` -- trivial, no research needed
- **Phase 2:** Backend Dockerfile -- multi-stage Python Docker builds are the most documented Docker pattern
- **Phase 3:** Frontend Dockerfile -- Node build to Nginx is industry-standard, documented everywhere
- **Phase 5:** Gzip, caching, security headers -- standard Nginx configuration snippets

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All base images are official Docker Hub images with verified tags. Gunicorn+UvicornWorker pattern is the FastAPI-recommended production deployment. Python slim vs Alpine comparison is well-documented. One new dependency (gunicorn). |
| Features | HIGH | Feature list derived from the v1.1 milestone definition in PROJECT.md plus codebase analysis. Every feature maps to a specific file or configuration change. Priority matrix is clear: all P1 features are required for `docker-compose up` to succeed. |
| Architecture | HIGH | Architecture is based on direct codebase analysis (config.py, main.py, api-client.ts, use-websocket.ts, vite.config.ts, sandbox.py, docker-compose.yml). The Nginx proxy pattern is verified against the existing frontend URL construction and backend endpoint structure. No assumptions. |
| Pitfalls | HIGH | Pitfalls are domain-specific (Docker/Nginx/FastAPI) with well-established solutions. WebSocket proxy configuration, Python Alpine compatibility, and service dependency ordering are well-documented issues with proven fixes. The PITFALLS.md research was scoped to the broader NextFlow platform; only the containerization-specific pitfalls apply to this milestone. |

**Overall confidence:** HIGH

### Gaps to Address

- **SkillSandbox network parameter:** The exact implementation of adding `network="nextflow"` to `sandbox.py` needs verification against the existing container creation code. The compose network name depends on the docker-compose project name (defaults to directory name), so the network parameter should use an environment variable (`COMPOSE_NETWORK_NAME`).

- **Gunicorn vs Uvicorn standalone:** STACK.md recommends Gunicorn for multi-worker process management, but ARCHITECTURE.md Pattern 1 uses standalone Uvicorn. The PITFALLS.md notes that Gunicorn adds value only at 10+ workers. Resolution: use Gunicorn for production (Phase 2 STACK.md approach) because it provides graceful restart and memory leak prevention even at 4 workers. The `max_requests` feature alone justifies the addition.

- **uv vs pip for backend Dockerfile:** STACK.md recommends pip with `--no-cache-dir`. ARCHITECTURE.md Pattern 1 recommends `uv sync --frozen`. The project has `uv.lock` and `pyproject.toml`. Resolution: use `uv` since the lockfile already exists and provides reproducible builds. The `uv sync --frozen --no-dev` approach in ARCHITECTURE.md is correct.

- **Alembic migration strategy:** STACK.md recommends a one-shot `docker compose run --rm backend alembic upgrade head` (explicit, separate from startup). ARCHITECTURE.md recommends an `entrypoint.sh` that runs migrations then exec's uvicorn (automatic). Resolution: use the entrypoint script approach (ARCHITECTURE.md Pattern 8) because it is simpler for operators and the `docker compose run` approach requires manual intervention. The migration is idempotent and safe to run on every startup.

## Sources

### Primary (HIGH confidence)
- Docker Hub official images: python:3.12-slim-bookworm, nginx:1.27-alpine, node:22-alpine -- verified tags exist and are current
- FastAPI deployment documentation: https://fastapi.tiangolo.com/deployment/docker/ -- Gunicorn + UvicornWorker pattern
- Nginx WebSocket proxy documentation: https://nginx.org/en/docs/http/websocket.html -- upgrade header requirements
- Docker multi-stage build documentation: https://docs.docker.com/build/building/multi-stage/ -- build patterns
- Docker Compose production best practices: https://docs.docker.com/compose/production/ -- compose configuration
- Uv Docker integration guide: https://docs.astral.sh/uv/guides/integration/docker/ -- `uv sync --frozen` pattern
- Gunicorn settings documentation: https://docs.gunicorn.org/en/stable/settings.html -- worker class configuration
- NextFlow existing codebase: `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/services/skill/sandbox.py`, `frontend/vite.config.ts`, `frontend/src/lib/api-client.ts`, `frontend/src/hooks/use-websocket.ts`, `docker-compose.yml` -- direct source analysis

### Secondary (MEDIUM confidence)
- Nginx SPA fallback pattern -- community standard, `try_files $uri $uri/ /index.html`
- Docker socket security implications -- documented trade-off, accepted for skill sandbox use case
- Vite content hashing for static assets -- Vite documentation, default behavior

### Tertiary (LOW confidence)
- Redis AOF persistence in containers -- recommended but not verified against current Redis config
- Docker socket proxy (Tecnativa) for v2 -- future consideration, not validated

---
*Research completed: 2026-03-31*
*Ready for roadmap: yes*
