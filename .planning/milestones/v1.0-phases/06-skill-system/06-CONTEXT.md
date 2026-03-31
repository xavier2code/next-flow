# Phase 6: Skill System - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can upload Skill packages (ZIP files containing SKILL.md + optional script/ and reference/), manage their lifecycle (upload, validate, enable, disable, hot-update), and execute skill tools in isolated Docker sandboxes with tools registered in the unified Tool Registry. Skills are AI capability packages — not just code, but a combination of knowledge (SKILL.md Agent instructions), executable tools (script/), and reference materials (reference/). Requirements SKIL-01 through SKIL-05.

</domain>

<decisions>
## Implementation Decisions

### Skill Package Format (SKIL-01)
- **D-01:** SKILL.md is the single source of truth, using YAML frontmatter to merge manifest metadata with Agent instructions (Jekyll/Hugo-style). No separate manifest.yaml
- **D-02:** SKILL.md frontmatter fields: name (required, globally unique), version, description, tools (list of {name, description, parameters JSON Schema}), permissions ({network: bool}). Body is Agent-facing instructions in Markdown
- **D-03:** Fixed ZIP structure: SKILL.md (required) + script/ (optional) + reference/ (optional) + requirements.txt (optional for service-type only)
- **D-04:** Tools are fully statically declared in SKILL.md frontmatter — name, description, parameters as JSON Schema. No runtime introspection needed
- **D-05:** Each tool maps to a file in script/ directory — filename matches tool name, contains `async def run(params: dict) -> dict`. One file per tool
- **D-06:** Pure knowledge Skills allowed — no script/ directory, no tool registration. Agent acts on SKILL.md instructions using existing built-in/MCP tools
- **D-07:** Single version per Skill name — re-uploading same-name Skill overwrites the old version. No multi-version coexistence in v1
- **D-08:** Python-only Skills in v1

### Reference Material Handling
- **D-09:** reference/ directory serves dual purpose: Agent-retrievable reference materials AND runtime resources for script/ code
- **D-10:** Size-based split: small files (<N tokens) injected directly into Agent context, large files go through RAG vector retrieval. Threshold at Claude's discretion

### Tool Discovery & Registration (SKIL-05)
- **D-11:** Tools registered to ToolRegistry on Skill enable, unregistered on disable. Follows MCP Manager connect/disconnect pattern
- **D-12:** Namespace format `skill__{skill_name}__{tool_name}` — double underscore separator, consistent with MCP convention. Bulk unregister via `unregister("skill__{name}__")` prefix
- **D-13:** Pure knowledge Skills (no script/) do NOT register any tools in ToolRegistry. Agent interacts via SKILL.md instructions only
- **D-14:** All tools globally shared across all Agents in v1 — consistent with Phase 2 D-14
- **D-15:** Skill names must be globally unique — upload rejects duplicate names

### Agent Context Injection
- **D-16:** When Skills are enabled, a comma-separated summary list (name + brief description) is injected as part of the Agent's SystemMessage. Format: "可用技能：weather-query(天气查询), doc-search(文档搜索)..."
- **D-17:** Full SKILL.md content is loaded on-demand via a built-in `load_skill(name)` tool. Agent calls this tool when it determines a specific Skill is relevant to the user's request. The SKILL.md body is then injected into conversation context
- **D-18:** load_skill is registered as a built-in tool in ToolRegistry (similar to existing built-in tools in builtins.py). Returns the full SKILL.md markdown body

### Skill Type Inference & Execution Model (SKIL-03)
- **D-19:** Platform auto-infers Skill type from structure: (1) no script/ = knowledge type (no container), (2) script/ + tools declared in frontmatter = service type (persistent container), (3) script/ + no tools declared = script type (one-shot execution)
- **D-20:** Service type: enable starts persistent Docker container with sidecar HTTP server. Container stays running until disable. Sidecar listens on single port, routes by path to script/{tool_name}.py's run() function
- **D-21:** Script type: on-demand execution — platform starts container, runs script, captures output, destroys container (docker run --rm). Triggered when Agent invokes via a built-in execution tool
- **D-22:** Knowledge type: no container at all. SKILL.md instructions injected via load_skill tool

### Sandbox Architecture
- **D-23:** HTTP API communication — SkillToolHandler sends HTTP POST to container sidecar. Mature, debuggable, ~10ms overhead
- **D-24:** Unified base image (platform-maintained, includes Python runtime + sidecar process) + volume mount for Skill files (script/, reference/, requirements.txt). No per-Skill image builds
- **D-25:** Base image sidecar: single HTTP port with path-based routing to script/{tool_name}.py. Auto-discovers run() functions. Developer writes pure `async def run(params: dict) -> dict` — no SDK import needed
- **D-26:** Global uniform resource limits via Settings (memory, CPU, timeout). No per-Skill customization in v1
- **D-27:** Health check + auto-restart for service-type containers — periodic /health endpoint check, restart on failure and re-register tools
- **D-28:** Script-type Skills can only use pre-installed libraries from base image — no pip install for one-shot execution. Service-type Skills may use requirements.txt (pip install during container startup)

