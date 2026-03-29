---
phase: 04-memory-system
plan: 02
subsystem: memory, database
tags: [redis, sorted-set, sliding-window, summary-compression, langgraph-store, long-term-memory, llm-dedup, memory-service, embedder-factory]

# Dependency graph
requires:
  - phase: 04-01
    provides: AsyncPostgresStore factory, embedding config in Settings, graph store wiring
provides:
  - ShortTermMemory with Redis Sorted Set sliding window and background LLM compression
  - LongTermMemory with Store-based fact storage, semantic search, and LLM dedup
  - get_embedder() factory mirroring get_llm() pattern with OpenAI/Ollama routing
  - MemoryService unified coordination layer with extract_and_store entry point
  - Complete backend/app/services/memory/ module with clean exports
affects: [04-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [redis sorted set sliding window with TTL refresh, fire-and-forget background compression, LLM-based fact deduplication, unified service composition pattern]

key-files:
  created:
    - backend/app/services/memory/short_term.py
    - backend/app/services/memory/long_term.py
    - backend/app/services/memory/embedder.py
    - backend/app/services/memory/service.py
    - backend/app/services/memory/__init__.py
  modified:
    - backend/tests/test_memory.py

key-decisions:
  - "Updated test_memory.py to match plan-specified API: thread_id parameter, nextflow:memory:short:{thread_id} key convention, ttl parameter name, get_context returning dict with summary+messages"
  - "extract_and_store filters to latest exchange only and skips short messages to avoid burning LLM tokens on trivial checks"

patterns-established:
  - "MemoryService composition: ShortTermMemory + LongTermMemory as internal components, single public API surface"
  - "Fire-and-forget async operations: extract_and_store and _compress wrap in try/except, log errors, never raise"
  - "LLM-based dedup via should_store: defaults to True on error for resilience"

requirements-completed: [MEM-01]

# Metrics
duration: 8min
completed: 2026-03-29
---

# Phase 04 Plan 02: Memory Service Module Summary

**ShortTermMemory with Redis Sorted Set sliding window + background LLM compression, LongTermMemory with Store fact storage + LLM dedup, unified MemoryService with extract_and_store entry point**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-29T12:08:33Z
- **Completed:** 2026-03-29T12:17:12Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created ShortTermMemory with Redis Sorted Set storage, atomic pipeline operations (ZADD + ZREMRANGEBYRANK + EXPIRE), and background LLM-based summary compression
- Created LongTermMemory with LangGraph Store integration for persistent fact storage, semantic search via asearch, and LLM-based deduplication (should_store)
- Created get_embedder() factory mirroring the established get_llm() pattern with OpenAI/Ollama provider routing
- Created unified MemoryService coordinating short-term and long-term memory with extract_and_store() as the single entry point for fact extraction and storage
- All 108 tests pass (7 memory tests active, 2 integration tests skipped as expected)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ShortTermMemory and get_embedder factory** - `ba80c4c` (feat)
2. **Task 2: Create LongTermMemory and unified MemoryService** - `1f63033` (feat)

## Files Created/Modified
- `backend/app/services/memory/short_term.py` - ShortTermMemory with Redis Sorted Set sliding window, TTL refresh, background compression
- `backend/app/services/memory/long_term.py` - LongTermMemory with Store fact storage, semantic search, LLM dedup
- `backend/app/services/memory/embedder.py` - get_embedder() factory with OpenAI/Ollama routing
- `backend/app/services/memory/service.py` - Unified MemoryService with extract_and_store entry point
- `backend/app/services/memory/__init__.py` - Clean module exports
- `backend/tests/test_memory.py` - Updated to match plan-specified API

## Decisions Made
- Updated test_memory.py test API to match the plan specification: `thread_id` parameter on `add_message`/`get_context`, `nextflow:memory:short:{thread_id}` key convention, `ttl` parameter name (not `ttl_seconds`), `get_context` returns dict with `summary` and `messages` keys
- `extract_and_store` filters to only the latest human+AI exchange and skips messages shorter than 10 characters to avoid wasting LLM tokens on trivial checks (Pitfall 4 heuristic)
- `should_store` defaults to True on error to ensure no facts are lost due to transient failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_memory.py API mismatch with plan-specified ShortTermMemory**
- **Found during:** Task 2 (verification)
- **Issue:** Test scaffold from Plan 01 expected a different API: `conversation_id` constructor arg, no `thread_id` on methods, `ttl_seconds` param, different key pattern, flat list return from get_context
- **Fix:** Updated all 4 MEM-01 tests to use the plan-specified API: `thread_id` on add_message/get_context, `nextflow:memory:short:` key prefix, `ttl` param, dict return with summary+messages
- **Files modified:** backend/tests/test_memory.py
- **Verification:** All 108 tests pass (7 memory tests active, 2 skipped)
- **Committed in:** 1f63033 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test API correction only. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required

None - no external service configuration required beyond what was already in place.

## Next Phase Readiness
- Memory module complete and ready for Plan 03 (wiring into Analyze and Respond nodes)
- MemoryService.extract_and_store() ready to be called after Respond node
- MemoryService.get_context() ready to be called by Analyze node for context injection
- Test scaffold fully activated: 7 tests passing

## Self-Check: PASSED

All files verified present:
- backend/app/services/memory/__init__.py, short_term.py, long_term.py, embedder.py, service.py
- backend/tests/test_memory.py

All commits verified:
- ba80c4c (Task 1), 1f63033 (Task 2)

---
*Phase: 04-memory-system*
*Completed: 2026-03-29*
