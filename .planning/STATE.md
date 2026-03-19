---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Shotlist & Production Breakdown
status: completed
stopped_at: Completed 18-two-mode-ui-shell/18-02-PLAN.md
last_updated: "2026-03-19T18:35:43.613Z"
last_activity: 2026-03-19 — Phase 17 Plan 01 completed (data foundation)
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** v3.0 Shotlist & Production Breakdown — Phase 17 Plan 01 complete

## Current Position

Phase: 17 of 25 (Data Foundation)
Plan: 1 of 1 in current phase
Status: Phase 17 complete
Last activity: 2026-03-19 — Phase 17 Plan 01 completed (data foundation)

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 1 (v3.0) / 33 (lifetime)
- Average duration: 5min (v3.0) / see milestones for historical
- Total execution time: 0.1 hours (v3.0)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 17-data-foundation | 1 | 5min | 5min |

**Recent Trend:**

- Last 5 plans: 17-01 (5min)
- Trend: --

*Updated after each plan completion*
| Phase 18-two-mode-ui-shell P01 | 12 | 3 tasks | 4 files |
| Phase 18-two-mode-ui-shell P02 | 3 | 3 tasks | 3 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- Scene ListItem ID stability: element_scene_links cascades on ListItem deletion; links break if scenes regenerated (carried from v2.0)
- Text Selection API cross-browser testing needed (Safari quirks) — research P2

## Session Continuity

Last session: 2026-03-19T18:20:27.161Z
Stopped at: Completed 18-two-mode-ui-shell/18-02-PLAN.md
Resume file: None
