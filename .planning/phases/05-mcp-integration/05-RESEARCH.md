# Phase 5: MCP Integration - Research

**Researched:** 2026-03-29
**Domain:** MCP (Model Context Protocol) client/server integration, tool discovery, unified registry routing
**Confidence:** MEDIUM

## Summary

Phase 5 integrates external MCP servers into the NextFlow agent platform. The core challenge is building a resilient MCP client layer that connects to external servers via Streamable HTTP transport (with legacy SSE fallback), discovers their tools, registers those tools in the existing Tool Registry under namespaced identifiers (`mcp__{server}__{tool}`), and allows the agent to invoke them transparently through the existing execute_node pipeline.

The MCP SDK (v1.26.x, `mcp` package on PyPI) provides `streamable_http_client` and `sse_client` async context managers that yield `ClientSession` objects. The session exposes `initialize()`, `list_tools()`, and `call_tool()` methods. The implementation should wrap each session in an MCPClient class, managed by an MCPManager singleton that handles lifecycle, health checks, and reconnection. A new MCPToolHandler class implementing the existing ToolHandler Protocol bridges MCP tool calls into the Tool Registry.

The existing codebase provides strong integration points: the ToolRegistry (needs an `unregister` method for deregistration), the ToolHandler Protocol, the MCPServer SQLAlchemy model, the main.py lifespan pattern, and the established CRUD/API/deps patterns. The main risk is transport auto-fallback behavior -- STATE.md specifically flags this needs real-server testing, and the MCP SDK cannot be verified locally (development machine runs Python 3.9, SDK requires 3.10+).

**Primary recommendation:** Use the MCP SDK's `streamable_http_client` as primary transport with try/except fallback to `sse_client`. Wrap each in an MCPClient with its own ClientSession. Register tools as MCPToolHandler instances in the existing ToolRegistry. Follow the established lifespan/dependency patterns exactly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Startup/shutdown connection -- MCPManager connects all registered MCPServer records during main.py lifespan startup, disconnects on shutdown
- **D-02:** Per-server independent MCPClient instances -- MCPManager holds dict[str, MCPClient] mapping server_id to client
- **D-03:** Synchronous startup -- block app startup until all MCP connections complete (or fail with error logged)
- **D-04:** Periodic health check -- background asyncio task pings each connected server at regular intervals
- **D-05:** Exponential backoff reconnection -- retry with backoff (1s, 2s, 4s, 8s... max 60s). On reconnect, re-sync tools
- **D-06:** Transport auto-fallback -- prefer Streamable HTTP, fallback to legacy SSE if Streamable HTTP fails
- **D-07:** Connect-only discovery -- call tools/list only on initial connection and on reconnect. No periodic refresh
- **D-08:** Reconnect refresh -- on successful reconnect, re-call tools/list and update ToolRegistry entries for that server
- **D-09:** Namespace format `mcp__{server_name}__{tool_name}` -- double underscore separator
- **D-10:** Direct MCP schema passthrough -- use MCP's tools/list JSON Schema directly in ToolRegistry
- **D-11:** Errors as ToolMessage -- failed MCP tool invocations return error info as ToolMessage content
- **D-12:** Fixed timeout -- uniform 30-second timeout for all MCP tool invocations
- **D-13:** Classified error messages -- 4 types: connection failure, timeout, protocol error, tool execution error
- **D-14:** Full CRUD endpoint set -- POST/DELETE/GET(list)/GET(detail)/PATCH/GET(tools) for mcp-servers
- **D-15:** JWT-only auth -- all endpoints require JWT authentication via existing get_current_user dependency
- **D-16:** Async registration -- POST returns 201 immediately with status="connecting", client polls for status
- **D-17:** Deregistration cleanup -- DELETE disconnects client, removes mcp__{server}__* tools from ToolRegistry, deletes DB record

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

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCP-01 | MCP Client implementation supporting Streamable HTTP transport with legacy SSE fallback | MCP SDK `streamable_http_client` and `sse_client` async context managers. Transport fallback via try/except on connection. MCPClient wraps ClientSession lifecycle. |
| MCP-02 | MCP Manager for server registration, connection lifecycle, and health monitoring | MCPManager singleton in `services/mcp/`. Follows lifespan pattern from main.py. Dict[str, MCPClient] mapping. Background asyncio task for health pings. Exponential backoff reconnection. |
| MCP-03 | MCP tool discovery (tools/list) and registration into unified Tool Registry | MCPClient calls session.list_tools() after connection. MCPManager iterates results, creates MCPToolHandler per tool, registers in ToolRegistry with `mcp__{server}__{tool}` naming. |
| MCP-04 | MCP admin API endpoints for server registration and status monitoring | New `api/v1/mcp_servers.py` route file. Full CRUD following agents.py pattern. EnvelopeResponse/PaginatedResponse schemas. JWT auth via get_current_user. |
| MCP-05 | MCP tool invocation via Tool Registry routing (namespaced as mcp__server__tool) | MCPToolHandler implements ToolHandler Protocol. execute_node already routes via ToolRegistry.invoke(). Namespaced names route to correct MCPToolHandler which calls session.call_tool(). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mcp | 1.26.x | MCP SDK for client connections | Official MCP SDK. Provides streamable_http_client, sse_client, ClientSession with list_tools/call_tool. Pinned to minor for protocol stability. |
| httpx | 0.28+ | Async HTTP client (MCP SDK dependency) | Already in project dependencies. MCP SDK uses httpx internally. Also available for direct HTTP calls if needed. |
| pydantic | 2.x | API schema validation | Already via FastAPI. Use for MCP server CRUD request/response schemas. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio (stdlib) | 3.12+ | Background tasks, event loop | Health check background task, connection lifecycle management |
| structlog | 24.x | Structured logging | Already in project. MCP operations logging with correlation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| MCP SDK streamable_http_client | Raw httpx with manual JSON-RPC | MCP SDK handles protocol details (session init, capability negotiation, message framing). Manual implementation would be error-prone and fragile. |
| MCP SDK ClientSession | Direct SSE/HTTP connection | ClientSession manages MCP protocol lifecycle (initialize handshake, capability exchange, session management). Reimplementing this is a full protocol implementation. |

