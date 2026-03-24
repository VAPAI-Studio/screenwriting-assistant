---
phase: 37-series-bible-data-api
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, bible, show-model, crud]

# Dependency graph
requires:
  - phase: 36-show-data-model-crud
    provides: Show model with CRUD endpoints and tests
provides:
  - Bible columns on Show model (bible_characters, bible_world_setting, bible_season_arc, bible_tone_style, episode_duration_minutes)
  - BibleUpdate and BibleResponse Pydantic schemas
  - GET /api/shows/{id}/bible endpoint
  - PUT /api/shows/{id}/bible endpoint with partial update support
  - Idempotent migration 007_bible_columns.sql
  - 14 new tests (2 model + 12 API)
affects: [38-show-management-ui, 39-episode-linking, 41-bible-ai-injection]

# Tech tracking
tech-stack:
  added: []
  patterns: [dedicated sub-resource endpoint pattern for bible data separate from show CRUD]

key-files:
  created:
    - backend/migrations/delta/007_bible_columns.sql
  modified:
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - backend/app/api/endpoints/shows.py
    - backend/app/tests/test_shows_api.py

key-decisions:
  - "Bible data accessed via dedicated /bible sub-resource endpoints, not mixed into ShowResponse"
  - "Episode duration accepts any integer 1-480, not restricted to presets"
  - "Duration nullable to support shows without a set duration"

patterns-established:
  - "Sub-resource endpoint pattern: GET/PUT /{parent_id}/sub-resource for related data"

requirements-completed: [BIBL-01, BIBL-02, BIBL-03]

# Metrics
duration: 5min
completed: 2026-03-24
---

# Phase 37 Plan 01: Series Bible Data & API Summary

**Four bible text fields and episode duration on Show model with GET/PUT /api/shows/{id}/bible endpoints, partial update support, and 14 comprehensive tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T18:44:04Z
- **Completed:** 2026-03-24T18:49:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Extended Show model with 5 new columns: bible_characters, bible_world_setting, bible_season_arc, bible_tone_style (Text, default=""), and episode_duration_minutes (Integer, nullable)
- Added BibleUpdate (partial, max_length=50000, duration ge=1 le=480) and BibleResponse schemas
- Built GET and PUT /api/shows/{id}/bible endpoints following existing show CRUD patterns
- Created idempotent migration 007_bible_columns.sql with ADD COLUMN IF NOT EXISTS
- Added 14 tests: 2 model tests (defaults, value assignment) + 12 API tests (defaults, partial/full update, round-trip, preset/custom duration, invalid values, 404s, null clear)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add bible columns to Show model, migration, and Pydantic schemas** - `ea44d30` (feat)
2. **Task 2: Add bible API endpoints and comprehensive tests** - `e1df4c4` (feat)

**Plan metadata:** `3b8a559` (docs: complete plan)

_Note: TDD tasks each had RED-GREEN cycle verified_

## Files Created/Modified
- `backend/app/models/database.py` - Added 5 bible/duration columns to Show model
- `backend/app/models/schemas.py` - Added BibleUpdate and BibleResponse Pydantic schemas
- `backend/migrations/delta/007_bible_columns.sql` - Idempotent ALTER TABLE migration for 5 new columns
- `backend/app/api/endpoints/shows.py` - Added GET and PUT /{show_id}/bible endpoints
- `backend/app/tests/test_shows_api.py` - Added TestBibleModel (2 tests) and TestBibleAPI (12 tests)

## Decisions Made
- Bible data accessed via dedicated /bible sub-resource endpoints, not mixed into ShowResponse -- keeps existing CRUD clean and allows bible-specific validation
- Episode duration accepts any positive integer 1-480 (not restricted to presets like 22, 44, 60) -- more flexible for varied show formats
- Duration is nullable, allowing shows without a defined episode length
- All four text fields default to empty string (not null) for simpler frontend handling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Bible data model and API complete, ready for Phase 38 (Show Management UI) to render and edit bible content
- Phase 39 (Episode Linking) can add show_id FK to Project model
- Phase 41 (Bible AI Injection) can read bible context via GET /api/shows/{id}/bible

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 37-series-bible-data-api*
*Completed: 2026-03-24*
