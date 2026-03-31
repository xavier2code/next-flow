# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-31
**Phases:** 7 | **Plans:** 22 | **Tasks:** 43

### What Was Built
- Complete backend: FastAPI + JWT auth + LangGraph 4-node agent pipeline + REST/WebSocket API
- Memory system: Redis short-term + LangGraph Store long-term + AgentState working memory
- MCP integration: Streamable HTTP/SSE client + server lifecycle + admin API
- Skill system: Docker sandbox + MinIO storage + SKILL.md/ZIP validation + tool registration
- Frontend: React 19 + shadcn/ui — auth, streaming chat, management dashboards, settings

### What Worked
- Inside-out build order (infrastructure → engine → communication → extensions → UI) minimized rework
- Protocol-based Tool Registry unified MCP tools, skill tools, and built-in tools under one interface
- LLM factory pattern with provider routing made adding Ollama alongside OpenAI straightforward
- Async-first architecture (asyncpg, redis.asyncio, httpx) aligned naturally with FastAPI's model
- Service layer pattern (routes → services → models) kept HTTP logic separate from business logic
- Zustand slice pattern with dynamic import() avoided circular dependency issues

### What Was Inefficient
- Phase 1 Plan 03 took 154 min (auth integration) — longest plan, complex test fixture setup
- LLM factory uses if/elif chain instead of registry pattern — extensible but not elegant
- Some SUMMARY.md files missing one_liner field — reduced archive quality
- REQUIREMENTS.md checkboxes not updated during execution — had to fix during archival
- ROADMAP.md 07-04 checkbox not updated after completion

### Patterns Established
- Lifespan wiring pattern: all managers (MCP, Skill, Memory) wired via FastAPI lifespan startup/shutdown
- Duck-typing over Protocol inheritance: MCPToolHandler and SkillToolHandler implement ToolHandler interface without explicit Protocol subclass
- Module-level service instances with setter pattern for graph node injection
- Test conftest layering: unit tests override session-scoped DB fixtures with no-ops
- Circular dependency resolution: registerCallback pattern (api-client) + dynamic import() (chat-store)

### Key Lessons
1. **Build infrastructure first, verify incrementally** — Docker Compose + health check in Plan 01-01 caught connectivity issues early
2. **Protocol-based registries scale well** — Tool Registry handled built-in, MCP, and skill tools with zero architectural changes
3. **Async context managers need careful cleanup** — Store factory returned dict with ctx for lifespan management
4. **Frontend scaffolding generates lots of files** — Phase 7 Plan 01 created 57 files in one plan
5. **Test independence matters** — Unit tests that override DB fixtures with no-ops run 10x faster than integration tests
6. **Update planning docs during execution** — Don't batch checkbox updates to archival time

### Cost Observations
- Model mix: balanced profile (opus/sonnet/haiku)
- Plans: 22 total, average ~15 min each
- Notable: Phase 1-4 (backend) completed in 2 days; Phase 5-7 (extensions + frontend) in 1 day
- Frontend phase generated most files but had fastest per-plan execution after scaffolding

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~8 | 7 | Initial implementation — established all core patterns |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | ~70+ | Untested % | 1 (next-flow itself) |

### Top Lessons (Verified Across Milestones)

1. Inside-out build order minimizes rework — validate each layer before building the next
2. Protocol-based registries (Tool Registry) handle organic growth better than hardcoded dispatch
3. Async-first + lifespan wiring is the correct pattern for FastAPI service composition
