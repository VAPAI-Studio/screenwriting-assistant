# Phase 63: Backend + Postgres + Volume on Railway - Context

**Gathered:** 2026-06-14 (autonomous yolo mode — repo-work decisions; manual Railway steps deferred to user checklist)
**Status:** Ready for planning

<domain>
## Phase Boundary

The FastAPI backend runs live on Railway against a Railway Postgres (pgvector) with a persistent `/media` volume and secrets from Railway env.

**This phase splits into two halves:**
- **Repo-work (AUTONOMOUS — this run):** everything in the repo that makes the service deployable reproducibly on Railway serving `$PORT`, ready to consume an injected `DATABASE_URL`, with `/media` persistence and pgvector readiness. All committed.
- **Manual (USER — human-in-the-loop, deferred to checklist):** Railway login/authorization, creating the Postgres + enabling pgvector, mounting the persistent volume at `/media`, and entering secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SECRET_KEY`) into Railway env.

**Out of scope:** CORS lock to a real domain (Phase 66), the deploy pipeline (Phase 65), the frontend (Phase 64).
</domain>

<decisions>
## Implementation Decisions

### Build mechanism (DBKD-01)
- **D-01:** Use the existing `backend/Dockerfile` as the production build (reproducible, already installs `libpq-dev`/`gcc` for psycopg2, runs as non-root `appuser`, sets `PYTHONPATH=/app`). Do NOT switch to nixpacks — a committed Dockerfile is more reproducible and Railway supports it directly.
- **D-02:** **Fix the hardcoded port.** `backend/Dockerfile` currently ends with `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` — Railway injects `$PORT`. Change to a shell-form CMD that honors `$PORT` with a sensible local default, e.g. `CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`. The `EXPOSE 8000` line is documentation-only and can stay or be dropped; keep it harmless. The existing `Procfile` already uses `$PORT` and stays as a fallback for nixpacks-style builds.
- **D-03:** Add a `railway.json` at repo root pinning the builder to DOCKERFILE with `backend/Dockerfile` as the dockerfilePath, and a restart policy. This makes the Railway build deterministic and committed, rather than relying on dashboard config. Keep it minimal.

### Database wiring (DBKD-02)
- **D-04:** No code change needed for `DATABASE_URL` — `config.py` already reads it from env (default is the local dev DSN). Railway auto-injects `DATABASE_URL` for a linked Postgres. VERIFY this path; do not hardcode anything.
- **D-05:** pgvector: `backend/migrations/init_db.sql` already does `CREATE EXTENSION IF NOT EXISTS "vector"`. Combined with Phase 62's fresh-DB step-0, the first boot will attempt to create the extension. On Railway the pgvector extension must be available/enabled (manual step). The repo already declares `pgvector==0.3.6` in requirements. No repo change required beyond confirming the `IF NOT EXISTS` guard is present. Document the manual enable step in the checklist. NOTE the Phase 62 fail-hard: if pgvector is not enabled, boot crashes loudly — that is intended.

### Media volume (DBKD-03)
- **D-06:** No code change needed for the mount point — `main.py` already does `os.makedirs(settings.MEDIA_DIR, exist_ok=True)` then `app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR))`, and `MEDIA_DIR` defaults to `<backend>/media`. For Railway, set `MEDIA_DIR=/media` via env so the StaticFiles dir points at the mounted volume. VERIFY `MEDIA_DIR` is env-overridable in `config.py` (it is a plain Settings field). Document the volume mount + `MEDIA_DIR=/media` env in the checklist. The Dockerfile already creates `/app/media`; the Railway volume mounts over `MEDIA_DIR`.

### Secrets (DBKD-04)
- **D-07:** No secret is committed. `config.py` already raises in production if `SECRET_KEY` is the default (existing prod guard). VERIFY `.env.example.txt` documents all three secrets and that none are hardcoded. The actual secret values are entered by the user into Railway env (manual). Ensure `ENVIRONMENT=production` is part of the documented Railway env so the prod guards activate.

### Claude's Discretion
- Exact `railway.json` schema fields (builder, dockerfilePath, restartPolicyType, healthcheckPath=`/health`).
- Whether to keep or drop `EXPOSE 8000`.
- Wording of the manual checklist.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` §"### Phase 63" — goal, constraints, 4 success criteria.
- `.planning/REQUIREMENTS.md` — DBKD-01 (line 13), DBKD-02 (14), DBKD-03 (15), DBKD-04 (16).

### Backend build & runtime
- `backend/Dockerfile` — production build; CMD port fix goes here (D-02).
- `Procfile` — `web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` (already $PORT-correct; fallback).
- `backend/app/main.py` §145-152 — media router + StaticFiles mount at `/media` (D-06).
- `backend/app/config.py` — `DATABASE_URL` (line 13), `MEDIA_DIR`/`UPLOAD_DIR`, `SECRET_KEY` prod guard, `ENVIRONMENT`.
- `backend/migrations/init_db.sql` — `CREATE EXTENSION IF NOT EXISTS "vector"` (D-05); consumed by Phase 62 migrations-on-boot.
- `backend/requirements.txt` — `pgvector==0.3.6`, `psycopg2-binary`, `sqlalchemy`.
- `backend/.env.example.txt` — secret documentation surface (D-07).

### Prior phase
- `.planning/phases/62-config-parametrization-migrations-on-boot/62-CONTEXT.md` — migrations-on-boot + fail-hard behavior this phase relies on.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/Dockerfile` already production-shaped (non-root, deps, PYTHONPATH) — only the CMD port needs fixing.
- `main.py` media mount + `config.py` env-driven Settings — no code change, just env wiring on Railway.
- Phase 62 `run_migrations` step-0 — a fresh Railway Postgres self-bootstraps the schema on first boot.

### Established Patterns
- "All config via env / pydantic Settings" — Railway env vars flow in without code changes.
- "Fail hard in prod on misconfig" (SECRET_KEY guard, Phase 62 migration fail-hard) — a broken Railway env surfaces loudly at boot, by design.

### Integration Points
- Railway → `DATABASE_URL` env → `config.py` → `db.py` engine → `init_db()` on boot (Phase 62).
- Railway volume → mounted at path → `MEDIA_DIR` env → `StaticFiles` mount.

</code_context>

<specifics>
## Specific Ideas

- Single Railway Postgres holds ALL data including pgvector embeddings (no separate agent DB) — per ROADMAP constraint.
- Reproducible committed build config (Dockerfile + railway.json) over dashboard-only config.

</specifics>

<deferred>
## Deferred Ideas

- CORS lock to Vercel domain → Phase 66.
- Deploy automation → Phase 65.
- **MANUAL (user, human-in-the-loop):** Railway login, create Postgres + enable pgvector, mount `/media` volume, enter secrets + `ENVIRONMENT=production` + `MEDIA_DIR=/media`. Captured in the final checklist, not implementable in-repo.

</deferred>

---

*Phase: 63-Backend + Postgres + Volume on Railway*
*Context gathered: 2026-06-14 (autonomous)*
