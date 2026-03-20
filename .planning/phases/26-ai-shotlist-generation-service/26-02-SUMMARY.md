---
phase: 26-ai-shotlist-generation-service
plan: 02
subsystem: api
tags: [fastapi, openai, pydantic, structured-output, sqlalchemy, shotlist, ai-generation, smart-merge]

# Dependency graph
requires:
  - phase: 26-ai-shotlist-generation-service
    provides: "user_modified and ai_generated Boolean columns on Shot model (Plan 01)"
  - phase: 17-data-foundation
    provides: "Shot model with JSONB fields column"
provides:
  - "ShotlistGenerationService with context builder, AI caller, and smart merge"
  - "POST /api/shots/{project_id}/generate endpoint"
  - "GeneratedShot and ShotlistGenerationResponse Pydantic structured output models"
  - "Smart merge algorithm: preserves user_modified shots, deletes stale AI shots, inserts new"
  - "11 tests covering AISG-01 through AISG-06"
affects: [27-generate-shotlist-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Structured AI output with Pydantic response_model for shotlist generation"
    - "Smart merge pattern: partition existing shots by provenance, delete stale AI, preserve user-edited"
    - "1-based scene_index mapping from AI response to scene_item_id via context dataclass"

key-files:
  created:
    - "backend/app/services/shotlist_generation_service.py"
    - "backend/app/tests/test_shotlist_generation.py"
  modified:
    - "backend/app/api/endpoints/shots.py"

key-decisions:
  - "temperature=0.3 for generation (higher than extraction's 0.15 to allow creative shot choices)"
  - "max_tokens=8000 to accommodate full shotlists for long screenplays"
  - "Screenplay text truncated at 50000 chars to stay within AI context limits"
  - "Sort ordering: user_modified shots placed first within each scene, AI shots appended after"

patterns-established:
  - "ShotlistGenerationService follows same singleton + context dataclass + structured output pattern as BreakdownService"
  - "Smart merge: query all -> partition by ai_generated/user_modified -> delete stale -> insert new -> re-number"

requirements-completed: [AISG-01, AISG-02, AISG-03, AISG-04, AISG-05, AISG-06]

# Metrics
duration: 6min
completed: 2026-03-20
---

# Phase 26 Plan 02: ShotlistGenerationService Summary

**AI shotlist generation service with structured output, 1-based scene mapping, and smart merge preserving user-edited shots via chat_completion_structured**

## Performance

- **Duration:** 6min
- **Started:** 2026-03-20T20:08:54Z
- **Completed:** 2026-03-20T20:15:31Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ShotlistGenerationService with full pipeline: context builder, AI caller (structured output), and smart merge algorithm
- POST /api/shots/{project_id}/generate endpoint wired to service with project ownership verification
- 11 comprehensive tests covering all 6 requirement IDs (AISG-01 through AISG-06) pass
- Smart merge correctly deletes stale AI shots while preserving both user-modified AI shots and manually-created user shots
- Full backend suite: 216 passed (2 pre-existing failures in unrelated files)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ShotlistGenerationService** - `ebc33fd` (feat)
2. **Task 2: Wire endpoint + tests (TDD)** - `07c16db` (test: RED), `311cb5a` (feat: GREEN)

_Note: TDD Task 2 has separate RED (failing tests) and GREEN (endpoint + passing) commits_

## Files Created/Modified
- `backend/app/services/shotlist_generation_service.py` - ShotlistGenerationService with GeneratedShot/ShotlistGenerationResponse models, context builder, AI caller, smart merge (297 lines)
- `backend/app/tests/test_shotlist_generation.py` - 11 tests across 6 test classes covering AISG-01 through AISG-06 (407 lines)
- `backend/app/api/endpoints/shots.py` - Added generate endpoint import and POST /{project_id}/generate route

## Decisions Made
- Used temperature=0.3 for generation (slightly creative) vs 0.15 for extraction (deterministic) -- shotlist benefits from varied shot choices
- max_tokens=8000 to allow full shotlist generation for screenplays with many scenes (3-10 shots per scene)
- Screenplay text truncated at 50000 chars to prevent exceeding AI context window
- Generate endpoint placed before /{project_id}/{shot_id} route to prevent FastAPI matching "generate" as a shot UUID

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test file had a stray unawaited coroutine call (line calling generate() without await before the asyncio.get_event_loop() call) -- removed in GREEN phase

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 26 complete: Shot model has AI provenance tracking + full generation service
- Phase 27 (Generate Shotlist UI) can call POST /api/shots/{project_id}/generate from frontend
- Response format provides shots_created/deleted/preserved counts for UI feedback
- All 6 AISG requirements covered by tests

---
*Phase: 26-ai-shotlist-generation-service*
*Completed: 2026-03-20*
