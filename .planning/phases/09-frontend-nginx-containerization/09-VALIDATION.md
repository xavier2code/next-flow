---
phase: 9
slug: frontend-nginx-containerization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Docker + Nginx smoke tests (no unit test framework needed) |
| **Config file** | frontend/vitest.config.ts (existing, for React tests only) |
| **Quick run command** | `docker build -t nextflow-frontend frontend/ && docker run --rm nextflow-frontend nginx -v` |
| **Full suite command** | `docker build -t nextflow-frontend frontend/ && docker run --rm -p 8080:80 nextflow-frontend` + curl smoke tests |
| **Estimated runtime** | ~60 seconds (build + verify) |

---

## Sampling Rate

- **After every task commit:** `docker build -t nextflow-frontend frontend/` (verify build succeeds)
- **After every plan wave:** Full Docker build + manual smoke test (curl health endpoint, verify SPA loads)
- **Before `/gsd:verify-work`:** Full Docker build must succeed, image must run, nginx -v outputs correct version
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | FRNT-01, FRNT-05 | smoke | `docker build -t nextflow-frontend frontend/ && docker run --rm nextflow-frontend nginx -v` | N/A — Docker test | ⬜ pending |
| 09-02-01 | 02 | 1 | FRNT-02, FRNT-03, FRNT-04, FRNT-06 | smoke | `docker build -t nextflow-frontend frontend/ && docker run --rm -p 8080:80 nextflow-frontend` + `curl -sI http://localhost:8080/ \| grep -c "200"` | N/A — Docker test | ⬜ pending |
| 09-02-02 | 02 | 1 | D-05 | unit | `test -d backend/app/api/ws/ && echo "FAIL" \|\| echo "PASS"` | N/A — filesystem check | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- This phase is primarily infrastructure (Dockerfile + Nginx config). No new test files needed.
- Validation is smoke-test based (Docker build, curl requests) rather than unit-test based.
- Existing Vitest setup is for React component tests and is not relevant to Docker/Nginx validation.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SPA try_files fallback (no 404 on refresh) | FRNT-02 | Requires running container + browser | `docker run --rm -p 8080:80 nextflow-frontend` then `curl -s http://localhost:8080/nonexistent-path` — should return index.html (200) |
| API proxy to backend | FRNT-03 | Requires backend running | `docker run --rm --network host nextflow-frontend` then `curl -s http://localhost/api/v1/health` — should proxy to backend |
| SSE proxy_buffering off | FRNT-04 | Requires live SSE stream | Send chat message, verify token-by-token streaming in browser (no buffering delay) |
| Gzip compression | FRNT-06 | Requires response header inspection | `curl -sI -H "Accept-Encoding: gzip" http://localhost:8080/assets/*.js` — check `Content-Encoding: gzip` |
| Build context size | FRNT-05 | Requires Docker build output | `docker build --progress=plain frontend/ 2>&1 | grep "Sending build context"` — should be <50MB |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
