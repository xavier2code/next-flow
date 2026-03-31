# Phase 3: Communication Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 03-communication-layer
**Areas discussed:** REST API Design, WebSocket Streaming Protocol, Connection Lifecycle

---

## REST API Design — CRUD Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Complete CRUD | Full create/list/get/update/delete/archive for conversations, agents, settings | ✓ |
| Minimal set | Only create/list/get, skip update/delete/archive | |
| Claude decides | Determine scope to satisfy COMM-01 | |

**User's choice:** Complete CRUD
**Notes:** Standard RESTful resource endpoints for all entities

## REST API Design — URL Style

| Option | Description | Selected |
|--------|-------------|----------|
| Resource-nested | POST /conversations, GET /conversations/{id}, POST /conversations/{id}/messages | ✓ |
| Hybrid | RPC-style operation endpoints mixed with RESTful resources | |
| Claude decides | Design per FastAPI + OpenAPI best practices | |

**User's choice:** Resource-nested
**Notes:** Clean RESTful structure

## REST API Design — Pagination

| Option | Description | Selected |
|--------|-------------|----------|
| Cursor-based | Use cursor with created_at ordering, better for real-time data | ✓ |
| Offset-based | offset/limit params with total count, simpler but worse at scale | |
| Claude decides | Choose appropriate method | |

**User's choice:** Cursor-based

## REST API Design — Settings Scope

| Option | Description | Selected |
|--------|-------------|----------|
| User preferences only | Default model, temperature, etc. stored in users table or settings table | |
| User + System config | User preferences + system config (available models, system status) | ✓ |
| Claude decides | Determine settings API scope | |

**User's choice:** User + System configuration
**Notes:** Requires new settings model/table

## REST API Design — Response Format

| Option | Description | Selected |
|--------|-------------|----------|
| Envelope wrapping | {data: {...}, meta: {cursor, has_more}} — consistent structure | ✓ |
| Bare data + headers | Return resource directly, pagination in response headers | |
| Claude decides | Choose response format | |

**User's choice:** Envelope wrapping

## REST API Design — Chat Entry Channel

| Option | Description | Selected |
|--------|-------------|----------|
| Pure WebSocket | Both send and receive via WebSocket | |
| REST send + WS receive | POST /messages returns 202, streaming via WebSocket | ✓ |
| Claude decides | Choose communication pattern | |

**User's choice:** REST send + WS receive
**Notes:** Decouples request from response channel

## WebSocket Streaming — Authentication

| Option | Description | Selected |
|--------|-------------|----------|
| Query param token | ws://host/ws/chat?token=xxx, validated before connection | ✓ |
| First message auth | Connect first, authenticate via first message | |
| Claude decides | Design WS auth | |

**User's choice:** Query param token
**Notes:** Simple, validates before connection accepted

## WebSocket Streaming — Event Direction

| Option | Description | Selected |
|--------|-------------|----------|
| Server-only push | Server streams events, client sends messages via REST | ✓ |
| Bidirectional | Client can also send commands via WebSocket | |
| Claude decides | Design event protocol | |

**User's choice:** Server-only push
**Notes:** Simpler protocol, REST handles client→server

## WebSocket Streaming — Event Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side mapping | Map astream_events v2 to 5 typed events on server | ✓ |
| Pass-through | Send raw LangGraph events, frontend handles parsing | |
| Claude decides | Design mapping layer | |

**User's choice:** Server-side mapping
**Notes:** Frontend only handles 5 event types

## Connection Lifecycle — Heartbeat

| Option | Description | Selected |
|--------|-------------|----------|
| WS native ping/pong | Protocol-level heartbeat, no app-layer overhead | ✓ |
| App-layer heartbeat | Custom heartbeat event type in application protocol | |
| Claude decides | Choose heartbeat method | |

**User's choice:** WS native ping/pong

## Connection Lifecycle — Disconnect Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate cancel | Cancel workflow on disconnect, clean up resources | |
| Graceful + reconnect | Workflow continues, checkpoint stored, user reconnects to retrieve | ✓ |
| Claude decides | Design disconnect strategy | |

**User's choice:** Graceful completion + reconnect recovery
**Notes:** Preserves in-progress work via checkpoint

## Connection Lifecycle — Multi-Connection

| Option | Description | Selected |
|--------|-------------|----------|
| Single connection | Only one active WS per user, new kicks old | |
| Multi-connection | Multiple tabs/devices, all receive same events | ✓ |
| Claude decides | Design connection model | |

**User's choice:** Multi-connection support

## Connection Lifecycle — Event Distribution

| Option | Description | Selected |
|--------|-------------|----------|
| Redis pub/sub broadcast | Publish events to Redis channel, all workers push to local connections | ✓ |
| Targeted push | Redis tracks which worker holds which connection, push to specific worker | |
| Claude decides | Design cross-worker distribution | |

**User's choice:** Redis pub/sub broadcast

## Claude's Discretion

- Exact Pydantic schema definitions
- Cursor token encoding/decoding
- astream_events v2 event type mapping logic
- WebSocket endpoint URL path
- Ping interval and timeout values
- Settings model schema
- Redis pub/sub channel naming
- Connection manager internal data structure

## Deferred Ideas

None — discussion stayed within phase scope
