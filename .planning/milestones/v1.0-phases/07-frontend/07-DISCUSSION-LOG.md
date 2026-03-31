# Phase 7: Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 07-frontend
**Areas discussed:** Layout & Navigation, Chat UX & Streaming, Management Pages Style, Theme & i18n, Auth UI

---

## Layout & Navigation

### App Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar + Chat main area | Left sidebar for navigation/history, right main area for content. ChatGPT/Claude-style. | ✓ |
| Top Nav + multi-page views | Top navigation bar with tabs switching to independent page views. Dashboard-style. | |
| Full-screen chat + floating management | Chat nearly full-screen, management via floating buttons or top menu. Chat-first. | |

**User's choice:** Sidebar + Chat main area
**Notes:** Classic layout familiar to ChatGPT/Claude users, good balance between chat focus and management accessibility.

### Sidebar Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Conversation-only sidebar | Sidebar only shows conversation history. Management via separate pages. | |
| Multi-tab sidebar | Sidebar top has tabs (Conversations/Agent/Skills/MCP) that change sidebar content. | |
| Activity bar navigation | Fixed icon column (VS Code style), clicking changes sidebar content. 3 items: Conversations/Management/Settings. | ✓ |

**User's choice:** Activity bar navigation
**Notes:** VS Code-style activity bar keeps navigation minimal while providing access to all modules.

### Navigation Items

| Option | Description | Selected |
|--------|-------------|----------|
| 5 items: Convo/Agent/Skills/MCP/Settings | Each module as separate navigation item. | |
| 3 items: Convo/Management/Settings | Management contains Agent+Skills+MCP with tab switching. | ✓ |
| 4 items: Convo/Agent/Tools/Settings | Skills+MCP merged as "External Tools". | |

**User's choice:** 3 items: Conversations / Management / Settings
**Notes:** Agent/Skills/MCP combined under "Management" with tab switching keeps activity bar clean.

---

## Chat UX & Streaming

### Message Display Style

| Option | Description | Selected |
|--------|-------------|----------|
| Bubble style | User messages right-aligned, AI left-aligned. WeChat/ChatGPT-style. | ✓ |
| Channel style | All messages left-aligned, avatar/icon distinguishes sender. Slack-style. | |
| Alternating full-width | User and AI messages alternate in full-width blocks. Email reply-style. | |

**User's choice:** Bubble style
**Notes:** Clear visual distinction between user and AI messages.

### Streaming Event Display

| Option | Description | Selected |
|--------|-------------|----------|
| Inline display | thinking/tool events embedded in message stream with collapsible sections and cards. | |
| Side panel display | thinking/tool events shown in side panel next to message stream. Message stream stays clean. | ✓ |

**User's choice:** Side panel display
**Notes:** Keeps message flow readable while still showing agent reasoning and tool invocations.

### Side Panel Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-appear + closeable | Panel opens automatically when events arrive, user can manually close. | ✓ |
| Click to expand | Panel hidden by default, user clicks "View reasoning" button to open. | |

**User's choice:** Auto-appear + closeable
**Notes:** Users see reasoning process in real-time without extra clicks.

### Input Box

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed at bottom of chat area | Does not scroll with messages. Shift+Enter for newline, Enter to send. | ✓ |
| Fixed at page bottom (full-width) | Input box spans full page width at bottom. Claude/ChatGPT latest style. | |

**User's choice:** Fixed at bottom of chat area
**Notes:** Standard chat input pattern with multi-line support.

---

## Management Pages Style

### Information Display

| Option | Description | Selected |
|--------|-------------|----------|
| List + detail panel | Left list, right detail panel with inline editing. DB tool-style. | ✓ |
| Card grid | Items as cards with key info and action buttons. Visually friendly but lower density. | |
| Data table | Traditional table layout with columns. Good for large datasets. | |

**User's choice:** List + detail panel
**Notes:** High information density suitable for configuration management. Consistent across Agent/Skills/MCP.

### Agent Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Dropdown at top of chat area | Select/switch Agent for current conversation via dropdown. Edit config in management page. | ✓ |
| Select at creation, cannot change | Agent fixed per conversation after creation. | |
| Input box side selector | Switch Agent next to input box before each message. | |

**User's choice:** Dropdown at top of chat area
**Notes:** Flexible Agent switching within a conversation.

### Management Tabs

| Option | Description | Selected |
|--------|-------------|----------|
| Tab switching | Top tabs for Agent/Skills/MCP sub-modules within management page. | ✓ |
| Single page sections | All three modules vertically stacked in one scrolling page. | |

**User's choice:** Tab switching
**Notes:** Clean separation of concerns, consistent list+detail panel per tab.

### Skill Upload

| Option | Description | Selected |
|--------|-------------|----------|
| Button-triggered file dialog | "Upload Skill" button opens file picker for ZIP selection. | ✓ |
| Drag & drop + button dual entry | Both drag-and-drop zone and click button for upload. | |

**User's choice:** Button-triggered file dialog
**Notes:** Simple interaction, sufficient for the upload use case.

### MCP Status Display

| Option | Description | Selected |
|--------|-------------|----------|
| Status lights + detail panel | Green/yellow/red indicator per server, detail panel shows full status and tools. | ✓ |
| Simplified display + separate view | Name and text status only, tools visible via separate button. | |

**User's choice:** Status lights + detail panel
**Notes:** Intuitive visual indicators with complete information in detail view.

---

## Theme & Style

### Theme

| Option | Description | Selected |
|--------|-------------|----------|
| Dark primary + light optional | Dark theme default, light theme toggle. shadcn/ui native support. | ✓ |
| Light primary + dark optional | Light theme default, dark as toggle option. | |
| Dark only | Single dark theme, no light support. | |
| Light only | Single light theme, no dark support. | |

**User's choice:** Dark primary + light optional
**Notes:** Developer/AI tool aesthetic, shadcn/ui makes dual-theme straightforward.

### Empty State

| Option | Description | Selected |
|--------|-------------|----------|
| Welcome + example prompts | Welcome message with clickable example prompt buttons. ChatGPT-style. | ✓ |
| Simple guide text | Minimal text and input box, no example prompts. | |

**User's choice:** Welcome + example prompts
**Notes:** Helps new users get started quickly with one-click examples.

---

## Auth UI

### Auth Page Style

| Option | Description | Selected |
|--------|-------------|----------|
| Independent full-screen pages | Login/register as separate route pages with centered card forms on branded background. | ✓ |
| Modal dialog | Login/register as popups over the main app interface. | |

**User's choice:** Independent full-screen pages
**Notes:** Clean separation, branded landing experience.

---

## Internationalization

### UI Language

| Option | Description | Selected |
|--------|-------------|----------|
| Pure Chinese | All UI text in Simplified Chinese. | ✓ |
| Pure English | All UI text in English. | |
| Chinese/English toggle | i18n framework with language switching. | |

**User's choice:** Pure Chinese
**Notes:** Primary user base is Chinese-speaking. Avoids i18n complexity for v1.

---

## Claude's Discretion

- Component decomposition and file structure
- Zustand store slice design
- API client setup (axios vs fetch, interceptors)
- WebSocket reconnection logic
- Sidebar/panel sizes, responsive breakpoints
- Exact shadcn/ui component selection
- Form validation library
- Loading states and skeleton screens
- Toast notification patterns
- Routing and route structure
- Vite proxy configuration

## Deferred Ideas

None — discussion stayed within phase scope
