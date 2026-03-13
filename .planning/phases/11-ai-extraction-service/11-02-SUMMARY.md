---
phase: 11-ai-extraction-service
plan: 02
subsystem: ai, api
tags: [extraction, structured-outputs, pydantic, upsert, scene-linking, breakdown]

# Dependency graph
requires:
  - phase: 11-ai-extraction-service
    plan: 01
    provides: BreakdownService skeleton, ExtractionResponse/ExtractedElement Pydantic models, chat_completion_structured(), EXTRACTION_SYSTEM_PROMPT
  - phase: 10-breakdown-api
    provides: BreakdownElement, ElementSceneLink, BreakdownRun database models and CRUD endpoints
provides:
  - Full extract() pipeline in BreakdownService with AI call, element upsert, scene link reconciliation, and run recording
  - Wired POST /extract/{project_id} endpoint calling real BreakdownService
affects: [11-03-integration-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: [upsert-with-sync-protection, scene-index-to-id-mapping, single-transaction-pipeline, ai-link-reconciliation]

key-files:
  created: []
  modified:
    - backend/app/services/breakdown_service.py
    - backend/app/api/endpoints/breakdown.py

key-decisions:
  - "Single db.commit() at end of extract() pipeline -- rollback on any failure, then record failed run in separate transaction"
  - "User-modified elements included in element_map for scene linking even though their description is not overwritten (SYNC-01)"
  - "AI scene links fully replaced on re-extraction (delete-all-ai then recreate) while user links are always preserved"

patterns-established:
  - "Upsert pattern: pre-load all elements in single query, build (category, name.lower()) lookup map, skip/update/create"
  - "Scene link reconciliation: delete AI-sourced links, skip pairs with existing user-sourced links, create new AI links"
  - "Pipeline error handling: rollback main transaction, record failed BreakdownRun in new transaction, re-raise"

requirements-completed: [EXTR-01, EXTR-02, EXTR-04, EXTR-05, SYNC-01, SYNC-02]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 11 Plan 02: Extraction Pipeline Summary

**Full AI extraction pipeline with structured output, element upsert respecting user-modified/soft-delete protection, scene link reconciliation, and wired API endpoint**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T20:46:17Z
- **Completed:** 2026-03-13T20:48:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented complete `extract()` pipeline in BreakdownService: context building, AI structured output call (temperature 0.15), element upsert, scene link reconciliation, and audit run recording
- Added `_upsert_elements()` that pre-loads all project elements in a single query and respects SYNC-01 (user-modified skip) and SYNC-02 (soft-deleted skip) protections
- Added `_reconcile_scene_links()` that replaces AI-sourced links while preserving user-sourced links
- Added `_map_scene_indices_to_ids()` converting 1-based AI scene indices to ListItem UUIDs
- Wired POST `/api/breakdown/extract/{project_id}` to call real `breakdown_service.extract()` instead of stub

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement extract() pipeline with upsert, scene linking, and run recording** - `2f4a4d3` (feat)
2. **Task 2: Wire trigger_extraction endpoint to real BreakdownService** - `882a02e` (feat)

## Files Created/Modified
- `backend/app/services/breakdown_service.py` - Full extraction pipeline with _call_ai_extraction, _upsert_elements, _reconcile_scene_links, _map_scene_indices_to_ids, _record_run, and extract()
- `backend/app/api/endpoints/breakdown.py` - Wired trigger_extraction to real service, removed stub code, added breakdown_service import

## Decisions Made
- Single `db.commit()` at end of extract() pipeline with `db.rollback()` on failure, then recording a failed BreakdownRun in a separate transaction before re-raising the exception
- User-modified elements are included in `element_map` for scene linking even though their description is not overwritten -- this ensures scene links are still updated for manually edited elements
- AI scene links are fully replaced on re-extraction (delete all AI-sourced, then recreate) while user-sourced links are never touched

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Extraction pipeline fully functional -- `POST /extract/{project_id}` performs real AI extraction
- Ready for Plan 11-03 integration tests to verify end-to-end extraction behavior
- Note: Existing Phase 10 stub tests for extraction endpoint will fail because the stub was replaced with real service calls (expected; addressed by 11-03)

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 11-ai-extraction-service*
*Completed: 2026-03-13*
