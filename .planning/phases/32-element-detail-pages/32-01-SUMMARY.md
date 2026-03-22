---
phase: 32-element-detail-pages
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, breakdown, endpoint]

# Dependency graph
requires:
  - phase: 09-breakdown-data
    provides: BreakdownElement, ElementSceneLink models and CRUD endpoints
provides:
  - GET /api/breakdown/element/{element_id} single-element endpoint
  - SceneLinkResponse enriched with scene_title from ListItem.content
  - TestGetElement and TestUpdateElementMetadata test classes
affects: [32-02-element-detail-pages, frontend-element-detail]

# Tech tracking
tech-stack:
  added: []
  patterns: [scene-title-enrichment-via-ListItem-join, single-element-GET-with-ownership]

key-files:
  created: []
  modified:
    - backend/app/api/endpoints/breakdown.py
    - backend/app/models/schemas.py
    - backend/app/tests/test_breakdown_api.py

key-decisions:
  - "Enrichment done at Pydantic level (not SQL join) for SQLite/PostgreSQL compat"
  - "scene_title is Optional[str] to handle orphaned scene links gracefully"

patterns-established:
  - "Single-element GET pattern: ownership check then selectinload then response enrichment"

requirements-completed: [EDP-01]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 32 Plan 01: Element Detail API Summary

**GET /api/breakdown/element/{element_id} endpoint with SceneLinkResponse scene_title enrichment and metadata persistence tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T16:51:06Z
- **Completed:** 2026-03-22T16:53:36Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- GET /api/breakdown/element/{element_id} returns single element with all fields, metadata, and scene_links
- SceneLinkResponse enriched with scene_title field populated from ListItem.content["title"]
- 6 new tests covering GET single element (4 tests) and metadata persistence (2 tests)
- All 37 breakdown tests pass, no regressions in broader suite

## Task Commits

Each task was committed atomically:

1. **Task 1: Add GET single-element endpoint with enriched scene titles**
   - `f0f11ab` (test: add failing tests - TDD RED)
   - `103e98d` (feat: implement GET endpoint and scene_title enrichment - TDD GREEN)

## Files Created/Modified
- `backend/app/api/endpoints/breakdown.py` - Added GET /element/{element_id} endpoint with ownership verification, selectinload, and scene title enrichment
- `backend/app/models/schemas.py` - Added scene_title: Optional[str] field to SceneLinkResponse
- `backend/app/tests/test_breakdown_api.py` - Added TestGetElement (4 tests) and TestUpdateElementMetadata (2 tests)

## Decisions Made
- Enrichment done at Pydantic response level (build title_map from ListItem query, inject into response) rather than SQL join, maintaining SQLite/PostgreSQL compatibility consistent with existing patterns
- scene_title is Optional[str] = None so orphaned scene links (ListItem deleted) degrade gracefully to null

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GET single-element endpoint ready for frontend element detail page (Plan 02)
- SceneLinkResponse.scene_title available for frontend to display scene titles in element detail view
- 1 pre-existing test failure in test_session_isolation.py (unrelated to this plan)

## Self-Check: PASSED

All files found: breakdown.py, schemas.py, test_breakdown_api.py, 32-01-SUMMARY.md
All commits found: f0f11ab, 103e98d

---
*Phase: 32-element-detail-pages*
*Completed: 2026-03-22*
