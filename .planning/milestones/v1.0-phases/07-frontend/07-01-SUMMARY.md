---
phase: 07-frontend
plan: 01
subsystem: ui
tags: [react, vite, shadcn-ui, zustand, typescript, tailwindcss, websocket, auth]

# Dependency graph
requires:
  - phase: 01-foundation-auth
    provides: JWT auth endpoints (register, login, refresh, logout, me) and token format
  - phase: 03-communication-layer
    provides: REST API envelope format, WebSocket protocol, 5 event types
provides:
  - Frontend project scaffold (Vite 7 + React 19 + TypeScript + TailwindCSS v4)
  - shadcn/ui component library with 20 components installed
  - TypeScript type definitions matching all backend Pydantic schemas
  - API client with auth interceptor, 401 refresh queue, envelope unwrapping
  - Zustand stores: auth-store, ui-store, chat-store
  - WebSocket hook with exponential backoff reconnection
  - Auth pages (login/register) with Chinese UI
  - App shell layout with activity bar, sidebar, main area
  - Route protection and navigation structure
affects: [07-02-PLAN, 07-03-PLAN, 07-04-PLAN]

# Tech tracking
tech-stack:
  added: [react@19, vite@7, typescript@5.8, tailwindcss@4, shadcn/ui, zustand@5, @tanstack/react-query@5, react-router@7, react-markdown@10, vitest@4, @testing-library/react, lucide-react]
  patterns: [zustand-slice-store, api-client-auth-interceptor, ws-hook-reconnection, protected-route, activity-bar-layout]

key-files:
  created:
    - frontend/src/lib/api-client.ts
    - frontend/src/stores/auth-store.ts
    - frontend/src/stores/ui-store.ts
    - frontend/src/stores/chat-store.ts
    - frontend/src/types/api.ts
    - frontend/src/types/ws-events.ts
    - frontend/src/hooks/use-websocket.ts
    - frontend/src/hooks/use-auth.ts
    - frontend/src/components/auth/LoginPage.tsx
    - frontend/src/components/auth/RegisterPage.tsx
    - frontend/src/components/layout/AppShell.tsx
    - frontend/src/components/layout/ActivityBar.tsx
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/pages/ProtectedRoute.tsx
  modified:
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/index.css

key-decisions:
  - "Used callback registration pattern (registerAuthCallbacks) to avoid circular imports between api-client and auth-store"
  - "Chat store dynamically imports ui-store for side-panel auto-open to avoid circular dependency at module load"
  - "Dark theme default with shadcn/ui CSS variable swap -- dark class on html root"

patterns-established:
  - "API client: lazy auth callbacks via registerAuthCallbacks for circular dependency avoidance"
  - "Zustand stores: create() with explicit state/actions interface split"
  - "UI store: persist middleware with partialize for theme-only localStorage persistence"
  - "WebSocket hook: exponential backoff (1s-16s) with token refresh before reconnect"
  - "Layout: activity bar (48px) + sidebar (260px) + main area (flex-1)"
  - "All user-facing text in Simplified Chinese per D-21"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 20min
completed: 2026-03-31
---

# Phase 7 Plan 01: Frontend Scaffold Summary

**Vite 7 + React 19 + shadcn/ui scaffold with auth pages, API client with 401 refresh, Zustand stores, and WebSocket hook**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-31T00:48:54Z
- **Completed:** 2026-03-31T01:09:35Z
- **Tasks:** 2
- **Files modified:** 57

## Accomplishments
- Complete frontend project scaffold with Vite 7, React 19, TypeScript, TailwindCSS v4, and shadcn/ui (20 components)
- TypeScript types matching all backend Pydantic schemas (User, Conversation, Agent, Message, Skill, MCPServer, ToolInfo, envelope/response wrappers)
- API client with Bearer token injection, 401 refresh queue (prevents concurrent refresh race conditions), envelope unwrapping, and proactive 12-minute token refresh timer
- Zustand stores: auth-store (in-memory JWT tokens), ui-store (dark/light theme persisted to localStorage), chat-store (handles all 5 WebSocket event types)
- WebSocket hook with exponential backoff reconnection (1s to 16s, max 5 attempts) and token refresh before reconnect
- Login and register pages with Chinese text, form validation, error handling
- App shell layout: 48px activity bar with 3 navigation icons, 260px context-switching sidebar, flex-1 main content area
- Route protection with token validation on mount

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold, shadcn/ui, dependencies, types, API client, and stores** - `0f707c1` (feat)
2. **Task 2: Auth pages and app shell layout with activity bar** - `3cd444b` (feat)

