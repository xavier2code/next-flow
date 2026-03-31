# Phase 2: Agent Engine Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 02-agent-engine-core
**Areas discussed:** Workflow Topology, LLM Provider Strategy, Tool Registry Design, AgentState Structure

---

## Workflow Topology

| Option | Description | Selected |
|--------|-------------|----------|
| 4-node linear (Analyze → Plan → Execute → Respond) | Simple reliable pipeline, Reflect deferred to v2 | ✓ |
| 5-node with Reflect loop | Higher complexity, evaluator-optimizer capability | |
| Configurable topology | Default 4-node, optional Reflect per agent config | |

**User's choice:** 4-node linear
**Notes:** Aligns with ROADMAP success criteria, Reflect explicitly in v2 ADVN-02

### Node Responsibility

| Option | Description | Selected |
|--------|-------------|----------|
| Single responsibility per node | Analyze=intent+context, Plan=LLM tool decisions, Execute=run tools, Respond=final answer | ✓ |
| Merged responsibility (3-node equivalent) | Fewer nodes but heavier per node | |

**User's choice:** Single responsibility per node

### Tool Execution Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential execution | One tool at a time, parallel deferred to v2 ADVN-01 | ✓ |
| Parallel tool execution | asyncio.gather for independent tools | |

**User's choice:** Sequential execution

### Conditional Routing

| Option | Description | Selected |
|--------|-------------|----------|
| Conditional skip of Execute | Plan node decides: tools needed → Execute, no tools → Respond directly | ✓ |
| Always traverse all nodes | Execute does nothing when no tools, simpler logic | |

**User's choice:** Conditional skip of Execute

### Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful degradation | Tool failures return ToolMessage, LLM explains in Respond | ✓ |
| Direct exception throwing | Errors propagate to global handler | |

**User's choice:** Graceful degradation

---

## LLM Provider Strategy

### Configuration Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Agent.model_config JSON | Per-agent provider/model/temperature config, factory creates ChatModel | ✓ |
| Global default config | All agents share one model via Settings | |
| Independent models table | Database table for model definitions, FK from Agent | |

**User's choice:** Agent.model_config JSON

### Instance Creation

| Option | Description | Selected |
|--------|-------------|----------|
| Simple factory function | `get_llm(config)` returns ChatModel based on provider string | ✓ |
| LLMRegistry class | Manages instances with caching, health checks | |

**User's choice:** Simple factory function

### API Key Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Environment variables | OPENAI_API_KEY, OLLAMA_BASE_URL in Settings/.env | ✓ |
| Database (encrypted) | Per-user API keys, more flexible but complex | |

**User's choice:** Environment variables

### Default Provider

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable defaults | DEFAULT_PROVIDER and DEFAULT_MODEL in Settings | ✓ |
| Ollama default | Developer-friendly, no API cost | |
| OpenAI default | Production-ready, needs API key | |

**User's choice:** Configurable defaults

### Streaming

| Option | Description | Selected |
|--------|-------------|----------|
| Enable streaming by default | streaming=True in ChatModel, ready for Phase 3 WebSocket | ✓ |
| Add streaming in Phase 3 | Non-streaming first, refactor later | |

**User's choice:** Enable streaming by default

---

## Tool Registry Design

### Storage

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory registry + Protocol | Python dict with Protocol-based handlers, lightweight | ✓ |
| Database registry | Query tools table on each invocation | |
| Hybrid (memory + DB) | Load from DB at startup, sync on changes | |

**User's choice:** In-memory registry + Protocol

### Built-in Tools

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (1 tool for testing) | get_current_time or echo, validates full chain | ✓ |
| Practical set (3-5 tools) | time, calculator, web search, etc. | |

**User's choice:** Minimal built-in tool set

### Registration Method

| Option | Description | Selected |
|--------|-------------|----------|
| Decorator registration | `@tool_registry.register`, tool definition + registration together | ✓ |
| Config file registration | JSON/YAML tool definitions, loaded at startup | |

**User's choice:** Decorator registration

### Tool-Agent Binding

| Option | Description | Selected |
|--------|-------------|----------|
| Global sharing | All agents can use all registered tools | ✓ |
| Per-agent configuration | Agent.model_config lists available tools | |

**User's choice:** Global sharing

---

## AgentState Structure

### Field Set

| Option | Description | Selected |
|--------|-------------|----------|
| Basic: messages, plan(str), scratchpad(str), remaining_steps(int) | Core fields per AGNT-02 and AGNT-06 | ✓ |
| Extended: + llm_config(dict), tools(list) | Runtime config cached in state | |

**User's choice:** Basic field set

### Field Types

| Option | Description | Selected |
|--------|-------------|----------|
| Both plan and scratchpad as str | Simple strings, plan=step description, scratchpad=reasoning | ✓ |
| plan as JSON, scratchpad as str | Structured plan with steps, simple scratchpad | |

**User's choice:** Both str

### State Type

| Option | Description | Selected |
|--------|-------------|----------|
| TypedDict | LangGraph standard, best add_messages compatibility | ✓ |
| Pydantic BaseModel | Stronger validation, extra integration work | |

**User's choice:** TypedDict

### Runtime Context (user_id, thread_id)

| Option | Description | Selected |
|--------|-------------|----------|
| Via config["configurable"] | LangGraph config pattern, state stays pure business data | ✓ |
| As state fields | Stored in AgentState, provided in input | |

**User's choice:** Via config

---

## Claude's Discretion

- Exact node function implementations and LLM prompt templates
- PostgresSaver connection setup and checkpoint table migration
- Tool Registry internal data structures
- Error message formatting
- Specific built-in tool choice (get_current_time, echo, or similar)

## Deferred Ideas

None — discussion stayed within phase scope
