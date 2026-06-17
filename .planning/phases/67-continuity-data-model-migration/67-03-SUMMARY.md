---
phase: 67-continuity-data-model-migration
plan: 03
subsystem: episodes-phase-data
tags: [fastapi, sqlalchemy, pydantic, staleness, continuity, episode-summary]

# Dependency graph
requires:
  - phase: 67-01
    provides: projects.episode_summary (TEXT) + episode_summary_stale (BOOLEAN) columns on Project ORM model
  - phase: 67-02
    provides: ContinuityMode enum + Show continuity_mode schema edits (not clobbered)
provides:
  - _mark_episode_summary_stale helper (existence-gated, no-commit) in phase_data.py
  - episode_summary_stale read-only flag on the Project read schema
  - test_episode_summary_staleness.py (existence/phase/standalone/idempotency/read-surface)
affects: [69-auto-episode-summary]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Existence-gated stale helper mirroring breakdown_stale/shotlist_stale: flip True only when the dependent artifact (here the same-row episode_summary text) already exists; never db.commit inside the helper (caller commits)"
    - "Read-only ORM-backed boolean surfaced via from_attributes while the underlying TEXT stays internal (D-04 info-disclosure control)"

key-files:
  created:
    - backend/app/tests/test_episode_summary_staleness.py
  modified:
    - backend/app/api/endpoints/phase_data.py
    - backend/app/models/schemas.py

key-decisions:
  - "Helper keys purely on episode_summary existence (truthy after strip), NOT on show linkage — standalone (show_id NULL) projects follow the same gate (D-02)"
  - "Reused the existing {write,scenes} BREAKDOWN_SENSITIVE_PHASES set; no new sensitive-phase constant (D-02a)"
  - "Surfaced episode_summary_stale read-only on Project; episode_summary text intentionally NOT added to any schema (D-04)"
  - "Idempotency asserted by static inspection of 011_continuity_columns.sql; 67-01/Task 1 grep gate is the runtime proof of record (SQLite fixture cannot run PG ADD COLUMN IF NOT EXISTS)"

patterns-established:
  - "Per-row existence-gated staleness helper invoked at the shared write/scenes PATCH edit site, sharing the caller's single db.commit()"

requirements-completed: [ESUM-02]

# Metrics
duration: 3min
completed: 2026-06-17
---

# Phase 67 Plan 03: Episode-Summary Staleness Hook Summary

**Editing an episode's screenplay/content (write/scenes PATCH) now marks an existing per-episode summary stale via the existence-gated `_mark_episode_summary_stale` helper (mirroring breakdown_stale/shotlist_stale), and the read-only `episode_summary_stale` flag is surfaced on the Project schema while the summary text stays internal — delivering ESUM-02.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-06-17T18:08:17Z
- **Completed:** 2026-06-17
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Added `_mark_episode_summary_stale(db, project_id)` immediately after `_mark_shotlist_stale` in `phase_data.py`: loads the Project, and sets `episode_summary_stale=True` only when `project.episode_summary` is non-empty (truthy after `.strip()`). No `db.commit()` inside the helper — the caller's existing commit persists it.
- Wired the helper at the existing stale-mark site inside the `if phase in BREAKDOWN_SENSITIVE_PHASES:` block (reusing `{write, scenes}`), right after the breakdown/shotlist marks and before `db.commit()`.
- Surfaced `episode_summary_stale: bool = False` (read-only) on the Project read schema in `schemas.py`, leaving the 67-02 `ContinuityMode` enum and Show schema edits untouched. `episode_summary` text is deliberately NOT exposed (D-04).
- Created `test_episode_summary_staleness.py` (6 tests): write-with-summary→True, write-without-summary→False (incl. whitespace-only), story-phase→False, standalone existence-gating (summary→True, no-summary→False), static migration-idempotency inspection, and a read-surface test proving the flag is dumped while the text is absent.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _mark_episode_summary_stale helper and call it at the existing stale-mark site** - `3f079db` (feat)
2. **Task 2: Surface episode_summary_stale on the Project schema and add the staleness test module** - `4b2b33f` (feat)

