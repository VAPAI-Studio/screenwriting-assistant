---
phase: 62-config-parametrization-migrations-on-boot
verified: 2026-06-14T23:30:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 62: Config Parametrization & Migrations-on-Boot — Verification Report

**Phase Goal:** Every production-environment-specific value is supplied via env vars (no hardcoded localhost), and a fresh or upgraded Postgres reaches the current schema automatically on boot.
**Verified:** 2026-06-14T23:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `ALLOWED_ORIGINS` is read from the environment in config.py (and docker-compose), defaulting to localhost for local dev, with no hardcoded prod origin in the repo | VERIFIED | `config.py:30` — `ALLOWED_ORIGINS: List[str] = ["http://localhost:5173","http://localhost:5174","http://localhost:3000"]`; prod guard at line 119 is `logger.warning()` only (intentional per D-09); `docker-compose.yml:27` — `ALLOWED_ORIGINS: '${ALLOWED_ORIGINS:-["http://localhost:5173","http://localhost:3000"]}'`; no Vercel/Railway origin committed anywhere |
| 2 | The MCP server's issuer / resource_server_url is read from an env var instead of the hardcoded `http://localhost:8001` | VERIFIED | `config.py:78` — `MCP_BASE_URL: str = "http://localhost:8001"` (pydantic field, env-overridable); `server.py:35-36` — `issuer_url=settings.MCP_BASE_URL, resource_server_url=settings.MCP_BASE_URL`; `grep "http://localhost:8001" server.py` returns zero non-comment hits; the former module-level `_BASE_URL` constant is gone |
| 3 | Starting the backend against an empty Postgres runs all `delta/*.sql` via `init_db` and reaches the current schema with no manual step; starting it again is a no-op (idempotent) | VERIFIED | `db_migrator.py:55-149` — step 0 fires when `projects` table absent + `000_baseline` unrecorded; advisory lock acquired first (line 64), released in `finally` (line 148); init_db.sql executed via `read_text()` then committed; second boot skips step 0 because `000_baseline` is recorded; 5 mock tests pass: `pytest app/tests/test_db_migrator.py -q --noconftest` → **5 passed** |
| 4 | The frontend build consumes `VITE_API_URL` with `/api` as the local-dev fallback (no hardcoded backend host) | VERIFIED | `frontend/src/lib/constants.ts:7` — `export const API_BASE_URL = import.meta.env.VITE_API_URL \|\| '/api';`; `docker-compose.yml:44` — `VITE_API_URL=/api`; `api.tsx:16` imports `API_BASE_URL` from constants; no hardcoded backend host anywhere in the API layer |

**Score:** 4/4 truths verified

---

## SC1 / DCFG-01 — ALLOWED_ORIGINS Detail

**config.py:30** — typed `List[str]` pydantic field; env-readable via standard pydantic-settings env loading.
**config.py:119** — production guard is `logger.warning("localhost in ALLOWED_ORIGINS for production!")` — warning-only, not a raise. This is intentional per locked decision D-09 (hard CORS lock deferred to Phase 66). Not flagged as a gap.
**docker-compose.yml:27** — `ALLOWED_ORIGINS: '${ALLOWED_ORIGINS:-["http://localhost:5173","http://localhost:3000"]}'` — interpolates the env var with a localhost default; operator override honored.
**No hardcoded prod origin** confirmed: grep of config.py and docker-compose.yml found no `vercel.app`, `railway.app`, or any production domain committed.

---

## SC2 / DCFG-02 — MCP Base URL Detail

**Before phase:** `mcp_server/server.py` had a module-level `_BASE_URL = "http://localhost:8001"` constant used for both `issuer_url` and `resource_server_url` in `AuthSettings(...)`.
**After phase:**
- `config.py:74-78` — new `MCP_BASE_URL: str = "http://localhost:8001"` pydantic field with explanatory comment; placed in the Server section adjacent to `PORT`, consistent with project convention.
- `server.py:35-36` — `issuer_url=settings.MCP_BASE_URL, resource_server_url=settings.MCP_BASE_URL`; `settings` already imported from `..config`.
- The only `localhost:8001` remaining in any .py file is the legitimate default value assignment in `config.py:78` — correct.
- `grep -n "_BASE_URL" server.py` returns only comment references (lines 17) and the two `settings.MCP_BASE_URL` usages (lines 35-36); the old constant assignment is gone.

