# Phase 9: Frontend + Nginx Containerization - Research

**Researched:** 2026-04-01
**Domain:** Docker multi-stage builds, Nginx reverse proxy, SPA deployment
**Confidence:** HIGH

## Summary

Phase 9 containerizes the React SPA using a multi-stage Docker build (Node 22 Alpine for building, Nginx 1.27 Alpine for serving) and produces an Nginx configuration that handles SPA fallback routing, API reverse proxying, SSE streaming passthrough, and gzip compression. The key complexity is ensuring SSE (Server-Sent Events) streams from the backend chat endpoint pass through Nginx without buffering, since Phase 11 replaced WebSocket with SSE as the streaming mechanism. The CONTEXT.md decision D-01 correctly updates the original requirement FRNT-04 (WebSocket proxy) to SSE proxy instead -- the Nginx config must reflect this. A secondary task is cleaning up dead WebSocket code from the backend.

**Primary recommendation:** Use a two-stage Dockerfile (node:22-alpine build, nginx:1.27-alpine runtime) with a single nginx.conf replacing the default config. Place the Nginx config at `frontend/nginx/nginx.conf` and reference it from the Dockerfile. The SSE chat endpoint at `POST /api/v1/conversations/{id}/chat` needs `proxy_buffering off` + `proxy_cache off` in the `/api/v1/` location block (no separate SSE location needed since the endpoint is under the API prefix).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Nginx keeps unified entry point (CLAUDE.md decision), but simplified config -- remove WebSocket proxy requirement. Phase 11 replaced WebSocket with SSE. Nginx only needs standard HTTP reverse proxy + SSE proxy_buffering off.
- **D-02:** Nginx config scope: minimal viable -- SPA try_files fallback, /api/v1/ reverse proxy to backend :8000, gzip compression, SSE endpoint proxy_buffering off. Security headers and cache strategy deferred to Phase 10.
- **D-03:** Multi-stage Dockerfile: Stage 1 uses Node 22 LTS to build React (npm ci && npm run build), Stage 2 uses Nginx Alpine to serve dist/. Non-root user runs Nginx.
- **D-04:** .dockerignore excludes node_modules, dist, .git, .env, etc.
- **D-05:** Delete backend `backend/app/api/ws/` directory (connection_manager.py and chat.py are dead code -- not mounted to main.py). Clean up stale `/ws` entry from Vite dev proxy.
- **D-06:** Phase 9 only produces containerization artifacts (Dockerfile + Nginx config). No docker-compose. Phase 10 creates docker-compose.prod.yml.

### Claude's Discretion

- Nginx version selection (Alpine latest stable)
- Nginx config file organization (single file vs conf.d/ directory)
- Frontend Dockerfile optimizations (layer caching, build args)
- .dockerignore specific entries

### Deferred Ideas (OUT OF SCOPE)

