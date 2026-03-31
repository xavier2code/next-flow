---
phase: 09-frontend-nginx-containerization
plan: 01
subsystem: infra
tags: [docker, nginx, react, vite, alpine]

# Dependency graph
requires:
  - phase: 07-frontend
    provides: React SPA source code, package.json, vite.config.ts
  - phase: 08-backend-containerization
    provides: Backend Dockerfile pattern for reference
provides:
  - frontend/Dockerfile (multi-stage build: node:22-alpine -> nginx:1.27-alpine)
  - frontend/.dockerignore (build context exclusions)
  - frontend/nginx/default.conf (placeholder SPA config, replaced in 09-02)
  - backend/app/services/event_mapper.py (relocated from ws/)
affects: [10-production-compose]

# Tech tracking
tech-stack:
  added: [nginx:1.27-alpine, node:22-alpine]
  patterns: [multi-stage Docker build, nginx worker privilege drop]

key-files:
  created:
    - frontend/Dockerfile
    - frontend/.dockerignore
    - frontend/nginx/default.conf
    - backend/app/services/event_mapper.py
  modified:
    - frontend/src/components/management/AgentDetail.tsx
    - backend/app/api/v1/messages.py
    - backend/tests/unit/test_event_mapper.py

key-decisions:
  - "Nginx master runs as root (required for port 80 binding), workers drop to nginx user via built-in user directive"
  - "event_mapper.py relocated to services/ but ws/ directory NOT deleted (still actively used by main.py)"

patterns-established:
  - "Multi-stage Docker build: Node builder -> Nginx runtime"
  - "Layer caching: COPY package.json + package-lock.json before source"

requirements-completed: [FRNT-01, FRNT-05]

# Metrics
duration: 5min
completed: 2026-03-31
---

# Phase 9 Plan 1: Frontend Dockerfile and .dockerignore Summary

**Multi-stage Docker build (node:22-alpine + nginx:1.27-alpine) serving React SPA on port 80 with worker privilege separation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T19:54:41Z
- **Completed:** 2026-03-31T19:59:41Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Production-ready frontend Dockerfile with multi-stage build (Node 22 -> Nginx 1.27)
- Build context reduced to ~764KB via .dockerignore (node_modules, dist, .git excluded)
- event_mapper.py relocated from ws/ to services/ with all imports updated
- Pre-existing TypeScript error in AgentDetail.tsx fixed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create frontend/.dockerignore** - `a90e9ec` (chore)
2. **Task 2: Create frontend/Dockerfile (multi-stage build)** - `8e0901c` (feat)
3. **Task 3: Relocate event_mapper.py out of ws/ directory** - `1ce7266` (refactor)

## Files Created/Modified
- `frontend/Dockerfile` - Multi-stage Docker build (node:22-alpine builder, nginx:1.27-alpine runtime)
- `frontend/.dockerignore` - Build context exclusions (node_modules, dist, .git, .env, etc.)
- `frontend/nginx/default.conf` - Placeholder Nginx server config with SPA try_files fallback
- `frontend/src/components/management/AgentDetail.tsx` - Fixed TS error (string|undefined vs string|null)
- `backend/app/services/event_mapper.py` - Relocated from ws/ (ThinkTagFilter + map_stream_events)
- `backend/app/api/v1/messages.py` - Updated import path for event_mapper
- `backend/tests/unit/test_event_mapper.py` - Updated import path for event_mapper

## Decisions Made
- Nginx master process runs as root (required to bind port 80 on Linux), worker processes drop to nginx user via the built-in `user nginx;` directive in nginx.conf. This is the standard nginx security model -- the `USER nginx` Docker directive was attempted but abandoned because it prevents port 80 binding and PID file creation.
- ws/ directory NOT deleted despite plan instruction (D-05). The CONTEXT.md claim that ws/ contains dead code is incorrect: main.py actively imports ws_router, start_pubsub_listener, and ConnectionManager from app.api.ws.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed TypeScript error in AgentDetail.tsx**
- **Found during:** Task 2 (Docker build failed with TS2345)
- **Issue:** `useAgent(isNew ? undefined : agentId ?? undefined)` passes `string | undefined` but hook expects `string | null`
- **Fix:** Changed to `useAgent(isNew ? null : agentId)` -- removes the redundant `?? undefined` and matches hook signature
- **Files modified:** `frontend/src/components/management/AgentDetail.tsx`
- **Committed in:** `8e0901c` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed empty nginx/default.conf causing connection reset**
- **Found during:** Task 2 (docker run served connection reset)
- **Issue:** Plan said to create empty placeholder file (`touch nginx/default.conf`) but empty nginx config causes nginx to fail silently (connection reset)
- **Fix:** Created minimal server block with `listen 80`, `root /usr/share/nginx/html`, and `try_files $uri $uri/ /index.html`
- **Files modified:** `frontend/nginx/default.conf`
- **Committed in:** `8e0901c` (Task 2 commit)

**3. [Rule 4 - Architectural] Did NOT delete backend/app/api/ws/ directory**
- **Found during:** Task 3 (discovered active imports before deletion)
- **Issue:** Plan (D-05) claimed ws/ directory was dead code. In reality, main.py actively imports `ws_router`, `start_pubsub_listener`, and `ConnectionManager` from `app.api.ws`. deps.py also imports `ConnectionManager`. Deleting would break the application.
- **Resolution:** Relocated event_mapper.py as planned but skipped the ws/ directory deletion. This requires a separate plan to properly decommission the WebSocket infrastructure.
- **Files NOT modified:** `backend/app/api/ws/` (kept intact)
- **Impact:** ws/ cleanup deferred to a future plan

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug), 1 architectural (ws/ deletion skipped)
**Impact on plan:** Auto-fixes were necessary for build correctness. ws/ deletion skip is a scope reduction that prevents breaking the application.

## Issues Encountered
- Nginx non-root execution required multiple iterations: initial `USER nginx` directive broke port 80 binding and PID file creation. Resolved by keeping standard nginx root-master/nginx-worker model.
- CONTEXT.md D-05 contained incorrect information about ws/ being dead code. This should be corrected to avoid misleading future plans.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Frontend Dockerfile ready for docker-compose integration (Phase 10)
- Placeholder nginx/default.conf needs to be replaced with full config in Plan 09-02 (API proxy, gzip, SSE support)
- ws/ directory cleanup is outstanding -- should be addressed before or during Phase 10

---
*Phase: 09-frontend-nginx-containerization*
*Completed: 2026-03-31*

## Self-Check: PASSED

- FOUND: frontend/Dockerfile
- FOUND: frontend/.dockerignore
- FOUND: frontend/nginx/default.conf
- FOUND: backend/app/services/event_mapper.py
- FOUND: 09-01-SUMMARY.md
- FOUND: a90e9ec (Task 1 commit)
- FOUND: 8e0901c (Task 2 commit)
- FOUND: 1ce7266 (Task 3 commit)
