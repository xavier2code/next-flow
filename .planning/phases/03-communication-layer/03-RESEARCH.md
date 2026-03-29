# Phase 3: Communication Layer - Research

**Researched:** 2026-03-29
**Domain:** REST API CRUD + WebSocket streaming with LangGraph event mapping
**Confidence:** HIGH

## Summary

Phase 3 builds the communication layer between external clients and the agent engine. It consists of two parallel tracks: (1) a REST API providing full CRUD on conversations, agents, and settings with cursor-based pagination and envelope response format, and (2) a WebSocket endpoint that streams LangGraph execution events to connected clients as five typed events (thinking, tool_call, tool_result, chunk, done). The critical technical challenge is mapping LangGraph's `astream_events` v2 event stream to the five application-level WebSocket events while maintaining clean connection lifecycle management.

The architecture uses FastAPI's native WebSocket support with Redis pub/sub for cross-worker event broadcasting, Uvicorn's built-in `ws_ping_interval`/`ws_ping_timeout` for protocol-level heartbeat, and a ConnectionManager singleton that tracks active connections per user. Chat messages enter via REST POST (returning 202 Accepted), and streaming responses are pushed through the WebSocket, cleanly separating the request and response channels.

**Primary recommendation:** Build the REST CRUD layer first (it is straightforward and independent), then the WebSocket streaming layer with its event mapper, connection manager, and Redis pub/sub integration. Test event mapping against real LangGraph execution early to validate the `astream_events` v2 event shapes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Complete CRUD for conversations, agents, and settings -- create, list, get, update, delete, archive
- **D-02:** Resource-nested URL style -- e.g., `POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages`, `GET /agents`, `PUT /agents/{id}`
- **D-03:** Cursor-based pagination for all list endpoints, using `created_at` ordering with cursor token
- **D-04:** Settings API covers both user preferences (default model, temperature, etc.) and system configuration (available models, system status) -- requires new settings model/table
- **D-05:** Envelope response format for all endpoints: `{data: {...}, meta: {cursor, has_more}}` -- consistent structure, frontend can predict response shape
- **D-06:** Chat message entry via REST -- `POST /conversations/{id}/messages` returns `202 Accepted`, streaming response pushed through WebSocket
- **D-07:** WebSocket authentication via query parameter token -- `ws://host/ws/chat?token=xxx`, validated before connection accepted
- **D-08:** Server-only push model -- WebSocket only streams events to client, client sends messages via REST POST
- **D-09:** Server-side event mapping -- LangGraph `astream_events` v2 events mapped to five typed WebSocket events: `thinking`, `tool_call`, `tool_result`, `chunk`, `done`. Frontend only handles these five event types
- **D-10:** WS native ping/pong frames for heartbeat -- server sends ping at regular interval, client auto-replies pong. No application-layer heartbeat events
- **D-11:** Graceful disconnect -- on client disconnect, in-progress LangGraph workflow continues execution to completion, results stored in checkpoint. User can reconnect and retrieve latest state
- **D-12:** Multi-connection support -- user can have multiple active WebSocket connections simultaneously (multiple tabs/devices)
- **D-13:** Redis pub/sub for cross-worker event broadcasting -- agent execution events published to Redis channel, all workers subscribe and push to their local connections for the same user

### Claude's Discretion
- Exact Pydantic schema definitions for request/response models
- Cursor token encoding/decoding implementation
- LangGraph astream_events v2 event type to WebSocket event mapping logic
- WebSocket endpoint URL path (e.g., `/ws/chat` vs `/ws/stream`)
- Ping interval and timeout configuration values
- Settings model schema and storage details
- Redis pub/sub channel naming convention
- Connection manager internal data structure

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMM-01 | REST API endpoints for CRUD on conversations, agents, and settings | Standard Stack: FastAPI routes + Pydantic schemas + SQLAlchemy async queries. Architecture Pattern: Layered routes -> services -> models. Cursor-based pagination with `created_at` ordering (D-03). Envelope response format (D-05). |
| COMM-02 | WebSocket endpoint with LangGraph v2 streaming integration | Standard Stack: FastAPI WebSocket + LangGraph `astream_events(version="v2")`. Architecture Pattern: ConnectionManager singleton tracks per-user connections. Redis pub/sub for cross-worker broadcasting (D-13). |
| COMM-03 | Event mapping from LangGraph StreamParts to WebSocket events (thinking, tool_call, tool_result, chunk, done) | Event Mapping section below documents exact `astream_events` v2 event names to WebSocket event type mapping. `get_stream_writer()` for custom thinking events. `on_chat_model_stream` for chunks, `on_tool_start`/`on_tool_end` for tool events. |
| COMM-04 | Connection lifecycle management with heartbeat, cleanup on disconnect | Uvicorn `ws_ping_interval`/`ws_ping_timeout` for protocol-level ping/pong (D-10). ConnectionManager with graceful disconnect: in-progress workflows continue, results persisted to checkpoint (D-11). Multi-connection support per user (D-12). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.x (installed) | REST endpoints + WebSocket server | Already in project. Native WebSocket support, Pydantic v2 validation, auto OpenAPI docs. |
| LangGraph | >=1.1.0 (installed) | Agent engine producing streaming events | Already in project. `astream_events(version="v2")` provides the event stream to map. |
| LangChain Core | >=0.3.0 (installed) | `astream_events` v2 event protocol, `adispatch_custom_event` | Already in project. Defines the StreamEvent schema with `event`, `name`, `data`, `metadata`, `run_id`, `parent_ids`. |
| redis (async) | >=5.0.0 (installed) | Pub/sub for cross-worker event broadcasting | Already in project. `redis.asyncio` provides async `pubsub.listen()` (AsyncIterator), `publish()`, `subscribe()`. |
| SQLAlchemy | >=2.0.0 (installed) | Async DB queries for CRUD operations | Already in project. `AsyncSession`, `select()`, `update()`, `delete()` for CRUD. |
| Pydantic | 2.x (via FastAPI) | Request/response schema validation | Already in project. `BaseModel` for all schemas, `model_config = {"from_attributes": True}` for ORM mode. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyJWT | >=2.10.0 (installed) | WebSocket auth token validation | Validating JWT from `?token=` query param before accepting WebSocket connection. Reuse existing `decode_token()` from `core/security.py`. |
| structlog | >=24.0.0 (installed) | Structured logging for streaming events | Log event mapping, connection lifecycle, pub/sub activity. |
| httpx | >=0.28.0 (installed) | WebSocket test client | Testing WebSocket endpoints via `httpx.AsyncClient` or `starlette.testclient.WebSocketTestSession`. |

### No New Installations Required
All dependencies for this phase are already installed. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/
│   ├── v1/
│   │   ├── router.py          # Add conversation, agent, settings routers
│   │   ├── auth.py            # Existing (pattern reference)
│   │   ├── conversations.py   # NEW: CRUD endpoints for conversations
│   │   ├── agents.py          # NEW: CRUD endpoints for agents
│   │   ├── settings.py        # NEW: user preferences + system config
│   │   └── messages.py        # NEW: POST /conversations/{id}/messages (202)
│   ├── deps.py                # Add get_connection_manager dependency
│   └── ws/
│       ├── __init__.py
│       ├── chat.py            # NEW: WebSocket endpoint
│       ├── connection_manager.py  # NEW: ConnectionManager singleton
│       └── event_mapper.py    # NEW: astream_events -> WS event mapping
├── schemas/
│   ├── conversation.py        # NEW: ConversationCreate, ConversationResponse, etc.
│   ├── agent.py               # NEW: AgentCreate, AgentUpdate, AgentResponse
│   ├── settings.py            # NEW: UserPreferences, SystemConfig
│   ├── message.py             # NEW: MessageCreate, MessageResponse
│   └── envelope.py            # NEW: EnvelopeResponse, PaginatedResponse
├── services/
│   ├── conversation_service.py # NEW: CRUD business logic
│   ├── agent_service.py       # NEW: CRUD business logic
│   ├── settings_service.py    # NEW: preferences + config logic
│   └── agent_engine/          # Existing (call from communication layer)
├── models/
│   ├── settings.py            # NEW: UserSettings model (user preferences)
│   ├── conversation.py        # Existing (extend if needed)
│   └── agent.py               # Existing (extend if needed)
```

### Pattern 1: Layered Route -> Service -> Model (REST CRUD)
**What:** Every REST endpoint follows: route handler validates request via Pydantic schema, delegates to service layer for business logic, service uses SQLAlchemy async session for data access. Route never touches DB directly.
**When to use:** All REST endpoints (conversations, agents, settings).
**Example:**
```python
# Follows existing auth.py pattern exactly
# backend/app/api/v1/conversations.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.schemas.envelope import EnvelopeResponse
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("", status_code=201)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EnvelopeResponse[ConversationResponse]:
    conversation = await ConversationService.create(db, user.id, data)
    return EnvelopeResponse(data=ConversationResponse.model_validate(conversation))
