---
phase: 04-async-safety-and-session-isolation
plan: 01
subsystem: api
tags: [asyncio, sqlalchemy, session-isolation, concurrency, gather]

# Dependency graph
requires:
  - phase: 03-pipeline-map-api-and-crud-wiring
    provides: Agent CRUD wiring and pipeline map infrastructure
provides:
  - Session-per-task pattern for all asyncio.gather sites in agent_service.py
  - SessionFactory type alias and wrapper methods for safe concurrent DB access
  - run_multi_agent_review accepts session_factory callable (required by Phase 5)
affects: [05-agent-review-middleware, 06-wizard-injection, 08-yolo-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [session-per-task via SessionFactory callable, try/finally session cleanup for asyncio safety]

key-files:
  created:
    - backend/app/tests/test_session_isolation.py
  modified:
    - backend/app/services/agent_service.py
    - backend/app/api/endpoints/chat.py

key-decisions:
  - "SessionFactory type alias (Callable[[], Session]) at module level for reuse across all gather sites"
  - "Optional session_factory param with backward-compatible fallback in _orchestrate and _orchestrate_stream_prepare"
  - "try/finally pattern for session cleanup to handle asyncio.CancelledError correctly"

patterns-established:
  - "Session-per-task: each asyncio.gather task creates/closes its own DB session via session_factory callable"
  - "Wrapper method pattern: _review_with_session and _get_specialist_context_with_session wrap existing methods with session lifecycle"

requirements-completed: [REVW-05]

# Metrics
duration: 3min
completed: 2026-03-12
---

# Phase 4 Plan 01: Async Safety and Session Isolation Summary

**Session-per-task pattern via SessionFactory callable at all 3 asyncio.gather sites, eliminating DetachedInstanceError under concurrent agent reviews**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-12T00:54:24Z
- **Completed:** 2026-03-12T00:58:13Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- Refactored all 3 asyncio.gather sites in agent_service.py to use session-per-task pattern
- Added SessionFactory type alias and 2 wrapper methods (_review_with_session, _get_specialist_context_with_session)
- Updated chat.py to pass SessionLocal as session_factory at both call sites
- 5 new tests prove session isolation behavior (factory call count, session close, error handling)
- Full test suite (51 tests) passes with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for session-per-task isolation** - `efca54a` (test) - TDD RED phase
2. **Task 2: Refactor all 3 gather sites + update callers** - `9abd19a` (feat) - TDD GREEN phase

_TDD plan: 2 commits (RED failing tests, GREEN implementation)_

## Files Created/Modified
- `backend/app/tests/test_session_isolation.py` - 5 async tests proving session isolation for all gather sites
- `backend/app/services/agent_service.py` - SessionFactory type, wrapper methods, refactored run_multi_agent_review/orchestrate/orchestrate_stream_prepare
- `backend/app/api/endpoints/chat.py` - Pass SessionLocal as session_factory at send_chat_message and send_chat_message_stream

## Decisions Made
- Used `Callable[[], Session]` type alias rather than importing SessionLocal directly into agent_service.py -- keeps the service testable via mock factories
- Made session_factory Optional in _orchestrate and _orchestrate_stream_prepare for backward compatibility -- when None, falls back to shared db session (existing behavior)
- Used try/finally (not try/except or context manager) for session cleanup to ensure cleanup even on asyncio.CancelledError
- Mock-based tests (not real DB) because SQLite StaticPool cannot truly isolate concurrent sessions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- run_multi_agent_review now accepts session_factory callable, ready for Phase 5 (Agent Review Middleware) to call it safely
- _orchestrate and _orchestrate_stream_prepare also support session_factory, fixing the same bug in the production chat flow
- All existing tests pass unchanged

## Self-Check: PASSED

- [x] backend/app/tests/test_session_isolation.py exists
- [x] backend/app/services/agent_service.py exists
- [x] backend/app/api/endpoints/chat.py exists
- [x] Commit efca54a exists (TDD RED)
- [x] Commit 9abd19a exists (TDD GREEN)

---
*Phase: 04-async-safety-and-session-isolation*
*Completed: 2026-03-12*
