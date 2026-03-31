---
phase: 7
created: 2026-03-30
status: complete
---

# Phase 7 Research: Frontend

## Backend API Surface (Complete Inventory)

### Auth Endpoints (`/api/v1/auth`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| POST | `/register` | `{email, password, display_name?}` | `UserResponse` (bare, no envelope) | 201 status |
| POST | `/login` | `{email, password}` | `TokenResponse {access_token, refresh_token, token_type}` | Bare response |
| POST | `/refresh` | `{refresh_token}` | `TokenResponse` | Rotates refresh token |
| POST | `/logout` | `{refresh_token?}` | `{message: "Logged out successfully"}` | Requires auth |
| GET | `/me` | — | `UserResponse` (bare) | Requires auth |

**Auth patterns:**
- Auth endpoints return bare objects (no envelope wrapper)
- Access token: 15 min lifetime → proactive refresh at ~12 min
- Refresh token: 7 day lifetime
- Header: `Authorization: Bearer {access_token}`

### Conversation Endpoints (`/api/v1/conversations`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| POST | `` | `{title?}` | `EnvelopeResponse<ConversationResponse>` | 201, default title "New Conversation" |
| GET | `` | — | `PaginatedResponse<ConversationResponse>` | Cursor pagination `?cursor=&limit=` |
| GET | `/{id}` | — | `EnvelopeResponse<ConversationResponse>` | |
| PATCH | `/{id}` | `{title?}` | `EnvelopeResponse<ConversationResponse>` | |
| DELETE | `/{id}` | — | 204 empty | |
| PATCH | `/{id}/archive` | — | `EnvelopeResponse<ConversationResponse>` | |

### Agent Endpoints (`/api/v1/agents`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| POST | `` | `{name, system_prompt?, llm_config?}` | `EnvelopeResponse<AgentResponse>` | 201 |
| GET | `` | — | `PaginatedResponse<AgentResponse>` | Cursor pagination |
| GET | `/{id}` | — | `EnvelopeResponse<AgentResponse>` | |
| PATCH | `/{id}` | `{name?, system_prompt?, llm_config?}` | `EnvelopeResponse<AgentResponse>` | |
| DELETE | `/{id}` | — | 204 empty | |

### Message Endpoint (`/api/v1/conversations/{id}/messages`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| POST | `/conversations/{id}/messages` | `{content}` | 202 empty | Triggers async agent execution |

### Skill Endpoints (`/api/v1/skills`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| POST | `` | `multipart/form-data` (file field) | `EnvelopeResponse<SkillResponse>` | 201, hot-update on duplicate name |
| GET | `` | — | `PaginatedResponse<SkillResponse>` | Cursor pagination |
| GET | `/{id}` | — | `EnvelopeResponse<SkillResponse>` | |
| PATCH | `/{id}` | `{description?}` | `EnvelopeResponse<SkillResponse>` | |
| DELETE | `/{id}` | — | 204 empty | Disables + deletes MinIO + DB |
| POST | `/{id}/enable` | — | `EnvelopeResponse<SkillResponse>` | Starts container, registers tools |
| POST | `/{id}/disable` | — | `EnvelopeResponse<SkillResponse>` | Stops container, unregisters tools |
| GET | `/{id}/tools` | — | `EnvelopeResponse<SkillToolResponse[]>` | Lists registered tools |

### MCP Server Endpoints (`/api/v1/mcp-servers`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| POST | `` | `{name, url, transport_type?, config?}` | `EnvelopeResponse<MCPServerResponse>` | 201, async connect in background |
| GET | `` | — | `PaginatedResponse<MCPServerResponse>` | Cursor pagination |
| GET | `/{id}` | — | `EnvelopeResponse<MCPServerResponse>` | |
| PATCH | `/{id}` | `{name?, url?, transport_type?, config?}` | `EnvelopeResponse<MCPServerResponse>` | Triggers reconnect |
| DELETE | `/{id}` | — | 204 empty | Disconnect + delete |
| GET | `/{id}/tools` | — | `EnvelopeResponse<MCPToolResponse[]>` | Lists discovered tools |

