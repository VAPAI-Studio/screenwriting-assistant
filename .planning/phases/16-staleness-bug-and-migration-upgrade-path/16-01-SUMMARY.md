---
phase: 16-staleness-bug-and-migration-upgrade-path
plan: 01
subsystem: api
tags: [staleness, scene_wizard, migration, breakdown, tdd, fastapi]

# Dependency graph
requires:
  - phase: 12-staleness-hooks
    provides: _mark_breakdown_stale helper in phase_data.py; one-commit rule established
  - phase: 09-breakdown-data-foundation
    provides: breakdown_elements table, breakdown_stale column on projects, migration 009

provides:
  - scene_wizard branch in wizards.py sets breakdown_stale=True via _mark_breakdown_stale
  - backend/migrations/delta/001_breakdown_tables.sql for idempotent auto-upgrade on existing Docker deployments
  - test_scene_wizard_sets_stale in TestStalenessHooks covering SYNC-03 for scene_wizard
  - SYNC-03 requirement marked [x] complete in REQUIREMENTS.md

affects:
  - frontend (StalenessBar now correctly shown after scene generation)
  - deployment (existing Docker volumes auto-upgrade breakdown schema on startup)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_mark_breakdown_stale before db.commit() in all wizard branches that touch screenplay/scene content"
    - "delta/ migration directory for idempotent schema patches on existing Docker deployments"

key-files:
  created:
    - backend/migrations/delta/001_breakdown_tables.sql
    - backend/app/tests/test_staleness.py (test_scene_wizard_sets_stale method added)
  modified:
    - backend/app/api/endpoints/wizards.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "scene_wizard _mark_breakdown_stale placed AFTER ListItem creation loop and BEFORE db.commit() — mirrors script_writer_wizard pattern exactly (one-commit rule preserved)"
  - "delta/001 is a verbatim copy of 009_breakdown_tables.sql — fully idempotent, no modifications needed"
  - "SYNC-03 traceability updated to Phase 12, Phase 16 — Phase 12 covered write/scenes PATCH and script_writer_wizard; Phase 16 completes scene_wizard"

patterns-established:
  - "All wizard branches that generate screenplay or scene content must call _mark_breakdown_stale before db.commit()"
  - "Migration deltas in backend/migrations/delta/ use ^\d+_ naming pattern and must be fully idempotent"

requirements-completed:
  - SYNC-03

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 16 Plan 01: Staleness Bug and Migration Upgrade Path Summary

**scene_wizard staleness fix (one-line _mark_breakdown_stale insertion) and breakdown schema delta for existing Docker deployments so StalenessBar appears after scene generation**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-18T19:58:50Z
- **Completed:** 2026-03-18T20:01:39Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Fixed scene_wizard branch missing _mark_breakdown_stale call — breakdown_stale now set after scenes generated
- Added idempotent migration delta (001_breakdown_tables.sql) so existing Docker deployments auto-upgrade breakdown schema on next startup
- Added test_scene_wizard_sets_stale to TestStalenessHooks (TDD: RED then GREEN in Tasks 1-2)
- All 11 staleness tests pass including the new scene_wizard coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add test_scene_wizard_sets_stale (TDD RED)** - `5cf0248` (test)
2. **Task 2: Fix scene_wizard staleness bug and copy migration delta** - `270ecaf` (fix)
3. **Task 3: Mark SYNC-03 complete and run full staleness suite** - `09676ea` (feat)

_Note: TDD task has separate RED commit before GREEN fix commit._

## Files Created/Modified
- `backend/app/api/endpoints/wizards.py` - Added `_mark_breakdown_stale(db, project.id)` before `db.commit()` in scene_wizard branch
- `backend/migrations/delta/001_breakdown_tables.sql` - Verbatim copy of 009_breakdown_tables.sql; idempotent DDL for existing deployments
- `backend/app/tests/test_staleness.py` - Added test_scene_wizard_sets_stale method to TestStalenessHooks
- `.planning/REQUIREMENTS.md` - SYNC-03 changed from [ ] to [x]; traceability row updated to "Phase 12, Phase 16 | Complete"

## Decisions Made
- `_mark_breakdown_stale` placed after ListItem creation loop and before `db.commit()` — mirrors script_writer_wizard pattern exactly; one-commit rule preserved (no second commit, no flush needed)
- delta/001 is a verbatim copy of 009 — no modifications since 009 is already fully idempotent throughout

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-existing test failure (out of scope):** `test_session_isolation.py::test_orchestrate_uses_session_factory` fails with `ValueError: Template '<MagicMock...>' not found`. This failure exists in the working tree due to pre-existing modified files (template_ai_service.py, agent_service.py listed in git status) and is unrelated to this plan's changes. Logged to deferred-items.md. All 135 other tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SYNC-03 is fully complete: all three staleness trigger paths covered (phase_data PATCH, script_writer_wizard, scene_wizard)
- StalenessBar will now correctly appear after scene generation
- Existing Docker deployments will auto-upgrade breakdown schema via delta/001 on next startup
- REQUIREMENTS.md is fully checked for all v2 requirements

## Self-Check: PASSED

All files exist, all commits verified, all success criteria met:
- `backend/migrations/delta/001_breakdown_tables.sql` - FOUND
- `backend/app/tests/test_staleness.py` (test_scene_wizard_sets_stale) - FOUND
- `.planning/phases/16-staleness-bug-and-migration-upgrade-path/16-01-SUMMARY.md` - FOUND
- Commit 5cf0248 (test RED) - FOUND
- Commit 270ecaf (fix + delta) - FOUND
- Commit 09676ea (REQUIREMENTS.md) - FOUND
- 3 _mark_breakdown_stale calls in wizards.py (1 import + 2 usage) - FOUND
- SYNC-03 [x] in REQUIREMENTS.md - FOUND
- Complete status in traceability table - FOUND

---
*Phase: 16-staleness-bug-and-migration-upgrade-path*
*Completed: 2026-03-18*
