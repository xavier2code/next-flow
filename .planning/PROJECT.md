# NextFlow — 通用Agent平台

## What This Is

一个可扩展、高性能、易集成的通用智能体（Agent）平台。系统采用前后端分离的微服务架构，前端基于 React + TypeScript，后端基于 Python + FastAPI + LangGraph，提供对话管理、技能系统、MCP 协议集成、分层记忆等核心能力，面向智能客服、自动化任务编排、知识库问答及企业 AI 应用集成等场景。

**v1.0 MVP 已交付（2026-03-31）**：完整的后端引擎（认证、Agent 工作流、REST/WebSocket API、记忆系统、MCP 集成、技能系统）和前端 UI（登录注册、流式对话、管理面板、设置页面）。

## Core Value

让 Agent 能够通过标准化的技能和工具接口，灵活接入多种 LLM 模型和外部服务，可靠地完成复杂任务——这是系统存在的唯一理由。如果 Agent 引擎不能正确编排工具调用并返回有效结果，其他一切都没有意义。

## Current Milestone: v1.1 Docker 部署就绪

**Goal:** 让 `docker-compose up` 一键拉起整套 NextFlow 服务（前端 + 后端 + 基础设施），可直接用于生产部署

**Target features:**
- 后端 FastAPI 服务 Dockerfile（多阶段构建、非 root 用户、健康检查）
- 前端 React 构建产物由 Nginx 托管（多阶段构建：Node 构建 → Nginx 托管）
- Nginx 反向代理（统一入口、API 代理、前端静态文件、WebSocket 路由）
- 生产级 docker-compose.yml（服务依赖、健康检查、重启策略、资源限制）
- 多环境配置模板（.env 文件示例 + 生产配置指南）
- 开发体验保持不变（docker-compose.dev.yml 仅基础设施，本地开发照旧）

## Current State

**Shipped: v1.0 MVP (2026-03-31)**

- 7 phases, 22 plans, 43 tasks completed in 3 days
- ~288K LOC (Python backend + TypeScript frontend)
- 296 files, 123 commits

**What works:**
- JWT authentication with refresh token rotation
- LangGraph 4-node agent pipeline (Analyze→Plan→Execute→Respond) with PostgreSQL checkpointer
- Multi-provider LLM factory (OpenAI + Ollama)
- REST API with cursor pagination + WebSocket streaming (5 event types)
- Three-layer memory (Redis sliding window + LangGraph Store semantic search + AgentState)
- MCP protocol integration with Streamable HTTP/SSE auto-fallback
- Docker-based skill sandbox with MinIO storage
- Full React 19 frontend with shadcn/ui (auth, chat streaming, management, settings)

**Phase 8 complete (2026-03-31):** Backend Dockerfile — multi-stage build (521MB), python:3.12-slim-bookworm, Gunicorn + UvicornWorker, non-root user, HEALTHCHECK, Alembic auto-migration entrypoint, SkillSandbox Docker Compose network support.

**Known gaps:**
- SKIL-04 (hot-update): Skill lifecycle CRUD exists but hot-update in production requires Docker Watch integration
- UI UAT pending: Frontend build verified (zero TS errors, 938KB bundle) but manual end-to-end testing requires running backend + frontend together
- Docker socket permissions: UID 999 (nextflow) cannot access Docker socket — deferred to Phase 10
- No RBAC: Auth is JWT-only, role-based access control deferred to v2
- No RAG pipeline: Knowledge base ingestion not yet implemented

## Requirements

### Validated

