---
phase: 25
slug: staleness-sync
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 25 — Validation Strategy

> Retroactively created 2026-03-25. Phase completed 2026-03-19.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + TypeScript tsc (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shotlist_staleness.py app/tests/test_staleness.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short && cd ../frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~1s |

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 25-01-01 | ShotlistStalenessBar.tsx compiles without errors | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 25-01-02 | Patching write phase sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_patch_write_phase_sets_shotlist_stale -q` | ✅ verified |
| 25-01-03 | Patching scenes phase sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_patch_scenes_phase_sets_shotlist_stale -q` | ✅ verified |
| 25-01-04 | Script wizard run sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_script_wizard_sets_shotlist_stale -q` | ✅ verified |
| 25-01-05 | Scene wizard run sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_scene_wizard_sets_shotlist_stale -q` | ✅ verified |
| 25-01-06 | shotlist_stale not set when project has no shots | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_no_stale_without_shots -q` | ✅ verified |
| 25-01-07 | Creating a scene sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_create_scene_sets_shotlist_stale -q` | ✅ verified |
| 25-01-08 | Updating a scene sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_update_scene_sets_shotlist_stale -q` | ✅ verified |
| 25-01-09 | Deleting a scene sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_delete_scene_sets_shotlist_stale -q` | ✅ verified |
| 25-01-10 | Creating a character sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_create_character_sets_shotlist_stale -q` | ✅ verified |
| 25-01-11 | Updating a character sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_update_character_sets_shotlist_stale -q` | ✅ verified |
| 25-01-12 | Deleting a character sets shotlist_stale=True | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_delete_character_sets_shotlist_stale -q` | ✅ verified |
| 25-01-13 | GET /shotlist-status returns current shotlist_stale value | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_get_shotlist_status -q` | ✅ verified |
| 25-01-14 | POST /shotlist-acknowledge clears shotlist_stale flag | pytest | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_acknowledge_clears_stale -q` | ✅ verified |
| 25-02-01 | Patching write phase sets breakdown stale flag | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_write_phase_sets_stale -q` | ✅ verified |
| 25-02-02 | Patching scenes phase sets breakdown stale flag | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_scenes_phase_sets_stale -q` | ✅ verified |
| 25-02-03 | Patching non-write phase does not set stale | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_non_write_phase_no_stale -q` | ✅ verified |
| 25-02-04 | Script wizard sets breakdown stale | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_script_wizard_sets_stale -q` | ✅ verified |
| 25-02-05 | Scene wizard sets breakdown stale | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_scene_wizard_sets_stale -q` | ✅ verified |
| 25-02-06 | Creating a scene sets breakdown stale | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_create_scene_sets_stale -q` | ✅ verified |
| 25-02-07 | Updating a scene sets breakdown stale | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_update_scene_sets_stale -q` | ✅ verified |
| 25-02-08 | Deleting a scene sets breakdown stale | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_delete_scene_sets_stale -q` | ✅ verified |
| 25-02-09 | Successful breakdown extraction clears stale flag | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_extraction_clears_stale -q` | ✅ verified |
| 25-02-10 | Failed breakdown extraction does not clear stale flag | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_failed_extraction_does_not_clear_stale -q` | ✅ verified |
| 25-02-11 | Stale not set when project has no breakdown | pytest | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_no_stale_without_breakdown -q` | ✅ verified |

---

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| ShotlistStalenessBar appears in BreakdownLayout when shotlist is stale | React Query polling + conditional render |
| Dismissing ShotlistStalenessBar calls acknowledge endpoint and hides bar | React mutation + state update |
| StalenessBar (breakdown) shows when breakdown is stale after script edit | React Query + StalenessBar component render |

---

## Key Files

| File | What it delivers |
|------|-----------------|
| `frontend/src/components/Breakdown/ShotlistStalenessBar.tsx` | Banner shown when shotlist needs regeneration; dismiss calls acknowledge |
| `frontend/src/components/Breakdown/StalenessBar.tsx` | Banner shown when breakdown needs re-extraction |
| `backend/app/tests/test_shotlist_staleness.py` | 13 tests: shotlist_stale hooks across all write operations |
| `backend/app/tests/test_staleness.py` | 11 tests: breakdown stale hooks across all write operations |

---

## Validation Sign-Off

- [x] All 25 tasks have automated verify
- [x] All 13 shotlist staleness tests confirmed passing
- [x] All 11 breakdown staleness tests confirmed passing
- [x] TypeScript compiles clean
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive
