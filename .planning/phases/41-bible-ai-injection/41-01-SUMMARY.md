---
phase: 41-bible-ai-injection
plan: 01
subsystem: api
tags: [openai, series-bible, prompt-injection, fastapi, sqlalchemy]

# Dependency graph
requires:
  - phase: 37-bible-data-api
    provides: Show model with bible columns (bible_characters, bible_world_setting, bible_season_arc, bible_tone_style, episode_duration_minutes)
  - phase: 39-episodes
    provides: Project.show_id FK linking episodes to shows
provides:
  - build_bible_context() shared helper for all AI prompt injection
  - Bible-aware AI generation for episode projects across all services
  - bible_context parameter on template_ai_service, openai_service, and breakdown_service
affects: [42-bible-ui-indicators, 43-polish-ux, ai-generation, breakdown-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: [bible-context-injection-pattern, prepend-with-separator]

key-files:
  created:
    - backend/app/utils/bible_context.py
    - backend/app/tests/test_bible_injection.py
  modified:
    - backend/app/services/template_ai_service.py
    - backend/app/services/openai_service.py
    - backend/app/services/breakdown_service.py
    - backend/app/api/endpoints/wizards.py
    - backend/app/api/endpoints/ai_chat.py
    - backend/app/api/endpoints/review.py
    - backend/app/api/endpoints/breakdown.py

key-decisions:
  - "Bible context built once in request handler and passed as string to background tasks (avoids DB re-fetch)"
  - "Bible context prepended with --- separator before existing prompt content"
  - "Returns None (no injection) for standalone projects, empty bibles, and missing shows"

patterns-established:
  - "Bible injection pattern: call build_bible_context(db, project) before any AI service call, pass as Optional[str]"
  - "Separator pattern: bible_context + newline + --- + newline + existing prompt content"

requirements-completed: [BIBL-04]

# Metrics
duration: 13min
completed: 2026-03-24
---

# Phase 41 Plan 01: Bible AI Injection Summary

**Shared build_bible_context() helper injecting series bible (characters, world, arc, tone, duration) into all AI prompts for episode projects via TDD**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-24T20:57:41Z
- **Completed:** 2026-03-24T21:10:40Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Created build_bible_context() helper that formats show bible data for AI prompts, returning None for standalone projects
- Modified all 3 AI services (template_ai_service, openai_service, breakdown_service) to accept and prepend bible_context
- Wired bible context through all 4 endpoint files (wizards, ai_chat, review, breakdown) covering 9 call sites
- 13 unit tests covering all helper edge cases and service injection points

## Task Commits

Each task was committed atomically:

1. **Task 1: Create bible context helper, tests, and modify service methods (TDD)**
   - `fe58b35` (test: add failing tests for bible context injection)
   - `84d638d` (feat: implement bible context helper and service injection)
2. **Task 2: Wire bible context through all endpoint handlers** - `0c1487d` (feat)

## Files Created/Modified
- `backend/app/utils/bible_context.py` - Shared build_bible_context() helper
- `backend/app/tests/test_bible_injection.py` - 13 tests across 4 test classes
- `backend/app/services/template_ai_service.py` - bible_context param on _build_project_context
- `backend/app/services/openai_service.py` - bible_context param on _get_system_prompt and review_section
- `backend/app/services/breakdown_service.py` - bible_context param on _call_ai_extraction and extract
- `backend/app/api/endpoints/wizards.py` - Bible context built and passed to background task
- `backend/app/api/endpoints/ai_chat.py` - Bible context at 6 call sites (send, stream, fill, notes, analyze, yolo)
- `backend/app/api/endpoints/review.py` - Bible context before openai_service.review_section
- `backend/app/api/endpoints/breakdown.py` - Bible context before breakdown_service.extract

## Decisions Made
- Bible context is built in the request handler and passed as a string to background tasks, avoiding the need for the background task's separate DB session to re-fetch the show
- Used Optional[str] = None parameter pattern so all existing callers are unaffected (backward compatible)
- Empty bible check: all four bible fields empty AND no duration means None is returned (no empty injection block)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures in test_session_isolation.py and test_shotlist_generation.py (unrelated to our changes, confirmed by running without changes)
- Pre-existing test ordering flakiness in test_yolo_integration.py (passes in isolation, fails in full suite due to shared state)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Bible context is now injected into all AI generation paths for episode projects
- Standalone film projects are completely unaffected
- Ready for Phase 42 (bible UI indicators) or any subsequent phase

---
*Phase: 41-bible-ai-injection*
*Completed: 2026-03-24*