```

### Pattern 2: ConnectionManager Singleton for WebSocket Lifecycle
**What:** A singleton class that tracks all active WebSocket connections per user. Supports multiple connections per user (D-12). Provides methods to broadcast events to all connections for a user, clean up on disconnect, and check liveness.
**When to use:** All WebSocket connection management.
**Example:**
```python
# backend/app/api/ws/connection_manager.py
import asyncio
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()

class ConnectionManager:
    """Manages active WebSocket connections per user.

    Supports multi-connection per user (D-12).
    Thread-safe via asyncio (single event loop per worker).
    """

    def __init__(self):
        # user_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    def connect(self, user_id: str, websocket: WebSocket) -> None:
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws is not websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def broadcast_to_user(self, user_id: str, event: dict) -> None:
        connections = self._connections.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    def get_connections(self, user_id: str) -> list[WebSocket]:
        return self._connections.get(user_id, [])
```

### Pattern 3: Event Mapper (astream_events v2 -> WebSocket Events)
**What:** A pure function that maps each LangGraph `astream_events` v2 event to one of five WebSocket event types. Isolates frontend from LangGraph internals (D-09).
**When to use:** Inside WebSocket streaming loop.
**Mapping table (verified from installed LangChain source):**

| LangGraph astream_events v2 event | WebSocket event | Data payload |
|----------------------------------|-----------------|-------------|
| `on_chat_model_stream` (AIMessageChunk with `tool_calls`) | `tool_call` | `{"name": ..., "args": ..., "id": ...}` |
| `on_tool_start` | `tool_call` | `{"name": event["name"], "args": event["data"]["input"]}` |
| `on_tool_end` | `tool_result` | `{"name": event["name"], "result": event["data"]["output"]}` |
| `on_chat_model_stream` (AIMessageChunk with text content) | `chunk` | `{"content": event["data"]["chunk"].content}` |
| Custom event via `get_stream_writer()` or `adispatch_custom_event()` | `thinking` | `{"content": ...}` |
| `on_chain_end` (graph-level, name matching graph) | `done` | `{"thread_id": ...}` |

**Example:**
```python
# backend/app/api/ws/event_mapper.py
from langchain_core.messages import AIMessageChunk

async def map_stream_events(graph, user_input: str, config: dict):
    """Yield mapped WebSocket events from LangGraph execution."""
    async for event in graph.astream_events(
        {"messages": [HumanMessage(content=user_input)]},
        config,
        version="v2",
    ):
        kind = event["event"]
        data = event.get("data", {})

        if kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if isinstance(chunk, AIMessageChunk):
                if chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        yield {"type": "tool_call", "data": {
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {}),
                            "id": tc.get("id", ""),
                        }}
                elif chunk.content:
                    yield {"type": "chunk", "data": {"content": chunk.content}}

        elif kind == "on_tool_start":
            yield {"type": "tool_call", "data": {
                "name": event["name"],
                "args": data.get("input", {}),
            }}

        elif kind == "on_tool_end":
            yield {"type": "tool_result", "data": {
                "name": event["name"],
                "result": data.get("output"),
            }}

        elif kind == "on_chain_end":
            # Only emit 'done' for the top-level graph completion
            if not event.get("parent_ids"):
                yield {"type": "done", "data": {}}
