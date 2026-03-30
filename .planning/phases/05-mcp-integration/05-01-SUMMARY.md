---
phase: 05-mcp-integration
plan: 01
subsystem: mcp, tool-registry
tags: [mcp, mcp-sdk, streamable-http, sse, transport-fallback, tool-handler, classified-errors]

# Dependency graph
requires:
  - phase: 02-agent-engine
    provides: "ToolRegistry, ToolHandler Protocol, ToolEntry"
provides:
  - "MCPClient class wrapping MCP SDK ClientSession with transport auto-fallback"
  - "MCPToolHandler implementing ToolHandler Protocol with classified errors"
  - "MCPToolError hierarchy: MCPToolTimeoutError, MCPToolConnectionError, MCPToolProtocolError, MCPToolExecutionError"
  - "ToolRegistry.unregister(prefix) method for bulk tool removal"
affects: [05-mcp-integration, tool-registry, agent-engine]

# Tech tracking
tech-stack:
  added: ["mcp>=1.26.0,<1.27.0"]
  patterns: ["Transport auto-fallback (Streamable HTTP -> SSE)", "Classified error hierarchy for tool invocation", "Per-server MCPClient instances"]

key-files:
  created:
    - backend/app/services/mcp/__init__.py
    - backend/app/services/mcp/client.py
    - backend/app/services/mcp/handler.py
    - backend/app/services/mcp/errors.py
    - backend/tests/unit/test_mcp_client.py
    - backend/tests/unit/test_mcp_handler.py
  modified:
    - backend/pyproject.toml
    - backend/app/services/tool_registry/registry.py
    - backend/tests/unit/test_tool_registry.py

key-decisions:
  - "MCP SDK installed at v1.26.0 matching project pinning strategy"
  - "MCPClient manages session/transport context managers directly (no external lifecycle library)"
  - "MCPToolHandler duck-types ToolHandler Protocol without explicit Protocol inheritance"

patterns-established:
  - "Transport auto-fallback: streamable_http with SSE fallback on connection failure"
  - "Classified errors: MCPToolTimeoutError, MCPToolConnectionError, MCPToolProtocolError, MCPToolExecutionError"
  - "Prefix-based tool unregistration for MCP server disconnect/reconnect"

requirements-completed: [MCP-01, MCP-05]

# Metrics
duration: 6min
completed: 2026-03-29
---

# Phase 5 Plan 1: MCP Client & Handler Summary

**MCPClient wrapping SDK ClientSession with Streamable HTTP/SSE auto-fallback, MCPToolHandler with 30s timeout and classified error hierarchy, ToolRegistry prefix-based unregister**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-29T15:25:08Z
- **Completed:** 2026-03-29T15:31:08Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- MCPClient connects via Streamable HTTP transport with automatic SSE fallback on failure
- MCPToolHandler implements ToolHandler Protocol with asyncio.wait_for timeout and four classified error types
- ToolRegistry.unregister(prefix) enables bulk removal of MCP tools by server prefix
- MCP SDK v1.26.0 dependency declared and installed in pyproject.toml
- All 26 tests passing (13 registry + 7 client + 6 handler)

## Task Commits

_No git commits -- project is not a git repository._

1. **Task 1: Add MCP SDK dependency and ToolRegistry.unregister method** - registry, pyproject.toml, tests
2. **Task 2: MCPClient with transport auto-fallback** - client.py, __init__.py, tests (TDD)
3. **Task 3: MCPToolHandler with classified errors** - errors.py, handler.py, tests (TDD)

## Files Created/Modified
- `backend/pyproject.toml` - Added `mcp>=1.26.0,<1.27.0` dependency
- `backend/app/services/tool_registry/registry.py` - Added `unregister(prefix)` method for bulk tool removal
- `backend/app/services/mcp/__init__.py` - Module init exporting MCPClient and MCPToolHandler
- `backend/app/services/mcp/client.py` - MCPClient class wrapping MCP SDK ClientSession with transport auto-fallback
- `backend/app/services/mcp/handler.py` - MCPToolHandler implementing ToolHandler Protocol with classified errors
- `backend/app/services/mcp/errors.py` - Error hierarchy: MCPToolError, MCPToolTimeoutError, MCPToolConnectionError, MCPToolProtocolError, MCPToolExecutionError
- `backend/tests/unit/test_tool_registry.py` - Added TestToolRegistryUnregister with 3 tests
- `backend/tests/unit/test_mcp_client.py` - 7 tests covering connect, fallback, SSE-only, list_tools, call_tool, disconnect, is_connected
- `backend/tests/unit/test_mcp_handler.py` - 6 tests covering success, timeout, connection error, execution error, error attributes

## Decisions Made
- MCP SDK v1.26.0 installed matching the project pinning strategy (mcp>=1.26.0,<1.27.0)
- MCPClient manages session and transport context managers directly rather than using an external lifecycle library
- MCPToolHandler uses duck typing for ToolHandler Protocol compliance (no explicit Protocol inheritance)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- MCPClient and MCPToolHandler are ready for MCPManager orchestration in Plan 02
- ToolRegistry.unregister is ready for MCP server disconnect/reconnect flows
- Error hierarchy ready for integration into agent workflow error handling
- MCP SDK installed and verified working with Python 3.12

---
*Phase: 05-mcp-integration*
*Completed: 2026-03-29*

## Self-Check: PASSED

- All 7 created/modified files verified present
- `def unregister` found exactly once in registry.py
- `mcp>=1.26.0,<1.27.0` confirmed in pyproject.toml
- All 26 tests passing (13 registry + 7 client + 6 handler)
- All MCP module imports resolve correctly
