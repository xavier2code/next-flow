# Requirements: NextFlow v1.1

**Defined:** 2026-03-31
**Core Value:** 让 Agent 能够通过标准化的技能和工具接口，灵活接入多种 LLM 模型和外部服务，可靠地完成复杂任务

## v1.1 Requirements — Docker 部署就绪

### Backend Containerization

- [x] **BACK-01**: 后端 Dockerfile 使用多阶段构建（uv 安装依赖 + 精简运行时），基于 python:3.12-slim-bookworm
- [x] **BACK-02**: 后端容器以非 root 用户运行，仅拥有 /app 目录写权限
- [x] **BACK-03**: 后端容器包含 HEALTHCHECK 指令，调用现有 /api/v1/health 端点
- [x] **BACK-04**: 后端入口脚本在启动 Uvicorn 前执行 `alembic upgrade head` 迁移
- [x] **BACK-05**: 后端 .dockerignore 排除 .venv、__pycache__、.env、.pytest_cache、.git 等
- [x] **BACK-06**: 后端容器优雅关闭——CMD 使用 exec 形式，Uvicorn 接收 SIGTERM 后完成进行中的请求

### Frontend + Nginx

- [ ] **FRNT-01**: 前端 Dockerfile 使用多阶段构建（node:22-alpine 构建 → nginx:1.27-alpine 运行时）
- [ ] **FRNT-02**: Nginx 配置 SPA 回退路由（`try_files $uri $uri/ /index.html`），客户端路由刷新不返回 404
- [ ] **FRNT-03**: Nginx 反向代理 `/api/v1/` 到后端容器（backend:8000）
- [ ] **FRNT-04**: Nginx 代理 `/ws/` WebSocket 路由到后端，配置 Upgrade/Connection 头和 86400s 超时
- [ ] **FRNT-05**: 前端 .dockerignore 排除 node_modules、dist、.git 等
- [ ] **FRNT-06**: Nginx 启用 gzip 压缩（text/css, application/javascript, application/json, image/svg+xml）

### Production Docker Compose

- [ ] **COMP-01**: 新建 docker-compose.prod.yml 包含全部服务（backend、frontend-nginx、postgres、redis、minio）
- [ ] **COMP-02**: 服务依赖使用 `condition: service_healthy`，确保 PostgreSQL/Redis/MinIO 就绪后启动后端
- [ ] **COMP-03**: 后端容器挂载 Docker socket（只读）以支持 SkillSandbox 的 `docker.from_env()` 调用
- [ ] **COMP-04**: 所有服务配置 `restart: unless-stopped` 重启策略
- [ ] **COMP-05**: Skill 沙箱容器加入 compose 网络以支持 DNS 解析（sandbox.py 网络参数修改）
- [ ] **COMP-06**: compose 中设置 `stop_grace_period: 30s` 确保优雅关闭

### Environment Configuration

- [ ] **CONF-01**: 创建 .env.production.example 模板，包含 Docker 内部主机名（postgres、redis、minio）
- [ ] **CONF-02**: 现有 docker-compose.yml 保持不变（仅基础设施），开发体验零影响
- [ ] **CONF-03**: 生产环境使用共享 bridge 网络（nextflow-net），服务间通过容器名通信

### Production Hardening

- [ ] **HARD-01**: Nginx 为 Vite 内容哈希资源设置 `Cache-Control: public, max-age=31536000, immutable` 长期缓存
- [ ] **HARD-02**: Nginx 添加安全响应头（X-Frame-Options: DENY, X-Content-Type-Options: nosniff, X-XSS-Protection）
- [ ] **HARD-03**: 各服务设置 deploy.resources.limits（后端 512M, Nginx 256M, PostgreSQL 1G, Redis 256M, MinIO 512M）
- [ ] **HARD-04**: Nginx 配置 JSON 格式结构化访问日志

## Out of Scope

| Feature | Reason |
|---------|--------|
| CI/CD 流水线 | 用户明确排除，后续里程碑 |
| 容器镜像仓库 (GHCR/Docker Hub) | 后续里程碑 |
| SSL/TLS 终止 | 由基础设施层（云 LB、Traefik、Caddy）处理 |
| Kubernetes manifests | v1.2 范围，复用相同 Docker 镜像 |
| Docker-in-Docker (DinD) | Docker 团队明确不推荐；只读 socket 挂载足够 |
| Alpine Python 运行时 | musl 缺少 asyncpg/psycopg 预编译 wheel，构建慢 5-10 倍 |
| Docker Compose Watch (生产) | 生产容器应不可变，Watch 仅用于开发 |
| Docker Secrets (Swarm) | 需要 Swarm 模式，.env 文件对单机部署足够 |
| 水平扩展/多副本 | 需要 WebSocket fan-out，超出单机 Compose 范围 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BACK-01 | Phase 8 | Complete |
| BACK-02 | Phase 8 | Complete |
| BACK-03 | Phase 8 | Complete |
| BACK-04 | Phase 8 | Complete |
| BACK-05 | Phase 8 | Complete |
| BACK-06 | Phase 8 | Complete |
| FRNT-01 | Phase 9 | Pending |
| FRNT-02 | Phase 9 | Pending |
| FRNT-03 | Phase 9 | Pending |
| FRNT-04 | Phase 9 | Pending |
| FRNT-05 | Phase 9 | Pending |
| FRNT-06 | Phase 9 | Pending |
| COMP-01 | Phase 10 | Pending |
| COMP-02 | Phase 10 | Pending |
| COMP-03 | Phase 10 | Pending |
| COMP-04 | Phase 10 | Pending |
| COMP-05 | Phase 10 | Pending |
| COMP-06 | Phase 10 | Pending |
| CONF-01 | Phase 10 | Pending |
| CONF-02 | Phase 10 | Pending |
| CONF-03 | Phase 10 | Pending |
| HARD-01 | Phase 10 | Pending |
| HARD-02 | Phase 10 | Pending |
| HARD-03 | Phase 10 | Pending |
| HARD-04 | Phase 10 | Pending |

**Coverage:**
- v1.1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after roadmap creation (traceability mapped)*
