# Architecture Patterns

**Domain:** Universal Agent Platform (LangGraph + MCP + FastAPI)
**Researched:** 2026-03-28

## Recommended Architecture

NextFlow follows a layered microservices architecture with a clear separation between the presentation layer (React SPA), the API gateway (FastAPI), the orchestration engine (LangGraph), and the data/storage layer. The Agent Engine is the heart of the system -- every user request flows through it.

```
                                    +-------------------+
                                    |   React SPA       |
                                    |  (Vite + shadcn)  |
                                    +--------+----------+
                                             |
                              REST API (CRUD) | WebSocket (streaming)
                                             |
                                    +--------v----------+
                                    |   FastAPI Gateway  |
                                    |  + JWT/RBAC Auth   |
                                    +--------+----------+
                                             |
                          +------------------+------------------+
                          |                  |                  |
                   +------v------+   +-------v------+   +------v------+
                   | Agent       |   | Skill        |   | MCP Manager |
                   | Engine      |   | Manager      |   |             |
                   | (LangGraph) |   |              |   |             |
                   +------+------+   +-------+------+   +------+------+
                          |                  |                  |
                   +------v------+   +-------v------+   +------v------+
                   | Tool        |<--+   Sandbox     |   | MCP Clients |
                   | Registry    |   |   Executor    |   | (multi-SSE) |
                   +------+------+   +---------------+   +------+------+
                          |                                     |
                   +------v-------------------------------------v------+
                   |              Memory System                        |
                   |  Working (State) | Short-term (Redis) | Long-term |
                   |                  |                    | (Vector)  |
                   +------+-----------+----------+---------+-----------+
                          |                      |         |
                   +------v------+   +-----------v--+  +---v--------+
                   | PostgreSQL  |   |    Redis     |  | Qdrant/    |
                   | (business)  |   | (cache/sess) |  | Milvus     |
                   +-------------+   +--------------+  +------------+
                                                             |
                                                    +--------v--------+
                                                    |     MinIO       |
                                                    | (files/skills)  |
                                                    +-----------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | Technology |
|-----------|---------------|-------------------|------------|
| **React SPA** | UI rendering, user interaction, real-time message display | FastAPI Gateway (REST + WS) | React 18, TypeScript, Vite, shadcn/ui, Zustand |
| **FastAPI Gateway** | Request routing, authentication, WebSocket lifecycle, API surface | Agent Engine, Skill Manager, MCP Manager, User Service | Python, FastAPI, PyJWT |
| **Agent Engine** | LangGraph StateGraph workflow: Analyze -> Plan -> Execute -> Reflect -> Respond. State persistence via checkpointer. Streaming via v2 StreamPart. | Tool Registry, Memory System, FastAPI Gateway | Python, LangGraph, LangChain |
| **Skill Manager** | Skill lifecycle (register, load, enable/disable, hot-update), package validation, metadata storage | Sandbox Executor, Tool Registry, MinIO, PostgreSQL | Python |
| **MCP Manager** | MCP server registration, connection lifecycle, tool discovery aggregation, health monitoring | MCP Clients, Tool Registry, PostgreSQL | Python, MCP SDK |
| **MCP Clients** | 1:1 connections to external MCP servers via Streamable HTTP or stdio. JSON-RPC 2.0 protocol. | MCP Manager, Tool Registry | Python, MCP SDK |
| **Tool Registry** | Unified tool namespace merging built-in tools, skill-exposed tools, and MCP-discovered tools. JSON Schema validation. Routes invocations to correct backend. | Agent Engine, Skill Manager, MCP Manager | Python |
| **Sandbox Executor** | Isolated skill execution (Docker/gVisor). Resource limits, timeout enforcement, output capture. | Skill Manager, Tool Registry | Docker, Python |
| **Memory System** | Three-layer memory coordination. Working memory in AgentState (LangGraph State). Short-term in Redis (per-thread context windows). Long-term in vector DB (cross-thread semantic search via LangGraph Store). | Agent Engine, PostgreSQL, Redis, Qdrant/Milvus | LangGraph Store, Redis, Qdrant |
| **User Service** | Authentication (JWT), authorization (RBAC), user profiles, conversation history management | FastAPI Gateway, PostgreSQL | Python, SQLAlchemy |
| **Task Queue** | Async processing for long-running tasks (skill packaging, batch operations, report generation) | FastAPI Gateway, Skill Manager, PostgreSQL | Celery, Redis |

### Data Flow

**Primary conversation flow (the critical path):**

```
User types message
       |
       v