### Lifecycle Management (SKIL-02, SKIL-04)
- **D-29:** Upload via ZIP (strictly one ZIP = one Skill). Platform validates: (1) SKILL.md exists and frontmatter parses, (2) required fields present (name, version, description), (3) tools JSON Schema valid, (4) script/ files match declared tools one-to-one
- **D-30:** Storage: ZIP stored as-is in MinIO (package_url field). Metadata parsed into Skill DB model. Container mounts extracted files via volume
- **D-31:** Hot-update (re-upload same name): synchronous stop-then-start — disable old (stop container, unregister tools), replace ZIP in MinIO, re-enable with new content. Brief unavailability window is acceptable
- **D-32:** Platform restart recovery: read enabled Skills from DB, pull ZIPs from MinIO, re-extract, re-start containers, re-register tools. Follows MCPManager connect_all pattern
- **D-33:** Extend existing Skill DB model — add fields: version (str), permissions (JSON), package_url (str, MinIO key), skill_type (str, auto-inferred: knowledge/script/service)
- **D-34:** Admin API follows MCP CRUD pattern: POST /skills (upload), GET /skills (list with cursor pagination), GET /skills/{id} (detail), PATCH /skills/{id} (update metadata), DELETE /skills/{id} (delete), POST /skills/{id}/enable, POST /skills/{id}/disable

### Claude's Discretion
- Exact SKILL.md frontmatter schema (additional optional fields beyond name/version/description/tools/permissions)
- Base image contents (which pre-installed libraries to include)
- Resource limit default values (suggest: memory=256MB, CPU=1 core, timeout=30s)
- Health check interval for service-type containers (suggest: 30s)
- Size threshold for reference file direct-inject vs RAG (suggest: 500 tokens)
- Sidecar HTTP server implementation details
- Exact load_skill tool response format
- Error handling and fallback behavior when sandbox is unavailable
- SkillToolHandler Protocol implementation details (similar to MCPToolHandler)
- Logging detail level for skill operations

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Skill Manager component, Sandbox Executor component, Skill loading flow, Pattern 5 (Unified Tool Registry with Strategy Routing)
- `.planning/research/STACK.md` — MinIO 7.x, Docker 7.x SDK, Celery 5.6.x entries
- `.planning/research/PITFALLS.md` — Pitfall 9 (Skill Sandbox Escapes), Pitfall 19 (MinIO Presigned URL Expiration), Integration Gotchas (async skill download), Security Mistakes (import restrictions)
- `.planning/PROJECT.md` — Skill system plugin architecture decision, MinIO for skill packages, key decisions table
- `.planning/REQUIREMENTS.md` — SKIL-01 through SKIL-05 acceptance criteria

### Phase Dependencies (MUST read)
- `.planning/phases/02-agent-engine-core/02-CONTEXT.md` — Tool Registry design (D-11 to D-14), ToolHandler Protocol, execute_node graceful degradation (D-05), global tool sharing (D-14)
- `.planning/phases/05-mcp-integration/05-CONTEXT.md` — MCP CRUD pattern, MCPManager lifecycle, MCPToolHandler, namespace convention, unregister(prefix) pattern — Skill System replicates this structure

### Existing Code (built in prior phases)
- `backend/app/services/tool_registry/registry.py` — ToolRegistry with register/invoke/unregister. SkillToolHandler implements ToolHandler Protocol
- `backend/app/services/tool_registry/handlers.py` — ToolHandler Protocol (async invoke(params) -> Any) and ToolEntry container
- `backend/app/services/tool_registry/builtins.py` — Built-in tool registration pattern (reference for load_skill tool)
- `backend/app/models/skill.py` — Existing Skill model (stub: id, name, description, manifest, status). MUST extend with version, permissions, package_url, skill_type
- `backend/app/models/tool.py` — Tool model with source_type discriminator ("skill" value ready to use)
- `backend/app/services/mcp/manager.py` — MCPManager lifecycle pattern — SkillManager follows same structure
- `backend/app/services/mcp/handler.py` — MCPToolHandler pattern — SkillToolHandler follows same duck-typing approach
- `backend/app/services/mcp_server_service.py` — MCPServerService CRUD pattern — SkillService follows same structure
- `backend/app/api/v1/mcp_servers.py` — MCP REST route pattern — Skills routes follow same structure
- `backend/app/schemas/mcp_server.py` — Pydantic schema pattern (Create/Update/Response) — Skill schemas follow same pattern
- `backend/app/api/deps.py` — get_tool_registry, get_current_user dependencies
- `backend/app/api/v1/router.py` — APIRouter with prefix, include new skills router
- `backend/app/main.py` — Lifespan initialization pattern (Redis, checkpointer, store, memory_service, MCPManager)
- `backend/app/core/config.py` — Settings class, MUST extend with MinIO and skill sandbox config
- `docker-compose.yml` — Currently only postgres + redis, MUST add MinIO