- ✓ JWT 认证与密码哈希（PyJWT + argon2） — v1.0 (Phase 1)
- ✓ FastAPI 项目骨架 + Docker Compose + PostgreSQL + Redis — v1.0 (Phase 1)
- ✓ SQLAlchemy 2.0 异步模型 + Alembic 迁移 — v1.0 (Phase 1)
- ✓ LangGraph StateGraph 4-node 工作流 + AgentState + PostgresSaver — v1.0 (Phase 2)
- ✓ 多模型 LLM 工厂（OpenAI + Ollama）+ 流式输出 — v1.0 (Phase 2)
- ✓ Protocol-based Tool Registry + 装饰器注册 — v1.0 (Phase 2)
- ✓ REST API CRUD + cursor 分页 + envelope 响应 — v1.0 (Phase 3)
- ✓ WebSocket 流式通信 + 5 种事件类型 + Redis pub/sub — v1.0 (Phase 3)
- ✓ 短期记忆（Redis Sorted Set 滑动窗口 + LLM 压缩） — v1.0 (Phase 4)
- ✓ 长期记忆（LangGraph Store 语义搜索 + 去重） — v1.0 (Phase 4)
- ✓ 记忆注入 Analyze 节点 + Respond 节点异步回写 — v1.0 (Phase 4)
- ✓ MCP Client + Streamable HTTP/SSE 自动回退 — v1.0 (Phase 5)
- ✓ MCP Manager 服务生命周期 + 健康监控 + 指数退避重连 — v1.0 (Phase 5)
- ✓ MCP 工具发现（tools/list）+ namespaced 注册（mcp__server__tool） — v1.0 (Phase 5)
- ✓ MCP Admin API（6 个 CRUD 端点 + JWT 认证） — v1.0 (Phase 5)
- ✓ Skill 包格式验证（SKILL.md + ZIP）+ MinIO 存储 — v1.0 (Phase 6)
- ✓ Docker 沙箱执行器 + 资源限制 + 超时 — v1.0 (Phase 6)
- ✓ Skill 工具注册到统一 Tool Registry — v1.0 (Phase 6)
- ✓ React 19 前端 + shadcn/ui + Zustand stores — v1.0 (Phase 7)
- ✓ 流式对话界面 + Markdown 渲染 + thinking/tool 事件侧边栏 — v1.0 (Phase 7)
- ✓ 管理面板（Agent/Skills/MCP tabs）+ 设置页面 — v1.0 (Phase 7)
- ✓ 登录/注册页面 + 认证持久化 + 主题切换 — v1.0 (Phase 7)

### Active

- [ ] Skill 热更新（Docker Watch 集成，无需重启容器）
- [ ] RBAC 权限控制（admin/developer/viewer 角色）
- [ ] 多租户数据隔离
- [ ] RAG 知识库（文档上传、自动分块、embedding 管道）
- [ ] 并行工具执行（LangGraph Send API）
- [ ] Evaluator-optimizer 循环（Reflect 节点）
- [ ] 多 LLM 路由与 fallback 链
- [ ] Human-in-the-loop 中断机制
- [ ] Skill 市场（打包、版本管理、审核）
- [ ] 水平扩展与高并发支持

### Out of Scope

| Feature | Reason |
|---------|--------|
| Visual workflow builder (drag-and-drop) | 工程投入巨大；面向开发者用户，代码优先 + 模板库是正确方向 |
| Voice interaction | STT/TTS 管道复杂度超出 v1 文本对话范围 |
| Mobile native app | 双倍前端工程量；响应式 PWA 对 v1 足够 |
| Real-time collaborative editing | CRDT/OT 复杂度与价值不成比例 |
| Built-in LLM fine-tuning | 不同工程领域；支持本地模型端点即可 |
| Low-code/no-code agent builder | 限制高级用户；模板库 + 代码定制更灵活 |
| GraphQL | WebSocket 流式场景下 REST 更简单高效 |
| Socket.IO | 私有协议层无必要，FastAPI 原生 WebSocket 足够 |
| MongoDB | 文档存储不适合关系型数据模型（用户→对话→消息） |
| Next.js | SSR 不适用于客户端 SPA 消费 REST + WebSocket 的架构 |

## Context

**Tech Stack（已验证）:**

- **前端**：React 19 + TypeScript + Vite 7 + shadcn/ui (base-ui + TailwindCSS v4) + Zustand 5
- **后端**：Python 3.12 + FastAPI 0.135 + LangGraph 1.1 + LangChain (core 1.2)
- **数据库**：PostgreSQL 16 (pgvector) + Redis 7 + Qdrant（未部署，长期记忆用 LangGraph Store）
- **任务队列**：Celery 5.6（已安装未使用，v2 启用）
- **对象存储**：MinIO（技能包 + 文档）
- **认证**：PyJWT + pwdlib[argon2]
- **MCP**：mcp SDK 1.26.x
- **代码规范**：ESLint + Prettier（前端）、structlog JSON（后端）

