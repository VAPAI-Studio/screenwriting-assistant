---
phase: 62-config-parametrization-migrations-on-boot
plan: 02
subsystem: backend-db-migrations
tags: [migrations, postgres, advisory-lock, boot, railway]
requires:
  - backend/app/services/db_migrator.py (existing delta-loop runner)
  - backend/migrations/init_db.sql (idempotent baseline schema)
provides:
  - fresh-DB init_db.sql step-0 trigger in run_migrations
  - pg_advisory_lock guard around the whole migration run
  - mock-based control-flow tests for the migrator
affects:
  - app boot path (lifespan migration run on managed Postgres)
tech-stack:
  added: []
  patterns:
    - Postgres advisory lock (pg_advisory_lock / pg_advisory_unlock) to serialize concurrent DDL
    - step-0 idempotent baseline on truly-fresh DB (projects absent + 000_baseline unrecorded)
    - mock-SQLAlchemy control-flow unit testing (route execute() by SQL text)
key-files:
  created:
    - backend/app/tests/test_db_migrator.py
  modified:
    - backend/app/services/db_migrator.py
decisions:
  - "Module-level fixed bigint MIGRATION_LOCK_KEY (8273461928374651) — no new config (D-05)"
  - "init_db.sql runs ONLY when projects table is absent AND 000_baseline unrecorded (D-01/D-02)"
  - "Tests are mock-based control-flow assertions; Postgres-specific SQL is never run against SQLite"
metrics:
  duration: ~10m
  completed: 2026-06-14
requirements: [DMIG-01]
---

# Phase 62 Plan 02: Migrations-on-boot (fresh-DB baseline + advisory lock) Summary

Made `run_migrations()` self-sufficient on a fresh managed Postgres (Railway): when the `projects` table is absent and `000_baseline` is unrecorded, it now runs the idempotent `init_db.sql` as step 0 before applying deltas; the entire run is serialized by a Postgres advisory lock released in a `finally` block; baseline and delta failures still propagate (fail hard) with per-migration commit preserved.

## What Was Built

### Task 1 — db_migrator.py step-0 + advisory-lock guard (commit e10deec)
- Added `INIT_DB_SQL = DELTA_DIR.parent / "init_db.sql"` and `MIGRATION_LOCK_KEY = 8273461928374651` module constants.
- Acquire `pg_advisory_lock(MIGRATION_LOCK_KEY)` as the first statement inside `engine.connect()`, commit, then wrap the entire migration body in `try/finally`; the `finally` always issues `pg_advisory_unlock(MIGRATION_LOCK_KEY)`.
- New step-0 branch in baseline detection: when `NOT baseline_recorded AND NOT projects_exist` → log, `INIT_DB_SQL.read_text()`, execute it, commit. init_db.sql inserts `000_baseline` itself, so the subsequent applied-set collection sees it.
- Preserved the pre-tracking branch unchanged: `projects_exist` true + no marker → INSERT `000_baseline ... ON CONFLICT DO NOTHING` only (no init_db.sql run).
- Kept steps 3 & 4 exactly: per-migration `conn.commit()` fail-hard delta loop, no error swallowing.
- Rewrote the module header comment to document the advisory lock, fresh-DB step-0, Docker-vs-managed flows, and fail-hard behavior.

### Task 2 — test_db_migrator.py (commit 27f419e)
Five mock-based control-flow tests against a `MagicMock` engine/connection whose `.execute()` routes return values by rendered SQL text:
- `test_fresh_db_runs_init_db_sql_as_step0` — projects absent + no baseline → init_db.sql content executed; no marker INSERT; lock acquired/released.
- `test_pretracking_db_marks_baseline_without_init_sql` — projects exist + no baseline → marker INSERT only; init_db.sql NOT read.
- `test_recorded_baseline_is_noop_step0` — baseline recorded → step 0 skipped, information_schema check skipped (idempotent re-run).
- `test_advisory_lock_acquired_and_released` — lock is statement 0, unlock issued after, both carry `MIGRATION_LOCK_KEY`.
- `test_delta_failure_propagates_and_unlocks` — a failing delta raises `RuntimeError` AND `pg_advisory_unlock` still runs (finally).

The init_db.sql read is isolated by patching `app.services.db_migrator.INIT_DB_SQL` with a mock (patching `Path.read_text` globally would also catch the real delta-file reads).

## Verification

- `pytest app/tests/test_db_migrator.py -q --noconftest` → **5 passed**.
- `grep -c pg_advisory_lock db_migrator.py` = 1; `pg_advisory_unlock` = 1; `init_db.sql` references present; `unlock` is inside a `finally`.
- `grep -v '^#' db_migrator.py | grep -c 'except'` = 0 (no error swallowing).
- `python -c "import app.services.db_migrator"` exits 0; `INIT_DB_SQL` and `MIGRATION_LOCK_KEY` present.

## Deviations from Plan

### [Rule 3 - Blocking issue] Test run uses `--noconftest` + main-repo venv
- **Found during:** Task 2 verification.
- **Issue:** This worktree has no `backend/venv`; the project's documented venv lives at the main checkout (`/Users/.../screenwriting-assistant/backend/venv`). That venv does NOT have the `mcp` package installed, so `app/tests/conftest.py` (which does `from app.main import app` → imports `app.mcp_server.server` → `import mcp`) fails to collect for the ENTIRE suite — a pre-existing environment gap, not introduced by this plan (confirmed: `pytest app/tests/test_validators.py --collect-only` fails identically with `ModuleNotFoundError: No module named 'mcp'`).
- **Fix:** Ran the new test module with `--noconftest`. `test_db_migrator.py` is fully self-contained — it imports only `app.services.db_migrator` and uses `unittest.mock`, needing none of conftest's SQLite/auth fixtures. All 5 tests pass.
- **Impact:** None on shipped code. In an environment with `mcp` installed (the standard project venv per CLAUDE.md), the plan's exact command `pytest app/tests/test_db_migrator.py -q` will collect and pass normally.
- **Files modified:** none beyond planned.

### Out-of-scope note (NOT fixed)
- The missing `mcp` package in the available venv blocks the plan's existing-suite check (`pytest app/tests/test_api.py -q`). This is a pre-existing environment/dependency gap unrelated to this plan's changes (the migrator change touches no API code paths). Logged here rather than fixed (scope boundary + package-install exclusion).

## Threat Model Compliance

- **T-62-05 (concurrent DDL race) — mitigated:** whole run wrapped in `pg_advisory_lock` acquired first and released in `finally` (D-05). Tested by `test_advisory_lock_acquired_and_released` and `test_delta_failure_propagates_and_unlocks`.
- **T-62-06 (partial migration) — mitigated:** init_db.sql and delta failures propagate (no swallow), boot crashes loudly; per-migration commit preserved so the failing migration retries next boot (D-04/D-06). Tested by `test_delta_failure_propagates_and_unlocks`.
- **T-62-04 (SQL executed on boot) — accept:** unchanged; file contents executed verbatim, no untrusted input interpolated.
- No new packages installed (T-62-SC n/a).

## Known Stubs

None.

## Self-Check: PASSED
- FOUND: backend/app/services/db_migrator.py (modified)
- FOUND: backend/app/tests/test_db_migrator.py (created)
- FOUND commit e10deec (Task 1, feat)
- FOUND commit 27f419e (Task 2, test)