React SPA sends via WebSocket
       |
       v
FastAPI Gateway authenticates JWT, resolves user/session
       |
       v
Gateway creates/retrieves LangGraph thread (thread_id = session_id)
       |
       v
Agent Engine receives message as HumanMessage in State
       |
       v
StateGraph executes: START -> Analyze -> Plan -> Execute -> Reflect -> Respond -> END
       |                                                          |
       |  During Execute node:                                    |
       |  - Tool Registry resolves tool_name to backend           |
       |  - Routes to built-in / skill / MCP as appropriate       |
       |  - Each tool_call streams back tool_call event           |
       |  - Each tool_result streams back tool_result event       |
       |                                                          |
       |  During all nodes:                                       |
       |  - Memory System injects context (short + long term)     |
       |  - Checkpointer saves state at each super-step           |
       |  - StreamPart events flow back via WebSocket             |
       |
       v
Final response streamed as chunk + done events
       |
       v
React SPA renders: thinking bubbles, tool calls, streamed text, final answer
```

**Event streaming detail (WebSocket):**

The Agent Engine uses LangGraph's v2 streaming protocol. Each StreamPart has shape `{type, ns, data}` where:
- `type` = `values` | `updates` | `messages` | `custom` | `checkpoints` | `tasks` | `debug`
- `ns` = subgraph namespace (for nested graph routing)
- `data` = payload specific to type

The FastAPI gateway maps these to application-level WebSocket events:

| LangGraph StreamPart | WebSocket Event | Direction | Purpose |
|---------------------|-----------------|-----------|---------|
| `custom` (via `get_stream_writer()`) | `thinking` | Server -> Client | Agent reasoning trace |
| `messages` (tool call delta) | `tool_call` | Server -> Client | Tool being invoked |
| `messages` (tool result) | `tool_result` | Server -> Client | Tool execution result |
| `messages` (AIMessageChunk) | `chunk` | Server -> Client | Streamed response text |
| `values` (final state) | `done` | Server -> Client | Workflow complete, final state |

**Memory retrieval flow:**

```
Analyze node starts
       |
       v
1. Read working memory from AgentState (messages, plan, scratchpad)
       |
       v
2. Query short-term memory (Redis) by thread_id -> recent conversation summary
       |
       v
3. Query long-term memory (LangGraph Store) by namespace + semantic search
   - Store.search(namespace=("users", user_id, "memories"), query=user_message)
   - Returns ranked memories with relevance scores
       |
       v
4. Inject all context into LLM prompt as system/user messages
       |
       v
5. After response, extract learnings -> Store.put() for cross-thread persistence
```

**Skill loading flow:**

```
Admin uploads skill package (ZIP) via REST API
       |
       v
Skill Manager validates package (manifest, entry point, permissions)
       |
       v
Package stored in MinIO (binary), metadata in PostgreSQL
       |
       v
On enable: Sandbox Executor provisions container with skill dependencies
       |
       v
Skill registers its tools with Tool Registry (name, schema, handler)
       |
       v
Agent Engine can now route tool calls to this skill via Tool Registry
```

**MCP server connection flow:**

```
Admin registers MCP server (URL, transport type) via REST API
       |
       v
MCP Manager creates MCP Client instance (1:1 with server)
       |
       v
Client connects via Streamable HTTP (HTTP POST + SSE for responses)
       |
       v
Client calls tools/list -> receives tool definitions with JSON Schema
       |
       v
MCP Manager registers discovered tools in Tool Registry (prefixed by server name)
       |
       v
