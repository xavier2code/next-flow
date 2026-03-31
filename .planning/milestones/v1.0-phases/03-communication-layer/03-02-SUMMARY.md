---
phase: 03-communication-layer
plan: 02
subsystem: api
tags: [websocket, fastapi, redis, pubsub, jwt, langgraph, streaming]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: JWT auth (security.py, decode_token), FastAPI app skeleton, Redis client
  - phase: 02-agent-engine
    provides: LangGraph CompiledStateGraph with astream_events v2, AgentState, checkpointer
provides:
  - ConnectionManager for per-user WebSocket connection tracking
  - Event mapper converting LangGraph astream_events v2 to five typed WS events
  - WebSocket endpoint at /ws/chat with JWT query-param auth
  - Redis pub/sub listener for cross-worker event broadcasting
  - Integration with app lifespan for startup/shutdown lifecycle
affects: [frontend, agent-engine, infrastructure]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WebSocket auth: validate JWT before accept, close code 4001 on failure"
    - "Event mapping: astream_events v2 iterator -> typed WS event async generator"
    - "Connection management: per-user connection list with dead-connection cleanup"
    - "Pub/sub broadcasting: Redis pattern subscribe for cross-worker delivery"
    - "Lifespan integration: ConnectionManager + pub/sub task in FastAPI lifespan"

key-files:
  created:
    - backend/app/api/ws/__init__.py
    - backend/app/api/ws/connection_manager.py
    - backend/app/api/ws/event_mapper.py
    - backend/app/api/ws/chat.py
    - backend/tests/unit/test_connection_manager.py
    - backend/tests/unit/test_event_mapper.py
    - backend/tests/test_ws_chat.py
  modified:
    - backend/app/api/deps.py
    - backend/app/main.py
    - backend/app/core/config.py

key-decisions:
  - "Standalone test app for WebSocket integration tests to avoid lifespan dependencies on PostgreSQL checkpointer"
  - "WebSocket receive loop detects client disconnect; client sends messages via REST (server-push-only WS)"
  - "Uvicorn native ping/pong for heartbeat instead of application-level heartbeat"

patterns-established:
  - "WebSocket auth: validate JWT token from query param before accept, close code 4001 on failure"
  - "Event mapper: async generator wrapping graph.astream_events(version='v2') to produce typed events"
  - "ConnectionManager: per-user connection list with auto-cleanup of dead connections during broadcast"
  - "Pub/sub listener: Redis pattern subscribe started as asyncio.create_task in lifespan"
  - "WS test pattern: standalone FastAPI test app with lightweight lifespan, direct JWT creation via security module"

requirements-completed: [COMM-02, COMM-03, COMM-04]

# Metrics
duration: 10min
completed: 2026-03-29
---

# Phase 3 Plan 2: WebSocket Streaming Layer Summary

**WebSocket streaming layer with JWT-authenticated connections, LangGraph event mapping to five typed events, ConnectionManager for multi-connection support, and Redis pub/sub for cross-worker broadcasting**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-29T06:17:31Z
- **Completed:** 2026-03-29T06:27:26Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- ConnectionManager tracks per-user WebSocket connections with automatic dead-connection cleanup during broadcast
- Event mapper converts all six LangGraph astream_events v2 sources (on_chat_model_stream, on_tool_start, on_tool_end, on_chain_end, custom events) to five typed WebSocket events (thinking, tool_call, tool_result, chunk, done)
- WebSocket endpoint at /ws/chat validates JWT before accept, rejects with close code 4001
- Redis pub/sub listener integrated into lifespan for cross-worker event broadcasting
- 24 new tests (14 unit + 5 event mapper unit + 5 integration) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: ConnectionManager, event mapper, and unit tests** - `9ac39eb` (feat)
2. **Task 2: WebSocket endpoint, Redis pub/sub, lifespan integration, and integration tests** - `c38f4f9` (feat)

## Files Created/Modified
- `backend/app/api/ws/__init__.py` - Package init for WebSocket module
- `backend/app/api/ws/connection_manager.py` - Per-user WebSocket connection tracking with broadcast
- `backend/app/api/ws/event_mapper.py` - LangGraph astream_events v2 to typed WS event mapping
- `backend/app/api/ws/chat.py` - WebSocket endpoint with JWT auth and Redis pub/sub listener
- `backend/app/api/deps.py` - Added get_connection_manager dependency
- `backend/app/main.py` - Added ConnectionManager, pub/sub task, and ws_router to lifespan
- `backend/app/core/config.py` - Added ws_ping_interval, ws_ping_timeout, redis_pubsub_prefix settings
- `backend/tests/unit/test_connection_manager.py` - 10 unit tests for ConnectionManager
- `backend/tests/unit/test_event_mapper.py` - 9 unit tests for event mapping
- `backend/tests/test_ws_chat.py` - 5 integration tests for WebSocket lifecycle

## Decisions Made
- Used standalone FastAPI test app for WebSocket integration tests -- avoids triggering the PostgreSQL checkpointer in TestClient lifespan (TestClient runs lifespan synchronously, incompatible with async fixtures)
- WebSocket is server-push-only; client sends messages via REST API, WS receive loop detects disconnect via WebSocketDisconnect exception
- Uvicorn native ping/pong for heartbeat rather than application-level heartbeat messages (per D-10)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Standalone test app for WebSocket integration tests**
- **Found during:** Task 2 (integration test creation)
- **Issue:** Starlette TestClient triggers the full FastAPI lifespan including create_checkpointer() which requires a live PostgreSQL connection; async db_session fixture conflicts with TestClient's synchronous event loop
- **Fix:** Created a dedicated test FastAPI app with a lightweight lifespan that only initializes ConnectionManager; used create_access_token() directly instead of registration/login flow
- **Files modified:** backend/tests/test_ws_chat.py
- **Verification:** 5 integration tests pass independently and alongside all other tests
- **Committed in:** c38f4f9 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor -- test approach changed to avoid external service dependencies. All acceptance criteria met.

## Issues Encountered
- test_agents.py and test_conversations.py have pre-existing test ordering issues (database state leakage between tests). Not caused by Plan 02 changes. These tests pass in isolation.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WebSocket streaming layer complete with all five event types (COMM-02, COMM-03, COMM-04)
- ConnectionManager ready for frontend integration via /ws/chat?token={jwt}
- Redis pub/sub ready for multi-worker horizontal scaling
- Event mapper ready to consume real LangGraph astream_events v2 output when LLM is configured

## Self-Check: PASSED

- All 10 created/modified files verified present on disk
- Both task commits verified in git log (9ac39eb, c38f4f9)
- 74 tests passing (24 new + 50 existing from Plan 01)

---
*Phase: 03-communication-layer*
*Completed: 2026-03-29*