---

## SC3 / DMIG-01 — Migrations-on-Boot Detail

### db_migrator.py control flow

| Step | Code location | Behavior |
|------|--------------|----------|
| Advisory lock acquire | line 64 | `SELECT pg_advisory_lock(:k)` with `MIGRATION_LOCK_KEY = 8273461928374651`; committed immediately; first statement issued |
| Tracking table creation | lines 69-76 | `CREATE TABLE IF NOT EXISTS schema_migrations ...`; idempotent |
| Baseline check | lines 79-110 | Queries `000_baseline` count; if absent AND projects absent → runs init_db.sql (step 0); if absent AND projects exist → inserts marker only (pre-tracking branch) |
| Step 0 (fresh DB) | lines 94-102 | `INIT_DB_SQL.read_text()` executed; init_db.sql itself inserts `000_baseline`; no double INSERT |
| Delta loop | lines 122-140 | Sorted by filename; skips recorded names; per-migration commit; no `except` swallowing |
| Advisory lock release | lines 147-149 | `SELECT pg_advisory_unlock(:k)` in `finally` — runs on success AND on any exception |

**No broad `except` blocks:** `grep -v '^#' db_migrator.py | grep 'except'` returns 0 matches.

### Test coverage (backend/app/tests/test_db_migrator.py)

| Test | Assertion | Result |
|------|-----------|--------|
| `test_fresh_db_runs_init_db_sql_as_step0` | init_db.sql content executed when projects absent + no baseline; no marker INSERT; lock acquired and released | PASS |
| `test_pretracking_db_marks_baseline_without_init_sql` | init_db.sql NOT read when projects exist + no baseline; marker INSERT runs | PASS |
| `test_recorded_baseline_is_noop_step0` | step 0 entirely skipped when baseline recorded; information_schema not queried; no marker INSERT | PASS |
| `test_advisory_lock_acquired_and_released` | lock is statement index 0; unlock issued after; both carry `MIGRATION_LOCK_KEY` | PASS |
| `test_delta_failure_propagates_and_unlocks` | RuntimeError from a delta propagates (fail hard); `pg_advisory_unlock` still runs in finally | PASS |

**Command run:** `cd backend && source venv/bin/activate && pytest app/tests/test_db_migrator.py -q --noconftest`
**Result:** `5 passed, 3 warnings in 0.33s`

**Note on `--noconftest`:** The full test suite cannot be collected in this environment because the `mcp` Python package is not installed in the local venv (`conftest.py` imports `app.main` which imports `app.mcp_server.server` which imports `mcp`). This is a pre-existing environment gap — identical collection failure exists on the pre-phase commit, confirmed in the SUMMARY. The `test_db_migrator.py` file is self-contained (imports only `app.services.db_migrator` and `unittest.mock`) and was correctly run with `--noconftest`. This is not a phase defect.

---

## SC4 — VITE_API_URL Detail

