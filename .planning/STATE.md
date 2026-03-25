---
gsd_state_version: 1.0
milestone: v4.2
milestone_name: TV Show Mode
status: complete
stopped_at: Phase 42 complete — v4.2 milestone done
last_updated: "2026-03-24T21:46:30.595Z"
progress:
  total_phases: 25
  completed_phases: 25
  total_plans: 42
  completed_plans: 42
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 42 — Breadcrumb Navigation

## Current Position

Phase: 42 (Breadcrumb Navigation) — COMPLETE
Plan: 1 of 1 (done)

## Performance Metrics

**Velocity:**

- Total plans completed: 55 (lifetime)
- Average duration: ~3min (recent)
- Total execution time: ~2.75 hours (lifetime)

**Recent Trend:**

- Last 5 plans: 35-02 (5min), 36-01 (9min), 37-01 (5min), 38-01 (4min), 38-02 (3min)
- Trend: Stable

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

Relevant to v4.2:

- Episodes reuse existing Project model with nullable show_id FK (not a separate table)
- Bible stored as columns on Show model (not separate table) for simplicity
- Bible injection modifies existing generation services, not a new service
- Standalone projects unaffected -- show_id = NULL means no bible context
- Used str() cast on UUID filters in shows router for SQLite/PostgreSQL compatibility
- Show model has no relationships yet -- Phase 37 adds bible columns, Phase 39 adds episodes
- Bible data accessed via dedicated /bible sub-resource endpoints, not mixed into ShowResponse
- Episode duration accepts any integer 1-480 (not restricted to presets)
- ShowCard displays hardcoded "0 episodes" -- actual count comes in Phase 39
- Home page split into "Shows" (indigo) and "Films" (amber) sections
- Show components live in frontend/src/components/Shows/ directory
- No query invalidation on bible mutation -- prevents refetch from overwriting local state
- Used loaded ref pattern for bible editor initial state
- Duration changes save immediately (select is discrete, not blur-based)
- [Phase 39]: Episodes reuse Project model with nullable show_id FK -- episode_number auto-increments via MAX+1
- [Phase 40]: Reuse deleteProject API for episode deletion since episodes are Projects with show_id FK
- [Phase 41]: Bible context built once in request handler, passed as string to background tasks (avoids DB re-fetch)
- [Phase 42]: Show title fetched with staleTime: Infinity in breadcrumb (stable within session)
- [Phase 42]: Breadcrumb height adjustment uses fixed 89px calc (56px header + 33px breadcrumb)

### Pending Todos

None.

### Blockers/Concerns

- None. Pre-existing TypeScript build errors in IndividualEditorView, RepeatableCardsView, SidebarChat were fixed in session following v4.2 completion.
- v5.0 phases renumbered from 36-37 to 43-44 to make room for v4.2

## Session Continuity

Last session: 2026-03-24T21:43:25.815Z
Stopped at: Completed 42-01-PLAN.md (Phase 42 complete)
Resume file: None
