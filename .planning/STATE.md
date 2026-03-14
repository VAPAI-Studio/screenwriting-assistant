---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Script Breakdown
status: verifying
stopped_at: Completed 13-01-PLAN.md
last_updated: "2026-03-14T14:55:19.803Z"
last_activity: 2026-03-14 -- Completed Plan 13-01 (breakdown page contracts)
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 12
  completed_plans: 10
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-12)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 11 complete - AI Extraction Service

## Current Position

Phase: 13 of 14 (Breakdown Page)
Plan: 1 of 3 in current phase
Status: Phase 13 in progress -- Plan 01 complete (contracts, types, API client, route, nav tab)
Last activity: 2026-03-14 -- Completed Plan 13-01 (SceneLinkResponse, TypeScript types, App route, PhaseNavigation Breakdown tab)

Progress: [█████████░] 93% (v2.0 Phase 13: 1/3 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 16 (v1.0)
- v2.0 plans completed: 7
- Total execution time: 24min

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
| Phase 11 P03 | 3min | 2 tasks | 4 files |
| Phase 12-staleness-hooks P01 | 20 | 2 tasks | 4 files |
| Phase 12-staleness-hooks P02 | 2 | 1 tasks | 2 files |
| Phase 13-breakdown-page P01 | 5min | 3 tasks | 10 files |

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
- Deduplication uses (category, canonical_name.lower()) as merge key, keeping first description and merging scene appearances (Phase 11)
- Integration tests mock chat_completion_structured at module level for precision (Phase 11)
- Conftest UUID default patching uses name/module check instead of identity check for robust SQLite compat (Phase 11)
- [Phase 12-01]: Helper does NOT commit; caller's existing commit covers breakdown_stale change (one-commit rule)
- [Phase 12-01]: str() cast on all UUID filter params in phase_data.py and list_items.py for SQLite/PostgreSQL compat
- [Phase 12-01]: _is_scene_item returns PhaseData object so callers have project_id for _mark_breakdown_stale
- [Phase 12-staleness-hooks]: breakdown_stale=False cleared atomically in extract() success path between _record_run() and db.commit() -- no second commit needed (SYNC-04)
- [Phase 12-staleness-hooks]: Failure path in extract() deliberately untouched -- failed extraction must not clear stale flag
- [Phase 13-breakdown-page]: selectinload on scene_links in all element-returning endpoints to avoid lazy-load errors outside session context
- [Phase 13-breakdown-page]: [Phase 13-01]: Breakdown route placed BEFORE /:phase wildcard in App.tsx to prevent route collision

### Pending Todos

None yet.

### Blockers/Concerns

- SDK version floors verified and upgraded (openai>=1.40.0, anthropic>=0.77.0) -- RESOLVED
- Scene ListItem ID stability: element_scene_links cascades on ListItem deletion; links break if scenes regenerated

## Session Continuity

Last session: 2026-03-14T14:55:19.801Z
Stopped at: Completed 13-01-PLAN.md
Resume file: None
