---
phase: 10-breakdown-api
plan: 02
subsystem: api
tags: [fastapi, breakdown, scene-links, summary, extraction, integration-tests, sqlalchemy]

# Dependency graph
requires:
  - phase: 10-breakdown-api
    plan: 01
    provides: Breakdown element CRUD endpoints, router mounted at /api/breakdown, ownership verification helpers
  - phase: 09-data-foundation
    provides: BreakdownElement, ElementSceneLink, BreakdownRun ORM models, Pydantic schemas
provides:
  - Extraction trigger stub (POST /extract/{project_id}) creating pending BreakdownRun
  - Scene link add/remove endpoints (POST/DELETE /element/{id}/scenes)
  - Summary endpoint (GET /summary/{project_id}) with GROUP BY aggregation
  - Comprehensive integration test suite (22 tests) covering all 7 API requirements
affects: [11-ai-extraction, 13-frontend-breakdown]

# Tech tracking
tech-stack:
  added: []
  patterns: [JSONResponse for status code override in idempotent endpoints, str() cast for UUID query params in SQLAlchemy filters]

key-files:
  created: [backend/app/tests/test_breakdown_api.py]
  modified: [backend/app/api/endpoints/breakdown.py]

key-decisions:
  - "Extraction stub returns 200 (synchronous) not 202 (async) per research recommendation"
  - "Scene link POST uses JSONResponse to return 200 for idempotent duplicates, overriding default 201"
  - "UUID params cast to str() in all SQLAlchemy filter queries for PostgreSQL/SQLite compatibility"
  - "Scene link DELETE is hard-delete (not soft-delete) since ElementSceneLink is a junction table"
  - "Summary aggregation uses single GROUP BY query, not N+1 per-category queries"

patterns-established:
  - "Idempotent POST: use JSONResponse(status_code=200) to override decorator status_code=201 for duplicate detection"
  - "UUID filter safety: str(uuid_param) in .filter() for cross-DB compatibility"
  - "Test project creation: use API client (not direct DB insert) to ensure owner_id stored correctly for auth verification"

requirements-completed: [API-01, API-06, API-07]

# Metrics
duration: 10min
completed: 2026-03-13
---

# Phase 10 Plan 02: Breakdown API Scene Links, Summary, and Tests Summary

**Scene link add/remove endpoints, extraction stub, summary with GROUP BY aggregation, and 22 integration tests covering all 7 API requirements**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-13T14:47:12Z
- **Completed:** 2026-03-13T14:58:09Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added 4 new endpoints completing the full breakdown API surface (8 routes total)
- POST /extract/{project_id} creates BreakdownRun with status='pending' as synchronous stub for Phase 11
- POST /element/{id}/scenes creates scene links with idempotent duplicate handling (returns 200 for existing)
- DELETE /element/{id}/scenes/{scene_id} hard-deletes junction table rows
- GET /summary/{project_id} returns category counts via efficient GROUP BY aggregation, staleness flag, and last run info
- 22 integration tests covering all 7 API requirements (API-01 through API-07) including happy paths, edge cases, and error cases
- Full backend test suite (112 tests) passes with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add scene link, summary, and extraction endpoints** - `0c2f4de` (feat)
2. **Task 2: Create comprehensive test suite with bug fixes** - `e8d97fe` (test)

## Files Created/Modified
- `backend/app/api/endpoints/breakdown.py` - Added extraction stub, scene link add/remove, summary endpoint; fixed UUID comparison and idempotent status code
- `backend/app/tests/test_breakdown_api.py` - New file: 22 integration tests organized by API requirement (API-01 through API-07, cross-cutting)

## Decisions Made
- Extraction stub returns 200 (not 202) since it's synchronous per research recommendation; Phase 11 will implement actual async extraction
- Scene link duplicate detection uses JSONResponse to explicitly return 200 status code, overriding the endpoint's default 201
- All UUID parameters in SQLAlchemy filter() calls cast to str() for PostgreSQL/SQLite compatibility
- Test helpers create projects via API (not direct DB insert) to ensure owner_id is stored correctly for auth verification on SQLite

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UUID comparison fails in SQLite test DB**
- **Found during:** Task 2 (integration test development)
- **Issue:** SQLAlchemy filter queries comparing UUID objects against String(36) columns returned no results on SQLite (used by test conftest). PostgreSQL handles this natively via type casting, but SQLite does not.
- **Fix:** Cast all UUID parameters to str() in filter() calls across all breakdown endpoints. This is safe on PostgreSQL (accepts string UUID representations) and fixes SQLite compatibility.
- **Files modified:** backend/app/api/endpoints/breakdown.py
- **Verification:** All 22 breakdown tests pass; full 112-test suite green
- **Committed in:** e8d97fe (Task 2 commit)

**2. [Rule 1 - Bug] Idempotent scene link returns 201 instead of 200**
- **Found during:** Task 2 (test_add_scene_link_idempotent)
- **Issue:** When a duplicate scene link was detected, the endpoint returned the correct body but with status 201 (from the @router.post decorator's status_code parameter) instead of 200.
- **Fix:** Used JSONResponse(status_code=200, content={...}) to explicitly override the response status code for the idempotent path.
- **Files modified:** backend/app/api/endpoints/breakdown.py
- **Verification:** test_add_scene_link_idempotent passes, first POST returns 201, duplicate POST returns 200
- **Committed in:** e8d97fe (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed bugs above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 7 API requirements (API-01 through API-07) have working, tested endpoints
- API surface ready for Phase 11 (AI extraction service) to implement the extraction logic behind POST /extract
- API surface ready for Phase 13 (frontend breakdown page) to consume all endpoints
- Summary endpoint provides efficient aggregation for dashboard display

## Self-Check: PASSED

- FOUND: backend/app/api/endpoints/breakdown.py
- FOUND: backend/app/tests/test_breakdown_api.py
- FOUND: 10-02-SUMMARY.md
- FOUND: commit 0c2f4de
- FOUND: commit e8d97fe

---
*Phase: 10-breakdown-api*
*Completed: 2026-03-13*
