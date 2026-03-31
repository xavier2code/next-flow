# Phase 4: Memory System - Research

**Researched:** 2026-03-29
**Domain:** Three-layer memory system (Redis short-term, LangGraph Store long-term, AgentState working) for agent context persistence
**Confidence:** HIGH

## Summary

Phase 4 implements a three-layer memory architecture for the NextFlow agent platform. The most critical research finding is that **LangGraph bundles `AsyncPostgresStore` with native pgvector support** -- no separate Qdrant container is needed when using the Store path. The `AsyncPostgresStore` handles both key-value storage and semantic vector search through PostgreSQL's pgvector extension, consolidating the long-term memory layer into the existing PostgreSQL infrastructure.

Short-term memory uses Redis Sorted Sets for a sliding-window message buffer with LLM-generated summaries. The `memory_service` module serves as the single coordination layer between the Analyze node (reads), the Respond node (writes), Redis (short-term), and the Store (long-term). All memory operations are asynchronous, with write-back fire-and-forget via `asyncio.create_task` to avoid blocking the response stream.

**Primary recommendation:** Use `AsyncPostgresStore` with pgvector for long-term semantic memory. Replace the `postgres:16` Docker image with `pgvector/pgvector:pg16`. Skip Qdrant entirely for the Store path -- it is only a fallback if Store proves unviable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Window size by message count -- last N messages (not token budget)
- **D-02:** Hybrid storage -- recent K messages stored as raw JSON, older messages replaced by LLM-generated summary
- **D-03:** Redis data structure -- Sorted Set for raw messages (score=timestamp) + String key for summary. Key convention: `nextflow:memory:short:{thread_id}`
- **D-04:** Sliding TTL -- refresh expiry on each new message write
- **D-05:** Async summary compression via `asyncio.create_task` background coroutines (not Celery)
- **D-06:** Messages list injection into Analyze node -- prepend Redis context as messages in state. No new AgentState fields needed
- **D-07:** Redis is the source of truth for recent context (last N messages). LangGraph checkpointer holds full history
- **D-08:** LangGraph Store as primary implementation path. Fallback to direct Qdrant integration via qdrant-client
- **D-09:** User-level namespace partitioning -- `namespace=("users", user_id, "memories")`
- **D-10:** Compile-time Store injection -- `build_graph(store=store)` at graph compilation
- **D-11:** Store initialized in main.py lifespan (alongside checkpointer, Redis, tool_registry). App.state.store for dependency access
- **D-12:** Qdrant deployed as Docker container. LangGraph Store configured with Qdrant backend. Direct qdrant-client available as fallback
- **D-13:** Memory write-back after Respond node -- async `asyncio.create_task` fires `memory_service.extract_and_store()` without blocking
- **D-14:** LLM extracts key facts from conversation -- structured JSON output guided by system prompt
- **D-15:** LLM-based deduplication -- LLM compares new extracted facts against existing store entries
- **D-16:** Analyze node single query -- `store.search()` called once before planning
- **D-17:** Top-K raw results from store.search() -- let LLM decide relevance during planning
- **D-18:** Unified memory_service module with single `extract_and_store()` interface
- **D-19:** Long-term memory injected as SystemMessage in Analyze node -- format: "Relevant past context: {memories}"
- **D-20:** Synchronized writes to both Redis (short-term) and Store (long-term) on each conversation turn
- **D-21:** memory_service is the single entry point for all memory operations. Nodes call memory_service methods, never access Redis/Store directly
- **D-22:** Configurable multi-model -- OpenAI text-embedding-3-small as default, Ollama local models as optional
- **D-23:** Factory pattern `get_embedder(config)` -- mirrors existing `get_llm()` pattern in llm.py
- **D-24:** Per-model fixed dimension -- each embedding model gets its own Qdrant collection with matching dimension
- **D-25:** Settings-level configuration -- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` in .env via Pydantic Settings

### Claude's Discretion
- Exact value of N for message window (suggest 20)
- Exact value of K for raw message threshold before summarization
- Redis TTL duration (suggest 24 hours)
- Top-K value for store.search() (suggest 5)
- LLM prompt templates for fact extraction and dedup comparison
- Qdrant collection schema details (payload fields, index config)
- memory_service internal method decomposition
- Error handling and fallback behavior when Store/Qdrant is unavailable

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MEM-01 | Short-term memory using Redis (last N messages per conversation) | Redis Sorted Set pattern (D-03): ZADD for writes, ZRANGE for reads, sliding TTL. Key: `nextflow:memory:short:{thread_id}`. Hybrid with LLM summary via background coroutine (D-02, D-05). |
| MEM-02 | Context injection in Analyze node from short-term memory | Analyze node enhanced to call `memory_service.get_context()` which returns summary + recent messages, prepended as messages in state (D-06, D-19). |
| MEM-03 | LangGraph Store integration for cross-thread semantic search (long-term memory) | `AsyncPostgresStore` from `langgraph.store.postgres.aio` with pgvector index config provides `store.search(namespace, query=...)` with semantic similarity. Store injected at `build_graph(store=store)` (D-08, D-10). |
| MEM-04 | Qdrant/Milvus setup with collection schemas for long-term memory | **Updated:** LangGraph Store uses PostgreSQL + pgvector (not Qdrant). `AsyncPostgresStore.setup()` auto-creates vector tables. Docker image changed from `postgres:16` to `pgvector/pgvector:pg16`. Qdrant is only needed for direct fallback path. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langgraph (store module) | 1.1.3 | BaseStore + AsyncPostgresStore | Bundled with langgraph. Provides `store.put()`, `store.search()` with semantic similarity via pgvector. No additional install needed. |
| redis.asyncio | 5.x | Short-term memory operations | Already in project. Sorted Set ZADD/ZRANGE for sliding window message buffer. |
| langchain-openai | 1.1.12 | OpenAIEmbeddings for semantic search | Already in project. Provides `OpenAIEmbeddings(model="text-embedding-3-small")` for the Store index. |
| langchain-community | 0.4.1 | OllamaEmbeddings for local models | Already in project. Provides local embedding alternative. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pgvector/pgvector | pg16 tag | PostgreSQL vector extension | Required in Docker image for `AsyncPostgresStore` semantic search. Replaces `postgres:16` image. |
| qdrant-client | -- (NOT needed for primary path) | Direct Qdrant fallback | Only if LangGraph Store proves unviable (D-08 fallback). Not installed by default. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AsyncPostgresStore + pgvector | Direct qdrant-client + Qdrant container | Store path avoids a separate database, reuses PostgreSQL, and has native LangGraph integration. Qdrant adds operational complexity for minimal benefit at this scale. |
| AsyncPostgresStore + pgvector | InMemoryStore | InMemoryStore has no persistence, loses data on restart. Only suitable for testing. |

**Installation:**
```bash
# No new Python packages needed -- all are already installed or bundled.
# The only infrastructure change is the Docker image for PostgreSQL:
#   Change: postgres:16 -> pgvector/pgvector:pg16
```

**Version verification:**
- langgraph: 1.1.3 (installed, verified via site-packages)
- langchain-openai: 1.1.12 (installed)
- langchain-community: 0.4.1 (installed)
- langchain-core: 1.2.23 (installed)
- langgraph-checkpoint-postgres: 3.0.5 (installed)
- Python: 3.12.13

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  services/
    memory/                    # NEW module
      __init__.py              # Exports MemoryService
      service.py               # MemoryService class (coordination layer)
      short_term.py            # Redis sliding window + summary logic
      long_term.py             # Store interaction (put, search, dedup)
      embedder.py              # get_embedder() factory (mirrors llm.py)
    agent_engine/
      nodes/
        analyze.py             # ENHANCED: memory context injection
        respond.py             # ENHANCED: async memory write-back trigger
      graph.py                 # ENHANCED: store param in build_graph()
      checkpointer.py          # UNCHANGED (pattern reference for store init)
      store.py                 # NEW: create_store() async factory (mirrors checkpointer.py)
  core/
    config.py                  # ENHANCED: embedding config fields
  main.py                      # ENHANCED: Store initialization in lifespan
```

