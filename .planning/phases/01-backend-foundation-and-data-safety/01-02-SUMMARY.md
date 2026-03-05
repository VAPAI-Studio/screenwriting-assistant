---
phase: 01-backend-foundation-and-data-safety
plan: 02
subsystem: database
tags: [sqlalchemy, postgresql, rag, soft-delete, book-chunks, migration]

# Dependency graph
requires:
  - phase: 01-01
    provides: Snippet test scaffold (RED test stubs for 7 behaviors)
provides:
  - SQL migration 006 with is_deleted, is_user_created, updated_at columns on book_chunks
  - BookChunk ORM model extended with three new columns
  - All 3 raw SQL book_chunks queries in rag_service.py filter AND bc.is_deleted IS NOT TRUE
  - retry_book() preserves is_user_created=True chunks (filter + synchronize_session=False)
affects:
  - 01-03 (snippets router depends on these columns for CRUD operations)
  - Phase 3 (rag_service changes affect semantic search weight scoring work)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - IS NOT TRUE rather than = FALSE for nullable boolean filtering (handles pre-migration NULL rows)
    - synchronize_session=False on SQLAlchemy ORM bulk .delete() for correctness
    - Partial indexes on book_chunks for query performance (not_deleted, user_created)
    - Idempotent ADD COLUMN IF NOT EXISTS pattern for migrations

key-files:
  created:
    - backend/migrations/006_snippet_management.sql
  modified:
    - backend/app/models/database.py
    - backend/app/services/rag_service.py
    - backend/app/services/book_processing_service.py

key-decisions:
  - "IS NOT TRUE rather than = FALSE for is_deleted filter — handles pre-migration NULL rows defensively (existing rows have NULL until migration runs, DEFAULT FALSE only applies to new inserts)"
  - "synchronize_session=False on retry_book() .delete() — required for SQLAlchemy 2.x ORM bulk delete on large datasets"
  - "Three partial indexes instead of full indexes — is_deleted=FALSE covers the hot path (list endpoint), is_user_created=TRUE covers retry exclusion lookup"

patterns-established:
  - "Soft-delete pattern: is_deleted IS NOT TRUE in all raw SQL WHERE clauses touching book_chunks"
  - "User-content safety: filter BookChunk.is_user_created == False before bulk delete operations"

requirements-completed: [EDIT-02, EDIT-04, CUST-02]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 1 Plan 02: Snippet Management Foundation Summary

**SQL migration 006 + BookChunk ORM columns (is_deleted, is_user_created, updated_at) enabling soft-delete RAG safety and retry_book user-content preservation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T23:36:36Z
- **Completed:** 2026-03-05T23:41:00Z
- **Tasks:** 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Wrote idempotent SQL migration 006 with ADD COLUMN IF NOT EXISTS for is_deleted, is_user_created, updated_at plus two partial indexes on book_chunks
- Extended BookChunk SQLAlchemy ORM model with all three columns (no new imports needed — Boolean and DateTime already imported)
- Patched all 3 raw SQL book_chunks queries in rag_service.py with AND bc.is_deleted IS NOT TRUE (get_supporting_chunks, semantic_search TAG_BASED, semantic_search BOOK_BASED)
- Fixed retry_book() to preserve is_user_created=True chunks by filtering is_user_created == False with synchronize_session=False before bulk delete
- Confirmed 16/16 existing tests pass with no model-related regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write SQL migration 006 and extend BookChunk ORM model** - `d5c804b` (feat)
2. **Task 2: Patch RAG raw SQL queries and fix retry_book() delete** - `72f514f` (fix)
3. **Task 3: Run test suite to confirm model changes do not break existing tests** - `63a876d` (test)

## Files Created/Modified
- `backend/migrations/006_snippet_management.sql` - Idempotent ALTER TABLE with 3 ADD COLUMN IF NOT EXISTS + 2 partial indexes
- `backend/app/models/database.py` - BookChunk extended with is_deleted, is_user_created, updated_at columns after created_at
- `backend/app/services/rag_service.py` - All 3 book_chunks raw SQL queries now include AND bc.is_deleted IS NOT TRUE
- `backend/app/services/book_processing_service.py` - retry_book() bulk delete now filters is_user_created == False with synchronize_session=False

## Decisions Made
- Used IS NOT TRUE rather than = FALSE for is_deleted filter — handles pre-migration NULL rows defensively. Existing rows before migration will have NULL (not FALSE) until the migration backfills; DEFAULT FALSE only applies to new inserts.
- Added synchronize_session=False to retry_book() .delete() — SQLAlchemy 2.x ORM bulk .delete() requires this flag on large datasets to avoid session-cache sync issues.
- Chose three partial indexes (not_deleted for book_id+chunk_index, user_created for book_id) over full indexes for targeted query optimization.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Migration 006 must be applied to the PostgreSQL database when deploying, but this is standard operational procedure.

## Next Phase Readiness
- DB schema is ready: is_deleted, is_user_created, updated_at exist in both migration and ORM model
- RAG is safe: deleted chunks will never surface in agent context (EDIT-04 downstream requirement met)
- retry_book() safety is in place: user-created snippets survive a full reprocess (CUST-02 met)
- Plan 01-03 (snippets router) can now be built on this foundation — all columns needed for snippet CRUD endpoints exist

---
*Phase: 01-backend-foundation-and-data-safety*
*Completed: 2026-03-05*

## Self-Check: PASSED

All files verified present. All commits verified in git history.
- FOUND: backend/migrations/006_snippet_management.sql
- FOUND: backend/app/models/database.py (BookChunk extended)
- FOUND: backend/app/services/rag_service.py (3x is_deleted IS NOT TRUE)
- FOUND: backend/app/services/book_processing_service.py (retry_book fixed)
- FOUND: 01-02-SUMMARY.md
- FOUND commit d5c804b (feat: migration 006 + BookChunk columns)
- FOUND commit 72f514f (fix: RAG queries + retry_book)
- FOUND commit 63a876d (test: suite verification)
