# Domain Pitfalls

**Domain:** Universal Agent Platform (LangGraph + FastAPI + React + MCP)
**Researched:** 2026-03-28
**Confidence:** MEDIUM (based on official documentation for LangGraph, MCP, LangChain, Zustand; community patterns inferred from domain expertise)

## Critical Pitfalls

### Pitfall 1: LangGraph Recursion Limit Surprises

**What goes wrong:**
The LangGraph agent workflow (analyze -> plan -> execute -> reflect -> respond) hits the default recursion limit of 1000 super-steps, causing `GraphRecursionError` in production. This typically happens when the agent enters a reflection loop -- the reflect node determines the answer is insufficient and routes back to plan, which executes again, reflects again, and so on until the limit is exceeded. The error arrives as an uncaught exception, leaving the WebSocket connection hanging with no response to the user.

**Why it happens:**
Developers design the graph with optimistic assumptions about loop termination. The reflect node's conditional edge routes back to planning when quality is "unsatisfactory," but no hard limit exists within the graph logic itself. During testing with simple queries the loop terminates quickly, but complex multi-step tasks or ambiguous user inputs cause the agent to cycle indefinitely.

**How to avoid:**
1. Use the `RemainingSteps` managed value in your state schema to proactively track remaining steps.
2. Add a conditional edge in the reflect node that checks `remaining_steps` and routes to the respond node when steps are running low (e.g., `<= 2`).
3. Set an explicit `recursion_limit` per invocation based on task complexity, passed via `config={"recursion_limit": N}`.
4. Log `config["metadata"]["langgraph_step"]` in each node for observability.
5. Never catch `GraphRecursionError` as the sole strategy -- use proactive handling inside the graph so the agent completes gracefully with a partial result.

```python
from langgraph.managed import RemainingSteps

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: RemainingSteps

def reflect_node(state: AgentState) -> dict:
    if state["remaining_steps"] <= 2:
        return {"messages": [AIMessage(content="Providing best-effort response due to complexity limit.")]}
    # normal reflection logic
    ...
```

**Warning signs:**
- Agent responses become slow and eventually hang on complex queries.
- `GraphRecursionError` appearing in logs for any non-trivial input.
- The reflect -> plan loop running more than 3 iterations in development.
- No `RemainingSteps` field in your state schema.

**Phase to address:** Phase 1 (Agent Engine Core) -- the graph structure and recursion handling must be built in from day one. Retrofitting `RemainingSteps` into an existing graph requires touching every conditional edge.

---

### Pitfall 2: LangGraph State Reducer Misconfiguration

**What goes wrong:**
Messages or other list-type state fields silently lose data because the wrong reducer is used. Without an explicit reducer, LangGraph uses the default behavior: node return values **overwrite** the field entirely. A node returning `{"messages": [new_message]}` replaces the entire conversation history with just that one message. The agent loses all prior context mid-conversation.

**Why it happens:**
LangGraph's default reducer behavior (overwrite) is unintuitive for list fields. Developers expect `list` fields to append by default. The `Annotated` syntax with `operator.add` or `add_messages` is easy to miss in documentation. Additionally, the `add_messages` reducer has special behavior -- it tracks message IDs and can **update** existing messages in addition to appending new ones, which is critical for human-in-the-loop patterns.

**How to avoid:**
1. Always use `Annotated[list[AnyMessage], add_messages]` for the messages field -- never use bare `list` or `operator.add` for messages.
2. Use `operator.add` (or a custom reducer) for other list fields that should accumulate.
3. For the `messages` channel specifically, `add_messages` handles serialization/deserialization automatically, allowing both `AIMessage` objects and plain dicts as input.
4. Write a state schema test that invokes a node twice and asserts the list has accumulated both updates.

```python
from langgraph.graph.message import add_messages

# CORRECT
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    documents: Annotated[list[str], operator.add]
    current_plan: str  # overwrite is correct here

# WRONG -- messages will be overwritten
class AgentState(TypedDict):
    messages: list[AnyMessage]
```

**Warning signs:**
- Agent "forgets" earlier messages in a conversation.
- State inspection shows only the last node's output in a list field.
- `add_messages` is not imported anywhere in the codebase.
- Nodes return partial state that accidentally erases fields.

