---
phase: 17-data-foundation
plan: 01
subsystem: database
tags: [sqlalchemy, pydantic, postgresql, jsonb, docker, migrations, orm]

# Dependency graph
requires:
  - phase: 09-data-foundation
    provides: "BreakdownElement model, element_scene_links, breakdown_runs tables"
provides:
  - "Shot, ShotElement, AssetMedia ORM models with correct FKs and cascades"
  - "Delta migration 002_shotlist_tables.sql (idempotent)"
  - "Consolidated init_db.sql with shotlist tables"
  - "Pydantic schemas: ShotCreate/Update/Response, AssetMediaCreate/Response, ScriptRange"
  - "Project.shotlist_stale column and shots/asset_media relationships"
  - "Docker media_uploads volume for persistent media storage"
affects: [18-shot-crud, 19-media-upload, 20-staleness, 21-shotlist-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: ["JSONB columns for extensible shot fields", "SET NULL FK for scene survival on deletion", "metadata_ alias pattern for AssetMedia (matches existing AIMessage/Book pattern)", "dual nullable FK pattern for media attachable to element or shot"]

key-files:
  created:
    - backend/migrations/delta/002_shotlist_tables.sql
    - backend/app/tests/test_shotlist_models.py
  modified:
    - backend/migrations/init_db.sql
    - backend/app/models/database.py
    - backend/app/models/schemas.py
    - docker-compose.yml

key-decisions:
  - "SQLite SET NULL test uses PRAGMA foreign_keys=ON + raw SQL DELETE to simulate PostgreSQL behavior"
  - "AssetMedia.shot relationship uses cascade='all, delete-orphan' to clean up media when shot is deleted"

patterns-established:
  - "SET NULL FK pattern: Shot.scene_item_id survives scene deletion (ondelete='SET NULL')"
  - "Dual nullable FK pattern: AssetMedia can reference element, shot, or both"
  - "JSONB extensibility: Shot.fields and Shot.script_range store freeform structured data"

requirements-completed: [DATA-01, DATA-02, DATA-03, DATA-06]

# Metrics
duration: 5min
completed: 2026-03-19
---

# Phase 17 Plan 01: Data Foundation Summary

**Shotlist DDL migration, Shot/ShotElement/AssetMedia ORM models with JSONB fields and SET NULL FKs, Pydantic schemas, and Docker media volume**

## Performance

- **Duration:** 5 min 17s
- **Started:** 2026-03-19T15:41:41Z
- **Completed:** 2026-03-19T15:46:58Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Delta migration 002 with 3 idempotent table definitions (shots, shot_elements, asset_media) plus shotlist_stale ALTER
- Shot ORM model with JSONB fields (script_range, fields) and SET NULL FK to list_items
- AssetMedia ORM model with dual nullable FKs (element_id, shot_id) and metadata_ alias
- 18 tests covering ORM round-trips, cascades, constraints, and Pydantic schema validation
- Docker media_uploads volume for persistent media file storage

## Task Commits

Each task was committed atomically:

1. **Task 1: Delta migration, init_db.sql, ORM models, Docker volume** - `914fb21` (feat)
2. **Task 2 RED: Test suite** - `993aec6` (test)
3. **Task 2 GREEN: Pydantic schemas** - `411c76f` (feat)

_Note: Task 2 followed TDD cycle with separate RED and GREEN commits_

## Files Created/Modified
- `backend/migrations/delta/002_shotlist_tables.sql` - Idempotent DDL for shots, shot_elements, asset_media tables + triggers
- `backend/migrations/init_db.sql` - Consolidated baseline schema with shotlist tables appended
- `backend/app/models/database.py` - Shot, ShotElement, AssetMedia ORM models + Project updates
- `backend/app/models/schemas.py` - ShotCreate/Update/Response, ShotElementCreate/Response, AssetMediaCreate/Response, ScriptRange
- `backend/app/tests/test_shotlist_models.py` - 18 tests covering DATA-01 through DATA-06
- `docker-compose.yml` - media_uploads volume added

## Decisions Made
- Used PRAGMA foreign_keys=ON + raw SQL DELETE in SQLite test for SET NULL behavior, since SQLite does not enforce ON DELETE SET NULL by default. The ORM model correctly specifies ondelete="SET NULL" for PostgreSQL.
- AssetMedia.shot relationship uses cascade="all, delete-orphan" to ensure media files are cleaned up when a shot is deleted (matches the SQL ON DELETE SET NULL for the reverse direction from shots).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLite SET NULL test required PRAGMA + raw SQL**
- **Found during:** Task 2 (test_shot_scene_set_null)
- **Issue:** SQLite does not enforce ON DELETE SET NULL by default, causing test to fail with stale scene_item_id
- **Fix:** Added PRAGMA foreign_keys=ON, used raw SQL DELETE instead of ORM delete, expunged shot from session, re-queried to verify NULL
- **Files modified:** backend/app/tests/test_shotlist_models.py
- **Verification:** Test passes, verifies SET NULL behavior correctly
- **Committed in:** 993aec6 (Task 2 test commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test technique adjustment for SQLite compatibility. No scope creep.

## Issues Encountered
- 2 pre-existing test failures in test_session_isolation.py and test_yolo_integration.py confirmed to exist before this plan's changes (verified by running against previous commit). Not related to shotlist work.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 3 tables (shots, shot_elements, asset_media) are defined in both delta and baseline migrations
- ORM models with full relationship graph are ready for CRUD endpoint development
- Pydantic schemas ready for API request/response serialization
- Docker volume configured for media file persistence
- Downstream phases 18-25 can begin building on this data foundation

## Self-Check: PASSED

- All 7 files verified present on disk
- All 3 task commits verified in git log (914fb21, 993aec6, 411c76f)

---
*Phase: 17-data-foundation*
*Completed: 2026-03-19*
