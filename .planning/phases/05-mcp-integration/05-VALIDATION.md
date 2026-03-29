---
phase: 5
slug: mcp-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | MCP-01 | unit | `cd backend && python -m pytest tests/test_mcp_client.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | MCP-01 | unit | `cd backend && python -m pytest tests/test_mcp_client.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | MCP-02 | unit | `cd backend && python -m pytest tests/test_mcp_manager.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | MCP-02 | unit | `cd backend && python -m pytest tests/test_mcp_manager.py -x -q` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 2 | MCP-03 | unit | `cd backend && python -m pytest tests/test_mcp_tool_sync.py -x -q` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 2 | MCP-05 | unit | `cd backend && python -m pytest tests/test_mcp_tool_sync.py -x -q` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 2 | MCP-04 | integration | `cd backend && python -m pytest tests/test_mcp_api.py -x -q` | ❌ W0 | ⬜ pending |
| 05-04-02 | 04 | 2 | MCP-04 | integration | `cd backend && python -m pytest tests/test_mcp_api.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_mcp_client.py` — stubs for MCP-01 (client connect, transport fallback)
- [ ] `backend/tests/test_mcp_manager.py` — stubs for MCP-02 (lifecycle, health check, reconnect)
- [ ] `backend/tests/test_mcp_tool_sync.py` — stubs for MCP-03, MCP-05 (tool discovery, namespaced registration, invocation)
- [ ] `backend/tests/test_mcp_api.py` — stubs for MCP-04 (CRUD endpoints, async registration)
- [ ] `backend/tests/conftest.py` — MCP-specific fixtures (mock MCPClient, mock ClientSession)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Transport auto-fallback to SSE | MCP-01 | Requires running MCP server with specific transport config | Start real MCP server, configure with SSE endpoint, verify fallback |
| Health check triggers reconnection | MCP-02 | Requires simulating server outage mid-connection | Disconnect server, verify reconnect with exponential backoff |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
