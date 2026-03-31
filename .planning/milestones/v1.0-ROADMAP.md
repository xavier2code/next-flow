# Roadmap: NextFlow — Universal Agent Platform

## Overview

NextFlow is built from the inside out: infrastructure and auth first, then the agent engine (the critical-path core), then the communication layer that exposes it, then the memory/MCP/skill systems that extend it, and finally the frontend that ties everything together. Each phase delivers a coherent, independently verifiable capability that the next phase depends on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Auth** - Project skeleton, database schema, Redis, and JWT authentication
- [ ] **Phase 2: Agent Engine Core** - LangGraph workflow, LLM integration, tool registry, and streaming architecture
- [ ] **Phase 3: Communication Layer** - REST API and WebSocket streaming with event mapping
- [ ] **Phase 4: Memory System** - Short-term Redis memory, long-term vector memory, and context injection
- [ ] **Phase 5: MCP Integration** - MCP client, server management, tool discovery, and admin API
- [ ] **Phase 6: Skill System** - Skill packages, MinIO storage, Docker sandbox, and lifecycle management
- [ ] **Phase 7: Frontend** - Full React UI for all platform capabilities

## Phase Details

### Phase 1: Foundation & Auth
**Goal**: The platform has a running backend skeleton with persistent storage, caching, and user authentication
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. User can sign up with email and password and receive a confirmation response
  2. User can log in and receive a JWT access token that grants access to protected endpoints
  3. User session persists across browser refreshes via automatic token refresh
  4. PostgreSQL schema exists for users, conversations, agents, skills, mcp_servers, and tools
  5. Redis is operational and usable for session storage and caching
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — FastAPI skeleton, Docker Compose, config, Redis, health check (AUTH-04, AUTH-06)
- [x] 01-02-PLAN.md — SQLAlchemy models and Alembic async migrations (AUTH-05)
- [x] 01-03-PLAN.md — JWT auth with registration, login, refresh, logout (AUTH-01, AUTH-02, AUTH-03)

### Phase 2: Agent Engine Core
**Goal**: Agents can execute multi-step workflows with tool calls, persist conversation state, and stream responses
**Depends on**: Phase 1
**Requirements**: AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05, AGNT-06
**Success Criteria** (what must be TRUE):
  1. Agent executes a LangGraph StateGraph workflow through Analyze, Plan, Execute, and Respond nodes
  2. Agent state (messages, plan, scratchpad) is correctly maintained across workflow steps using the add_messages reducer
  3. Conversation state persists to PostgreSQL via PostgresSaver checkpointer and can be resumed after interruption
  4. Agent can invoke at least one LLM (OpenAI or Ollama) and return a valid response
  5. Tool Registry accepts tool registrations and routes invocations to the correct handler
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md — AgentState TypedDict, StateGraph 4-node pipeline, conditional edges, RemainingSteps (AGNT-01, AGNT-02, AGNT-06)
- [x] 02-02-PLAN.md — LLM factory with OpenAI + Ollama providers, Settings extension (AGNT-04)
- [x] 02-03-PLAN.md — Tool Registry with Protocol handlers, decorator registration, built-in tools (AGNT-05, AGNT-06)
- [x] 02-04-PLAN.md — PostgresSaver checkpointer, node wiring to LLM + Tool Registry, lifespan init (AGNT-03)

### Phase 3: Communication Layer
**Goal**: External clients can interact with the agent engine via REST endpoints and real-time WebSocket streaming
**Depends on**: Phase 2
**Requirements**: COMM-01, COMM-02, COMM-03, COMM-04
**Success Criteria** (what must be TRUE):
  1. REST API supports full CRUD on conversations, agents, and settings with proper auth guards
  2. WebSocket endpoint accepts connections and streams LangGraph execution events to connected clients
  3. Streamed events are mapped to typed WebSocket events (thinking, tool_call, tool_result, chunk, done)
  4. WebSocket connections are cleaned up on disconnect with heartbeat-based liveness detection
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — REST API CRUD for conversations, agents, settings, messages with cursor pagination and envelope format (COMM-01)
- [x] 03-02-PLAN.md — WebSocket streaming with event mapper, ConnectionManager, Redis pub/sub, and connection lifecycle (COMM-02, COMM-03, COMM-04)

### Phase 4: Memory System
**Goal**: Agents retain conversation context across turns and can recall relevant information from long-term semantic memory
**Depends on**: Phase 3
**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04
**Success Criteria** (what must be TRUE):
  1. Last N messages per conversation are cached in Redis and available for context retrieval
  2. Analyze node injects short-term memory context into the agent workflow before planning
  3. LangGraph Store enables cross-thread semantic search for long-term memory retrieval
  4. PostgreSQL with pgvector extension supports vector similarity search for embedding storage
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — PostgreSQL pgvector upgrade, Store async factory, graph store wiring, Settings embedding config, test scaffold (MEM-04)
- [x] 04-02-PLAN.md — Memory service module: ShortTermMemory (Redis sliding window), LongTermMemory (Store interaction), get_embedder factory, unified MemoryService (MEM-01)
- [x] 04-03-PLAN.md — Analyze node memory injection, Respond node async write-back, MemoryService lifespan wiring (MEM-02, MEM-03)

