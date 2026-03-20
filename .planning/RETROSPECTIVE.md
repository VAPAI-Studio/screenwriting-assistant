# Retrospective: Screenwriting Assistant

---

## Milestone: v2.0 — Script Breakdown

**Shipped:** 2026-03-18
**Phases:** 8 (9-16) | **Plans:** 16 | **Commits:** ~52 feat commits

### What Was Built

- `breakdown_elements`, `element_scene_links`, `breakdown_runs` tables with cascade-delete, soft-delete, unique constraints, and JSONB metadata
- Full CRUD REST API (7 endpoints) with 22 integration tests — list, create, update, soft-delete, scene links, extraction trigger, summary
- AI extraction service using structured outputs (GPT-4/Claude): context builder from screenplay + project data, deduplication by canonical name, scene link reconciliation, user_modified preservation
- Staleness hooks across all 4 script-change paths: phase_data PATCH, script_writer_wizard, scene_wizard (Phase 16 bug fix), list_items CRUD
- React breakdown page: CategoryTabs (Radix), ElementCard with optimistic PUT, scene chips with deep-link navigation, StalenessBar (30s polling), AddElementDialog, empty state
- Reverse sync: "Add to Characters" creates story.characters ListItem; idempotent; synced_to_characters computed field
- `delta/001_breakdown_tables.sql` idempotent migration for Docker zero-downtime upgrades

### What Worked

- **Phase 15 as a gap-closure pattern**: When Phase 13 shipped without formal VERIFICATION.md and with missing requirement documentation, dedicating a focused Phase 15 to close the documentation and fix the route bug was faster than holding Phase 13 until everything was perfect.
- **Integration checker subagent**: Caught the `selectinload` result-discarding bug (API-03/API-04) and the `LIST_ITEMS` cache invalidation gap in the audit that automated phase verification missed.
- **delta/ migration pattern**: Adding idempotent DDL to `backend/migrations/delta/` solved the Docker upgrade problem elegantly without needing any orchestration changes.
- **Structured outputs for extraction**: Schema-enforced JSON from the AI made parsing trivially reliable; no defensive error handling for malformed responses.
- **One-commit rule**: Keeping each task as a single atomic commit made the git history clean and made phase verification straightforward.

### What Was Inefficient

- **ROADMAP tracking slippage**: Phases 9 and 13 were marked `[ ]` in ROADMAP.md even after completion — the `phase complete` CLI command didn't properly update their checkboxes. Required manual notice at milestone audit time.
- **Phase 13 documentation debt**: Plan 13-03 implemented UI-07/UI-08 but the SUMMARY frontmatter and REQUIREMENTS.md weren't updated, creating a documentation trail break that required Phase 15 to close.
- **MILESTONES.md task count**: The CLI extracted `tasks: 3` instead of ~30 because SUMMARY `task_count` frontmatter uses a custom pattern the extractor didn't parse. Needed manual stat gathering.
- **scene_wizard staleness bug**: The Phase 16 bug (scene_wizard bypassing `_mark_breakdown_stale`) was discovered during Phase 15 audit, not during Phase 12 when staleness hooks were wired. A review of all `apply_wizard_result_to_db` branches at Phase 12 time would have caught it.

### Patterns Established

- **Breakdown as non-template phase**: Cross-cutting derived data (breakdown elements) live in their own tables and page, not as a template phase. This pattern could apply to any cross-cutting analytics view.
- **user_modified flag**: Simple boolean that shields user edits from AI overwrites on re-extraction. Applies to any AI-generated content that users can refine.
- **Staleness flag + banner**: `breakdown_stale` boolean + 30s polling summary query + StalenessBar is a clean, low-overhead pattern for "content may be outdated" UX without WebSockets.
- **Soft-delete + check-and-restore on create**: POST create checks for soft-deleted duplicates and restores rather than erroring — avoids confusing "duplicate" errors for items the user deleted and re-created.
- **synced_to_characters as computed field with False default**: Non-stored Pydantic field that gets populated by a pre-loop lookup. Keeps DB clean while enabling instant frontend feedback.

### Key Lessons

1. **Document as you ship**: SUMMARY frontmatter and REQUIREMENTS.md checkboxes should be updated in the same commit as the code, not deferred. Phase 15 cost was entirely documentation cleanup.
2. **Audit all branches of critical paths**: When adding a hook to a function that has multiple branches (wizards.py `apply_wizard_result_to_db`), verify ALL branches get the hook, not just the ones named in the plan.
3. **One delta file per migration**: The `delta/` directory pattern with monotonically numbered idempotent files is low-overhead and solves a real production pain point for users with persistent volumes.
4. **Integration checker catches what phase verifiers miss**: Phase verifiers check their own scope; the integration checker reads across all phases and catches wiring gaps (selectinload, cache invalidation) that individual verifiers can't see.

### Cost Observations

- Model: claude-sonnet-4-6 for all executor and verifier agents
- Sessions: ~10-12 GSD sessions across 17 days
- Notable: parallel wave execution made phases 9-12 feel fast; phases 13-16 required more sequential debugging

---

## Milestone: v3.0 — Shotlist & Production Breakdown

**Shipped:** 2026-03-20
**Phases:** 9 (17-25) | **Plans:** 14 | **Files changed:** 108 (+21,108 lines)

### What Was Built