```

### Pattern 4: Redis Pub/Sub for Cross-Worker Broadcasting
**What:** When running multiple Uvicorn workers, agent execution happens on one worker but the user's WebSocket connections may be distributed across workers. Redis pub/sub ensures all workers can push events to their local connections.
**When to use:** Always -- even with single worker, pub/sub decouples execution from connection management.
**Example:**
```python
# Channel naming: nextflow:ws:events:{user_id}
# Publisher (in event streaming loop):
await redis.publish(f"nextflow:ws:events:{user_id}", json.dumps(event))

# Subscriber (background task per worker):
async def subscribe_to_user_events(redis, manager: ConnectionManager):
    pubsub = redis.pubsub()
    # Subscribe to all user event channels via pattern
    await pubsub.psubscribe("nextflow:ws:events:*")
    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            channel = message["channel"]  # e.g., "nextflow:ws:events:user123"
            user_id = channel.split(":")[-1]
            event = json.loads(message["data"])
            await manager.broadcast_to_user(user_id, event)
```

### Anti-Patterns to Avoid
- **Calling graph.ainvoke() or graph.invoke() in WebSocket handler:** Must use `astream_events(version="v2")` to get streaming events. Synchronous invoke blocks the event loop (Pitfall 12).
- **Application-level heartbeat JSON messages:** Use Uvicorn's native `ws_ping_interval`/`ws_ping_timeout` instead (D-10). No `{type: "ping"}` / `{type: "pong"}` messages -- wastes bandwidth and adds complexity.
- **Storing WebSocket connections in Redis:** Connections are process-local (file descriptors). Only store events/data in Redis, not connection references.
- **Validating JWT on every WebSocket message:** Validate once on connect (D-07). Token is in query param, not per-message header.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket heartbeat | Application-level ping/pong JSON messages | Uvicorn `ws_ping_interval` / `ws_ping_timeout` config | Protocol-level ping/pong is more reliable, handled by the ASGI server, and requires zero application code. Uvicorn defaults: `ws_ping_interval=20.0`, `ws_ping_timeout=20.0`. |
| Event streaming | Custom SSE or polling | LangGraph `astream_events(version="v2")` | LangGraph provides rich event types (on_chat_model_stream, on_tool_start, on_tool_end) with proper async iteration. Building custom streaming loses checkpoint integration. |
| Custom event dispatch | Custom event bus | `get_stream_writer()` from `langgraph.config` or `adispatch_custom_event()` from `langchain_core.callbacks.manager` | These integrate natively with `astream_events` v2 and appear as custom events in the stream. |
| Cursor pagination | Offset-based pagination | Cursor-based with base64-encoded `created_at` + UUID | Offset pagination degrades on large tables and is unstable with inserts. Cursor-based is index-friendly on `(created_at, id)`. |
| JWT validation in WebSocket | Re-implement JWT decode | Reuse `decode_token()` from `app.core.security` | Already handles algorithm, expiry, and error formatting. |
| Cross-worker messaging | Direct connection sharing between workers | Redis pub/sub | Connections are process-local. Redis pub/sub is the standard pattern for distributing events across workers. |

**Key insight:** The most complex component is the event mapper. It MUST be tested against real LangGraph execution because `astream_events` v2 event shapes vary by LLM provider (OpenAI vs Ollama produce slightly different chunk structures for tool calls).

## Common Pitfalls

### Pitfall 1: astream_events v2 Event Shape Differences Between Providers
**What goes wrong:** The event mapper works with OpenAI but breaks with Ollama (or vice versa). OpenAI streams tool call arguments incrementally (multiple `on_chat_model_stream` chunks with partial `tool_calls`), while Ollama may emit tool calls differently. The mapper assumes a specific chunk structure that only matches one provider.
**Why it happens:** LangChain normalizes `tool_calls` on `AIMessage` but `AIMessageChunk` streaming behavior varies. Some providers emit empty content chunks before tool calls, others include `additional_kwargs` with provider-specific data.
**How to avoid:** (1) Test event mapper with both OpenAI and Ollama. (2) Check for `tool_calls` on AIMessageChunk robustly -- handle both incremental and complete tool call chunks. (3) Use `on_tool_start`/`on_tool_end` as the reliable tool event source (these are always emitted regardless of provider), not `on_chat_model_stream` tool_call chunks. (4) The `on_tool_start` event has `data.input` with the full args dict; `on_tool_end` has `data.output` with the result.
**Warning signs:** Tool calls missing in WebSocket stream with one provider but not another. Chunks with empty content. Tool call events appearing twice.

### Pitfall 2: WebSocket Disconnect During Active Graph Execution
**What goes wrong:** Client disconnects mid-execution. The `websocket.send_json()` raises `WebSocketDisconnect` or `ConnectionClosed`, and the unhandled exception crashes the handler or leaks resources. The graph execution continues running on a dead connection.
**Why it happens:** FastAPI/Starlette does not auto-detect disconnect during long-running operations. The disconnect is only detected when the server tries to send.
**How to avoid:** (1) Wrap the entire streaming loop in `try/except (WebSocketDisconnect, Exception)`. (2) In the `finally` block, unregister from ConnectionManager. (3) Per D-11, the graph execution continues to completion -- the checkpointer saves the final state. (4) When the user reconnects, they can retrieve the latest state from the checkpointer.
**Warning signs:** Unhandled `WebSocketDisconnect` exceptions in logs. Memory leak from abandoned connections. Graph executions reported as "timed out" when they actually completed but the results were discarded.

### Pitfall 3: Cursor Pagination with Non-Unique Timestamps
**What goes wrong:** Multiple records have the same `created_at` timestamp (common with batch inserts or fast operations). Using only `created_at` as cursor causes pagination to skip or duplicate records.
**Why it happens:** Timestamps have millisecond precision but database operations can complete within the same millisecond, creating duplicate timestamps.
**How to avoid:** Use a composite cursor: `base64(f"{created_at_iso}|{uuid}")`. The WHERE clause is `WHERE (created_at, id) < (cursor_ts, cursor_id) ORDER BY created_at DESC, id DESC`. Create a composite index on `(created_at DESC, id DESC)` for efficient cursor-based lookups.
**Warning signs:** Missing or duplicate items when paginating through rapidly created records. Pagination returning fewer items than the page size.

### Pitfall 4: Redis Pub/Sub Listener Not Starting on Worker Startup
**What goes wrong:** The Redis pub/sub listener task is started inside the WebSocket handler instead of during application startup. If no WebSocket connections exist yet, the listener never starts. When the first connection is established, it misses events that were published before the listener subscribed.
**Why it happens:** Pub/sub subscription is typically added inside connection handlers for simplicity, but it should be a long-lived background task per worker.
**How to avoid:** Start the pub/sub listener as a background task in the FastAPI lifespan startup (alongside Redis and checkpointer initialization). Use `psubscribe` with a pattern to catch all user channels. The listener runs for the worker's lifetime.
**Warning signs:** Events not reaching WebSocket clients intermittently. Events only arrive when multiple workers have active connections.

### Pitfall 5: WebSocket Auth Token in Query Param Logging
**What goes wrong:** JWT tokens in WebSocket query parameters (`?token=xxx`) get logged by access logs, middleware, or error handlers, leaking authentication credentials into log storage.
**Why it happens:** Standard HTTP access logging includes full URLs. Error handlers may log the request URL including query parameters.
**How to avoid:** (1) Configure Uvicorn/access logging to strip or redact query parameters on WebSocket endpoints. (2) In middleware, detect WebSocket upgrade requests and sanitize the URL before logging. (3) Use a short-lived one-time token for WebSocket auth (generate a temporary WS-specific token via REST that expires in 60 seconds) rather than reusing the long-lived access token.
**Warning signs:** JWT tokens visible in log aggregation systems. Access logs showing `ws://host/ws/chat?token=eyJ...`.

