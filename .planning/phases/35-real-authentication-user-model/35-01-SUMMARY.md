---
phase: 35-real-authentication-user-model
plan: 01
subsystem: auth
tags: [jwt, bcrypt, passlib, jose, fastapi, sqlalchemy, pydantic]

# Dependency graph
requires:
  - phase: 17-data-foundation
    provides: "SQLAlchemy Base, migration pattern, conftest.py test fixtures"
provides:
  - "User SQLAlchemy model (users table)"
  - "POST /api/auth/register endpoint (email+password -> JWT)"
  - "POST /api/auth/login endpoint (email+password -> JWT)"
  - "GET/PATCH /api/auth/me profile endpoints"
  - "RegisterRequest, LoginRequest, UserUpdate Pydantic schemas"
  - "get_current_user dependency queries real User from DB via JWT sub claim"
  - "Migration 005_users_table.sql with seed dev user"
affects: [35-02, frontend-auth, user-settings]

# Tech tracking
tech-stack:
  added: []
  patterns: [real-user-db-lookup-in-get_current_user, bcrypt-password-hashing, jwt-sub-claim-user-id]

key-files:
  created:
    - backend/app/tests/test_auth.py
    - backend/migrations/delta/005_users_table.sql
  modified:
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - backend/app/api/endpoints/auth.py
    - backend/app/api/dependencies.py
    - backend/app/services/auth_service.py

key-decisions:
  - "Used /api/projects/ for JWT acceptance test (plan referenced non-existent /api/v2/projects)"
  - "Kept legacy magic-link endpoints for backward compatibility"
  - "Mock-token auth preserved in development mode alongside real JWT auth"

patterns-established:
  - "Real user DB query: get_current_user decodes JWT sub claim -> queries database.User -> returns schemas.User"
  - "Register/login pattern: hash with bcrypt via passlib, issue JWT with user.id as sub claim"

requirements-completed: [UM-01, UM-02, UM-03]

# Metrics
duration: 3min
completed: 2026-03-23
---

# Phase 35 Plan 01: Backend Auth Foundation Summary

**Real register/login endpoints with bcrypt password hashing, JWT token issuance, and get_current_user DB query replacing mock user lookup**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-23T14:33:44Z
- **Completed:** 2026-03-23T14:37:28Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- User SQLAlchemy model with id, email, hashed_password, display_name, is_active, created_at, updated_at
- Register endpoint creates user with bcrypt-hashed password and returns JWT
- Login endpoint verifies password against bcrypt hash and returns JWT
- get_current_user dependency now queries real User from database via JWT sub claim
- Mock-token auth still works in development mode (no regression in existing tests)
- 9 comprehensive auth tests covering registration, login, JWT acceptance, and backward compat

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 -- Write test stubs for auth behaviors** - `6335ec2` (test)
2. **Task 2: User model, migration, schemas, and auth service updates** - `3dd35b4` (feat)
3. **Task 3: Register/login endpoints and get_current_user DB query** - `2dee739` (feat)

## Files Created/Modified
- `backend/app/tests/test_auth.py` - 9 test methods covering User model, register, login, JWT acceptance, mock-token compat
- `backend/migrations/delta/005_users_table.sql` - Users table DDL with seed dev user
- `backend/app/models/database.py` - Added User(Base) SQLAlchemy model
- `backend/app/models/schemas.py` - Added RegisterRequest, LoginRequest, UserUpdate schemas; display_name to User
- `backend/app/api/endpoints/auth.py` - Register, login, profile endpoints; kept legacy magic-link endpoints
- `backend/app/api/dependencies.py` - get_current_user queries real User from DB, added HTTPException re-raise
- `backend/app/services/auth_service.py` - MockAuthService returns display_name="Dev User"

## Decisions Made
- Used `/api/projects/` for JWT acceptance test instead of `/api/v2/projects` (which does not exist in the codebase)
- Kept legacy magic-link endpoints for backward compatibility rather than removing them
- Added `except HTTPException: raise` before generic except in get_current_user to avoid swallowing specific 401s

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected test endpoint from /api/v2/projects to /api/projects/**
- **Found during:** Task 1 (test stubs)
- **Issue:** Plan referenced `/api/v2/projects` endpoint which does not exist in the codebase; only `/api/projects/` is registered
- **Fix:** Used `/api/projects/` in test_jwt_accepted_by_endpoints and test_mock_token_still_works
- **Files modified:** backend/app/tests/test_auth.py
- **Verification:** Tests pass with correct endpoint
- **Committed in:** 6335ec2 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correction for test correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auth foundation complete with real user DB lookup
- Ready for Plan 02 (frontend auth integration, login/register UI, token storage)
- All existing tests pass -- safe to build on top of

## Self-Check: PASSED

All files verified present. All 3 commit hashes confirmed in git log.

---
*Phase: 35-real-authentication-user-model*
*Completed: 2026-03-23*