## Files Created/Modified
- `backend/app/api/endpoints/phase_data.py` - Added the existence-gated `_mark_episode_summary_stale` helper after `_mark_shotlist_stale`; invoked it inside the `BREAKDOWN_SENSITIVE_PHASES` block before the existing `db.commit()`.
- `backend/app/models/schemas.py` - Added `episode_summary_stale: bool = False` to the `Project` read schema (read-only, D-04). No `episode_summary` text added. ContinuityMode/Show edits from 67-02 preserved.
- `backend/app/tests/test_episode_summary_staleness.py` - New dedicated test module mirroring `test_staleness.py` fixtures/helpers (SQLite-backed `db_session`, `client`, `mock_auth_headers`).

## Decisions Made
- Existence gate keys on the Project's OWN `episode_summary` (D-02), so the hook is independent of `show_id` — standalone projects with a summary still flip True, and standalone projects without one stay False (proven by test 4).
- Reused the `{write, scenes}` `BREAKDOWN_SENSITIVE_PHASES` set rather than introducing a new constant (D-02a).
- Whitespace-only summaries are treated as absent (`.strip()` gate), so a placeholder of spaces does not trigger staleness.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 6 passed the class instead of an instance to model_validate**
- **Found during:** Task 2
- **Issue:** `schemas.Project.model_validate(_FakeProject)` was passed the class object, raising `model_attributes_type` ValidationError (Pydantic needs an instance to extract attributes).
- **Fix:** Changed to `model_validate(_FakeProject())` (instantiate the fake ORM object).
- **Files modified:** backend/app/tests/test_episode_summary_staleness.py
- **Commit:** 4b2b33f

## Issues Encountered
- The `mcp` package is now installed in `backend/venv` (per the execution ENVIRONMENT NOTE), so the full REST pytest suite collects cleanly — unlike the 67-02 env gap. All verification ran via `PYTHONPATH=. ./venv/bin/python -m pytest`.

## Threat Surface
- **T-67-05 (Tampering, mitigate):** The stale flag flips only via the existing auth-gated write/scenes PATCH path and only when a summary already exists. No new endpoint or write surface. Mitigation implemented.
- **T-67-06 (Information Disclosure, mitigate):** Only the boolean `episode_summary_stale` was added to the read schema; `episode_summary` text is explicitly NOT added (D-04). Asserted by test 6 (dumped surface includes the flag, excludes the text).
- **T-67-01 (DoS, mitigate):** Migration idempotency corroborated structurally by test 5's static `IF NOT EXISTS` inspection of `011_continuity_columns.sql`; 67-01/Task 1's grep gate remains the runtime proof of record.
- No new packages installed.

## Next Phase Readiness
- ESUM-02 satisfied: an episode whose summary exists is marked stale when its screenplay/content is edited, gated on summary existence and the write/scenes phase set — mirroring breakdown_stale/shotlist_stale.
- Phase 69 (auto episode summary + lazy regen) can read `episode_summary_stale` to decide when to regenerate; the read-only flag is exposed without leaking the summary text.
- No blockers.

## Verification
- `pytest app/tests/test_episode_summary_staleness.py` → 6 passed.
- `pytest app/tests/test_staleness.py app/tests/test_shows_api.py` → 56 passed (no regression).
- Task 1 inspect gate (`_mark_episode_summary_stale` defined after `_mark_shotlist_stale`, called at site, sets flag True) → OK.

## Self-Check: PASSED

- FOUND: backend/app/api/endpoints/phase_data.py
- FOUND: backend/app/models/schemas.py
- FOUND: backend/app/tests/test_episode_summary_staleness.py
- FOUND commit: 3f079db (Task 1)
- FOUND commit: 4b2b33f (Task 2)
