# Phase 4: Memory System - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 04-memory-system
**Areas discussed:** Short-term Memory Design, Long-term Memory Implementation, Memory Extraction & Write-back, Embedding Model Selection

---

## Short-term Memory Design

| Option | Description | Selected |
|--------|-------------|----------|
| 按消息条数 | Last N messages, simple & predictable | ✓ |
| 按 token 预算 | Token count-based truncation | |
| Claude 决定 | Let Claude choose | |

**User's choice:** 按消息条数（推荐）
**Notes:** Redis holds recent context only; LangGraph checkpointer has full history

---

| Option | Description | Selected |
|--------|-------------|----------|
| 原始消息存储 | Store raw HumanMessage/AIMessage JSON | |
| LLM 摘要存储 | LLM-generated summary replacing raw messages | |
| 混合（摘要+原始） | Recent K raw + older summarized | ✓ |

**User's choice:** 混合（摘要+原始）
**Notes:** Balance between token efficiency and detail preservation

---

| Option | Description | Selected |
|--------|-------------|----------|
| 滑动 TTL | Refresh TTL on each new message | ✓ |
| 固定 TTL | Fixed from first write | |
| 永不过期 | Manual lifecycle management | |

**User's choice:** 滑动 TTL（推荐）
**Notes:** Active conversations stay alive, inactive ones auto-expire

---

| Option | Description | Selected |
|--------|-------------|----------|
| 异步摘要压缩 | asyncio background coroutines for summarization | ✓ |
| 同步摘要生成 | Real-time summary on each read | |

**User's choice:** 异步摘要压缩（推荐）
**Notes:** No extra infrastructure (Celery not yet set up), asyncio.create_task sufficient

---

| Option | Description | Selected |
|--------|-------------|----------|
| Celery 异步任务 | Distributed task queue for summarization | |
| asyncio 后台协程 | Background coroutines, no extra infra | ✓ |
| Claude 决定 | Let Claude choose | |

**User's choice:** asyncio 后台协程（推荐）
**Notes:** Celery not deployed yet; asyncio sufficient for v1 memory summarization

---

| Option | Description | Selected |
|--------|-------------|----------|
| Messages 列表注入 | Prepend context as messages in state | ✓ |
| 分字段注入 | Summary in scratchpad, raw in messages | |

**User's choice:** Messages 列表注入（推荐）
**Notes:** Leverages LangChain add_messages reducer naturally

---

| Option | Description | Selected |
|--------|-------------|----------|
| Sorted Set + String | Sorted Set for messages, String for summary | ✓ |
| 独立 key per message | Individual keys, SCAN for retrieval | |
| Claude 决定 | Let Claude choose | |

**User's choice:** Sorted Set + String（推荐）
**Notes:** Efficient range queries by timestamp, proven pattern for sliding window

---

## Long-term Memory Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| LangGraph Store 优先 | Native Store with store.search()/store.put() | ✓ |
| 直接 Qdrant 集成 | Custom Qdrant management | |
| 渐进式（先验证再决定） | Research first, then choose | |

**User's choice:** LangGraph Store 优先（推荐）
**Notes:** STATE.md flags production readiness needs validation; fallback to direct Qdrant if not viable

---

| Option | Description | Selected |
|--------|-------------|----------|
| 回退到直接 Qdrant | Switch to direct integration if Store fails | ✓ |
| 坚持 LangGraph Store | Accept limitations, wait for improvements | |

**User's choice:** 回退到直接 Qdrant
**Notes:** Abstract memory operations so backend can be swapped

---

| Option | Description | Selected |
|--------|-------------|----------|
| 编译时注入 | build_graph(store=store) at compilation | ✓ |
| 运行时注入 | FastAPI Depends or global variable | |

**User's choice:** 编译时注入（推荐）
**Notes:** Consistent with existing checkpointer pattern in graph.py

---

| Option | Description | Selected |
|--------|-------------|----------|
| 用户级别 | namespace=("users", user_id, "memories") | ✓ |
| 线程级别 | namespace=("threads", thread_id, "memories") | |
| 双层（用户+线程） | Both user and thread namespaces | |

**User's choice:** 用户级别（推荐）
**Notes:** Memories shared across conversations per user — more useful than thread-scoped

---

| Option | Description | Selected |
|--------|-------------|----------|
| Respond 节点后异步 | Async after response, non-blocking | ✓ |
| Respond 节点内同步 | Inline write, adds latency | |
| 新增 MEMORY 节点 | Dedicated node after Respond | |

**User's choice:** Respond 节点后异步（推荐）
**Notes:** asyncio.create_task fires extract_and_store() without blocking response stream

---

| Option | Description | Selected |
|--------|-------------|----------|
| Qdrant Docker + 双路径 | Store primary + qdrant-client fallback | ✓ |
| Qdrant Docker + 直接集成 | Direct qdrant-client only | |

**User's choice:** Qdrant Docker + 双路径（推荐）
**Notes:** LangGraph Store with Qdrant backend; direct client available as fallback

---

| Option | Description | Selected |
|--------|-------------|----------|
| lifespan 初始化 | Init alongside checkpointer in lifespan | ✓ |
| 懒加载 | First-use initialization | |

