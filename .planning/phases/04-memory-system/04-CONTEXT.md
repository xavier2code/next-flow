# Phase 4: Memory System - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents retain conversation context across turns via short-term Redis memory and can recall relevant information from long-term semantic memory (LangGraph Store + Qdrant). The Analyze node is enhanced from stub to full context injection, and a memory_service module handles extraction, deduplication, and write-back. Requirements MEM-01 through MEM-04.

</domain>

<decisions>
## Implementation Decisions

### Short-term Memory (Redis)
- **D-01:** Window size by message count — last N messages (not token budget). Simple, predictable, fixed Redis usage
- **D-02:** Hybrid storage — recent K messages stored as raw JSON, older messages replaced by LLM-generated summary
- **D-03:** Redis data structure — Sorted Set for raw messages (score=timestamp) + String key for summary. Key convention: `nextflow:memory:short:{thread_id}`
- **D-04:** Sliding TTL — refresh expiry on each new message write. Inactive conversations auto-expire to free memory
- **D-05:** Async summary compression via `asyncio.create_task` background coroutines (not Celery). Triggered when new message arrives and window exceeds threshold
- **D-06:** Messages list injection into Analyze node — prepend Redis context (summary + recent messages) as messages in the state. No new AgentState fields needed
- **D-07:** Redis is the source of truth for recent context (last N messages). LangGraph checkpointer holds full history for state persistence

### Long-term Memory (LangGraph Store + Qdrant)
- **D-08:** LangGraph Store as primary implementation path. Research phase validates production readiness. If Store is not viable, fallback to direct Qdrant integration via qdrant-client
- **D-09:** User-level namespace partitioning — `namespace=("users", user_id, "memories")`. Each user only searches their own memories
- **D-10:** Compile-time Store injection — `build_graph(store=store)` at graph compilation, consistent with existing checkpointer pattern
- **D-11:** Store initialized in main.py lifespan (alongside checkpointer, Redis, tool_registry). App.state.store for dependency access
- **D-12:** Qdrant deployed as Docker container in docker-compose.yml. LangGraph Store configured with Qdrant backend. Direct qdrant-client available as fallback
- **D-13:** Memory write-back after Respond node — async `asyncio.create_task` fires `memory_service.extract_and_store()` without blocking the response stream

### Memory Extraction & Write-back
- **D-14:** LLM extracts key facts from conversation — structured JSON output guided by system prompt. Not raw messages, not summaries. Only valuable knowledge points are persisted
- **D-15:** LLM-based deduplication — LLM compares new extracted facts against existing store entries. Decides: update/merge/skip. More intelligent than simple cosine similarity threshold
- **D-16:** Analyze node single query — `store.search()` called once before planning. Results injected as SystemMessage context
- **D-17:** Top-K raw results from store.search() — let LLM decide relevance during planning. No secondary filtering
- **D-18:** Unified memory_service module with single `extract_and_store()` interface. Encapsulates: fact extraction, dedup check, Redis update, Store write. Called from one place after Respond
- **D-19:** Long-term memory injected as SystemMessage in Analyze node — format: "Relevant past context: {memories}". Consistent with existing messages pattern
- **D-20:** Synchronized writes to both Redis (short-term, sliding TTL refresh) and Store (long-term, fact extraction) on each conversation turn. Prevents three-tier memory sync drift (PITFALLS.md Pitfall 8)
- **D-21:** memory_service is the single entry point for all memory operations. Nodes call memory_service methods, never access Redis/Store directly

### Embedding Model
- **D-22:** Configurable multi-model — OpenAI text-embedding-3-small as default, Ollama local models as optional alternative
- **D-23:** Factory pattern `get_embedder(config)` — mirrors existing `get_llm()` pattern in llm.py. Returns LangChain Embeddings instance based on provider
- **D-24:** Per-model fixed dimension — each embedding model gets its own Qdrant collection with matching dimension. Switching models requires new collection (document this trade-off)
- **D-25:** Settings-level configuration — `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` in .env via Pydantic Settings. Not per-Agent (global for v1)