**架构关键决策：**

- Agent 引擎采用 LangGraph 有状态图工作流，支持条件边与循环 ✓
- 技能系统采用插件化设计，运行在 Docker 沙箱隔离环境 ✓
- MCP 客户端支持多服务器连接、工具发现、统一调用 ✓
- 记忆系统分为三层：短期（Redis）、长期（LangGraph Store）、工作记忆（AgentState） ✓
- 前后端通过 REST API + WebSocket 双通道通信 ✓

**适用场景：**
- 智能客服与对话机器人
- 自动化任务执行与工作流编排
- 知识库问答与辅助决策
- 企业级 AI 应用集成底座

**Known Technical Debt:**
- base-ui 组件 API 与 shadcn/ui 默认不完全一致（onCheckedChange、onValueChange 等）
- LLM factory 使用 if/elif 链而非注册表模式，扩展新 provider 需改代码
- WebSocket 使用 uvicorn 原生 ping/pong 而非应用层心跳
- 部分 SUMMARY.md 的 one_liner 字段缺失
- Celery 已安装但未启用（异步任务处理待 v2）

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph 作为 Agent 编排引擎 | 有状态图工作流天然支持条件边、循环、状态传递 | ✓ Validated: 4-node pipeline with conditional edges, checkpointer (Phase 2) |
| LangChain 作为 LLM 抽象层 | 统一接口支持多模型切换，降低锁定风险 | ✓ Validated: OpenAI + Ollama factory (Phase 2) |
| shadcn/ui 作为前端组件库 | base-ui 无障碍 + TailwindCSS 灵活样式 | ✓ Validated: 20+ components, dark/light theme (Phase 7) |
| Zustand 状态管理 | 轻量级，API 简洁 | ✓ Validated: auth-store, ui-store, chat-store slice pattern (Phase 7) |
| MCP 协议集成 | 标准化工具协议，生态扩展快 | ✓ Validated: Full MCP stack (Phase 5) |
| PyJWT + pwdlib[argon2] 替代 python-jose + passlib | python-jose 不再维护 | ✓ Validated: 13 passing auth tests (Phase 1) |
| 三层记忆架构 | 平衡性能与上下文完整性 | ✓ Validated: Redis + Store + AgentState (Phase 4) |
| Redis Sorted Set 滑动窗口 | O(log N) 范围查询，天然按时间排序 | ✓ Validated: ShortTermMemory (Phase 4) |
| Docker 沙箱隔离技能执行 | 安全边界清晰，资源限制可控 | ✓ Validated: SkillSandbox with security hardening (Phase 6) |
| MinIO S3-compatible 存储 | 避免云供应商锁定，迁移到 S3 零成本 | ✓ Validated: SkillStorage (Phase 6) |
| LangGraph Store 替代 Qdrant 直接集成 | 减少外部依赖，内置语义搜索 | ✓ Validated: LongTermMemory (Phase 4) |
| Cursor-based 分页 | 比 offset 分页更适合实时数据流 | ✓ Validated: REST API envelope (Phase 3) |
| Redis pub/sub 跨 worker 消息 | WebSocket 水平扩展基础 | ✓ Validated: ConnectionManager (Phase 3) |

## Constraints

- **Tech Stack**: 前端 React + TypeScript + Vite；后端 Python + FastAPI + LangGraph — 用户已在架构文档中明确指定
- **LLM Integration**: 通过 LangChain 抽象层统一接入，支持 OpenAI/Azure/Anthropic/本地模型（vLLM、Ollama）
- **Protocol**: MCP 协议作为工具集成标准
- **Deployment**: Docker 容器化，支持 Kubernetes 编排
- **Performance**: 支持流式输出降低首字延迟，异步处理耗时任务
- **Security**: JWT + RBAC（RBAC deferred to v2），技能沙箱隔离，敏感配置加密存储

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-03-31 after Phase 8 (Backend Containerization) completed*
