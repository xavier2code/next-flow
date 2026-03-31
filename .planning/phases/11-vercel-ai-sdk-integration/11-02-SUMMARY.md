---
phase: 11-vercel-ai-sdk-integration
plan: 02
subsystem: ui
tags: [react, vercel-ai-sdk, usechat, sse, typescript, zustand]

# Dependency graph
requires:
  - phase: 11-01
    provides: "SSE streaming endpoint at POST /api/v1/conversations/{id}/chat with Data Stream Protocol v2"
provides:
  - "Frontend chat powered by useChat hook from @ai-sdk/react"
  - "Eliminated WebSocket dependency from frontend (no more useWebSocket, ws-events, ConnectionStatus)"
  - "Simplified chat-store to conversation tracking only (removed ~180 lines of streaming state)"
  - "ChatMessage component rendering UIMessage from useChat"
  - "SidePanel reading toolInvocations from useChat messages"
affects: [frontend-chat, frontend-auth, frontend-layout]

# Tech tracking
tech-stack:
  added: ["@ai-sdk/react", "ai"]
  patterns: ["useChat hook for chat interaction", "fetch override for auth token injection", "UIMessage rendering pattern"]

key-files:
  created:
    - frontend/src/components/chat/ChatMessage.tsx
  modified:
    - frontend/src/components/chat/ChatView.tsx
    - frontend/src/components/chat/SidePanel.tsx
    - frontend/src/components/layout/AppShell.tsx
    - frontend/src/pages/ChatPage.tsx
    - frontend/src/stores/chat-store.ts
    - frontend/src/stores/ui-store.ts
    - frontend/src/types/api.ts
    - frontend/package.json
  deleted:
    - frontend/src/hooks/use-websocket.ts
    - frontend/src/types/ws-events.ts
    - frontend/src/components/chat/StreamingText.tsx
    - frontend/src/components/chat/ConnectionStatus.tsx
    - frontend/src/components/chat/MessageBubble.tsx
    - frontend/src/components/chat/ThinkingEntry.tsx

key-decisions:
  - "useChat fetch override for auth token injection (localStorage access for fresh token on each request)"
  - "SidePanel uses timestamp=Date.now() for tool invocations since useChat toolInvocations lack timestamp"
  - "ThinkingEntry display removed from SidePanel (useChat does not surface reasoning parts in UIMessage)"

patterns-established:
  - "useChat hook as sole chat interaction mechanism (send, stream, abort, regenerate)"
  - "No WebSocket code in frontend -- SSE-only streaming via useChat"
  - "chat-store reduced to minimal conversation tracking state"

requirements-completed: [SC-02, SC-05, SC-06]

# Metrics
duration: 3min
completed: 2026-03-31
---

# Phase 11 Plan 02: useChat Frontend Integration Summary

**Replaced custom WebSocket/Zustand streaming with Vercel AI SDK useChat hook, eliminating ~500 lines of custom state management and WebSocket infrastructure from the frontend**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-31T15:33:58Z
- **Completed:** 2026-03-31T15:36:41Z
- **Tasks:** 2 (plus 1 auto-approved checkpoint)
- **Files modified:** 13 (8 modified, 1 created, 6 deleted)

## Accomplishments
- ChatView rewritten to use `useChat` from `@ai-sdk/react` for all chat interactions (send, stream, abort)
- Eliminated entire WebSocket infrastructure from frontend (hook, types, connection status indicator)
- Simplified chat-store from ~180 lines of streaming state to ~15 lines of conversation tracking
- SidePanel now reads `toolInvocations` directly from useChat's `UIMessage` objects
- TypeScript compiles cleanly with zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Install @ai-sdk/react and ai packages** - `e7723e9` (chore)
2. **Task 2: Rewrite ChatView to useChat, remove WebSocket code, update all consumers** - `cba1db2` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `frontend/src/components/chat/ChatMessage.tsx` - New UIMessage renderer replacing MessageBubble
- `frontend/src/components/chat/ChatView.tsx` - Rewritten with useChat hook for chat interaction
- `frontend/src/components/chat/SidePanel.tsx` - Reads toolInvocations from useChat messages
- `frontend/src/components/layout/AppShell.tsx` - Removed WebSocket connection management
- `frontend/src/pages/ChatPage.tsx` - Simplified (removed connectionStatus prop)
- `frontend/src/stores/chat-store.ts` - Stripped to currentConversationId tracking only
- `frontend/src/stores/ui-store.ts` - Removed connectionStatus field and setter
- `frontend/src/types/api.ts` - Removed unused chat state types
- `frontend/package.json` - Added @ai-sdk/react and ai dependencies

Deleted files:
- `frontend/src/hooks/use-websocket.ts` - WebSocket hook with reconnect logic
- `frontend/src/types/ws-events.ts` - WebSocket event type definitions
- `frontend/src/components/chat/StreamingText.tsx` - Custom streaming text renderer
- `frontend/src/components/chat/ConnectionStatus.tsx` - WebSocket connection indicator
- `frontend/src/components/chat/MessageBubble.tsx` - Old Message type renderer
- `frontend/src/components/chat/ThinkingEntry.tsx` - Thinking display component

## Decisions Made
- **useChat fetch override for auth:** Used `fetch` option on useChat to inject `Authorization` header from localStorage on each request, since useChat's `headers` option is not reactive to token changes
- **SidePanel timestamp workaround:** useChat's `toolInvocations` don't include timestamps, so `Date.now()` is used as placeholder for ToolCallCard/ToolResultCard timestamp props
- **ThinkingEntry removal:** useChat does not currently surface reasoning/thinking content in the UIMessage interface. Thinking display was removed from SidePanel. Can be re-added when useChat supports reasoning parts natively

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all changes compiled cleanly on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Frontend is fully wired to SSE streaming via useChat -- no further chat plumbing needed
- Plan 11-03 can proceed with any remaining integration work
- Note: Thinking/reasoning display will need re-implementation when useChat supports reasoning parts

---
*Phase: 11-vercel-ai-sdk-integration*
*Completed: 2026-03-31*
