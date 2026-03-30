---
phase: 4
slug: memory-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | MEM-04 | integration | `pytest tests/test_memory.py::test_pgvector_available -x` | Wave 0 | pending |
| 04-01-02 | 01 | 1 | MEM-04 | integration | `pytest tests/test_memory.py::test_store_setup -x` | Wave 0 | pending |
| 04-02-01 | 02 | 1 | MEM-01 | unit | `pytest tests/test_memory.py::test_short_term_add_and_retrieve -x` | Wave 0 | pending |
| 04-02-02 | 02 | 1 | MEM-01 | unit | `pytest tests/test_memory.py::test_sliding_window_trim -x` | Wave 0 | pending |
| 04-02-03 | 02 | 1 | MEM-01 | unit | `pytest tests/test_memory.py::test_summary_compression -x` | Wave 0 | pending |
| 04-02-04 | 02 | 1 | MEM-01 | unit | `pytest tests/test_memory.py::test_ttl_refresh -x` | Wave 0 | pending |
| 04-03-01 | 03 | 2 | MEM-02 | unit | `pytest tests/test_memory.py::test_analyze_context_injection -x` | Wave 0 | pending |
| 04-03-02 | 03 | 2 | MEM-03 | integration | `pytest tests/test_memory.py::test_store_semantic_search -x` | Wave 0 | pending |
| 04-03-03 | 03 | 2 | MEM-03 | unit | `pytest tests/test_memory.py::test_store_user_scoped_namespace -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_memory.py` — stubs for MEM-01 through MEM-04
- [ ] Test fixtures for InMemoryStore (unit tests without PostgreSQL dependency)
- [ ] Test fixture for Redis mock/fake (reuse existing test_redis fixture from conftest.py)
- [ ] Docker image change verification (manual: pull pgvector/pgvector:pg16, update docker-compose.yml)

*Existing infrastructure covers pytest framework and async test support.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PostgreSQL pgvector extension installed | MEM-04 | Requires running Docker container with pgvector image | `docker exec nextflow-postgres psql -U nextflow -c "SELECT * FROM pg_extension WHERE extname = 'vector'"` |
| Store setup creates vector tables | MEM-04 | Requires running PostgreSQL instance | Check `store` and `store_vectors` tables exist after `store.setup()` |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