### Claude's Discretion
- Exact value of N for message window (suggest 20)
- Exact value of K for raw message threshold before summarization
- Redis TTL duration (suggest 24 hours)
- Top-K value for store.search() (suggest 5)
- LLM prompt templates for fact extraction and dedup comparison
- Qdrant collection schema details (payload fields, index config)
- memory_service internal method decomposition
- Error handling and fallback behavior when Store/Qdrant is unavailable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Architecture
- `.planning/research/ARCHITECTURE.md` — Memory System component, Pattern 4 (Three-Layer Memory with LangGraph Store), memory retrieval/write-back data flows
- `.planning/research/STACK.md` — Qdrant 1.x, langgraph-store, qdrant-client, redis 5.x entries with version rationale
- `.planning/research/PITFALLS.md` — Pitfall 8 (Three-tier memory synchronization drift) — MUST follow write-through policy
- `.planning/PROJECT.md` — Three-layer memory architecture decision, key decisions table
- `.planning/REQUIREMENTS.md` — MEM-01 through MEM-04 acceptance criteria

### Phase Dependencies (MUST read)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — Redis setup, key naming convention, deps.py patterns
- `.planning/phases/02-agent-engine-core/02-CONTEXT.md` — AgentState, graph build pattern, Analyze node stub, checkpointer setup
- `.planning/phases/03-communication-layer/03-CONTEXT.md` — WebSocket streaming, REST message endpoint, connection manager

### Existing Code (built in prior phases)
- `backend/app/services/agent_engine/nodes/analyze.py` — Current stub, MUST be enhanced with memory injection
- `backend/app/services/agent_engine/state.py` — AgentState TypedDict (messages, plan, scratchpad, remaining_steps)
- `backend/app/services/agent_engine/graph.py` — build_graph() with checkpointer param, MUST add store param
- `backend/app/services/agent_engine/checkpointer.py` — create_checkpointer() pattern, follow for Store initialization
- `backend/app/services/agent_engine/llm.py` — get_llm() factory, follow same pattern for get_embedder()
- `backend/app/core/config.py` — Settings class, MUST extend with embedding config
- `backend/app/db/redis.py` — Redis client access, key prefix convention
- `backend/app/main.py` — Lifespan initialization pattern (Redis, checkpointer, tool_registry, connection_manager)
- `docker-compose.yml` — Existing postgres + redis services, MUST add Qdrant

### STATE.md Concern
- STATE.md flags "LangGraph Store production readiness needs validation (affects Phase 4)" — research phase MUST validate this before implementation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `analyze.py`: Stub with Phase 4 comment — natural injection point for both short-term and long-term memory
- `graph.py`: build_graph(checkpointer) pattern — extend with store parameter
- `checkpointer.py`: create_checkpointer() async factory — replicate for Store initialization
- `llm.py`: get_llm(config) factory — replicate pattern for get_embedder(config)
- `config.py`: Settings Pydantic class — extend with embedding_provider, embedding_model fields
- `redis.py`: Redis client from app.state.redis — reuse for short-term memory operations
- `main.py` lifespan: Proven initialization pattern — add Store init alongside checkpointer

### Established Patterns
- Layered structure: `api/` → `services/` → `core/`
- Service pattern: `services/{domain}/` with __init__.py exports
- Factory pattern: `get_llm(config)` returns provider-specific instance
- Lifespan init: async resources created in lifespan, stored on app.state
- Dependency injection: FastAPI Depends + app.state access
- Key naming: `nextflow:{domain}:{key}`
- UUID primary keys for all entities

### Integration Points
- `backend/app/services/agent_engine/nodes/analyze.py` — MUST add memory retrieval logic
- `backend/app/services/agent_engine/nodes/respond.py` — MUST trigger async memory write-back after response
- `backend/app/services/agent_engine/graph.py` — MUST accept and pass store parameter
- `backend/app/main.py` — MUST initialize Store in lifespan
- `backend/app/core/config.py` — MUST add embedding configuration
- `docker-compose.yml` — MUST add Qdrant service
- `backend/app/services/` — New `memory/` service module for memory_service

</code_context>

<specifics>
## Specific Ideas

- Follow LangGraph Store usage from ARCHITECTURE.md Pattern 4 — `store.search(namespace=("users", user_id, "memories"), query=user_message)`
- memory_service is the coordination layer between Analyze (read) and Respond (write) and the two storage backends (Redis + Store)
- Short-term memory uses Redis Sorted Set (fast reads by timestamp range) + String (summary cache) — proven pattern for sliding window
- Long-term memory uses LLM-extracted key facts, not raw messages — keeps Store focused and retrieval-relevant
- Embedding factory mirrors LLM factory — consistent developer experience

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 04-memory-system*
*Context gathered: 2026-03-29*
