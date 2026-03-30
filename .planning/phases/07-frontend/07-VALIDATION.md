---
phase: 7
slug: 07-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (Vite-native test runner) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run --coverage` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run --coverage`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | UI-01 | integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | UI-01 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | UI-02 | integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | UI-03 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-02-03 | 02 | 1 | UI-04, UI-05, UI-06 | unit | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | UI-07, UI-08 | integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | UI-09 | integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |
| 07-03-03 | 03 | 2 | UI-10 | integration | `cd frontend && npx vitest run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/vitest.config.ts` — Vitest configuration with jsdom environment
- [ ] `frontend/src/__tests__/setup.ts` — test setup with fetch/mock utilities
- [ ] `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom` — test dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebSocket streaming renders chunks in real-time | UI-03 | Requires live backend + WS connection | 1. Start backend, 2. Open app, 3. Send message, 4. Verify streaming text appears progressively |
| Dark/light theme toggle persists | UI-01 (D-20) | CSS variable swap visual verification | 1. Toggle theme in Settings, 2. Refresh page, 3. Verify theme persists |
| Side panel auto-opens on thinking/tool events | UI-05, UI-06 | Requires live streaming events | 1. Send message that triggers tool use, 2. Verify side panel opens, 3. Verify thinking/tool cards appear |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
