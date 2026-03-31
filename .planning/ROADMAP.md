# Roadmap: NextFlow — Universal Agent Platform

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-03-31)
  - [Archive](milestones/v1.0-ROADMAP.md) | [Requirements](milestones/v1.0-REQUIREMENTS.md)
- 🚧 **v1.1 Docker Deployment** — Phases 8-10 (in progress)
- 📋 **v1.2 Vercel AI SDK Integration** — Phase 11 (planned)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-03-31</summary>

- [x] Phase 1: Foundation & Auth (3/3 plans) — completed 2026-03-28
- [x] Phase 2: Agent Engine Core (4/4 plans) — completed 2026-03-29
- [x] Phase 3: Communication Layer (2/2 plans) — completed 2026-03-29
- [x] Phase 4: Memory System (3/3 plans) — completed 2026-03-29
- [x] Phase 5: MCP Integration (3/3 plans) — completed 2026-03-30
- [x] Phase 6: Skill System (3/3 plans) — completed 2026-03-30
- [x] Phase 7: Frontend (4/4 plans) — completed 2026-03-31

</details>

### 🚧 v1.1 Docker Deployment (In Progress)

**Milestone Goal:** `docker-compose up` brings up the entire NextFlow stack (frontend + backend + infrastructure), ready for production use.

- [ ] **Phase 8: Backend Containerization** — Package FastAPI backend into a production-ready Docker container
- [ ] **Phase 9: Frontend + Nginx Containerization** — Build React SPA and serve behind Nginx reverse proxy
- [ ] **Phase 10: Production Compose & Hardening** — Wire all services together with docker-compose.prod.yml and harden for production

### 📋 v1.2 Vercel AI SDK Integration (Planned)

**Milestone Goal:** Replace custom WebSocket streaming with Vercel AI SDK Data Stream Protocol v2 + useChat hook for a more robust, feature-rich chat experience.

- [ ] **Phase 11: Vercel AI SDK Deep Integration** — Replace REST+WebSocket+Redis pub/sub streaming with SSE Data Stream v2 + useChat hook

## Phase Details

### Phase 8: Backend Containerization
**Goal**: The FastAPI backend runs as a standalone Docker container with production-grade process management, automatic database migrations, and health monitoring
**Depends on**: v1.0 complete (Phases 1-7)
**Requirements**: BACK-01, BACK-02, BACK-03, BACK-04, BACK-05, BACK-06
**Success Criteria** (what must be TRUE):
  1. `docker build -t nextflow-backend .` succeeds and the resulting image runs the FastAPI application on port 8000
  2. The backend container starts with a non-root user and Alembic migrations execute automatically before Uvicorn accepts requests
  3. `docker inspect` shows the container's HEALTHCHECK hitting `/api/v1/health` and reporting healthy
  4. Sending SIGTERM to the container completes in-flight requests before shutting down (no dropped connections)
  5. `.dockerignore` prevents `.venv`, `__pycache__`, `.env`, `.pytest_cache`, and `.git` from entering the build context
**Plans**: TBD

Plans:
- [x] 08-01: Backend Dockerfile and .dockerignore
- [x] 08-02: Entrypoint script, health check, and graceful shutdown

### Phase 9: Frontend + Nginx Containerization
**Goal**: The React SPA is built inside Docker and served by Nginx, which also reverse-proxies API and WebSocket traffic to the backend
**Depends on**: Phase 8
**Requirements**: FRNT-01, FRNT-02, FRNT-03, FRNT-04, FRNT-05, FRNT-06
**Success Criteria** (what must be TRUE):
  1. `docker build -t nextflow-frontend .` produces an Nginx-based image serving the React SPA with client-side routing working (page refresh does not return 404)
  2. Nginx proxies `/api/v1/` requests to the backend container and the REST API responds correctly through the proxy
  3. WebSocket connections through `/ws/` route to the backend with token-by-token streaming visible in the browser
  4. Static assets (JS, CSS, SVG) are served with gzip compression enabled
  5. `.dockerignore` prevents `node_modules`, `dist`, and `.git` from entering the build context
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 09-01: Frontend Dockerfile and .dockerignore
- [ ] 09-02: Nginx configuration (SPA fallback, API proxy, WebSocket proxy, gzip)