### STATE.md Concern
- STATE.md flags "Docker sandbox security configurations need deeper investigation (affects Phase 6)" — research phase MUST validate Docker isolation settings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ToolRegistry`: In-memory dict with register/invoke/unregister. Needs unregister(prefix) — already implemented for MCP. SkillManager uses same bulk-unregister pattern
- `ToolHandler` Protocol: async invoke(params) -> Any. SkillToolHandler implements this with HTTP call to sandbox container
- `Skill` model: SQLAlchemy stub with id, name, description, manifest, status. Extend with version, permissions, package_url, skill_type
- `Tool` model: source_type="skill" discriminator ready, source_id can reference Skill.id
- `MCPServerService`: Static CRUD methods pattern with cursor pagination — replicate for SkillService
- `mcp_servers.py` routes: Full REST route pattern with EnvelopeResponse/PaginatedResponse — replicate for skills
- `MCPManager`: Lifecycle management with connect_all/disconnect_all — replicate as SkillManager with enable_all/disable_all
- `MCPToolHandler`: Duck-typed ToolHandler with timeout and classified errors — replicate as SkillToolHandler
- `main.py` lifespan: Proven async resource initialization pattern — add SkillManager + MinIO client
- `deps.py`: DI pattern for managers via request.app.state

### Established Patterns
- Layered structure: `api/` (routes) → `services/` (business logic) → `core/` (config)
- Service pattern: `services/{domain}/` with __init__.py exports
- Manager pattern: init in lifespan, store on app.state, expose via deps.py
- Handler pattern: duck-type ToolHandler Protocol, classified errors
- Envelope response: `{data: {...}, meta: {cursor, has_more}}`
- Namespace convention: `{source}__{entity}__{tool}` with prefix-based unregister
- UUID primary keys for all entities
- `nextflow:{domain}:{key}` Redis key convention

### Integration Points
- `backend/app/services/` — New `skill/` service module for SkillManager, SkillToolHandler
- `backend/app/services/skill_service.py` — SkillService CRUD (follows mcp_server_service.py pattern)
- `backend/app/services/tool_registry/builtins.py` — Add load_skill built-in tool
- `backend/app/services/agent_engine/nodes/analyze.py` — Inject Skill summary list into Agent SystemMessage
- `backend/app/models/skill.py` — Extend Skill model with new fields
- `backend/app/main.py` — Initialize MinIO client + SkillManager in lifespan
- `backend/app/api/v1/router.py` — Include new skills router
- `backend/app/api/v1/` — New `skills.py` route file
- `backend/app/schemas/` — New schemas for skill request/response
- `backend/app/core/config.py` — Add MinIO settings + skill sandbox settings
- `docker-compose.yml` — Add MinIO service

</code_context>

<specifics>
## Specific Ideas

- SKILL.md is inspired by Jekyll/Hugo frontmatter — structured metadata at top, free-form Agent instructions below. Developers don't need to learn a new format
- Three skill types auto-inferred from structure, not declared. Developer just puts files in the right directories
- Sidecar in base image auto-discovers run() functions — zero-boilerplate for skill developers. Write `async def run(params: dict) -> dict`, done
- load_skill as built-in tool enables "summary list → on-demand detail" two-step context loading, saving context window for multi-skill scenarios
- SkillManager lifecycle mirrors MCPManager exactly — consistent lifespan pattern, consistent CRUD pattern, consistent handler pattern
- reference/ dual-use is pragmatic: small docs help Agent directly (injected), large docs help via RAG (vector search), and script/ code can read reference files at runtime

</specifics>

<deferred>
## Deferred Ideas

- Per-agent skill binding — v2, after RBAC is implemented
- Multi-version skill coexistence — v2, when marketplace (MKT-01) is built
- Skill marketplace with review system — v2 MKT-01
- Custom per-skill resource limits — v2
- SDK pip package for enhanced developer experience — evaluate if sidecar proves limiting
- Celery integration for async skill packaging/unpackaging — if synchronous processing becomes a bottleneck
- Git repository import for skills — future enhancement
- Online skill editor — future enhancement

</deferred>

---
*Phase: 06-skill-system*
*Context gathered: 2026-03-30*
