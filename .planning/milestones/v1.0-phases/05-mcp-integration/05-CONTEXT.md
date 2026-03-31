# Phase 5: MCP Integration - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

External MCP servers can be registered via Admin API, connected via MCP Client with Streamable HTTP transport (auto-fallback to SSE), their tools discovered via tools/list and registered in the unified Tool Registry with namespaced identifiers (mcp__server__tool), and invoked by the agent through the Tool Registry. MCPManager handles server lifecycle, health monitoring, and reconnection. Requirements MCP-01 through MCP-05.

</domain>

<decisions>
## Implementation Decisions

### Connection Lifecycle Management
- **D-01:** Startup/shutdown connection — MCPManager connects all registered MCPServer records during main.py lifespan startup, disconnects on shutdown. Consistent with existing lifespan pattern (checkpointer, Redis, store init)
- **D-02:** Per-server independent MCPClient instances — MCPManager holds a dict[str, MCPClient] mapping server_id to client. Each client manages its own connection independently. Failures are isolated
- **D-03:** Synchronous startup — block app startup until all MCP connections complete (or fail with error logged). Ensures tools are available before requests arrive
- **D-04:** Periodic health check — background asyncio task pings each connected server at regular intervals. Detects failures, marks MCPServer.status as "disconnected", triggers reconnection
- **D-05:** Exponential backoff reconnection — on health check failure, retry with exponential backoff (1s, 2s, 4s, 8s... max 60s). On successful reconnect, auto re-sync tools via tools/list
- **D-06:** Transport auto-fallback — prefer Streamable HTTP per MCPServer.transport_type config, fallback to legacy SSE if Streamable HTTP fails. Validate with real servers during implementation (STATE.md flag)

### Tool Discovery & Synchronization
- **D-07:** Connect-only discovery — call tools/list only on initial connection and on reconnect. No periodic refresh in v1
- **D-08:** Reconnect refresh — on successful reconnect, re-call tools/list and update ToolRegistry entries for that server. Replace all previously registered tools for that server
- **D-09:** Namespace format `mcp__{server_name}__{tool_name}` — double underscore separator. Locked from ROADMAP success criteria. Example: `mcp__weather__get_forecast`
- **D-10:** Direct MCP schema passthrough — use MCP's tools/list JSON Schema directly in ToolRegistry. No conversion to OpenAI function calling format. LangChain handles both formats at tool invocation time

### Error Handling & Resilience
- **D-11:** Errors as ToolMessage — failed MCP tool invocations return error info as ToolMessage content (consistent with existing execute_node graceful degradation, Phase 2 D-05). LLM explains failure in Respond node
- **D-12:** Fixed timeout — uniform timeout (e.g., 30 seconds) for all MCP tool invocations. Configurable via Settings in future. Timeout returns classified error ToolMessage
- **D-13:** Classified error messages — distinguish four error types: (1) connection failure — server unreachable, (2) timeout — server too slow, (3) protocol error — MCP SDK level error, (4) tool execution error — server returned error result. Each type has distinct ToolMessage content so LLM can explain precisely

### Admin API
- **D-14:** Full CRUD endpoint set — POST /mcp-servers (register), DELETE /mcp-servers/{id} (deregister), GET /mcp-servers (list with status), GET /mcp-servers/{id} (detail), PATCH /mcp-servers/{id} (update config, triggers reconnect), GET /mcp-servers/{id}/tools (list discovered tools)
- **D-15:** JWT-only auth — all endpoints require JWT authentication via existing get_current_user dependency. No role restriction (RBAC planned but not enforced in v1)
- **D-16:** Async registration — POST /mcp-servers returns 201 Created immediately with server record (status="connecting"). MCPManager connects in background. Client polls GET /mcp-servers/{id} for status updates
- **D-17:** Deregistration cleanup — DELETE disconnects client, removes all mcp__{server}__* tools from ToolRegistry, deletes MCPServer database record

### Claude's Discretion
- Exact MCPClient class implementation (wrapper around mcp SDK ClientSession)
- MCPManager internal data structure and locking
- Health check interval and ping implementation
- Exact exponential backoff timing constants
- Timeout value (suggest 30 seconds)
- MCPToolHandler Protocol implementation details
- Pydantic schema definitions for Admin API request/response
- ToolRegistry.unregister(server_prefix) method signature
- Logging detail level for MCP operations

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — MCP Manager component, MCP Clients, Tool Registry integration, MCP server connection flow, Pattern 5 (Unified Tool Registry with Strategy Routing)
- `.planning/research/STACK.md` — MCP SDK 1.26.x, streamable_http_client transport, JSON-RPC 2.0
- `.planning/research/PITFALLS.md` — Known pitfalls for MCP integration
- `.planning/PROJECT.md` — MCP protocol as tool integration standard, key decisions
- `.planning/REQUIREMENTS.md` — MCP-01 through MCP-05 acceptance criteria