### Phase 10: Production Compose & Hardening
**Goal**: A single `docker-compose up` command brings up the entire NextFlow platform with all services healthy, properly networked, and hardened for production traffic
**Depends on**: Phase 8, Phase 9
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, CONF-01, CONF-02, CONF-03, HARD-01, HARD-02, HARD-03, HARD-04
**Success Criteria** (what must be TRUE):
  1. `docker-compose -f docker-compose.prod.yml up -d` starts all five services (backend, frontend-nginx, postgres, redis, minio) and all report healthy within 60 seconds
  2. Services start in correct dependency order: PostgreSQL, Redis, MinIO become healthy before backend starts; Nginx starts after backend is ready
  3. The existing `docker-compose.yml` (dev) continues to work unchanged — developer workflow is unaffected
  4. Skill sandbox containers launched from the backend can resolve backend DNS on the compose network (skill tool invocation succeeds)
  5. Nginx serves Vite-hashed assets with `Cache-Control: public, max-age=31536000, immutable` and includes security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection) on all responses
  6. Each service has explicit memory limits and `restart: unless-stopped` policy, and `docker-compose down` grants 30s graceful shutdown
**Plans**: TBD

Plans:
- [ ] 10-01: Production docker-compose.yml with service dependencies, networking, and environment template
- [ ] 10-02: Production hardening (caching headers, security headers, resource limits, structured logging)

### Phase 11: Vercel AI SDK Deep Integration
**Goal**: Replace the custom REST+WebSocket+Redis pub/sub streaming architecture with Vercel AI SDK Data Stream Protocol v2 (SSE) + useChat hook, reducing frontend code by 60%+ while gaining built-in abort, regenerate, retry, tool invocation UI, and reasoning display
**Depends on**: v1.0 complete (Phases 1-7)
**Requirements**: SC-01, SC-02, SC-03, SC-04, SC-05, SC-06, SC-07
**Success Criteria** (what must be TRUE):
  1. `POST /api/v1/conversations/{id}/chat` returns an SSE stream in Data Stream Protocol v2 format with `x-vercel-ai-ui-message-stream: v1` header
  2. Frontend uses `useChat` from `@ai-sdk/react` for all chat interactions — no custom WebSocket or Zustand streaming state
  3. LangGraph `astream_events` are mapped to protocol part types: `text-delta`, `reasoning-delta`, `tool-input-start/available`, `tool-output-available`, `finish`
  4. ThinkTagFilter logic preserved — `<think...</think` content maps to `reasoning-delta` events
  5. Abort (stop generation) and regenerate work correctly through the SSE transport
  6. Tool calls display in the UI using useChat's built-in `toolInvocations` on UIMessage
  7. Conversation CRUD REST APIs remain unchanged
**Plans**: 3 plans
**UI hint**: yes

Plans:
- [x] 11-01-PLAN.md — Backend SSE chat endpoint with Data Stream v2 mapper
- [ ] 11-02-PLAN.md — Frontend useChat integration + dead code removal
- [x] 11-03-PLAN.md — Backend WebSocket infrastructure cleanup

## Progress

**Execution Order:**
Phases execute in numeric order: 8 → 9 → 10 → 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Auth | v1.0 | 3/3 | Complete | 2026-03-28 |
| 2. Agent Engine Core | v1.0 | 4/4 | Complete | 2026-03-29 |
| 3. Communication Layer | v1.0 | 2/2 | Complete | 2026-03-29 |
| 4. Memory System | v1.0 | 3/3 | Complete | 2026-03-29 |
| 5. MCP Integration | v1.0 | 3/3 | Complete | 2026-03-30 |
| 6. Skill System | v1.0 | 3/3 | Complete | 2026-03-30 |
| 7. Frontend | v1.0 | 4/4 | Complete | 2026-03-31 |
| 8. Backend Containerization | v1.1 | 0/2 | Not started | - |
| 9. Frontend + Nginx Containerization | v1.1 | 0/2 | Not started | - |
| 10. Production Compose & Hardening | v1.1 | 0/2 | Not started | - |
| 11. Vercel AI SDK Deep Integration | v1.2 | 2/3 | In Progress|  |