**Phase to address:** Phase 1 (Agent Engine Core) -- the state schema is foundational and extremely painful to change once nodes are built against it.

---

### Pitfall 3: MCP Transport Incompatibility and Stale SSE Usage

**What goes wrong:**
The MCP client connects to MCP servers using the deprecated SSE transport, which will lose protocol support in future updates. Alternatively, the client attempts Streamable HTTP against servers that only support legacy SSE, causing initialization failures. The system silently fails to discover tools from external MCP servers, leaving the agent unable to call critical tools.

**Why it happens:**
The MCP specification transitioned from an older SSE-only transport to the Streamable HTTP transport. Many existing MCP servers still use the legacy SSE endpoints (`/sse` + `/messages`). The MCP documentation explicitly marks the SSE transport as **deprecated**. New implementations should default to Streamable HTTP but must support backwards compatibility detection.

**How to avoid:**
1. Implement transport detection: attempt Streamable HTTP first (POST with `Accept: application/json, text/event-stream`), then fall back to legacy SSE on 4xx.
2. Never hard-code a transport type -- let the client detect based on server response.
3. Use the `Mcp-Session-Id` header for session management with Streamable HTTP.
4. Implement `Last-Event-ID` for resumability on broken connections.
5. Monitor MCP server logs for transport negotiation errors.

```python
async def detect_transport(server_url: str) -> str:
    # Try Streamable HTTP first
    response = await client.post(server_url, json=initialize_request,
                                  headers={"Accept": "application/json, text/event-stream"})
    if response.ok:
        return "streamable-http"
    # Fall back to legacy SSE
    sse_response = await client.get(server_url, headers={"Accept": "text/event-stream"})
    if sse_response.ok:
        return "legacy-sse"
    raise ValueError("Unsupported MCP transport")
```

**Warning signs:**
- MCP tool list is empty despite server being "connected."
- Connection works in development but fails against production MCP servers.
- Error messages referencing `/sse` endpoint in production logs.
- No transport detection logic in the MCP client code.

**Phase to address:** Phase 2 (MCP Integration) -- transport handling must be designed into the MCP client from the start.

---

### Pitfall 4: MCP DNS Rebinding and Origin Validation Gaps

**What goes wrong:**
Local MCP servers bound to `0.0.0.0` are accessible from any network interface. Without Origin header validation, a malicious webpage can use DNS rebinding to interact with local MCP servers from a remote website. An attacker crafts a webpage that resolves to `127.0.0.1`, then sends tool invocation requests to the local MCP server, potentially exfiltrating data or executing unauthorized actions.

**Why it happens:**
MCP security considerations are documented but easy to overlook during implementation. Developers bind to `0.0.0.0` during development for convenience and never change it for production. Origin validation feels like a frontend concern, but for MCP servers it is a critical transport-layer requirement.

**How to avoid:**
1. Always validate the `Origin` header on all incoming connections to MCP servers.
2. Bind local MCP servers to `127.0.0.1` only -- never `0.0.0.0`.
3. Use TLS/HTTPS for all production MCP connections.
4. Validate `Mcp-Session-Id` values are cryptographically secure.
5. Implement proper authentication on all MCP endpoints.
6. Add rate limiting and message size limits.

**Warning signs:**
- MCP server listening on `0.0.0.0` in any configuration.
- No Origin header validation in the MCP server middleware.
- Local MCP servers accessible from non-localhost addresses.
- No authentication on MCP tool invocation endpoints.

**Phase to address:** Phase 2 (MCP Integration) and Phase 5 (Security Hardening) -- transport security must be designed early, verified later.

---

### Pitfall 5: Streaming Chain Breakage from Non-Streaming Components

**What goes wrong:**
The frontend never receives token-by-token streaming despite the LLM supporting it. The user sees a blank response area for several seconds, then the entire response appears at once. The root cause is a non-streaming component in the LangChain chain between the LLM and the WebSocket output. Components like retrievers, certain parsers, or custom functions that operate on **finalized inputs** rather than **input streams** break the streaming pipeline.

