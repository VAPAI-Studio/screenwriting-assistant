---
phase: 5
slug: agent-review-middleware
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `backend/pytest.ini` or pyproject.toml (existing) |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_agent_review_middleware.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_agent_review_middleware.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | REVW-04 | unit | `pytest app/tests/test_agent_review_middleware.py::test_zero_agents_passthrough -x` | W0 | pending |
| 05-01-02 | 01 | 1 | REVW-02 | unit | `pytest app/tests/test_agent_review_middleware.py::test_parallel_fanout_uses_session_factory -x` | W0 | pending |
| 05-01-03 | 01 | 1 | REVW-01-partial | unit | `pytest app/tests/test_agent_review_middleware.py::test_review_returns_result_with_agents_consulted -x` | W0 | pending |
| 05-01-04 | 01 | 1 | REVW-02 | unit | `pytest app/tests/test_agent_review_middleware.py::test_failed_agent_review_filtered_out -x` | W0 | pending |
| 05-01-05 | 01 | 1 | REVW-02 | unit | `pytest app/tests/test_agent_review_middleware.py::test_all_agents_fail_returns_raw_output -x` | W0 | pending |
| 05-02-01 | 02 | 2 | REVW-03 | unit | `pytest app/tests/test_agent_review_middleware.py::test_merge_preserves_idea_wizard_schema -x` | W0 | pending |
| 05-02-02 | 02 | 2 | REVW-03 | unit | `pytest app/tests/test_agent_review_middleware.py::test_merge_preserves_scene_wizard_schema -x` | W0 | pending |
| 05-02-03 | 02 | 2 | REVW-03 | unit | `pytest app/tests/test_agent_review_middleware.py::test_merge_preserves_script_wizard_schema -x` | W0 | pending |
| 05-02-04 | 02 | 2 | REVW-03 | unit | `pytest app/tests/test_agent_review_middleware.py::test_merge_invalid_schema_falls_back_to_raw -x` | W0 | pending |
| 05-02-05 | 02 | 2 | REVW-01-partial | unit | `pytest app/tests/test_agent_review_middleware.py::test_agents_consulted_has_summary -x` | W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_agent_review_middleware.py` — stubs for REVW-01 through REVW-04
- [ ] No new framework install needed — pytest and pytest-asyncio already present
- [ ] No new conftest fixtures needed — existing `db_session`, `make_agent`, and mock patterns sufficient

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Timing: N agents take ~1x not N*x time | REVW-02 | Timing assertions are flaky in CI | Run `pytest app/tests/test_agent_review_middleware.py::test_parallel_fanout_uses_session_factory -x -s` and verify timing output shows concurrent execution |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
