---
phase: 02-agent-engine-core
plan: 03
subsystem: agent-engine
tags: [tool-registry, protocol, decorator, langgraph, structlog]

# Dependency graph
requires:
  - phase: 01-foundation-auth
    provides: "structlog logging, service layer patterns, deps.py DI pattern"
provides:
  - "ToolRegistry class with register/invoke/list_tools"
  - "ToolHandler Protocol for type-safe handler contracts"
  - "ToolNotFoundError exception for missing tools"
  - "Decorator-based registration via @registry.register"
  - "get_current_time built-in tool"
  - "get_tool_registry() factory function"
affects: [03-conversation-ui, 05-mcp-integration, 06-skills-system]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Protocol-based handler pattern", "Decorator-based tool registration", "Dual-mode invoke (Protocol objects and bare async functions)"]

key-files:
  created:
    - "backend/app/services/tool_registry/__init__.py"
    - "backend/app/services/tool_registry/registry.py"
    - "backend/app/services/tool_registry/handlers.py"
    - "backend/app/services/tool_registry/builtins.py"
    - "backend/tests/unit/test_tool_registry.py"
  modified: []

key-decisions:
  - "Invoke method handles both Protocol objects (with .invoke()) and bare async functions (decorator pattern)"
  - "Last-write-wins for duplicate tool names (no error, silent overwrite)"

patterns-established:
  - "Protocol-based handler: ToolHandler Protocol defines async invoke(params) -> Any contract"
  - "Decorator registration: @registry.register(name, schema) on async functions"
  - "Service package layout: __init__.py exports public API, registry.py has class, handlers.py has Protocol, builtins.py has registration"

requirements-completed: [AGNT-05, AGNT-06]

# Metrics
duration: 2min
completed: 2026-03-29
---

# Phase 02 Plan 03: Tool Registry Summary

**Protocol-based Tool Registry with decorator registration and get_current_time built-in tool**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-28T23:59:34Z
- **Completed:** 2026-03-29T00:02:18Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments
- ToolRegistry with register/invoke/list_tools and dual-mode decorator support
- ToolHandler Protocol defining async invoke(params) -> Any contract for all handler types
- Decorator-based registration (@registry.register(name, schema)) for built-in tools
- get_current_time built-in tool validating the full registration -> routing -> invocation chain
- ToolNotFoundError with descriptive error message for missing tool invocations
- All 10 unit tests passing (TDD: RED -> GREEN)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for Tool Registry and built-in tools (RED)** - `90b02fa` (test)
2. **Task 2: Implement Tool Registry, handlers, and built-in tools (GREEN)** - `305f1f0` (feat)

## Files Created/Modified
- `backend/app/services/tool_registry/__init__.py` - Public API: ToolRegistry, ToolNotFoundError, get_tool_registry factory
- `backend/app/services/tool_registry/registry.py` - ToolRegistry class with register/invoke/list_tools + ToolNotFoundError
- `backend/app/services/tool_registry/handlers.py` - ToolHandler Protocol and ToolEntry data container
- `backend/app/services/tool_registry/builtins.py` - register_builtin_tools and get_current_time tool
- `backend/tests/unit/__init__.py` - Unit test package marker
- `backend/tests/unit/test_tool_registry.py` - 10 unit tests for full registry coverage

## Decisions Made
- Invoke method uses `hasattr(handler, "invoke")` to support both Protocol objects and bare async functions, enabling decorator pattern without requiring wrapper classes
- Duplicate tool registration silently overwrites (last-write-wins), matching D-14 global shared tools design

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed decorator-registered functions failing on invoke**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Decorator registration stored raw async functions in ToolEntry.handler, but invoke() called handler.invoke(params) which fails on bare functions
- **Fix:** Added dual-mode dispatch in invoke(): checks hasattr(handler, "invoke") for Protocol objects, falls back to direct await handler(params) for bare functions
- **Files modified:** backend/app/services/tool_registry/registry.py
- **Verification:** All 10 tests pass including test_decorator_registration
- **Committed in:** 305f1f0 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for decorator registration to work. No scope creep.

## Issues Encountered
None beyond the auto-fix above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Tool Registry ready for integration into Execute node (02-04)
- Registry can be initialized in main.py lifespan and injected via deps.py
- Built-in tools registration validates the full chain for MCP tools (Phase 5) and skill tools (Phase 6)

## Self-Check: PASSED

All files verified present:
- backend/app/services/tool_registry/__init__.py: FOUND
- backend/app/services/tool_registry/registry.py: FOUND
- backend/app/services/tool_registry/handlers.py: FOUND
- backend/app/services/tool_registry/builtins.py: FOUND
- backend/tests/unit/test_tool_registry.py: FOUND

Commits verified:
- 90b02fa: FOUND
- 305f1f0: FOUND

---
*Phase: 02-agent-engine-core*
*Completed: 2026-03-29*
