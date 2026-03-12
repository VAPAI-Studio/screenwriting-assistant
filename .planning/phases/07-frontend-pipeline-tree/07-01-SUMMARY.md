---
phase: 07-frontend-pipeline-tree
plan: 01
subsystem: api
tags: [typescript, react-query, fastapi, pipeline-map, agents]

# Dependency graph
requires:
  - phase: 03-api-and-recomposition
    provides: "GET /api/agents/pipeline-map and PATCH /api/agents/{id} backend endpoints"
provides:
  - "PipelineMapEntry and PipelineMapResponse TypeScript interfaces"
  - "QUERY_KEYS.PIPELINE_MAP constant for React Query cache keys"
  - "api.getPipelineMap() fetch method for pipeline map data"
  - "api.updateAgent() fetch method for agent PATCH updates"
  - "Backend list_agents returning all agents (including inactive)"
affects: [07-02-PLAN, 07-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pipeline map types mirroring backend Pydantic schemas"

key-files:
  created: []
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/constants.ts
    - frontend/src/lib/api.tsx
    - backend/app/api/endpoints/agents.py

key-decisions:
  - "No new dependencies needed -- all types, constants, and API methods use existing project patterns"

patterns-established:
  - "PipelineMapEntry/Response types follow same string-UUID convention as Agent type"

requirements-completed: [TREE-01, TREE-03]

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 7 Plan 1: API Layer & Backend Fix Summary

**PipelineMapEntry/Response types, PIPELINE_MAP query key, getPipelineMap/updateAgent API methods, and backend list_agents returning inactive agents**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-12T12:18:06Z
- **Completed:** 2026-03-12T12:20:17Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added PipelineMapEntry and PipelineMapResponse TypeScript interfaces matching backend schema shapes
- Added PIPELINE_MAP query key and getPipelineMap()/updateAgent() API methods for downstream tree component
- Fixed backend list_agents to return all agents including is_active=false, preventing UX bug where toggled-off agents disappear

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PipelineMap types, PIPELINE_MAP query key, and API methods** - `085f1ae` (feat)
2. **Task 2: Remove is_active filter from backend list_agents endpoint** - `d7e521f` (fix)

## Files Created/Modified
- `frontend/src/types/index.ts` - Added PipelineMapEntry and PipelineMapResponse interfaces
- `frontend/src/lib/constants.ts` - Added PIPELINE_MAP to QUERY_KEYS object
- `frontend/src/lib/api.tsx` - Added getPipelineMap() and updateAgent() methods to api object
- `backend/app/api/endpoints/agents.py` - Removed is_active==True filter from list_agents query

## Decisions Made
- No new dependencies needed -- all changes use existing project patterns and conventions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing TypeScript errors in IndividualEditorView.tsx, RepeatableCardsView.tsx, and SidebarChat.tsx cause `npm run build` to fail. These are unrelated to Phase 07 changes and are documented in deferred-items.md. The new types/methods compile cleanly in isolation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PipelineMapEntry/Response types available for import by tree component (07-02)
- PIPELINE_MAP query key ready for React Query hooks (07-02)
- api.getPipelineMap() and api.updateAgent() ready for tree component data fetching and toggle wiring (07-02, 07-03)
- Backend list_agents now returns inactive agents, enabling frontend visual distinction of toggled-off agents

## Self-Check: PASSED

- All 4 modified files exist on disk
- Both task commits (085f1ae, d7e521f) verified in git log
- All must_have artifacts confirmed: PipelineMapEntry, PIPELINE_MAP, getPipelineMap, updateAgent
- Backend is_active filter confirmed removed

---
*Phase: 07-frontend-pipeline-tree*
*Completed: 2026-03-12*