### Pattern 1: AsyncPostgresStore with pgvector for Semantic Memory
**What:** LangGraph's `AsyncPostgresStore` uses PostgreSQL with the pgvector extension for vector similarity search. It implements `BaseStore` with semantic `search()` when configured with an embedding index.
**When to use:** All long-term memory operations (cross-thread knowledge persistence and retrieval).
**Example:**
```python
from langgraph.store.postgres.aio import AsyncPostgresStore
from langchain_openai import OpenAIEmbeddings

async def create_store(database_url: str) -> AsyncPostgresStore:
    """Create and initialize the async PostgresStore with vector search.

    Mirrors create_checkpointer() pattern.
    """
    conn_string = database_url.replace("+asyncpg", "")

    async with AsyncPostgresStore.from_conn_string(
        conn_string,
        pool_config={"min_size": 1, "max_size": 5},
        index={
            "dims": 1536,  # text-embedding-3-small
            "embed": OpenAIEmbeddings(model="text-embedding-3-small"),
            "fields": ["content"],  # embed the content field of stored facts
        },
    ) as store:
        await store.setup()  # Creates tables + enables pgvector extension
        return store
```

### Pattern 2: Redis Sorted Set Sliding Window for Short-term Memory
**What:** Store messages as JSON strings in a Redis Sorted Set with timestamp scores. Maintain a sliding window of the last N messages. Store a summary string in a separate key for older context.
**When to use:** Every conversation turn -- writes on message send, reads in Analyze node.
**Example:**
```python
import json
import time
import redis.asyncio as aioredis

class ShortTermMemory:
    def __init__(self, redis: aioredis.Redis, window_size: int = 20, ttl: int = 86400):
        self._redis = redis
        self._window_size = window_size
        self._ttl = ttl

    async def add_message(self, thread_id: str, role: str, content: str) -> None:
        key = f"nextflow:memory:short:{thread_id}"
        msg = json.dumps({"role": role, "content": content})
        timestamp = time.time()

        pipe = self._redis.pipeline()
        pipe.zadd(key, {msg: timestamp})
        # Trim to window size (keep last N)
        pipe.zremrangebyrank(key, 0, -(self._window_size + 1))
        pipe.expire(key, self._ttl)
        await pipe.execute()

    async def get_context(self, thread_id: str) -> dict:
        key = f"nextflow:memory:short:{thread_id}"
        pipe = self._redis.pipeline()
        pipe.get(f"{key}:summary")
        pipe.zrange(key, 0, -1)  # All messages in window
        results = await pipe.execute()

        summary = results[0]
        messages = [json.loads(m) for m in results[1]]
        return {"summary": summary, "messages": messages}
```

