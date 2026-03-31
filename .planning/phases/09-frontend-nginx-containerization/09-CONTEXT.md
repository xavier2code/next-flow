# Phase 9: Frontend + Nginx Containerization - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

React SPA Docker 化并由 Nginx 托管。产出：前端 Dockerfile（多阶段构建）+ Nginx 基础配置（SPA 回退 + API 反向代理 + gzip + SSE 支持）。不包含 docker-compose（Phase 10）和生产加固（Phase 10）。顺带清理 WebSocket 残留代码。

</domain>

<decisions>
## Implementation Decisions

### Nginx 角色
- **D-01:** Nginx 保持统一入口（CLAUDE.md 已决定），但简化配置——移除 WebSocket 代理需求。Phase 11 已用 SSE 替代 WebSocket，Nginx 只需处理标准 HTTP 反向代理 + SSE 的 proxy_buffering off。
- **D-02:** Nginx 配置范围限定为最小可用：SPA try_files 回退、/api/v1/ 反向代理到后端 :8000、gzip 压缩、SSE 端点的 proxy_buffering off。安全头和缓存策略留给 Phase 10。

### 前端 Dockerfile
- **D-03:** 多阶段构建：Stage 1 用 Node 22 LTS 构建 React（`npm ci && npm run build`），Stage 2 用 Nginx Alpine 托管 dist/。非 root 用户运行 Nginx。
- **D-04:** .dockerignore 排除 node_modules、dist、.git、.env 等。

### WebSocket 残留清理
- **D-05:** 删除后端 `backend/app/api/ws/` 目录（connection_manager.py 和 chat.py 未挂载到 main.py，是死代码）。清理 Vite dev proxy 中过时的 `/ws` 条目。

### Compose 策略
- **D-06:** Phase 9 只产出容器化产物（Dockerfile + Nginx 配置），不写 docker-compose。Phase 10 创建 docker-compose.prod.yml 把 backend + frontend + nginx + 基础设施串起来。

### Claude's Discretion
- Nginx 版本选择（Alpine 最新稳定版）
- Nginx 配置文件组织方式（单文件 vs conf.d/ 目录）
- 前端 Dockerfile 的具体优化（layer caching、build args）
- .dockerignore 具体条目

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Definition
- `.planning/ROADMAP.md` §Phase 9 — Phase 9 目标、依赖、成功标准、需求编号（FRNT-01~06）
- `.planning/ROADMAP.md` §Phase 10 — Phase 10 的生产加固范围（确认 Phase 9 不越界）

### Tech Stack Constraints
- `CLAUDE.md` §Technology Stack — Node.js 22 LTS（前端构建）、Vite 7.x（构建工具）、React 19（前端框架）
- `CLAUDE.md` §Anti-Recommendations — 不使用 Next.js SSR、不使用 Socket.IO

### Existing Infrastructure
- `backend/Dockerfile` — 后端 Dockerfile（Phase 8 产出，了解现有 Docker 模式）
- `backend/.dockerignore` — 后端 .dockerignore（参考模式）
- `backend/gunicorn.conf.py` — Gunicorn 配置（后端监听 :8000）
- `backend/entrypoint.sh` — 后端入口脚本（了解现有 Docker 启动流程）
- `docker-compose.yml` — 开发环境 compose（仅基础设施：postgres、redis、minio）

### SSE Streaming (Phase 11)
- `backend/app/api/v1/chat.py` — SSE 聊天端点，已设置 `X-Accel-Buffering: no` 头
- `frontend/src/components/chat/ChatView.tsx` — useChat 使用相对路径 `/api/v1/conversations/.../chat`

### WebSocket Cleanup Targets
- `backend/app/api/ws/connection_manager.py` — 死代码，需删除
- `backend/app/api/ws/chat.py` — 死代码，需删除
- `frontend/vite.config.ts` — `/ws` proxy 条目需移除

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/Dockerfile` — 多阶段构建模式（uv 安装依赖 → 非 root 运行），Phase 9 前端 Dockerfile 应遵循类似模式
- `backend/.dockerignore` — 排除模式参考
- `frontend/vite.config.ts` — Vite 配置，base 路径默认 `/`，输出到 `dist/`

### Established Patterns
- 所有 API 路由统一前缀 `/api/v1/`（`backend/app/api/v1/router.py`）
- 前端所有 API 调用使用相对路径（`frontend/src/lib/api-client.ts`）
- 后端无静态文件服务（`main.py` 无 StaticFiles 挂载）——正确，Nginx 负责托管
- 后端健康检查端点 `GET /api/v1/health`（检查 Redis 连接）
- CORS 中间件配置在 `main.py`（Nginx 同源部署后可移除，但无害）

### Integration Points
- Nginx `proxy_pass` 指向 `http://backend:8000`（Docker Compose 服务名，Phase 10 定义）
- SSE 端点需要 `proxy_buffering off` + `proxy_cache off`（后端已发 `X-Accel-Buffering: no`）
- 前端 `useChat` 的 fetch override 从 `localStorage` 读取 JWT token——跨域时需注意，但 Nginx 同源部署无此问题

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. 用户明确要求简化 Nginx 配置（最小可用），安全头和缓存策略留给 Phase 10。

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-frontend-nginx-containerization*
*Context gathered: 2026-04-01*
