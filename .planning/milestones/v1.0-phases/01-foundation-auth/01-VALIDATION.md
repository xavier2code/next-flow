---
phase: 1
slug: foundation-auth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio for async tests) |
| **Config file** | `backend/pyproject.toml` — Wave 0 creates |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=long` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --tb=long`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | AUTH-04 | unit | `cd backend && python -m pytest tests/test_health.py -v` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | AUTH-05 | unit | `cd backend && python -m pytest tests/test_models.py -v` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | AUTH-06 | unit | `cd backend && python -m pytest tests/test_redis.py -v` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | AUTH-01 | integration | `cd backend && python -m pytest tests/test_auth.py::test_register -v` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | AUTH-02 | integration | `cd backend && python -m pytest tests/test_auth.py::test_login -v` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 2 | AUTH-03 | integration | `cd backend && python -m pytest tests/test_auth.py::test_refresh -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared fixtures (async test client, test DB, test Redis)
- [ ] `backend/tests/test_health.py` — stubs for AUTH-04 health check
- [ ] `backend/tests/test_models.py` — stubs for AUTH-05 schema validation
- [ ] `backend/tests/test_redis.py` — stubs for AUTH-06 Redis connectivity
- [ ] `backend/tests/test_auth.py` — stubs for AUTH-01/02/03 auth flow
- [ ] `pytest`, `pytest-asyncio`, `httpx` — installed via pyproject.toml

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Token refresh across simulated browser refresh | AUTH-03 | Requires simulating client-side token lifecycle | 1. Register user 2. Login, get access+refresh tokens 3. Wait 16 min (or mock expiry) 4. Use refresh token to get new access token 5. Verify old refresh token is invalidated |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
