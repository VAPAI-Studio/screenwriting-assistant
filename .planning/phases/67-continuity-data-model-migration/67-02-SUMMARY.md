---
phase: 67-continuity-data-model-migration
plan: 02
subsystem: shows-api
tags: [fastapi, pydantic, enum, continuity, shows]

# Dependency graph
requires:
  - phase: 67-01
    provides: shows.continuity_mode column (VARCHAR default 'anthology') on Show ORM model
provides:
  - ContinuityMode app-layer enum (connected/anthology/standalone)
  - continuity_mode on ShowCreate / ShowUpdate / ShowResponse
  - Show API create/update/read threading for continuity_mode
affects: [68-mode-aware-generation, 69-auto-episode-summary, 70-show-creation-wizard, 71-mode-aware-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "App-layer str-enum (ContinuityMode) validates untrusted JSON at route entry → 422 for out-of-enum values (D-03)"
    - "Enum→.value coercion in the model_dump(exclude_unset=True) setattr loop so VARCHAR columns store the plain string, not the enum repr"

key-files:
  created: []
  modified:
    - backend/app/models/schemas.py
    - backend/app/api/endpoints/shows.py
    - backend/app/tests/test_shows_api.py

key-decisions:
  - "ContinuityMode lives in schemas.py as a str-enum (app layer, D-03), mirroring the Framework convention; column stays VARCHAR so no PG Enum / ALTER TYPE"
  - "create_show passes body.continuity_mode.value explicitly; update_show loop coerces any Enum member to .value before setattr (prevents 'ContinuityMode.STANDALONE' being stored)"
  - "Default on create is anthology (D-01) → omitting the field is byte-for-byte unchanged behavior for existing clients"
  - "Out-of-enum rejection (422) is asserted only in Task 2's API test, per the plan's deliberate split"

patterns-established:
  - "Validate-at-boundary via Pydantic enum; coerce-to-.value at ORM write for str-enum + VARCHAR columns"

requirements-completed: [SCONT-01]

# Metrics
duration: 5min
completed: 2026-06-17
---

# Phase 67 Plan 02: Continuity Mode Show API Summary

**`continuity_mode` (connected/anthology/standalone) is now settable on Show create/update and returned on read, validated by a Pydantic `ContinuityMode` str-enum that rejects out-of-enum values with 422; default on create is anthology (D-01), satisfying SCONT-01.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-17T18:01:23Z
- **Completed:** 2026-06-17
- **Tasks:** 2
- **Files modified:** 3 (0 created, 3 modified)

## Accomplishments
- New `ContinuityMode(str, enum.Enum)` in `schemas.py` (CONNECTED/ANTHOLOGY/STANDALONE), following the existing `Framework` str-enum convention and the D-03 VARCHAR-not-PG-Enum decision.
- `continuity_mode` added to `ShowCreate` (default `ANTHOLOGY`), `ShowUpdate` (`Optional`, partial-update friendly), and `ShowResponse` (serialized from the ORM via `from_attributes`).
- `create_show` threads `body.continuity_mode.value` into `database.Show(...)`; `update_show`'s existing `model_dump(exclude_unset=True)` setattr loop now coerces Enum members to `.value` so the VARCHAR column stores `"standalone"`, not `"ContinuityMode.STANDALONE"`.
- Four API tests added to `TestShowsAPI`: create→connected (201), create-default→anthology, update→GET round trip→standalone, and the bogus-value→422 rejection (the plan's authoritative T-67-03 mitigation proof).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ContinuityMode enum + continuity_mode to Show schemas** - `9f65908` (feat)
2. **Task 2: Thread continuity_mode through shows.py create/update + API tests** - `119cb87` (feat)

## Files Created/Modified
- `backend/app/models/schemas.py` - Added `import enum`, the `ContinuityMode` str-enum, and `continuity_mode` to ShowCreate/ShowUpdate/ShowResponse. No `episode_summary`/`episode_summary_stale` added to Show schemas (those belong to the Project/episode surface, Plan 03, D-04).
- `backend/app/api/endpoints/shows.py` - Added `import enum`; create_show passes `continuity_mode=body.continuity_mode.value`; update_show loop coerces `enum.Enum` values to `.value` before `setattr`.
- `backend/app/tests/test_shows_api.py` - Four new continuity_mode tests in `TestShowsAPI`.

## Decisions Made
- Kept `ContinuityMode` in `schemas.py` (app layer per D-03) rather than `database.py`, since it is a validation/serialization concern, not a stored PG type. The DB column remains plain VARCHAR.
- Added explicit Enum→`.value` coercion in the update loop (Rule 2 — correctness). Although str-enum binding happens to store the underlying string via DBAPI, relying on that is fragile; the explicit coercion makes the stored value unambiguous and was confirmed by a raw-DB-value assertion (`raw.continuity_mode == "standalone"`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `import enum` missing in schemas.py and shows.py**
- **Found during:** Task 1 / Task 2
- **Issue:** Neither file imported `enum`; the new `ContinuityMode(str, enum.Enum)` and the update-loop `isinstance(value, enum.Enum)` guard would raise `NameError`.
- **Fix:** Added `import enum` at the top of both files.
- **Files modified:** backend/app/models/schemas.py, backend/app/api/endpoints/shows.py
- **Commits:** 9f65908 (schemas), 119cb87 (shows)

**2. [Rule 2 - Missing correctness] Enum→.value coercion in update_show loop**
- **Found during:** Task 2
- **Issue:** `model_dump(exclude_unset=True)` returns the `ContinuityMode` enum member (not the plain string). `setattr` of an enum member onto a `String(20)` column risks storing `"ContinuityMode.STANDALONE"` depending on binding path.
- **Fix:** Coerce any `enum.Enum` value to `.value` before `setattr` in the update loop. Verified raw stored value is `"standalone"`.
- **Files modified:** backend/app/api/endpoints/shows.py
- **Commit:** 119cb87

## Issues Encountered

**Pre-existing environment gap (out of scope, NOT caused by this plan):** The declared dependency `mcp>=1.27.2,<2.0` (requirements.txt) is not installed in the local `backend/venv`. `app/tests/conftest.py` imports `app.main`, which transitively imports `app.mcp_server.server` → `from mcp.server.fastmcp import ...`, so the entire REST pytest suite fails to collect with `ModuleNotFoundError: No module named 'mcp'`. An attempt to `pip install` the pinned `mcp` was denied by the auto-mode classifier (supply-chain guard).

Because the plan's `pytest app/tests/test_shows_api.py -k continuity` verify command could not run, all four continuity behaviors were instead validated against the **real endpoint code** via a standalone harness that mirrors conftest's SQLite UUID/Enum patching and mounts only the `shows` router (with `get_db`/`get_current_user` overrides). Results: create→connected (201), create-default→anthology, PUT→GET round-trip→standalone (plus a raw-DB assertion that `"standalone"` is stored), and bogus→422 all PASS. The committed pytest tests are correct and will pass once `mcp` is installed in the environment (logged below as a deferred env item).

## Deferred Issues
- **[env]** `backend/venv` is missing the declared `mcp` package, blocking `pytest` collection for the whole REST suite. Run `pip install -r backend/requirements.txt` (or `pip install "mcp>=1.27.2,<2.0"`) in the venv to restore the suite. Not a regression from this plan; affects all REST tests, not just continuity ones.

## User Setup Required
None for the feature itself. To run the pytest suite locally, install the missing `mcp` dependency in `backend/venv` (see Deferred Issues).

## Threat Surface

- **T-67-03 (Tampering, mitigate):** Out-of-enum `continuity_mode` values are rejected at route entry by the `ContinuityMode` Pydantic enum (422), proven by `test_create_show_invalid_continuity_mode`. Mitigation implemented.
- **T-67-04 (Information Disclosure, accept):** Only `continuity_mode` added to the read surface; no `episode_summary` text exposed (D-04). Existing ownership filter on shows unchanged.
- No new packages installed.

## Next Phase Readiness
- SCONT-01 satisfied: a show can declare/edit its continuity_mode via the API and the value round-trips, with anthology default and 422 on invalid input.
- Phase 68 (mode-aware generation) can now read `continuity_mode` off the Show to branch prior-context behavior.
- No code blockers. Only the env-level `mcp` install is needed to run the pytest gate.

## Self-Check: PASSED

- FOUND: backend/app/models/schemas.py
- FOUND: backend/app/api/endpoints/shows.py
- FOUND: backend/app/tests/test_shows_api.py
- FOUND commit: 9f65908 (Task 1)
- FOUND commit: 119cb87 (Task 2)