**Why it happens:**
LangChain's `stream`/`astream` methods only stream the final output. If any step in the chain requires the full input before producing output, streaming is blocked at that point. The `astream_events` API can still stream intermediate steps from streaming-capable components, but developers often use `astream` without realizing it stops streaming at the first non-streaming component.

**How to avoid:**
1. Use `astream_events` (V2) instead of `astream` for the agent chain to get intermediate step events.
2. Ensure custom functions in chains operate on input streams (use generator functions with `yield`).
3. For tools that invoke runnables internally, **propagate callbacks** explicitly -- pass `callbacks` parameter from the tool signature to any `.invoke()` calls.
4. Test streaming end-to-end early -- if you see `on_chat_model_stream` events in `astream_events` but the WebSocket only sends a single chunk, a non-streaming component is blocking.
5. Place non-streaming components (like retrievers) before the LLM call, not after.

```python
# WRONG -- callbacks not propagated, no stream events from inner runnable
@tool
def search_tool(query: str):
    result = retriever.invoke(query)  # callbacks lost
    return result

# CORRECT -- propagate callbacks
@tool
def search_tool(query: str, callbacks):
    result = retriever.invoke(query, {"callbacks": callbacks})
    return result
```

**Warning signs:**
- Frontend shows no streaming despite LLM supporting it.
- `astream` works but `astream_events` shows events from the model that never reach the client.
- Tools invoked from LangGraph nodes do not appear in stream events.
- Large latency gap between user input and first visible response token.

**Phase to address:** Phase 1 (Agent Engine Core) for the streaming architecture, Phase 3 (Frontend) for WebSocket integration.

---

### Pitfall 6: WebSocket Connection Lifecycle Mismanagement

**What goes wrong:**
WebSocket connections leak on the server when clients disconnect without clean closure (mobile network switching, browser crash, tab close). FastAPI's WebSocket handler continues holding resources, the agent graph execution keeps running on a dead connection, and Redis session data accumulates. Under load, the server runs out of connection handles or memory.

**Why it happens:**
FastAPI (Starlette) WebSocket connections do not automatically detect client disconnects during long-running operations. If the server is in the middle of streaming agent output via `websocket.send_text()`, and the client drops, the next `send_text()` call raises `WebSocketDisconnect`, but only if the server tries to send. If the agent is in a long computation phase, no send is attempted, and the disconnect goes undetected.

