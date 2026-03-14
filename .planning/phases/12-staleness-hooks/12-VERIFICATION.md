---
phase: 12-staleness-hooks
verified: 2026-03-14T15:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 12: Staleness Hooks Verification Report

**Phase Goal:** Implement staleness hooks so breakdown results auto-invalidate when scripts change, and clear when extraction succeeds
**Verified:** 2026-03-14T15:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | PATCH phase_data for a write or scenes phase sets breakdown_stale=true when a breakdown exists | VERIFIED | `phase_data.py` lines 199-200: `if phase in BREAKDOWN_SENSITIVE_PHASES: _mark_breakdown_stale(db, project_id)` before `db.commit()` |
| 2  | PATCH phase_data for idea or story phases does NOT set breakdown_stale | VERIFIED | Guard is exclusive to `BREAKDOWN_SENSITIVE_PHASES = {"write", "scenes"}` (line 17); test_patch_non_write_phase_no_stale passes |
| 3  | apply_wizard_result_to_db() for script_writer_wizard sets breakdown_stale=true | VERIFIED | `wizards.py` line 244: `_mark_breakdown_stale(db, project.id)` called before `db.commit()` inside the `script_writer_wizard` branch |
| 4  | Creating, updating, or deleting a scene ListItem sets breakdown_stale=true | VERIFIED | `list_items.py` lines 112-115 (create), 142-145 (update), 163-166 (delete): `_is_scene_item()` guard + `_mark_breakdown_stale()` + `db.commit()` in all three endpoints |
| 5  | None of the above triggers stale when no BreakdownElement exists for the project | VERIFIED | `_mark_breakdown_stale()` queries BreakdownElement first (`has_breakdown` check at line 26-29); only proceeds if found |
| 6  | A successful extraction clears breakdown_stale to false on the project | VERIFIED | `breakdown_service.py` lines 468-473: `stale_project.breakdown_stale = False` inserted between `_record_run()` and `db.commit()` in the success path |
| 7  | breakdown_stale is cleared in the same transaction as the extraction commit (atomic) | VERIFIED | The clear is inside the try block before the single `db.commit()` at line 476; no second commit used |
| 8  | A completed breakdown_runs audit record is created on successful extraction | VERIFIED | `_record_run(db, project_id, "completed", ...)` called at step 6; test_extraction_clears_stale confirms BreakdownRun with status="completed" exists |
| 9  | A failed extraction does NOT clear the stale flag | VERIFIED | `except` block in `breakdown_service.py` lines 479-484: rollback executed, stale-clear block is in the try scope only; test_failed_extraction_does_not_clear_stale passes |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/endpoints/phase_data.py` | `_mark_breakdown_stale()` helper + `BREAKDOWN_SENSITIVE_PHASES` guard in `update_subsection_data` | VERIFIED | Helper at lines 20-35; constant at line 17; call at lines 199-200. Substantive (205 lines). Wired: imported by `wizards.py` line 13 and `list_items.py` line 10 |
| `backend/app/api/endpoints/wizards.py` | Staleness hook inside `script_writer_wizard` branch of `apply_wizard_result_to_db` | VERIFIED | Line 13: `from .phase_data import _mark_breakdown_stale`. Line 244: called before `db.commit()` inside `script_writer_wizard` block. Substantive (289 lines) |
| `backend/app/api/endpoints/list_items.py` | `_is_scene_item()` guard + staleness hook in create/update/delete endpoints | VERIFIED | `_is_scene_item()` at lines 43-53; hooks in create (112-115), update (142-145), delete (163-166). Import at line 10 |
| `backend/app/tests/test_staleness.py` | Integration tests for SYNC-03 (8 cases) + SYNC-04 (2 cases) = 10 total | VERIFIED | 356 lines. 10 test methods in `TestStalenessHooks`. All 10 pass (130/130 full suite passes) |
| `backend/app/services/breakdown_service.py` | `breakdown_stale = False` set before the single `db.commit()` in `extract()` | VERIFIED | Lines 468-473: stale-clear block between `_record_run()` and `db.commit()` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `phase_data.py update_subsection_data` | `_mark_breakdown_stale()` | Called before `db.commit()` when phase in `BREAKDOWN_SENSITIVE_PHASES` | WIRED | Lines 199-202: guard → helper → commit |
| `wizards.py apply_wizard_result_to_db script_writer_wizard branch` | `_mark_breakdown_stale()` | Called before `db.commit()` in the `script_writer_wizard` block | WIRED | Line 244: `_mark_breakdown_stale(db, project.id)` then `db.commit()` at line 245 |
| `list_items.py create/update/delete endpoints` | `_mark_breakdown_stale()` | `_is_scene_item()` check before marking stale | WIRED | Pattern present in all three endpoints; phase_data_id captured before delete |
| `breakdown_service.py extract() success path` | `project.breakdown_stale = False` | Inserted between `_record_run()` (step 6) and `db.commit()` (step 7) | WIRED | Line 473: `stale_project.breakdown_stale = False` |
| `extract() success path` | `breakdown_runs` audit record | `_record_run()` called with `status='completed'` | WIRED | `_record_run(db, project_id, "completed", ...)` at lines 454-466 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SYNC-03 | 12-01-PLAN.md | Staleness detection — saving screenplay content or regenerating scenes sets `breakdown_stale=true` on the project | SATISFIED | `_mark_breakdown_stale()` wired into phase_data PATCH (write/scenes), wizards apply (script_writer_wizard), and list_items CRUD (scene_list). 8 SYNC-03 tests all pass |
| SYNC-04 | 12-02-PLAN.md | Re-extraction clears the stale flag and creates a new `breakdown_runs` audit record | SATISFIED | `breakdown_service.extract()` clears `breakdown_stale=False` atomically before single `db.commit()`. BreakdownRun with status="completed" recorded. 2 SYNC-04 tests pass |

No orphaned requirements found for Phase 12 in REQUIREMENTS.md.

---

### Anti-Patterns Found

No anti-patterns found. The one `return []` detected (wizards.py line 50) is a legitimate early-exit guard in `_get_character_data()` when no characters PhaseData exists — not a stub.

---

### Human Verification Required

None. All behaviors are programmatically verifiable through integration tests. The staleness flag is a boolean database column, fully testable without UI.

---

### Commit Verification

All four commits documented in summaries exist in git history:

| Commit | Type | Description |
|--------|------|-------------|
| `b6a630b` | feat | Add `_mark_breakdown_stale` helper and wire phase_data + wizards |
| `a634bda` | feat | Hook list_items CRUD with staleness and complete SYNC-03 test suite |
| `934e7ab` | test | Add failing SYNC-04 tests (RED) |
| `3aebb47` | feat | Clear `breakdown_stale` atomically in `extract()` success path (GREEN) |

---

### Test Suite Results

```
app/tests/test_staleness.py — 10 passed
Full backend suite — 130 passed, 0 failed
```

---

### Gaps Summary

None. All truths verified, all artifacts substantive and wired, all key links confirmed in source code, both requirement IDs fully satisfied by passing integration tests.

---

_Verified: 2026-03-14T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