### Phase 5: MCP Integration
**Goal**: External MCP servers can be registered, discovered, and their tools invoked through the unified Tool Registry
**Depends on**: Phase 3
**Requirements**: MCP-01, MCP-02, MCP-03, MCP-04, MCP-05
**Success Criteria** (what must be TRUE):
  1. MCP Client connects to external servers via Streamable HTTP transport with legacy SSE fallback
  2. MCP Manager tracks server registration, connection health, and lifecycle (connect, disconnect, reconnect)
  3. Tools from registered MCP servers are discovered via tools/list and registered in the Tool Registry with namespaced identifiers (mcp__server__tool)
  4. Admin API allows registering new MCP servers and monitoring their connection status
  5. Agent can invoke an MCP-discovered tool through the Tool Registry and receive a valid result
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — MCPClient with transport auto-fallback, MCPToolHandler with classified errors, ToolRegistry.unregister (MCP-01, MCP-05)
- [x] 05-02-PLAN.md — MCPManager with server lifecycle, health monitoring, exponential backoff reconnect, tool discovery and sync (MCP-02, MCP-03)
- [x] 05-03-PLAN.md — Admin API CRUD endpoints, MCPServerService, Pydantic schemas, main.py lifespan wiring (MCP-04)

### Phase 6: Skill System
**Goal**: Users can upload, manage, and execute skills in isolated sandboxes with tools registered in the unified Tool Registry
**Depends on**: Phase 3
**Requirements**: SKIL-01, SKIL-02, SKIL-03, SKIL-04, SKIL-05
**Success Criteria** (what must be TRUE):
  1. Skill packages follow a defined manifest format (name, description, permissions, tools) and can be uploaded to MinIO
  2. Skills execute in Docker-based sandboxes with resource limits and timeout enforcement
  3. Skill lifecycle operations (upload, validate, enable, disable, hot-update) work end-to-end
  4. Skill-exposed tools are registered in the Tool Registry and invocable by the agent
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Infrastructure setup: MinIO, dependencies, Skill model migration, SKILL.md/ZIP validation, MinIO storage (SKIL-01, SKIL-02)
- [x] 06-02-PLAN.md — Docker sandbox executor, SkillToolHandler, SkillManager lifecycle with tool registration and health checks (SKIL-03, SKIL-05)
- [x] 06-03-PLAN.md — SkillService CRUD, REST API endpoints, main.py lifespan wiring, load_skill built-in tool, Agent context injection (SKIL-04, SKIL-05)

### Phase 7: Frontend
**Goal**: Users have a complete web interface to manage agents, conversations, skills, and MCP servers with real-time streaming
**Depends on**: Phase 4, Phase 5, Phase 6
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08, UI-09, UI-10
**Success Criteria** (what must be TRUE):
  1. User can register, log in, and stay authenticated across page refreshes
  2. User can create conversations, send messages, and see streaming agent responses in real-time
  3. Agent responses render with full Markdown formatting and code syntax highlighting
  4. Thinking process and tool call/result events display as collapsible sections and inline cards during streaming
  5. User can configure agents (model selection, system prompt, temperature) and manage conversation history
  6. User can manage skills (list, enable/disable, upload) and MCP servers (register, view status, list tools)
**Plans**: 4 plans

Plans:
- [x] 07-01-PLAN.md — Project scaffold, shadcn/ui, auth pages, API client, Zustand stores, WebSocket hook, app shell (UI-01, UI-02)
- [x] 07-02-PLAN.md — Chat view with streaming messages, Markdown rendering, side panel for thinking/tool events, conversation sidebar (UI-03, UI-04, UI-05, UI-06, UI-08)
- [x] 07-03-PLAN.md — Management pages (Agent/Skills/MCP tabs with list+detail), settings page with theme toggle (UI-07, UI-09, UI-10)
- [ ] 07-04-PLAN.md — Final build verification and user acceptance testing (UI-01 through UI-10)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7
Note: Phases 5 and 6 both depend on Phase 3 and can proceed in parallel if desired, but Phase 7 requires 4, 5, and 6 to be complete.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Auth | 3/3 | Complete | 2026-03-28 |
| 2. Agent Engine Core | 4/4 | Complete | 2026-03-29 |
| 3. Communication Layer | 2/2 | Complete | 2026-03-29 |
| 4. Memory System | 3/3 | Complete | 2026-03-29 |
| 5. MCP Integration | 3/3 | Complete | 2026-03-30 |
| 6. Skill System | 3/3 | Complete | 2026-03-30 |
| 7. Frontend | 2/4 | In Progress|  |
