# Phase 2: Agent Engine Core - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

LangGraph StateGraph workflow engine with 4-node linear topology (Analyze → Plan → Execute → Respond), LLM integration via LangChain with multi-provider support (OpenAI + Ollama), Tool Registry with unified registration interface, and conversation state persistence via PostgresSaver. Requirements AGNT-01 through AGNT-06.

</domain>

<decisions>
## Implementation Decisions

### Workflow Topology
- **D-01:** 4-node linear pipeline: Analyze → Plan → Execute → Respond (no Reflect node in v1)
- **D-02:** Single responsibility per node — Analyze analyzes intent + injects context, Plan decides tool calls via LLM, Execute runs tools, Respond generates final answer
- **D-03:** Sequential tool execution in Execute node — one tool at a time, parallel execution deferred to v2 (ADVN-01, Send API)
- **D-04:** Conditional edge from Plan node — if no tools needed, skip Execute and go directly to Respond
- **D-05:** Graceful degradation on errors — tool failures return error as ToolMessage, LLM explains failure in Respond; no exceptions thrown to caller

### LLM Provider Strategy
- **D-06:** Model configuration stored in Agent.model_config JSON field — provider, model name, temperature, max_tokens, etc.
- **D-07:** Simple factory function `get_llm(config)` to create LangChain ChatModel instances based on provider string (e.g., "openai" → ChatOpenAI, "ollama" → ChatOllama)
- **D-08:** API keys and connection URLs configured via environment variables (OPENAI_API_KEY, OLLAMA_BASE_URL, etc.) in Settings — no database storage of credentials in v1
- **D-09:** Configurable default provider and model via Settings (DEFAULT_PROVIDER, DEFAULT_MODEL) — not hardcoded
- **D-10:** LLM instances created with streaming=True by default — Phase 2 sets up streaming primitives, Phase 3 maps to WebSocket events

### Tool Registry
- **D-11:** In-memory registry (Python dict) with Protocol-based handler pattern — register() adds name/schema/handler, invoke() routes to correct handler
- **D-12:** Minimal built-in tools — one simple tool (e.g., get_current_time or echo) to validate the full registration → routing → invocation chain
- **D-13:** Decorator-based registration (`@tool_registry.register`) for built-in tools — similar to FastAPI route decorators
- **D-14:** All tools globally shared across all Agents in v1 — no per-agent tool filtering (deferred to later phases)

### AgentState Structure
- **D-15:** TypedDict-based state with fields: messages (Annotated[list, add_messages]), plan (str), scratchpad (str), remaining_steps (int, managed value for recursion limit)
- **D-16:** plan and scratchpad both typed as str — plan stores current step description, scratchpad stores intermediate reasoning/context
- **D-17:** user_id and thread_id passed via LangGraph config["configurable"], not stored in AgentState — state contains only business data

### Claude's Discretion
- Exact node function implementations and prompt templates
- PostgresSaver connection setup and migration details
- Tool Registry internal data structure details
- Error message formatting in graceful degradation
- Alembic migration for any new checkpoint tables

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flows, LangGraph patterns (Patterns 1, 5 are directly relevant)
- `.planning/research/STACK.md` — LangGraph 1.1.x, LangChain core versions
- `.planning/research/PITFALLS.md` — Known pitfalls for agent engine implementation
- `.planning/PROJECT.md` — Core value, tech stack constraints, key decisions
- `.planning/REQUIREMENTS.md` — AGNT-01 through AGNT-06 acceptance criteria

### Phase 1 Context (dependencies)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — Project structure, database schema, Redis setup, auth patterns

### Existing Code (built in Phase 1)
- `backend/app/models/agent.py` — Agent model with model_config JSON field
- `backend/app/models/tool.py` — Tool model with source_type, source_id, schema fields
- `backend/app/core/config.py` — Settings with database_url, redis_url (needs LLM settings)
- `backend/app/api/deps.py` — get_current_user, get_db, get_redis dependency injection
- `backend/app/main.py` — FastAPI app lifespan with Redis initialization

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Agent.model_config` (JSON field): Ready to store per-agent LLM configuration (provider, model, temperature, etc.)
- `Tool` model (source_type, source_id, schema): Defines tool metadata structure, consistent with registry's tool entries
- `Settings` (Pydantic Settings): Can be extended with LLM provider config (API keys, base URLs, defaults)
- `deps.py` pattern: Dependency injection via FastAPI Depends — same pattern for Tool Registry singleton
- Redis async client: Already initialized in app lifespan, available for future memory caching

### Established Patterns
- Layered structure: `api/` (routes) → `services/` (business logic) → `core/` (config, security)
- Pydantic Settings with `.env` file for configuration
- UUID primary keys for all entities
- `nextflow:{domain}:{key}` Redis key naming convention
- Structured logging with structlog

### Integration Points
- `backend/app/core/config.py` — Needs LLM provider settings (API keys, base URLs, defaults)
- `backend/app/services/` — New `agent_engine/` service for LangGraph workflow
- `backend/app/main.py` — Tool Registry initialization in lifespan (like Redis)
- `backend/app/db/session.py` — PostgresSaver will use same database URL
- `backend/app/api/` — Future Phase 3 REST/WebSocket endpoints will invoke the agent engine

</code_context>

<specifics>
## Specific Ideas

- Follow LangGraph StateGraph pattern from ARCHITECTURE.md Pattern 1 (Agent Orchestration)
- Follow Tool Registry pattern from ARCHITECTURE.md Pattern 5 (Unified Tool Registry with Strategy Routing)
- Agent workflow: START → Analyze → Plan → [conditional] → Execute → Respond → END
- Each node is a pure function `(State) -> Partial[State]`
- STATE.md flags `astream_events` v2 event shapes need prototyping — test during implementation

</specifics>

<deferred>
## Deferred Ideas

- Reflect node with evaluator-optimizer loop — v2 ADVN-02 (Command goto pattern)
- Parallel tool execution via Send API — v2 ADVN-01
- Multi-LLM routing and fallback chains — v2 ADVN-03
- Human-in-the-loop interrupts — v2 ADVN-04
- Per-agent tool filtering — future phase
- Rich built-in tool library (web search, code execution, etc.) — future phases
- Database-backed tool registration — evaluate if needed for persistence across restarts

</deferred>

---
*Phase: 02-agent-engine-core*
*Context gathered: 2026-03-29*
