---
phase: 02-frontend-snippets-page
plan: 02
subsystem: database
tags: [sqlalchemy, postgresql, pgvector, knowledge-extraction, embeddings, openai]

# Dependency graph
requires:
  - phase: 02-frontend-snippets-page
    plan: 01
    provides: "RED test stubs for snippet extraction (test_snippet_extraction.py)"

provides:
  - "Migration 007: snippets table DDL with HNSW embedding index"
  - "Snippet ORM model registered in Base.metadata (conftest VectorAsText patch applies automatically)"
  - "Book.snippets cascade relationship (all, delete-orphan)"
  - "extract_snippets() Stage 4 in KnowledgeExtractionService"
  - "process_chapter() returns snippets key with extracted passages"
  - "BookProcessingService persists Snippet records with embed_batch() after chapter loop"
  - "retry_book() deletes Snippet records before reprocessing"

affects:
  - 02-03-snippets-api
  - 02-04-snippets-frontend

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Snippet model mirrors BookChunk pattern: SafeVector(1536) + deferred(), is_deleted soft-delete, JSON concept_ids"
    - "embed_batch() called once after full chapter loop (not per-snippet) for efficiency"
    - "chapter_title injected into snippet dicts by caller after extract_snippets() returns"
    - "concept_name_to_db map reused for snippet concept linkage without extra DB query"

key-files:
  created:
    - backend/migrations/007_snippets_table.sql
  modified:
    - backend/app/models/database.py
    - backend/app/services/knowledge_extraction_service.py
    - backend/app/services/book_processing_service.py
    - backend/app/tests/test_snippet_extraction.py

key-decisions:
  - "Snippet.concept_ids stores str(UUID) for SQLite compatibility (consistent with existing decisions)"
  - "All AI-generated snippets deleted in retry_book() — no user-created snippets exist in this model"
  - "synchronize_session=False on Snippet bulk delete in retry_book() — consistent with BookChunk pattern"

patterns-established:
  - "Stage 4 extraction: extract_snippets() returns [] early when concepts list is empty"
  - "Snippet persistence: embed_batch called once for all snippets collected across all chapters"

requirements-completed: [EXTR-01, EXTR-02]

# Metrics
duration: 2min
completed: 2026-03-06
---

# Phase 2 Plan 02: Snippet Backend Foundation Summary

**Snippet ORM model + migration 007, AI-curated passage extraction (Stage 4), and BookProcessingService batch persistence with embeddings and concept linkage**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-06T03:19:30Z
- **Completed:** 2026-03-06T03:22:04Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created migration 007 with snippets table, partial soft-delete index, and HNSW embedding index
- Added Snippet ORM model to database.py mirroring BookChunk pattern, registered in Base.metadata so conftest VectorAsText patching applies automatically
- Added extract_snippets() Stage 4 to KnowledgeExtractionService with early-return on empty concepts, JSON-mode AI call, and error recovery
- Updated process_chapter() to call Stage 4 and return {"concepts", "relationships", "snippets"}
- Added Snippet import + batch persistence to BookProcessingService with single embed_batch() call after chapter loop
- Added Snippet deletion to retry_book() with synchronize_session=False
- Turned 2 RED stubs GREEN: test_extract_snippets_creates_records and test_snippets_have_embeddings_and_concept_ids

## Task Commits

Each task was committed atomically:

1. **Task 1: DB migration + Snippet ORM model** - `0baa414` (feat)
2. **Task 2: extract_snippets() Stage 4 + BookProcessingService persistence + tests GREEN** - `a7a3708` (feat)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `backend/migrations/007_snippets_table.sql` - Snippets table DDL: UUID PK, book_id FK cascade, content, justification, concept_ids/names JSONB, embedding vector(1536), is_deleted, partial + HNSW indexes
- `backend/app/models/database.py` - Added Snippet class after BookChunk, added Book.snippets relationship
- `backend/app/services/knowledge_extraction_service.py` - Added extract_snippets() method + Stage 4 call in process_chapter()
- `backend/app/services/book_processing_service.py` - Added Snippet import, all_raw_snippets collection in loop, batch embed+persist block, Snippet deletion in retry_book()
- `backend/app/tests/test_snippet_extraction.py` - Replaced 2 pytest.fail() stubs with real test implementations (both PASS)

## Decisions Made

- `Snippet.book_id` uses `str(book.id)` for SQLite compatibility — consistent with prior decisions documented in STATE.md
- All snippets deleted in `retry_book()` because all snippets are AI-generated (no user-created snippets in this model)
- `synchronize_session=False` on `db.query(Snippet).delete()` — consistent with existing BookChunk pattern in retry_book()

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Snippet model is in place and fully tested — Plan 03 (Snippets API) can build the REST endpoints
- `concept_name_to_db` reuse pattern established — Plan 03 can query Snippet records by book_id
- 4 RED stubs remain in test_snippet_manager.py (Wave 0 from Plan 01) — Plan 03 will turn them GREEN

---
*Phase: 02-frontend-snippets-page*
*Completed: 2026-03-06*

## Self-Check: PASSED

- FOUND: backend/migrations/007_snippets_table.sql
- FOUND: .planning/phases/02-frontend-snippets-page/02-02-SUMMARY.md
- FOUND commit: 0baa414 (Task 1)
- FOUND commit: a7a3708 (Task 2)
- snippets in Base.metadata: True
- Book.snippets relationship: True
- extract_snippets() method exists: True
