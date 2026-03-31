---
phase: 02-agent-engine-core
plan: 04
subsystem: agent-engine
tags: [langgraph, checkpointer, postgres, llm, tool-registry, fastapi]

# Dependency graph
requires:
  - phase: 02-agent-engine-core
    provides: "AgentState TypedDict + StateGraph + 4 node stubs (Plan 01), LLM factory (Plan 02), Tool Registry with built-in tools (Plan 03)"
provides:
  - "AsyncPostgresSaver checkpointer for conversation state persistence"
  - "LLM-powered Plan and Respond nodes"
  - "Tool Registry-powered Execute node"
  - "Lifespan initialization for Tool Registry and checkpointer"
  - "get_tool_registry FastAPI dependency"
affects: [03-conversation-api, 04-memory-system, 05-mcp-integration]

# Tech tracking
tech-stack:
  added: [langgraph-checkpoint-postgres>=2.0.0, psycopg[binary]>=3.1.0]
  patterns: [checkpointer-creation-with-url-stripping, lifespan-initialization-of-services, node-wiring-to-llm-factory]

key-files:
  created:
    - backend/app/services/agent_engine/checkpointer.py
    - backend/tests/unit/test_checkpointer.py
  modified:
    - backend/app/services/agent_engine/graph.py
    - backend/app/services/agent_engine/nodes/plan.py
    - backend/app/services/agent_engine/nodes/execute.py
    - backend/app/services/agent_engine/nodes/respond.py
    - backend/app/main.py
    - backend/app/api/deps.py
    - backend/pyproject.toml

key-decisions:
  - "Used InMemorySaver instead of MagicMock for graph compilation tests (LangGraph validates checkpointer type)"
  - "Added setuptools packages.find config to pyproject.toml to fix flat-layout build error"
  - "Added psycopg[binary] to dependencies for local development without libpq system library"
  - "Execute node accepts tool_registry as keyword-only parameter for future injection via graph config"

patterns-established:
  - "Checkpointer URL stripping: replace '+asyncpg' suffix for psycopg3 compatibility"
  - "Lifespan initialization pattern: create service -> store on app.state -> log"
  - "Node graceful degradation: try/except returning AIMessage with error content on failure"

requirements-completed: [AGNT-03]

# Metrics
duration: 7min
completed: 2026-03-29
---

# Phase 02 Plan 04: Wire Components Summary

**AsyncPostgresSaver checkpointer with psycopg3 URL handling, LLM-powered Plan/Respond nodes, Tool Registry-backed Execute node, and FastAPI lifespan initialization**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-29T00:14:22Z
- **Completed:** 2026-03-29T00:21:41Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Created AsyncPostgresSaver checkpointer with automatic URL normalization (+asyncpg stripping)
- Wired Plan and Respond nodes to LLM factory for real LLM invocation
- Connected Execute node to Tool Registry for tool execution routing
- Updated FastAPI lifespan to initialize Tool Registry and checkpointer at startup
- Added get_tool_registry FastAPI dependency in deps.py
- Full unit test coverage for checkpointer and graph compilation (6 tests, 37 total pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create checkpointer module, wire nodes to LLM and Tool Registry** - `5f7a245` (feat)
2. **Task 2: Create checkpointer unit tests and verify full agent engine integration** - `def8f82` (test)

## Files Created/Modified
- `backend/app/services/agent_engine/checkpointer.py` - AsyncPostgresSaver factory with URL stripping
- `backend/tests/unit/test_checkpointer.py` - 6 unit tests for checkpointer and graph compilation
- `backend/app/services/agent_engine/graph.py` - build_graph with optional checkpointer parameter
- `backend/app/services/agent_engine/nodes/plan.py` - LLM-powered planning node via get_llm()
- `backend/app/services/agent_engine/nodes/execute.py` - Tool Registry-backed execution node
- `backend/app/services/agent_engine/nodes/respond.py` - LLM-powered response generation node
- `backend/app/main.py` - Lifespan with Tool Registry and checkpointer initialization
- `backend/app/api/deps.py` - get_tool_registry dependency
- `backend/pyproject.toml` - Added langgraph-checkpoint-postgres, psycopg[binary], setuptools config

## Decisions Made
- Used InMemorySaver for graph compilation tests because LangGraph validates checkpointer type via isinstance(BaseCheckpointSaver), rejecting plain MagicMock
- Added `[tool.setuptools.packages.find]` to pyproject.toml with `include = ["app*"]` to resolve flat-layout build error when installing with uv
- Added `psycopg[binary]` as explicit dependency to avoid needing system-level libpq on development machines
- Execute node uses keyword-only `tool_registry` parameter (`*, tool_registry`) for cleaner injection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added setuptools package discovery config**
- **Found during:** Task 1 (dependency installation)
- **Issue:** `uv pip install -e ".[dev]"` failed with "Multiple top-level packages discovered in a flat-layout" error because pyproject.toml lacked package discovery configuration
- **Fix:** Added `[tool.setuptools.packages.find] include = ["app*"]` to pyproject.toml
- **Files modified:** backend/pyproject.toml
- **Verification:** `uv pip install -e ".[dev]"` succeeds
- **Committed in:** 5f7a245 (Task 1 commit)

**2. [Rule 3 - Blocking] Added psycopg[binary] dependency**
- **Found during:** Task 1 (import verification)
- **Issue:** psycopg3 requires either libpq system library or binary package. Import failed with "no pq wrapper available" on macOS without libpq
- **Fix:** Added `psycopg[binary]>=3.1.0` to pyproject.toml dependencies
- **Files modified:** backend/pyproject.toml
- **Verification:** All imports succeed, all 37 tests pass
- **Committed in:** 5f7a245 (Task 1 commit)

**3. [Rule 1 - Bug] Used InMemorySaver instead of MagicMock for graph test**
- **Found during:** Task 2 (test execution)
- **Issue:** LangGraph's compile() validates checkpointer type via isinstance(BaseCheckpointSaver), so MagicMock causes TypeError
- **Fix:** Changed test to use InMemorySaver (real but lightweight checkpointer) instead of MagicMock
- **Files modified:** backend/tests/unit/test_checkpointer.py
- **Verification:** All 6 new tests pass
- **Committed in:** def8f82 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All auto-fixes necessary for build and test correctness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Agent engine fully wired: LLM-powered nodes, Tool Registry execution, PostgreSQL checkpointer
- Ready for Phase 03 (Conversation API) to expose the agent engine via REST/WebSocket
- Tool Registry singleton initialized at lifespan, available via get_tool_registry dependency
- Checkpointer initialized at lifespan, stored on app.state.checkpointer

---
*Phase: 02-agent-engine-core*
*Completed: 2026-03-29*

## Self-Check: PASSED

All 10 files verified present. Both task commits (5f7a245, def8f82) confirmed in git log.
