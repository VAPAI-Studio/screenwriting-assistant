---
phase: 12-staleness-hooks
plan: 01
subsystem: api
tags: [staleness, breakdown, sqlite, sqlalchemy, tdd, fastapi]

# Dependency graph
requires:
  - phase: 11-ai-extraction-service
    provides: BreakdownElement model and extraction pipeline that writes breakdown data
  - phase: 09-breakdown-data-foundation
    provides: Project.breakdown_stale column, BreakdownElement table
provides:
  - _mark_breakdown_stale() helper in phase_data.py (imported by wizards.py and list_items.py)
  - BREAKDOWN_SENSITIVE_PHASES constant ("write", "scenes")
  - Staleness hook in update_subsection_data (phase_data PATCH)
  - Staleness hook in apply_wizard_result_to_db (script_writer_wizard branch)
  - _is_scene_item() helper in list_items.py
  - Staleness hooks in create/update/delete list item endpoints (scene_list items only)
  - test_staleness.py with 8 SYNC-03 integration tests (all passing)
affects:
  - 12-02-staleness-api (GET /breakdown/stale endpoint reads breakdown_stale)
  - 13-ui-staleness-banner (frontend reads stale flag to show banner)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_mark_breakdown_stale helper: query-before-set, no commit, caller commits"
    - "str() cast on all UUID filter parameters for SQLite/PostgreSQL compatibility"
    - "One-commit rule: mark stale then existing commit covers it (no extra commit)"
    - "_is_scene_item guard: only scenes phase + scene_list subsection triggers stale"

key-files:
  created:
    - backend/app/tests/test_staleness.py
  modified:
    - backend/app/api/endpoints/phase_data.py
    - backend/app/api/endpoints/wizards.py
    - backend/app/api/endpoints/list_items.py

key-decisions:
  - "Helper does NOT commit; caller's existing commit covers breakdown_stale change (one-commit rule)"
  - "Import _mark_breakdown_stale from phase_data into wizards.py and list_items.py (no circular imports)"
  - "str() cast on UUID filter params in all three endpoint files for SQLite/PostgreSQL compat"
  - "_is_scene_item returns PhaseData object (not bool) so caller has project_id for _mark_breakdown_stale"

patterns-established:
  - "str(project_id) pattern: all SQLAlchemy filter UUIDs cast to str() for SQLite compat"
  - "Staleness guard pattern: check BreakdownElement exists before setting breakdown_stale"
  - "TDD RED-GREEN flow: write failing tests first, then implement, confirm all pass"

requirements-completed: [SYNC-03]

# Metrics
duration: 20min
completed: 2026-03-14
---

# Phase 12 Plan 01: Staleness Hooks Summary

**breakdown_stale flag wired to three trigger points: phase_data PATCH (write/scenes only), script_writer_wizard apply, and scene_list ListItem CRUD -- with 8 SYNC-03 integration tests all passing**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-14T13:45:41Z
- **Completed:** 2026-03-14T14:06:00Z
- **Tasks:** 2
- **Files modified:** 4 (3 endpoint files + 1 new test file)

## Accomplishments
- Added `_mark_breakdown_stale(db, project_id)` helper in `phase_data.py` that queries BreakdownElement and sets `Project.breakdown_stale=True` only when a non-deleted breakdown exists
- Wired staleness into `update_subsection_data` (guarded by `BREAKDOWN_SENSITIVE_PHASES = {"write", "scenes"}`) and `apply_wizard_result_to_db` (guarded by `wizard_type == "script_writer_wizard"`)
- Added `_is_scene_item()` helper and staleness hooks in `create_list_item`, `update_list_item`, and `delete_list_item` (guarded by `phase == "scenes"` and `subsection_key == "scene_list"`)
- Created `test_staleness.py` with 8 SYNC-03 integration tests covering all trigger points and the no-stale-without-breakdown guard -- all 128 tests in the full suite pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _mark_breakdown_stale helper and hook phase_data + wizards** - `b6a630b` (feat)
2. **Task 2: Hook list_items CRUD and create test_staleness.py with all SYNC-03 cases** - `a634bda` (feat)

**Plan metadata:** `[pending]` (docs: complete plan)

_Note: TDD tasks - RED tests written first, GREEN implementation made them pass_

## Files Created/Modified
- `backend/app/api/endpoints/phase_data.py` - Added `BREAKDOWN_SENSITIVE_PHASES`, `_mark_breakdown_stale()` helper, staleness call in `update_subsection_data`; fixed `str()` UUID casts throughout
- `backend/app/api/endpoints/wizards.py` - Imported `_mark_breakdown_stale`, added call before `db.commit()` in `script_writer_wizard` branch
- `backend/app/api/endpoints/list_items.py` - Added `_is_scene_item()` helper, staleness hooks in create/update/delete; fixed `str()` UUID casts in ownership verifiers
- `backend/app/tests/test_staleness.py` - New file with 8 SYNC-03 integration tests (TestStalenessHooks class)

## Decisions Made
- Helper does NOT commit -- caller's existing commit covers the `breakdown_stale` change (one-commit rule from research)
- Import `_mark_breakdown_stale` from `phase_data` module into `wizards.py` and `list_items.py` (no circular import risk; `phase_data.py` does not import from either)
- `_is_scene_item()` returns `PhaseData | None` (not bool) so callers have `project_id` available for the stale call
- Tests use `_create_project_via_api()` for API-tested cases to ensure correct owner_id storage in SQLite

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing str() UUID casts across three endpoint files**
- **Found during:** Task 1 (test_patch_write_phase_sets_stale failing with 404)
- **Issue:** `_verify_project_ownership` in `phase_data.py` filtered with raw UUID objects; SQLite adapter was insufficient for filter equality when projects were created via API (UUID returned as string from JSON). Same issue existed in `list_items.py` ownership helpers.
- **Fix:** Added `str()` casts to all UUID filter parameters in `_verify_project_ownership` (phase_data.py), `update_subsection_data` PhaseData query, `_verify_phase_data_ownership` (list_items.py), and `_verify_item_ownership` (list_items.py). This matches the pattern already established in `breakdown.py`.
- **Files modified:** `backend/app/api/endpoints/phase_data.py`, `backend/app/api/endpoints/list_items.py`
- **Verification:** 8 SYNC-03 tests pass; 128-test full suite passes
- **Committed in:** b6a630b (Task 1), a634bda (Task 2)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Auto-fix necessary for SQLite test compat. Pattern already established in breakdown.py; applied consistently to phase_data.py and list_items.py. No scope creep.

## Issues Encountered
- Initial test failures due to missing `str()` casts in UUID filter comparisons -- resolved by applying the established `str(project_id)` pattern from `breakdown.py` to `phase_data.py` and `list_items.py`

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Staleness hook infrastructure complete: `breakdown_stale` is now set whenever write/scenes content changes
- Ready for Phase 12 Plan 02: API endpoint to expose `breakdown_stale` flag for frontend consumption
- Ready for Phase 13 UI: frontend staleness banner can read the flag

---
*Phase: 12-staleness-hooks*
*Completed: 2026-03-14*
