---
phase: 4
slug: async-safety-and-session-isolation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 + pytest-asyncio 0.23.5 |
| **Config file** | None explicit (pytest discovers via `app/tests/`) |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_session_isolation.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_session_isolation.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | REVW-05 | audit | manual code review | N/A | ⬜ pending |
| 04-02-01 | 02 | 1 | REVW-05 (a)(b) | unit (mock DB + LLM) | `python -m pytest app/tests/test_session_isolation.py::test_concurrent_review_no_detached_error -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | REVW-05 (b) | unit (mock factory) | `python -m pytest app/tests/test_session_isolation.py::test_session_factory_creates_separate_sessions -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | REVW-05 (c) | integration | `python -m pytest app/tests/ -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_session_isolation.py` — stubs for REVW-05 (concurrent session safety tests)
- [ ] No framework install needed (pytest-asyncio already in requirements.txt)
- [ ] No conftest changes needed (existing fixtures sufficient for mock-based tests)

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audit of call sites and session passing | REVW-05 | Code review task, not testable | Review `agent_service.py` gather sites, document current session flow |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