## Files Created/Modified
- `frontend/package.json` - Dependencies: zustand, @tanstack/react-query, react-router, react-markdown, vitest, testing-library
- `frontend/vite.config.ts` - Vite config with TailwindCSS plugin, path aliases, API/WS proxy
- `frontend/src/types/api.ts` - All entity types matching backend schemas exactly
- `frontend/src/types/ws-events.ts` - WebSocket event types (thinking, tool_call, tool_result, chunk, done)
- `frontend/src/lib/api-client.ts` - Fetch wrapper with auth, 401 refresh queue, envelope unwrapping
- `frontend/src/lib/query-client.ts` - TanStack Query client (30s staleTime, retry 1)
- `frontend/src/stores/auth-store.ts` - Auth state with login/register/logout/refresh actions, in-memory tokens
- `frontend/src/stores/ui-store.ts` - UI state with theme persistence via Zustand persist middleware
- `frontend/src/stores/chat-store.ts` - Chat state with handleWSEvent routing all 5 event types
- `frontend/src/hooks/use-websocket.ts` - WebSocket connection hook with exponential backoff reconnection
- `frontend/src/hooks/use-auth.ts` - Thin auth store wrapper hook
- `frontend/src/components/auth/LoginPage.tsx` - Full-screen login form with Chinese text
- `frontend/src/components/auth/RegisterPage.tsx` - Full-screen register form with Chinese text
- `frontend/src/components/layout/AppShell.tsx` - App layout: activity bar + sidebar + main area
- `frontend/src/components/layout/ActivityBar.tsx` - 48px icon column with 3 navigation items
- `frontend/src/components/layout/Sidebar.tsx` - 260px context-dependent sidebar
- `frontend/src/pages/ProtectedRoute.tsx` - Route guard with token validation
- `frontend/src/main.tsx` - App entry with QueryClientProvider, BrowserRouter, TooltipProvider
- `frontend/src/App.tsx` - Route definitions for all pages
- `frontend/src/index.css` - TailwindCSS v4 imports + shadcn CSS variables (dark/light themes)
- `frontend/vitest.config.ts` - Vitest config with jsdom environment
- `frontend/src/__tests__/setup.ts` - Test setup with localStorage mock
- `frontend/src/__tests__/setup.test.ts` - 10 tests for store initialization and WS event routing

## Decisions Made
- Used callback registration pattern (`registerAuthCallbacks`) in api-client.ts to break circular dependency between api-client and auth-store, avoiding `require()` which is incompatible with `verbatimModuleSyntax`
- Chat store uses dynamic `import()` for ui-store side-panel auto-open to avoid circular dependency at module load time
- Dark theme is default per D-20; shadcn/ui CSS variables handle dark/light swap automatically
- Vite scaffold created a nested `.git` repository -- removed it before committing to keep frontend as part of the main repo

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed embedded .git repository from frontend/ scaffold**
- **Found during:** Task 1 (git staging)
- **Issue:** `npm create vite` created a `.git` directory inside `frontend/`, causing git to treat it as an embedded repository (submodule)
- **Fix:** Removed cached gitlink and deleted `frontend/.git` directory, then re-added files
- **Files modified:** none (git metadata)
- **Verification:** `git add frontend/` stages individual files correctly
- **Committed in:** `0f707c1` (Task 1 commit)

**2. [Rule 3 - Blocking] Replaced require() with callback registration pattern for circular import avoidance**
- **Found during:** Task 1 (TypeScript compilation)
- **Issue:** `verbatimModuleSyntax` in tsconfig prevents `require()` calls; api-client needed auth-store token access but auth-store imports api-client
- **Fix:** Created `registerAuthCallbacks()` function in api-client that auth-store calls during initialization to provide lazy getters
- **Files modified:** `frontend/src/lib/api-client.ts`, `frontend/src/stores/auth-store.ts`
- **Verification:** `npx tsc --noEmit` passes with zero errors
- **Committed in:** `0f707c1` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for correct build and git operations. No scope creep.

## Issues Encountered
- shadcn/ui init requires TailwindCSS CSS file to exist first (`@import "tailwindcss"` in index.css) -- needed to create the CSS import before running `npx shadcn@latest init`
- jsdom test environment lacks localStorage -- added mock in `src/__tests__/setup.ts` for Zustand persist middleware

## Next Phase Readiness
- Plan 02 (Chat UI) can build on chat-store, useWebSocket, AppShell, and all type definitions
- Plan 03 (Management pages) can build on API client, layout, and type definitions
- All stores, hooks, and types are ready for consumption

## Self-Check: PASSED

- All 15 key files verified present on disk
- Commit `0f707c1` found in git log
- Commit `3cd444b` found in git log

---
*Phase: 07-frontend*
*Completed: 2026-03-31*