**Installation:**
```bash
# Add to pyproject.toml dependencies
pip install "mcp>=1.26.0,<1.27.0"
```

**Note:** MCP SDK requires Python >=3.10. The project targets 3.12+ (in Docker). Local development machine has Python 3.9 -- cannot install SDK locally. All SDK API details below are from training knowledge and STACK.md documentation, not local introspection.

**Version verification:** Could not verify against live PyPI from this machine (Python 3.9 incompatible). STACK.md confirms 1.26.x as target version. The PyPI error output confirmed versions exist up through 1.26.0 with Requires-Python >=3.10.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  services/
    mcp/                        # New service module
      __init__.py               # Export MCPManager, get_mcp_manager
      client.py                 # MCPClient class (wraps SDK ClientSession)
      manager.py                # MCPManager singleton (lifecycle, health, reconnect)
      handler.py                # MCPToolHandler (implements ToolHandler Protocol)
  api/
    v1/
      mcp_servers.py            # New CRUD route file
  schemas/
    mcp_server.py               # New Pydantic schemas (Create, Update, Response, ToolResponse)
```

### Pattern 1: MCPClient as SDK Session Wrapper
**What:** Each MCPClient instance owns exactly one MCP SDK ClientSession connected to one external server. The client handles connection establishment, transport selection, tool discovery, and tool invocation for its server.
**When to use:** One MCPClient per registered MCP server.
**Example:**
```python
# Source: MCP SDK API (training knowledge, MEDIUM confidence)
from contextlib import asynccontextmanager
from mcp.client.streamable_http import streamable_http_client
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