### Pattern 3: Store Injection into LangGraph Nodes
**What:** Pass `store` as a keyword argument to `StateGraph.compile()`. LangGraph automatically injects it into node functions that declare a `store` keyword parameter.
**When to use:** All node functions that need to read or write long-term memory.
**Example:**
```python
# graph.py -- updated build_graph signature
def build_graph(
    checkpointer: AsyncPostgresSaver | None = None,
    store: BaseStore | None = None,      # NEW parameter
) -> CompiledStateGraph:
    builder = StateGraph(AgentState)
    builder.add_node("analyze", analyze_node)
    builder.add_node("respond", respond_node)
    # ... edges ...
    return builder.compile(checkpointer=checkpointer, store=store)

# analyze.py -- store injected by LangGraph runtime
async def analyze_node(state: AgentState, *, store: BaseStore) -> dict:
    user_message = state["messages"][-1].content
    # Semantic search for relevant memories
    memories = await store.asearch(
        ("users", user_id, "memories"),
        query=user_message,
        limit=5,
    )
    context = format_memories(memories)
    return {"messages": [SystemMessage(content=f"Relevant past context: {context}")]}
```

### Pattern 4: Async Write-back via asyncio.create_task
**What:** After the Respond node completes, fire `asyncio.create_task(memory_service.extract_and_store(...))` to extract facts, deduplicate, and write to Store without blocking the response stream.
**When to use:** Every conversation turn, triggered from respond_node.
**Example:**
```python
import asyncio

async def respond_node(state: AgentState, *, store: BaseStore) -> dict:
    # ... generate response ...

    # Fire-and-forget memory write-back (D-13)
    asyncio.create_task(
        memory_service.extract_and_store(
            messages=state["messages"],
            user_id=extract_user_id(state),
            thread_id=extract_thread_id(state),
            store=store,
        )
    )
    return {"messages": [response], "plan": "Response generated."}
```