### Settings Endpoints (`/api/v1/settings`)

| Method | Path | Request Body | Response | Notes |
|--------|------|-------------|----------|-------|
| GET | `` | — | `EnvelopeResponse<UserSettingsResponse>` | |
| PATCH | `` | UserSettingsUpdate | `EnvelopeResponse<UserSettingsResponse>` | |
| GET | `/system` | — | `EnvelopeResponse<SystemConfigResponse>` | No auth required |

### WebSocket Endpoint

- URL: `ws://localhost:8000/ws/chat?token={access_token}`
- Server-push only (client sends via REST)
- 5 event types sent as JSON `{type, data}`:
  - `thinking`: `{content}` — agent reasoning
  - `tool_call`: `{name, args, id?}` — tool about to be invoked
  - `tool_result`: `{name, result}` — tool completed
  - `chunk`: `{content}` — text fragment of response
  - `done`: `{thread_id}` or `{error}` — execution finished
- Uvicorn native ping/pong heartbeat (no app-level heartbeat)

### Shared Response Patterns

**EnvelopeResponse:**
```json
{"data": {...}, "meta": null}
```

**PaginatedResponse:**
```json
{"data": [...], "meta": {"cursor": "base64...", "has_more": true}}
```

**Cursor pagination:** base64-encoded `"{ISO timestamp}|{uuid}"`, passed as `?cursor=X&limit=N`

**Error format:**
```json
{"error": {"code": "ERROR_CODE", "message": "description"}}
```

### Entity Schemas (from Pydantic)

**UserResponse:** `{id: UUID, email, display_name?, avatar_url?, role, created_at}`
**ConversationResponse:** `{id: UUID, title, is_archived, created_at, updated_at}`
**AgentResponse:** `{id: UUID, name, system_prompt?, llm_config?, created_at, updated_at}`
**MessageResponse:** `{id: UUID, conversation_id, role, content, created_at}`
**SkillResponse:** `{id: UUID, name, description?, version, skill_type, status, permissions?, manifest?, created_at, updated_at}`
**MCPServerResponse:** `{id: UUID, name, url, transport_type, status, config?, created_at, updated_at}`
**SkillToolResponse:** `{name, namespaced_name, description?, input_schema?}`
**MCPToolResponse:** `{name, namespaced_name, description?, input_schema?}`

---

## Frontend Architecture Research

### Project Scaffolding

1. **Vite 7 + React 19 + TypeScript**: `npm create vite@7 frontend -- --template react-ts`
2. **shadcn/ui init**: `cd frontend && npx shadcn@latest init` — New York style, Zinc color, CSS variables
3. **Components to install**: button, card, input, label, dialog, dropdown-menu, tabs, scroll-area, separator, avatar, badge, sheet, select, slider, textarea, toast, tooltip, collapsible, switch, sonner, skeleton
4. **Dependencies**: zustand, @tanstack/react-query, react-router, react-markdown, remark-gfm, rehype-highlight, lucide-react

### State Management Strategy

**Zustand (client state):**
- `authStore`: tokens (in memory only), user profile, login/logout/refresh actions
- `uiStore`: active nav item, sidebar width, theme preference, side panel open state
- Persist only theme preference via `persist` middleware on uiStore

**React Query (server state):**
- `useConversations`: list + CRUD with cursor pagination
- `useAgents`: list + CRUD
- `useSkills`: list + CRUD + enable/disable + upload
- `useMCPServers`: list + CRUD + tools
- `useSettings`: get/update user settings
- Invalidation strategy: mutate → invalidate related queries → optimistic updates where appropriate

### API Client Design

- Base: native `fetch` (no axios dependency needed)
- Wrapper: `apiClient.get/post/patch/del(path, body?, options?)`
- Interceptors: attach `Authorization: Bearer {token}` header; on 401 → attempt refresh → retry
- Proactive token refresh: schedule timer at 80% of token lifetime (12 min for 15 min token)
- Error handling: parse `{error: {code, message}}` format, map to toast notifications

