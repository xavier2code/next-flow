<!-- GSD:project-start source:PROJECT.md -->
## Project

**NextFlow — 通用Agent平台**

一个可扩展、高性能、易集成的通用智能体（Agent）平台。系统采用前后端分离的微服务架构，前端基于 React + TypeScript，后端基于 Python + FastAPI + LangGraph，提供对话管理、技能系统、MCP 协议集成、分层记忆等核心能力，面向智能客服、自动化任务编排、知识库问答及企业 AI 应用集成等场景。

**Core Value:** 让 Agent 能够通过标准化的技能和工具接口，灵活接入多种 LLM 模型和外部服务，可靠地完成复杂任务——这是系统存在的唯一理由。如果 Agent 引擎不能正确编排工具调用并返回有效结果，其他一切都没有意义。

### Constraints

- **Tech Stack**: 前端 React + TypeScript + Vite；后端 Python + FastAPI + LangGraph — 用户已在架构文档中明确指定
- **LLM Integration**: 通过 LangChain 抽象层统一接入，支持 OpenAI/Azure/Anthropic/本地模型（vLLM、Ollama）
- **Protocol**: MCP 协议作为工具集成标准
- **Deployment**: Docker 容器化，支持 Kubernetes 编排
- **Performance**: 支持流式输出降低首字延迟，异步处理耗时任务
- **Security**: JWT + RBAC，技能沙箱隔离，敏感配置加密存储
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Runtime & Language
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Backend runtime | LangGraph requires >=3.10. Python 3.12 is the sweet spot: mature, fast (free-threading experiments in 3.13 are unstable), and all libraries support it. Pin to 3.12 for stability, allow 3.13 opt-in. | HIGH |
| Node.js | 22 LTS | Frontend runtime | Vite 7/8, React 19, and shadcn/ui tooling all target Node 22 LTS. Long-term support through April 2027. | HIGH |
| TypeScript | ~5.7 | Frontend type safety | Strict typing catches integration errors between Zustand stores, WebSocket events, and API responses. The ~5.7 range matches current Vite/React tooling expectations. | HIGH |
### Core Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| FastAPI | 0.135.x | API gateway, WebSocket server | Async-native, Pydantic v2 validation, native WebSocket support, automatic OpenAPI docs. v0.135 adds Starlette 1.0 support and native SSE. The fastest-growing Python web framework. | HIGH |
| LangGraph | 1.1.x | Agent orchestration engine | The core differentiator. Stateful graph workflow with checkpointing, conditional edges, loops, and streaming. v1.1.x is production-stable (reached 1.0 in Oct 2025). No viable alternative for this use case. | HIGH |
| LangChain | latest (core 1.2.x) | LLM abstraction layer | Required for multi-provider model switching (OpenAI, Anthropic, Ollama). Provides `BaseChatModel` interface, tool call normalization, and streaming primitives. LangGraph depends on it. | HIGH |
| React | 19.x | Frontend UI framework | React 19 is current (v19.2.4 on npm). The PROJECT.md specifies React 18, but React 19 is backward-compatible and provides Server Components, Actions, and improved suspense. No reason to start a new project on 18. | HIGH |
| Vite | 7.x | Frontend build tool | Vite 7.3.1 is the established stable. Vite 8.0.1 was released days ago (March 2026) and may have ecosystem plugin incompatibilities. Use Vite 7 for production stability, upgrade to 8 after ecosystem catches up. | HIGH |
### Database
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PostgreSQL | 16 | Primary relational database | Business data (users, conversations, agents, skills, MCP servers, tools). LangGraph `PostgresSaver` for checkpoint persistence. Mature, reliable, excellent Python drivers via SQLAlchemy + asyncpg. v16 has performance improvements over v15. | HIGH |
| Redis | 7.x | Cache, session store, Celery broker | Short-term memory (conversation context windows). Celery task broker (separate db index from cache). Session storage. Pub/sub for cross-worker WebSocket messaging at scale. | HIGH |
| Qdrant | 1.x | Vector database (long-term memory) | Chosen over Milvus for three reasons: (1) qdrant-client has first-class async Python support with `async_qdrant_client`, critical for FastAPI's async model; (2) simpler operational model -- single binary or Docker container vs Milvus's multi-component architecture; (3) LangChain and LangGraph have native Qdrant integrations. Milvus is better at massive scale (100M+ vectors) but Qdrant handles millions comfortably. | MEDIUM |
### Infrastructure
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Celery | 5.6.x | Distributed task queue | Async processing for long-running tasks: skill packaging, batch embedding, report generation. v5.6 adds Python 3.14 support and critical memory leak fixes. Redis as broker (already in stack). | HIGH |
| MinIO | latest | Object storage | Skill packages (ZIP files), uploaded documents for RAG. S3-compatible API means migration to AWS S3 is trivial if needed. Self-hosted avoids cloud vendor lock-in. | HIGH |
| Docker | 27.x | Containerization | Skill sandbox execution (isolated containers with resource limits). Service orchestration via Docker Compose for development. Production-ready for Kubernetes deployment. | HIGH |
| SQLAlchemy | 2.x | ORM, database migrations | Async support via `sqlalchemy[asyncio]` + asyncpg. Alembic for schema migrations. Declarative models with Pydantic-compatible type annotations. | HIGH |
| Alembic | 1.14+ | Database migration tool | Standard for SQLAlchemy projects. Auto-generates migration scripts from model changes. | HIGH |
### Supporting Libraries -- Backend
| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| langchain-openai | latest | OpenAI/Azure LLM integration | Primary LLM provider adapter. Use for GPT-4, GPT-4o, Azure OpenAI endpoints. | HIGH |
| langchain-anthropic | latest | Anthropic LLM integration | Secondary LLM provider. Use for Claude models. Validates multi-provider abstraction. | HIGH |
| langchain-community | latest | Ollama, vLLM integration | Local model support. Use for Ollama (development) and vLLM (production local inference). | HIGH |
| langgraph-checkpoint-postgres | latest | LangGraph PostgreSQL checkpointer | State persistence for agent workflows. `PostgresSaver.from_conn_string()`. Required for conversation resumption and time-travel debugging. | HIGH |
| langgraph-store | latest | LangGraph Store (long-term memory) | Cross-thread semantic memory persistence. `store.search()` and `store.put()` for user-scoped knowledge. Replaces custom vector DB integration for long-term memory. | MEDIUM |
| mcp | 1.26.x | MCP SDK (Model Context Protocol) | MCP client implementation. FastMCP for server-side, streamable HTTP transport. Tool discovery, invocation, and session management. `streamable_http_client` for connecting to external MCP servers. | HIGH |
| python-jose | 3.3+ | JWT token encoding/decoding | Authentication. Access tokens + refresh tokens. RS256 algorithm. | HIGH |
| passlib | 1.7+ | Password hashing | User registration/login. bcrypt backend. | HIGH |
| pydantic | 2.x (via FastAPI) | Data validation, settings | API request/response models, configuration management. FastAPI already depends on Pydantic v2. Use `BaseModel` for all schemas. | HIGH |
| uvicorn | 0.34+ | ASGI server | FastAPI runtime. Use `--workers` for multi-process. Standard production setup. | HIGH |
| httpx | 0.28+ | Async HTTP client | MCP server connections (when not using SDK transport), external API calls, skill sandbox communication. Supports HTTP/2. | HIGH |
| structlog | 24.x | Structured logging | JSON-formatted logs for production. Correlation IDs, request tracing. Better than stdlib logging for microservices. | MEDIUM |
| asyncpg | 0.30+ | Async PostgreSQL driver | Direct async DB access for SQLAlchemy. Faster than psycopg2 for concurrent queries. | HIGH |
| redis | 5.x | Async Redis client | `redis.asyncio` for cache, session store, and Celery broker connection. | HIGH |
| qdrant-client | 1.x | Qdrant vector DB client | `AsyncQdrantClient` for vector operations. Used by LangChain Qdrant integration and directly for custom embedding pipelines. | MEDIUM |
| minio | 7.x | MinIO Python client | Skill package upload/download, document storage. Presigned URL generation. | HIGH |
| docker | 7.x | Docker SDK for Python | Skill sandbox management. Container lifecycle (create, start, stop, remove). Resource limit enforcement. | HIGH |
### Supporting Libraries -- Frontend
| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| shadcn/ui | latest | Component library (Radix + TailwindCSS) | All UI components. Not an npm package -- installed via CLI (`npx shadcn@latest init`). Provides accessible, customizable components built on Radix UI primitives. Copy-paste model means full control. | HIGH |
| Zustand | 5.x | State management | Client-side state. Use slice pattern from day one (separate stores for chat, skills, MCP, agent config). `useShallow` for multi-field selectors. Middleware: `devtools` (outermost), `persist` (for user preferences). | HIGH |
| TailwindCSS | 4.x | Utility-first CSS | Required by shadcn/ui. v4 uses CSS-native configuration (`@theme` in CSS) instead of `tailwind.config.js`. | HIGH |
| react-markdown | 9.x | Markdown rendering | LLM response display. Supports code block syntax highlighting via rehype plugins. | HIGH |
| remark-gfm | 4.x | GitHub-flavored markdown | Tables, strikethrough, task lists in LLM responses. Plugin for react-markdown. | HIGH |
| rehype-highlight | 7.x | Code syntax highlighting | Code blocks in LLM responses. Uses highlight.js under the hood. | MEDIUM |
| @tanstack/react-query | 5.x | Server state management | API data fetching, caching, and synchronization. Complements Zustand (Zustand for client state, React Query for server state). | HIGH |
## Alternatives Considered
### Database -- Vector Store
| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **Qdrant** | Milvus | Milvus requires etcd, MinIO, and multiple service components even in standalone mode. Qdrant is a single binary. Milvus's Python client lacks first-class async support. Milvus wins at 100M+ vector scale, but NextFlow will not reach that for v1/v2. |
| **Qdrant** | ChromaDB | Chroma is designed for prototyping, not production. No production-grade deployment tooling. Poor performance above 1M vectors. LangChain integration is less mature. |
| **Qdrant** | pgvector | pgvector (PostgreSQL extension) avoids adding a new database to the stack. However, its HNSW implementation is slower than Qdrant's, and it does not support filtering + vector search as efficiently. Adds write amplification to the primary database. Revisit if operational simplicity is prioritized over search quality. |
### State Management
| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **Zustand** | Redux Toolkit | Redux adds boilerplate (actions, reducers, slices, middleware configuration) for marginal benefit at this scale. Zustand's API is 5x more concise. No need for Redux's devtools middleware superiority -- Zustand's devtools integration is sufficient. |
| **Zustand** | Jotai | Jotai is atom-based (bottom-up), which works for simple apps but becomes hard to reason about when multiple atoms interact. Zustand's store-based (top-down) model is better for complex state with inter-slice dependencies (chat state depends on MCP connection state). |
| **Zustand** | MobX | MobX's observable pattern is magical and hard to debug. Zustand's explicit `set()` calls are easier to trace. MobX's proxy-based reactivity can cause surprising performance issues with WebSocket message streams. |
### Agent Orchestration
| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **LangGraph** | Custom DAG implementation | LangGraph provides checkpointing, streaming, human-in-the-loop, and time-travel debugging out of the box. Building these from scratch would take months. The graph abstraction maps perfectly to the analyze-plan-execute-reflect-respond workflow. |
| **LangGraph** | CrewAI / AutoGen | These are higher-level multi-agent frameworks. NextFlow needs low-level graph control for conditional branching, loops, and parallel tool execution. LangGraph provides this. CrewAI and AutoGen abstract away too much control. |
| **LangGraph** | Dify (visual builder) | Dify is a product, not a library. Cannot be embedded in a custom platform. The visual workflow builder is explicitly excluded from NextFlow's scope. |
### Build Tool
| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **Vite 7.x** | Vite 8.x (latest) | Vite 8.0.1 was released days ago (March 2026). Ecosystem plugins (shadcn/ui, TailwindCSS v4, etc.) may not be fully compatible. Wait 2-3 months for ecosystem to stabilize, then upgrade. |
| **Vite** | Webpack | Webpack is slower (no native ESM), more complex to configure, and the React ecosystem has moved to Vite. No benefit for a greenfield project. |
| **Vite** | Turbopack | Turbopack is still in beta and tightly coupled to Next.js. Not applicable for a Vite + React SPA. |
## Anti-Recommendations (What NOT to Use)
| Technology | Why Avoid | What to Use Instead |
|------------|-----------|-------------------|
| **Milvus** | Operational complexity (etcd + MinIO + multiple services), weak async Python support. Overkill for expected scale. | Qdrant -- single binary, native async, simpler operations. |
| **Redux / Redux Toolkit** | Excessive boilerplate for this scope. Zustand achieves the same with 5x less code. | Zustand with slice pattern. |
| **Flask** | Synchronous framework. No native WebSocket support. No automatic API documentation. Would require workarounds for every async operation. | FastAPI -- async-native, WebSocket support, Pydantic validation, auto-generated docs. |
| **Django** | Monolithic framework. ORM is synchronous. WebSocket support requires Channels (additional complexity). Not suited for async-heavy agent platform. | FastAPI -- purpose-built for async APIs. |
| **Socket.IO** | Proprietary protocol layer over WebSocket. Adds complexity without benefit since NextFlow controls both client and server. FastAPI's native WebSocket is sufficient. | FastAPI WebSocket with custom event protocol. |
| **GraphQL** | Adds complexity (schema definition, resolver functions, query parsing) for a use case dominated by WebSocket streaming. REST + WebSocket is simpler and more performant for this architecture. | REST API (CRUD) + WebSocket (streaming). |
| **MongoDB** | Document store does not fit relational data model (users -> conversations -> messages, agents -> tools, skills -> permissions). Would sacrifice referential integrity and query flexibility. | PostgreSQL -- relational model fits the data perfectly. |
| **ChromaDB** | Prototype-grade vector database. Not suitable for production. Performance degrades above 1M vectors. No production deployment tooling. | Qdrant -- production-grade, single binary, good performance. |
| **Prisma** (backend) | Prisma is a Node.js ORM. NextFlow's backend is Python. | SQLAlchemy 2.x with asyncpg. |
| **Next.js** | Adds SSR complexity that NextFlow does not need. The frontend is a client-side SPA consuming REST + WebSocket APIs. Next.js SSR/RSC provides no benefit for this architecture. | Vite + React SPA. |
| **SSE (Server-Sent Events) for primary channel** | SSE is unidirectional (server -> client). The chat interface requires bidirectional communication (send messages, receive streaming). SSE would require a separate channel for client -> server. | WebSocket for bidirectional real-time communication. |
## Version Resolution Notes
### React 18 vs React 19
### Vite 7 vs Vite 8
### Qdrant vs Milvus Decision
## Installation
### Backend (Python)
# Core framework
# Agent engine
# MCP protocol
# Authentication
# Database clients
# Task queue
# Utilities
# Development
### Frontend (Node.js)
# Create project
# UI framework
# State management
# Markdown rendering
# WebSocket
# Development
### Docker Services (docker-compose.yml)
## Pinning Strategy
| Category | Strategy | Rationale |
|----------|----------|-----------|
| LangGraph | `1.1.*` (minor+patch) | Rapid release cadence (weekly). Pin minor to avoid breaking changes. |
| LangChain ecosystem | `latest` (no pin) | LangChain follows semver loosely. Pinning causes version conflict cascades. Use `requirements.txt` lockfile from CI. |
| FastAPI | `0.135.*` | Pre-1.0 semver -- patch versions may have minor features but stay compatible within 0.135.x. |
| MCP SDK | `1.26.*` | Protocol version matters. New SDK versions may change transport behavior. Pin minor. |
| Celery | `5.6.*` | Stable release series. Patch versions are bugfix-only. |
| React | `19.x` | Major version pin. React follows semver strictly. |
| Vite | `7.x` | Major version pin. Ecosystem compatibility matters. |
| All others | Latest compatible | Use `pip freeze` / `npm shrinkwrap` for reproducible builds. |
## Sources
- LangGraph PyPI: https://pypi.org/project/langgraph/ -- v1.1.3, released 2026-03-18, Python >=3.10 (HIGH confidence -- official PyPI)
- MCP SDK PyPI: https://pypi.org/project/mcp/ -- v1.26.0, released 2026-01-24, Python >=3.10 (HIGH confidence -- official PyPI)
- Celery GitHub Releases: https://github.com/celery/celery/releases -- v5.6.2, released 2026-01-04 (HIGH confidence -- official GitHub)
- FastAPI GitHub Releases: https://github.com/fastapi/fastapi/releases -- v0.135.1, released 2026-03-01 (HIGH confidence -- official GitHub)
- Qdrant async support: https://pypi.org/project/qdrant-client/ -- `AsyncQdrantClient` available (MEDIUM confidence -- PyPI docs, verified by project research)
- Vite version verification: https://www.npmjs.com/package/vite -- v8.0.1 (days old), v7.3.1 (stable) (HIGH confidence -- official npm)
- React version: https://www.npmjs.com/package/react -- v19.2.4 current (HIGH confidence -- official npm)
- Zustand docs: https://zustand.docs.pmnd.rs/ -- v5.x with slice pattern (HIGH confidence -- official docs)
- LangGraph Persistence docs: https://docs.langchain.com/oss/python/langgraph/persistence (HIGH confidence -- official LangChain docs)
- MCP Transports spec: https://modelcontextprotocol.io/docs/concepts/transports (HIGH confidence -- official MCP spec)
- PROJECT.md: `.planning/PROJECT.md` -- project constraints and architecture decisions (HIGH confidence -- project definition)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
