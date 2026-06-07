---
gsd_state_version: 1.0
milestone: v7.0
milestone_name: Breakdown Fidelity
status: planning
last_updated: "2026-06-07T04:16:27.640Z"
last_activity: 2026-06-07
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** v6.0 Script Quality — improve craft quality of AI-generated screenplays (continuity, format fidelity, character voice, craft guidance, side-by-side eval)

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-06-07 — Milestone v7.0 started

## Performance Metrics

**Velocity:**

- Total plans completed: 57 (lifetime)
- Average duration: ~3min (recent)
- Total execution time: ~2.85 hours (lifetime)

**Recent Trend:**

- Last 5 plans: 46-01 (3min), 47-01 (4min), 48-01 (15min), 49-01 (10min), 49-02 (3min, AUTO only — UAT pending)
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
- [Phase 46]: Scene-writing call switched to native output (json_mode=False) so JSON string-encoding no longer degrades screenplay formatting; title parsed off a TITLE: line with scene-summary fallback (never fails on missing title)
- [Phase 46]: Native path adopted outright (no runtime A/B toggle, D-46-04); Phase 45 {screenplays,synopsis} + per-screenplay {title,content,episode_index} contract and success-only continuity advance preserved byte-for-byte
- [Phase 46]: Continuity test mock routes scene-vs-synopsis by the positive 'YOUR TASK: Write scene' marker (both calls now json_mode=False); avoids ambiguous 'story so far' string
- [Phase 47]: run_wizard injection guard broadened to wizard_type in ('scene_wizard','script_writer_wizard') so character profiles reach _generate_scripts; persisted WizardRun.config=request.config split preserved (no _characters re-persisted)
- [Phase 47]: _generate_scripts injects a conditional character_block (reused _build_character_section + a 'distinct, consistent voice' instruction) that collapses to '' when _characters is empty/absent → byte-identical Phase 46 prompt; SCENE_MARKER, json_mode=False, return contract, continuity advance unchanged
- [Phase 47]: under-specified voices are derived + carried by the Phase 45 continuity block (no structured voice ledger), consistent with Phase 45's no-ledger decision
- [Phase 48]: _generate_scripts carries an UNCONDITIONAL '## Screenwriting Craft' block (subtext/on-the-nose, economical action, show-don't-tell + 'no internal or unfilmable description', white-space pacing) as a plain f-string literal — added equally to both character paths so Phase 47's byte-identical empty-vs-absent contract holds
- [Phase 48]: craft anchors chosen to NOT collide with continuity ('Story so far'/'Previous scene') or voice ('distinct, consistent voice') markers asserted ABSENT elsewhere; all 21 prior tests stay green; lines 394-462 untouched (additive only)
- [Phase 49]: extracted _generate_one_scene as the SINGLE shared per-scene prompt source; _generate_scripts loop + new regenerate_single_scene both delegate to it (no divergent prompt); 27 prior tests stay green byte-for-byte
- [Phase 49]: single-scene regenerate returns a PREVIEW (no DB write); keep persists only screenplays[episode_index] + the matching ScreenplayContent row and marks breakdown/shotlist stale; global synopsis left untouched on keep (D-49-05); episode_index is the implicit scene key (no migration, D-49-03)
- [Phase 49]: regenerate/keep owner filter uses str() coercion (codebase _verify_project_ownership convention), not run_wizard's raw-UUID compare — Postgres-safe AND SQLite-test-safe

### Pending Todos

None.

### Blockers/Concerns

- None. Pre-existing TypeScript build errors in IndividualEditorView, RepeatableCardsView, SidebarChat were fixed in session following v4.2 completion.
- v5.0 phases renumbered from 36-37 to 43-44 to make room for v4.2

## Session Continuity

Last session: 2026-06-06T20:09:31Z
Stopped at: Completed 49-01-PLAN.md
Resume file: None
