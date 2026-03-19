---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Shotlist & Production Breakdown
status: unknown
stopped_at: Completed 20-02-PLAN.md (Phase 20 complete)
last_updated: "2026-03-19T19:57:43.099Z"
progress:
  total_phases: 9
  completed_phases: 4
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 20 — shotlist-panel

## Current Position

Phase: 20 (shotlist-panel) — COMPLETE
Plan: 2 of 2 (all plans complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 4 (v3.0) / 36 (lifetime)
- Average duration: 3.5min (v3.0) / see milestones for historical
- Total execution time: 0.23 hours (v3.0)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 17-data-foundation | 1 | 5min | 5min |
| 19-shot-crud-api-core-model | 1 | 3min | 3min |
| 20-shotlist-panel | 2 | 6min | 3min |

**Recent Trend:**

- Last 5 plans: 17-01 (5min), 19-01 (3min), 20-01 (4min), 20-02 (2min)
- Trend: improving

*Updated after each plan completion*
| Phase 18-two-mode-ui-shell P01 | 12 | 3 tasks | 4 files |
| Phase 18-two-mode-ui-shell P02 | 3 | 3 tasks | 3 files |
| Phase 20 P02 | 2 | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

v2.0 decisions carried forward:

- Breakdown is NOT a template phase — cross-cutting derived view
- Bidirectional sync on save/generate (staleness flag), not real-time
- Single breakdown_elements table with category column + JSONB metadata
- `delta/` directory for incremental migrations

v3.0 decisions (from research):

- JSONB for shot fields — extensible, matches freeform requirement
- CSS variables scoped to mode context for visual identity separation
- Pillow only new backend dep; lean on existing stack
- Media stored locally (Docker volume), not S3/CDN for MVP
- Extend SidebarChat — don't create separate chat component
- Script view is read-only — no rich text editor needed

v3.0 decisions (from execution):

- Shot.scene_item_id uses ON DELETE SET NULL so shots survive scene deletion
- AssetMedia has dual nullable FKs (element_id, shot_id) with SET NULL
- AssetMedia.shot cascade="all, delete-orphan" cleans up media when shot deleted
- [Phase 18-two-mode-ui-shell]: Used .breakdown-mode CSS class for palette override — consistent with Tailwind class-based theming
- [Phase 18-two-mode-ui-shell]: ModeToggle self-guards via useParams returning null when projectId absent
- [Phase 18-two-mode-ui-shell]: BreakdownPage import commented out (not deleted) in App.tsx — reserved for Phase 23; TypeScript noUnusedLocals prevented keeping as live unused import
- [Phase 19-shot-crud-api-core-model]: _verify_project_ownership copied locally into shots.py -- avoids cross-module coupling
- [Phase 19-shot-crud-api-core-model]: Reorder returns 403 for foreign shot IDs (not 404) -- ownership violation vs not-found
- [Phase 19-shot-crud-api-core-model]: PUT fields replacement (not merge) -- consistent with JSONB column semantics
- [Phase 20-shotlist-panel]: Frontend spreads existing fields before overriding changed key in update mutation -- prevents JSONB wipe since PUT replaces entire fields dict
- [Phase 20-shotlist-panel]: Scene grouping is frontend-only -- flat API response grouped by scene_item_id with unassigned shots last
- [Phase 20-shotlist-panel]: 5 visible columns in table (shot_size, camera_angle, camera_movement, description, action); remaining 8 fields deferred to detail/expansion view
- [Phase 20-shotlist-panel]: Empty state CTA creates shot with scene_item_id: null (unassigned) -- simplest approach, user can reassign later
- [Phase 20-shotlist-panel]: Reorder swaps sort_order values between adjacent shots -- minimizes API payload vs recalculating all
- [Phase 20-shotlist-panel]: Action controls (reorder + delete) use opacity-0 group-hover:opacity-100 for hover-reveal
- [Phase 20]: Empty state CTA creates shot with scene_item_id: null (unassigned)
- [Phase 20]: Reorder swaps sort_order values between adjacent shots -- minimizes API payload
- [Phase 20]: Action controls use opacity-0 group-hover:opacity-100 for hover-reveal

### Pending Todos

None yet.

### Blockers/Concerns

- Scene ListItem ID stability: element_scene_links cascades on ListItem deletion; links break if scenes regenerated (carried from v2.0)
- Text Selection API cross-browser testing needed (Safari quirks) — research P2

## Session Continuity

Last session: 2026-03-19T19:53:01.420Z
Stopped at: Completed 20-02-PLAN.md (Phase 20 complete)
Resume file: None