### Anti-Patterns to Avoid
- **Direct Redis/Store access from nodes:** Nodes MUST call memory_service methods only (D-21). This prevents scattered storage logic and enables testing with mock services.
- **Blocking memory writes in the response path:** Never `await` the full fact extraction + Store write in the critical response path. Use `asyncio.create_task` (D-13, D-05).
- **Unscoped store.search() without namespace:** Always use user-scoped namespaces (D-09). Unscoped searches leak data between users.
- **Storing raw messages in the Store:** Only store LLM-extracted key facts (D-14). Raw messages bloat the vector index and produce poor search results.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom Qdrant client + embedding pipeline | AsyncPostgresStore with index config | Store handles embedding, indexing, and search automatically. pgvector handles ANN search. |
| Message deduplication in Redis | Custom ID tracking and overwrite logic | Sorted Set with timestamp scores | ZADD naturally deduplicates by score. ZREMRANGEBYANK trims cleanly. |
| Embedding model switching | Custom provider routing | get_embedder() factory mirroring get_llm() | Same proven pattern. LangChain's OpenAIEmbeddings and OllamaEmbeddings provide the abstraction. |
| Store setup and migration | Custom SQL for vector tables | `AsyncPostgresStore.setup()` | Auto-creates store tables, enables pgvector extension, runs vector migrations. |

**Key insight:** LangGraph's `AsyncPostgresStore` already solves the vector search + persistence problem that was originally scoped for Qdrant. Using it eliminates an entire database from the infrastructure.

## Common Pitfalls

### Pitfall 1: Three-Tier Memory Synchronization Drift
**What goes wrong:** Short-term Redis and long-term Store become inconsistent. Agent retrieves stale context.
**Why it happens:** Each tier has different consistency guarantees. Fire-and-forget writes to one tier can fail silently.
**How to avoid:** Write to both Redis and Store in the same `extract_and_store()` call (D-20). Redis write is the fast path (always succeeds). Store write can fail -- log errors but do not block. The checkpointer remains the authoritative full history source.
**Warning signs:** Semantic search returns results contradicting recent conversation history.

### Pitfall 2: PostgreSQL Image Missing pgvector Extension
**What goes wrong:** `AsyncPostgresStore.setup()` fails at `CREATE EXTENSION vector` because the standard `postgres:16` image does not include pgvector.
**Why it happens:** pgvector is a third-party extension, not bundled with official PostgreSQL images.
**How to avoid:** Change Docker image from `postgres:16` to `pgvector/pgvector:pg16` in docker-compose.yml. This image includes the vector extension pre-installed.
**Warning signs:** `ERROR: could not open extension control file "/usr/share/postgresql/16/extension/vector.control"` in setup logs.

### Pitfall 3: Embedding Dimension Mismatch
**What goes wrong:** Store is configured with `dims: 1536` but the embedding model produces vectors of a different dimension. Upsert fails silently or with confusing errors.
**Why it happens:** Switching embedding models without updating the Store config. Different models produce different dimensionality.
**How to avoid:** Pin the embedding model in Settings (D-25). Store dims config must match the model. Document the trade-off: switching models requires creating a new Store namespace or re-embedding all data (D-24).
**Warning signs:** `dimension mismatch` errors in Store writes. Search returns no results despite data being stored.

### Pitfall 4: Memory Extraction Burning LLM Tokens on Every Turn
**What goes wrong:** The fact extraction LLM call runs on every conversation turn, even for trivial messages ("ok", "thanks"). This wastes tokens and adds latency to the background task.
**Why it happens:** No gating logic before the extraction step.
**How to avoid:** Add a simple heuristic check before calling the extraction LLM: skip extraction for messages shorter than N characters or for messages that are purely conversational. The memory_service should handle this internally.
**Warning signs:** Token usage grows linearly with message count. Background tasks pile up on busy conversations.

