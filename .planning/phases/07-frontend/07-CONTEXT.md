# Phase 7: Frontend - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Users have a complete web interface to manage agents, conversations, skills, and MCP servers with real-time streaming. This phase builds the entire React SPA frontend that consumes the backend REST API and WebSocket streaming protocol. Requirements UI-01 through UI-10.

</domain>

<decisions>
## Implementation Decisions

### App Layout & Navigation
- **D-01:** Sidebar + Chat main area layout — left sidebar for navigation/history, right main area for content. ChatGPT/Claude-style classic layout
- **D-02:** Activity bar-style navigation — fixed icon column on far left (like VS Code), 3 primary items: Conversations (chat icon), Management (grid icon), Settings (gear icon). Clicking an item changes sidebar content; main area shows corresponding detail
- **D-03:** Management page uses top tab bar to switch between Agent/Skills/MCP sub-modules. Tab switching updates both list panel and detail panel content
- **D-04:** Settings page accessible via activity bar gear icon — user preferences, theme toggle, account info

### Chat UX
- **D-05:** Bubble-style message display — user messages right-aligned, AI responses left-aligned. Clear visual distinction between sender types
- **D-06:** Side panel for thinking/tool events — thinking events show as collapsible reasoning entries, tool_call shows tool name + params, tool_result shows outcome. Side panel keeps message stream clean
- **D-07:** Side panel auto-appears when thinking or tool events arrive during streaming. User can manually close it. Panel persists after message completion
- **D-08:** Fixed bottom input box — does not scroll with messages. Multi-line support: Shift+Enter for newline, Enter to send
- **D-09:** Agent dropdown selector at top of chat area — user can switch which Agent handles the current conversation via dropdown
- **D-10:** Empty/new conversation state — welcome message with example prompt buttons for quick start. ChatGPT-style

### Streaming Protocol (already locked from Phase 3)
- **D-11:** WebSocket receives 5 event types: thinking, tool_call, tool_result, chunk, done — no other event types to handle
- **D-12:** Messages sent via REST POST (returns 202), streaming responses via WebSocket — decoupled channels
- **D-13:** Markdown rendering with code syntax highlighting in AI responses (react-markdown + remark-gfm + rehype-highlight)

### Management Pages
- **D-14:** List + detail panel layout — left panel shows item list, right panel shows selected item's full details with inline editing. Consistent across Agent/Skills/MCP
- **D-15:** Agent configuration — name, model selection (dropdown), system prompt (textarea), temperature (slider), llm_config JSON fields
- **D-16:** Skill management — list with status badges, upload via "Upload Skill" button triggering file dialog for ZIP selection, enable/disable toggle per skill
- **D-17:** MCP server management — list with connection status indicator lights (green=connected, yellow=connecting, red=disconnected), detail panel shows server config + discovered tools list

### Auth UI
- **D-18:** Independent full-screen auth pages — login and register are separate route pages with centered card forms on branded background
- **D-19:** JWT tokens stored in memory (not localStorage) per Phase 1 D-14. Proactive refresh before expiry

### Theme & Internationalization
- **D-20:** Dark theme as default, light theme as toggle option. Leverage shadcn/ui's built-in dark mode support with TailwindCSS v4
- **D-21:** Pure Chinese interface — all UI text, labels, placeholders, error messages in Simplified Chinese

### Claude's Discretion
- Exact component decomposition and file structure within frontend/
- Zustand store slice design (chat store, auth store, management store, etc.)
- API client setup (axios vs fetch, interceptors, error handling)
- WebSocket reconnection and retry logic
- Sidebar width, panel sizes, responsive breakpoints
- Exact shadcn/ui component selection (Dialog vs Sheet, etc.)
- Form validation library choice
- Loading states and skeleton screens
- Toast notification patterns
- Routing library (react-router) and route structure
- Vite proxy configuration for backend API

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — React SPA component, data flows, REST + WebSocket dual-channel communication
- `.planning/research/STACK.md` — React 19.x, Vite 7.x, shadcn/ui, Zustand 5.x, TailwindCSS 4.x, react-markdown, @tanstack/react-query
- `.planning/PROJECT.md` — Tech stack constraints, key decisions, shadcn/ui + Zustand decisions
- `.planning/REQUIREMENTS.md` — UI-01 through UI-10 acceptance criteria
- `CLAUDE.md` — Technology Stack section with detailed frontend library recommendations and anti-recommendations

