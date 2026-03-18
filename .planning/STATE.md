---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Shotlist & Production Breakdown
status: defining_requirements
stopped_at: Milestone v3.0 started — defining requirements
last_updated: "2026-03-18T00:00:00.000Z"
last_activity: 2026-03-18 -- v3.0 Shotlist & Production Breakdown started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** v3.0 Shotlist & Production Breakdown

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-18 — Milestone v3.0 started

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

v1.0 decisions carried forward:
- Architecture: Build custom using only existing dependencies -- no LangGraph, CrewAI, or AutoGen
- Architecture: Pipeline re-composes on agent CRUD via BackgroundTasks
- Architecture: Session-per-task pattern for `asyncio.gather` parallel reviews

v2.0 decisions carried forward:
- Breakdown is NOT a template phase -- cross-cutting derived view with dedicated tables, API, and page
- Bidirectional sync on save/generate (staleness flag), not real-time
- Reverse sync is user-initiated only, not automatic script modification
- Single breakdown_elements table with category column + JSONB metadata
- AI extraction uses structured outputs (schema-enforced JSON) via upgraded SDKs
- `delta/` directory for incremental migrations

### Pending Todos

None yet.

### Blockers/Concerns

- SDK version floors verified and upgraded (openai>=1.40.0, anthropic>=0.77.0) -- RESOLVED
- Scene ListItem ID stability: element_scene_links cascades on ListItem deletion; links break if scenes regenerated

## Session Continuity

Last session: 2026-03-18
Stopped at: Milestone v3.0 started — defining requirements
Resume file: None
