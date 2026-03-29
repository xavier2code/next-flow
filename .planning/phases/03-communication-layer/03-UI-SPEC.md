---
phase: 3
slug: communication-layer
status: draft
shadcn_initialized: false
preset: none
created: 2026-03-29
---

# Phase 3 — UI Design Contract

> Visual and interaction contract for the Communication Layer phase. This phase is **backend-only** (no frontend exists yet). The "UI" for this phase is the API contract that frontend clients (Phase 7) will consume: REST response shapes, WebSocket event types, and error states. Frontend design tokens, spacing, typography, and color will be specified in Phase 7.

---

## Phase Scope Note

Phase 3 builds REST API endpoints and WebSocket streaming. The project has no frontend directory, no `components.json`, no Tailwind config, and no CSS files. shadcn/ui is planned for Phase 7 (Frontend) per ROADMAP.md and REQUIREMENTS.md UI-01.

This contract therefore defines:
1. **API response contracts** -- the shapes and states downstream UI will render
2. **WebSocket event contracts** -- the typed events the frontend will handle
3. **Error state contracts** -- the error shapes the frontend will display
4. **Placeholder sections** for design tokens (to be specified in Phase 7)

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (Phase 7 scope) |
| Preset | not applicable |
| Component library | none (Phase 7 scope) |
| Icon library | none (Phase 7 scope) |
| Font | none (Phase 7 scope) |

---

## Spacing Scale

Not applicable for this phase. Deferred to Phase 7 (Frontend).

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| -- | -- | Deferred to Phase 7 |

Exceptions: none

---

## Typography

Not applicable for this phase. Deferred to Phase 7 (Frontend).

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| -- | -- | -- | Deferred to Phase 7 |

---

## Color

Not applicable for this phase. Deferred to Phase 7 (Frontend).

| Role | Value | Usage |
|------|-------|-------|
| -- | -- | Deferred to Phase 7 |

Accent reserved for: Deferred to Phase 7.

---

## API Response Contract (Phase 3 Primary Deliverable)

### Envelope Format

All REST responses use a consistent envelope (D-05):

```json
{
  "data": { ... },
  "meta": {
    "cursor": "base64_encoded_cursor_or_null",
    "has_more": false
  }
}
```

- Single-item responses: `{ "data": { ... } }` (meta omitted or null)
- List responses: `{ "data": [...], "meta": { "cursor": "...", "has_more": true } }`
- Error responses: `{ "error": { "code": "ERROR_CODE", "message": "Human-readable description" } }`

### Pagination Contract

- Cursor-based pagination using composite `created_at + UUID` cursor (D-03)
- Default page size: 20 items
- Maximum page size: 100 items
- Cursor is base64-encoded string of `{ISO_timestamp}|{UUID}`
- Ordering: `created_at DESC, id DESC`
- Response includes `meta.has_more: true` when additional items exist

### REST Endpoints (COMM-01)

| Method | Path | Status | Response Shape |
|--------|------|--------|----------------|
| POST | `/api/v1/conversations` | 201 | `{ data: ConversationResponse }` |
| GET | `/api/v1/conversations` | 200 | `{ data: [...], meta: PaginationMeta }` |
| GET | `/api/v1/conversations/{id}` | 200 | `{ data: ConversationResponse }` |
| PATCH | `/api/v1/conversations/{id}` | 200 | `{ data: ConversationResponse }` |
| DELETE | `/api/v1/conversations/{id}` | 204 | No body |
| PATCH | `/api/v1/conversations/{id}/archive` | 200 | `{ data: ConversationResponse }` |
| POST | `/api/v1/conversations/{id}/messages` | 202 | No body (D-06) |
| POST | `/api/v1/agents` | 201 | `{ data: AgentResponse }` |
| GET | `/api/v1/agents` | 200 | `{ data: [...], meta: PaginationMeta }` |
| GET | `/api/v1/agents/{id}` | 200 | `{ data: AgentResponse }` |
| PATCH | `/api/v1/agents/{id}` | 200 | `{ data: AgentResponse }` |
| DELETE | `/api/v1/agents/{id}` | 204 | No body |
| GET | `/api/v1/settings` | 200 | `{ data: UserSettingsResponse }` |
| PATCH | `/api/v1/settings` | 200 | `{ data: UserSettingsResponse }` |
| GET | `/api/v1/settings/system` | 200 | `{ data: SystemConfigResponse }` |

### WebSocket Endpoint (COMM-02)

| Path | Auth | Protocol |
|------|------|----------|
| `/ws/chat?token={jwt}` | JWT in query param, validated before accept (D-07) | WebSocket, server-push only (D-08) |

---

## WebSocket Event Contract (COMM-03)

The frontend handles exactly five event types (D-09). These are the typed events the Phase 7 UI will render.

### Event: `thinking`

Emitted when the agent's thinking process is available (custom event via `get_stream_writer()`).

```json
{
  "type": "thinking",
  "data": {
    "content": "Analyzing the user's request..."
  }
}
```

Frontend rendering (Phase 7): Collapsible section showing agent's reasoning process.

### Event: `tool_call`

Emitted when the agent invokes a tool. Sources: `on_chat_model_stream` (AIMessageChunk with `tool_calls`) and `on_tool_start`.

```json
{
  "type": "tool_call",
  "data": {
    "name": "search_web",
    "args": { "query": "NextFlow documentation" },
    "id": "call_abc123"
  }
}
```

Frontend rendering (Phase 7): Inline card showing tool name and arguments.

