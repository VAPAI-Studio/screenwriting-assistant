---
phase: 36-show-data-model-crud-api
plan: 01
subsystem: api, database
tags: [fastapi, sqlalchemy, pydantic, crud, shows, tv-mode]

# Dependency graph
requires:
  - phase: 35-real-authentication-user-model
    provides: "User model with FK target for Show.owner_id"
provides:
  - "Show SQLAlchemy model with FK to users"
  - "ShowCreate, ShowUpdate, ShowResponse Pydantic schemas"
  - "Delta migration 006 for shows table"
  - "5 CRUD endpoints at /api/shows (POST, GET list, GET single, PUT, DELETE)"
  - "14 integration tests covering all CRUD operations"
affects: [37-show-bible-columns, 38-bible-ui, 39-episode-model, 40-show-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: ["str() cast on UUID filters for SQLite/PostgreSQL compatibility in router"]

key-files:
  created:
    - backend/app/api/endpoints/shows.py
    - backend/app/tests/test_shows_api.py
    - backend/migrations/delta/006_shows_table.sql
  modified:
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - backend/app/main.py

key-decisions:
  - "Used str() cast on UUID comparisons in router filters for SQLite test compatibility (safe on PostgreSQL)"
  - "Show model has no relationships yet -- Phase 37 adds bible columns, Phase 39 adds episodes relationship"

patterns-established:
  - "Show CRUD router pattern: owner_id scoping on all endpoints via Depends(get_current_user)"
  - "Model test FK safety: create User row before inserting FK-dependent models in tests"

requirements-completed: [SHOW-01, SHOW-04]

# Metrics
duration: 9min
completed: 2026-03-24
---

# Phase 36 Plan 01: Show Data Model & CRUD API Summary

**Show SQLAlchemy model with owner_id FK, 3 Pydantic schemas, delta migration 006, and 5 REST endpoints at /api/shows with 14 passing integration tests**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-24T15:52:43Z
- **Completed:** 2026-03-24T16:02:22Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Show SQLAlchemy model with id, owner_id (FK to users), title, description, created_at, updated_at
- ShowCreate, ShowUpdate, ShowResponse Pydantic schemas with title validation (min 2 chars, no whitespace-only)
- Delta migration 006 creating shows table with owner_id FK constraint and index
- 5 CRUD endpoints: POST (201), GET list (owner-scoped), GET single, PUT, DELETE -- all auth-protected
- 14 integration tests covering create, read, update, delete, validation errors, and not-found cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Show model, schemas, migration, and test scaffolding (TDD RED)** - `dcf120b` (test)
2. **Task 2: Show CRUD router and main.py registration (TDD GREEN)** - `2b88303` (feat)
3. **Task 3: Full test suite regression and cleanup** - `0f61243` (test)

## Files Created/Modified
- `backend/app/models/database.py` - Added Show SQLAlchemy model after User class
- `backend/app/models/schemas.py` - Added ShowCreate, ShowUpdate, ShowResponse schemas
- `backend/migrations/delta/006_shows_table.sql` - Delta migration for shows table with FK and index
- `backend/app/api/endpoints/shows.py` - CRUD router with 5 endpoints, owner_id scoping
- `backend/app/main.py` - Registered shows router at /api/shows prefix
- `backend/app/tests/test_shows_api.py` - 14 tests: 1 model + 13 API integration tests

## Decisions Made
- Used `str()` cast on UUID filter comparisons in the shows router for SQLite test compatibility. This is transparent on PostgreSQL (SQLAlchemy auto-casts strings to UUID for UUID columns).
- Show model placed after User class, before SectionType enum, with comment noting future relationship additions by Phase 37 and 39.
- Model test creates User row before Show insertion to satisfy FK constraints when SQLite FK enforcement is active.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UUID comparison failing in SQLite test environment**
- **Found during:** Task 2 (CRUD router implementation)
- **Issue:** `database.Show.owner_id == current_user.id` failed in SQLite because column stores strings but `current_user.id` is a UUID object
- **Fix:** Used `str()` cast on all UUID filter comparisons in the shows router
- **Files modified:** backend/app/api/endpoints/shows.py
- **Verification:** All 14 tests pass; pattern is safe on PostgreSQL
- **Committed in:** 2b88303 (Task 2 commit)

**2. [Rule 1 - Bug] FK constraint violation in model test during full suite**
- **Found during:** Task 3 (regression testing)
- **Issue:** TestShowModel.test_show_model_columns inserted a Show with owner_id but no matching User row, causing FK constraint failure when SQLite FK enforcement was active from prior test sessions
- **Fix:** Added User row creation before Show insertion in the model test
- **Files modified:** backend/app/tests/test_shows_api.py
- **Verification:** Full suite passes (243 passed, 0 regressions)
- **Committed in:** 0f61243 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
- 3 pre-existing test failures detected in full suite (test_session_isolation, test_shotlist_generation, test_yolo_integration) -- all confirmed pre-existing and unrelated to our changes. The shotlist failures are caused by uncommitted local changes to `shotlist_generation_service.py`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Show model and CRUD API are complete and tested
- Phase 37 can add bible columns (logline, premise, theme, tone, setting, characters_overview) to the Show model
- Phase 39 can add episode relationships (nullable show_id FK on Project model)
- All 5 endpoints documented in OpenAPI at /docs

---
*Phase: 36-show-data-model-crud-api*
*Completed: 2026-03-24*
