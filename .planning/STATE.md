---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: TV Show Mode
status: defining requirements
stopped_at: Milestone v4.0 started — defining requirements
last_updated: "2026-03-24T00:00:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-20)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Milestone v4.0 — TV Show Mode (defining requirements)

## Current Position

Phase: Not started (defining requirements)
Plan: —

## Performance Metrics

**Velocity:**

- Total plans completed: 49 (lifetime)
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
| Phase 32 P01 | 2min | 1 tasks | 3 files |
| Phase 32 P02 | 4min | 3 tasks | 10 files |
| Phase 33 P01 | 2min | 2 tasks | 5 files |
| Phase 34 P01 | 2min | 2 tasks | 5 files |
| Phase 35 P01 | 3min | 3 tasks | 7 files |
| Phase 35 P02 | 5min | 3 tasks | 9 files |

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
- [Phase 32]: Enrichment done at Pydantic level (not SQL join) for SQLite/PostgreSQL compat
- [Phase 32]: scene_title is Optional[str] to handle orphaned scene links gracefully
- [Phase 32]: Extended fields auto-save on blur with read-modify-write pattern to preserve metadata keys
- [Phase 32]: ElementCard primary click navigates to detail page; inline quick-edit preserved via pencil button
- [Phase 33]: CSS-only tooltip via title attribute for zero-dependency hover hints
- [Phase 33]: Word-boundary regex with longest-match-first ordering to avoid partial matches
- [Phase 34]: indexOf-based case-sensitive substring matching for shot.script_text overlay
- [Phase 34]: Character-level Set<Shot> coverage array merged into contiguous ranges
- [Phase 34]: Element-highlight click priority over shot-overlay click via stopPropagation
- [Phase 34]: Segment sub-splitting for partial overlap between element highlights and shot ranges
- [Phase 35]: Real user DB query in get_current_user via JWT sub claim; mock-token preserved in dev mode
- [Phase 35]: Kept legacy magic-link endpoints for backward compatibility
- [Phase 35]: Added HTTPException re-raise in get_current_user to avoid swallowing specific 401s
- [Phase 35]: Login/register routes outside ProtectedRoute wrapper to avoid infinite redirect loop
- [Phase 35]: Auth helpers in separate lib/auth.ts module for cross-component reuse
- [Phase 35]: ProfilePage uses React Query useQuery/useMutation for profile data lifecycle

### Pending Todos

- Nyquist validation for phases 17-25 (carried forward)

### Blockers/Concerns

- 3 pre-existing TypeScript build errors in unrelated files (IndividualEditorView, RepeatableCardsView, SidebarChat)
- `user_modified` flag added to Shot model via delta migration 003 (Plan 26-01 complete)

## Session Continuity

Last session: 2026-03-23T15:19:06.166Z
Stopped at: Completed 35-02-PLAN.md (Phase 35 complete)
Resume file: None
