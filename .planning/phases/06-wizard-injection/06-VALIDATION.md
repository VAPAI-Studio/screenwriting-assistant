---
phase: 6
slug: wizard-injection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `backend/pytest.ini` (existing) |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_wizard_injection.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_wizard_injection.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REVW-01 | integration | `pytest app/tests/test_wizard_injection.py::test_wizard_injection_with_mapped_agents -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | REVW-01 | integration | `pytest app/tests/test_wizard_injection.py::test_agents_consulted_in_response -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | REVW-01 | integration | `pytest app/tests/test_wizard_injection.py::test_wizard_passthrough_no_agents -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | REVW-01 | unit | `pytest app/tests/test_agent_review_middleware.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_wizard_injection.py` — stubs for REVW-01 injection, metadata propagation, and pass-through
- No new framework install needed
- No new conftest fixtures needed — existing `db_session`, `mock_auth_headers`, and `owner_id` patterns are sufficient

*Existing Phase 5 middleware tests (10 tests in `test_agent_review_middleware.py`) cover middleware internals.*

---

## Manual-Only Verifications

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
