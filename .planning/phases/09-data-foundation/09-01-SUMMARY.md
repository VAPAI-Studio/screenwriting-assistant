---
phase: 09-data-foundation
plan: 01
subsystem: database
tags: [postgresql, sql-migration, uuid, jsonb, breakdown, cascade, indexes]

# Dependency graph
requires:
  - phase: v1.0
    provides: projects table, list_items table (FKs reference these)
provides:
  - breakdown_elements table with category, soft-delete, unique constraint
  - element_scene_links junction table with dual CASCADE foreign keys
  - breakdown_runs audit table for extraction tracking
  - breakdown_stale column on projects table
affects: [09-02 models-and-schemas, 10-breakdown-api, 11-ai-extraction, 12-staleness-hooks]

# Tech tracking
tech-stack:
  added: []
  patterns: [idempotent DDL with IF NOT EXISTS, partial index for soft-delete filtering, JSONB for extensible metadata, VARCHAR over PG ENUM for extensibility]

key-files:
  created:
    - backend/migrations/009_breakdown_tables.sql
  modified: []

key-decisions:
  - "VARCHAR(50) for category column instead of PG ENUM -- allows adding categories without migration"
  - "Full UNIQUE constraint on (project_id, category, name) rather than partial index excluding soft-deleted -- simpler, API handles restore of soft-deleted duplicates"
  - "JSONB for metadata and config columns -- supports GIN indexing if needed later"

patterns-established:
  - "Breakdown tables follow 008 migration pattern: header comment, CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS"
  - "Dual CASCADE on junction table: element_scene_links cascades on both breakdown_elements and list_items deletion"

requirements-completed: [BKDN-01, BKDN-02, BKDN-03, BKDN-04]

# Metrics
duration: 1min
completed: 2026-03-13
---

# Phase 9 Plan 01: Breakdown Tables SQL Migration Summary

**Idempotent PostgreSQL migration creating 3 breakdown tables (elements, scene links, runs) with cascading FKs, partial indexes, and staleness column on projects**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-13T12:26:12Z
- **Completed:** 2026-03-13T12:27:34Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `breakdown_elements` table with UUID PK, project FK cascade, VARCHAR(50) category, JSONB metadata, soft-delete via `is_deleted`, user-modification tracking via `user_modified`, and UNIQUE constraint on (project_id, category, name)
- Created `element_scene_links` junction table with ON DELETE CASCADE on both `breakdown_elements` and `list_items` foreign keys, plus UNIQUE constraint on (element_id, scene_item_id)
- Created `breakdown_runs` audit table tracking extraction status, element counts, config, result summary, and timestamps
- Added `breakdown_stale BOOLEAN DEFAULT FALSE` column to projects table
- All statements use `IF NOT EXISTS` for safe idempotent re-runs

## Task Commits

Each task was committed atomically:

1. **Task 1: Write 009_breakdown_tables.sql migration** - `ef7b8e6` (feat)

## Files Created/Modified
- `backend/migrations/009_breakdown_tables.sql` - DDL for 3 new tables (breakdown_elements, element_scene_links, breakdown_runs) plus ALTER TABLE projects for breakdown_stale column

## Decisions Made
- Used VARCHAR(50) for category column instead of PostgreSQL ENUM type, following the architecture spec for extensibility without migrations
- Applied full UNIQUE constraint rather than partial index excluding soft-deleted rows; API layer will handle check-and-restore for soft-deleted duplicates
- Used JSONB (not JSON) for metadata, config, and result_summary columns to support future GIN indexing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Migration file ready to be applied via `psql -f backend/migrations/009_breakdown_tables.sql`
- Plan 09-02 (SQLAlchemy models, Pydantic schemas, relationship wiring) can proceed immediately -- it depends on this migration for table definitions
- All table names, column names, and constraint names match the architecture spec exactly

## Self-Check: PASSED

- FOUND: backend/migrations/009_breakdown_tables.sql
- FOUND: .planning/phases/09-data-foundation/09-01-SUMMARY.md
- FOUND: commit ef7b8e6

---
*Phase: 09-data-foundation*
*Completed: 2026-03-13*