### Pitfall 6: Missing Message Model for Chat History Persistence
**What goes wrong:** The `POST /conversations/{id}/messages` endpoint triggers graph execution but does not persist the user's message or the agent's response to the database. Only the LangGraph checkpointer stores state. When the user refreshes the conversation list, messages are gone.
**Why it happens:** The checkpointer stores LangGraph state (messages in AgentState format), but there is no separate `messages` table for easy REST retrieval. Reading messages from the checkpointer requires graph-specific API calls, not simple SQL queries.
**How to avoid:** Create a `Message` model (id, conversation_id, role, content, created_at). Persist user messages before triggering graph execution. Persist agent responses after completion (or from the `done` event). This provides fast message retrieval via simple SQL without touching the checkpointer.
**Warning signs:** Conversation detail endpoint has no messages. Needing to call LangGraph checkpointer APIs just to display chat history.

## Code Examples

Verified patterns from installed package source code and existing project patterns:

### WebSocket Authentication via Query Parameter
```python
# Source: Verified against installed starlette.WebSocket API
# backend/app/api/ws/chat.py
from fastapi import WebSocket, Query
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException

async def get_user_from_ws_token(token: str) -> str:
    """Validate JWT from WebSocket query param, return user_id."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Invalid token")
    return user_id

@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    # Validate auth BEFORE accepting connection
    try:
        user_id = await get_user_from_ws_token(token)
    except UnauthorizedException:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    # ... connection lifecycle
```

