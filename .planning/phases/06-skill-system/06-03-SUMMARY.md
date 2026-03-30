---
plan: "06-03"
phase: "06-skill-system"
status: complete
started: "2026-03-30T05:40:00Z"
completed: "2026-03-30T07:00:00Z"
---

# Plan 06-03: Full-Stack Skill Integration

## Objective

Wire everything together: build the SkillService CRUD layer, Pydantic schemas, REST API endpoints (with hot-update on duplicate name), main.py lifespan integration, load_skill and run_skill_script built-in tools, and Agent context injection with name + description summaries.

## Self-Check: PASSED

- [x] SkillService CRUD with cursor pagination (mirrors MCPServerService)
- [x] Pydantic schemas (SkillResponse, SkillUpdate, SkillToolResponse)
- [x] REST API endpoints: upload, list, detail, update, delete, enable, disable, list-tools
- [x] Hot-update on duplicate name: disable old, replace ZIP, re-enable if was enabled
- [x] SkillManager initialized in lifespan with enable_all/disable_all
- [x] load_skill built-in tool returns SKILL.md content
- [x] run_skill_script built-in tool executes script-type skills on demand
- [x] Skill tools registered with skill__ namespace in ToolRegistry
- [x] Agent SystemMessage includes enabled skill summary with name + description
- [x] get_skill_manager dependency added to deps.py
- [x] Skills router registered in v1 router

## Key Files

### created
- `backend/app/schemas/skill.py` -- Pydantic schemas for skill CRUD
- `backend/app/services/skill_service.py` -- SkillService CRUD layer
- `backend/app/api/v1/skills.py` -- REST endpoints for skill management
- `backend/tests/unit/test_skill_crud.py` -- CRUD unit tests (10 tests)
- `backend/tests/unit/test_skill_builtins.py` -- Built-in tools tests (8 tests)
- `backend/tests/unit/test_skill_registry.py` -- Registry prefix tests (5 tests)

### modified
- `backend/app/api/deps.py` -- Added get_skill_manager + get_mcp_manager dependencies
- `backend/app/api/v1/router.py` -- Registered skills + mcp_servers routers
- `backend/app/main.py` -- SkillManager lifespan wiring
- `backend/app/services/tool_registry/builtins.py` -- load_skill + run_skill_script tools
- `backend/app/services/tool_registry/registry.py` -- Prefix-based unregister doc
- `backend/app/services/skill/manager.py` -- Added run_script_skill method
- `backend/app/services/agent_engine/nodes/analyze.py` -- Skill summary injection

## Decisions

- [D-07]: Hot-update on duplicate name overwrites automatically (no 409 conflict)
- [D-16]: Skill summaries include both name AND description in Agent SystemMessage
- [D-17/D-18]: load_skill returns full SKILL.md markdown body
- [D-21]: run_skill_script starts one-shot container for script-type skills
- [D-31]: Hot-update is synchronous: stop old → replace → start new
- [D-32]: SkillManager enable_all on startup, disable_all on shutdown
- Module-level setter pattern for skill_manager (same as memory_service in analyze.py)

## Deviations

None.
