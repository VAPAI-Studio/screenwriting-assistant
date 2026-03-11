---
phase: 02-pipeline-composer-service
plan: 01
subsystem: api
tags: [ai, pipeline, composition, sqlalchemy, caching, sha256]

# Dependency graph
requires:
  - phase: 01-db-foundation
    provides: AgentPipelineMap ORM model, PipelineMapEntry/PipelineMapResponse schemas, agent_pipeline_maps table
provides:
  - PipelineComposer singleton service with compose_pipeline(), template discovery, prompt construction, AI call, response parsing, DB full-replace
  - is_semantic_change() helper for dirty-flag gating
  - PIPELINE_BATCH_SIZE and PIPELINE_COMPOSITION_MAX_TOKENS config settings
affects: [02-pipeline-composer-service, 03-pipeline-map-api-and-crud-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns: [singleton-service, hash-based-cache, batch-splitting, full-replace-write, template-target-discovery]

key-files:
  created:
    - backend/app/services/pipeline_composer.py
    - backend/app/tests/test_pipeline_composer.py
  modified:
    - backend/app/config.py

key-decisions:
  - "String UUID casting in AgentPipelineMap creation for SQLite/PostgreSQL dual compatibility"
  - "agent_id stored as string (not UUID object) in parsed AI response for cross-database compatibility"

patterns-established:
  - "Template target discovery: filter ui_pattern containing 'wizard', exclude import_project by key"
  - "Hash-based cache: SHA-256 of sorted agents' semantic fields (system_prompt_template + description + agent_type)"
  - "Full-replace write: delete existing mappings with synchronize_session='fetch', flush, then insert fresh results"
  - "Batch splitting: ceil(N/PIPELINE_BATCH_SIZE) AI calls with concatenated results"

requirements-completed: [COMP-01]

# Metrics
duration: 7min
completed: 2026-03-11
---

# Phase 2 Plan 01: Core Pipeline Composer Service Summary

**AI-driven pipeline composition service mapping agents to wizard-pattern template steps with batch splitting, SHA-256 caching, and full-replace DB persistence**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-11T17:43:46Z
- **Completed:** 2026-03-11T17:50:37Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 3

## Accomplishments
- PipelineComposer service with compose_pipeline() producing AgentPipelineMap rows from AI analysis
- Template target discovery finding exactly 3 wizard subsections (idea_wizard, scene_wizard, script_writer_wizard), excluding import_project
- Batch splitting for >5 agents with concatenated results
- Zero-agent early return with mapping cleanup (no AI calls)
- Hash-based in-memory cache keyed on semantic fields
- is_semantic_change() helper ready for Phase 3 CRUD wiring
- All 4 COMP-01 tests pass; full suite 37/37 pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Write COMP-01 test scaffold (RED)** - `df922a3` (test)
2. **Task 2: Build pipeline_composer.py service (GREEN)** - `0d22cd2` (feat)

## Files Created/Modified
- `backend/app/services/pipeline_composer.py` - PipelineComposer class with compose_pipeline(), template discovery, AI orchestration, response parsing, cache, and is_semantic_change()
- `backend/app/tests/test_pipeline_composer.py` - 4 COMP-01 unit tests with mocked AI calls
- `backend/app/config.py` - Added PIPELINE_BATCH_SIZE (5) and PIPELINE_COMPOSITION_MAX_TOKENS (2000) settings

## Decisions Made
- Used string UUIDs consistently in AgentPipelineMap creation (`id=str(uuid4())`, `owner_id=str(owner_id)`, `agent_id=str(entry["agent_id"])`) for compatibility with both PostgreSQL (auto-casts string to UUID) and SQLite (String(36) columns in test environment)
- Kept agent_id as string after AI response parsing (validate UUID format but store as string) rather than converting to UUID object, avoiding type mismatch issues across database backends
- Test fixtures use string UUIDs (`str(uuid.uuid4())`) rather than UUID objects to match SQLite's patched String(36) column types

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] SQLite UUID/String type mismatch in test environment**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** SQLite test engine patches UUID columns to String(36), causing Agent query `Agent.owner_id == uuid_object` to return zero results (string vs UUID comparison fails). Additionally, AgentPipelineMap insert failed with sentinel matching error when id column default generated UUID objects instead of strings.
- **Fix:** (a) Changed test `owner_id` fixture to return `str(uuid.uuid4())` instead of `uuid.uuid4()`. (b) Changed test `make_agent` fixture to use `id=str(uuid.uuid4())`. (c) Updated service to create AgentPipelineMap with explicit `id=str(uuid_mod.uuid4())` and cast `owner_id`/`agent_id` to string. (d) Changed `_parse_ai_response` to store agent_id as validated string rather than UUID object.
- **Files modified:** `backend/app/services/pipeline_composer.py`, `backend/app/tests/test_pipeline_composer.py`
- **Verification:** All 4 tests pass; full suite 37/37 pass
- **Committed in:** 0d22cd2 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary to handle SQLite test infrastructure's UUID-to-String column patching. No scope creep. Production PostgreSQL behavior unaffected.

## Issues Encountered
- conftest `_patch_uuid_columns_for_sqlite` has a latent bug where `column.default.arg is uuid.uuid4` identity check never matches (each column's default holds a distinct function reference to `uuid4`). This means no UUID column defaults are actually patched to generate strings. Existing tests work because they always pass explicit IDs. Not fixed here (pre-existing, out of scope) but documented for awareness.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- pipeline_composer.py is ready for Phase 2 Plan 02 (hash-based cache and semantic change detection COMP-03 tests)
- compose_pipeline() accepts explicit Session parameter, ready for Phase 3 BackgroundTasks wiring
- is_semantic_change() helper ready for Phase 3 CRUD gating

## Self-Check: PASSED

- FOUND: backend/app/services/pipeline_composer.py
- FOUND: backend/app/tests/test_pipeline_composer.py
- FOUND: backend/app/config.py
- FOUND: 02-01-SUMMARY.md
- FOUND: df922a3 (Task 1 commit)
- FOUND: 0d22cd2 (Task 2 commit)

---
*Phase: 02-pipeline-composer-service*
*Completed: 2026-03-11*
