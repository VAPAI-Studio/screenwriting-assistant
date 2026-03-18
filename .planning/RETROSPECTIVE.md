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

## Cross-Milestone Trends

| Trend | v1.0 | v2.0 |
|-------|------|------|
| Phases | 8 | 8 |
| Plans | 16 | 16 |
| Timeline | ~2 days | 17 days |
| Verification gaps at audit | 0 | 2 (Phase 13 docs, scene_wizard) |
| Phases needing gap closure | 0 | 2 (Phase 15, 16) |
| Nyquist compliant phases | 1/8 | 1/8 |

**Pattern:** Both milestones completed with 1 Nyquist-compliant phase (Phase 7). Nyquist compliance is a persistent backlog item across both milestones.