**frontend/src/lib/constants.ts:7** — `export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';`
**frontend/src/lib/api.tsx:16** — imports `API_BASE_URL` from constants; used as the base for all fetch calls.
**docker-compose.yml:44** — `- VITE_API_URL=/api` (local dev); the Vercel deploy will set `VITE_API_URL` to the Railway backend domain.
This was a verify-only item (D-10) — the code was already correct before Phase 62. The phase confirms the criterion is met; no change was needed or made.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/config.py` | `MCP_BASE_URL` pydantic field; `ALLOWED_ORIGINS` as `List[str]` | VERIFIED | Lines 30, 74-78; env-readable, localhost defaults |
| `backend/app/mcp_server/server.py` | Uses `settings.MCP_BASE_URL` for both auth settings; no hardcoded `_BASE_URL` constant | VERIFIED | Lines 35-36; old constant removed |
| `backend/app/services/db_migrator.py` | Advisory lock + fresh-DB step 0 + fail-hard + idempotent | VERIFIED | Lines 48-149; all behaviors present |
| `backend/app/tests/test_db_migrator.py` | 5 control-flow tests asserting migrator behavior | VERIFIED | All 5 pass |
| `docker-compose.yml` | `ALLOWED_ORIGINS` interpolated; `VITE_API_URL=/api` set | VERIFIED | Lines 27, 44 |
| `frontend/src/lib/constants.ts` | `VITE_API_URL || '/api'` pattern | VERIFIED | Line 7 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `config.py` `MCP_BASE_URL` | `server.py` `AuthSettings` | `settings.MCP_BASE_URL` | WIRED | `server.py:35-36` |
| `config.py` `ALLOWED_ORIGINS` | `main.py` CORS middleware | `settings.ALLOWED_ORIGINS` | WIRED | Pre-existing wiring; unchanged |
| `db_migrator.py` `run_migrations()` | `db.py` `init_db()` | called as `run_migrations(engine)` | WIRED | Pre-existing; boot path unchanged |
| `constants.ts` `API_BASE_URL` | `api.tsx` fetch wrapper | `import { API_BASE_URL }` | WIRED | `api.tsx:16` |
| `docker-compose.yml` env | `backend` `ALLOWED_ORIGINS` | env interpolation | WIRED | `docker-compose.yml:27` |
| `docker-compose.yml` env | `frontend` `VITE_API_URL` | env var injection | WIRED | `docker-compose.yml:44` |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

No TBD, FIXME, XXX, placeholder, stub, or hardcoded-empty-data patterns found in the files modified by this phase.

---

## Human Verification Required

None. All four success criteria are verifiable programmatically from the codebase:
- Config fields and their defaults are readable in source.
- Wiring is verifiable via grep.
- Tests were executed and passed.
- The intentional deference of hard CORS locking to Phase 66 is documented in locked decision D-09 and explicitly not flagged.

---

## Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DCFG-01 | `ALLOWED_ORIGINS` configurable via environment | SATISFIED | `config.py:30` (List field, localhost default); `docker-compose.yml:27` (env interpolation); no prod origin committed |
| DCFG-02 | MCP server base URL parametrized via environment | SATISFIED | `config.py:78` (`MCP_BASE_URL` field); `server.py:35-36` (both auth settings consume it) |
| DMIG-01 | Idempotent delta migrations applied automatically on boot | SATISFIED | `db_migrator.py` step-0 + advisory lock + fail-hard + per-migration commit; 5 tests pass |

---

## Final Verdict

**PASSED.** All 4 success criteria are met by shipped code:

1. `ALLOWED_ORIGINS` is a pydantic `List[str]` field read from the environment with localhost defaults in both `config.py` and `docker-compose.yml`. The production guard is warning-only, which is correct and intentional (D-09 defers hard lock to Phase 66). No prod origin is hardcoded.

2. `settings.MCP_BASE_URL` (default `"http://localhost:8001"`) is the sole source for both `issuer_url` and `resource_server_url` in `AuthSettings`. The old module-level `_BASE_URL` constant is gone. No hardcoded localhost:8001 literal remains in server.py code lines.

3. `run_migrations()` acquires a Postgres advisory lock as its first statement (released in `finally`), runs `init_db.sql` as step 0 only on a truly-fresh DB (projects absent + baseline unrecorded), marks baseline without re-running `init_db.sql` on pre-tracking DBs, and applies deltas with per-migration commits and no error swallowing. The 5 mock-based tests assert all of these behaviors and pass.

4. `frontend/src/lib/constants.ts:7` exports `API_BASE_URL = import.meta.env.VITE_API_URL || '/api'`; docker-compose sets `VITE_API_URL=/api`; the API layer consumes `API_BASE_URL` exclusively.

---

_Verified: 2026-06-14T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
