---
phase: 67-continuity-data-model-migration
plan: 01
subsystem: database
tags: [postgres, sqlalchemy, migration, delta, continuity]

# Dependency graph
requires:
  - phase: 36-show-data-model-api
    provides: shows table + Show SQLAlchemy model
  - phase: 39-episodes
    provides: projects.show_id / episode_number (episodes as Project rows)
provides:
  - shows.continuity_mode column (VARCHAR, default 'anthology')
  - projects.episode_summary column (TEXT, nullable)
  - projects.episode_summary_stale column (BOOLEAN, default FALSE)
  - SQLAlchemy Show/Project model parity for all three columns
affects: [68-mode-aware-generation, 69-auto-episode-summary, 70-show-creation-wizard, 71-mode-aware-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "VARCHAR-not-PG-Enum for extensible mode columns (D-03, mirrors breakdown category String(50) decision)"
    - "server_default parity between delta SQL and SQLAlchemy column so non-ORM inserts default correctly"

key-files:
  created:
    - backend/migrations/delta/011_continuity_columns.sql
  modified:
    - backend/app/models/database.py

key-decisions:
  - "continuity_mode is VARCHAR(20) with string default 'anthology', NOT a PG Enum (D-03) — new modes need no ALTER TYPE migration"
  - "Default 'anthology' = zero behavior change on upgrade (D-01); existing shows behave as today (bible-only)"
  - "episode_summary_stale mirrors breakdown_stale/shotlist_stale exactly (Boolean, server_default false)"
  - "Both ORM default and server_default set on continuity_mode so rows inserted outside the ORM also default correctly"

patterns-established:
  - "Migration↔model parity: every delta ADD COLUMN has a matching SQLAlchemy Column with matching default/server_default"

requirements-completed: [SCONT-01, ESUM-02]

# Metrics
duration: 4min
completed: 2026-06-17
---

# Phase 67 Plan 01: Continuity Data Model & Migration Summary

**Idempotent delta migration 011 adds shows.continuity_mode (VARCHAR default 'anthology'), projects.episode_summary (TEXT nullable) and projects.episode_summary_stale (BOOLEAN default FALSE), mirrored on the Show/Project SQLAlchemy models as String/Text/Boolean (no PG Enum).**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-17T17:56:54Z
- **Completed:** 2026-06-17
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- New idempotent boot-applied delta migration `011_continuity_columns.sql` adding all three continuity columns with `ADD COLUMN IF NOT EXISTS` (re-run safe, additive only, no prior delta touched)
- `Show.continuity_mode` and `Project.episode_summary` / `episode_summary_stale` mirrored on the SQLAlchemy models with String/Text/Boolean types and anthology/null/False defaults, parity-matched to the migration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create idempotent delta migration 011_continuity_columns.sql** - `836cda4` (feat)
2. **Task 2: Mirror the three columns on the SQLAlchemy Show and Project models** - `c10ed6c` (feat)

## Files Created/Modified
- `backend/migrations/delta/011_continuity_columns.sql` - Idempotent ADD COLUMN IF NOT EXISTS for continuity_mode, episode_summary, episode_summary_stale; leading comment documents v10.0 purpose + D-03 VARCHAR-not-PG-enum deviation
- `backend/app/models/database.py` - Added `continuity_mode` to Show model (String(20), default/server_default "anthology") and `episode_summary` (Text nullable) + `episode_summary_stale` (Boolean, server_default "false") to Project model

## Decisions Made
- Kept the D-03 conscious deviation: continuity_mode is VARCHAR/String, not a PG Enum, so future modes are added without ALTER TYPE.
- Set both ORM `default` and `server_default` on continuity_mode and episode_summary_stale to keep DB-level parity with the delta migration.

## Deviations from Plan

None - plan executed exactly as written.

The only adjustment was non-functional: the migration's leading comment originally contained the literal phrase "ADD COLUMN IF NOT EXISTS", which inflated the verify gate's `grep -c` to 4. Reworded the comment to "guard with IF NOT EXISTS" so the gate counts exactly the 3 SQL statements. No behavior change; not a plan deviation.

## Issues Encountered
- Verify gate count mismatch from the comment text (described above) — resolved by rewording the comment. SQLAlchemy import + column/type assertions passed on first run.

## User Setup Required
None - no external service configuration required. Columns apply automatically on next backend boot via the delta migrator.

## Next Phase Readiness
- Schema foundation ready for Phase 68 (mode-aware generation context injection), Phase 69 (auto episode summary + lazy regen), Phase 70 (wizard), Phase 71 (mode-aware review).
- No blockers. Plan 02/03 of this phase (idempotency test, etc.) still pending per phase map.

## Self-Check: PASSED

- FOUND: backend/migrations/delta/011_continuity_columns.sql
- FOUND: backend/app/models/database.py
- FOUND commit: 836cda4 (Task 1)
- FOUND commit: c10ed6c (Task 2)
