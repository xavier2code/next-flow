---
phase: 6
slug: skill-system
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | backend/pyproject.toml (asyncio_mode = "auto") |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SKIL-01 | unit | `cd backend && python -m pytest tests/unit/test_skill_validator.py -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | SKIL-02 | unit | `cd backend && python -m pytest tests/unit/test_skill_minio.py -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | SKIL-03 | unit | `cd backend && python -m pytest tests/unit/test_skill_sandbox.py -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | SKIL-03 | unit | `cd backend && python -m pytest tests/unit/test_skill_handler.py -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | SKIL-04 | integration | `cd backend && python -m pytest tests/test_skills.py -x` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | SKIL-05 | unit | `cd backend && python -m pytest tests/unit/test_skill_registry.py -x` | ❌ W0 | ⬜ pending |
| 06-03-03 | 03 | 2 | SKIL-05 | unit | `cd backend && python -m pytest tests/unit/test_skill_builtins.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_skill_validator.py` — SKILL.md parsing, ZIP validation, path traversal prevention (SKIL-01)
- [ ] `tests/unit/test_skill_minio.py` — MinIO upload/download of skill packages (SKIL-02)
- [ ] `tests/unit/test_skill_sandbox.py` — Docker container lifecycle with resource limits (SKIL-03)
- [ ] `tests/unit/test_skill_handler.py` — SkillToolHandler timeout, connection, execution errors (SKIL-03, SKIL-05)
- [ ] `tests/unit/test_skill_registry.py` — Tool registration/unregistration with skill namespace prefix (SKIL-05)
- [ ] `tests/unit/test_skill_builtins.py` — load_skill built-in tool (SKIL-05)
- [ ] `tests/test_skills.py` — Integration tests for Skill CRUD API endpoints (SKIL-04)
- [ ] `tests/conftest.py` — Add MinIO mock fixture, SkillManager fixture

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker sandbox resource limits enforced | SKIL-03 | Requires running Docker daemon | Start service-type skill, verify container has cpu_count/memory limits set via `docker inspect` |
| MinIO bucket creation and file storage | SKIL-02 | Requires running MinIO service | Upload skill package, verify object exists in MinIO console |
| Hot-update stop-then-start cycle | SKIL-04 | Requires full stack running | Enable skill, upload new version, verify old container stopped and new started |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
