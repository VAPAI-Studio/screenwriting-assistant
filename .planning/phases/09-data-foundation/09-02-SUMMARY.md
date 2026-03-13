---
phase: 09-data-foundation
plan: 02
subsystem: database
tags: [sqlalchemy, pydantic, orm, breakdown, postgresql]

# Dependency graph
requires:
  - phase: 09-data-foundation/01
    provides: "Migration 009 with breakdown_elements, element_scene_links, breakdown_runs tables and breakdown_stale column"
provides:
  - "BreakdownElement, ElementSceneLink, BreakdownRun SQLAlchemy ORM models"
  - "BreakdownCategory Python enum"
  - "Project.breakdown_stale column, breakdown_elements and breakdown_runs relationships"
  - "BreakdownElementCreate, BreakdownElementUpdate, BreakdownElementResponse, BreakdownRunResponse, BreakdownSummaryResponse, SceneLinkCreate Pydantic schemas"
  - "19-test suite covering model importability, ORM round-trips, cascade behavior, schema validation"
affects: [10-breakdown-api, 11-extraction-service]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "metadata_ Column alias with validation_alias for ORM-to-schema round-trip"
    - "BreakdownCategory(str, enum.Enum) for Python-level category validation (VARCHAR in DB for extensibility)"
    - "Dual cascade on junction table (parent cascade + FK ondelete=CASCADE)"

key-files:
  created:
    - "backend/app/tests/test_breakdown_models.py"
  modified:
    - "backend/app/models/database.py"
    - "backend/app/models/schemas.py"

key-decisions:
  - "Used Python BreakdownCategory enum for code validation while keeping VARCHAR(50) in DB for extensibility"
  - "Used metadata_ Column alias pattern (matching AIMessage) to avoid SQLAlchemy MetaData clash"
  - "No back_populates on ListItem for scene_links -- navigated via BreakdownElement.scene_links only"

patterns-established:
  - "Breakdown model test pattern: importability + ORM round-trip + cascade + schema validation in single test file"

requirements-completed: [BKDN-01, BKDN-02, BKDN-03, BKDN-04]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 9 Plan 2: Breakdown Models & Schemas Summary

**SQLAlchemy ORM models (BreakdownElement, ElementSceneLink, BreakdownRun) with cascade relationships, Pydantic v2 schemas with metadata alias, and 19-test TDD suite**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T12:26:20Z
- **Completed:** 2026-03-13T12:30:19Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- BreakdownElement, ElementSceneLink, and BreakdownRun ORM models with full relationship wiring and cascade delete-orphan
- Project model updated with breakdown_stale column and two new relationships
- 6 Pydantic v2 schemas with regex category validation, partial updates, metadata_ alias for ORM round-trips
- 19 passing tests (11 model + 8 schema) with zero regressions across the full 90-test suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SQLAlchemy models and update Project relationships**
   - `2d0902b` (test: failing model tests - TDD RED)
   - `6d93d19` (feat: implement ORM models - TDD GREEN)
2. **Task 2: Add Pydantic schemas and ORM round-trip tests**
   - `7f1edbd` (test: failing schema tests - TDD RED)
   - `9a25679` (feat: implement Pydantic schemas - TDD GREEN)
3. **Task 3: Run full test suite to verify no regressions** - verification only, no commit needed

## Files Created/Modified
- `backend/app/models/database.py` - Added BreakdownCategory enum, BreakdownElement, ElementSceneLink, BreakdownRun models; updated Project with breakdown_stale and relationships
- `backend/app/models/schemas.py` - Added BreakdownElementCreate, BreakdownElementUpdate, BreakdownElementResponse, BreakdownRunResponse, BreakdownSummaryResponse, SceneLinkCreate
- `backend/app/tests/test_breakdown_models.py` - 19 tests covering model importability, ORM round-trips, cascade deletes, unique constraints, soft-delete flags, schema validation, and ORM-to-schema conversion

## Decisions Made
- Used Python BreakdownCategory(str, enum.Enum) for code-level validation while keeping VARCHAR(50) in PostgreSQL for extensibility -- matches existing project pattern where some enums are PG-level and some Python-only
- Used metadata_ = Column("metadata", JSON, ...) alias pattern matching AIMessage to avoid SQLAlchemy MetaData clash, with validation_alias="metadata_" in the Pydantic response schema
- No back_populates on ListItem for scene_links -- the junction table is navigated via BreakdownElement.scene_links only, keeping ListItem unchanged

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 3 ORM models importable and relationship-wired to Project
- All 6 Pydantic schemas ready for API endpoint implementation (Phase 10)
- BreakdownElement.scene_links and BreakdownRun.project relationships ready for extraction service (Phase 11)
- Full test suite green (90 tests, 0 failures)

## Self-Check: PASSED

- All 3 source/test files exist on disk
- All 4 task commits verified in git log (2d0902b, 6d93d19, 7f1edbd, 9a25679)
- 09-02-SUMMARY.md exists

---
*Phase: 09-data-foundation*
*Completed: 2026-03-13*