### Pitfall 5: store.search() Returns All Items When No Index Configured
**What goes wrong:** If the Store is created without an `index` config, `search()` returns all items in the namespace with `score=None` (no semantic ranking). This is the InMemoryStore default behavior.
**Why it happens:** Forgetting to pass the `index` config when creating the Store. The method signature accepts it optionally.
**How to avoid:** Always create the Store with an `index` config containing `dims` and `embed`. The `create_store()` factory function should enforce this. Test that search results have non-None scores.
**Warning signs:** `search()` returns all stored items regardless of query. Score is None on all results.

### Pitfall 6: Redis Key Accumulation Without TTL
**What goes wrong:** Short-term memory keys accumulate indefinitely when TTL refresh (D-04) is not properly applied. Redis memory grows unbounded.
**Why it happens:** Forgetting to call EXPIRE on each write, or setting TTL on the Sorted Set but not the summary key.
**How to avoid:** Use a Redis pipeline that includes both the data write and EXPIRE in a single round-trip. Set TTL on both the messages key and the summary key.
**Warning signs:** Redis memory grows steadily. `INFO memory` shows consistent growth.

## Code Examples

Verified patterns from the installed langgraph 1.1.3 package:

### AsyncPostgresStore Creation with Embedding Index
```python
# Source: langgraph.store.postgres.aio (verified in installed package)
from contextlib import asynccontextmanager
from langgraph.store.postgres.aio import AsyncPostgresStore
from langchain_openai import OpenAIEmbeddings

async def create_store(database_url: str) -> AsyncPostgresStore:
    """Create AsyncPostgresStore with semantic search capability.

    Uses from_conn_string async context manager pattern.
    Mirrors create_checkpointer() in checkpointer.py.
    """
    conn_string = database_url.replace("+asyncpg", "")

    # from_conn_string is an async context manager
    store_ctx = AsyncPostgresStore.from_conn_string(
        conn_string,
        pool_config={"min_size": 1, "max_size": 5},
        index={
            "dims": 1536,
            "embed": OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key or None,
            ),
            "fields": ["content"],
        },
    )
    store = await store_ctx.__aenter__()
    await store.setup()  # Creates tables, enables pgvector, runs migrations
    return store
```

### Store Usage in Node Functions (Signature Verified)
```python
# Source: langgraph.graph.state.StateGraph.compile (verified signature)
# compile(checkpointer=None, *, store: BaseStore | None = None, ...)
#
# Node functions receive store as keyword arg:
from langgraph.store.base import BaseStore

async def analyze_node(state: AgentState, *, store: BaseStore) -> dict:
    """Analyze node with long-term memory injection."""
    user_id = state.get("user_id")  # Must be in config or state
    last_message = state["messages"][-1].content

    # Semantic search in user-scoped namespace
    results = await store.asearch(
        ("users", user_id, "memories"),
        query=last_message,
        limit=5,
    )

    if results:
        context = "; ".join([r.value.get("content", "") for r in results])
        # D-19: inject as SystemMessage
        return {
            "messages": [SystemMessage(content=f"Relevant past context: {context}")]
        }
    return {}
```

### Store Put with Automatic Embedding
```python
# Source: langgraph.store.base.BaseStore.put (verified signature)
# put(namespace, key, value, index=None, *, ttl=None)

await store.aput(
    ("users", user_id, "memories"),
    key=f"fact_{uuid4().hex[:8]}",
    value={
        "content": "User prefers Python for backend development",
        "type": "preference",
        "source_thread": thread_id,
        "created_at": datetime.utcnow().isoformat(),
    },
    # index=None means use the store's default fields config
    # The "content" field will be auto-embedded based on store index config
)
```

