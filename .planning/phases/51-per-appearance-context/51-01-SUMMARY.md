---
phase: 51-per-appearance-context
plan: 01
subsystem: api
tags: [breakdown, scene-links, extraction, react, fastapi, sqlalchemy]

# Dependency graph
requires:
  - phase: 50-scene-text-extraction
    provides: scene-scoped extraction prompt + ExtractedSceneAppearance (scene_index, context)
provides:
  - ElementSceneLink.context populated with AI per-appearance context (was "")
  - _map_scene_indices_to_ids returns (scene_id, context) pairs
  - Card scene chips expose per-appearance context as a native hover tooltip
  - Tests proving APPR-02 context persistence and APPR-03 consolidation
affects: [breakdown-ui, future-breakdown-export, scene-level-reporting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Thread per-appearance metadata through the scene-id mapping boundary as (scene_id, context) tuples rather than bare ID lists"
    - "Graceful empty tooltip via title={value || undefined} (no 'undefined' string)"

key-files:
  created: []
  modified:
    - backend/app/services/breakdown_service.py
    - backend/app/tests/test_breakdown_service.py
    - frontend/src/components/Breakdown/ElementCard.tsx

key-decisions:
  - "Used Tuple[str, str] (scene_id, context) as the threading shape per D-51-01 — minimal, no schema change"
  - "APPR-03 verified-not-rebuilt: existing _deduplicate_elements already consolidates; test only asserts it (D-51-03)"
  - "Card chip tooltip via native title attribute, no popover dependency (D-51-02)"

patterns-established:
  - "Pattern 1: Per-appearance context flows AI -> _map_scene_indices_to_ids -> _reconcile_scene_links -> ElementSceneLink.context in one coupled change"
  - "Pattern 2: Empty/legacy link context renders as no-tooltip (title undefined)"

requirements-completed: [APPR-01, APPR-02, APPR-03]

# Metrics
duration: ~8min
completed: 2026-06-07
---

# Phase 51 Plan 01: Per-Appearance Context Summary

**ElementSceneLink.context now persists the AI's per-appearance context (no longer ""), threaded through the scene-id mapping boundary and surfaced as a card scene-chip hover tooltip.**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-06-07
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Backend threads `ExtractedSceneAppearance.context` through `_map_scene_indices_to_ids` (now returns `(scene_id, context)` pairs) into `_reconcile_scene_links`, which writes `context=context` instead of `context=""` (APPR-02 backend).
- Added APPR-02 context-persistence test (RED → GREEN) and APPR-03 consolidation verify test (one element, two scene links).
- Frontend card scene chips expose per-appearance context on hover via `title={link.context || undefined}` — graceful when empty (APPR-02 UI).
- All preserved behavior intact: single AI call, EXTRACTION_SYSTEM_PROMPT, `_deduplicate_elements` (APPR-03), `_upsert_elements` (user_modified/is_deleted), staleness clear, audit run, Phase 50 scene-scoped prompt, user-vs-ai link sourcing. No schema change, no migration, no new dependency.

## Task Commits

1. **Task 2 (RED): failing APPR-02 + APPR-03 tests** - `5acf56e` (test)
2. **Task 1 (GREEN): thread per-appearance context into ElementSceneLink** - `d2b99f7` (feat)
3. **Task 3: card scene-chip context tooltip** - `3d14f97` (feat)

_Note: Plan tasks 1 and 2 are TDD-coupled (test → feat); the consolidation test was already green at RED time, confirming APPR-03 is verify-not-rebuild._

## Files Created/Modified
- `backend/app/services/breakdown_service.py` - `_map_scene_indices_to_ids` returns `List[Tuple[str, str]]`; `_reconcile_scene_links` accepts `new_links: List[Tuple[str, str]]` and writes `context=context`; `extract()` caller variable renamed; `Tuple` added to typing import.
- `backend/app/tests/test_breakdown_service.py` - `test_scene_link_context_persisted` (APPR-02: link.context == AI context "Draws sword"/"Presents sword"); `test_appearance_consolidation_one_element_two_links` (APPR-03: one element, two links).
- `frontend/src/components/Breakdown/ElementCard.tsx` - scene chip `<button>` gains `title={link.context || undefined}`.

## Decisions Made
- None beyond plan — followed D-51-01..D-51-03 as specified.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. The out-of-range scene_index warning path and user-link skip logic were preserved unchanged.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None. The previously empty `context=""` write was the targeted gap and is now removed.

## Verification Results
- `pytest app/tests/test_breakdown_service.py -x -q` → **15 passed** (13 baseline + 2 new)
- `pytest app/tests/test_breakdown_api.py app/tests/test_staleness.py -q` → **48 passed** (no regression)
- `npm run build` (tsc && vite build) → **clean** (pre-existing chunk-size warning only, not an error)
- `grep -n 'context=context' breakdown_service.py` → present; `grep 'context=""'` → none

## Next Phase Readiness
- APPR-01/02/03 satisfied. Per-appearance context is persisted and surfaced in both detail (pre-existing) and card (this plan) views.
- No blockers. No schema/migration work outstanding.

## Self-Check: PASSED

All modified files and all task commits (5acf56e, d2b99f7, 3d14f97) verified present.

---
*Phase: 51-per-appearance-context*
*Completed: 2026-06-07*