### Phase Dependencies (MUST read)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — Auth endpoints, JWT flow, token storage strategy, error format
- `.planning/phases/03-communication-layer/03-CONTEXT.md` — REST API patterns, envelope format, cursor pagination, WebSocket protocol, 5 event types
- `.planning/phases/05-mcp-integration/05-CONTEXT.md` — MCP admin API endpoints, server status states, tool namespace format
- `.planning/phases/06-skill-system/06-CONTEXT.md` — Skill CRUD API, upload (multipart ZIP), enable/disable endpoints, skill types

### Existing Backend Code (API surface to consume)
- `backend/app/api/v1/router.py` — All API routes under /api/v1 prefix
- `backend/app/api/v1/auth.py` — Register, login, refresh, logout, me endpoints
- `backend/app/api/v1/conversations.py` — Conversation CRUD + archive
- `backend/app/api/v1/agents.py` — Agent CRUD
- `backend/app/api/v1/messages.py` — Message create (POST, returns 202)
- `backend/app/api/v1/skills.py` — Skill upload (multipart), CRUD, enable/disable
- `backend/app/api/v1/mcp_servers.py` — MCP server CRUD, tools list
- `backend/app/api/v1/settings.py` — User settings, system config
- `backend/app/api/ws/chat.py` — WebSocket endpoint (ws://host/ws/chat?token=xxx)
- `backend/app/api/ws/event_mapper.py` — Event mapping (thinking, tool_call, tool_result, chunk, done)
- `backend/app/schemas/envelope.py` — EnvelopeResponse and PaginatedResponse format
- `backend/app/schemas/` — All Pydantic request/response schemas

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Complete backend REST API: auth, conversations, agents, messages, skills, MCP servers, settings — all endpoints functional
- WebSocket streaming: 5 typed events, server-push only, Redis pub/sub for cross-worker delivery
- Envelope response format: `{data: {...}, meta: {cursor, has_more}}` — consistent across all CRUD endpoints
- Cursor pagination: base64-encoded cursor token, `?cursor=X&limit=N` query params
- JWT auth flow: register → login → access_token (15min) + refresh_token (7days) → proactive refresh

### Established Patterns
- Backend API prefix: `/api/v1`
- Auth header: `Authorization: Bearer {access_token}`
- WebSocket auth: query param `?token={access_token}`
- Error format: `{"error": {"code": "ERROR_CODE", "message": "description"}}`
- Auth endpoints return bare objects (no envelope); all other endpoints use envelope
- Cursor pagination on all list endpoints
- UUID primary keys for all entities
- Namespace format: `mcp__{server}__{tool}` and `skill__{skill}__{tool}`

### Integration Points
- Frontend project scaffold: new `frontend/` directory (Vite + React + TypeScript + shadcn/ui)
- API proxy: Vite dev server proxies `/api/v1` and `/ws` to backend (FastAPI default port 8000)
- WebSocket connection: `ws://localhost:8000/ws/chat?token={jwt}` — established on app load after auth
- REST client: base URL `/api/v1` with Bearer token interceptor and auto-refresh logic

</code_context>

<specifics>
## Specific Ideas

- Activity bar + sidebar pattern mirrors VS Code — familiar to developer audience, proven navigation model
- Side panel for streaming events keeps message stream clean while still providing transparency into agent reasoning
- Three management tabs (Agent/Skills/MCP) under one "Management" navigation item keeps the activity bar minimal
- Dark-first theme with shadcn/ui built-in dark mode — matches developer/AI tool aesthetic
- Chinese UI text with English code identifiers — user-facing labels in Chinese, technical terms (API paths, variable names) stay English

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 07-frontend*
*Context gathered: 2026-03-30*