class MCPClient:
    """Wraps MCP SDK ClientSession for a single external MCP server."""

    def __init__(self, server_url: str, server_name: str, transport_type: str = "streamable_http"):
        self.server_url = server_url
        self.server_name = server_name
        self.transport_type = transport_type
        self._session: ClientSession | None = None
        self._session_ctx: AsyncContextManager | None = None
        self._transport_ctx: AsyncContextManager | None = None

    async def connect(self) -> None:
        """Establish connection with transport auto-fallback (D-06)."""
        try:
            if self.transport_type == "streamable_http":
                await self._connect_streamable_http()
            else:
                await self._connect_sse()
        except Exception:
            # Fallback to SSE if Streamable HTTP fails
            if self.transport_type == "streamable_http":
                await self._connect_sse()

    async def _connect_streamable_http(self) -> None:
        """Connect via Streamable HTTP transport."""
        self._transport_ctx = streamable_http_client(self.server_url)
        transport = await self._transport_ctx.__aenter__()
        self._session_ctx = ClientSession(*transport)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

    async def _connect_sse(self) -> None:
        """Connect via legacy SSE transport."""
        self._transport_ctx = sse_client(self.server_url)
        transport = await self._transport_ctx.__aenter__()
        self._session_ctx = ClientSession(*transport)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()

    async def list_tools(self) -> list[dict]:
        """Call tools/list on the connected server."""
        result = await self._session.list_tools()
        # result.tools is list of Tool objects with name, description, inputSchema
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
            for t in result.tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a specific tool on this server."""
        result = await self._session.call_tool(tool_name, arguments)
        return result

    async def disconnect(self) -> None:
        """Clean up session and transport."""
        if self._session_ctx:
            await self._session_ctx.__aexit__(None, None, None)
        if self._transport_ctx:
            await self._transport_ctx.__aexit__(None, None, None)
        self._session = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None
```

### Pattern 2: MCPToolHandler Bridging MCP to Tool Registry
**What:** Implements the existing ToolHandler Protocol. Each MCPToolHandler holds a reference to its parent MCPClient and the tool name. On invoke(), it calls client.call_tool() with classified error handling.
**When to use:** One MCPToolHandler per discovered MCP tool, registered in ToolRegistry.
**Example:**
```python
# Follows existing ToolHandler Protocol from handlers.py
import asyncio
from typing import Any

import structlog

logger = structlog.get_logger()


class MCPToolHandler:
    """ToolHandler implementation that routes to MCP client.

    Implements ToolHandler Protocol: async def invoke(self, params: dict) -> Any
    """

    def __init__(self, client: "MCPClient", tool_name: str, timeout: float = 30.0):
        self._client = client
        self._tool_name = tool_name
        self._timeout = timeout

    async def invoke(self, params: dict) -> Any:
        """Invoke MCP tool with timeout and classified errors (D-12, D-13)."""
        try:
            result = await asyncio.wait_for(
                self._client.call_tool(self._tool_name, params),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            raise MCPToolTimeoutError(self._tool_name, self._timeout)
        except ConnectionError as e:
            raise MCPToolConnectionError(self._tool_name, str(e))
        except Exception as e:
            # Classify as protocol or execution error based on exception type
            raise MCPToolExecutionError(self._tool_name, str(e))
```

### Pattern 3: MCPManager Lifespan Integration
**What:** MCPManager is initialized in main.py lifespan alongside existing resources. Follows the exact pattern used for checkpointer, store, and memory_service.
**When to use:** Application startup and shutdown.
**Example:**
```python
# In main.py lifespan -- follows existing pattern
from app.services.mcp import MCPManager

mcp_manager = MCPManager(
    tool_registry=registry,
    db_url=settings.database_url,
    timeout=30.0,
    health_check_interval=60.0,
)
app.state.mcp_manager = mcp_manager

# Connect all registered servers (D-03: synchronous startup)
await mcp_manager.connect_all()
logger.info("mcp_manager_initialized", servers=len(mcp_manager.clients))

# ... yield ...

# In shutdown section
await mcp_manager.disconnect_all()
```

### Pattern 4: Admin API Following Existing CRUD Pattern
**What:** New `mcp_servers.py` route file following the exact pattern from `agents.py`: router with prefix, JWT auth via get_current_user, envelope responses, service layer for business logic.
**When to use:** All MCP admin API endpoints.
**Example:**
```python
# Follows agents.py pattern exactly
from fastapi import APIRouter, Depends, Query, Response
from app.api.deps import get_current_user, get_db, get_tool_registry
from app.schemas.envelope import EnvelopeResponse, PaginatedResponse, PaginationMeta

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])

@router.post("", status_code=201)
async def register_server(
    data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    registry: ToolRegistry = Depends(get_tool_registry),
) -> EnvelopeResponse[MCPServerResponse]:
    # Create DB record with status="connecting" (D-16)
    server = await MCPServerService.create(db, str(current_user.id), data)
    await db.commit()
    # Trigger async connection in background
    # ... (get MCPManager from app.state, call connect_server)
    return EnvelopeResponse(data=MCPServerResponse.model_validate(server))
```

### Anti-Patterns to Avoid
- **Don't block the event loop during MCP calls:** The MCP SDK is async. Always use `await`. Never call sync methods.
- **Don't store MCPClient references in the database:** MCPClient is a runtime object. Store server config in MCPServer model, create/destroy MCPClient instances at runtime.
- **Don't create a new connection per tool invocation:** Reuse the ClientSession across calls. Connection establishment is expensive (initialization handshake, capability negotiation).
- **Don't silently swallow connection errors during startup:** Per D-03, log errors but continue. Don't raise and crash the entire application because one MCP server is unreachable.
- **Don't use a single global ClientSession for all servers:** Each server needs its own session with its own connection state, capabilities, and error isolation (D-02).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol implementation | Custom JSON-RPC client | MCP SDK ClientSession | Protocol has initialization handshake, capability negotiation, session management. SDK handles all of this. |
| Transport layer | Custom HTTP/SSE client | MCP SDK streamable_http_client / sse_client | Transport handles message framing, SSE parsing, session headers (Mcp-Session-Id), resumability (Last-Event-ID). |
| JSON Schema conversion | MCP-to-OpenAI schema adapter | Direct passthrough (D-10) | LangChain handles both JSON Schema formats at invocation time. Conversion introduces bugs and loses MCP-specific features. |
| Connection pooling | Custom connection manager | Per-server MCPClient instances | Each server is independent (D-02). No benefit to pooling connections to different servers. |
| Retry logic | Custom retry decorator | asyncio.wait_for + exponential backoff in MCPManager | Retry semantics are specific to MCP (re-initialize session, re-discover tools). Generic retry decorators don't handle session lifecycle. |

**Key insight:** The MCP SDK provides the entire client-side protocol implementation. The only custom code needed is the management layer (MCPManager orchestration) and the integration layer (MCPToolHandler bridging to ToolRegistry). Do not reimplement protocol features the SDK already handles.

## Common Pitfalls

### Pitfall 1: MCP SDK Context Manager Lifecycle
**What goes wrong:** The MCP SDK transport and session are async context managers. If you don't properly enter/exit them, connections leak or sessions are never initialized. Calling `session.list_tools()` before `session.initialize()` raises protocol errors.
**Why it happens:** The SDK pattern requires nested async context managers (transport first, then session). Developers may try to create sessions without entering the transport context, or forget to call initialize().
**How to avoid:** Use explicit `__aenter__`/`__aexit__` calls in MCPClient.connect()/disconnect() methods. Always call `session.initialize()` after entering the session context. Track context manager references for cleanup.
**Warning signs:** `SessionNotInitialized` errors. Connections that appear to work but return empty tool lists. Memory leaks from unclosed transport connections.

### Pitfall 2: Transport Auto-Fallback Race Condition
**What goes wrong:** STATE.md specifically flags this needs real-server testing. The fallback from Streamable HTTP to SSE may fail if the server's SSE endpoint is at a different URL path (e.g., `/sse` instead of `/`). The fallback logic tries SSE with the same URL and gets a 404.
**Why it happens:** MCP servers implementing legacy SSE often expose it at `/sse` while Streamable HTTP is at `/`. The auto-detection logic may not account for URL path differences.
**How to avoid:** The MCPServer model has a `transport_type` field (default "streamable_http") and a `config` JSON field. Allow admins to specify the exact transport type and optionally override the SSE URL in config. Auto-fallback should try the configured URL first, then try appending `/sse` as a fallback path. Log transport negotiation results.
**Warning signs:** Tool discovery returns empty results despite server being "connected". Error logs showing 404 on SSE fallback. Servers that work with one client but not another.

### Pitfall 3: Stale Tool References After Reconnection
**What goes wrong:** After an MCP server disconnects and reconnects, the tools it previously registered may have changed (new tools, removed tools, schema changes). The ToolRegistry still has the old MCPToolHandler instances pointing to the old session.
**Why it happens:** D-08 mandates re-calling tools/list on reconnect. But if the implementation forgets to unregister old tools before registering new ones, duplicate or stale entries remain. Or if registration happens before the new session is fully initialized.
**How to avoid:** On reconnect, always: (1) unregister all `mcp__{server_name}__*` tools from ToolRegistry, (2) re-discover tools via tools/list, (3) register fresh MCPToolHandler instances with the new client reference. Make this atomic -- don't leave the registry in a partial state.
**Warning signs:** Tool invocation errors after server reconnects. Stale tool schemas. Duplicate tool entries in list_tools output.

### Pitfall 4: Startup Latency from Sequential MCP Connections
**What goes wrong:** Connecting to multiple MCP servers sequentially during app startup adds seconds per server (initialization handshake + tool discovery). With 10 servers, startup could take 30+ seconds.
**Why it happens:** D-03 mandates synchronous startup (block until all connections complete). If connections are made sequentially with await, each server adds its full connection time.
**How to avoid:** Use `asyncio.gather()` to connect all servers in parallel during startup. Each MCPClient.connect() is independent (D-02). Log individual connection failures but don't block other servers. PITFALLS.md Pitfall 18 recommends async parallel discovery.
**Warning signs:** Application startup takes >5 seconds. Increasing startup time as more MCP servers are registered. Health check timeouts during startup.

### Pitfall 5: Health Check False Positives
**What goes wrong:** The health check background task marks servers as "disconnected" when they're actually healthy, triggering unnecessary reconnection storms. This happens if the health check timeout is too aggressive or the ping implementation doesn't match the server's expectations.
**Why it happens:** MCP doesn't have a standardized "ping" in all server implementations. Some servers may not respond to certain session methods quickly. Network latency spikes can cause false timeouts.
**How to avoid:** Use a generous health check interval (30-60 seconds). Implement health check as a lightweight operation -- try `session.list_tools()` with a short timeout, or use a simple session capability check. Add jitter to health check timing to avoid thundering herd.
**Warning signs:** Reconnection storms in logs. Server status oscillating between "connected" and "disconnected". Successful tool invocations from a server marked "disconnected".

## Code Examples

Verified patterns from existing codebase:

### ToolRegistry.unregister() (to be added)
```python
# Source: Existing registry.py pattern -- this method must be ADDED
def unregister(self, prefix: str) -> int:
    """Remove all tools whose name starts with the given prefix.

    Used by MCPManager on deregistration (D-17) and reconnect refresh (D-08).
    Returns the number of tools removed.
    """
    to_remove = [name for name in self._tools if name.startswith(prefix)]
    for name in to_remove:
        del self._tools[name]
        logger.info("tool_unregistered", name=name)
    return len(to_remove)
```

### MCPToolHandler Implementing ToolHandler Protocol
```python
# Source: handlers.py Protocol definition
class ToolHandler(Protocol):
    async def invoke(self, params: dict) -> Any: ...

# MCPToolHandler satisfies this Protocol via duck typing (no inheritance needed)
class MCPToolHandler:
    async def invoke(self, params: dict) -> Any:
        # ... calls self._client.call_tool(...)
```

### Lifespan Integration Pattern (from existing main.py)
```python
# Source: main.py -- existing pattern for resource initialization
# MCPManager follows this EXACT pattern

# Init section (after existing inits):
from app.services.mcp import MCPManager
mcp_manager = MCPManager(tool_registry=registry, timeout=30.0)
app.state.mcp_manager = mcp_manager
await mcp_manager.connect_all()
logger.info("mcp_manager_initialized")

# Cleanup section (before existing cleanup):
await mcp_manager.disconnect_all()
```

### Dependency for get_mcp_manager (from existing deps.py pattern)
```python
# Source: deps.py -- follows get_tool_registry pattern
from app.services.mcp import MCPManager

def get_mcp_manager(request: Request) -> MCPManager:
    """Retrieve the MCPManager instance from application state."""
    return request.app.state.mcp_manager
```

### Admin API Route Pattern (from existing agents.py)
```python
# Source: agents.py -- MCP routes follow this exact pattern
router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])

@router.post("", status_code=201)
async def register_server(
    data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[MCPServerResponse]:
    ...

@router.get("")
async def list_servers(...) -> PaginatedResponse[MCPServerResponse]:
    ...

@router.get("/{server_id}")
async def get_server(...) -> EnvelopeResponse[MCPServerResponse]:
    ...

@router.patch("/{server_id}")
async def update_server(...) -> EnvelopeResponse[MCPServerResponse]:
    ...

@router.delete("/{server_id}", status_code=204)
async def delete_server(...) -> Response:
    ...

@router.get("/{server_id}/tools")
async def list_server_tools(...) -> EnvelopeResponse[list[MCPToolResponse]]:
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE-only MCP transport | Streamable HTTP (preferred) with SSE legacy | MCP spec 2025 revision | New servers use Streamable HTTP. SSE is deprecated but widely deployed. Must support both. |
| Manual MCP protocol implementation | MCP SDK ClientSession | MCP SDK 1.0+ (2025) | SDK handles initialization, capability negotiation, session management. No reason to implement protocol manually. |
| Static tool registration | Dynamic tool discovery via tools/list | MCP spec from inception | Tools can change on server restart. Must re-discover on reconnect. |

**Deprecated/outdated:**
- MCP SSE transport: Marked deprecated in MCP spec. Still widely used by existing servers. Must support as fallback (D-06).

## Open Questions

1. **MCP SDK streamable_http_client exact API**
   - What we know: SDK provides `streamable_http_client(url)` async context manager that yields transport streams for ClientSession. Similar for `sse_client(url)`. ClientSession exposes `initialize()`, `list_tools()`, `call_tool()`.
   - What's unclear: Exact parameter signatures. Whether `streamable_http_client` accepts headers for auth. How session IDs are managed. The exact return type of `list_tools()` and `call_tool()`.
   - Recommendation: Pin SDK to 1.26.x and test against a real MCP server (e.g., the FastMCP reference server) during implementation. The SDK API is well-typed Python so IDE introspection in the Docker environment will reveal exact signatures.

2. **Transport fallback URL handling**
   - What we know: Streamable HTTP uses POST to the server URL. Legacy SSE uses GET to `/sse` endpoint typically.
   - What's unclear: Whether the same URL works for both transports, or if the SSE endpoint is at a different path. This is flagged in STATE.md as needing real-server testing.
   - Recommendation: Store the base URL in MCPServer.url. For Streamable HTTP, use it directly. For SSE fallback, try the URL directly first, then try `{url}/sse` if that fails. Allow override in MCPServer.config JSON field.

3. **Health check ping implementation**
   - What we know: MCP sessions need periodic health verification. The SDK may or may not have a dedicated ping method.
   - What's unclear: Whether ClientSession has a `ping()` or similar lightweight method. If not, calling `list_tools()` for health checks adds overhead.
   - Recommendation: During implementation, check if ClientSession exposes a ping method. If not, use a short-timeout call to a known method (e.g., list_tools with timeout=5s). Log the approach chosen.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | MCP SDK, project runtime | Local: 3.9.6 (NO) / Docker: YES | -- | Docker development environment |
| MCP SDK (mcp>=1.26.0) | MCP Client, transport | Not installed locally | 1.26.0 on PyPI | Install in Docker only |
| PostgreSQL | MCPServer model storage | Available (Docker) | 16 | -- |
| Redis | Health check state (optional) | Available (Docker) | 7.x | -- |
| pytest + pytest-asyncio | Test framework | Installed | 8.0+/0.24+ | -- |
| httpx | MCP SDK dependency, test client | Installed | 0.28+ | -- |

**Missing dependencies with no fallback:**
- MCP SDK must be added to pyproject.toml before implementation. It is NOT currently listed.
- Local development requires Docker environment for MCP SDK (Python 3.12+ requirement).

**Missing dependencies with fallback:**
- Local Python 3.9 cannot run MCP code. Use Docker development environment. Unit tests for MCPManager logic can mock the SDK.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `pytest tests/unit/test_mcp*.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | MCPClient connects via Streamable HTTP with SSE fallback | unit (mocked SDK) | `pytest tests/unit/test_mcp_client.py -x` | Wave 0 |
| MCP-01 | Transport auto-fallback on connection failure | unit (mocked transport) | `pytest tests/unit/test_mcp_client.py::test_fallback_to_sse -x` | Wave 0 |
| MCP-02 | MCPManager connects/disconnects all registered servers | unit (mocked DB) | `pytest tests/unit/test_mcp_manager.py -x` | Wave 0 |
| MCP-02 | Health check detects disconnected server, triggers reconnect | unit (mocked client) | `pytest tests/unit/test_mcp_manager.py::test_health_check_reconnect -x` | Wave 0 |
| MCP-02 | Exponential backoff on reconnect failure | unit | `pytest tests/unit/test_mcp_manager.py::test_backoff -x` | Wave 0 |
| MCP-03 | Tool discovery registers tools in ToolRegistry with namespace | unit | `pytest tests/unit/test_mcp_manager.py::test_tool_discovery -x` | Wave 0 |
| MCP-03 | Reconnect refreshes tools (unregister old, register new) | unit | `pytest tests/unit/test_mcp_manager.py::test_reconnect_refresh -x` | Wave 0 |
| MCP-04 | Admin API CRUD endpoints with JWT auth | integration | `pytest tests/test_mcp_servers.py -x` | Wave 0 |
| MCP-04 | Async registration returns 201 with connecting status | integration | `pytest tests/test_mcp_servers.py::test_async_register -x` | Wave 0 |
| MCP-04 | Deregistration removes tools and disconnects client | integration | `pytest tests/test_mcp_servers.py::test_deregister -x` | Wave 0 |
| MCP-05 | MCP tool invoked through ToolRegistry returns result | unit | `pytest tests/unit/test_mcp_handler.py -x` | Wave 0 |
| MCP-05 | Classified error messages on tool failure | unit | `pytest tests/unit/test_mcp_handler.py::test_classified_errors -x` | Wave 0 |
| MCP-05 | Tool timeout returns classified error | unit | `pytest tests/unit/test_mcp_handler.py::test_timeout -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_mcp*.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_mcp_client.py` -- covers MCP-01 (transport, fallback, connect/disconnect)
- [ ] `tests/unit/test_mcp_manager.py` -- covers MCP-02, MCP-03 (lifecycle, health, discovery, reconnect)
- [ ] `tests/unit/test_mcp_handler.py` -- covers MCP-05 (ToolHandler bridge, errors, timeout)
- [ ] `tests/test_mcp_servers.py` -- covers MCP-04 (Admin API integration with mocked MCPManager)
- [ ] `mcp>=1.26.0` must be added to pyproject.toml dependencies
- [ ] `ToolRegistry.unregister(prefix)` method must be added to registry.py

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/services/tool_registry/registry.py`, `handlers.py`, `builtins.py` -- verified registration/invoke/Protocol patterns
- Existing codebase: `backend/app/models/mcp_server.py` -- verified MCPServer SQLAlchemy model fields
- Existing codebase: `backend/app/main.py` -- verified lifespan initialization pattern
- Existing codebase: `backend/app/api/v1/agents.py`, `deps.py`, `router.py` -- verified CRUD/auth/envelope patterns
- `.planning/research/STACK.md` -- MCP SDK 1.26.x, streamable_http_client transport
- `.planning/research/ARCHITECTURE.md` -- MCP server connection flow, component boundaries
- `.planning/research/PITFALLS.md` -- Pitfall 3 (MCP Transport), Pitfall 18 (Discovery Performance)

### Secondary (MEDIUM confidence)
- MCP SDK API patterns (ClientSession, streamable_http_client, sse_client) -- from training knowledge, not locally verified. SDK cannot be installed on this machine (Python 3.9 vs required 3.10+).
- MCP transport specification (Streamable HTTP, SSE fallback, session management) -- from training knowledge of MCP specification.

### Tertiary (LOW confidence)
- MCP SDK exact method signatures (list_tools return type, call_tool parameter names) -- from training knowledge only. Must verify against actual SDK in Docker environment during implementation.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM -- MCP SDK confirmed on PyPI but cannot install/inspect locally. API patterns from training knowledge.
- Architecture: HIGH -- follows existing codebase patterns (lifespan, CRUD, ToolRegistry, ToolHandler Protocol). All integration points verified in code.
- Pitfalls: MEDIUM -- transport fallback flagged as needing real-server testing (STATE.md). SDK lifecycle pitfalls from training knowledge.

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (30 days -- MCP SDK is stable at 1.26.x)
