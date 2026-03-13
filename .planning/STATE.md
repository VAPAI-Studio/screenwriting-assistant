---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Script Breakdown
status: in-progress
stopped_at: Completed 11-02-PLAN.md
last_updated: "2026-03-13T20:49:00Z"
last_activity: 2026-03-13 -- Completed Plan 11-02 (extraction pipeline implementation)
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 7
  completed_plans: 6
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 11 - AI Extraction Service

## Current Position

Phase: 11 of 14 (AI Extraction Service)
Plan: 2 of 3 in current phase
Status: Plan 11-02 complete -- extraction pipeline implemented and endpoint wired
Last activity: 2026-03-13 -- Completed Plan 11-02 (extraction pipeline implementation)

Progress: [█████████-] 86% (v2.0 Phase 11: 2/3 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 16 (v1.0)
- v2.0 plans completed: 6
- Total execution time: 21min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 Phases 1-8 | 16/16 | -- | -- |
| v2.0 Phase 9 Plan 01 | 1/14 | 1min | 1min |
| v2.0 Phase 9 Plan 02 | 2/14 | 3min | 3min |
| v2.0 Phases 9-14 | 4/14 | 15min | ~4min |
| Phase 09 P02 | 3min | 3 tasks | 3 files |
| Phase 10 P01 | 1min | 2 tasks | 2 files |
| Phase 10 P02 | 10min | 2 tasks | 2 files |
| Phase 11 P01 | 3min | 2 tasks | 3 files |
| Phase 11 P02 | 3min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

v1.0 decisions carried forward:
- Architecture: Build custom using only existing dependencies -- no LangGraph, CrewAI, or AutoGen
- Architecture: Pipeline re-composes on agent CRUD via BackgroundTasks
- Architecture: Session-per-task pattern for `asyncio.gather` parallel reviews

v2.0 decisions:
- Breakdown is NOT a template phase -- cross-cutting derived view with dedicated tables, API, and page
- Bidirectional sync on save/generate (staleness flag), not real-time
- Reverse sync is user-initiated only, not automatic script modification
- Single breakdown_elements table with category column + JSONB metadata
- AI extraction uses structured outputs (schema-enforced JSON) via upgraded SDKs
- VARCHAR(50) for breakdown category (not PG ENUM) -- extensible without migration
- Full UNIQUE constraint on (project_id, category, name) -- API handles soft-deleted duplicates via check-and-restore
- Python BreakdownCategory(str, enum.Enum) for code-level validation while keeping VARCHAR(50) in DB
- metadata_ Column alias pattern (matching AIMessage) to avoid SQLAlchemy MetaData clash
- No back_populates on ListItem for scene_links -- navigated via BreakdownElement.scene_links only
- POST create checks for soft-deleted duplicates and restores them rather than erroring (Phase 10)
- PUT update always sets user_modified=True regardless of which fields change (Phase 10)
- Ownership verification follows two-helper pattern from list_items.py (Phase 10)
- Extraction stub returns 200 (synchronous) not 202; Phase 11 implements actual async extraction (Phase 10)
- Scene link POST uses JSONResponse to return 200 for idempotent duplicates, overriding default 201 (Phase 10)
- UUID params cast to str() in all SQLAlchemy filter queries for PostgreSQL/SQLite compatibility (Phase 10)
- Scene link DELETE is hard-delete (junction table), not soft-delete (Phase 10)
- Use response_format JSON schema for Anthropic structured outputs (more robust than messages.parse() across SDK versions) (Phase 11)
- OpenAI structured output tries stable API first, falls back to beta API for older SDK versions (Phase 11)
- Scene indexing is 1-based in prompts so AI scene_index maps directly to position (Phase 11)
- Single db.commit() at end of extract() pipeline; rollback on failure then record failed run in separate transaction (Phase 11)
- User-modified elements included in element_map for scene linking even though description not overwritten (SYNC-01) (Phase 11)
- AI scene links fully replaced on re-extraction (delete-all-ai then recreate) while user links always preserved (Phase 11)

### Pending Todos

None yet.

### Blockers/Concerns

- SDK version floors verified and upgraded (openai>=1.40.0, anthropic>=0.77.0) -- RESOLVED
- Scene ListItem ID stability: element_scene_links cascades on ListItem deletion; links break if scenes regenerated

## Session Continuity

Last session: 2026-03-13T20:49:00Z
Stopped at: Completed 11-02-PLAN.md
Resume file: None