**How to avoid:**
1. Wrap every WebSocket handler in try/except for `WebSocketDisconnect` and `ConnectionClosed`.
2. Implement a heartbeat/ping mechanism -- send periodic keepalive frames and close connections that miss too many pongs.
3. Use `asyncio.wait_for` with timeouts on long-running agent operations to prevent indefinite blocking on dead connections.
4. Clean up all resources (Redis session, agent state, connection registry) in the finally block.
5. Register each connection in a connection manager that tracks active connections per user.
6. For agent execution, check connection liveness before each streaming chunk.

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connection_manager.register(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Launch agent execution with connection liveness check
            async for event in agent.astream_events(data, config):
                if not connection_manager.is_alive(session_id):
                    break  # Client disconnected
                await websocket.send_json(event)
    except WebSocketDisconnect:
        pass  # Clean disconnect
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.unregister(session_id)
        # Clean up Redis session, cancel running tasks
```

**Warning signs:**
- Server memory grows steadily over time despite consistent user count.
- Redis keys for old sessions never expire.
- Agent graph executions running for minutes on dead connections.
- `WebSocketDisconnect` errors appearing but not handled.

**Phase to address:** Phase 3 (Frontend + WebSocket) -- the connection manager must be designed as a core infrastructure component, not bolted on later.

---

### Pitfall 7: Zustand Store Design Without Slices for Complex State

**What goes wrong:**
The Zustand store grows into a monolithic object with 30+ fields covering chat state, skill management, MCP connections, agent configuration, and user preferences. Every state update triggers re-renders across unrelated components. The store becomes a bottleneck where any change risks breaking unrelated features. TypeScript types become unwieldy with a single `create<MassiveState>()(...)` call.

**Why it happens:**
Zustand's simplicity makes it tempting to dump everything into one store. The slices pattern requires more upfront setup with `StateCreator` generics. Teams start with a small store for chat state, then incrementally add skill state, MCP state, user state, etc., without refactoring. By the time the problem is noticeable, the store is deeply intertwined with every component.

**How to avoid:**
1. Adopt the slices pattern from the start -- separate stores for chat, skills, MCP, agent config, and user state.
2. Each slice has its own `StateCreator` with explicit generics for cross-slice access where needed.
3. Use `useShallow` for selectors that depend on multiple fields to prevent unnecessary re-renders.
4. Keep middleware order consistent: `devtools` should be the outermost middleware.
5. Use the curried `create<T>()(...)` syntax for explicit typing.
6. Consider using `combine` middleware for simpler slices where full type inference is desired.

```typescript
// Slice pattern with proper typing
interface ChatSlice {
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => void;
}

interface McpSlice {
  servers: McpServer[];
  connectServer: (url: string) => void;
}

const createChatSlice: StateCreator<ChatSlice & McpSlice, [], [], ChatSlice> = (set) => ({
  messages: [],
  isStreaming: false,
  sendMessage: (content) => set((state) => ({
    messages: [...state.messages, { role: 'user', content }]
  })),
});

const useStore = create<ChatSlice & McpSlice>()((...a) => ({
  ...createChatSlice(...a),
  ...createMcpSlice(...a),
}));
```

**Warning signs:**
- Single Zustand store with more than 10 top-level fields.
- Components re-rendering when unrelated state changes.
- Deeply nested `set()` calls modifying multiple domains at once.
- Difficulty adding new state features without touching existing code.

**Phase to address:** Phase 3 (Frontend) -- store architecture must be decided before building any UI components.

---

### Pitfall 8: Three-Tier Memory Synchronization Drift

**What goes wrong:**
The three-tier memory system (short-term Redis, long-term vector DB, working memory AgentState) becomes inconsistent. The agent retrieves stale context from the vector store because short-term Redis updates were not synced. Conversation history in Redis shows recent messages, but the vector store's semantic search returns results based on older embeddings. The agent produces contradictory or repetitive responses.

**Why it happens:**
Each memory tier has different consistency guarantees, latency profiles, and failure modes. Redis is fast but ephemeral; vector DB writes are slow but persistent; AgentState is request-scoped. Developers treat memory writes as fire-and-forget without coordination. The vector embedding pipeline may batch updates, creating a window where short-term memory has data that long-term memory does not.

**How to avoid:**
1. Define a clear write-through policy: every memory update should write to both Redis (fast read) and the vector DB (persistent) in a coordinated manner.
2. Use Redis as the source of truth for recent context (last N messages) and the vector DB for historical/semantic retrieval.
3. Implement vector embedding as an async task (Celery) but with a "pending sync" flag that prevents stale reads.
4. Add versioning or timestamps to memory entries so the agent can detect and resolve conflicts.
5. Implement a memory reconciliation job that periodically checks consistency between tiers.
6. When reading from both tiers, merge results with recency bias -- prefer Redis for recent context, vector DB for older knowledge.

**Warning signs:**
- Agent responds with outdated information that was recently corrected.
- Semantic search returns results that contradict recent conversation history.
- Memory-related bugs that only appear after extended conversations.
- No synchronization logic between Redis writes and vector DB upserts.

**Phase to address:** Phase 2 (Memory System) -- the memory architecture and sync policy must be designed before building agent logic that depends on it.

---

### Pitfall 9: Skill Sandbox Escapes and Untrusted Code Execution

**What goes wrong:**
A malicious or buggy skill package executes arbitrary code outside its intended sandbox, accessing the host filesystem, network, or other skills' data. Since skills are dynamically loaded and potentially user-contributed (from a "skill marketplace"), a compromised skill can exfiltrate conversation data, modify agent behavior, or launch attacks on internal services.

**Why it happens:**
Sandboxing Python code is notoriously difficult. Developers may use `subprocess` isolation or Docker containers for sandboxing but fail to properly restrict resource limits, network access, or filesystem mounts. Skills may import dangerous standard library modules (`os`, `subprocess`, `socket`) if the sandbox does not enforce import restrictions.

**How to avoid:**
1. Run each skill in an isolated Docker container with minimal base image and no network access by default.
2. Use resource limits (CPU, memory, execution time) on skill containers.
3. Mount only the specific data directories a skill needs, read-only where possible.
4. Implement an allowlist of imports/modules rather than a denylist.
5. Scan skill packages for known dangerous patterns before loading.
6. Log all skill invocations with input/output for audit.
7. Require skill packages to declare permissions (filesystem, network, compute) and enforce them at the container level.

**Warning signs:**
- Skills running in the same process as the agent engine.
- No resource limits on skill execution.
- Skills can import `os`, `subprocess`, or `socket` without restriction.
- No audit logging of skill invocations.
- Skill marketplace accepts packages without security scanning.

**Phase to address:** Phase 4 (Skill System) -- sandboxing architecture must be designed before any dynamic skill loading.

---

### Pitfall 10: LLM Provider Abstraction Leaking Through

**What goes wrong:**
The LangChain abstraction layer is supposed to make LLM providers interchangeable, but provider-specific behavior leaks through. OpenAI returns `tool_calls` in a different format than Anthropic. Streaming behavior differs between providers (some emit empty initial chunks, some include usage metadata on first chunk, others on last). Token counting methods vary. Error handling (rate limits, context window exceeded) has different error codes per provider. The agent works perfectly with one provider and fails subtly with another.

**Why it happens:**
LangChain's `BaseChatModel` provides a common interface, but each provider's implementation has quirks. The `AIMessage.tool_calls` format is normalized by LangChain, but `additional_kwargs` contains provider-specific data. Streaming event shapes differ. Token limits are provider-specific. Developers test against one provider and assume the abstraction works for all.

**How to avoid:**
1. Never access `additional_kwargs` directly -- use the normalized `tool_calls` property.
2. Handle provider-specific errors at the adapter layer, not in agent logic.
3. Implement a provider configuration registry that includes per-provider settings (max tokens, rate limits, streaming quirks).
4. Write integration tests against every supported provider from the start.
5. Use `init_chat_model` with explicit `model_provider` parameter rather than relying on auto-detection.
6. Normalize streaming output in a middleware layer before sending to the WebSocket.

**Warning signs:**
- Agent works with OpenAI but fails with Anthropic or local models.
- Tool call parsing breaks when switching providers.
- Streaming events have different structures depending on the model.
- Error messages reference provider-specific error codes in agent logic.

**Phase to address:** Phase 1 (Agent Engine Core) for the abstraction layer design, with provider-specific tests in every subsequent phase.

---

## Moderate Pitfalls

### Pitfall 11: LangGraph Checkpoint Serialization with Pydantic State

**What goes wrong:**
Using Pydantic `BaseModel` as the state schema causes serialization failures when using checkpoints (persistence). Pydantic models may contain fields that are not JSON-serializable (database connections, file handles, custom objects). Checkpoint deserialization fails on graph resumption, losing conversation state.

**How to avoid:** Use `TypedDict` or `dataclass` for state schemas instead of Pydantic when using checkpoints. If Pydantic validation is needed, validate at node boundaries and store validated data in TypedDict state.

---

### Pitfall 12: FastAPI Sync Blocking in Async Endpoints

**What goes wrong:**
Calling synchronous LangChain or LangGraph methods (`.invoke()` instead of `.ainvoke()`) inside an `async def` FastAPI endpoint blocks the event loop. Under concurrent load, all async request handlers stall waiting for the blocking call to complete.

**How to avoid:** Always use `await` with async variants (`ainvoke`, `astream`, `astream_events`). If a sync-only library must be used, wrap it in `asyncio.to_thread()` or `run_in_executor()`.

---

### Pitfall 13: Qdrant/Milvus Embedding Dimension Mismatch

**What goes wrong:**
The embedding model used for indexing documents produces vectors of dimension X (e.g., 1536 for OpenAI text-embedding-3-small), but the vector database collection was created with dimension Y. Upsert operations fail silently or with confusing dimension mismatch errors. Switching embedding models requires re-embedding all documents.

**How to avoid:** Pin the embedding model version in configuration. Validate collection dimensions on startup. Implement an embedding model migration strategy (re-embed on model change). Store the embedding model identifier alongside vectors.

---

### Pitfall 14: Celery Task Queue Starvation for Agent Operations

**What goes wrong:**
Long-running agent operations consume all Celery workers, starving shorter tasks like email notifications or analytics events. A single complex agent task (with multiple LLM calls and tool invocations) can block a worker for minutes.

**How to avoid:** Use separate Celery queues with dedicated workers for different task types (agent tasks, background jobs, notifications). Set per-task time limits. Use `task_acks_late=True` to prevent premature acknowledgment.

---

### Pitfall 15: JWT Token Refresh Race Condition

**What goes wrong:**
When a JWT token expires during an active WebSocket connection, the frontend sends a refresh request. If multiple concurrent requests trigger refresh simultaneously, the first refresh succeeds but subsequent ones fail (old refresh token already used). The WebSocket connection drops because one of the concurrent refresh attempts invalidates the session.

**How to avoid:** Implement a refresh mutex on the frontend -- only one refresh request at a time, with other requests queuing behind it. Send refresh tokens proactively before expiry. Use the WebSocket connection itself for token renewal rather than parallel HTTP requests.

---

## Minor Pitfalls

### Pitfall 16: Zustand `get()` Called During Initialization

**What goes wrong:**
Calling `get()` during store initialization returns `undefined`, causing runtime errors. This is a known unsoundness in Zustand's types -- the types claim `get()` always returns `T`, but during synchronous initialization it returns `undefined`.

**How to avoid:** Never call `get()` in the initial state factory function. Only use `get()` inside action callbacks that are called after store creation.

---

### Pitfall 17: LangGraph `Command` vs Conditional Edge Confusion

**What goes wrong:**
Developers use `Command(update=..., goto=...)` when they should use conditional edges, or vice versa. `Command` is for when a node needs to **both update state and route** in one step. Conditional edges are for **routing only** based on state. Mixing these patterns creates confusing graph logic.

**How to avoid:** Use conditional edges for routing decisions. Use `Command` only when state update and routing must happen atomically. Use `Send` for map-reduce patterns where the number of parallel branches is dynamic.

---

### Pitfall 18: MCP Tool Discovery Performance on Startup

**What goes wrong:**
Connecting to all configured MCP servers and discovering their tools on every application startup adds 10-30 seconds of cold-start latency. Tool schemas are fetched sequentially, and each server requires an initialization handshake.

**How to avoid:** Cache tool schemas in Redis with TTL. Discover tools asynchronously in parallel on startup. Support lazy tool discovery for servers that are rarely used. Implement a health check endpoint that confirms MCP connections without full re-discovery.

---

### Pitfall 19: MinIO Presigned URL Expiration for Skill Packages

**What goes wrong:**
Skill packages stored in MinIO are accessed via presigned URLs that expire. If a skill takes longer than the URL expiration time to download (large package, slow network), the download fails mid-transfer. The skill fails to load.

**How to avoid:** Use longer expiration times for skill packages (24h+). Implement retry logic with fresh presigned URLs on download failure. Consider using MinIO's bucket policies for internal service-to-service access instead of presigned URLs.

---

### Pitfall 20: React 18 Strict Mode Double-Rendering WebSocket Connections

**What goes wrong:**
In development, React 18 Strict Mode renders components twice, causing WebSocket connections to be established twice. The second connection receives duplicate messages, or the first connection is abandoned without clean closure, creating a ghost connection on the server.

**How to avoid:** Use a ref-based singleton pattern for WebSocket connections. Initialize connections outside the render cycle (in `useEffect` with cleanup). Use Zustand to manage connection state rather than component-local state.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Single Zustand store for all state | Fast to implement | Re-render storms, merge conflicts, unmaintainable types | Prototype only -- never past Phase 1 |
| Skip MCP transport detection, hardcode Streamable HTTP | Simpler client code | Breaks against legacy MCP servers in production | Never -- implement detection from day one |
| Use `operator.add` instead of `add_messages` for messages | Simpler reducer import | Loses message ID tracking, breaks human-in-the-loop updates | Never for messages field |
| Run skills in-process | No Docker overhead | Security vulnerabilities, resource contention | Development only -- sandbox for staging/production |
| Skip vector DB sync on every message write | Faster response times | Memory drift, stale retrieval results | Acceptable if reconciliation job runs within 60 seconds |
| Use `.invoke()` instead of `.ainvoke()` in async handlers | Faster to write | Event loop blocking under load | Never in production |
| Hard-code LLM provider settings | Quick setup | Provider lock-in, migration pain | Prototype only |
| Skip checkpoint persistence for agent state | Simpler architecture | Cannot resume interrupted conversations | MVP acceptable if acknowledged as debt |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| LangChain Chat Models | Accessing `additional_kwargs` for tool calls | Use normalized `tool_calls` property |
| LangGraph + FastAPI | Running graph `.invoke()` in async endpoint | Use `.ainvoke()` or `.astream_events()` |
| MCP + WebSocket | Blocking MCP tool calls during WebSocket streaming | Use async MCP client, stream tool results |
| Qdrant + LangChain | Creating collection without matching embedding dimensions | Validate dimensions on startup, pin embedding model |
| Celery + Redis | Sharing Redis connection pool between cache and Celery broker | Use separate Redis databases (db 0 for cache, db 1 for broker) |
| MinIO + Skills | Downloading skill packages synchronously during agent execution | Download asynchronously before agent starts |
| JWT + WebSocket | Validating JWT only on HTTP upgrade, not on messages | Validate token on upgrade AND periodically during connection |
| LangGraph + PostgreSQL | Using checkpoint serializer with non-JSON-serializable state | Use TypedDict state, keep Pydantic for validation only |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded message history in AgentState | Agent slows down, memory grows per conversation | Implement sliding window or summarization after N messages | 50+ messages per conversation |
| Sequential MCP tool calls | Tool execution time linear in number of tools | Parallelize independent tool calls, cache tool schemas | 5+ tool calls per agent turn |
| Full vector DB query on every message | Response latency increases with knowledge base size | Implement hybrid search with metadata filters, cache frequent queries | 100K+ documents in vector DB |
| WebSocket message queue without backpressure | Server memory spikes, messages dropped | Implement bounded queues with backpressure signaling | 100+ concurrent connections streaming simultaneously |
| No connection pooling for Redis/PostgreSQL | Connection exhaustion under load | Use connection pools with proper min/max sizing | 50+ concurrent agent executions |
| Embedding computation on every document write | Write throughput bottlenecked by embedding API | Batch embedding requests, use async embedding pipeline | 100+ document writes per minute |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| MCP server bound to 0.0.0.0 | DNS rebinding attacks, unauthorized access | Bind to 127.0.0.1, validate Origin headers |
| Skills with unrestricted imports | Arbitrary code execution, data exfiltration | Import allowlist, Docker sandbox |
| JWT secret in environment variables without rotation | Token forgery if secret leaks | Use secret management service, rotate regularly |
| No rate limiting on WebSocket messages | DoS via message flooding | Implement per-connection and per-user rate limits |
| Tool call results logged with sensitive data | Data leakage through logs | Sanitize tool results before logging, use structured logging with PII redaction |
| API keys for LLM providers in frontend code | Key theft, unauthorized usage | Backend proxy for all LLM calls, never expose keys to frontend |
| No input sanitization on agent prompts | Prompt injection attacks | Implement input validation, use prompt templates, add guardrails |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No streaming during agent thinking | User sees blank screen for 5-30 seconds, thinks app is broken | Stream thinking events ("Analyzing your request...", "Planning steps...") |
| No progress indication for tool calls | User does not know agent is executing tools | Show tool call status with expandable details |
| Agent error shown as raw exception | Users see technical error messages they cannot act on | Show friendly error with retry option, log technical details server-side |
| No conversation history persistence | Users lose all conversations on page refresh | Persist conversations to backend, load on reconnect |
| Skill configuration requires technical knowledge | Non-technical users cannot customize agent behavior | Provide visual configuration UI with sensible defaults |

## "Looks Done But Isn't" Checklist

- [ ] **Agent streaming:** Often missing proper `astream_events` integration -- verify chunks arrive token-by-token in the browser network tab
- [ ] **MCP tool discovery:** Often works in demo but fails against real external MCP servers -- verify with at least 3 different server implementations
- [ ] **Memory persistence:** Often works for short conversations but loses context after Redis restart -- verify vector DB is authoritative source for long-term memory
- [ ] **Skill sandboxing:** Often appears sandboxed but shares filesystem with host -- verify with a skill that attempts to read `/etc/passwd`
- [ ] **WebSocket reconnection:** Often reconnects but loses in-flight agent state -- verify agent execution resumes or restarts cleanly after reconnect
- [ ] **Multi-LLM switching:** Often works for text but breaks for tool calls -- verify tool call format is correct after switching providers
- [ ] **RBAC permissions:** Often works for happy path but misses edge cases (admin viewing other user's conversations) -- verify with role matrix test
- [ ] **Celery task monitoring:** Often runs tasks but silently fails without monitoring -- verify dead letter queue and task failure alerts work

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| State reducer misconfiguration | HIGH | Redefine state schema, migrate all checkpointed conversations, rewrite all node return values |
| Monolithic Zustand store | MEDIUM | Extract slices one at a time, update all component selectors, maintain backwards compatibility |
| MCP transport hardcoded to SSE | LOW | Add transport detection layer, test against both transport types |
| No RemainingSteps in agent graph | MEDIUM | Add field to state, update reflect/plan conditional edges, test recursion scenarios |
| Skills running in-process | HIGH | Containerize all skills, update skill loader, implement container orchestration |
| JWT-only-on-upgrade validation | LOW | Add periodic validation to WebSocket message handler |
| Sync blocking in async endpoints | LOW | Replace `.invoke()` with `.ainvoke()` throughout, add linter rule to enforce |
| Memory tier drift | MEDIUM | Implement reconciliation job, backfill vector DB from Redis, add sync checks |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Recursion limit surprises | Phase 1: Agent Engine | Test with a query that triggers 5+ reflect cycles |
| State reducer misconfiguration | Phase 1: Agent Engine | Assert message count after multi-node execution |
| MCP transport incompatibility | Phase 2: MCP Integration | Test against both Streamable HTTP and legacy SSE servers |
| MCP DNS rebinding | Phase 2: MCP Integration | Security audit of MCP server binding and Origin validation |
| Streaming chain breakage | Phase 1: Agent Engine | Verify token-by-token chunks arrive in WebSocket |
| WebSocket lifecycle mismanagement | Phase 3: Frontend + WebSocket | Kill client mid-stream, verify server cleans up |
| Zustand monolithic store | Phase 3: Frontend | Review store structure before building any UI |
| Three-tier memory drift | Phase 2: Memory System | Write to Redis and vector DB, read from both, compare |
| Skill sandbox escapes | Phase 4: Skill System | Test with skill that attempts filesystem access |
| LLM provider abstraction leaks | Phase 1: Agent Engine | Integration test against 2+ providers from day one |
| FastAPI sync blocking | Phase 1: Agent Engine | Load test with 10 concurrent requests, verify no stalls |
| JWT refresh race condition | Phase 5: Security | Simulate concurrent token refresh from same session |

## Sources

- LangGraph Graph API overview: https://docs.langchain.com/oss/python/langgraph/graph-api (MEDIUM confidence -- official docs, fetched 2026-03-28)
- MCP Transports specification: https://modelcontextprotocol.io/docs/concepts/transports (HIGH confidence -- official MCP spec)
- LangChain Streaming How-to: https://python.langchain.com/docs/how_to/streaming/ (HIGH confidence -- official LangChain docs)
- Zustand TypeScript Guide: https://zustand.docs.pmnd.rs/guides/typescript (HIGH confidence -- official Zustand docs)
- NextFlow PROJECT.md: `.planning/PROJECT.md` (project context for architecture decisions)

---
*Pitfalls research for: Universal Agent Platform (NextFlow)*
*Researched: 2026-03-28*
