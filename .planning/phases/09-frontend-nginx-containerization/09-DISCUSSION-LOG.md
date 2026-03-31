# Phase 9: Frontend + Nginx Containerization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 09-frontend-nginx-containerization
**Areas discussed:** Nginx 角色, Nginx 基础配置, 前端 Dockerfile, WebSocket 残留清理, Compose 策略

---

## Nginx 角色

| Option | Description | Selected |
|--------|-------------|----------|
| Nginx 仍然作为统一入口 | SPA 托管 + /api/v1/ 反向代理，去掉 WebSocket 代理，SSE 只需 proxy_buffering off | ✓ |
| 后端直接托管 SPA | FastAPI StaticFiles，单容器方案，但失去 gzip/安全头/缓存优化 | |
| Caddy 替代 Nginx | 自动 HTTPS，但引入新工具，CLAUDE.md 已决定 Nginx | |

**User's choice:** Nginx 仍然作为统一入口
**Notes:** Phase 11 移除 WebSocket 后 Nginx 简化，但统一入口仍有价值（SPA 托管、API 代理、gzip）

---

## Nginx 基础配置

| Option | Description | Selected |
|--------|-------------|----------|
| 最小可用配置 | SPA try_files + API proxy + gzip + SSE proxy_buffering off，安全头和缓存留给 Phase 10 | ✓ |
| 完整生产配置 | 一次到位包含安全头、CSP、缓存策略 | |

**User's choice:** 最小可用配置
**Notes:** Phase 9 做最小可用，Phase 10 做生产加固，职责清晰

---

## 前端 Dockerfile

| Option | Description | Selected |
|--------|-------------|----------|
| Node 22 LTS | CLAUDE.md 指定 Node.js 22 LTS | ✓ |
| Node 20 LTS | 更保守，但 CLAUDE.md 已决定 22 | |

**User's choice:** Node 22 LTS
**Notes:** Nginx runtime 版本由 Claude 决定

---

## WebSocket 残留清理

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 9 顺带清理 | 删除后端 ws/ 模块 + 清理 Vite /ws proxy | ✓ |
| 延后处理 | 先不管，专注 Docker 化 | |

**User's choice:** Phase 9 顺带清理
**Notes:** Phase 11 SUMMARY 已声明移除 WebSocket 基础设施，但文件残留在磁盘

---

## Compose 策略

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 9 只做容器，Phase 10 做 compose | 职责清晰，Phase 9 产出 Dockerfile + Nginx 配置 | ✓ |
| Phase 9 就写完整 compose | 需要改现有 dev compose | |

**User's choice:** Phase 9 只做容器，Phase 10 做 compose
**Notes:** 现有 docker-compose.yml 是 dev-only（仅基础设施），不应改动

---

## Claude's Discretion

- Nginx 版本选择（Alpine 最新稳定版）
- Nginx 配置文件组织方式（单文件 vs conf.d/ 目录）
- 前端 Dockerfile 的具体优化（layer caching、build args）
- .dockerignore 具体条目

## Deferred Ideas

None
