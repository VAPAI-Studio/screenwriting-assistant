---
phase: 13-breakdown-page
plan: "01"
subsystem: ui
tags: [react, typescript, fastapi, pydantic, sqlalchemy, react-query]

# Dependency graph
requires:
  - phase: 09-breakdown-data-foundation
    provides: BreakdownElement, ElementSceneLink ORM models and CRUD API
  - phase: 10-breakdown-api-crud
    provides: breakdown endpoints (list, create, update, delete, scene links, summary, extract)
  - phase: 12-staleness-hooks
    provides: breakdown_stale flag and staleness detection
provides:
  - SceneLinkResponse schema in backend/app/models/schemas.py with scene_links on BreakdownElementResponse
  - 6 typed breakdown API client methods in frontend/src/lib/api.tsx
  - BreakdownCategory, SceneLink, BreakdownElement, BreakdownSummary, BreakdownRun TypeScript types
  - BREAKDOWN_CATEGORIES constant in frontend/src/lib/constants.ts
  - QUERY_KEYS.BREAKDOWN_SUMMARY and QUERY_KEYS.BREAKDOWN_ELEMENTS in constants.ts
  - ROUTES.PROJECT_BREAKDOWN helper in constants.ts
  - /projects/:projectId/breakdown route in App.tsx before /:phase wildcard
  - PhaseNavigation Breakdown tab (onBreakdownClick / isBreakdownActive props)
  - BreakdownPage stub component at frontend/src/components/Breakdown/BreakdownPage.tsx
affects:
  - 13-02 (BreakdownPage full implementation imports from all files defined here)
  - 13-03 (scene link management uses these types and API methods)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "selectinload for scene_links eager loading to avoid lazy-load errors outside session context"
    - "import('../types') pattern for inline type imports in api.tsx method signatures"
    - "Breakdown route placed BEFORE /:phase wildcard in App.tsx to prevent route collision"

key-files:
  created:
    - frontend/src/components/Breakdown/BreakdownPage.tsx
    - .planning/phases/13-breakdown-page/deferred-items.md
  modified:
    - backend/app/models/schemas.py
    - backend/app/api/endpoints/breakdown.py
    - backend/app/tests/test_breakdown_api.py
    - frontend/src/types/index.ts
    - frontend/src/lib/constants.ts
    - frontend/src/lib/api.tsx
    - frontend/src/App.tsx
    - frontend/src/components/Workspace/PhaseNavigation.tsx
    - frontend/src/components/Workspace/ProjectWorkspace.tsx

key-decisions:
  - "selectinload on scene_links in list_elements, create_element, update_element to guarantee relationship loaded in response serialization"
  - "BreakdownPage stub returns minimal div so route is registered before Plan 13-02 builds the real page"
  - "Breakdown tab uses amber-400 active color (matching scenes phase) to distinguish from other phases"
  - "isBreakdownActive=false hard-coded in ProjectWorkspace since that page is never the breakdown page"

patterns-established:
  - "Breakdown API methods use fetchWithTimeout (standard 30s timeout) not CHAT_TIMEOUT"
  - "BREAKDOWN_CATEGORIES typed as Array<{ value: BreakdownCategory; label: string }> for use in category filter UI"

requirements-completed:
  - UI-01
  - UI-02
  - UI-03

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 13 Plan 01: Breakdown Page Contracts Summary

**SceneLinkResponse schema + 6 typed API client methods + TypeScript types + App route + PhaseNavigation Breakdown tab establishing all contracts for Plans 13-02 and 13-03**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-14T14:49:22Z
- **Completed:** 2026-03-14T14:54:12Z
- **Tasks:** 3 (Task 0 TDD + Task 1 + Task 2)
- **Files modified:** 9

## Accomplishments
- Added `SceneLinkResponse` to backend schemas and `scene_links: List[SceneLinkResponse]` to `BreakdownElementResponse`, backed by `selectinload` in all element-returning endpoints
- Created all TypeScript type definitions and `BREAKDOWN_CATEGORIES`, `QUERY_KEYS.BREAKDOWN_*`, `ROUTES.PROJECT_BREAKDOWN` constants
- Added 6 typed API client methods and wired the `/projects/:projectId/breakdown` route before `/:phase` wildcard with a `BreakdownPage` stub
- Added `Breakdown` tab to `PhaseNavigation` with `onBreakdownClick`/`isBreakdownActive` props; wired in `ProjectWorkspace`

## Task Commits

Each task was committed atomically:

1. **Task 0: SceneLinkResponse + scene_links + backend tests (TDD)** - `1c6b322` (feat)
2. **Task 1: TypeScript types, constants, API client** - `93db6c4` (feat)
3. **Task 2: App.tsx route, PhaseNavigation tab, BreakdownPage stub** - `6d5f3f4` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 0 used TDD — test written first (RED), then implementation (GREEN)_

## Files Created/Modified
- `backend/app/models/schemas.py` - Added SceneLinkResponse, extended BreakdownElementResponse.scene_links
- `backend/app/api/endpoints/breakdown.py` - Added selectinload import and eager loading on list/create/update
- `backend/app/tests/test_breakdown_api.py` - Added test_element_response_includes_scene_links
- `frontend/src/types/index.ts` - Added BreakdownCategory, SceneLink, BreakdownElement, BreakdownRun, BreakdownSummary, BreakdownElementCreate, BreakdownElementUpdate
- `frontend/src/lib/constants.ts` - Added BREAKDOWN_CATEGORIES, QUERY_KEYS.BREAKDOWN_*, ROUTES.PROJECT_BREAKDOWN
- `frontend/src/lib/api.tsx` - Added 6 breakdown API methods
- `frontend/src/App.tsx` - Added /projects/:projectId/breakdown route before /:phase
- `frontend/src/components/Workspace/PhaseNavigation.tsx` - Added ListChecks icon, onBreakdownClick/isBreakdownActive props, Breakdown tab
- `frontend/src/components/Workspace/ProjectWorkspace.tsx` - Wired onBreakdownClick and isBreakdownActive into PhaseNavigation
- `frontend/src/components/Breakdown/BreakdownPage.tsx` - Created stub component (Plan 13-02 will replace)

## Decisions Made
- Used `selectinload` on `scene_links` in all endpoints that return `BreakdownElementResponse` to avoid lazy-load errors outside SQLAlchemy session context
- `BreakdownPage` stub renders a placeholder div — keeps route registered without blocking plan execution
- Breakdown tab uses amber-400 active color (matching the scenes phase palette) for visual consistency
- `isBreakdownActive=false` hard-coded in ProjectWorkspace — that workspace page is never the breakdown page

## Deviations from Plan

None - plan executed exactly as written.

Pre-existing TypeScript build errors in unrelated files (IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx) were logged to `deferred-items.md` and not modified (out of scope per deviation rules).

## Issues Encountered
- Pre-existing TypeScript errors in 3 files not modified by this plan prevent `tsc` from exiting 0. Logged to `deferred-items.md`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All contracts established: Plan 13-02 can import from types/index.ts, constants.ts, and api.tsx without modification
- BreakdownPage stub at correct route — Plan 13-02 replaces the stub with the full component
- PhaseNavigation Breakdown tab is live — clicking it navigates to /projects/:projectId/breakdown
- Backend scene_links field tested and green (23/23 tests)

---
*Phase: 13-breakdown-page*
*Completed: 2026-03-14*

## Self-Check: PASSED

All 11 files found. All 3 task commits verified.