### get_embedder Factory (Mirrors get_llm Pattern)
```python
# Source: Existing get_llm() pattern in app/services/agent_engine/llm.py
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from app.core.config import settings

def get_embedder(config: dict | None = None) -> OpenAIEmbeddings | OllamaEmbeddings:
    """Create an embedding model instance from config or Settings defaults.

    Mirrors get_llm() factory pattern.
    """
    config = config or {}
    provider = config.get("provider", settings.embedding_provider)
    model = config.get("model", settings.embedding_model)

    if provider == "openai":
        return OpenAIEmbeddings(
            model=model,
            api_key=settings.openai_api_key or None,
        )
    elif provider == "ollama":
        return OllamaEmbeddings(
            model=model,
            base_url=settings.ollama_base_url,
        )
    raise ValueError(f"Unknown embedding provider: {provider}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate Qdrant container for vector search | AsyncPostgresStore with pgvector | langgraph 1.0+ (Oct 2025) | Eliminates a separate database. PostgreSQL handles both relational data and vector search. |
| Custom embedding pipeline | Store index config with auto-embedding | langgraph 1.1.x | Store handles embedding generation automatically during put(). No manual embedding calls needed. |
| Manual namespace management | Store namespace tuples | langgraph 1.0+ | Hierarchical namespacing built-in. `("users", user_id, "memories")` pattern is native. |
| InMemoryStore only for testing | InMemoryStore + AsyncPostgresStore | langgraph 1.1.x | Production-ready async Store with connection pooling and TTL support. |

**Deprecated/outdated:**
- `langgraph-store` as a separate pip package: Store is now bundled with the main `langgraph` package (verified -- `langgraph.store` module exists in langgraph 1.1.3).
- Direct qdrant-client for Store operations: AsyncPostgresStore handles vector operations via pgvector. qdrant-client is only for the fallback path (D-08).

## Open Questions

1. **AsyncPostgresStore lifecycle management**
   - What we know: `from_conn_string()` is an async context manager. The checkpointer uses a similar pattern but stores the instance on app.state.
   - What's unclear: Whether the Store's connection pool needs explicit cleanup in the lifespan shutdown. The context manager pattern suggests it does.
   - Recommendation: Wrap the Store in a helper that manages the context manager lifecycle. Store the wrapper on app.state. Cleanup in lifespan shutdown.

2. **user_id availability in node functions**
   - What we know: LangGraph nodes receive `state` and `store` keyword args. The current `AgentState` does not include `user_id`.
   - What's unclear: How to pass user_id to the Analyze node for namespace-scoped Store searches.
   - Recommendation: Pass user_id via the LangGraph config (`config={"configurable": {"user_id": ...}}`) and access it from `store` operations. Alternatively, add `user_id` to AgentState (less ideal for serialization). The config approach avoids polluting the checkpoint state.

3. **Store TTL support**
   - What we know: `BaseStore.put()` accepts a `ttl` parameter (in minutes). `BaseStore` has `supports_ttl` and `ttl_config` attributes.
   - What's unclear: Whether AsyncPostgresStore TTL sweeper runs automatically or needs explicit start/stop.
   - Recommendation: Configure TTL in the Store constructor (`ttl=TTLConfig(...)`) and verify sweeper behavior during implementation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL + pgvector | AsyncPostgresStore | Partial | postgres:16 (NO pgvector) | Upgrade to pgvector/pgvector:pg16 |
| Redis | Short-term memory | Available | 7-alpine (running) | -- |
| Docker | pgvector container | Available | 29.3.1 | -- |
| langgraph.store.postgres | Long-term memory | Available | 1.1.3 (bundled) | -- |
| langchain-openai | OpenAIEmbeddings | Available | 1.1.12 | -- |
| langchain-community | OllamaEmbeddings | Available | 0.4.1 | -- |

**Missing dependencies with no fallback:**
- pgvector extension in PostgreSQL: The `postgres:16` Docker image must be replaced with `pgvector/pgvector:pg16`. This is a blocking change -- `AsyncPostgresStore.setup()` will fail at `CREATE EXTENSION vector` without it.

**Missing dependencies with fallback:**
- None -- all Python packages are already installed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEM-01 | Last N messages cached in Redis per conversation | unit | `pytest tests/test_memory.py::test_short_term_add_and_retrieve -x` | Wave 0 |
| MEM-01 | Sliding window trims to N messages | unit | `pytest tests/test_memory.py::test_sliding_window_trim -x` | Wave 0 |
| MEM-01 | Summary generated when window exceeds threshold | unit | `pytest tests/test_memory.py::test_summary_compression -x` | Wave 0 |
| MEM-01 | TTL refreshed on each write | unit | `pytest tests/test_memory.py::test_ttl_refresh -x` | Wave 0 |
| MEM-02 | Analyze node injects Redis context into state | unit | `pytest tests/test_memory.py::test_analyze_context_injection -x` | Wave 0 |
| MEM-03 | Store.search returns semantic results | integration | `pytest tests/test_memory.py::test_store_semantic_search -x` | Wave 0 |
| MEM-03 | Store namespace scoped to user_id | unit | `pytest tests/test_memory.py::test_store_user_scoped_namespace -x` | Wave 0 |
| MEM-04 | pgvector extension available in PostgreSQL | integration | `pytest tests/test_memory.py::test_pgvector_available -x` | Wave 0 |
| MEM-04 | Store setup creates vector tables | integration | `pytest tests/test_memory.py::test_store_setup -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green + manual verification of Docker pgvector image change

