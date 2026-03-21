---
gsd_state_version: 1.0
milestone: v3.1
milestone_name: AI Shotlist Generation
status: unknown
stopped_at: Completed 27-01-PLAN.md (Phase 27 complete)
last_updated: "2026-03-21T22:11:29.698Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 28 — ux-improvements

## Current Position

Phase: 28 (ux-improvements) — EXECUTING
Plan: 1 of 3

## Performance Metrics

**Velocity:**

- Total plans completed: 47 (lifetime)
- Average duration: ~3min (v3.0)
- Total execution time: 0.33 hours (v3.0)

**By Phase (v3.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 17-data-foundation | 1 | 5min | 5min |
| 19-shot-crud-api-core-model | 1 | 3min | 3min |
| 20-shotlist-panel | 2 | 6min | 3min |
| 21-script-read-view-text-selection | 1 | 2min | 2min |
| 22-media-upload-backend | 1 | 4min | 4min |

**Recent Trend:**

- Last 5 plans: 19-01 (3min), 20-01 (4min), 20-02 (2min), 21-01 (2min), 22-01 (4min)
- Trend: improving

| Phase 26 P01 | 4min | 2 tasks | 5 files |
| Phase 26 P02 | 6min | 2 tasks | 3 files |
| Phase 27 P01 | 4min | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

Relevant to v3.1:

- JSONB `fields` column for shot properties -- freeform schema
- Two-phase AI call pattern (stream then extract) from breakdown chat
- Staleness flag pattern (save/generate triggers stale, user acknowledges)
- Shot.scene_item_id uses ON DELETE SET NULL
- [Phase 26]: user_modified not in ShotCreate; always starts False, only set by update endpoint
- [Phase 26]: ai_generated passed through ShotCreate for AI generation service to set on creation
- [Phase 26]: ShotlistGenerationService uses temperature=0.3, max_tokens=8000 for generation
- [Phase 26]: Smart merge deletes stale AI shots, preserves user_modified and manual user shots
- [Phase 26]: Generate endpoint at POST /api/shots/{project_id}/generate
- [Phase 27]: Used useEffect callback to lift generate mutation state from ShotlistPanel to BreakdownLayout

### Pending Todos

- Nyquist validation for phases 17-25 (carried forward)

### Blockers/Concerns

- 3 pre-existing TypeScript build errors in unrelated files (IndividualEditorView, RepeatableCardsView, SidebarChat)
- `user_modified` flag added to Shot model via delta migration 003 (Plan 26-01 complete)

## Session Continuity

Last session: 2026-03-21T17:51:48.266Z
Stopped at: Completed 27-01-PLAN.md (Phase 27 complete)
Resume file: None
