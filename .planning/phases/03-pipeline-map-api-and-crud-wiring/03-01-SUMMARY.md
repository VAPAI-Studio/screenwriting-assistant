---
phase: 03-pipeline-map-api-and-crud-wiring
plan: 01
subsystem: api
tags: [fastapi, backgroundtasks, pipeline-composer, pydantic, sqlalchemy]

# Dependency graph
requires:
  - phase: 01-db-foundation
    provides: "AgentPipelineMap model, PipelineMapEntry/PipelineMapResponse schemas"
  - phase: 02-pipeline-composer-service
    provides: "pipeline_composer singleton with compose_pipeline() and is_semantic_change()"
provides:
  - "GET /api/agents/pipeline-map endpoint returning PipelineMapResponse"
  - "Background pipeline recomposition on agent create/update/delete"
  - "AgentUpdate schema with system_prompt_template and agent_type fields"
affects: [05-review-middleware, 07-frontend-tree, 03-02-integration-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: ["BackgroundTasks with own SessionLocal for post-response DB work", "Semantic change gating via is_semantic_change() before dispatching recomposition"]

key-files:
  created: []
  modified:
    - "backend/app/models/schemas.py"
    - "backend/app/api/endpoints/agents.py"

key-decisions:
  - "GET /pipeline-map placed after /tags and before /{agent_id} to avoid UUID parameter capture"
  - "Background helper accepts owner_id as string and creates own SessionLocal for session safety"
  - "update_agent gates recomposition on is_semantic_change() -- cosmetic fields (name, color, icon) skip recomposition"

patterns-established:
  - "Background recomposition pattern: pass string IDs, create own session, try/except/finally close"
  - "Route ordering in agents.py: static paths before parameterized {agent_id} paths"

requirements-completed: [COMP-04, COMP-01, COMP-03]

# Metrics
duration: 2min
completed: 2026-03-11
---

# Phase 3 Plan 1: Pipeline Map API and CRUD Wiring Summary

**GET /pipeline-map endpoint and BackgroundTasks wiring that auto-recomposes agent-to-step mappings on agent CRUD lifecycle events**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-11T21:47:16Z
- **Completed:** 2026-03-11T21:49:07Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Expanded AgentUpdate schema with system_prompt_template and agent_type optional fields
- Added GET /pipeline-map endpoint returning PipelineMapResponse with all user's agent-to-step mappings
- Wired BackgroundTasks into create_agent (unconditional), update_agent (semantic-gated), and delete_agent (unconditional)
- Added _recompose_pipeline_background helper with own SessionLocal and error handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand AgentUpdate schema and add GET /pipeline-map endpoint with background helper** - `c0dc1ce` (feat)
2. **Task 2: Wire BackgroundTasks into agent create, update, and delete endpoints** - `3a47ac9` (feat)

## Files Created/Modified
- `backend/app/models/schemas.py` - Added system_prompt_template and agent_type fields to AgentUpdate
- `backend/app/api/endpoints/agents.py` - Added imports, _recompose_pipeline_background helper, GET /pipeline-map endpoint, BackgroundTasks wiring in create/update/delete

## Decisions Made
- GET /pipeline-map placed after /tags and before /{agent_id} to avoid FastAPI interpreting "pipeline-map" as a UUID parameter
- Background helper creates its own SessionLocal following the session-per-task pattern (BackgroundTasks run after response is sent)
- update_agent gates recomposition on is_semantic_change(update_data) so cosmetic-only changes (name, color, icon) do not trigger AI recomposition
- owner_id passed as string to background helper to match Phase 2's string-based owner_id storage pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pipeline map API is live and wired to agent CRUD lifecycle
- Ready for 03-02 integration tests to validate end-to-end behavior
- Downstream consumers (Phase 5 review middleware, Phase 7 frontend tree) can now query GET /pipeline-map

## Self-Check: PASSED

- FOUND: backend/app/models/schemas.py
- FOUND: backend/app/api/endpoints/agents.py
- FOUND: commit c0dc1ce
- FOUND: commit 3a47ac9
- FOUND: 03-01-SUMMARY.md

---
*Phase: 03-pipeline-map-api-and-crud-wiring*
*Completed: 2026-03-11*
