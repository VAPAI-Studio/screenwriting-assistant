---
phase: 11-ai-extraction-service
plan: 01
subsystem: ai, api
tags: [openai, anthropic, structured-outputs, pydantic, extraction, breakdown]

# Dependency graph
requires:
  - phase: 10-breakdown-api
    provides: BreakdownElement, ElementSceneLink, BreakdownRun database models and CRUD endpoints
provides:
  - chat_completion_structured() function in ai_provider.py for dual-provider structured outputs
  - BreakdownService class with extraction context builder and user prompt formatter
  - ExtractionResponse/ExtractedElement/ExtractedSceneAppearance Pydantic models for structured AI output
  - EXTRACTION_SYSTEM_PROMPT with on-screen-only and deduplication rules
affects: [11-02-extraction-pipeline, 11-03-extraction-endpoint]

# Tech tracking
tech-stack:
  added: [openai>=1.40.0, anthropic>=0.77.0]
  patterns: [structured-outputs-via-pydantic, extraction-context-builder, scene-indexed-prompting]

key-files:
  created:
    - backend/app/services/breakdown_service.py
  modified:
    - backend/app/services/ai_provider.py
    - backend/requirements.txt

key-decisions:
  - "Use response_format JSON schema for Anthropic structured outputs (more robust than messages.parse() across SDK versions)"
  - "OpenAI structured output tries stable API first, falls back to beta API for older SDK versions"
  - "Scene indexing is 1-based in prompts so AI scene_index maps directly to position"

patterns-established:
  - "chat_completion_structured() pattern: Type[T] response_model parameter returning validated Pydantic instance"
  - "ExtractionContext dataclass for gathering and passing DB data to prompt builder"
  - "Scene-indexed prompting: numbered scenes in prompt with AI returning integer indices for reliable matching"

requirements-completed: [EXTR-01, EXTR-02, EXTR-04]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 11 Plan 01: AI Extraction Service Foundation Summary

**Dual-provider structured output function and BreakdownService skeleton with Pydantic extraction models and database context builder**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T20:39:55Z
- **Completed:** 2026-03-13T20:42:59Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `chat_completion_structured()` to ai_provider.py supporting both OpenAI and Anthropic structured outputs
- Upgraded SDK version floors (openai>=1.40.0, anthropic>=0.77.0) for structured output support
- Created BreakdownService class with `_build_extraction_context()` that gathers screenplay content, character names, and scene summaries from the database
- Defined ExtractionResponse/ExtractedElement/ExtractedSceneAppearance Pydantic models with Field descriptions for schema-enforced AI responses
- Added EXTRACTION_SYSTEM_PROMPT with on-screen-only extraction rules (EXTR-04) and deduplication instructions

## Task Commits

Each task was committed atomically:

1. **Task 1: Upgrade SDK versions and add chat_completion_structured()** - `2f2585b` (feat)
2. **Task 2: Create BreakdownService skeleton with Pydantic models and context builder** - `3c58f83` (feat)

## Files Created/Modified
- `backend/requirements.txt` - Updated openai and anthropic SDK version floors
- `backend/app/services/ai_provider.py` - Added chat_completion_structured(), _openai_structured(), _anthropic_structured() functions
- `backend/app/services/breakdown_service.py` - New file: BreakdownService class, Pydantic models, ExtractionContext, system prompt, context builder

## Decisions Made
- Used `response_format` JSON schema approach for Anthropic (rather than `messages.parse()`) for broader SDK compatibility
- OpenAI structured output implementation tries stable `client.chat.completions.parse()` first, falls back to `client.beta.chat.completions.parse()` for older SDK versions
- Scene indexing uses 1-based numbering in prompts so AI `scene_index` references map directly to position without offset arithmetic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- BreakdownService skeleton ready for Plan 11-02 to implement the full extraction pipeline (extract() method)
- chat_completion_structured() ready for Plan 11-02 to use for AI extraction calls
- ExtractionResponse model ready to be passed as response_model to structured output function

## Self-Check: PASSED

All files verified present. All commits verified in git log.

---
*Phase: 11-ai-extraction-service*
*Completed: 2026-03-13*