Agent Engine routes tool calls: registry resolves "mcp__server__tool" -> MCP Client -> JSON-RPC call
       |
       v
Health check: periodic ping, auto-reconnect on failure, status in PostgreSQL
```

## Patterns to Follow

### Pattern 1: LangGraph StateGraph for Agent Orchestration
**What:** Define the agent workflow as a directed graph where each node is a pure function `(State) -> Partial[State]` and edges (including conditional) control flow. State is a TypedDict or Pydantic model. Reducers control how updates merge (e.g., `add_messages` for message history with ID-based dedup).

**When:** Every agent workflow. This IS the Agent Engine.

**Example:**
```python
from langgraph.graph import StateGraph, START, END
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    plan: str
    scratchpad: str
    tools_to_call: list[dict]

def analyze(state: AgentState) -> dict:
    # LLM analyzes user intent, returns plan
    ...

def plan(state: AgentState) -> dict:
    # Break plan into tool calls
    ...

def execute(state: AgentState) -> dict:
    # Run tools, collect results
    ...

def reflect(state: AgentState) -> dict:
    # Evaluate results, decide if more steps needed
    ...

def should_continue(state: AgentState) -> str:
    if state["plan"] and needs_more_work(state):
        return "execute"
    return "respond"

builder = StateGraph(AgentState)
builder.add_node("analyze", analyze)
builder.add_node("plan", plan)
builder.add_node("execute", execute)
builder.add_node("reflect", reflect)
builder.add_node("respond", respond)

builder.add_edge(START, "analyze")
builder.add_edge("analyze", "plan")
builder.add_edge("plan", "execute")
builder.add_edge("execute", "reflect")
builder.add_conditional_edges("reflect", should_continue)
builder.add_edge("respond", END)

checkpointer = PostgresSaver.from_conn_string(DB_URI)
graph = builder.compile(checkpointer=checkpointer)
```

### Pattern 2: Orchestrator-Worker with Send API for Parallel Tool Execution
**What:** When the Plan node identifies multiple independent tool calls, use LangGraph's `Send` API to dynamically create parallel worker nodes, each with its own slice of state. Workers execute concurrently, and results are reduced back into the main state.

**When:** Multiple independent tool calls in the Execute phase.

**Example:**
```python
from langgraph.types import Send

def plan(state: AgentState) -> dict:
    tool_calls = identify_tool_calls(state)
    # Dynamically route each tool call to its own worker
    return {
        "tools_to_call": tool_calls,
        "__send__": [Send("tool_worker", {"tool_call": tc}) for tc in tool_calls]
    }

def tool_worker(state: dict) -> dict:
    result = execute_tool(state["tool_call"])
    return {"messages": [ToolMessage(content=result, tool_call_id=state["tool_call"]["id"])]}
```

### Pattern 3: Evaluator-Optimizer Loop for Complex Tasks
**What:** After the Reflect node evaluates execution results, if quality is insufficient, route back to Plan with feedback injected into state. The LLM sees its own critique and produces an improved plan. Use `Command(goto="plan")` to loop back.

**When:** Multi-step reasoning, complex tool orchestration where first attempt may fail.

**Example:**
```python
from langgraph.types import Command

def reflect(state: AgentState) -> Command:
    quality = evaluate_results(state)
    if quality.score < threshold:
        return Command(
            update={"scratchpad": f"Previous attempt scored {quality.score}. Feedback: {quality.feedback}"},
            goto="plan"
        )
    return Command(goto="respond")
```

### Pattern 4: Three-Layer Memory with LangGraph Store
**What:** Working memory lives in AgentState (ephemeral, per-invocation). Short-term memory uses LangGraph checkpointer keyed by thread_id (conversation history). Long-term memory uses LangGraph Store with semantic search for cross-thread knowledge.

**When:** All agent interactions. Memory retrieval happens at the start of Analyze node.

**Example:**
```python
from langgraph.store.base import BaseStore

def analyze(state: AgentState, *, store: BaseStore) -> dict:
    # Long-term: semantic search across all conversations for this user
    memories = store.search(
        namespace=("users", state["user_id"], "memories"),
        query=state["messages"][-1].content
    )
    # Short-term: already in state from checkpointer
    context = format_memories(memories)
    return {"scratchpad": context}

