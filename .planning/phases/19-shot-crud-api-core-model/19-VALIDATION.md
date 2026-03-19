---
phase: 19
slug: shot-crud-api-core-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shots.py -x -q` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/test_shots.py -x -q`
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 0 | SHOT-01 | unit | `pytest app/tests/test_shots.py -x -q` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | SHOT-01 | integration | `pytest app/tests/test_shots.py::TestShotsAPI::test_create_shot -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | SHOT-02 | integration | `pytest app/tests/test_shots.py::TestShotsAPI::test_create_shot_fields -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 1 | DATA-04 | integration | `pytest app/tests/test_shots.py::TestShotsAPI::test_list_shots -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 1 | DATA-04 | integration | `pytest app/tests/test_shots.py::TestShotsAPI::test_update_shot -x` | ❌ W0 | ⬜ pending |
| 19-01-06 | 01 | 1 | DATA-04 | integration | `pytest app/tests/test_shots.py::TestShotsAPI::test_delete_shot -x` | ❌ W0 | ⬜ pending |
| 19-01-07 | 01 | 1 | SHOT-01 | integration | `pytest app/tests/test_shots.py::TestShotsAPI::test_reorder_shots -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_shots.py` — stub test file with test class and placeholder tests for all CRUD endpoints + reorder
- [ ] `backend/app/tests/conftest.py` — verify Shot/ShotElement fixtures exist or add them

*Existing pytest infrastructure covers the framework; only test stubs for the new endpoint are new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shot fields JSONB stores all 13 standard fields correctly | SHOT-02 | Requires DB inspection | Create shot with all fields, inspect DB record via psql or admin tool |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
