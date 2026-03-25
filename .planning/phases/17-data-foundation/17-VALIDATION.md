---
phase: 17
slug: data-foundation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 17 — Validation Strategy

> Retroactively created 2026-03-25. Phase completed 2026-03-19.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shotlist_models.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short` |
| **Estimated runtime** | ~0.1s |

---

## Sampling Rate

- **After every task commit:** Run quick pytest command
- **After every plan wave:** Run full suite
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 17-01-01 | Shot, ShotElement, AssetMedia importable from database module | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_importable app/tests/test_shotlist_models.py::test_shot_element_importable app/tests/test_shotlist_models.py::test_asset_media_importable -q` | ✅ verified |
| 17-01-02 | Shot/ShotElement/AssetMedia tables registered in SQLAlchemy metadata | pytest | `pytest app/tests/test_shotlist_models.py::test_tables_in_metadata -q` | ✅ verified |
| 17-01-03 | Project.shotlist_stale column exists and defaults to False | pytest | `pytest app/tests/test_shotlist_models.py::test_project_shotlist_stale -q` | ✅ verified |
| 17-01-04 | Shot ORM round-trip (create, query, verify all fields) | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_orm_roundtrip -q` | ✅ verified |
| 17-01-05 | Shot.scene_item_id SET NULL on scene delete (no cascade) | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_scene_set_null -q` | ✅ verified |
| 17-01-06 | Shots cascade delete with project | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_cascade_delete -q` | ✅ verified |
| 17-01-07 | ShotElement (shot_id, element_id) unique constraint enforced | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_element_unique -q` | ✅ verified |
| 17-01-08 | AssetMedia ORM round-trip | pytest | `pytest app/tests/test_shotlist_models.py::test_asset_media_orm_roundtrip -q` | ✅ verified |
| 17-01-09 | AssetMedia dual FK (project_id + element_id, both nullable) | pytest | `pytest app/tests/test_shotlist_models.py::test_asset_media_dual_fk -q` | ✅ verified |
| 17-01-10 | Project cascade to shots | pytest | `pytest app/tests/test_shotlist_models.py::test_project_cascade_to_shots -q` | ✅ verified |
| 17-01-11 | ShotCreate Pydantic schema validates valid input | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_create_valid -q` | ✅ verified |
| 17-01-12 | ShotCreate rejects invalid source value | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_create_invalid_source -q` | ✅ verified |
| 17-01-13 | ShotUpdate partial schema accepts subset of fields | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_update_partial -q` | ✅ verified |
| 17-01-14 | ShotResponse constructs from ORM instance | pytest | `pytest app/tests/test_shotlist_models.py::test_shot_response_from_orm -q` | ✅ verified |
| 17-01-15 | AssetMediaResponse metadata alias serialization | pytest | `pytest app/tests/test_shotlist_models.py::test_asset_media_response_metadata_alias -q` | ✅ verified |
| 17-01-16 | ScriptRange schema accepts start/end indices | pytest | `pytest app/tests/test_shotlist_models.py::test_script_range_schema -q` | ✅ verified |

---

## Manual-Only Verifications

None — all Phase 17 deliverables (ORM models, Pydantic schemas, migration SQL) are fully covered by pytest.

> **Note:** `backend/migrations/delta/002_shotlist_tables.sql` has no dedicated migration test, but its DDL correctness is implicitly validated by the ORM round-trip tests (models must match the schema or tests fail).

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] All 18 tests confirmed passing (18 passed in 0.07s)
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive
