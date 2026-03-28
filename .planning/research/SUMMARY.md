# Research Summary: NextFlow -- Universal Agent Platform

**Domain:** Universal Agent Platform (AI agent orchestration with MCP integration, skill system, and three-layer memory)
**Researched:** 2026-03-28
**Overall confidence:** HIGH

## Executive Summary

NextFlow is a full-stack AI agent platform built on three technical pillars: LangGraph for stateful graph-based agent orchestration, MCP (Model Context Protocol) for standardized tool integration, and a three-layer memory architecture (Redis short-term, Qdrant long-term, AgentState working memory). The platform targets developers building agent-powered applications -- intelligent customer service, automated task orchestration, knowledge-base Q&A, and enterprise AI integration.

The technology landscape for this domain in early 2026 is mature but rapidly evolving. LangGraph reached production stability (v1.1.3) in late 2025 and now provides the checkpointing, streaming, and human-in-the-loop capabilities that would take months to build from scratch. The MCP specification has stabilized around Streamable HTTP transport, deprecating the older SSE approach. On the frontend, React 19 with Vite 7, Zustand 5, and shadcn/ui provides a modern, fast component model without the overhead of Next.js SSR (which the project does not need).

The primary technical risk is integration complexity. Each subsystem (agent engine, MCP client, skill sandbox, memory layers, WebSocket streaming) works well in isolation, but the interfaces between them -- particularly the Tool Registry unifying built-in tools, MCP-discovered tools, and skill-exposed tools -- require careful upfront design. The research identifies ten critical pitfalls, with the most impactful being LangGraph recursion limit mismanagement (causing silent hangs in production), MCP transport incompatibility (legacy SSE vs Streamable HTTP), and streaming chain breakage from non-streaming components in the LangChain pipeline.

The recommended build order follows a strict dependency chain: foundation (PostgreSQL, Redis, FastAPI skeleton, auth) comes first; the agent engine (LangGraph StateGraph with checkpointer and streaming) is the critical path; communication layer (REST + WebSocket) wraps the engine; then memory, MCP, skills, and frontend build outward from the core. Frontend scaffolding can begin in parallel with Phase 3 but needs the WebSocket API to become functional.

## Key Findings

**Stack:** Python 3.12 + FastAPI 0.135 + LangGraph 1.1 + React 19 + Vite 7 + PostgreSQL 16 + Redis 7 + Qdrant 1.x + MinIO + Celery 5.6. Every choice is current-stable, not bleeding-edge. React 19 supersedes the PROJECT.md specification of React 18. Vite 7 is chosen over Vite 8 (released days ago) for ecosystem stability. Qdrant chosen over Milvus for operational simplicity and first-class async Python support.

**Architecture:** Layered microservices with FastAPI gateway, LangGraph agent engine, unified Tool Registry (strategy pattern for built-in/skill/MCP routing), MCP Manager (multi-server client pool), Skill Manager (Docker sandboxed execution), and three-layer memory coordinated through LangGraph Store.

**Critical pitfall:** LangGraph state reducer misconfiguration (using bare `list` instead of `Annotated[list, add_messages]`) silently loses conversation history. This must be prevented in Phase 1 with schema tests, because retrofitting the reducer requires touching every node's return values and migrating all checkpointed conversations.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation & Auth** - PostgreSQL schema, Redis setup, FastAPI project skeleton, JWT auth + RBAC middleware
   - Addresses: User authentication (table stakes), database infrastructure
   - Avoids: Building agent logic without persistence layer ready

2. **Agent Engine Core** - LangGraph StateGraph definition, PostgresSaver checkpointer, LLM integration, Tool Registry skeleton, streaming architecture
   - Addresses: Core differentiating engine, tool invocation, multi-LLM abstraction
   - Avoids: Pitfalls 1 (recursion limits), 2 (state reducers), 5 (streaming chain breakage), 10 (provider abstraction leaks) by building correct patterns from day one

3. **Communication Layer** - REST API endpoints, WebSocket endpoint with LangGraph streaming, event mapping (StreamPart to WebSocket events)
   - Addresses: Streaming response (table stakes), WebSocket infrastructure needed by all real-time features
   - Avoids: Pitfall 6 (WebSocket lifecycle mismanagement) with connection manager from start

4. **Memory System** - Qdrant setup, LangGraph Store integration, short-term Redis memory manager, context injection in Analyze node
   - Addresses: Three-layer memory (differentiator), short-term memory for coherent multi-turn
   - Avoids: Pitfall 8 (memory synchronization drift) with explicit write-through policy

5. **MCP Integration** - MCP client (Streamable HTTP transport), MCP Manager, tool discovery, admin API
   - Addresses: MCP protocol integration (core differentiator)
   - Avoids: Pitfall 3 (transport incompatibility) with detection logic, Pitfall 4 (DNS rebinding) with security from day one

6. **Skill System** - Package format, MinIO storage, Docker sandbox executor, lifecycle management, tool registration
   - Addresses: Dynamic skill loading (differentiator)
   - Avoids: Pitfall 9 (sandbox escapes) with container isolation from start

7. **Frontend** - Vite + React + TypeScript + shadcn/ui + Zustand (slices), auth UI, conversation UI with streaming, thinking/tool visualization, agent config, skill/MCP management
   - Addresses: All table-stakes UX features, thinking visualization (differentiator)
   - Avoids: Pitfall 7 (monolithic Zustand store) with slices from day one
   - Note: Can begin scaffolding in parallel with Phase 3, becomes functional after Phase 3 completes

8. **Advanced Patterns** - Parallel tool execution (Send API), evaluator-optimizer loops, multi-LLM routing, human-in-the-loop interrupts, knowledge base (RAG)
   - Addresses: Reflect node, RAG knowledge base, advanced agent capabilities
   - Depends on: All previous phases operational for end-to-end testing

**Phase ordering rationale:**

- Agent Engine (Phase 2) is the critical path -- every subsystem either feeds into it (tools, memory) or consumes from it (WebSocket events, frontend). It must be built early and correctly.
- Tool Registry must exist before MCP (Phase 5) and Skills (Phase 6) can register their tools. The registry is the integration backbone.
- Memory (Phase 4) requires both the graph (for LangGraph Store integration) and Redis (from Phase 1) to be ready.
- MCP and Skills (Phases 5-6) can be built in either order but both depend on Tool Registry (Phase 2) and the admin API pattern (Phase 3).
- Frontend (Phase 7) can start scaffold in parallel with Phase 3 but needs REST + WebSocket APIs to become functional.
- Advanced patterns (Phase 8) require all subsystems operational for end-to-end testing.

**Research flags for phases:**

- Phase 2 (Agent Engine): Needs deeper research on LangGraph `astream_events` v2 event shapes to correctly map streaming to WebSocket events. The documentation was consulted but event filtering and namespace handling for subgraphs may require prototyping.
- Phase 4 (Memory): LangGraph Store's production readiness needs validation. The Store API is newer than the core graph API and may have edge cases around namespace-based retrieval and vector search quality.
- Phase 5 (MCP): Transport detection (Streamable HTTP vs legacy SSE fallback) needs prototyping against real external MCP servers. The specification describes the protocol but real-world server implementations may have quirks.
- Phase 6 (Skills): Docker-based sandboxing with gVisor or similar runtime security needs investigation. The research identified the approach but specific container security configurations (seccomp profiles, capability restrictions) require phase-specific research.
- Phase 7 (Frontend): Standard patterns, unlikely to need research. shadcn/ui, Zustand, and React 19 are well-documented with stable APIs.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI, npm, and GitHub releases within the last 7 days. Version pinning strategy accounts for ecosystem release cadence. |
| Features | HIGH | Feature landscape mapped against three direct competitors (Dify, Open WebUI, LobeChat). MVP scope is realistic. Anti-features identified with clear rationale. |
| Architecture | HIGH | LangGraph patterns verified against official documentation. MCP architecture verified against specification. Component boundaries and data flows are internally consistent. |
| Pitfalls | MEDIUM | Critical pitfalls (recursion limits, state reducers, streaming) verified against LangGraph/LangChain docs. MCP transport pitfalls verified against MCP spec. Skill sandboxing and memory sync patterns are based on domain expertise rather than NextFlow-specific production experience. |

## Gaps to Address

- **LangGraph Store vector search quality:** The Store API for long-term semantic memory is newer than the core graph API. Production behavior under concurrent access, namespace partitioning performance, and embedding model compatibility need validation during Phase 4 implementation.
- **MCP real-world server compatibility:** The transport detection strategy (Streamable HTTP first, legacy SSE fallback) needs testing against at least 3-5 real external MCP server implementations. The specification defines the protocol but implementations may diverge.
- **Skill sandbox security depth:** Docker-based isolation is the recommended approach, but specific security configurations (seccomp profiles, network policies, filesystem restrictions, resource limits) need phase-specific research during Phase 6. gVisor or similar runtime security may be warranted.
- **WebSocket horizontal scaling:** The architecture handles single-process WebSocket well. The Redis pub/sub pattern for cross-worker messaging at 10K+ concurrent connections needs validation during scaling work. This is a known pattern but implementation details matter.
- **Streaming event normalization across LLM providers:** Different providers (OpenAI, Anthropic, Ollama) emit different streaming event shapes. LangChain normalizes tool calls but `astream_events` event structures may still vary. Integration tests against each provider during Phase 2 will surface this.

## Files in This Research

| File | Purpose | Confidence |
|------|---------|------------|
| `.planning/research/STACK.md` | Technology recommendations with versions, rationale, anti-recommendations, pinning strategy | HIGH |
| `.planning/research/FEATURES.md` | Feature landscape (table stakes, differentiators, anti-features), dependency graph, MVP definition, competitor analysis | HIGH |
| `.planning/research/ARCHITECTURE.md` | System structure, component boundaries, data flows, patterns, anti-patterns, scalability, build order | HIGH |
| `.planning/research/PITFALLS.md` | 20 pitfalls (10 critical, 5 moderate, 5 minor), technical debt patterns, integration gotchas, recovery strategies | MEDIUM |

---
*Research summary for: NextFlow -- Universal Agent Platform*
*Researched: 2026-03-28*
