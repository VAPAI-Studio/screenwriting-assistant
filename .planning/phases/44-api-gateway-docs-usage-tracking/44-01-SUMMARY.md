---
phase: 44-api-gateway-docs-usage-tracking
plan: 01
subsystem: api
tags: [rate-limiting, openapi, swagger, usage-tracking, middleware, fastapi]

# Dependency graph
requires:
  - phase: 43-api-key-management
    provides: ApiKey model, key creation/revocation endpoints, API key auth flow
provides:
  - Per-key usage tracking via atomic request_count increment
  - Per-key rate limiting middleware (1000 req/hour, 429 + Retry-After)
  - Comprehensive Swagger docs with all 20 router tags and dual-auth security scheme
affects: [44-02-PLAN, frontend-api-key-settings]

# Tech tracking
tech-stack:
  added: []
  patterns: [atomic-sql-update-for-counters, per-key-rate-limiting-via-middleware, mini-app-test-pattern]

key-files:
  created:
    - backend/migrations/delta/010_api_key_usage.sql
    - backend/app/tests/test_api_gateway.py
  modified:
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - backend/app/api/dependencies.py
    - backend/app/middleware.py
    - backend/app/api_docs.py
    - backend/app/main.py

key-decisions:
  - "Atomic SQL UPDATE for request_count avoids race conditions vs ORM-level increment"
  - "Per-key rate limiter uses in-memory timestamp tracking (same pattern as IP rate limiter)"
  - "rate_limit column defaults to NULL meaning use system default (1000 req/hour)"
  - "429 test uses isolated Starlette mini-app with limit=2 to avoid sending 1000 requests"

patterns-established:
  - "Atomic SQL counter pattern: UPDATE table SET col = col + 1 WHERE id = :id (avoids lost updates)"
  - "Mini-app test pattern: create isolated Starlette app with middleware for focused testing"

requirements-completed: [AK-05, AK-06]

# Metrics
duration: 6min
completed: 2026-03-31
---

# Phase 44 Plan 01: API Gateway Docs & Usage Tracking Summary

**Per-key usage tracking with atomic SQL increment, per-key rate limiting middleware (1000 req/hr, 429+Retry-After), and comprehensive Swagger docs with all 20 router tags and dual JWT/API-key security scheme**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-31T07:32:29Z
- **Completed:** 2026-03-31T07:38:22Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- Migration 010 adds request_count and rate_limit columns to api_keys table
- Atomic SQL UPDATE replaces ORM-based last_used_at update, incrementing request_count on every API key request
- ApiKeyRateLimitMiddleware returns 429 with Retry-After header when API key exceeds 1000 req/hour; JWT requests pass through unaffected
- Swagger UI at /docs documents all 20 router tags with descriptions and dual-auth security scheme (JWT + API key)
- 10 integration tests covering docs accessibility, usage tracking, and rate limiting (including mini-app 429 verification)

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration, model, schema, and atomic increment** - `53877a0` (feat)
2. **Task 2: Per-key rate limiter middleware and API docs enhancement** - `880865f` (feat)
3. **Task 3: Integration tests for docs, usage tracking, and rate limiting** - `a7fa529` (test)

## Files Created/Modified
- `backend/migrations/delta/010_api_key_usage.sql` - Adds request_count and rate_limit columns to api_keys
- `backend/app/models/database.py` - ApiKey model updated with request_count and rate_limit columns
- `backend/app/models/schemas.py` - ApiKeyResponse schema exposes request_count field
- `backend/app/api/dependencies.py` - Atomic SQL increment replaces ORM-based last_used_at update
- `backend/app/middleware.py` - New ApiKeyRateLimitMiddleware class for per-key rate limiting
- `backend/app/api_docs.py` - Complete rewrite with all 20 tags, dual-auth security, API key docs
- `backend/app/main.py` - Imports and registers ApiKeyRateLimitMiddleware in middleware stack
- `backend/app/tests/test_api_gateway.py` - 10 tests covering docs, usage tracking, rate limiting

## Decisions Made
- Used atomic SQL UPDATE (`request_count = request_count + 1`) instead of ORM-level increment to prevent race conditions under concurrent requests
- Per-key rate limiter uses same in-memory timestamp tracking pattern as existing IP-based RateLimitMiddleware
- rate_limit column defaults to NULL (use system default of 1000 req/hour) rather than storing 1000 explicitly -- allows future per-key customization
- 429 test uses isolated Starlette mini-app with limit=2 to trigger rate limiting without sending 1000 real requests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _create_api_key helper missing db_session for user creation**
- **Found during:** Task 3 (integration tests)
- **Issue:** API key auth flow looks up user in DB, but mock auth creates keys with a mock user_id that doesn't exist in the test SQLite database -- pre-existing issue in test setup
- **Fix:** Updated _create_api_key helper to accept db_session and call _ensure_user to create the mock user in the test DB before API key creation
- **Files modified:** backend/app/tests/test_api_gateway.py
- **Verification:** All 10 tests pass, existing 15 API key tests also pass
- **Committed in:** a7fa529 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix for test setup)
**Impact on plan:** Essential fix for test correctness. No scope creep.

## Issues Encountered
None beyond the test setup issue documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend API gateway features complete (AK-05, AK-06)
- Ready for Phase 44-02 (frontend API key settings panel with usage display)
- request_count field now available in API key list responses for UI display

## Self-Check: PASSED

All 8 files verified present. All 3 task commits verified (53877a0, 880865f, a7fa529).

---
*Phase: 44-api-gateway-docs-usage-tracking*
*Completed: 2026-03-31*