### LangGraph astream_events v2 Event Structure
```python
# Source: Verified from installed langchain_core.runnables.base.Runnable.astream_events docstring
# Event structure (v2 schema):
{
    "event": "on_chat_model_stream",      # Event type name
    "name": "ChatOpenAI",                  # Runnable name
    "data": {                              # Event-specific data
        "chunk": AIMessageChunk(content="hello")
    },
    "metadata": {},                        # Runnable metadata
    "tags": [],                            # Runnable tags
    "run_id": "uuid",                      # Unique run identifier
    "parent_ids": ["uuid"],                # Parent chain (v2 only)
}

# Complete event type list (from source):
# on_chat_model_start, on_chat_model_stream, on_chat_model_end
# on_llm_start, on_llm_stream, on_llm_end
# on_chain_start, on_chain_stream, on_chain_end
# on_tool_start, on_tool_end
# on_retriever_start, on_retriever_end
# on_prompt_start, on_prompt_end
# Custom events via adispatch_custom_event()
```

### Cursor Token Encoding/Decoding
```python
# backend/app/schemas/envelope.py
import base64
from datetime import datetime
from pydantic import BaseModel, Field
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginationMeta(BaseModel):
    cursor: str | None = None
    has_more: bool = False

class EnvelopeResponse(BaseModel, Generic[T]):
    data: T
    meta: dict | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta

def encode_cursor(created_at: datetime, item_id: str) -> str:
    """Encode cursor from timestamp + UUID."""
    raw = f"{created_at.isoformat()}|{item_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()

def decode_cursor(cursor: str) -> tuple[datetime, str]:
    """Decode cursor to (created_at, id) tuple."""
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, item_id = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), item_id
```

### Service Layer Pattern (follows existing user_service.py pattern)
```python
# backend/app/services/conversation_service.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation

class ConversationService:
    @staticmethod
    async def create(db: AsyncSession, user_id, data) -> Conversation:
        conv = Conversation(user_id=user_id, title=data.title)
        db.add(conv)
        await db.flush()
        return conv

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: str,
        cursor_ts=None,
        cursor_id=None,
        limit: int = 20,
    ) -> tuple[list[Conversation], bool]:
        """List conversations with cursor pagination.

        Returns (items, has_more). Fetches limit+1 to detect has_more.
        """
        q = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        ).order_by(Conversation.created_at.desc(), Conversation.id.desc())

        if cursor_ts and cursor_id:
            q = q.where(
                (Conversation.created_at, Conversation.id) < (cursor_ts, cursor_id)
            )

        q = q.limit(limit + 1)
        result = await db.execute(q)
        items = result.scalars().all()
        has_more = len(items) > limit
        return items[:limit], has_more
```

### Chat Message Trigger (REST POST -> 202 -> WebSocket streaming)
```python
# backend/app/api/v1/messages.py
from fastapi import APIRouter, Depends, Response
from app.api.deps import get_current_user, get_db
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService

router = APIRouter()

@router.post("/conversations/{conversation_id}/messages", status_code=202)
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept chat message, trigger agent execution. Response streamed via WebSocket.

    Per D-06: Returns 202 Accepted immediately. The agent processes the message
    and streams results through the user's WebSocket connection.
    """
    # Validate conversation ownership
    conversation = await ConversationService.get_for_user(db, user.id, conversation_id)
    if not conversation:
        raise NotFoundException(message="Conversation not found")

    # Persist user message
    message = await ConversationService.add_message(
        db, conversation_id, role="user", content=data.content
    )

    # Trigger async agent execution (publishes to Redis for streaming)
    # The actual execution is picked up by a background task or the
    # WebSocket handler's streaming loop.
    await trigger_agent_execution(
        conversation_id=conversation_id,
        user_id=str(user.id),
        message=data.content,
    )

    return Response(status_code=202)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraph `astream_events` v1 | `astream_events` v2 | LangChain 0.2.x | v1 deprecated, will be removed in 0.4.0. v2 adds `parent_ids` and custom event support. Always pass `version="v2"`. |
| Application-level WebSocket ping/pong | Uvicorn native `ws_ping_interval` | Uvicorn 0.20+ | Protocol-level ping is more reliable and requires zero app code. Configure in uvicorn.run() or uvicorn.Config. |
| `langchain_community.chat_models.ChatOllama` | `langchain_ollama.ChatOllama` | langchain-ollama >= 1.0.0 | Already adopted in Phase 2 (verified in llm.py). |
| `InMemorySaver` for testing | `AsyncPostgresSaver` | LangGraph 1.0+ | Production uses AsyncPostgresSaver. InMemorySaver still valid for unit tests. Already established in Phase 2. |

**Deprecated/outdated:**
- `astream_events` v1: Use `version="v2"` parameter. v1 lacks `parent_ids` and custom events.
- `Socket.IO`: Not needed. FastAPI native WebSocket is sufficient (explicitly decided in STACK.md anti-recommendations).

## Open Questions

1. **Message persistence strategy**
   - What we know: Conversation model exists but no Message model. LangGraph checkpointer stores message history in its own tables.
   - What's unclear: Whether to create a separate `messages` table for REST retrieval, or read from the checkpointer.
   - Recommendation: Create a `Message` model. Reading from the checkpointer requires graph-specific API calls and serializes LangChain message objects. A simple `messages` table (id, conversation_id, role, content, metadata_json, created_at) provides fast SQL retrieval for conversation history display. Persist user messages before execution, agent responses after completion.

2. **Settings model design**
   - What we know: D-04 requires settings API for both user preferences and system configuration.
   - What's unclear: Single table vs. split tables for user preferences vs. system config.
   - Recommendation: Two models: `UserSettings` (user_id FK, preferences JSON) and use existing Settings/Pydantic for system config from environment. User settings override system defaults. Single `user_settings` table with `user_id` unique constraint and `preferences` JSON field.

3. **Agent execution trigger mechanism**
   - What we know: REST POST returns 202. Agent execution needs to happen asynchronously and stream events via WebSocket.
   - What's unclear: Whether to use a background task (`asyncio.create_task`), a dedicated execution queue, or have the WebSocket handler itself pick up pending executions.
   - Recommendation: Use `asyncio.create_task` for Phase 3. The task publishes events to Redis pub/sub. The WebSocket handler (or its pub/sub listener) picks up events and pushes to the client. This is simpler than Celery for Phase 3 and avoids the complexity of task serialization.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | REST CRUD, checkpointer | Available (Docker) | 16 | -- |
| Redis | Pub/sub, session store | Available (Docker) | 7-alpine (port 6380) | -- |
| Python 3.12 | Backend runtime | Available (.venv) | 3.12 | -- |
| FastAPI | REST + WebSocket | Available (.venv) | 0.135.x | -- |
| LangGraph | Agent engine | Available (.venv) | >=1.1.0 | -- |
| langchain-core | astream_events | Available (.venv) | >=0.3.0 | -- |
| Uvicorn | ASGI server with WS ping | Available (.venv) | >=0.34.0 | -- |
| Docker Compose | PostgreSQL, Redis | Available | Running | -- |

**Missing dependencies with no fallback:**
- None -- all dependencies are available.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `.venv/bin/python -m pytest tests/ -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMM-01 | REST CRUD conversations | integration | `.venv/bin/python -m pytest tests/test_conversations.py -x` | Wave 0 |
| COMM-01 | REST CRUD agents | integration | `.venv/bin/python -m pytest tests/test_agents.py -x` | Wave 0 |
| COMM-01 | REST CRUD settings | integration | `.venv/bin/python -m pytest tests/test_settings.py -x` | Wave 0 |
| COMM-01 | Cursor pagination | unit | `.venv/bin/python -m pytest tests/unit/test_pagination.py -x` | Wave 0 |
| COMM-02 | WebSocket connection + auth | integration | `.venv/bin/python -m pytest tests/test_ws_chat.py -x` | Wave 0 |
| COMM-02 | 202 Accepted on message POST | integration | `.venv/bin/python -m pytest tests/test_messages.py -x` | Wave 0 |
| COMM-03 | Event mapping (astream_events -> WS events) | unit | `.venv/bin/python -m pytest tests/unit/test_event_mapper.py -x` | Wave 0 |
| COMM-04 | Connection lifecycle (connect, disconnect, cleanup) | integration | `.venv/bin/python -m pytest tests/unit/test_connection_manager.py -x` | Wave 0 |
| COMM-04 | Multi-connection per user | unit | `.venv/bin/python -m pytest tests/unit/test_connection_manager.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/ -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_conversations.py` -- covers COMM-01 conversation CRUD
- [ ] `tests/test_agents.py` -- covers COMM-01 agent CRUD
- [ ] `tests/test_settings.py` -- covers COMM-01 settings CRUD
- [ ] `tests/test_messages.py` -- covers COMM-02 message POST (202)
- [ ] `tests/test_ws_chat.py` -- covers COMM-02 WebSocket streaming
- [ ] `tests/unit/test_pagination.py` -- covers cursor encoding/decoding
- [ ] `tests/unit/test_event_mapper.py` -- covers COMM-03 event mapping
- [ ] `tests/unit/test_connection_manager.py` -- covers COMM-04 lifecycle