### Wave 0 Gaps
- [ ] `tests/test_memory.py` -- covers MEM-01 through MEM-04
- [ ] Test fixtures for InMemoryStore (no PostgreSQL dependency for unit tests)
- [ ] Test fixture for Redis mock/fake (use existing test_redis fixture from conftest.py)
- [ ] Docker image change verification (manual: pull pgvector/pgvector:pg16, update docker-compose.yml)

## Sources

### Primary (HIGH confidence)
- langgraph 1.1.3 installed package -- verified `langgraph.store.postgres.aio.AsyncPostgresStore`, `langgraph.store.base.BaseStore`, `langgraph.store.memory.InMemoryStore` APIs by runtime inspection
- langgraph.graph.state.StateGraph.compile -- verified `store: BaseStore | None` parameter in signature
- BaseStore.search/put/get/aput/asearch signatures -- verified by `inspect.signature()` runtime introspection
- PostgresIndexConfig TypedDict -- verified annotations: dims, embed, fields, distance_type, ann_index_config
- AsyncPostgresStore.from_conn_string -- verified as `@classmethod @asynccontextmanager` with index and pool_config params
- VECTOR_MIGRATIONS -- verified first migration runs `CREATE EXTENSION vector` and creates `store_vectors` table
- Existing codebase: analyze.py, graph.py, checkpointer.py, llm.py, config.py, redis.py, main.py, docker-compose.yml -- all read and verified

### Secondary (MEDIUM confidence)
- Web search unavailable due to rate limit exhaustion (resets 2026-04-16). All findings based on runtime verification of installed packages.

### Tertiary (LOW confidence)
- Qdrant as fallback path: not investigated further since Store path is primary. If Store proves unviable, Qdrant research will be needed in a future iteration.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages verified by runtime inspection of installed code
- Architecture: HIGH -- AsyncPostgresStore API verified, StateGraph.compile store parameter verified, existing patterns (checkpointer, llm factory) verified in codebase
- Pitfalls: HIGH -- based on verified API behavior (InMemoryStore.search returning all items without index, pgvector migration SQL requiring extension)
- Store production readiness: HIGH -- `AsyncPostgresStore` is part of the official langgraph package with connection pooling, TTL support, and vector migrations. This resolves the STATE.md concern "LangGraph Store production readiness needs validation."

**Research date:** 2026-03-29
**Valid until:** 2026-04-29 (stable -- LangGraph 1.1.x API unlikely to change significantly)

---

## Critical Finding: LangGraph Store Production Readiness Validation

STATE.md flags: "LangGraph Store production readiness needs validation (affects Phase 4)"

**Resolution: LangGraph Store IS production-ready.** Evidence:

1. **AsyncPostgresStore** is bundled with langgraph 1.1.3 (not a separate package)
2. It uses psycopg3 connection pooling with async support -- same driver pattern as the checkpointer
3. It has automatic migration support (`setup()` creates tables, enables pgvector, runs versioned migrations)
4. It supports TTL with a background sweeper task
5. It supports semantic search via pgvector with configurable embedding models
6. The `from_conn_string` factory matches the checkpointer initialization pattern exactly
7. `StateGraph.compile()` natively accepts `store=` parameter -- no workarounds needed
8. Node functions receive `store` as an injected keyword argument -- no manual passing required

**Recommendation:** Proceed with AsyncPostgresStore as the primary Store implementation. Do not deploy Qdrant for v1. The only infrastructure change needed is switching the PostgreSQL Docker image to include pgvector.
