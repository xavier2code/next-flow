---
phase: 06-skill-system
plan: 02
subsystem: runtime
tags: [docker, sandbox, skill, handler, manager, httpx, tool-registry, health-check]

# Dependency graph
requires:
  - phase: 06-skill-system
    provides: "SkillStorage, parse_skill_manifest, Skill model, classified errors, Settings"
provides:
  - "SkillSandbox: Docker container lifecycle with security hardening for service/script types"
  - "SkillToolHandler: HTTP POST invocation to sandbox sidecar with classified errors"
  - "SkillManager: enable/disable lifecycle with tool registration, SKILL.md body parsing, health checks"
  - "ContainerInfo dataclass for container metadata"
affects: [06-skill-system, 07-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker sandbox security hardening: cap_drop ALL, no-new-privileges, read-only fs, non-root user"
    - "SkillToolHandler duck-types ToolHandler Protocol via HTTP (mirrors MCPToolHandler)"
    - "Namespace format skill__{name}__{tool} with prefix-based unregister (mirrors MCP convention)"
    - "SkillManager lifecycle mirrors MCPManager: enable_all/disable_all/health_check pattern"
    - "_skill_content dict for SKILL.md body storage (populated by _enable_one)"
    - "_skill_descriptions dict for skill summaries (per D-16)"

key-files:
  created:
    - backend/app/services/skill/sandbox.py
    - backend/app/services/skill/handler.py
    - backend/app/services/skill/manager.py
    - backend/tests/unit/test_skill_sandbox.py
    - backend/tests/unit/test_skill_handler.py
    - backend/tests/unit/test_skill_manager.py
  modified:
    - backend/app/services/skill/__init__.py

key-decisions:
  - "SkillSandbox uses docker.from_env() directly (injected in tests via mock)"
  - "SkillToolHandler wraps httpx.AsyncClient with classified error mapping mirroring MCPToolHandler"
  - "SkillManager constructor accepts skill_content dict for DI (shared with load_skill tool)"
  - "get_enabled_skill_summaries deduplicates by skill name (multiple tools per skill)"

patterns-established:
  - "HTTP POST to sandbox sidecar for tool invocation (mirrors MCP HTTP transport)"
  - "Background asyncio.Task for health check loop with graceful cancellation"
  - "ZIP extraction from MinIO bytes with SKILL.md body parsing at enable time"

requirements-completed: [SKIL-03, SKIL-05]

# Metrics
duration: 17min
completed: 2026-03-30
---

# Phase 6 Plan 02: Skill Runtime Summary

**Docker sandbox executor with security hardening, SkillToolHandler HTTP invocation, and SkillManager lifecycle with tool registration and health checks**

## Performance

- **Duration:** 17 min
- **Started:** 2026-03-30T05:50:59Z
- **Completed:** 2026-03-30T06:08:48Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- SkillSandbox manages Docker containers with full security hardening: cap_drop ALL, no-new-privileges, read-only filesystem, non-root user, resource limits (per D-20, D-23 to D-28)
- SkillSandbox supports both service-type (persistent container) and script-type (one-shot execution with output capture) per D-21
- SkillToolHandler routes HTTP POST invocations to sandbox sidecar with classified errors (timeout, connection, execution) mirroring MCPToolHandler pattern per D-23
- SkillManager enables/disables skills with tool registration in ToolRegistry using namespace format skill__{name}__{tool} per D-11, D-12
- SkillManager parses SKILL.md body and stores in _skill_content dict for load_skill tool, and stores descriptions for summaries per D-16
- Health check loop monitors service-type containers with auto-restart on failure per D-27
- 33 new unit tests all passing (142 total unit tests green)

## Task Commits

Each task was committed atomically with TDD (RED then GREEN):

1. **Task 1: Docker sandbox executor and SkillToolHandler** - `c8d6e64` (test) + `64cb7f3` (feat)
2. **Task 2: SkillManager lifecycle with tool registration and health checks** - `771f047` (test) + `cc3c2aa` (feat)

## Files Created/Modified
- `backend/app/services/skill/sandbox.py` - Docker container lifecycle (service/script types, stale cleanup)
- `backend/app/services/skill/handler.py` - SkillToolHandler with HTTP POST and classified errors
- `backend/app/services/skill/manager.py` - SkillManager lifecycle, tool registration, health checks, SKILL.md parsing
- `backend/app/services/skill/__init__.py` - Updated re-exports with SkillSandbox, SkillToolHandler, SkillManager
- `backend/tests/unit/test_skill_sandbox.py` - 10 sandbox tests
- `backend/tests/unit/test_skill_handler.py` - 6 handler tests
- `backend/tests/unit/test_skill_manager.py` - 17 manager tests

## Decisions Made
- SkillSandbox uses `docker.from_env()` directly at construction; tests mock the docker module via patch
- SkillToolHandler wraps all non-classified exceptions in SkillToolExecutionError for uniform error handling
- SkillManager constructor accepts `skill_content` dict as a shared mutable reference -- the load_skill built-in tool (Plan 03) will read from this same dict
- Health check uses httpx.AsyncClient with 5s timeout and GET /health endpoint; any exception triggers restart

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing DB-dependent test failures in tests/test_agents.py (requires running PostgreSQL) -- out of scope, unit tests all pass

## User Setup Required
None - no external service configuration required. Docker must be available for sandbox execution at runtime.

## Next Phase Readiness
- Skill runtime fully in place: sandbox, handler, manager
- Ready for Plan 06-03: SkillService CRUD, REST API endpoints, main.py lifespan wiring, load_skill built-in tool, Agent context injection

---
*Phase: 06-skill-system*
*Completed: 2026-03-30*

## Self-Check: PASSED

All 8 files verified present. All 4 task commits (c8d6e64, 64cb7f3, 771f047, cc3c2aa) confirmed in git log.