## Sources

### Primary (HIGH confidence)
- Installed `langchain_core.runnables.base.Runnable.astream_events` source code -- verified v2 event schema with all event types, StreamEvent structure, custom event support
- Installed `langgraph.config.get_stream_writer` -- verified signature `() -> Callable[[Any], None]`
- Installed `langchain_core.callbacks.manager.adispatch_custom_event` -- verified signature for custom event dispatch
- Installed `starlette.websockets.WebSocket` -- verified all methods: accept, send_json, receive_json, close, send_text, iter_json
- Installed `uvicorn.Config` -- verified `ws_ping_interval=20.0`, `ws_ping_timeout=20.0`, `ws_per_message_deflate=True` defaults
- Installed `redis.asyncio` pubsub -- verified async `subscribe()`, `listen()` (AsyncIterator), `aclose()`, `ping()`
- Existing codebase: `api/v1/auth.py`, `services/auth_service.py`, `schemas/auth.py` -- patterns for routes, services, schemas
- Existing codebase: `services/agent_engine/graph.py` -- `build_graph()` returns `CompiledStateGraph`, `astream_events` available
- Existing codebase: `services/agent_engine/state.py` -- `AgentState` TypedDict
- Existing codebase: `core/security.py` -- `decode_token()` for JWT validation reuse
- Existing codebase: `db/redis.py` -- `KEY_PREFIX = "nextflow"` naming convention
- ARCHITECTURE.md -- Pattern 6 (WebSocket Streaming with Backpressure)
- PITFALLS.md -- Pitfall 6 (WebSocket Connection Lifecycle), Pitfall 12 (FastAPI Sync Blocking)

### Secondary (MEDIUM confidence)
- LangGraph streaming documentation patterns (verified against installed source, not live docs due to API limit)
- Redis pub/sub channel naming pattern based on existing `nextflow:{domain}:{key}` convention

### Tertiary (LOW confidence)
- None -- all critical findings verified against installed package source code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages already installed in project .venv, versions verified
- Architecture: HIGH -- patterns follow established project conventions (auth.py, user_service.py), verified against installed library APIs
- Event mapping: HIGH -- verified astream_events v2 schema from installed langchain_core source docstring
- Pitfalls: HIGH -- based on verified library APIs and established project patterns
- WebSocket lifecycle: HIGH -- Uvicorn ping config verified from installed source, Starlette WebSocket API verified

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (30 days -- stable stack, no fast-moving dependencies)
