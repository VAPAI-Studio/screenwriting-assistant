---
phase: 16-staleness-bug-and-migration-upgrade-path
verified: 2026-03-18T20:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 16: Staleness Bug and Migration Upgrade Path — Verification Report

**Phase Goal:** Fix scene_wizard staleness bug and provide migration delta for Docker auto-upgrade
**Verified:** 2026-03-18T20:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Running scene_wizard via apply_wizard_result_to_db sets project.breakdown_stale=True when a breakdown element exists | VERIFIED | `_mark_breakdown_stale(db, project.id)` at wizards.py line 317; 11/11 staleness tests pass including test_scene_wizard_sets_stale |
| 2 | backend/migrations/delta/001_breakdown_tables.sql exists and contains idempotent CREATE TABLE IF NOT EXISTS statements | VERIFIED | File exists; `diff` against 009_breakdown_tables.sql is identical; line 9 confirmed `CREATE TABLE IF NOT EXISTS breakdown_elements` |
| 3 | SYNC-03 is checked [x] in REQUIREMENTS.md | VERIFIED | REQUIREMENTS.md line 57: `- [x] **SYNC-03**:` and traceability line 125: `Phase 12, Phase 16 \| Complete` |
| 4 | pytest app/tests/test_staleness.py passes green with test_scene_wizard_sets_stale included | VERIFIED | `11 passed, 21 warnings in 0.18s` — all tests green |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/migrations/delta/001_breakdown_tables.sql` | Idempotent breakdown schema delta for existing Docker deployments | VERIFIED | File exists; verbatim copy of 009_breakdown_tables.sql; fully idempotent throughout (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS, ALTER TABLE ADD COLUMN IF NOT EXISTS) |
| `backend/app/tests/test_staleness.py` | scene_wizard staleness test covering SYNC-03 | VERIFIED | `test_scene_wizard_sets_stale` found at line 184; 47 lines added in commit 5cf0248; substantive test with project + BreakdownElement setup + assertion |
| `backend/app/api/endpoints/wizards.py` | scene_wizard branch calls _mark_breakdown_stale before db.commit() | VERIFIED | Line 317: `_mark_breakdown_stale(db, project.id)`; placed after ListItem creation loop, before `db.commit()` at line 318; mirrors script_writer_wizard pattern at line 274 |
| `.planning/REQUIREMENTS.md` | SYNC-03 checkbox and traceability updated | VERIFIED | Line 57 shows `[x]`; line 125 shows `Phase 12, Phase 16 \| Complete` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/api/endpoints/wizards.py` | `backend/app/api/endpoints/phase_data.py:_mark_breakdown_stale` | direct function call before db.commit() in scene_wizard branch | WIRED | Import at line 14: `from .phase_data import _mark_breakdown_stale`; call at line 317 inside scene_wizard branch after ListItem loop, before line 318 `db.commit()`; `_mark_breakdown_stale` defined at phase_data.py line 20 |
| `backend/migrations/delta/001_breakdown_tables.sql` | `backend/migrations/009_breakdown_tables.sql` | identical copy — no modifications | WIRED | `diff` output: FILES_IDENTICAL; both contain `CREATE TABLE IF NOT EXISTS breakdown_elements` at line 9 |
| `backend/app/services/db_migrator.py` | `backend/migrations/delta/001_breakdown_tables.sql` | DELTA_DIR scan matching `^\d+_` pattern on startup | WIRED | db_migrator.py line 31: `DELTA_DIR = Path(__file__).parent.parent.parent / "migrations" / "delta"`; line 79: `re.match(r"^\d+_", f.name)`; 001_breakdown_tables.sql matches pattern and will be applied on next app startup to pre-v2.0 deployments |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SYNC-03 | 16-01-PLAN.md | Staleness detection — saving screenplay content or regenerating scenes sets `breakdown_stale=true` on the project | SATISFIED | scene_wizard branch now calls `_mark_breakdown_stale` before `db.commit()`; test_scene_wizard_sets_stale confirms behavior; REQUIREMENTS.md updated to `[x]` with Complete status |

No orphaned requirements: SYNC-03 is the only requirement declared for Phase 16 and it is fully accounted for.

---

### Anti-Patterns Found

No blocking anti-patterns detected in modified files.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/tests/test_staleness.py` | (pre-existing) | `test_session_isolation.py::test_orchestrate_uses_session_factory` failing due to MagicMock template lookup | Info | Pre-existing failure unrelated to Phase 16; logged in deferred-items.md; all 11 staleness tests pass; does not affect SYNC-03 coverage |

---

### Human Verification Required

#### 1. Docker auto-upgrade on existing deployment

**Test:** On a pre-v2.0 Docker deployment (volume without breakdown tables), restart the container after pulling the Phase 16 changes.
**Expected:** `db_migrator` log shows `"db_migrator: applying 001_breakdown_tables"` and breakdown tables are created successfully without requiring a volume wipe.
**Why human:** Requires a live pre-v2.0 Docker volume. Cannot be verified programmatically without provisioning a separate database instance missing the breakdown schema.

#### 2. StalenessBar appears after scene generation in the UI

**Test:** In a running app, open a project with a completed breakdown extraction. Navigate to the Scenes wizard and generate scenes. Return to the Breakdown page.
**Expected:** The staleness banner ("Breakdown is outdated") should appear, indicating breakdown_stale was set to True.
**Why human:** Requires running frontend + backend stack with a real project; UI rendering cannot be verified programmatically.

---

### Gaps Summary

No gaps. All four must-haves verified against actual codebase:

1. The scene_wizard staleness bug is fixed: `_mark_breakdown_stale(db, project.id)` appears at wizards.py line 317, immediately before `db.commit()` at line 318, after the ListItem creation loop. This mirrors the script_writer_wizard pattern at line 274.

2. The migration delta exists and is wired: `backend/migrations/delta/001_breakdown_tables.sql` is a verbatim copy of `009_breakdown_tables.sql` (confirmed by `diff`), and `db_migrator.py` will pick it up automatically on next startup via the `^\d+_` filename pattern scan of `DELTA_DIR`.

3. SYNC-03 is marked complete in REQUIREMENTS.md with the correct traceability entry (`Phase 12, Phase 16 | Complete`).

4. The TDD cycle was properly executed: commit `5cf0248` (RED test), then `270ecaf` (fix + delta), then `09676ea` (REQUIREMENTS.md). All 11 staleness tests pass green.

Two items remain for human verification: live Docker auto-upgrade test and UI staleness banner validation.

---

_Verified: 2026-03-18T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