def respond(state: AgentState, *, store: BaseStore) -> dict:
    # Persist learnings for future conversations
    learnings = extract_learnings(state)
    store.put(
        namespace=("users", state["user_id"], "memories"),
        key=f"memory_{uuid4()}",
        value={"content": learnings, "type": "learning"}
    )
    return {"messages": [AIMessage(content=state["response"])]}
```

### Pattern 5: Unified Tool Registry with Strategy Routing
**What:** A single Tool Registry maintains a unified namespace of all available tools (built-in, skill-derived, MCP-discovered). Each tool entry contains its invocation strategy: direct function call, sandbox RPC, or MCP JSON-RPC. The Agent Engine only interacts with the registry, never with backends directly.

**When:** All tool invocations from the Execute node.

**Example:**
```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}

    def register(self, name: str, schema: dict, handler: ToolHandler):
        self._tools[name] = ToolEntry(name=name, schema=schema, handler=handler)

    async def invoke(self, name: str, params: dict) -> Any:
        entry = self._tools.get(name)
        if not entry:
            raise ToolNotFoundError(name)
        return await entry.handler.invoke(params)

class ToolHandler(Protocol):
    async def invoke(self, params: dict) -> Any: ...

class BuiltinHandler: ...    # Direct function call
class SkillHandler: ...      # Sandbox RPC via HTTP/gRPC
class MCPHandler: ...        # JSON-RPC via MCP Client
```

### Pattern 6: WebSocket Streaming with Backpressure
**What:** FastAPI WebSocket endpoint calls `graph.astream_events(input, config, version="v2")` and maps LangGraph StreamParts to application events. Use an async queue between the LangGraph stream and the WebSocket send to handle backpressure and allow clean disconnection.

**When:** Every streaming conversation.

**Example:**
```python
from fastapi import WebSocket

