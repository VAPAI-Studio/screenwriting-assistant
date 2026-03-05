---
phase: 01-backend-foundation-and-data-safety
plan: 01
subsystem: testing
tags: [pytest, sqlite, safevector, embedding, tdd, snippets]

# Dependency graph
requires: []
provides:
  - "Test scaffold for all 7 snippet behaviors (BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03) in RED state"
  - "SafeVector SQLite patch in conftest.py — prevents vector(1536) crash in test engine"
  - "mock_embed fixture returning [0.1]*1536 — no live OpenAI calls in tests"
affects:
  - 01-02-PLAN (BookChunk schema changes — tests reference is_user_created and is_deleted)
  - 01-03-PLAN (snippets router — these stubs go GREEN when router is implemented)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SafeVector SQLite patch: extend _patch_uuid_columns_for_sqlite() with elif isinstance(column.type, SafeVector): column.type = Text()"
    - "Embed mock: patch app.services.embedding_service.embedding_service.embed_text with AsyncMock returning [0.1]*1536"
    - "TDD RED stubs: pytest.fail('not implemented — waiting for Plan 0N') as the test body"

key-files:
  created:
    - backend/app/tests/test_snippets_api.py
  modified:
    - backend/app/tests/conftest.py

key-decisions:
  - "Patch SafeVector to Text() in conftest (not in database.py) — keeps production model clean, only affects test engine"
  - "Use pytest.fail() not pytest.skip() for stubs — stubs must be RED to satisfy Nyquist verification requirement"
  - "mock_embed patches at the definition site (embedding_service module) not import site — ensures all importers are affected"

patterns-established:
  - "SafeVector patch pattern: add elif block in _patch_uuid_columns_for_sqlite() for any new vector column types"
  - "Embed mock pattern: use mock_embed fixture (not autouse) so only tests that need it pay the patch cost"

requirements-completed: [BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03]

# Metrics
duration: 4min
completed: 2026-03-05
---

# Phase 1 Plan 01: Snippet Test Scaffold Summary

**pytest test scaffold with 7 RED stubs for snippet API behaviors, SafeVector SQLite patch, and mock_embed fixture — zero live OpenAI calls in test suite**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-05T23:32:27Z
- **Completed:** 2026-03-05T23:36:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Extended `_patch_uuid_columns_for_sqlite()` to patch `SafeVector(1536)` columns to `Text()` — SQLite test engine no longer crashes on vector columns
- Added `mock_embed` fixture that stubs `embedding_service.embed_text` with `AsyncMock` returning `[0.1] * 1536` — no live OpenAI calls during tests
- Created `test_snippets_api.py` with 7 failing stubs (6 in `TestSnippetsAPI`, 1 in `TestRetryBook`) confirming all requirement IDs are tracked before implementation

## Task Commits

Each task was committed atomically:

1. **Task 1: Patch conftest.py for SafeVector SQLite compatibility and embed mock** - `d4d45f0` (chore)
2. **Task 2: Write failing test stubs for all 7 snippet behaviors** - `f083d78` (test)

## Files Created/Modified

- `backend/app/tests/conftest.py` — Added SafeVector patch in `_patch_uuid_columns_for_sqlite()`, added `Text` and `AsyncMock/patch` imports, added `mock_embed` fixture
- `backend/app/tests/test_snippets_api.py` — New file: `TestSnippetsAPI` (6 stubs) + `TestRetryBook` (1 stub), all FAIL with "not implemented" message

## Decisions Made

- Patching SafeVector in conftest (not database.py) keeps production model clean; patch only applies to SQLite test engine
- Using `pytest.fail()` rather than `pytest.skip()` — skipped tests don't count as RED, they just disappear from results
- Patch target `app.services.embedding_service.embedding_service.embed_text` patches at definition site so all importers see the mock

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 01-02 can proceed: it needs to add `is_user_created`, `is_deleted`, `updated_at` columns to `BookChunk` (referenced in `_make_chunk` helper)
- Plan 01-03 can proceed after 01-02: implementing the snippets router will turn these 7 stubs GREEN
- Existing test suite (test_api.py 10 passed, test_validators.py 6 passed) remains unbroken

---
*Phase: 01-backend-foundation-and-data-safety*
*Completed: 2026-03-05*
