# Phase 65: CI/CD with GitHub Actions - Context

**Gathered:** 2026-06-14 (autonomous yolo — repo-work; manual token/secret steps in final checklist)
**Status:** Ready for planning

<domain>
## Phase Boundary

Pushes are gated by the backend test suite; merges to `main` auto-deploy backend→Railway and frontend→Vercel.

- **Repo-work (AUTONOMOUS):** create `.github/workflows/` (test gate + deploy), add the rerun dependency for flake tolerance.
- **Manual (USER):** generate Railway + Vercel deploy tokens/IDs and enter them as GitHub repo secrets. Depends on Phases 63+64 being configured.

**Out of scope:** the smoke-test deploy gate (Phase 66), the actual Railway/Vercel resources (63/64).
</domain>

<decisions>
## Implementation Decisions

### Test gate (DCICD-01)
- **D-01:** `.github/workflows/test.yml` runs on `push` and `pull_request`. Python 3.11 → `pip install -r backend/requirements.txt` → `pytest`. Tests use **in-memory SQLite** (conftest.py `sqlite://` + StaticPool) — NO external Postgres service needed in CI. `mcp` and all test deps come from requirements.txt (so the local-only import gap does not affect CI).
- **D-02:** Tolerate the 4 documented pre-existing suite-isolation flakes via **`pytest-rerunfailures`** (`--reruns 2 --reruns-delay 1`). This is the correct mechanism: a genuine regression fails all 3 attempts and fails the run (satisfies "a failing test beyond the tolerated flakes fails the run"); only transient isolation flakes are absorbed. Added `pytest-rerunfailures==14.0` to `backend/requirements.txt`. Did NOT hard-skip/xfail specific tests (would mask real failures and is brittle to test renames).
- **D-03:** CI test env sets `ENVIRONMENT=development` + a throwaway `SECRET_KEY` so the prod guards don't fire during tests.

### Deploy (DCICD-02)
- **D-04:** `.github/workflows/deploy.yml` runs on `push` to `main` only. A `test` job (same gate) is a hard `needs:` prerequisite for both deploy jobs — a broken main never deploys.
- **D-05:** Backend → **Railway CLI** (`railway up --service <name> --ci`) authenticated by `RAILWAY_TOKEN` (repo secret); service name via `RAILWAY_SERVICE_NAME` secret.
- **D-06:** Frontend → **Vercel CLI** (`vercel pull` → `vercel build --prod` → `vercel deploy --prebuilt --prod`) authenticated by `VERCEL_TOKEN` + `VERCEL_ORG_ID` + `VERCEL_PROJECT_ID` (repo secrets), working-directory `frontend`.
- **D-07:** ALL credentials are GitHub repo secrets — none committed (DCICD constraint + success criterion #4).

### Claude's Discretion
- Exact rerun counts; CLI flag specifics; whether to split test/deploy into one or two files (chose two: `test.yml` for the universal gate, `deploy.yml` for main-only deploy with its own gate).

</decisions>

<canonical_refs>
## Canonical References

### Phase definition & requirements
- `.planning/ROADMAP.md` §"### Phase 65" — goal, constraints, 4 success criteria.
- `.planning/REQUIREMENTS.md` — DCICD-01 (line 34), DCICD-02 (line 35).

### CI/CD artifacts (created this phase)
- `.github/workflows/test.yml` — push/PR test gate.
- `.github/workflows/deploy.yml` — main-only deploy (Railway + Vercel), gated by tests.
- `backend/requirements.txt` — added `pytest-rerunfailures`.

### Test harness
- `backend/app/tests/conftest.py` — in-memory SQLite engine (why CI needs no Postgres service).
- `backend/pytest.ini` — testpaths, asyncio_mode.

### Prior phases
- `.planning/phases/63-...` (Railway target), `.planning/phases/64-...` (Vercel target).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- SQLite-based conftest → fast, hermetic CI with zero service containers.
- requirements.txt already pins pytest/pytest-asyncio/httpx → CI install is one step.

### Established Patterns
- `SKIP_MCP_LIFESPAN` env in conftest → REST tests don't need the MCP manager.

### Integration Points
- GitHub secrets → workflow env → Railway/Vercel CLIs.
- `needs: test` → deploy jobs gated on green suite.

</code_context>

<specifics>
## Specific Ideas
- Deploy on merge to `main` = prod (single-environment deploy per ROADMAP).
- Tolerate flakes without masking real failures (reruns, not skips).

</specifics>

<deferred>
## Deferred Ideas
- Post-deploy smoke test as the deploy success gate → Phase 66 (will extend deploy.yml).
- **MANUAL (user):** generate `RAILWAY_TOKEN`, `RAILWAY_SERVICE_NAME`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` and add as GitHub repo secrets. In the final checklist.

</deferred>

---

*Phase: 65-CI/CD with GitHub Actions*
*Context gathered: 2026-06-14 (autonomous)*
