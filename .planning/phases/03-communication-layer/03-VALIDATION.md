---
phase: 03
slug: communication-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` (asyncio_mode = "auto") |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -x -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | COMM-01 | integration | `.venv/bin/python -m pytest tests/test_conversations.py -x` | Wave 0 | pending |
| 03-01-02 | 01 | 1 | COMM-01 | integration | `.venv/bin/python -m pytest tests/test_agents.py -x` | Wave 0 | pending |
| 03-01-03 | 01 | 1 | COMM-01 | integration | `.venv/bin/python -m pytest tests/test_settings.py -x` | Wave 0 | pending |
| 03-01-04 | 01 | 1 | COMM-01 | unit | `.venv/bin/python -m pytest tests/unit/test_pagination.py -x` | Wave 0 | pending |
| 03-02-01 | 02 | 1 | COMM-02 | integration | `.venv/bin/python -m pytest tests/test_messages.py -x` | Wave 0 | pending |
| 03-02-02 | 02 | 1 | COMM-02 | integration | `.venv/bin/python -m pytest tests/test_ws_chat.py -x` | Wave 0 | pending |
| 03-02-03 | 02 | 1 | COMM-03 | unit | `.venv/bin/python -m pytest tests/unit/test_event_mapper.py -x` | Wave 0 | pending |
| 03-02-04 | 02 | 1 | COMM-04 | integration | `.venv/bin/python -m pytest tests/unit/test_connection_manager.py -x` | Wave 0 | pending |
| 03-02-05 | 02 | 1 | COMM-04 | unit | `.venv/bin/python -m pytest tests/unit/test_connection_manager.py -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_conversations.py` -- stubs for COMM-01 conversation CRUD
- [ ] `tests/test_agents.py` -- stubs for COMM-01 agent CRUD
- [ ] `tests/test_settings.py` -- stubs for COMM-01 settings CRUD
- [ ] `tests/test_messages.py` -- stubs for COMM-02 message POST (202)
- [ ] `tests/test_ws_chat.py` -- stubs for COMM-02 WebSocket streaming
- [ ] `tests/unit/test_pagination.py` -- stubs for cursor encoding/decoding
- [ ] `tests/unit/test_event_mapper.py` -- stubs for COMM-03 event mapping
- [ ] `tests/unit/test_connection_manager.py` -- stubs for COMM-04 lifecycle

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebSocket ping/pong liveness | COMM-04 | Requires real TCP connection observation | Connect via ws client, observe ping frames in network tab |
| Multi-tab message delivery | COMM-04 | Requires browser multi-tab coordination | Open 2 tabs, send message in one, verify both receive events |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
