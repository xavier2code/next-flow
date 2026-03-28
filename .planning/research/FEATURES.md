# Feature Research

**Domain:** Universal Agent Platform (通用Agent平台)
**Researched:** 2026-03-28
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-turn conversation | Every chat product has this; users expect persistent message threads with context | MEDIUM | Store messages in PostgreSQL, render conversation list + message history. Zustand for client state. |
| Streaming response (SSE/WebSocket) | Users will not wait for full responses; typing animation is the baseline UX | MEDIUM | WebSocket with chunk/done events. LangGraph supports stream modes (values, updates, messages). |
| Multi-LLM model switching | Users expect to choose between GPT-4, Claude, local models from a dropdown | MEDIUM | LangChain abstraction layer. Provider configs stored per-agent. OpenAI/Azure/Anthropic/Ollama adapters. |
| User authentication (JWT) | Any platform with user data requires login/session management | LOW | FastAPI + python-jose. Register/login/logout, token refresh. Standard pattern. |
| Agent configuration UI | Users expect to set model, system prompt, temperature from a settings panel | LOW | React form with Zustand store. CRUD against agent config API. |
| Conversation history management | Users expect to browse, search, rename, delete past conversations | LOW | List view + detail view. Pagination. Soft delete. |
| Markdown rendering in responses | LLM outputs are markdown; failing to render code blocks, tables, lists is broken | LOW | react-markdown + rehype/remark plugins. Syntax highlighting via shiki. |
| Basic error handling & retry | LLM calls fail; users expect graceful error messages, not white screens | LOW | Toast notifications, retry button on failed messages. Exponential backoff on API calls. |
| Responsive web UI | Users may access from tablets or narrow browser windows | LOW | shadcn/ui + Tailwind responsive utilities. Mobile-friendly layout, not native app. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| LangGraph agent workflow (Analyze-Plan-Execute-Reflect-Respond) | Structured multi-step reasoning produces higher-quality results than single-shot prompting; enables complex task decomposition | HIGH | LangGraph StateGraph with conditional edges and loops. Checkpointing for resumability. Each node is a distinct processing step. |
| MCP protocol integration (multi-server) | Standard tool protocol avoids vendor lock-in; any MCP-compatible service connects without custom code | HIGH | MCP client supporting Streamable HTTP transport. Tool discovery via tools/list, invocation via tools/call. Dynamic tool registration when servers connect/disconnect. |
| Three-layer memory architecture | Short-term (Redis) + Long-term (vector DB) + Working (AgentState) gives agents persistent knowledge without context window bloat | HIGH | Redis for recent conversation context. Qdrant/Milvus for semantic search over accumulated knowledge. AgentState carries current-task working memory through LangGraph graph. |
| Skill system with dynamic loading | Plugin architecture lets users extend agent capabilities without code changes; enables a skill marketplace | HIGH | Sandboxed skill execution. Hot-reload without agent restart. Skill manifest with metadata (name, description, required tools, permissions). |
| Tool registry (unified) | Single registry for built-in tools + skills + MCP tools gives agents consistent tool access regardless of source | MEDIUM | Abstract Tool interface. Registry service resolves tool by name, delegates to correct backend (internal/skill/MCP). Tool metadata includes input schema, annotations (readOnly, destructive). |
| Thinking process visualization | Showing agent reasoning steps builds user trust and enables debugging of agent behavior | MEDIUM | WebSocket thinking events streamed from LangGraph nodes. Collapsible "thinking" sections in chat UI. Separate from final response. |
| Tool call/result streaming | Users see which tools are being called and their results in real-time, making agent actions transparent | MEDIUM | WebSocket tool_call and tool_result events. Render as inline cards showing tool name, inputs, outputs. Part of LangGraph custom streaming via get_stream_writer(). |
| RBAC permission system | Enterprise readiness; different roles for admin/developer/viewer with scoped agent and tool access | MEDIUM | Role-based access control on API endpoints. Agent ownership. Tool permission scoping. Admin vs user vs viewer roles. |
| Agent marketplace / skill marketplace | Community ecosystem where users share and install agent configurations and skills | HIGH | Defer to v2. Requires packaging format, versioning, review system, install/uninstall lifecycle. |
| Knowledge base (RAG) | Upload documents, auto-chunk and embed, agents retrieve relevant context during conversations | HIGH | Document ingestion pipeline (chunking + embedding). Qdrant/Milvus storage. Retrieval integrated into LangGraph workflow as a tool or pre-processing node. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Visual workflow builder (drag-and-drop) | Dify popularized this; non-technical users want to design agent flows visually | Massive engineering investment (200+ hours for a usable DAG editor); most users end up using templates anyway; version control and debugging of visual graphs is painful; LangGraph's graph is best expressed in code | Provide well-documented agent templates (YAML/JSON config) that cover common patterns: single-turn, multi-step, RAG, tool-using. Let power users define custom graphs in Python. |
| Voice interaction | "ChatGPT has voice mode" | Significant additional complexity (STT/TTS pipelines, real-time audio streaming, latency requirements); explicitly out of scope per PROJECT.md | Text-first. Defer voice to v2+ when core platform is stable. |
| Multi-tenant isolation | "We want to sell this to enterprises" | Adds data isolation, billing, tenant-scoped resources, audit logging across every service; premature for v1 | Single-tenant v1. Design data model with tenant_id fields from day one, but do not enforce isolation logic until v2. |
| Mobile native app | "Users want an app" | Doubles frontend engineering; explicitly out of scope per PROJECT.md | Responsive PWA. Mobile browser experience is sufficient for v1. |
| Real-time collaborative editing | "Multiple users editing an agent config simultaneously" | Requires CRDT or OT, presence system, conflict resolution; complexity disproportionate to value | Standard optimistic locking. "Last save wins" with conflict notification. |
| Built-in LLM fine-tuning | "Train custom models" | Entirely different engineering domain; GPU infrastructure, training pipelines, evaluation | Support local model endpoints (Ollama/vLLM). Let users bring their own fine-tuned models. |
| Low-code/no-code agent builder | "Non-technical users should build agents" | Dumbs down capabilities; power users feel constrained; maintaining both code and visual interfaces doubles maintenance | Template library + code-based customization. Clear documentation. Agent configuration UI handles 80% of cases. |

