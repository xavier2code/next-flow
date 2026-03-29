# Requirements: NextFlow — 通用Agent平台

**Defined:** 2026-03-28
**Core Value:** 让 Agent 通过标准化技能和工具接口，灵活接入多种 LLM 和外部服务，可靠完成复杂任务

## v1 Requirements

### Foundation & Auth

- [x] **AUTH-01**: User can sign up with email and password
- [x] **AUTH-02**: User can log in and receive JWT token with refresh mechanism
- [x] **AUTH-03**: User session persists across browser refresh via token refresh
- [x] **AUTH-04**: FastAPI project skeleton with config management, logging, and error handling
- [x] **AUTH-05**: PostgreSQL schema for users, conversations, agents, skills, mcp_servers, tools
- [x] **AUTH-06**: Redis setup for session store and cache

### Agent Engine

- [ ] **AGNT-01**: LangGraph StateGraph workflow with Analyze → Plan → Execute → Respond nodes
- [ ] **AGNT-02**: AgentState TypedDict with messages (add_messages reducer), plan, scratchpad fields
- [ ] **AGNT-03**: PostgresSaver checkpointer for conversation state persistence and resumability
- [ ] **AGNT-04**: LLM integration via LangChain with at least OpenAI and Ollama providers
- [x] **AGNT-05**: Tool Registry skeleton with unified registration interface and built-in tools
- [x] **AGNT-06**: RemainingSteps managed value for graceful recursion limit handling

### Communication

- [ ] **COMM-01**: REST API endpoints for CRUD on conversations, agents, and settings
- [ ] **COMM-02**: WebSocket endpoint with LangGraph v2 streaming integration
- [ ] **COMM-03**: Event mapping from LangGraph StreamParts to WebSocket events (thinking, tool_call, tool_result, chunk, done)
- [ ] **COMM-04**: Connection lifecycle management with heartbeat, cleanup on disconnect

### Memory

- [ ] **MEM-01**: Short-term memory using Redis (last N messages per conversation)
- [ ] **MEM-02**: Context injection in Analyze node from short-term memory
- [ ] **MEM-03**: LangGraph Store integration for cross-thread semantic search (long-term memory)
- [ ] **MEM-04**: Qdrant/Milvus setup with collection schemas for long-term memory

### MCP Integration

- [ ] **MCP-01**: MCP Client implementation supporting Streamable HTTP transport with legacy SSE fallback
- [ ] **MCP-02**: MCP Manager for server registration, connection lifecycle, and health monitoring
- [ ] **MCP-03**: MCP tool discovery (tools/list) and registration into unified Tool Registry
- [ ] **MCP-04**: MCP admin API endpoints for server registration and status monitoring
- [ ] **MCP-05**: MCP tool invocation via Tool Registry routing (namespaced as mcp__server__tool)

### Skill System

- [ ] **SKIL-01**: Skill package format definition with manifest (name, description, permissions, tools)
- [ ] **SKIL-02**: MinIO integration for skill package storage
- [ ] **SKIL-03**: Docker-based sandbox executor with resource limits and timeout enforcement
- [ ] **SKIL-04**: Skill lifecycle management (upload, validate, enable, disable, hot-update)
- [ ] **SKIL-05**: Skill tool registration into unified Tool Registry

### Frontend

- [ ] **UI-01**: Project setup with Vite + React + TypeScript + shadcn/ui + Zustand (slice pattern)
- [ ] **UI-02**: Auth UI (login/register pages with form validation)
- [ ] **UI-03**: Conversation UI with message list, input box, and streaming response rendering
- [ ] **UI-04**: Markdown rendering with code syntax highlighting in responses
- [ ] **UI-05**: Thinking process visualization (collapsible sections)
- [ ] **UI-06**: Tool call/result visualization (inline cards)
- [ ] **UI-07**: Agent configuration UI (model selection, system prompt, temperature)
- [ ] **UI-08**: Conversation history management (list, create, delete)
- [ ] **UI-09**: Skill management UI (list, enable/disable, upload)
- [ ] **UI-10**: MCP management UI (server registration, connection status, tool list)

## v2 Requirements

### Advanced Agent Patterns

- **ADVN-01**: Parallel tool execution via LangGraph Send API
- **ADVN-02**: Evaluator-optimizer loop (Reflect node) with Command for complex tasks
- **ADVN-03**: Multi-LLM routing and fallback chains
- **ADVN-04**: Human-in-the-loop interrupts

### Enterprise

- **RBAC-01**: Role-based access control (admin/developer/viewer)
- **TENANT-01**: Multi-tenant data isolation
- **MKT-01**: Skill marketplace with packaging, versioning, and review system

### Knowledge

- **KNOW-01**: RAG knowledge base with document upload, auto-chunking, and embedding
- **KNOW-02**: Document ingestion pipeline integrated with LangGraph workflow

## Out of Scope

| Feature | Reason |
|---------|--------|
| Visual workflow builder (drag-and-drop) | Massive engineering investment; code-first with templates is the right approach for developer audience |
| Voice interaction | STT/TTS pipeline complexity; explicitly out of scope per PROJECT.md |
| Mobile native app | Doubles frontend engineering; responsive PWA sufficient for v1 |
| Multi-tenant isolation | Premature for v1; design tenant_id fields early but do not enforce until v2 |
| Real-time collaborative editing | CRDT/OT complexity disproportionate to value |
| Built-in LLM fine-tuning | Different engineering domain; support local model endpoints instead |
| Low-code/no-code agent builder | Constrains power users; template library + code customization better |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| AUTH-06 | Phase 1 | Complete |
| AGNT-01 | Phase 2 | Pending |
| AGNT-02 | Phase 2 | Pending |
| AGNT-03 | Phase 2 | Pending |
| AGNT-04 | Phase 2 | Pending |
| AGNT-05 | Phase 2 | Complete |
| AGNT-06 | Phase 2 | Complete |
| COMM-01 | Phase 3 | Pending |
| COMM-02 | Phase 3 | Pending |
| COMM-03 | Phase 3 | Pending |
| COMM-04 | Phase 3 | Pending |
| MEM-01 | Phase 4 | Pending |
| MEM-02 | Phase 4 | Pending |
| MEM-03 | Phase 4 | Pending |
| MEM-04 | Phase 4 | Pending |
| MCP-01 | Phase 5 | Pending |
| MCP-02 | Phase 5 | Pending |
| MCP-03 | Phase 5 | Pending |
| MCP-04 | Phase 5 | Pending |
| MCP-05 | Phase 5 | Pending |
| SKIL-01 | Phase 6 | Pending |
| SKIL-02 | Phase 6 | Pending |
| SKIL-03 | Phase 6 | Pending |
| SKIL-04 | Phase 6 | Pending |
| SKIL-05 | Phase 6 | Pending |
| UI-01 | Phase 7 | Pending |
| UI-02 | Phase 7 | Pending |
| UI-03 | Phase 7 | Pending |
| UI-04 | Phase 7 | Pending |
| UI-05 | Phase 7 | Pending |
| UI-06 | Phase 7 | Pending |
| UI-07 | Phase 7 | Pending |
| UI-08 | Phase 7 | Pending |
| UI-09 | Phase 7 | Pending |
| UI-10 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after roadmap creation (7 phases, 40 requirements mapped)*
