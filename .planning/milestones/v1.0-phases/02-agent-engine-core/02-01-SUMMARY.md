---
phase: 02-agent-engine-core
plan: 01
subsystem: agent-engine
tags: [langgraph, stategraph, typeddict, add_messages, conditional_edges, remaining_steps]

# Dependency graph
requires:
  - phase: 01-foundation-auth
    provides: "Project structure, pyproject.toml, service layer patterns, pytest config"
provides:
  - "AgentState TypedDict with add_messages reducer for message accumulation"
  - "build_graph() function returning compiled StateGraph with 4-node pipeline"
  - "should_execute() conditional edge routing based on tool_calls"
  - "4 async node stubs: analyze_node, plan_node, execute_node, respond_node"
  - "9 unit tests proving graph structure, state schema, and conditional routing"
affects: [02-02-llm-factory, 02-03-tool-registry, 02-04-checkpointer, 03-conversation-api]

# Tech tracking
tech-stack:
  added: ["langgraph>=1.1.0,<2.0.0", "langchain-core>=0.3.0"]
  patterns:
    - "LangGraph StateGraph with TypedDict state (not Pydantic BaseModel)"
    - "add_messages reducer for message accumulation with ID-based dedup"
    - "Conditional edge routing via should_execute function"
    - "RemainingSteps managed value for proactive recursion limit handling"
    - "Node stub pattern: async functions returning dict partials"

key-files:
  created:
    - backend/app/services/agent_engine/__init__.py
    - backend/app/services/agent_engine/state.py
    - backend/app/services/agent_engine/graph.py
    - backend/app/services/agent_engine/nodes/__init__.py
    - backend/app/services/agent_engine/nodes/analyze.py
    - backend/app/services/agent_engine/nodes/plan.py
    - backend/app/services/agent_engine/nodes/execute.py
    - backend/app/services/agent_engine/nodes/respond.py
    - backend/tests/unit/test_workflow.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Used TypedDict for AgentState instead of Pydantic BaseModel for checkpoint serialization safety (Pitfall 11)"
  - "RemainingSteps is a managed value -- verified via graph.channels, not ainvoke() output dict"
  - "Node stubs return dict partials (not full state), allowing LangGraph to merge via reducers"
  - "user_id and thread_id excluded from AgentState per D-17, passed via config['configurable']"

patterns-established:
  - "Agent engine service package: app/services/agent_engine/ with state.py, graph.py, nodes/"
  - "Graph construction: build_graph() returns CompiledStateGraph, nodes imported from nodes/ subpackage"
  - "Node function signature: async def {name}_node(state: AgentState) -> dict"

requirements-completed: [AGNT-01, AGNT-02, AGNT-06]

# Metrics
duration: 8min
completed: 2026-03-29
---

# Phase 2 Plan 1: LangGraph StateGraph Workflow Summary

**LangGraph StateGraph with 4-node pipeline (Analyze-Plan-Execute-Respond), AgentState TypedDict with add_messages reducer, conditional edge routing via should_execute, and RemainingSteps managed value**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-28T23:59:28Z
- **Completed:** 2026-03-29T00:07:34Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- AgentState TypedDict with messages (add_messages reducer), plan, scratchpad, remaining_steps fields
- Compiled StateGraph with correct 4-node topology and conditional edge from Plan node
- 9 unit tests covering state schema, node structure, conditional routing, message accumulation, and end-to-end execution
- All tests pass (GREEN phase complete)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests (TDD RED)** - `800c53b` (test)
2. **Task 2: Implement AgentState, graph, and node stubs (TDD GREEN)** - `3487b73` (feat)

_Note: TDD tasks produce 2 commits (RED + GREEN). No refactor commit needed._

## Files Created/Modified
- `backend/app/services/agent_engine/__init__.py` - Public API: AgentState, build_graph
- `backend/app/services/agent_engine/state.py` - AgentState TypedDict with add_messages reducer
- `backend/app/services/agent_engine/graph.py` - build_graph() and should_execute() functions
- `backend/app/services/agent_engine/nodes/__init__.py` - Node functions package
- `backend/app/services/agent_engine/nodes/analyze.py` - Analyze node: intent analysis stub
- `backend/app/services/agent_engine/nodes/plan.py` - Plan node: returns AIMessage without tool_calls
- `backend/app/services/agent_engine/nodes/execute.py` - Execute node: sequential tool invocation stub
- `backend/app/services/agent_engine/nodes/respond.py` - Respond node: final answer generation stub
- `backend/tests/unit/test_workflow.py` - 9 unit tests for graph, state, and conditional edges
- `backend/pyproject.toml` - Added langgraph and langchain-core dependencies

## Decisions Made
- Used TypedDict for AgentState (not Pydantic BaseModel) for checkpoint serialization safety per research Pitfall 11
- RemainingSteps managed value verified via graph.channels rather than ainvoke() output -- managed values are not returned in the output dict
- Node stubs return dict partials allowing LangGraph's reducer system to handle state merging

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_remaining_steps_present assertion**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** Test asserted `remaining_steps in result` but RemainingSteps is a managed value that does not appear in ainvoke() output dict
- **Fix:** Changed test to verify `remaining_steps in graph.channels` which correctly checks the managed value is registered in the graph
- **Files modified:** backend/tests/unit/test_workflow.py
- **Verification:** All 9 tests pass
- **Committed in:** 3487b73 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test adjustment for correct LangGraph managed value behavior. No scope creep.

## Issues Encountered
None - implementation matched plan and research patterns closely.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Agent engine graph structure is ready for LLM integration (Plan 02: nodes will call get_llm)
- Node stubs ready for Tool Registry wiring (Plan 03: execute_node will route to registry)
- Graph ready for PostgresSaver checkpointing (Plan 04: build_graph will accept checkpointer)
- All 9 tests provide a safety net for future changes

## Self-Check: PASSED

All 9 source files verified present on disk. Both task commits (800c53b, 3487b73) verified in git history.

---
*Phase: 02-agent-engine-core*
*Completed: 2026-03-29*