## Feature Dependencies

```
[Multi-LLM Model Switching]
    └──requires──> [LangChain Abstraction Layer]
                       └──requires──> [Agent Configuration UI]

[LangGraph Agent Workflow]
    └──requires──> [Multi-LLM Model Switching]
    └──requires──> [Tool Registry (Unified)]
    └──requires──> [WebSocket Streaming]

[Tool Registry (Unified)]
    └──requires──> [Abstract Tool Interface]
    └──integrates──> [MCP Protocol Integration]
    └──integrates──> [Skill System]

[MCP Protocol Integration]
    └──requires──> [Tool Registry (Unified)]
    └──requires──> [WebSocket Streaming] (for tool_call/result events)

[Three-Layer Memory]
    └──requires──> [Redis (Short-term)]
    └──requires──> [Qdrant/Milvus (Long-term)]
    └──requires──> [LangGraph Agent Workflow] (Working memory via AgentState)

[Skill System with Dynamic Loading]
    └──requires──> [Tool Registry (Unified)]
    └──requires──> [Sandboxed Execution Environment]
    └──enhanced_by──> [Skill Marketplace] (v2)

[Knowledge Base (RAG)]
    └──requires──> [Three-Layer Memory] (vector storage)
    └──requires──> [Document Ingestion Pipeline]
    └──integrates──> [LangGraph Agent Workflow] (as retrieval node)

[Thinking Process Visualization]
    └──requires──> [WebSocket Streaming]
    └──requires──> [LangGraph Agent Workflow] (stream from nodes)

[RBAC Permission System]
    └──requires──> [User Authentication (JWT)]
    └──scopes──> [Agent Configuration UI]
    └──scopes──> [Tool Registry (Unified)]
    └──scopes──> [MCP Protocol Integration]

[Streaming Response (SSE/WebSocket)]
    └──required_by──> [Tool Call/Result Streaming]
    └──required_by──> [Thinking Process Visualization]
    └──required_by──> [LangGraph Agent Workflow] (for live updates)
```

### Dependency Notes

