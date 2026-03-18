---
phase: 10-breakdown-api
plan: 01
subsystem: api
tags: [fastapi, crud, breakdown, soft-delete, sqlalchemy]

# Dependency graph
requires:
  - phase: 09-data-foundation
    provides: BreakdownElement ORM model, Pydantic schemas, database migration
provides:
  - Breakdown element CRUD endpoints (list, create, update, soft-delete)
  - Router mounted at /api/breakdown
  - Ownership verification helpers for breakdown elements
affects: [10-02 (scene links, summary, extraction endpoints), 11-ai-extraction, 13-frontend-breakdown]

# Tech tracking
tech-stack:
  added: []
  patterns: [ownership verification via helper functions, soft-delete pattern, duplicate check-and-restore]

key-files:
  created: [backend/app/api/endpoints/breakdown.py]
  modified: [backend/app/main.py]

key-decisions:
  - "POST create checks for soft-deleted duplicates and restores them rather than erroring"
  - "PUT update always sets user_modified=True regardless of which fields change"
  - "Ownership verification follows two-helper pattern from list_items.py"

patterns-established:
  - "Breakdown ownership: _verify_project_ownership checks project.owner_id, _verify_element_ownership chains to it"
  - "Soft-delete: DELETE sets is_deleted=True, never uses db.delete()"
  - "metadata_ alias: Pydantic 'metadata' maps to ORM 'metadata_' attribute in create/update"

requirements-completed: [API-02, API-03, API-04, API-05]

# Metrics
duration: 1min
completed: 2026-03-13
---

# Phase 10 Plan 01: Breakdown API CRUD Summary

**FastAPI breakdown element CRUD at /api/breakdown with soft-delete, duplicate restore, and ownership verification**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-13T14:43:04Z
- **Completed:** 2026-03-13T14:44:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created breakdown.py router with 4 CRUD endpoints and 2 ownership helper functions
- GET endpoint supports category filtering and include_deleted toggle, ordered by sort_order then created_at
- POST endpoint handles duplicate detection: restores soft-deleted elements, returns 409 for active duplicates
- PUT endpoint applies partial updates via model_dump(exclude_unset=True) and always marks user_modified=True
- DELETE endpoint soft-deletes only (sets is_deleted=True, never hard-deletes)
- Mounted router in main.py at /api/breakdown prefix

## Task Commits

Each task was committed atomically:

1. **Task 1: Create breakdown.py router with element CRUD endpoints** - `3b27218` (feat)
2. **Task 2: Mount breakdown router in main.py** - `e32416a` (feat)

## Files Created/Modified
- `backend/app/api/endpoints/breakdown.py` - New file: breakdown element CRUD router with 4 endpoints and ownership helpers
- `backend/app/main.py` - Added breakdown router import and include_router mount

## Decisions Made
- POST create checks for soft-deleted duplicates and restores them (setting source='user', user_modified=True) rather than creating a new row that would violate the UNIQUE constraint
- PUT update always sets user_modified=True regardless of which fields are changed, marking human involvement
- Followed the list_items.py two-helper ownership verification pattern (_verify_project_ownership + _verify_element_ownership)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CRUD endpoints ready for frontend consumption (Phase 13)
- Plan 10-02 can now add scene link, summary, and extraction endpoints on top of this router
- AI extraction service (Phase 11) has endpoints to write elements via POST

## Self-Check: PASSED

- FOUND: backend/app/api/endpoints/breakdown.py
- FOUND: 10-01-SUMMARY.md
- FOUND: commit 3b27218
- FOUND: commit e32416a

---
*Phase: 10-breakdown-api*
*Completed: 2026-03-13*
