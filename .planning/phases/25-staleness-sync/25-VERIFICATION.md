---
phase: 25-staleness-sync
verified: 2026-03-20T17:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 25: Staleness Sync Verification Report

**Phase Goal:** Script changes are detected and the shotlist is flagged as stale, keeping breakdown mode in sync with screenplay edits
**Verified:** 2026-03-20T17:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                       | Status     | Evidence                                                                                               |
|----|---------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------|
| 1  | Saving script content (PATCH write/scenes phase) sets shotlist_stale=True on the project    | VERIFIED   | `update_subsection_data` calls `_mark_shotlist_stale` when `phase in SHOTLIST_SENSITIVE_PHASES` (phase_data.py line 219-220) |
| 2  | Generating script via script_writer_wizard sets shotlist_stale=True                         | VERIFIED   | `_mark_shotlist_stale(db, project.id)` at wizards.py line 275, after script_writer_wizard branch       |
| 3  | Generating scenes via scene_wizard sets shotlist_stale=True                                 | VERIFIED   | `_mark_shotlist_stale(db, project.id)` at wizards.py line 319, after scene_wizard branch               |
| 4  | Creating, updating, or deleting a character list item sets shotlist_stale=True              | VERIFIED   | `_is_character_item` + `_mark_shotlist_stale` in all three CRUD handlers in list_items.py (lines 131-134, 167-170, 194-197) |
| 5  | Creating, updating, or deleting a scene list item sets shotlist_stale=True                  | VERIFIED   | Dual hook in all three handlers: both `_mark_shotlist_stale` and `_mark_breakdown_stale` for scene items (list_items.py lines 125-129, 161-165, 188-192) |
| 6  | No staleness flag set when no shots exist for the project                                    | VERIFIED   | `_mark_shotlist_stale` guards on `has_shots` check — only flags if at least one `Shot` row exists (phase_data.py lines 45-53) |
| 7  | GET status endpoint returns shotlist_stale and shot_count                                   | VERIFIED   | `get_shotlist_status` at shots.py lines 76-90 returns `{"shotlist_stale": ..., "shot_count": ...}`     |
| 8  | POST acknowledge-stale endpoint clears shotlist_stale flag                                  | VERIFIED   | `acknowledge_shotlist_stale` at shots.py lines 93-103 sets `project.shotlist_stale = False`            |
| 9  | Breakdown mode displays an amber staleness banner when shotlist_stale is true and shots > 0 | VERIFIED   | BreakdownLayout.tsx line 236 conditional: `shotlistStatus?.shotlist_stale && shotlistStatus.shot_count > 0` |
| 10 | Clicking dismiss calls acknowledge-stale and removes the banner                             | VERIFIED   | `dismissStaleMutation.mutate()` on dismiss, `queryClient.invalidateQueries` on success (BreakdownLayout.tsx lines 78-81) |
| 11 | Banner does not appear when shotlist_stale is false or no shots exist                       | VERIFIED   | Both conditions required in JSX conditional (line 236); guard also enforced at backend `_mark_shotlist_stale` |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact                                                              | Expected                                                          | Status     | Details                                                          |
|-----------------------------------------------------------------------|-------------------------------------------------------------------|------------|------------------------------------------------------------------|
| `backend/app/api/endpoints/phase_data.py`                            | `_mark_shotlist_stale` helper + `SHOTLIST_SENSITIVE_PHASES`       | VERIFIED   | Both present at lines 18, 39-53; guard uses `database.Shot`      |
| `backend/app/api/endpoints/shots.py`                                 | `get_shotlist_status` + `acknowledge_shotlist_stale` endpoints    | VERIFIED   | Both present, routes ordered before `/{project_id}/{shot_id}`    |
| `backend/app/tests/test_shotlist_staleness.py`                       | Integration tests (min 150 lines, 13+ test methods)              | VERIFIED   | 416 lines, exactly 13 test methods, all 13 pass                  |
| `frontend/src/components/Breakdown/ShotlistStalenessBar.tsx`         | Amber warning banner component                                    | VERIFIED   | 28 lines, substantive, exports `ShotlistStalenessBar`            |
| `frontend/src/components/Breakdown/BreakdownLayout.tsx`              | Integration of staleness banner in center panel                   | VERIFIED   | `shotlist-status` query, `ShotlistStalenessBar` render wired     |
| `frontend/src/lib/api.tsx`                                           | `getShotlistStatus` + `acknowledgeShotlistStale` API functions    | VERIFIED   | Both at lines 922-937; correct URL patterns                      |

