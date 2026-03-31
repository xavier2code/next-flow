---
phase: 2
slug: agent-engine-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `backend/pyproject.toml` (existing) |
| **Quick run command** | `cd backend && python -m pytest tests/unit/test_agent_engine.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/unit/test_agent_engine.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | AGNT-01 | unit | `pytest tests/unit/test_workflow.py -k "test_analyze_node" -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | AGNT-01 | unit | `pytest tests/unit/test_workflow.py -k "test_plan_node" -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | AGNT-01 | unit | `pytest tests/unit/test_workflow.py -k "test_execute_node" -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | AGNT-01 | unit | `pytest tests/unit/test_workflow.py -k "test_respond_node" -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | AGNT-02 | unit | `pytest tests/unit/test_workflow.py -k "test_agent_state" -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | AGNT-01 | unit | `pytest tests/unit/test_workflow.py -k "test_conditional_edge" -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | AGNT-03 | unit | `pytest tests/unit/test_checkpointer.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | AGNT-03 | integration | `pytest tests/integration/test_checkpoint_resume.py -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | AGNT-04 | unit | `pytest tests/unit/test_llm_factory.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 1 | AGNT-04 | integration | `pytest tests/integration/test_llm_invoke.py -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 1 | AGNT-05, AGNT-06 | unit | `pytest tests/unit/test_tool_registry.py -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 1 | AGNT-06 | unit | `pytest tests/unit/test_tool_registry.py -k "test_decorator" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/test_workflow.py` — stubs for AGNT-01, AGNT-02 (StateGraph nodes, AgentState, conditional edges)
- [ ] `backend/tests/unit/test_checkpointer.py` — stubs for AGNT-03 (PostgresSaver setup, resume)
- [ ] `backend/tests/unit/test_llm_factory.py` — stubs for AGNT-04 (get_llm factory, provider routing)
- [ ] `backend/tests/unit/test_tool_registry.py` — stubs for AGNT-05, AGNT-06 (register, invoke, decorator)
- [ ] `backend/tests/integration/test_checkpoint_resume.py` — stubs for AGNT-03 (full resume flow)
- [ ] `backend/tests/integration/test_llm_invoke.py` — stubs for AGNT-04 (LLM invocation with mocked provider)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