None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FRNT-01 | Frontend Dockerfile multi-stage build (node:22-alpine build, nginx:1.27-alpine runtime) | Verified images available; nginx:1.27.5-alpine, node:22-alpine (v22.22.2). Multi-stage pattern documented below. |
| FRNT-02 | Nginx SPA fallback routing (try_files $uri $uri/ /index.html) | Standard pattern; verified against official Nginx image default config. |
| FRNT-03 | Nginx reverse proxy /api/v1/ to backend container (backend:8000) | Standard proxy_pass pattern; backend confirmed listening on :8000 (gunicorn.conf.py). |
| FRNT-04 | Nginx proxy /ws/ WebSocket route -- **SUPERSEDED by D-01**: Replace with SSE proxy_buffering off | SSE endpoint is POST /api/v1/conversations/{id}/chat under /api/v1/ prefix. Needs proxy_buffering off + proxy_cache off in same location block. Backend already sends X-Accel-Buffering: no. |
| FRNT-05 | Frontend .dockerignore excludes node_modules, dist, .git, etc. | Standard pattern; backend .dockerignore provides reference template. |
| FRNT-06 | Nginx gzip compression (text/css, application/javascript, application/json, image/svg+xml) | Verified MIME types in Nginx image; gzip module available. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nginx:1.27-alpine | 1.27.5 (verified via `docker run`) | Runtime container serving static files + reverse proxy | Official Docker image, ~40MB, includes gzip module. 1.27 is mainline (current latest). Alpine variant is minimal. |
| node:22-alpine | v22.22.2 (verified via `docker run`) | Build-stage container for Vite + React build | Node 22 LTS as specified by CLAUDE.md. Alpine variant for minimal build image. |
| Docker | 29.3.1 (verified on host) | Build tool | Required for building and testing images. |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| Nginx gzip module | built-in | Static asset compression | Enabled globally; specific MIME types per FRNT-06 |
| Nginx proxy module | built-in | Reverse proxy to backend | For /api/v1/ location block |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nginx:1.27-alpine | nginx:stable-alpine | 1.27 IS the latest mainline; stable tag would be 1.26. Use 1.27 since it is current and the official image is well-tested. |
| Single nginx.conf | conf.d/*.conf include pattern | Single file is simpler for a single-server setup. The official image already does `include /etc/nginx/conf.d/*.conf` in nginx.conf. A single replacement default.conf in conf.d/ is cleaner than replacing nginx.conf entirely. |
| Replace nginx.conf entirely | Drop custom config in conf.d/ | Replacing nginx.conf loses gzip and other http-level settings. Better to replace conf.d/default.conf and add gzip settings there. |

**Installation:**
No npm packages needed. This phase is pure Docker + Nginx config.

**Version verification:**
```
docker run --rm nginx:1.27-alpine nginx -v  # nginx version: nginx/1.27.5
docker run --rm node:22-alpine node --version  # v22.22.2
docker --version  # Docker version 29.3.1
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/
  Dockerfile           # Multi-stage build (Phase 9 creates this)
  .dockerignore        # Build context exclusions (Phase 9 creates this)
  nginx/
    default.conf       # Nginx server config (Phase 9 creates this)
  package.json         # Existing
  vite.config.ts       # Existing (cleanup /ws proxy entry)
  dist/                # Build output (excluded from build context)
  node_modules/        # Dependencies (excluded from build context)
  src/                 # Source code
  ...
```

### Pattern 1: Multi-Stage Docker Build for React SPA
**What:** Two-stage Dockerfile where Stage 1 installs dependencies and runs `npm run build`, Stage 2 copies only the `dist/` output into an Nginx image.
**When to use:** Any React/Vite SPA that needs containerization. This is the standard pattern.
**Example:**
```dockerfile
# ---- Stage 1: Build ----
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency specs first for Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Runtime ----
FROM nginx:1.27-alpine

# Remove default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built SPA from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Key details:**
- `npm ci` (not `npm install`) for deterministic builds from lockfile
- Copy `package.json` + `package-lock.json` first, then source -- layer caching means dependency changes trigger npm ci but source-only changes skip it
- Vite outputs to `dist/` by default (confirmed in vite.config.ts: no custom `build.outDir`)
- The official nginx:1.27-alpine image runs as `user nginx` by default (confirmed from nginx.conf: `user nginx;`)
- No need to create a custom non-root user -- the official image already uses `nginx` user
- `CMD ["nginx", "-g", "daemon off;"]` is the standard foreground run command

### Pattern 2: Nginx Config for SPA + API Proxy + SSE
**What:** Single server block that serves static files with SPA fallback, proxies API requests to backend, and disables buffering for SSE streams.
**When to use:** When Nginx serves as the unified entry point for a SPA frontend and API backend.
**Example:**
```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression (FRNT-06)
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/javascript
        application/json
        application/xml
        application/rss+xml
        image/svg+xml;

    # API reverse proxy (FRNT-03) + SSE passthrough (FRNT-04 superseded by D-01)
    location /api/v1/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE streaming: disable buffering so events arrive immediately
        # Backend sends X-Accel-Buffering: no, but Nginx must also be configured
        proxy_buffering off;
        proxy_cache off;

        # Keep SSE connections alive (agent workflows can run minutes)
        proxy_read_timeout 300s;
    }

    # SPA fallback routing (FRNT-02)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Key details:**
- SSE endpoint is `POST /api/v1/conversations/{id}/chat` -- it lives under `/api/v1/` so no separate location block is needed
- The backend already sends `X-Accel-Buffering: no` header (confirmed in chat.py line 309), but Nginx's own `proxy_buffering off` is still required because Nginx buffers responses by default regardless of backend hints
- `proxy_http_version 1.1` is needed for keepalive connections to the backend
- `proxy_read_timeout 300s` (5 minutes) covers long agent workflows. The original FRNT-04 specified 86400s for WebSocket; 300s is appropriate for SSE since the connection is request-scoped (each chat message is a new POST request), not a persistent connection like WebSocket
- `gzip_proxied any` ensures gzip works for proxied API responses too
- `server_name _` matches any hostname (appropriate for Docker Compose internal networking)
- The `backend:8000` hostname is the Docker Compose service name (Phase 10 will define it). For Phase 9 standalone testing, this can be overridden via envsubst or build arg, but since Phase 9 does not create docker-compose, the config should use the service name as-is and document that it requires Compose networking

### Pattern 3: .dockerignore for Frontend
**What:** Exclude files that should not enter the Docker build context (reduces context size, prevents stale artifacts from leaking in).
**When to use:** Every Docker project.
**Example:**
```
node_modules
dist
.git
.gitignore
.env
.env.*
*.local
.vscode
.idea
coverage
src/__tests__
```

**Key details:**
- `node_modules` is the most critical exclusion -- it can be 500MB+ and is rebuilt by `npm ci` in the container
- `dist` prevents stale build artifacts from entering the image
- `.env` and `.env.*` prevent secrets from entering the image
- `src/__tests__` excludes test files from the production image (they are not needed at runtime)
- Reference: `backend/.dockerignore` for the pattern already established in this project

### Anti-Patterns to Avoid
- **Running Nginx as root:** The official nginx:alpine image already runs as `user nginx`. Do not add `USER root` or remove the user directive. This satisfies D-03 (non-root user) without extra work.
- **Copying node_modules into the image:** Always run `npm ci` inside the container, never COPY node_modules. Lockfile-only copy for layer caching is the correct approach.
- **Separate SSE location block:** The SSE endpoint is under `/api/v1/` prefix. A separate location block for SSE would add complexity without benefit. Put `proxy_buffering off` in the `/api/v1/` block.
- **Replacing nginx.conf entirely:** The default nginx.conf includes `conf.d/*.conf`. Dropping a `default.conf` in `conf.d/` is cleaner than replacing the main config. It preserves the default worker_processes, error_log, and MIME type includes.
- **Enabling gzip for SSE:** Gzip compression should NOT be applied to `text/event-stream` responses. The `gzip_types` directive listed above does not include `text/event-stream`, which is correct. If Nginx's `gzip_proxied any` causes issues with SSE, add `proxy_set_header Accept-Encoding ""` to the SSE-specific behavior, but this is unlikely to be needed since `text/event-stream` is not in `gzip_types`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Static file serving | Custom Express/Python static server | Nginx | 10x faster at serving static files, built-in gzip, mature ecosystem |
| SPA routing | Custom 404 handler | Nginx `try_files` | Single line, battle-tested, handles all edge cases |
| Reverse proxy | Custom proxy implementation | Nginx `proxy_pass` | Handles headers, buffering, timeouts, connection pooling correctly |
| Docker layer caching | Manual cache management | Docker's built-in layer caching + COPY ordering | Docker caches each layer; copy lockfile before source for optimal cache hits |
| Non-root container user | Manual useradd/groupadd | Official nginx:alpine `user nginx` | Already configured in the official image |

**Key insight:** The entire Phase 9 deliverable is wiring together well-understood infrastructure components. There is nothing to hand-roll -- every problem (SPA serving, API proxying, SSE passthrough, gzip) has a standard Nginx directive for it.

## Common Pitfalls

### Pitfall 1: SSE Buffering by Nginx
**What goes wrong:** SSE events from the backend arrive in batches (seconds of delay) or not at all in the browser.
**Why it happens:** Nginx buffers proxied responses by default. Even though the backend sends `X-Accel-Buffering: no`, Nginx's own `proxy_buffering` directive takes precedence.
**How to avoid:** Add `proxy_buffering off;` and `proxy_cache off;` to the `/api/v1/` location block. This is the single most important Nginx config for this phase.
**Warning signs:** Chat streaming appears laggy or arrives all-at-once instead of token-by-token.

### Pitfall 2: SPA Refresh Returns 404
**What goes wrong:** Navigating to `/conversations/abc` directly (or refreshing) returns Nginx 404.
**Why it happens:** Nginx tries to find a file at `/conversations/abc` on disk, which does not exist. The React router handles client-side routing, but the server must serve index.html for all non-file paths.
**How to avoid:** `try_files $uri $uri/ /index.html;` in the `/` location block. The `$uri` check first serves actual static files (JS, CSS, images), then falls back to index.html for everything else.
**Warning signs:** Any direct URL navigation returns 404.

### Pitfall 3: Docker Build Context Too Large
**What goes wrong:** `docker build` takes minutes just for the "Sending build context" step.
**Why it happens:** `node_modules` (hundreds of MB) and `.git` directory are included in the build context.
**How to avoid:** A proper `.dockerignore` excluding `node_modules`, `dist`, `.git`. Verify with `docker build --progress=plain` and check the "Sending build context" line.
**Warning signs:** Build context is >50MB.

### Pitfall 4: Gzip Not Working for Proxied Content
**What goes wrong:** API responses or static assets are not compressed despite gzip being enabled.
**Why it happens:** By default, Nginx does not gzip proxied responses. The `gzip_proxied` directive must be set to `any` (or at least `no-cache`).
**How to avoid:** Include `gzip_proxied any;` in the server block.
**Warning signs:** Response headers lack `Content-Encoding: gzip` in browser dev tools.

### Pitfall 5: Vite Build Fails Due to Missing Environment Variables
**What goes wrong:** `npm run build` fails inside Docker because it references env vars like `VITE_API_URL` that are not set during build.
**Why it happens:** Vite bakes `VITE_*` env vars into the build at build time. If the frontend uses absolute API URLs (e.g., `VITE_API_URL=http://localhost:8000`), the Docker build needs these vars.
**How to avoid:** Verify that the frontend uses relative paths for API calls (confirmed: `api-client.ts` uses `fetch('/api/v1/...')` with relative paths). No `VITE_*` env vars are needed for API URLs. If other `VITE_*` vars exist, pass them as `ARG` in the Dockerfile.
**Warning signs:** Build logs show undefined variable errors.

### Pitfall 6: WebSocket Dead Code Not Cleaned Up
**What goes wrong:** Future developers find `backend/app/api/ws/` and assume WebSocket is still in use, leading to confusion.
**Why it happens:** Phase 11 replaced WebSocket with SSE but left the old code in place.
**How to avoid:** Delete `backend/app/api/ws/connection_manager.py` and `backend/app/api/ws/chat.py` as part of Phase 9 (D-05). Also remove the `/ws` proxy entry from `frontend/vite.config.ts`. Note: `backend/app/api/ws/event_mapper.py` is still imported by `chat.py` (SSE endpoint) and must NOT be deleted -- move it out of the `ws/` directory first (e.g., to `backend/app/api/v1/` or `backend/app/services/`).
**Warning signs:** Grep for imports of `event_mapper` to confirm no breakage before deleting the ws/ directory.

## Code Examples

### Frontend Dockerfile (Complete)
```dockerfile
# ---- Stage 1: Build React SPA ----
FROM node:22-alpine AS builder

WORKDIR /app

# Copy dependency specs first for Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve with Nginx ----
FROM nginx:1.27-alpine

# Remove default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built SPA from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx server config
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Nginx runs as 'nginx' user by default (set in /etc/nginx/nginx.conf)
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx default.conf (Complete)
```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression (FRNT-06)
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/javascript
        application/json
        application/xml
        application/rss+xml
        image/svg+xml;

    # API reverse proxy (FRNT-03) with SSE passthrough (D-01)
    location /api/v1/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE: disable buffering so events stream immediately
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # SPA fallback routing (FRNT-02)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### .dockerignore (Complete)
```
node_modules
dist
.git
.gitignore
.env
.env.*
*.local
coverage
src/__tests__
*.log
```

### WebSocket Cleanup: event_mapper.py Relocation
The file `backend/app/api/ws/event_mapper.py` is imported by `backend/app/api/v1/chat.py`:
```python
from app.api.ws.event_mapper import ThinkTagFilter
```
Before deleting `backend/app/api/ws/`, move `event_mapper.py` to a non-ws location (e.g., `backend/app/services/event_mapper.py`) and update the import in `chat.py`. Then delete the entire `backend/app/api/ws/` directory.

### Vite Dev Proxy Cleanup
Current `frontend/vite.config.ts` has a stale `/ws` proxy entry:
```typescript
'/ws': {
  target: 'ws://localhost:8000',
  ws: true,
},
```
Remove this entire block. The `/api/v1` proxy entry should remain for local development.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSocket for streaming | SSE (Server-Sent Events) | Phase 11 (this project) | Nginx config uses proxy_buffering off instead of Upgrade/Connection headers. Simpler configuration. |
| Single-stage Docker build | Multi-stage build | Industry standard for years | Smaller final image (~40MB vs ~500MB+ with node_modules). |
| Separate WebSocket Nginx location | SSE in API location block | Phase 11 decision | Fewer location blocks, simpler config. |
| Custom Nginx user | Official image default user | Current best practice | nginx:alpine already runs as non-root `nginx` user. |

**Deprecated/outdated:**
- FRNT-04 (WebSocket proxy): Superseded by D-01 (SSE proxy). The requirement as written in REQUIREMENTS.md specifies WebSocket Upgrade/Connection headers and 86400s timeout. These are no longer applicable. The plan should implement SSE passthrough instead.

## Open Questions

1. **event_mapper.py relocation target**
   - What we know: `event_mapper.py` is used by `chat.py` (SSE endpoint) for `ThinkTagFilter`. It must be moved before deleting `backend/app/api/ws/`.
   - What's unclear: Whether it belongs in `backend/app/services/` or `backend/app/api/v1/`.
   - Recommendation: Move to `backend/app/services/event_mapper.py` since it is a utility (filter/transformation logic), not an API endpoint. Update the import in `chat.py`.

2. **Nginx config: separate SSE location vs combined API location**
   - What we know: The SSE endpoint is `POST /api/v1/conversations/{id}/chat`, which is under `/api/v1/`.
   - What's unclear: Whether putting `proxy_buffering off` on the entire `/api/v1/` block has any negative side effects on non-SSE API calls.
   - Recommendation: Keep it combined. `proxy_buffering off` on regular API responses is harmless (responses are small and fast). A separate location block for SSE adds complexity. If performance testing shows issues later, a more specific location match (e.g., `location /api/v1/conversations/`) can be added in Phase 10.

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified beyond Docker itself, which is confirmed available)

Docker is available on the host (v29.3.1). The phase only produces Dockerfile and Nginx config files -- no external services, CLIs, or runtimes beyond Docker are needed at implementation time. The built images depend on Docker Hub for base images (nginx:1.27-alpine, node:22-alpine), which are already verified as pullable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.2 (configured in frontend/vitest.config.ts) |
| Config file | frontend/vitest.config.ts |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FRNT-01 | Docker build produces Nginx-based image | smoke | `docker build -t nextflow-frontend frontend/ && docker run --rm nextflow-frontend nginx -v` | N/A -- Docker test |
| FRNT-02 | SPA try_files fallback (no 404 on refresh) | smoke | Manual: docker run + curl to non-existent path, expect 200 with index.html | N/A -- Docker test |
| FRNT-03 | API proxy to backend:8000 | smoke | Manual: docker run with --network, curl /api/v1/health | N/A -- Docker test |
| FRNT-04 | SSE proxy_buffering off | smoke | Manual: verify no buffering via curl or browser | N/A -- Docker test |
| FRNT-05 | .dockerignore excludes correct files | unit | `docker build --progress=plain frontend/ 2>&1 \| grep "Sending build context"` | N/A -- Docker test |
| FRNT-06 | Gzip compression on static assets | smoke | Manual: curl -H "Accept-Encoding: gzip" and check Content-Encoding header | N/A -- Docker test |
| D-05 | WebSocket dead code deleted | unit | `test -d backend/app/api/ws/ && echo "FAIL" \| \| echo "PASS"` | N/A -- filesystem check |

### Sampling Rate
- **Per task commit:** `docker build -t nextflow-frontend frontend/` (verify build succeeds)
- **Per wave merge:** Full Docker build + manual smoke test (curl health endpoint, verify SPA loads)
- **Phase gate:** `docker build` succeeds, image runs, `nginx -v` outputs correct version, static files served

### Wave 0 Gaps
- This phase is primarily infrastructure (Dockerfile + Nginx config). The existing Vitest setup is for React component tests and is not relevant to Docker/Nginx validation.
- Validation is smoke-test based (Docker build, curl requests) rather than unit-test based.
- No new test files are needed. The planner should include manual verification steps in each task.

## Sources

### Primary (HIGH confidence)
- Docker image verification: `docker run --rm nginx:1.27-alpine nginx -v` confirmed nginx/1.27.5
- Docker image verification: `docker run --rm node:22-alpine node --version` confirmed v22.22.2
- Default nginx.conf inspection: `docker run --rm nginx:1.27-alpine cat /etc/nginx/nginx.conf` confirmed `user nginx;`, `include conf.d/*.conf`
- Default conf.d/default.conf inspection: confirmed default `location /` with `root /usr/share/nginx/html`
- Backend SSE endpoint: `backend/app/api/v1/chat.py` confirmed `X-Accel-Buffering: no` header, `text/event-stream` media type
- Backend gunicorn: `backend/gunicorn.conf.py` confirmed `bind = "0.0.0.0:8000"`
- Frontend api-client.ts: confirmed all API calls use relative paths (`/api/v1/...`)
- Frontend vite.config.ts: confirmed `/ws` proxy entry exists (stale, needs cleanup)
- Nginx MIME types: `docker run --rm nginx:1.27-alpine cat /etc/nginx/mime.types` confirmed all relevant types (json, javascript, css, svg)
- WebSocket dead code: `backend/app/api/ws/` directory exists with connection_manager.py, chat.py, event_mapper.py
- CONTEXT.md D-01 through D-06: User decisions constraining implementation scope

### Secondary (MEDIUM confidence)
- Nginx SSE configuration pattern: proxy_buffering off + proxy_cache off is well-documented standard practice for SSE through Nginx reverse proxy
- Multi-stage Docker build pattern: Industry standard for Node.js/React SPAs

### Tertiary (LOW confidence)
- None -- all findings verified against actual files or Docker images

## Project Constraints (from CLAUDE.md)

The following constraints from CLAUDE.md are relevant to Phase 9:

1. **Tech Stack**: Frontend React + TypeScript + Vite -- confirmed by package.json (React 19.1.1, Vite 7.1.7, TypeScript 5.8.3)
2. **Deployment**: Docker containerization -- this is the core deliverable of Phase 9
3. **Performance**: Streaming output with low first-token latency -- SSE proxy_buffering off is critical for this
4. **Anti-Recommendation**: Do NOT use Socket.IO (CLAUDE.md explicitly lists this). Phase 11 already removed WebSocket; this phase cleans up remaining WebSocket code.
5. **Anti-Recommendation**: Do NOT use Next.js. The frontend is a Vite + React SPA. Nginx serves static files, not SSR.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All images verified by pulling and inspecting on the actual host
- Architecture: HIGH - Multi-stage Docker builds and Nginx SPA config are mature, well-documented patterns
- Pitfalls: HIGH - All pitfalls identified from direct code inspection and verified Nginx behavior

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable domain; Nginx and Node LTS images rarely change)