- **LangGraph Agent Workflow requires Multi-LLM + Tool Registry + WebSocket:** The agent engine orchestrates LLM calls, invokes tools, and streams progress -- all three must exist first.
- **Tool Registry is the integration backbone:** Both MCP tools and Skills register into the unified Tool Registry. The agent engine only interacts with the registry, never directly with MCP or Skills. This decouples the agent from tool sources.
- **Three-Layer Memory requires LangGraph Workflow:** Working memory (AgentState) is inherently tied to the LangGraph graph execution. The memory layers cannot be built independently of the workflow engine.
- **MCP Integration requires Tool Registry:** MCP tools are discovered dynamically and must be registered into the unified Tool Registry for the agent to access them.
- **Thinking/Tool streaming requires WebSocket:** These real-time events are delivered via WebSocket. The streaming infrastructure must be in place before any progress visualization can work.
- **RBAC scopes all managed resources:** Permission checks apply to agents, tools, and MCP servers. Must be designed after those resources exist.
- **Knowledge Base (RAG) requires vector storage and ingestion:** Depends on the vector DB layer from Three-Layer Memory and a document processing pipeline. Can be added after core memory is working.
- **Skill Marketplace enhances but does not block Skill System:** Skills work without a marketplace (manually installed). Marketplace is a v2 distribution layer.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what is needed to validate the concept.

- [ ] Multi-turn conversation with streaming -- Core value prop; without conversation there is no product
- [ ] Multi-LLM model switching (OpenAI + at least one local model via Ollama) -- Validates LangChain abstraction works
- [ ] LangGraph agent workflow (Analyze-Plan-Execute-Respond, skip Reflect for v1) -- The core differentiating engine
- [ ] Tool Registry with built-in tools (web search, code interpreter) -- Proves tool invocation works end-to-end
- [ ] MCP client (connect to 1-2 MCP servers, discover and call tools) -- Validates MCP integration
- [ ] User authentication (JWT, register/login) -- Required for any multi-user platform
- [ ] Agent configuration UI (model selection, system prompt, temperature) -- Users must be able to configure agents
- [ ] WebSocket streaming (chunk, done, tool_call, tool_result events) -- Required for real-time UX
- [ ] Markdown rendering with code highlighting -- Table stakes for LLM output
- [ ] Basic conversation history (list, create, delete) -- Users need to manage conversations
- [ ] Short-term memory (Redis, last N messages) -- Minimum memory for coherent multi-turn

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Reflect node in agent workflow (evaluator-optimizer pattern) -- Enhances output quality after basic flow works
- [ ] Thinking process visualization -- Builds trust once agent is producing useful results
- [ ] Three-layer memory with long-term (vector DB) -- Adds persistent knowledge after short-term is validated
- [ ] Skill system with dynamic loading -- Extends agent capabilities once core tools work
- [ ] RBAC with admin/developer/viewer roles -- Enterprise readiness after individual users are validated
- [ ] MCP multi-server management UI -- Scales MCP from 1-2 servers to many
- [ ] Knowledge base (RAG) with document upload -- High-value feature once vector storage is in place
- [ ] Agent templates library -- Reduces onboarding friction after patterns are proven

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Skill marketplace -- Requires community, review system, packaging format
- [ ] Visual workflow builder -- Massive engineering investment; validate that templates are insufficient first
- [ ] Multi-tenant isolation -- Enterprise feature; design tenant_id early but do not enforce until needed
- [ ] Advanced analytics / usage dashboards -- Useful for admins but not core to agent execution
- [ ] Custom LangGraph graph editor (code-based, not visual) -- Power user feature after templates cover 80%
- [ ] A/B testing of agent configurations -- Optimization feature after baseline is established

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Multi-turn conversation with streaming | HIGH | MEDIUM | P1 |
| Multi-LLM model switching | HIGH | MEDIUM | P1 |
| LangGraph agent workflow | HIGH | HIGH | P1 |
| Tool Registry (unified) | HIGH | MEDIUM | P1 |
| MCP protocol integration | HIGH | HIGH | P1 |
| User authentication (JWT) | HIGH | LOW | P1 |
| Agent configuration UI | HIGH | LOW | P1 |
| WebSocket streaming events | HIGH | MEDIUM | P1 |
| Markdown rendering | HIGH | LOW | P1 |
| Conversation history | MEDIUM | LOW | P1 |
| Short-term memory (Redis) | HIGH | LOW | P1 |
| Thinking process visualization | MEDIUM | MEDIUM | P2 |
| Three-layer memory (full) | HIGH | HIGH | P2 |
| Skill system with dynamic loading | MEDIUM | HIGH | P2 |
| RBAC permission system | MEDIUM | MEDIUM | P2 |
| Knowledge base (RAG) | HIGH | HIGH | P2 |
| Tool call/result streaming UI | MEDIUM | MEDIUM | P2 |
| MCP multi-server management | MEDIUM | MEDIUM | P2 |
| Agent templates library | MEDIUM | LOW | P2 |
| Skill marketplace | MEDIUM | HIGH | P3 |
| Visual workflow builder | LOW | VERY HIGH | P3 |
| Multi-tenant isolation | LOW | HIGH | P3 |
| Advanced analytics | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch -- core agent platform functionality
- P2: Should have, add when possible -- completes the platform
- P3: Nice to have, future consideration -- ecosystem and enterprise features

