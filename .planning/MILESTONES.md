# Milestones

## v1.0 MVP (Shipped: 2026-03-31)

**Phases completed:** 7 phases, 22 plans, 43 tasks

**Key accomplishments:**

- FastAPI app skeleton with Docker Compose (PostgreSQL 16 + Redis 7), pydantic-settings config, structlog JSON logging, async SQLAlchemy session factory, Redis client via lifespan, and health check endpoint
- SQLAlchemy 2.0 async models for all six core tables with UUID PKs, timestamp/tenant mixins, and Alembic async migration system that creates tables in PostgreSQL
- JWT auth with PyJWT/pwdlib[argon2], refresh token rotation in Redis, 13 passing integration tests
- LangGraph StateGraph with 4-node pipeline (Analyze-Plan-Execute-Respond), AgentState TypedDict with add_messages reducer, conditional edge routing via should_execute, and RemainingSteps managed value
- Multi-provider LLM factory (OpenAI + Ollama) with streaming=True default, Settings extension for LLM configuration, and 12 passing unit tests
- Protocol-based Tool Registry with decorator registration and get_current_time built-in tool
- AsyncPostgresSaver checkpointer with psycopg3 URL handling, LLM-powered Plan/Respond nodes, Tool Registry-backed Execute node, and FastAPI lifespan initialization
- REST CRUD endpoints for conversations, agents, settings with cursor pagination, envelope responses, and 202 message posting
- WebSocket streaming layer with JWT-authenticated connections, LangGraph event mapping to five typed events, ConnectionManager for multi-connection support, and Redis pub/sub for cross-worker broadcasting
- pgvector Docker image, AsyncPostgresStore factory with OpenAI/Ollama embedder routing, graph store wiring, and 9-test memory scaffold
- ShortTermMemory with Redis Sorted Set sliding window + background LLM compression, LongTermMemory with Store fact storage + LLM dedup, unified MemoryService with extract_and_store entry point
- Analyze node with short-term + long-term memory context injection, respond node with async fire-and-forget write-back, MemoryService wired into app lifespan
- MCPClient wrapping SDK ClientSession with Streamable HTTP/SSE auto-fallback, MCPToolHandler with 30s timeout and classified error hierarchy, ToolRegistry prefix-based unregister
- MCPManager orchestrating MCP server lifecycles with parallel connect_all, namespaced tool discovery (mcp__server__tool), background health checks, and exponential backoff reconnection
- Six REST endpoints for MCP server CRUD with JWT auth, async background connection, cursor pagination, and MCPManager wired into application lifespan startup/shutdown
- SKILL.md frontmatter validator, ZIP structure validator with path safety, MinIO package storage, and extended Skill model with migration
- Docker sandbox executor with security hardening, SkillToolHandler HTTP invocation, and SkillManager lifecycle with tool registration and health checks
- Vite 7 + React 19 + shadcn/ui scaffold with auth pages, API client with 401 refresh, Zustand stores, and WebSocket hook
- Complete chat interface with message bubbles, streaming text, Markdown rendering, side panel for thinking/tool events, conversation sidebar with CRUD, and agent dropdown selector

---