### WebSocket Hook Design

- `useWebSocket(token)`: connects on mount, reconnects with exponential backoff on disconnect
- Event routing: dispatch events to zustand chatStore based on `type` field
- Connection status: exposed as `connectionStatus: 'connecting' | 'connected' | 'disconnected'`
- Reconnection: max 5 attempts, exponential backoff (1s, 2s, 4s, 8s, 16s)
- Token refresh on reconnect

### Routing (react-router v7)

| Route | Component | Auth |
|-------|-----------|------|
| `/login` | LoginPage | No |
| `/register` | RegisterPage | No |
| `/` | ChatPage (default) | Yes |
| `/conversations/:id` | ChatPage (specific) | Yes |
| `/manage/agents` | ManageAgentsPage | Yes |
| `/manage/agents/:id` | ManageAgentsPage (selected) | Yes |
| `/manage/skills` | ManageSkillsPage | Yes |
| `/manage/servers` | ManageServersPage | Yes |
| `/manage/servers/:id` | ManageServersPage (selected) | Yes |
| `/settings` | SettingsPage | Yes |

Protected routes: redirect to `/login` if no valid token.

### Chat Streaming Implementation

1. User sends message via `POST /api/v1/conversations/{id}/messages` (returns 202)
2. Optimistically add user message to local chat state
3. WebSocket receives events in order:
   - `thinking` → append to side panel ThinkingEntry
   - `tool_call` → append ToolCallCard to side panel
   - `chunk` → append to current streaming AI message content
   - `tool_result` → append ToolResultCard to side panel
   - `done` → finalize AI message, stop streaming indicator
4. Markdown rendering on finalized messages via react-markdown + remark-gfm + rehype-highlight
5. Streaming text uses `StreamingText` component with animated cursor

### Layout Implementation

- AppShell: activity bar (48px fixed) + sidebar (260px default) + main area (flex-1)
- Activity bar: 3 icons (MessageSquare, LayoutGrid, Settings) using Lucide React
- Sidebar content changes based on active nav item
- Chat layout: header (48px) + message stream (scrollable) + side panel (320px collapsible) + input box (64px fixed bottom)
- Management layout: tab bar (40px) + list panel (left half) + detail panel (right half)

### Key Technical Decisions

1. **fetch over axios**: Native fetch sufficient; no need for axios interceptors — custom wrapper handles auth
2. **Zustand slice pattern**: Separate stores by domain (auth, chat, ui) rather than one monolithic store
3. **React Query for server state**: Keeps API data separate from UI state, handles caching/invalidation
4. **react-router v7**: Latest stable, supports lazy loading via `React.lazy()`
5. **shadcn/ui defaults**: New York style, Zinc color — matches dark-first theme requirement
6. **Vite proxy**: Dev proxy `/api/v1` and `/ws` to `http://localhost:8000`

### Validation Architecture

**Dimension 1 — External Integration Points:**
- WebSocket event parsing: 5 event types must map to correct UI actions
- API envelope unwrapping: `data` field extraction consistent across all endpoints
- Cursor pagination: base64 cursor encode/decode round-trip
- JWT refresh timing: proactive at 80% of token lifetime

**Dimension 2 — State Consistency:**
- Token refresh race condition: concurrent API calls during refresh must queue/retry
- WebSocket reconnect: events queued during disconnect must be processed on reconnect
- Optimistic updates: message send must handle 202 success but also network failure rollback

**Dimension 3 — Component Boundaries:**
- ChatStore manages messages and streaming state; React Query manages conversation list
- AuthStore manages tokens; UI never reads tokens directly — only through hooks
- Side panel state (open/closed) in uiStore; thinking/tool events in chatStore

**Dimension 4 — Error Recovery:**
- WebSocket disconnect → exponential backoff reconnect + status indicator
- API 401 → attempt refresh → redirect to login if refresh fails
- Skill upload validation error → toast with specific Chinese error message

---

## RESEARCH COMPLETE