**User's choice:** lifespan 初始化（推荐）
**Notes:** Follows existing checkpointer initialization pattern in main.py

---

## Memory Extraction & Write-back

| Option | Description | Selected |
|--------|-------------|----------|
| LLM 提取关键事实 | Structured extraction of key knowledge points | ✓ |
| 全部存储 | Store all messages as vectors | |
| 摘要存储 | LLM-generated conversation summaries | |

**User's choice:** LLM 提取关键事实（推荐）
**Notes:** System prompt guides LLM to output structured JSON with extracted facts

---

| Option | Description | Selected |
|--------|-------------|----------|
| LLM 判断重复 | LLM compares new vs existing memories | ✓ |
| 不去重（推荐 v1） | Accept duplicates, semantic search handles ranking | |
| 相似度去重 | Cosine similarity threshold | |

**User's choice:** LLM 判断重复
**Notes:** LLM compares new facts against existing store entries; decides update/merge/skip

---

| Option | Description | Selected |
|--------|-------------|----------|
| Analyze 节点单次查询 | store.search() once before planning | ✓ |
| 多节点查询 | Query in multiple nodes | |
| Claude 决定 | Let Claude choose | |

**User's choice:** Analyze 节点单次查询（推荐）
**Notes:** Single search call, results injected as SystemMessage context

---

| Option | Description | Selected |
|--------|-------------|----------|
| Top-K 原始结果 | Return top K results, LLM judges relevance | ✓ |
| LLM 二次筛选 | LLM re-ranks search results | |
| 阈值过滤 | Score threshold cutoff | |

**User's choice:** Top-K 原始结果（推荐）
**Notes:** Simple, let LLM naturally weigh relevance during planning

---

| Option | Description | Selected |
|--------|-------------|----------|
| 单一 memory_service 封装 | Unified extract_and_store() interface | ✓ |
| 分散处理 | Separate modules for extract, store, dedup | |

**User's choice:** 单一 memory_service 封装（推荐）
**Notes:** One entry point for all memory operations; nodes never access Redis/Store directly

---

| Option | Description | Selected |
|--------|-------------|----------|
| System message 注入 | "Relevant past context: {memories}" as SystemMessage | ✓ |
| State 新字段 | New AgentState field for memory context | |

**User's choice:** System message 注入（推荐）
**Notes:** No AgentState modification needed; consistent with messages pattern

---

| Option | Description | Selected |
|--------|-------------|----------|
| 同步写入两层 | Write both Redis and Store on each turn | ✓ |
| 独立写入 | Each tier writes independently | |

**User's choice:** 同步写入两层（推荐）
**Notes:** Prevents PITFALLS.md Pitfall 8 — three-tier memory sync drift

---

| Option | Description | Selected |
|--------|-------------|----------|
| 统一接口封装 | Single extract_and_store() method | ✓ |
| 分离 API | Separate APIs for extract, dedup, store | |

**User's choice:** 统一接口封装（推荐）
**Notes:** RESPOND node calls one method; memory_service handles all coordination internally

---

## Embedding Model Selection

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI embedding | text-embedding-3-small, quality & cost-effective | |
| 本地模型（Ollama） | No API cost, lower quality | |
| 可配置多模型 | OpenAI default + Ollama optional | ✓ |

**User's choice:** 可配置多模型
**Notes:** Default OpenAI, configurable to local models via Settings

---

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI 默认 + Ollama 可选 | text-embedding-3-small default, Ollama alternative | ✓ |
| Ollama 默认 + OpenAI 可选 | Local default, cloud optional | |

**User's choice:** OpenAI 默认 + Ollama 可选（推荐）
**Notes:** Matches LLM provider strategy — cloud default, local option

---

| Option | Description | Selected |
|--------|-------------|----------|
| Factory 模式 | get_embedder(config) mirrors get_llm() | ✓ |
| 硬编码调用 | Direct embedding calls in memory_service | |
| Claude 决定 | Let Claude choose | |

**User's choice:** Factory 模式（推荐）
**Notes:** Consistent with LLM factory pattern in llm.py

---

| Option | Description | Selected |
|--------|-------------|----------|
| 每个模型固定维度 | Each model gets its own Qdrant collection | ✓ |
| 统一维度 | All models output same dimension | |

**User's choice:** 每个模型固定维度（推荐）
**Notes:** Switching models requires new collection; document this trade-off

---

| Option | Description | Selected |
|--------|-------------|----------|
| Settings 配置 | Global EMBEDDING_PROVIDER in .env | ✓ |
| Agent 级别配置 | Per-agent embedding model selection | |

**User's choice:** Settings 配置（推荐）
**Notes:** Global for v1; per-agent configuration deferred to future phase

---

## Claude's Discretion

- Exact N value for message window
- Exact K threshold for raw vs summary
- Redis TTL duration
- Top-K value for store.search()
- Fact extraction prompt templates
- Dedup comparison prompt templates
- Qdrant collection schema details
- memory_service internal method names and decomposition
- Error handling when Store/Qdrant unavailable

## Deferred Ideas

None — discussion stayed within phase scope
