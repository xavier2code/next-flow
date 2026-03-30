---
phase: 05-mcp-integration
plan: 02
subsystem: mcp, tool-registry
tags: [mcp, mcp-manager, health-check, exponential-backoff, tool-discovery, tool-sync, namespaced-tools]

# Dependency graph
requires:
  - phase: 05-mcp-integration
    provides: "MCPClient, MCPToolHandler, ToolRegistry.unregister"
provides:
  - "MCPManager: server lifecycle orchestration, health monitoring, tool synchronization"
  - "Exponential backoff reconnection (1s, 2s, 4s... max 60s)"
  - "Background health check task with asyncio.create_task"
  - "Namespaced tool registration (mcp__{server}__{tool})"
affects: [05-mcp-integration, tool-registry, agent-engine]

# Tech tracking
tech-stack:
  added: []
  patterns: ["MCPManager orchestrates per-server MCPClient instances", "asyncio.gather for parallel server connections", "Exponential backoff reconnection loop", "Prefix-based tool cleanup on reconnect (mcp__{server}__)"]

key-files:
  created:
    - backend/app/services/mcp/manager.py
    - backend/tests/unit/test_mcp_manager.py
  modified:
    - backend/app/core/config.py
    - backend/app/services/mcp/__init__.py

key-decisions:
  - "MCPManager uses session_factory (async_sessionmaker) injected at construction for DB queries"
  - "Tool sync unregisters old server tools before registering new ones on every connect/reconnect"
  - "Health check uses list_tools() as lightweight liveness probe with 5s timeout"
  - "connect_all uses asyncio.gather for parallel server connections"

patterns-established:
  - "Namespaced tool registration: mcp__{server_name}__{tool_name} format prevents cross-server collisions"
  - "Manager pattern: single class owns all client instances, coordinates lifecycle"
  - "Exponential backoff: backoff = min(backoff * 2, max_backoff) with 1s start and 60s cap"

requirements-completed: [MCP-02, MCP-03]

# Metrics
duration: 9min
completed: 2026-03-29
---

# Phase 5 Plan 2: MCPManager Summary

**MCPManager orchestrating MCP server lifecycles with parallel connect_all, namespaced tool discovery (mcp__server__tool), background health checks, and exponential backoff reconnection**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-29T15:35:14Z
- **Completed:** 2026-03-29T15:44:24Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- MCPManager connects all registered MCP servers from database in parallel using asyncio.gather
- Tools are discovered via tools/list on connect and registered in ToolRegistry with mcp__{server}__{tool} namespace
- On reconnect, old server tools are unregistered before new ones are registered
- Background health check task detects disconnected servers and triggers reconnection with exponential backoff (1s, 2s, 4s... max 60s)
- All 8 unit tests passing covering lifecycle, tool sync, and reconnection scenarios

## Task Commits

_No git commits -- project is not a git repository._

1. **Task 1: MCPManager core -- connect_all, disconnect_all, sync_tools** - manager.py, config.py, __init__.py, test_mcp_manager.py (TDD)

## Files Created/Modified
- `backend/app/services/mcp/manager.py` - MCPManager class: server lifecycle, health monitoring, tool sync, exponential backoff reconnection
- `backend/app/core/config.py` - Added mcp_tool_timeout and mcp_health_check_interval settings
- `backend/app/services/mcp/__init__.py` - Added MCPManager to module exports
- `backend/tests/unit/test_mcp_manager.py` - 8 unit tests covering connect_all, disconnect_all, sync_tools, connect_server, disconnect_server

## Decisions Made
- MCPManager uses session_factory (async_sessionmaker) injected at construction for all database queries
- Tool sync always unregisters old server tools before registering new ones, handling both initial connect and reconnect uniformly
- Health check uses list_tools() as a lightweight liveness probe with a 5-second timeout
- connect_all uses asyncio.gather for parallel server connections rather than sequential awaits

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Simplified connect_server logging to avoid internal state access**
- **Found during:** Task 1 (implementation)
- **Issue:** Plan's connect_server included `len(client.list_tools.__self__._session is not None)` which accessed internal SDK state and would fail with mocked clients
- **Fix:** Replaced with simple logger.info with server name only
- **Files modified:** backend/app/services/mcp/manager.py
- **Verification:** All 8 tests pass, import resolves

**2. [Rule 1 - Bug] Fixed test mocking strategy for MCPClient construction**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Patching MCPClient.__init__ with return_value=None left instances without _session attribute, causing is_connected to raise AttributeError. Patching the class with side_effect returned coroutines instead of objects since the factory was a regular function
- **Fix:** Used patch("app.services.mcp.manager.MCPClient", side_effect=fn) where fn returns pre-built mock clients directly. Tests use @asynccontextmanager-based make_session_factory instead of AsyncMock for session factory mocking
- **Files modified:** backend/tests/unit/test_mcp_manager.py
- **Verification:** All 8 tests pass

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- MCPManager is ready for Admin API integration in Plan 03 (lifespan wiring, REST endpoints)
- Health check and reconnection logic ready for production use
- Tool namespace format (mcp__server__tool) established and testable
- All 86 unit tests passing across the full test suite (34 MCP + 52 earlier)

---
*Phase: 05-mcp-integration*
*Completed: 2026-03-29*

## Self-Check: PASSED

- [x] backend/app/services/mcp/manager.py exists and contains class MCPManager
- [x] backend/app/core/config.py contains mcp_tool_timeout and mcp_health_check_interval
- [x] backend/app/services/mcp/__init__.py exports MCPManager
- [x] backend/tests/unit/test_mcp_manager.py contains 8 tests
- [x] All 86 unit tests pass (8 new + 78 existing)
