# Phase 3: Communication Layer - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

External clients can interact with the agent engine via REST API endpoints (full CRUD on conversations, agents, and settings) and real-time WebSocket streaming that maps LangGraph execution events to typed client events. Requirements COMM-01 through COMM-04.

</domain>

<decisions>
## Implementation Decisions

### REST API Design
- **D-01:** Complete CRUD for conversations, agents, and settings — create, list, get, update, delete, archive
- **D-02:** Resource-nested URL style — e.g., `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages`, `GET /agents`, `PUT /agents/{id}`
- **D-03:** Cursor-based pagination for all list endpoints, using `created_at` ordering with cursor token
- **D-04:** Settings API covers both user preferences (default model, temperature, etc.) and system configuration (available models, system status) — requires new settings model/table
- **D-05:** Envelope response format for all endpoints: `{data: {...}, meta: {cursor, has_more}}` — consistent structure, frontend can predict response shape
- **D-06:** Chat message entry via REST — `POST /conversations/{id}/messages` returns `202 Accepted`, streaming response pushed through WebSocket

### WebSocket Streaming Protocol
- **D-07:** WebSocket authentication via query parameter token — `ws://host/ws/chat?token=xxx`, validated before connection accepted
- **D-08:** Server-only push model — WebSocket only streams events to client, client sends messages via REST POST
- **D-09:** Server-side event mapping — LangGraph `astream_events` v2 events mapped to five typed WebSocket events: `thinking`, `tool_call`, `tool_result`, `chunk`, `done`. Frontend only handles these five event types

### Connection Lifecycle
- **D-10:** WS native ping/pong frames for heartbeat — server sends ping at regular interval, client auto-replies pong. No application-layer heartbeat events
- **D-11:** Graceful disconnect — on client disconnect, in-progress LangGraph workflow continues execution to completion, results stored in checkpoint. User can reconnect and retrieve latest state
- **D-12:** Multi-connection support — user can have multiple active WebSocket connections simultaneously (multiple tabs/devices)
- **D-13:** Redis pub/sub for cross-worker event broadcasting — agent execution events published to Redis channel, all workers subscribe and push to their local connections for the same user

### Claude's Discretion
- Exact Pydantic schema definitions for request/response models
- Cursor token encoding/decoding implementation
- LangGraph astream_events v2 event type to WebSocket event mapping logic
- WebSocket endpoint URL path (e.g., `/ws/chat` vs `/ws/stream`)
- Ping interval and timeout configuration values
- Settings model schema and storage details
- Redis pub/sub channel naming convention
- Connection manager internal data structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows, WebSocket streaming patterns
- `.planning/research/STACK.md` — FastAPI 0.135.x WebSocket support, Redis pub/sub
- `.planning/research/PITFALLS.md` — Pitfall 12 (FastAPI sync blocking in WebSocket handlers)
- `.planning/PROJECT.md` — Constraints, key decisions, tech stack (REST + WebSocket dual-channel)
- `.planning/REQUIREMENTS.md` — COMM-01 through COMM-04 acceptance criteria

### Phase Dependencies (MUST read)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — Project structure, Redis setup, auth patterns, error format
- `.planning/phases/02-agent-engine-core/02-CONTEXT.md` — Graph build, AgentState, LLM streaming, Tool Registry

### Existing Code (built in prior phases)
- `backend/app/api/v1/router.py` — APIRouter with `/api/v1` prefix, existing auth/health routes
- `backend/app/api/deps.py` — `get_current_user`, `get_db`, `get_redis`, `get_tool_registry` dependencies
- `backend/app/main.py` — FastAPI app with lifespan, CORS, exception handlers
- `backend/app/services/agent_engine/graph.py` — `build_graph()` returning `CompiledStateGraph`
- `backend/app/services/agent_engine/state.py` — `AgentState` TypedDict
- `backend/app/services/agent_engine/llm.py` — LLM factory with streaming=True
- `backend/app/models/conversation.py` — Conversation model (id, user_id, title, is_archived)
- `backend/app/models/agent.py` — Agent model (id, user_id, name, system_prompt, model_config)
- `backend/app/schemas/` — Existing auth and user schemas (pattern reference)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/v1/router.py`: Ready to include new conversation, agent, settings routers
- `deps.py`: `get_current_user`, `get_db`, `get_redis`, `get_tool_registry` — all Phase 3 endpoints will use these
- `graph.py`: `build_graph()` returns `CompiledStateGraph` — call `astream_events()` for WebSocket streaming
- `Conversation` model: Already has `is_archived` field for archive endpoint
- `Agent` model: `model_config` JSON field ready for agent configuration updates
- Redis client: Already initialized in app lifespan, available for pub/sub

### Established Patterns
- Layered structure: `api/` (routes) → `services/` (business logic) → `core/` (config, security)
- Pydantic schemas in `schemas/` for request/response validation
- UUID primary keys, `nextflow:{domain}:{key}` Redis key convention
- Error format: `{"error": {"code": ..., "message": ...}}`
- Dependency injection via FastAPI `Depends`

### Integration Points
- `api/v1/router.py` — Add conversation, agent, settings routers
- `api/deps.py` — May need new dependencies (e.g., `get_connection_manager` for WebSocket)
- `main.py` — WebSocket route mounting, connection manager initialization in lifespan
- `models/` — May need new `settings` or `user_preferences` model
- `schemas/` — New schemas for conversation, agent, settings request/response
- `services/` — New `conversation_service.py`, `agent_service.py`, `settings_service.py`

</code_context>

<specifics>
## Specific Ideas

- Chat entry via REST POST returns 202, streaming via WebSocket — decouples request from response channel
- Server-side event mapping isolates frontend from LangGraph internals — frontend only handles 5 event types
- Redis pub/sub enables horizontal scaling — multiple uvicorn workers can all push events to connected clients
- Graceful disconnect preserves in-progress work — checkpoint allows reconnection and state recovery

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 03-communication-layer*
*Context gathered: 2026-03-29*
