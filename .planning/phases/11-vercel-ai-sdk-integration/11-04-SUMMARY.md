---
phase: 11-vercel-ai-sdk-integration
plan: 04
subsystem: ui, api
tags: [vercel-ai-sdk, reasoning, sse, usechat, react]

# Dependency graph
requires:
  - phase: 11-vercel-ai-sdk-integration/01
    provides: SSE chat endpoint with Data Stream v2 protocol
  - phase: 11-vercel-ai-sdk-integration/02
    provides: useChat hook integration in ChatView
provides:
  - Backend reasoning-end SSE event emission at all reasoning-to-text and reasoning-to-finish transitions
  - ReasoningEntry collapsible component for SidePanel reasoning display
  - SidePanel reasoning parts extraction from UIMessage.parts
  - Regenerate button wired to reload() in ChatView header
affects: [11-vercel-ai-sdk-integration/05, frontend-chat, backend-sse]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reasoning part lifecycle: reasoning-start -> reasoning-delta* -> reasoning-end"
    - "Collapsible card pattern for reasoning display (Brain icon, streaming/done badge)"

key-files:
  created:
    - frontend/src/components/chat/ReasoningEntry.tsx
  modified:
    - backend/app/api/v1/chat.py
    - frontend/src/components/chat/SidePanel.tsx
    - frontend/src/components/chat/ChatView.tsx

key-decisions:
  - "Reasoning entries render before tool entries in SidePanel (reasoning precedes tool calls in agent flow)"
  - "Reasoning card defaults open when streaming, collapsed when done"
  - "Regenerate button only visible when status is idle and messages exist"

patterns-established:
  - "ReasoningEntry follows same Card + Badge + Collapsible pattern as ToolCallCard/ToolResultCard"

requirements-completed: [SC-05]

# Metrics
duration: 1min
completed: 2026-04-01
---

# Phase 11 Plan 04: Reasoning Display and Regenerate Button Summary

**Backend reasoning-end SSE emission with ReasoningEntry collapsible component and Regenerate button in chat header**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-31T19:13:10Z
- **Completed:** 2026-03-31T19:14:11Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments
- Backend now emits `reasoning-end` SSE event at all 3 transition points (reasoning-to-text in main loop, reasoning-to-text in flush, reasoning-to-finish at stream end)
- SidePanel extracts and renders reasoning parts from `UIMessage.parts` using the new `ReasoningEntry` component
- Regenerate button with RefreshCw icon calls `reload()` in ChatView header when status is idle

## Task Commits

1. **Task 1: Fix backend reasoning-end emission and add Regenerate button + reasoning display** - `5ff2ce4` (feat)

## Files Created/Modified
- `frontend/src/components/chat/ReasoningEntry.tsx` - New collapsible card component with Brain icon, streaming/done badge states
- `backend/app/api/v1/chat.py` - Added reasoning-end emission at 3 transition points in SSE generator
- `frontend/src/components/chat/SidePanel.tsx` - Extract reasoning parts from UIMessage.parts, render before tool entries
- `frontend/src/components/chat/ChatView.tsx` - Added Regenerate button with reload() in header

## Decisions Made
- Reasoning entries render before tool entries in SidePanel since reasoning precedes tool calls in the agent execution flow
- ReasoningEntry card defaults open when streaming for visibility, collapsed when done to save space
- Regenerate button only visible when `status !== 'streaming'` AND `status !== 'submitted'` AND `messages.length > 0`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Worktree was out of sync with main branch (pre-AI-SDK migration version). Resolved by fast-forward merging main into the worktree branch before executing.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Reasoning display pipeline fully functional end-to-end
- Regenerate button wired and functional
- No blockers for plan 05 (stale chat-store tests)

---
*Phase: 11-vercel-ai-sdk-integration*
*Completed: 2026-04-01*
