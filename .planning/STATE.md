---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: Script Quality
status: executing
stopped_at: Completed 45-01-PLAN.md
last_updated: "2026-06-06T03:29:09Z"
last_activity: 2026-06-06 -- Phase 45 Plan 01 executed (continuity-aware generation)
progress:
  total_phases: 14
  completed_phases: 10
  total_plans: 14
  completed_plans: 14
  percent: 72
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** v6.0 Script Quality — improve craft quality of AI-generated screenplays (continuity, format fidelity, character voice, craft guidance, side-by-side eval)

## Current Position

Phase: Phase 45 (Continuity-Aware Generation) — in progress
Plan: 45-01 complete
Status: Ready to verify / continue
Last activity: 2026-06-06 -- Phase 45 Plan 01 executed (continuity-aware generation)

## Performance Metrics

**Velocity:**

- Total plans completed: 57 (lifetime)
- Average duration: ~3min (recent)
- Total execution time: ~2.85 hours (lifetime)

**Recent Trend:**

- Last 5 plans: 37-01 (5min), 38-01 (4min), 38-02 (3min), 44-01 (6min), 45-01 (13min)
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
- [Phase 44]: Atomic SQL UPDATE for request_count avoids race conditions vs ORM-level increment
- [Phase 44]: Per-key rate limiter uses in-memory timestamp tracking (same pattern as IP rate limiter)
- [Phase 44]: rate_limit column defaults to NULL meaning use system default (1000 req/hour)
- [Phase 45]: Scene generation threads a running prose synopsis + the immediately-preceding scene's verbatim text into each later prompt; first/single scene gets no continuity block
- [Phase 45]: Synopsis re-summarized to a ~400-word cap per scene via a separate json_mode=False chat_completion call; advances only on success so a failed scene cannot poison continuity
- [Phase 45]: Final synopsis persisted into existing screenplay_editor PhaseData.content JSON via flag_modified — no migration; per-screenplay {title,content,episode_index} contract unchanged

### Pending Todos

None.

### Blockers/Concerns

- None. Pre-existing TypeScript build errors in IndividualEditorView, RepeatableCardsView, SidebarChat were fixed in session following v4.2 completion.
- v5.0 phases renumbered from 36-37 to 43-44 to make room for v4.2

## Session Continuity

Last session: 2026-06-06T03:29:09Z
Stopped at: Completed 45-01-PLAN.md
Resume file: None