## Competitor Feature Analysis

| Feature | Dify | Open WebUI | LobeChat | NextFlow Approach |
|---------|------|------------|----------|-------------------|
| Agent workflow engine | Visual DAG builder, prompt IDE | Basic chaining | Plugin-based with tool calling | LangGraph stateful graph (code-first, not visual) |
| Multi-LLM support | 50+ providers, model management | Ollama-first, OpenAI compatible | Multi-provider with uniform API | LangChain abstraction; OpenAI + Anthropic + Ollama initially |
| Tool/plugin system | Custom tools + API integration | Functions, Ollama tools | Plugin system with marketplace | Unified Tool Registry: built-in + Skills + MCP tools |
| MCP support | Community plugins, no native MCP | Emerging MCP support | MCP integration via plugins | Native MCP client from day one; multi-server tool discovery |
| Memory/knowledge | Dataset-based RAG, vector storage | Document upload, basic RAG | File-based knowledge per chat | Three-layer architecture: short-term (Redis) + long-term (vector DB) + working (AgentState) |
| Streaming | SSE streaming | SSE streaming | SSE streaming | WebSocket with structured events (thinking/tool_call/tool_result/chunk/done) |
| User management | Workspace-based, RBAC | Admin/user roles | Basic auth or OIDC | JWT + RBAC (admin/developer/viewer) |
| Skill marketplace | Plugin marketplace | Open WebUI community | Plugin marketplace (100+) | Defer to v2; focus on skill system first |
| Deployment | Docker, cloud, self-hosted | Docker, K8s | Docker, Vercel | Docker containers, K8s ready |
| Open source | Yes (Apache 2.0) | Yes (MIT) | Yes (MIT) | Planned |
| Visual builder | Full drag-and-drop workflow editor | None | None | Explicitly excluded; code-first with templates |
| Agent reasoning visibility | Node execution logs | Token streaming | Model thoughts display | LangGraph node streaming with thinking events |

### Competitive Positioning

**NextFlow differentiates on three axes:**

1. **MCP-native:** While Dify uses a proprietary tool format and LobeChat adds MCP as a plugin, NextFlow treats MCP as a first-class protocol. Any MCP-compatible service connects without custom integration code. This is a bet on the MCP ecosystem growing rapidly (it is).

2. **LangGraph agent engine:** Most competitors use simple prompt-chaining or basic tool loops. LangGraph's stateful graph enables genuinely complex multi-step workflows with conditional branching, loops, and checkpointing. This is the technical moat.

3. **Three-layer memory:** Most competitors have either session-scoped context or flat RAG. The explicit short-term/long-term/working memory split, with AgentState carrying task-specific working memory through the graph, enables more coherent long-running agent tasks.

**Where NextFlow concedes:** Dify's visual workflow builder is genuinely useful for non-technical users. NextFlow explicitly trades this for a code-first approach with templates. This is the right trade because (a) the target audience is developers building agent-powered applications, not non-technical users, and (b) visual builders create maintenance and debugging burdens that slow iteration.

## Sources

- **Dify** - GitHub README and documentation (github.com/langgenius/dify). Analyzed workflow engine, plugin system, multi-model support.
- **Open WebUI** - GitHub README and documentation (github.com/open-webui). Analyzed Ollama integration, RAG approach, community plugins.
- **LobeChat** - GitHub README and documentation (github.com/lobehub/lobe-chat). Analyzed plugin marketplace, multi-provider support, MCP integration approach.
- **MCP Protocol Specification** - modelcontextprotocol.io. Architecture, tools specification, transport layer, annotations.
- **LangGraph Documentation** - langchain-ai.github.io/langgraph. Workflow patterns, streaming modes, custom streaming, subgraph support.
- **PROJECT.md** - NextFlow project context defining constraints, tech stack decisions, and out-of-scope items.

---
*Feature research for: Universal Agent Platform (通用Agent平台)*
*Researched: 2026-03-28*