### Event: `tool_result`

Emitted when a tool execution completes. Source: `on_tool_end`.

```json
{
  "type": "tool_result",
  "data": {
    "name": "search_web",
    "result": "..."
  }
}
```

Frontend rendering (Phase 7): Inline card appended to the corresponding tool_call card, showing result.

### Event: `chunk`

Emitted for each token/streaming chunk of the agent's text response. Source: `on_chat_model_stream` (AIMessageChunk with text content).

```json
{
  "type": "chunk",
  "data": {
    "content": "Hello"
  }
}
```

Frontend rendering (Phase 7): Appended to the streaming response text, rendered with Markdown.

### Event: `done`

Emitted when the graph execution completes. Source: `on_chain_end` (graph-level, no parent_ids).

```json
{
  "type": "done",
  "data": {
    "thread_id": "conv_uuid"
  }
}
```

Frontend rendering (Phase 7): Marks end of streaming, enables input box, finalizes message.

### Event Mapping Source

| LangGraph astream_events v2 | WebSocket Event | Notes |
|------------------------------|-----------------|-------|
| `on_chat_model_stream` (AIMessageChunk with `tool_calls`) | `tool_call` | Incremental tool call args |
| `on_tool_start` | `tool_call` | Reliable tool invocation signal |
| `on_tool_end` | `tool_result` | Tool execution complete |
| `on_chat_model_stream` (AIMessageChunk with text content) | `chunk` | Streaming text tokens |
| Custom event via `get_stream_writer()` | `thinking` | Agent reasoning |
| `on_chain_end` (no parent_ids) | `done` | Graph execution complete |

---

## Connection Lifecycle Contract (COMM-04)

### Heartbeat

- Mechanism: WebSocket native ping/pong frames (D-10)
- No application-level heartbeat JSON messages
- Configured via Uvicorn `ws_ping_interval` and `ws_ping_timeout`

### Multi-Connection

- User may have multiple simultaneous WebSocket connections (D-12)
- All connections receive the same events via Redis pub/sub broadcast

### Disconnect

- Graceful disconnect: in-progress LangGraph workflow continues to completion (D-11)
- Results stored in PostgreSQL checkpoint
- User can reconnect and retrieve latest state
- ConnectionManager cleans up process-local connection reference

### Redis Pub/Sub

- Channel pattern: `nextflow:ws:events:{user_id}`
- Publisher: agent execution task publishes mapped events
- Subscriber: per-worker background task (started in FastAPI lifespan)
- All workers push to their local connections for the same user

---

## Copywriting Contract

### REST API Error Messages

| Error Code | HTTP Status | Copy |
|------------|-------------|------|
| `UNAUTHORIZED` | 401 | "Authentication required" |
| `FORBIDDEN` | 403 | "You do not have access to this resource" |
| `NOT_FOUND` | 404 | "{Resource} not found" |
| `VALIDATION_ERROR` | 422 | "Invalid request: {field-specific message}" |
| `CONFLICT` | 409 | "{Resource} already exists" |
| `WS_AUTH_FAILED` | N/A (WS close) | Close code 4001, reason: "Unauthorized" |

### WebSocket-Specific States

| State | Behavior |
|-------|----------|
| Auth failure | WebSocket closed with code 4001 before accept |
| Server error during stream | `done` event with `data.error` field, then clean close |
| Client disconnect mid-stream | Server continues execution, checkpoint persists result |
| Reconnection after disconnect | Client retrieves latest state via REST `GET /conversations/{id}` |

### Primary CTA

Not applicable (no frontend). Phase 7 will define CTAs.

### Empty State

| Endpoint | Empty Condition | Response |
|----------|----------------|----------|
| `GET /conversations` | User has no conversations | `{ "data": [], "meta": { "cursor": null, "has_more": false } }` |
| `GET /agents` | User has no agents | `{ "data": [], "meta": { "cursor": null, "has_more": false } }` |

Frontend empty state copy (Phase 7 responsibility):
- Conversations: "No conversations yet. Start a new conversation to begin."
- Agents: "No agents configured. Create an agent to get started."

### Destructive Actions

| Action | Method | Confirmation |
|--------|--------|-------------|
| Delete conversation | `DELETE /api/v1/conversations/{id}` | No server-side confirmation; frontend must prompt (Phase 7) |
| Delete agent | `DELETE /api/v1/agents/{id}` | No server-side confirmation; frontend must prompt (Phase 7) |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable (Phase 7) |

No third-party registries. No frontend dependencies in this phase.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS -- API error messages and state descriptions defined; frontend copy deferred to Phase 7
- [x] Dimension 2 Visuals: PASS -- No frontend visuals in this phase; API contract shapes are explicit
- [x] Dimension 3 Color: PASS -- No color contract needed; deferred to Phase 7
- [x] Dimension 4 Typography: PASS -- No typography needed; deferred to Phase 7
- [x] Dimension 5 Spacing: PASS -- No spacing needed; deferred to Phase 7
- [x] Dimension 6 Registry Safety: PASS -- No registries in use

**Approval:** pending

---

## Pre-Populated Sources

| Source | Decisions Used |
|--------|---------------|
| CONTEXT.md | 13 decisions (D-01 through D-13) |
| RESEARCH.md | Event mapping table, architecture patterns, code examples |
| REQUIREMENTS.md | COMM-01 through COMM-04 scope boundaries |
| components.json | Not found (expected -- Phase 7 scope) |
| User input | 0 (all decisions pre-populated from upstream artifacts) |
