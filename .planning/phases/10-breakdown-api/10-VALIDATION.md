---
phase: 10
slug: breakdown-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 with FastAPI TestClient |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_breakdown_api.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_breakdown_api.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | API-02 | integration | `pytest app/tests/test_breakdown_api.py::test_list_elements_excludes_deleted -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | API-02 | integration | `pytest app/tests/test_breakdown_api.py::test_list_elements_filter_by_category -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | API-03 | integration | `pytest app/tests/test_breakdown_api.py::test_update_element_sets_user_modified -x` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | API-04 | integration | `pytest app/tests/test_breakdown_api.py::test_create_element_source_user -x` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 1 | API-04 | integration | `pytest app/tests/test_breakdown_api.py::test_create_element_duplicate_conflict -x` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 1 | API-05 | integration | `pytest app/tests/test_breakdown_api.py::test_delete_element_soft_deletes -x` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | API-06 | integration | `pytest app/tests/test_breakdown_api.py::test_add_scene_link -x` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | API-06 | integration | `pytest app/tests/test_breakdown_api.py::test_remove_scene_link -x` | ❌ W0 | ⬜ pending |
| 10-02-03 | 02 | 1 | API-07 | integration | `pytest app/tests/test_breakdown_api.py::test_summary_returns_counts -x` | ❌ W0 | ⬜ pending |
| 10-02-04 | 02 | 1 | API-01 | integration | `pytest app/tests/test_breakdown_api.py::test_extract_creates_pending_run -x` | ❌ W0 | ⬜ pending |
| 10-02-05 | 02 | 1 | API-01 | integration | `pytest app/tests/test_breakdown_api.py::test_extract_response_shape -x` | ❌ W0 | ⬜ pending |
| 10-02-06 | 02 | 1 | ALL | integration | `pytest app/tests/test_breakdown_api.py::test_no_auth_returns_403 -x` | ❌ W0 | ⬜ pending |
| 10-02-07 | 02 | 1 | ALL | integration | `pytest app/tests/test_breakdown_api.py::test_nonexistent_project_404 -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_breakdown_api.py` — stubs for API-01 through API-07 (endpoint integration tests)
- [ ] `backend/app/api/endpoints/breakdown.py` — router file must exist for tests to import
- [ ] No new conftest fixtures needed (existing `client`, `db_session`, `mock_auth_headers` fixtures sufficient)
- [ ] No new framework install needed

*Existing infrastructure covers framework and fixture requirements.*

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