async def stream_agent_response(websocket: WebSocket, graph, user_input: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    stream_writer = get_stream_writer()

    async for event in graph.astream_events(
        {"messages": [HumanMessage(content=user_input)]},
        config,
        version="v2"
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            await websocket.send_json({
                "type": "chunk",
                "data": {"content": event["data"]["chunk"].content}
            })
        elif kind == "on_tool_start":
            await websocket.send_json({
                "type": "tool_call",
                "data": {"name": event["name"], "args": event["data"].get("input")}
            })
        # ... map other events
```

### Pattern 7: MCP Multi-Server Client Management
**What:** MCP Manager maintains a pool of MCP Client instances, each bound to one MCP server via Streamable HTTP transport. Tool discovery aggregates from all connected servers with namespacing (`server_name.tool_name`). Health checks use ping messages. Reconnection on transport failure with exponential backoff.

**When:** Always. Every registered MCP server gets a persistent client.

**Example:**
```python
class MCPManager:
    def __init__(self, tool_registry: ToolRegistry):
        self._clients: dict[str, MCPClient] = {}
        self._registry = tool_registry

    async def register_server(self, server_config: MCPServerConfig):
        client = MCPClient(server_config)
        await client.connect()
        tools = await client.list_tools()
        for tool in tools:
            namespaced_name = f"mcp__{server_config.name}__{tool.name}"
            self._registry.register(
                namespaced_name,
                schema=tool.inputSchema,
                handler=MCPHandler(client, tool.name)
            )
        self._clients[server_config.name] = client

    async def health_check_loop(self):
        for name, client in self._clients.items():
            if not await client.ping():
                await self._reconnect(name, client)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: LLM Direct in WebSocket Handler
**What:** Calling LLM APIs directly inside FastAPI route handlers without LangGraph orchestration.
**Why bad:** Loses state persistence, replay capability, streaming unification, and human-in-the-loop support. Turns the Agent Engine into ad-hoc procedural code.
**Instead:** Always route through the compiled LangGraph StateGraph. The graph provides checkpointing, streaming, and interrupt/resume for free.

### Anti-Pattern 2: Flat Tool Namespace Without Routing Strategy
**What:** Registering all tools (built-in, skill, MCP) as flat function references with no invocation strategy differentiation.
**Why bad:** Skill tools need sandbox isolation. MCP tools need JSON-RPC serialization. Built-in tools are direct calls. Mixing invocation patterns in the Execute node couples it to every backend type.
**Instead:** Tool Registry with strategy pattern. Each entry carries its handler type. Execute node calls `registry.invoke(name, params)` uniformly.

### Anti-Pattern 3: In-Memory State Without Checkpointing
**What:** Using `InMemorySaver` or no checkpointer in production, storing conversation state only in process memory.
**Why bad:** Server restart loses all conversations. Cannot scale horizontally (state not shared). No replay, no time travel, no human-in-the-loop.
**Instead:** `PostgresSaver` for production. Thread_id maps to session_id. Every super-step persisted.

### Anti-Pattern 4: Single LLM Client Without Routing
**What:** Hardcoding one LLM provider (e.g., only OpenAI) with no abstraction for model switching.
**Why bad:** Model lock-in. Cannot route different tasks to different models (e.g., cheap model for analysis, capable model for code generation). No fallback on provider outage.
**Instead:** LangChain's `BaseChatModel` abstraction. Router that selects model by task type, cost budget, or user preference. Fallback chain for resilience.

### Anti-Pattern 5: Synchronous Tool Execution in Agent Loop
**What:** Awaiting each tool call sequentially when multiple tools are independent.
**Why bad:** N independent tool calls take N * avg_latency instead of avg_latency. Poor user experience with long waits.
**Instead:** LangGraph `Send` API for parallel worker nodes. Async tool execution with `asyncio.gather` within the Execute node when tools are independent.

### Anti-Pattern 6: Unscoped Memory Retrieval
**What:** Dumping entire conversation history + all stored memories into every LLM call without relevance filtering.
**Why bad:** Token waste, increased latency, degraded LLM output quality from noise. Costs scale linearly with history.
**Instead:** Semantic search via LangGraph Store with relevance thresholds. Sliding window for short-term memory (last N messages or token-budgeted summary). Retrieve only what the current query needs.

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 100K+ users |
|---------|--------------|--------------|----------------|
| **WebSocket connections** | Single FastAPI process, in-memory connection map | Multiple FastAPI workers behind load balancer with sticky sessions or Redis pub/sub for cross-worker messaging | Dedicated WebSocket gateway (e.g., dedicated ASGI servers), Redis Streams for event distribution |
| **LangGraph execution** | Single process, `PostgresSaver` for state | Celery workers for long-running graphs, async execution for streaming graphs. Postgres connection pooling (pgbouncer) | Horizontally scaled LangGraph Server (managed) or custom worker fleet with shared PostgresSaver |
| **LLM API rate limits** | Unlikely to hit limits | Request queue with priority levels, rate limit tracking per provider, model fallback chains | Multi-provider load balancing, local model fallback (vLLM/Ollama) for overflow, token budget management per user tier |
| **MCP server connections** | Pool of persistent connections, negligible overhead | Connection pooling per server, lazy connect on first tool call, idle timeout | MCP gateway service with shared connection pool, gRPC internal routing |
| **Vector search (long-term memory)** | Single Qdrant/Milvus node, brute-force search | Indexed collections per tenant/user namespace, HNSW index tuning | Sharded vector DB, read replicas, embedding cache to avoid re-embedding common queries |
| **Skill sandbox execution** | Docker containers on same host, serial execution | Container pool with pre-warmed images, resource limits per skill | Kubernetes-based sandbox with auto-scaling, job queue with priority, GPU access for ML skills |
| **PostgreSQL** | Single instance adequate | Read replicas for queries, connection pooling, partitioned conversations table | Sharded by user_id, dedicated analytics replica, TimescaleDB for metrics |

## Build Order (Dependency-Aware)

Components must be built in this order because of hard dependencies:

```
Phase 1: Foundation (no dependencies)
  1.1 PostgreSQL schema (users, conversations, skills, mcp_servers, tools)
  1.2 Redis setup (session store, cache)
  1.3 FastAPI project skeleton (project structure, config, logging)
  1.4 JWT auth + RBAC middleware

Phase 2: Agent Engine Core (depends on 1.1, 1.3)
  2.1 LangGraph StateGraph definition (AgentState, nodes, edges)
  2.2 PostgresSaver checkpointer integration
  2.3 Basic LLM integration via LangChain (single model)
  2.4 Tool Registry skeleton (registration interface, built-in tools)

Phase 3: Communication Layer (depends on 2.1)
  3.1 REST API endpoints (CRUD for conversations, agents, settings)
  3.2 WebSocket endpoint with LangGraph streaming integration
  3.3 Event mapping (StreamPart -> WebSocket events)

Phase 4: Memory System (depends on 2.1, 2.2, 1.2)
  4.1 Qdrant/Milvus setup and collection schemas
  4.2 LangGraph Store integration for long-term memory
  4.3 Short-term memory manager (Redis-based conversation summaries)
  4.4 Context injection in Analyze node

Phase 5: MCP Integration (depends on 2.4)
  5.1 MCP Client implementation (Streamable HTTP transport)
  5.2 MCP Manager (server registration, tool discovery, health check)
  5.3 MCP tool registration in Tool Registry
  5.4 MCP admin API endpoints

Phase 6: Skill System (depends on 2.4, 1.3)
  6.1 Skill package format and validation
  6.2 MinIO integration for skill storage
  6.3 Sandbox executor (Docker-based isolation)
  6.4 Skill lifecycle management (upload, enable, disable, hot-update)
  6.5 Skill tool registration in Tool Registry

Phase 7: Frontend (can start in parallel with Phase 3, fully usable after Phase 3)
  7.1 Project setup (Vite + React 18 + TypeScript + shadcn/ui + Zustand)
  7.2 Auth UI (login/register)
  7.3 Conversation UI (message list, input, streaming display)
  7.4 Thinking/tool call visualization
  7.5 Agent configuration UI
  7.6 Skill management UI
  7.7 MCP management UI

Phase 8: Advanced Agent Patterns (depends on 2-6)
  8.1 Parallel tool execution via Send API
  8.2 Evaluator-optimizer loops for complex tasks
  8.3 Multi-LLM routing and fallback chains
  8.4 Human-in-the-loop interrupts
```

Key dependency rationale:
- Agent Engine (Phase 2) is the critical path -- everything else depends on it
- Tool Registry must exist before MCP and Skill systems can register their tools
- Memory System requires both the graph (for Store integration) and Redis (for short-term) to be ready
- Frontend can begin scaffold in parallel with backend work but needs REST/WS APIs (Phase 3) to become functional
- Advanced patterns (Phase 8) require all subsystems to be operational for end-to-end testing

## Sources

- LangGraph Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api (HIGH confidence -- official docs)
- LangGraph Workflow Patterns: https://docs.langchain.com/oss/python/langgraph/workflows-agents (HIGH confidence -- official docs)
- LangGraph Persistence & Store: https://docs.langchain.com/oss/python/langgraph/persistence (HIGH confidence -- official docs)
- LangGraph Streaming v2: https://docs.langchain.com/oss/python/langgraph/streaming (HIGH confidence -- official docs)
- MCP Architecture: https://modelcontextprotocol.io/docs/concepts/architecture (HIGH confidence -- official spec)
- MCP Transports: https://modelcontextprotocol.io/docs/concepts/transports (HIGH confidence -- official spec)
- MCP Tools: https://modelcontextprotocol.io/docs/concepts/tools (HIGH confidence -- official spec)
- MCP Resources: https://modelcontextprotocol.io/docs/concepts/resources (HIGH confidence -- official spec)
- Skill sandboxing patterns: MEDIUM confidence -- based on general container isolation best practices, not NextFlow-specific
- Multi-LLM routing: MEDIUM confidence -- LangChain router chains are documented but production patterns are community-derived
