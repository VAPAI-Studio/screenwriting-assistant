---
phase: 43-api-key-management
plan: 01
subsystem: auth
tags: [api-keys, sha256, dual-auth, fastapi, sqlalchemy, pydantic]

# Dependency graph
requires:
  - phase: 35-real-authentication-user-model
    provides: User model with JWT auth and mock auth for development
provides:
  - ApiKey SQLAlchemy model with SHA-256 hash storage
  - Pydantic schemas for API key create/list/revoke flows
  - POST/GET/DELETE /api/auth/api-keys CRUD endpoints
  - Dual-auth middleware (JWT + API key) in get_current_user
  - Migration 009 for api_keys table
  - 15 tests covering model, CRUD, and auth flows
affects: [44-api-key-frontend, any-future-api-consumers]

# Tech tracking
tech-stack:
  added: [hashlib-sha256, secrets-token-urlsafe]
  patterns: [sa_prefix_secret-key-format, dual-auth-bearer-dispatch]

key-files:
  created:
    - backend/migrations/delta/009_api_keys.sql
    - backend/app/tests/test_api_keys.py
  modified:
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - backend/app/api/endpoints/auth.py
    - backend/app/api/dependencies.py

key-decisions:
  - "API key format uses sa_<prefix>_<secret> with SHA-256 hash storage for lookup"
  - "Dual-auth dispatches on sa_ prefix before falling through to JWT verification"
  - "Soft-revoke via is_active=False; list endpoint filters to active-only"
  - "last_used_at updated on every successful API key authentication"

patterns-established:
  - "sa_ prefix dispatch: Bearer tokens starting with sa_ route to API key auth, all others to JWT"
  - "Secret-once pattern: full API key returned only at creation, never retrievable after"

requirements-completed: [AK-01, AK-02, AK-03, AK-04]

# Metrics
duration: 6min
completed: 2026-03-25
---

# Phase 43 Plan 01: API Key Management Summary

**API key CRUD with sa_<prefix>_<secret> format, SHA-256 hash-based dual auth, and 15 passing tests**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-25T19:28:51Z
- **Completed:** 2026-03-25T19:35:08Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ApiKey model with all required columns (id, user_id, name, key_prefix, key_hash, scopes, expires_at, created_at, last_used_at, is_active)
- Three Pydantic schemas: ApiKeyCreate (input), ApiKeyCreateResponse (secret shown once), ApiKeyResponse (no secret)
- POST/GET/DELETE endpoints on /api/auth/api-keys for create, list, and revoke
- Dual-auth middleware: sa_ prefix triggers hash lookup; JWT/mock-token auth unaffected
- 15 tests covering model persistence, cascade delete, CRUD operations, auth flow, expiry, revocation, and last_used_at tracking

## Task Commits

Each task was committed atomically:

1. **Task 1: ApiKey model, migration, schemas, and test scaffolding** - `7e021f7` (feat)
2. **Task 2: API key CRUD endpoints, dual-auth dependency, and passing tests** - `1a2e227` (feat)

**Plan metadata:** [pending] (docs: complete plan)

## Files Created/Modified
- `backend/app/models/database.py` - Added ApiKey SQLAlchemy model after User model
- `backend/app/models/schemas.py` - Added ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse schemas
- `backend/migrations/delta/009_api_keys.sql` - PostgreSQL migration for api_keys table with indexes
- `backend/app/tests/test_api_keys.py` - 15 tests across TestApiKeyModel, TestApiKeysAPI, TestApiKeyAuth
- `backend/app/api/dependencies.py` - Added hashlib import and sa_ prefix dual-auth branch in get_current_user
- `backend/app/api/endpoints/auth.py` - Added generate_api_key helper and three CRUD endpoints

## Decisions Made
- API key format: `sa_<prefix>_<secret>` using secrets.token_urlsafe for cryptographic randomness
- SHA-256 hash storage: full key never stored, only the hash for lookup
- Dual-auth dispatch in get_current_user: checks `credentials.credentials.startswith("sa_")` before JWT flow
- Soft-revoke: DELETE sets is_active=False; list endpoint filters active-only
- Timezone-aware expiry comparison: strips tzinfo for utcnow() comparison to handle SQLite test compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cascade delete test for SQLite compatibility**
- **Found during:** Task 2 (test execution)
- **Issue:** SQLite doesn't enforce foreign key CASCADE by default; test_api_key_cascade_delete failed
- **Fix:** Added PRAGMA foreign_keys = ON temporarily in test, used raw SQL DELETE, and restored PRAGMA foreign_keys = OFF in finally block to avoid affecting other tests
- **Files modified:** backend/app/tests/test_api_keys.py
- **Verification:** Cascade test passes; full suite shows no regressions from PRAGMA change
- **Committed in:** 1a2e227 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed timezone-aware expiry comparison**
- **Found during:** Task 2 (dual-auth implementation)
- **Issue:** SQLite stores datetime without timezone info; comparing timezone-aware expires_at with datetime.utcnow() would fail
- **Fix:** Used `.replace(tzinfo=None)` on expires_at before comparing with utcnow()
- **Files modified:** backend/app/api/dependencies.py
- **Verification:** test_expired_key_rejected passes with timezone-aware expiry
- **Committed in:** 1a2e227 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for test/SQLite compatibility. No scope creep.

## Issues Encountered
- Pre-existing test failures in test_session_isolation.py (mock config issue) and test_yolo_integration.py (test ordering) are unrelated to this plan -- logged but not addressed per scope boundary rules.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- API key backend is complete; ready for Phase 43-02 (frontend API key management UI)
- All four requirements (AK-01 through AK-04) satisfied by backend implementation
- Endpoints available at /api/auth/api-keys for frontend integration

## Self-Check: PASSED

All 7 files verified present. Both task commits (7e021f7, 1a2e227) verified in git log.

---
*Phase: 43-api-key-management*
*Completed: 2026-03-25*