### Phase Dependencies (MUST read)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — MCPServer model, project structure, Redis key convention, auth patterns
- `.planning/phases/02-agent-engine-core/02-CONTEXT.md` — Tool Registry design (D-11 to D-14), ToolHandler Protocol, execute_node graceful degradation (D-05)
- `.planning/phases/03-communication-layer/03-CONTEXT.md` — REST API patterns, envelope format, cursor pagination, lifespan initialization

### Existing Code (built in prior phases)
- `backend/app/services/tool_registry/registry.py` — ToolRegistry with register/invoke/list_tools. MUST add unregister method
- `backend/app/services/tool_registry/handlers.py` — ToolHandler Protocol and ToolEntry container. MCPToolHandler will implement this Protocol
- `backend/app/services/tool_registry/builtins.py` — Built-in tool registration pattern (reference for MCP tool registration)
- `backend/app/models/mcp_server.py` — MCPServer SQLAlchemy model (id, name, url, transport_type, config, status)
- `backend/app/api/deps.py` — get_tool_registry, get_current_user, get_db dependencies
- `backend/app/api/v1/router.py` — APIRouter with /api/v1 prefix, include new mcp_servers router
- `backend/app/main.py` — Lifespan initialization pattern (Redis, checkpointer, store, memory_service). MUST add MCPManager init

### STATE.md Concern
- STATE.md flags "MCP transport detection needs testing against real servers (affects Phase 5)" — research phase MUST validate transport fallback behavior

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ToolRegistry`: In-memory dict with register/invoke/list_tools. Needs unregister(server_prefix) method for deregistration. MCPToolHandler wraps MCP client calls
- `ToolHandler` Protocol: async invoke(params) -> Any. MCPToolHandler implements this with MCP client tool invocation
- `MCPServer` model: SQLAlchemy model with all needed fields (name, url, transport_type, config, status). Status transitions: disconnected → connecting → connected → disconnected
- `main.py` lifespan: Proven async resource initialization pattern. MCPManager init follows same pattern as checkpointer/store
- `deps.py`: get_tool_registry dependency available for API routes
- `api/v1/router.py`: Ready to include new mcp_servers router
- `api/v1/` route patterns: Established pattern for CRUD (auth.py, agents.py, conversations.py as reference)

### Established Patterns
- Layered structure: `api/` (routes) → `services/` (business logic) → `core/` (config)
- Service pattern: `services/{domain}/` with __init__.py exports
- Lifespan init: async resources created in lifespan, stored on app.state
- Dependency injection: FastAPI Depends + app.state access
- Envelope response: `{data: {...}, meta: {cursor, has_more}}`
- Error format: `{"error": {"code": ..., "message": ...}}`
- UUID primary keys for all entities
- `nextflow:{domain}:{key}` Redis key convention

### Integration Points
- `backend/app/services/` — New `mcp/` service module for MCPManager, MCPClient
- `backend/app/services/tool_registry/registry.py` — MUST add unregister method
- `backend/app/services/tool_registry/handlers.py` — MCPToolHandler implements ToolHandler Protocol
- `backend/app/main.py` — MUST initialize MCPManager in lifespan, store on app.state
- `backend/app/api/v1/router.py` — MUST include new mcp_servers router
- `backend/app/api/v1/` — New `mcp_servers.py` route file
- `backend/app/schemas/` — New schemas for MCP server request/response
- `backend/app/core/config.py` — MAY need MCP-specific settings (timeout, health check interval)

</code_context>

<specifics>
## Specific Ideas

- MCPManager follows same lifespan pattern as checkpointer, store, memory_service — init in lifespan, store on app.state, cleanup on shutdown
- MCPToolHandler wraps MCP ClientSession.call_tool() behind ToolHandler Protocol — execute_node routes transparently via ToolRegistry
- Transport auto-fallback: try streamable_http_client first, catch connection error, fallback to sse_client. STATE.md specifically flags this needs real-server testing
- Classified errors in ToolMessage give LLM rich context to explain: "The weather server is currently unreachable" vs "The forecast tool timed out"
- Async registration with polling follows established REST pattern — POST returns immediately, status transitions visible via GET

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 05-mcp-integration*
*Context gathered: 2026-03-29*