---

### Key Link Verification

| From                                  | To                                        | Via                                    | Status     | Details                                                             |
|---------------------------------------|-------------------------------------------|----------------------------------------|------------|---------------------------------------------------------------------|
| `phase_data.py`                       | `wizards.py`                              | `import _mark_shotlist_stale`          | WIRED      | Line 14: `from .phase_data import _mark_breakdown_stale, _mark_shotlist_stale` |
| `phase_data.py`                       | `list_items.py`                           | `import _mark_shotlist_stale`          | WIRED      | Line 10: `from .phase_data import _mark_breakdown_stale, _mark_shotlist_stale` |
| `phase_data.py`                       | `database.Shot`                           | Shot model query for guard condition   | WIRED      | Lines 45-47: `db.query(database.Shot).filter(...)` in `_mark_shotlist_stale` |
| `BreakdownLayout.tsx`                 | `api.tsx`                                 | `useQuery` calling `getShotlistStatus` | WIRED      | Lines 70-75: `queryFn: () => api.getShotlistStatus(projectId!)`    |
| `BreakdownLayout.tsx`                 | `ShotlistStalenessBar.tsx`                | Conditional render on `shotlist_stale` | WIRED      | Lines 236-240: component rendered when stale and shot_count > 0    |
| `api.tsx`                             | Backend `/api/shots/{project_id}/status` | `fetchWithTimeout` GET                 | WIRED      | Line 923: URL is `/shots/${projectId}/status`                      |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                         | Status    | Evidence                                                              |
|-------------|-------------|-------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------|
| SYNC-01     | 25-01-PLAN  | Script content changes (save/generate) set `shotlist_stale = true` on the project  | SATISFIED | `_mark_shotlist_stale` wired into PATCH phase_data + wizard branches  |
| SYNC-02     | 25-02-PLAN  | Breakdown mode shows a staleness banner when shotlist is stale                      | SATISFIED | `ShotlistStalenessBar` rendered conditionally in `BreakdownLayout`    |
| SYNC-03     | 25-01-PLAN  | Character name changes propagate to Breakdown via staleness pattern                 | SATISFIED | `_is_character_item` + `_mark_shotlist_stale` in list_items CRUD      |
| SYNC-04     | 25-01-PLAN  | Staleness hooks placed in same locations as v2.0 breakdown_stale hooks              | SATISFIED | Dual hooks in scene CRUD; character adds shotlist_stale-only hook     |

All 4 requirements satisfied. No orphaned requirements detected (REQUIREMENTS.md confirms all 4 map to Phase 25, all 4 claimed by plans).

---

### Anti-Patterns Found

No anti-patterns detected across any phase 25 modified files:

- No TODO/FIXME/PLACEHOLDER comments in any modified file
- No stub implementations (empty returns, console.log-only handlers)
- No disconnected wiring — all imports and usages traced end-to-end
- Route ordering in shots.py is correct: `/status` and `/acknowledge-stale` are defined before the `/{project_id}/{shot_id}` catch-all, preventing FastAPI route shadowing

---

### Test Suite Status

- `test_shotlist_staleness.py`: **13/13 passed** (0.30s)
- Full backend suite (excluding pre-existing failures): **204/204 passed**
- Pre-existing failures confirmed pre-date phase 25:
  - `test_session_isolation.py::test_orchestrate_uses_session_factory` — introduced in phase 4
  - `test_yolo_integration.py::test_yolo_wizard_routes_through_middleware` — introduced in phase 8 (passes individually, likely environment-dependent)
- Neither failure was introduced by phase 25 changes

---

### Human Verification Required

#### 1. Staleness Banner End-to-End Flow

**Test:** Create shots in breakdown mode, edit script in screenwriting mode, return to breakdown mode
**Expected:** Amber banner appears at top of Shotlist panel with dismiss button; banner disappears on dismiss; banner reappears if script is edited again
**Why human:** Visual appearance, real-time polling behavior, and user flow completion cannot be verified programmatically

---

### Gaps Summary

No gaps. All automated checks pass. All 11 observable truths are verified with direct code evidence. All 4 requirements are satisfied. The only remaining verification is the end-to-end visual/behavioral flow in the browser, which was reportedly approved by the user during plan execution (25-02-SUMMARY.md Task 3 human-verify checkpoint).

---

_Verified: 2026-03-20T17:00:00Z_
_Verifier: Claude (gsd-verifier)_
