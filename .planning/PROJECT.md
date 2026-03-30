# NextFlow — 通用Agent平台

## What This Is

一个可扩展、高性能、易集成的通用智能体（Agent）平台。系统采用前后端分离的微服务架构，前端基于 React + TypeScript，后端基于 Python + FastAPI + LangGraph，提供对话管理、技能系统、MCP 协议集成、分层记忆等核心能力，面向智能客服、自动化任务编排、知识库问答及企业 AI 应用集成等场景。

## Core Value

让 Agent 能够通过标准化的技能和工具接口，灵活接入多种 LLM 模型和外部服务，可靠地完成复杂任务——这是系统存在的唯一理由。如果 Agent 引擎不能正确编排工具调用并返回有效结果，其他一切都没有意义。

## Requirements

### Validated

- [x] JWT 认证与 RBAC 权限控制 — Validated in Phase 1: Foundation & Auth (JWT register/login/refresh/logout, RBAC deferred to v2)
- [x] 前后端分离架构，提供 REST API 与 WebSocket 流式接口 — Validated in Phase 1: FastAPI skeleton with REST API, WebSocket deferred to Phase 3
- [x] 支持多种 LLM 模型（OpenAI、本地模型等）的灵活接入与切换 — Validated in Phase 2: LLM factory with OpenAI + Ollama providers
- [x] Agent 引擎：基于 LangGraph 的有状态图工作流（分析→规划→执行→反思→响应） — Validated in Phase 2: StateGraph 4-node pipeline with checkpointer
- [x] 工具注册中心：统一管理内置工具、技能、MCP 工具 — Validated in Phase 2: Protocol-based Tool Registry with decorator registration
- [x] REST API CRUD 端点（对话、Agent、设置、消息）+ Envelope 响应格式 + Cursor 分页 — Validated in Phase 3: Communication Layer
- [x] WebSocket 实时通信，支持 thinking/tool_call/tool_result/chunk/done 事件 — Validated in Phase 3: WebSocket streaming with event mapper, ConnectionManager, Redis pub/sub

### Active

- [ ] 内置技能（Skill）系统，支持动态加载与热更新
- [x] 完整实现 MCP（Model Context Protocol）协议，无缝对接外部工具与服务 — Validated in Phase 5: MCP Client (streamable HTTP + SSE fallback), MCPManager (lifecycle/health/reconnect), MCPToolHandler bridge, Admin API with JWT auth
- [x] 具备短期/长期记忆能力，支持对话上下文与知识库检索 — Validated in Phase 4: Three-layer memory (Redis sliding window + Store semantic search + AgentState), workflow integration
- [ ] 支持水平扩展与高并发场景
- [ ] 对话模块：消息展示、输入框、流式响应渲染、思考过程展示
- [ ] 技能管理模块：技能列表、技能市场、技能配置与启用/禁用
- [ ] MCP 管理模块：MCP 服务器注册、连接状态监控、工具列表展示
- [ ] Agent 配置模块：模型选择、提示词编辑、参数调节
- [ ] 用户系统模块：登录/注册、个人设置、对话历史管理

### Out of Scope

- 移动端原生应用 — v1 仅提供 Web 端和 API 接口
- 私有化部署方案 — 初期聚焦云端部署
- 语音交互 — 超出 v1 文本对话范围
- 多租户隔离 — 初期为单租户架构
- 实时协作编辑 — 非核心场景

## Context

**技术栈（已确定）：**

- **前端**：React 18 + TypeScript + Vite + shadcn/ui（Radix UI + TailwindCSS）+ Zustand
- **后端**：Python + FastAPI + LangGraph（Agent 编排）+ LangChain（LLM 集成）
- **数据库**：PostgreSQL（业务数据）、Redis（缓存/会话）、Qdrant/Milvus（向量检索）
- **任务队列**：Celery + Redis
- **对象存储**：MinIO（文件/技能包）
- **代码规范**：ESLint + Prettier（前端）、结构化日志（后端）

**架构关键决策：**

- Agent 引擎采用 LangGraph 有状态图工作流，支持条件边与循环
- 技能系统采用插件化设计，运行在独立沙箱环境
- MCP 客户端支持多服务器连接、工具发现、统一调用
- 记忆系统分为三层：短期记忆（Redis）、长期记忆（向量库）、工作记忆（AgentState）
- 前后端通过 REST API + WebSocket 双通道通信

**适用场景：**
- 智能客服与对话机器人
- 自动化任务执行与工作流编排
- 知识库问答与辅助决策
- 企业级 AI 应用集成底座

## Constraints

- **Tech Stack**: 前端 React + TypeScript + Vite；后端 Python + FastAPI + LangGraph — 用户已在架构文档中明确指定
- **LLM Integration**: 通过 LangChain 抽象层统一接入，支持 OpenAI/Azure/Anthropic/本地模型（vLLM、Ollama）
- **Protocol**: MCP 协议作为工具集成标准
- **Deployment**: Docker 容器化，支持 Kubernetes 编排
- **Performance**: 支持流式输出降低首字延迟，异步处理耗时任务
- **Security**: JWT + RBAC，技能沙箱隔离，敏感配置加密存储

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph 作为 Agent 编排引擎 | 有状态图工作流天然支持条件边、循环、状态传递，适合复杂 Agent 流程 | — Validated: 4-node pipeline with conditional edges, checkpointer (Phase 2) |
| LangChain 作为 LLM 抽象层 | 统一接口支持多模型切换，降低模型锁定风险 | — Validated: OpenAI + Ollama factory, Plan/Respond nodes (Phase 2) |
| shadcn/ui 作为前端组件库 | Radix UI 无障碍 + TailwindCSS 灵活样式，社区活跃 | — Pending |
| Zustand 状态管理 | 轻量级，API 简洁，适合中等复杂度应用 | — Pending |
| MCP 协议集成 | 标准化工具协议，生态正在快速扩展，避免自建工具协议的维护成本 | — Validated: MCPClient + MCPManager + MCPToolHandler + Admin API (Phase 5) |
| Qdrant/Milvus 向量数据库 | 高性能向量检索，支持长期记忆的语义搜索 | — Pending |
| 三层记忆架构 | 短期（Redis）+ 长期（向量库）+ 工作记忆（AgentState），平衡性能与上下文完整性 | — Validated: ShortTermMemory + LongTermMemory + MemoryService (Phase 4) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-30 after Phase 5 completion*