- `shots`, `asset_media` tables with JSONB fields; `shotlist_stale` column on projects; idempotent delta migration 002
- Two-mode UI shell: ModeToggle dropdown, `/projects/:id/breakdown` route, BreakdownLayout 3-panel layout, `.breakdown-mode` CSS palette (amber → steel-blue), panel resize/collapse with localStorage persistence
- Full Shot CRUD API (6 endpoints) + scene-grouped shotlist panel with inline editing, two-click delete, arrow reorder, and optimistic cache mutations
- ScriptReadView: read-only screenplay rendering with text selection detection, floating SelectionBar, and shot creation from selected text
- Media upload backend: image/audio upload with Pillow WebP thumbnail generation, 20MB size limit, StaticFiles mount; AssetsPanel with Script/Assets toggle, category groups, thumbnails, audio playback with overlap prevention, drag-and-drop upload
- AI breakdown chat: SSE streaming endpoint with shotlist + element context injection; ShotProposalCard confirmation flow for shot create/modify; two-phase AI call (stream then JSON-mode extraction)
- Shotlist staleness hooks across 6 mutation paths (phase_data PATCH, wizards, character/scene CRUD); banner with React Query polling and dismiss

### What Worked

- **Tight phase scoping**: Each phase had exactly one responsibility — the 9-phase split (data → UI shell → CRUD → panel → script view → media backend → assets UI → AI chat → staleness) meant each phase verified cleanly and hand-offs were clear.
- **Reusing v2.0 patterns**: The staleness flag pattern from v2.0 (`breakdown_stale`) was replicated verbatim for `shotlist_stale` — same hook locations, same polling approach, same acknowledge endpoint. Zero design work needed.
- **Two-phase AI call for breakdown chat**: Streaming the response first, then running a separate JSON-mode extraction for shot actions, preserved the streaming UX while still enabling structured action parsing.
- **React Query optimistic mutations**: Implementing optimistic cache updates with rollback for delete and reorder made the UI feel instant without any custom state management.
- **AssetsPanel extract button**: Re-surfacing the breakdown extraction button inside the Assets panel (which was lost when BreakdownPage was replaced) was a quick post-audit fix that restored full feature parity.

### What Was Inefficient

- **BreakdownPage regression**: The v2.0 breakdown extraction UI was inadvertently removed when Phase 18 replaced the `/breakdown` route. Caught in manual testing after milestone audit, not during phase verification — a cross-phase regression that individual phase VERIFICATIONs couldn't detect.
- **ModeToggle navigation**: Initial implementation navigated to `/projects/:id` (Editor) when switching to Screenwriting mode, losing the user's position. Fixed post-audit with localStorage persistence of last screenwriting path.
- **Nyquist VALIDATION.md drafts**: All 9 VALIDATION.md files were created in draft state (`nyquist_compliant: false`) and never executed. Same pattern as v2.0 — Nyquist validation remains consistently deferred.
- **Scene-to-sort_order heuristic**: The ScriptReadView maps screenplay entries to scene ListItems using `sort_order === idx`, which is fragile when sort_order values have gaps. Identified in audit but not fixed — acceptable risk for v3.0 scope.

### Patterns Established

- **Two-mode app pattern**: Separate route + CSS class on `<html>` for palette switching is a clean, zero-JS-overhead approach to distinct visual identities per mode.
- **JSONB shot fields**: Storing all production fields (shot_size, camera_angle, etc.) in a single JSONB column lets the schema evolve without migrations — new field types just appear in the UI.
- **Two-phase AI streaming + action extraction**: SSE stream for UX, second JSON-mode call for structured data extraction, ShotProposalCard for confirmation. Reusable pattern for any AI action that needs user confirmation.
- **localStorage path memory for mode toggle**: Saving last screenwriting URL before switching modes lets users resume exactly where they were — applicable to any multi-mode app.

### Key Lessons

1. **Cross-phase regressions need integration testing**: The BreakdownPage removal wasn't caught by any phase verifier because each verifier only checks its own scope. The integration checker focused on wiring, not feature regressions from prior milestones. Manual testing post-audit caught it.
2. **UX flows are not just wiring**: Mode switch navigation, scroll preservation, and path memory are UX flows that need explicit success criteria in plans — they're easy to miss in automated verification.
3. **Audit before closing, not after**: Running the milestone audit before declaring "done" surfaced the two post-audit fixes (extraction button, mode toggle path). The audit earned its place as a gate.

### Cost Observations

- Model: claude-sonnet-4-6 for all agents
- Sessions: ~8-10 GSD sessions across 2 days
- Notable: Parallel phase execution (17+18+19+22 in parallel, then 20+21+23 in parallel) made v3.0 significantly faster than v2.0 despite similar scope

---

## Cross-Milestone Trends

| Trend | v1.0 | v2.0 | v3.0 |
|-------|------|------|------|
| Phases | 8 | 8 | 9 |
| Plans | 16 | 16 | 14 |
| Timeline | ~2 days | 17 days | 2 days |
| Files changed | — | — | 108 (+21k lines) |
| Verification gaps at audit | 0 | 2 (Phase 13 docs, scene_wizard) | 2 (SELC-04 heuristic, SYNC-01 reorder) |
| Post-audit fixes needed | 0 | 0 | 2 (extraction button, mode toggle path) |
| Phases needing gap closure | 0 | 2 (Phase 15, 16) | 0 |
| Nyquist compliant phases | 1/8 | 1/8 | 0/9 |

**Patterns across milestones:**
- Nyquist compliance is consistently deferred — 0 phases fully compliant in v3.0, same as v1.0/v2.0. Worth addressing as a dedicated cleanup phase.
- Integration checker catches code wiring but not behavioral regressions (BreakdownPage removal was invisible to it). Manual testing post-audit remains essential.
- v3.0's 2-day timeline vs v2.0's 17 days reflects parallel phase execution and a more modular design — the two-mode split made phases independent.
