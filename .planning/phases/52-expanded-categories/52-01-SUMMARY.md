---
phase: 52-expanded-categories
plan: 01
subsystem: breakdown
tags: [taxonomy, breakdown, pydantic, fastapi, react, typescript, extraction-prompt]

# Dependency graph
requires:
  - phase: prior breakdown phases (9-13, 50, 51)
    provides: BreakdownCategory enum, EXTRACTION_SYSTEM_PROMPT, BreakdownElementCreate gate, FE CategoryTabs + constants
provides:
  - 10-category breakdown taxonomy (added set_dressing, animal, sfx, makeup_hair, extras) across all 6 definition sites in lockstep
  - Extended extraction prompt guidance (on-screen-only descriptions + precedence note) teaching the AI the new categories
  - Tests proving new-category accept + extract + persist with no regression
affects: [breakdown, shotlist, future-taxonomy-expansion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lockstep taxonomy: every category value defined identically across enum, schema regex gate, prompt (2 sites), FE union, and 3 FE category-keyed maps"
    - "tsc exhaustiveness as a build gate: growing the BreakdownCategory union forces matching keys in Record<BreakdownCategory,...> maps"

key-files:
  created: []
  modified:
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - backend/app/services/breakdown_service.py
    - frontend/src/types/index.ts
    - frontend/src/lib/constants.ts
    - backend/app/tests/test_breakdown_api.py
    - backend/app/tests/test_breakdown_service.py

key-decisions:
  - "Reused the generic prop-style 3-field shape for ELEMENT_EXTENDED_FIELDS of 4 new categories; extras uses a 'Headcount' field; animal/makeup_hair got natural owner labels (Handler/Artist)"
  - "Chose distinct Tailwind-400 hues for the 5 new CATEGORY_COLORS: set_dressing=teal, animal=orange, sfx=rose, makeup_hair=fuchsia, extras=slate"
  - "No migration (category stays String(50)); no existing category removed/renamed (CATG-02)"

patterns-established:
  - "Lockstep taxonomy edits: all 6 sites moved together; lockstep grep gate + tsc exhaustiveness catch drift"

requirements-completed: [CATG-01, CATG-02, CATG-03]

# Metrics
duration: ~12min
completed: 2026-06-07
---

# Phase 52 Plan 01: Expanded Categories Summary

**Broadened the breakdown element taxonomy from 5 to 10 categories (added set_dressing, animal, sfx, makeup_hair, extras) additively across all 6 backend/frontend definition sites in lockstep, with extended on-screen-only extraction-prompt guidance and tests proving new-category accept + extract + persist with no regression.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-07
- **Completed:** 2026-06-07
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Added 5 new categories to all 4 backend sites in lockstep: `BreakdownCategory` enum, the `BreakdownElementCreate.category` regex gate, the `EXTRACTION_SYSTEM_PROMPT` CATEGORIES list (+ precedence note), and the `ExtractedElement.category` structured-output description.
- Preserved the EXTRACTION_SYSTEM_PROMPT CRITICAL RULES + DEDUPLICATION blocks verbatim; new category descriptions are on-screen-only and the precedence note covers ridden-horse → animal and set_dressing-vs-prop.
- Added 5 new categories to all 3 frontend category-keyed structures (`BreakdownCategory` union, `BREAKDOWN_CATEGORIES`, exhaustive `CATEGORY_COLORS`, exhaustive `ELEMENT_EXTENDED_FIELDS`); `CategoryTabs.tsx` unchanged (auto-renders 10 tabs).
- Added tests proving schema accept (5 new) + reject (unknown), and a mocked extraction that persists a `set_dressing` element; existing tests untouched (no regression).
- No migration added; `category` column remains `String(50)`.

## Task Commits

1. **Task 1: Backend taxonomy — all 4 backend sites in lockstep** - `b148f43` (feat)
2. **Task 2: Frontend taxonomy — union + 3 category-keyed sites** - `04c6b68` (feat)
3. **Task 3: Tests — accept + extract + persist, no regression** - `dfe50c8` (test)

**Plan metadata:** committed separately (docs: complete plan)

_Note: Task 3 was TDD; implementation already existed from Tasks 1-2, so the new tests passed immediately (GREEN) on first run — the lockstep gate was already in place._

## Files Created/Modified
- `backend/app/models/database.py` - Added SET_DRESSING/ANIMAL/SFX/MAKEUP_HAIR/EXTRAS to BreakdownCategory enum (column unchanged String(50))
- `backend/app/models/schemas.py` - Extended BreakdownElementCreate.category regex gate to the 10 values
- `backend/app/services/breakdown_service.py` - Appended 5 on-screen-only CATEGORIES descriptions + precedence note to EXTRACTION_SYSTEM_PROMPT; updated ExtractedElement.category description
- `frontend/src/types/index.ts` - Extended BreakdownCategory union with 5 literals
- `frontend/src/lib/constants.ts` - Added 5 entries to BREAKDOWN_CATEGORIES, CATEGORY_COLORS, ELEMENT_EXTENDED_FIELDS
- `backend/app/tests/test_breakdown_api.py` - TestExpandedCategorySchema (accept/reject)
- `backend/app/tests/test_breakdown_service.py` - TestExpandedCategoryExtraction (extract+persist)

## Verification Results
- Backend suites: `pytest test_breakdown_service.py test_breakdown_api.py test_staleness.py -q` → **68 passed**
- Frontend build: `npm run build` (tsc + vite) → **clean** (no type errors)
- Lockstep grep (all 5 new values across all 5 source files): **LOCKSTEP OK**
- No-new-migration (git diff --diff-filter=A): **NO NEW MIGRATION (expected)**
- Task 1 backend assertion script: **OK** (enum=10, set_dressing validates, nonsense rejected, CRITICAL RULES present, prompt+ExtractedElement list all 10)

## Decisions Made
- **CATEGORY_COLORS:** set_dressing=`rgb(45,212,191)` teal-400, animal=`rgb(251,146,60)` orange-400, sfx=`rgb(251,113,133)` rose-400, makeup_hair=`rgb(232,121,249)` fuchsia-400, extras=`rgb(148,163,184)` slate-400 — all distinct from the existing 5 hues.
- **ELEMENT_EXTENDED_FIELDS:** Reused the generic prop-style 3-field shape (specs/owner/status). Natural owner labels: animal→"Handler / Responsible", makeup_hair→"Artist / Responsible", set_dressing/sfx→"Owner / Responsible". extras uses `{key:'count', label:'Headcount'}` per the plan suggestion.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. All three tasks executed mechanically; verification passed on first run.

## User Setup Required
None - no external service configuration required (no migration, no new dependency).

## Next Phase Readiness
- 10-category taxonomy is live end-to-end (extraction → validation → persistence → UI tabs/filter).
- No blockers. Future expansion follows the same lockstep pattern across the 6 sites; the lockstep grep + tsc exhaustiveness gates remain the drift guards.

## Self-Check: PASSED

All 7 modified source files + the SUMMARY exist on disk; all 3 task commits (b148f43, 04c6b68, dfe50c8) are present in git history.

---
*Phase: 52-expanded-categories*
*Completed: 2026-06-07*
