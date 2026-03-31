---
phase: 07-frontend
plan: 03
subsystem: ui
tags: [react, management, agents, skills, mcp-servers, settings, tabs, crud]

# Dependency graph
requires:
  - phase: 07-01
    provides: Frontend project scaffold, API client, Zustand stores, TypeScript types
  - phase: 07-02
    provides: useAgents hook pattern, ConversationList, Sidebar structure
provides:
  - React Query hooks: use-skills, use-mcp-servers, use-settings
  - Management page with tab bar (Agent/Skills/MCP servers) and list+detail split panels
  - Agent CRUD with name, model, system prompt, temperature configuration
  - Skill upload (.zip), enable/disable toggle, tool discovery
  - MCP server registration, status monitoring (StatusDot), tool listing
  - Settings page with dark mode toggle, account info, logout
  - Updated Sidebar with management navigation and settings content
  - Updated App.tsx routes for all management and settings pages
affects: [07-04-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [management-tab-layout, list-detail-split, status-dot-indicator, skill-upload-multipart, mcp-polling-30s, theme-toggle-light-class]

key-files:
  created:
    - frontend/src/hooks/use-skills.ts
    - frontend/src/hooks/use-mcp-servers.ts
    - frontend/src/hooks/use-settings.ts
    - frontend/src/components/management/ManagementPage.tsx
    - frontend/src/components/management/AgentList.tsx
    - frontend/src/components/management/AgentDetail.tsx
    - frontend/src/components/management/SkillList.tsx
    - frontend/src/components/management/SkillDetail.tsx
    - frontend/src/components/management/MCPServerList.tsx
    - frontend/src/components/management/MCPServerDetail.tsx
    - frontend/src/components/management/StatusDot.tsx
    - frontend/src/components/settings/SettingsPage.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/components/layout/Sidebar.tsx
    - frontend/src/components/layout/AppShell.tsx
    - frontend/src/hooks/use-agents.ts

## Self-Check: PASSED

# Execution Log

## Task 1: React Query hooks + Management page with tabs

Created all hooks and management components:
- `use-skills.ts`: useSkills, useSkill, useUploadSkill (FormData), useToggleSkill, useDeleteSkill, useSkillTools
- `use-mcp-servers.ts`: useMCPServers (30s polling), useMCPServer, useCreateMCPServer, useUpdateMCPServer, useDeleteMCPServer, useMCPServerTools
- `use-settings.ts`: useUserSettings, useUpdateSettings, useSystemConfig
- `ManagementPage.tsx`: Tabs layout with "智能体", "技能", "MCP 服务器" tabs
- `AgentList/AgentDetail`: Agent CRUD with delete confirmation dialog
- `SkillList/SkillDetail`: Upload .zip, enable/disable Switch with confirmation
- `MCPServerList/MCPServerDetail`: StatusDot, registration form, discovered tools
- `StatusDot.tsx`: Green/yellow/red/gray status indicator

Commit: 87d91d9 feat(07-03): add management hooks, components, and tabs for agents/skills/MCP

## Task 2: Settings page, sidebar management nav, route wiring

- `SettingsPage.tsx`: "外观" with dark mode Switch, "账户" with email/name, "关于", "退出登录" button
- `Sidebar.tsx`: Added ManageSidebar with navigation items, SettingsSidebar with label
- `AppShell.tsx`: Route-based activeNav sync via useEffect
- `App.tsx`: Routes wired to ManagementPage and SettingsPage
- Theme toggle: adds/removes 'light' class on html element

Commit: d31082a feat(07-03): add settings page, sidebar management nav, and route wiring

## Merge Resolution

Merged with 07-02 chat UI branch. Resolved conflicts in:
- App.tsx: Combined ChatPage routes (07-02) + ManagementPage/SettingsPage routes (07-03)
- Sidebar.tsx: Combined imports from both branches
- use-agents.ts: Used 07-02's typed version with PaginatedResponse

Commit: 0d7f2ed merge(07): resolve conflicts between chat UI (07-02) and management pages (07-03)

# Deviations

None. All components match UI-SPEC and CONTEXT spec.

# Decisions

- MCP server list uses refetchInterval: 30000 for status polling
- Skill upload uses FormData with browser auto-boundary (no manual Content-Type)
- StatusDot maps: connected=green, connecting=yellow, disconnected=red, unknown/empty=gray
- Theme toggle uses shadcn class strategy (add/remove 'light' class on html element)
