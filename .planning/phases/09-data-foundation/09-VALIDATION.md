---
phase: 9
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_breakdown_models.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_breakdown_models.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | BKDN-01 | unit | `pytest app/tests/test_breakdown_models.py::test_breakdown_element_importable -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | BKDN-01 | unit | `pytest app/tests/test_breakdown_models.py::test_element_soft_delete -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | BKDN-02 | unit | `pytest app/tests/test_breakdown_models.py::test_scene_link_cascade -x` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 1 | BKDN-03 | unit | `pytest app/tests/test_breakdown_models.py::test_breakdown_run_importable -x` | ❌ W0 | ⬜ pending |
| 09-01-05 | 01 | 1 | BKDN-04 | unit | `pytest app/tests/test_breakdown_models.py::test_project_breakdown_stale -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | ALL | unit | `pytest app/tests/test_breakdown_models.py::test_element_orm_roundtrip -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 1 | ALL | unit | `pytest app/tests/test_breakdown_models.py::test_tables_in_metadata -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_breakdown_models.py` — stubs for BKDN-01 through BKDN-04 (model importability, ORM round-trips, cascade behavior, schema validation)
- No new framework install needed (pytest already configured)
- No new conftest fixtures needed (existing `db_session`, `client`, `mock_auth_headers` fixtures sufficient; `_patch_uuid_columns_for_sqlite()` auto-handles new models)

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
