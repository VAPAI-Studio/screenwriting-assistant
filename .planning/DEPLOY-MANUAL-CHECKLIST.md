# v9.0 Deploy — Manual Steps Checklist (human-in-the-loop)

All in-repo work for phases 63–66 is done and committed. The steps below are the
ones only you can do (logins + secrets in external accounts). Do them in order —
each phase depends on the previous one's output (the Railway domain, then the
Vercel domain, then the tokens).

---

## Phase 63 — Railway (backend + Postgres + volume)

1. **Log in to Railway** and create a new project from this GitHub repo.
2. On the backend service → **Settings → Root Directory = `backend`**
   (so `railway.json`'s `dockerfilePath: "Dockerfile"` resolves to
   `backend/Dockerfile` with the correct build context).
3. Add a **Postgres** plugin to the project. `DATABASE_URL` auto-wires into the
   backend service. **Enable the `pgvector` extension** on that Postgres
   (Railway Postgres supports it; the app's `init_db.sql` runs
   `CREATE EXTENSION IF NOT EXISTS "vector"` on first boot — if pgvector isn't
   available the backend will fail-hard on boot, by design).
4. Add a **persistent Volume**, mount it (e.g. at `/media`), and set env
   **`MEDIA_DIR=/media`** so uploads survive redeploys.
5. Set service **environment variables**:
   - `OPENAI_API_KEY` = your key
   - `ANTHROPIC_API_KEY` = your key
   - `SECRET_KEY` = a strong random secret (NOT the default — prod guard rejects it)
   - `ENVIRONMENT=production`
   - `AI_PROVIDER` = `anthropic` or `openai` as desired
   - `MEDIA_DIR=/media`
6. Deploy. ✅ Verify: `https://<service>.up.railway.app/health` returns 200.
7. **Note the Railway backend domain** — you need it for Phase 64.

---

## Phase 64 — Vercel (frontend)

1. **Log in to Vercel** (VAPAI-Studio account) and import this repo.
2. Set project **Root Directory = `frontend`** (picks up `frontend/vercel.json`).
3. Set env **`VITE_API_URL`** = the Railway backend domain + `/api`, e.g.
   `https://<service>.up.railway.app/api`.
4. Deploy. ✅ Verify: the Vercel URL loads the app.
   (Full end-to-end calls also need the CORS lock in Phase 66.)
5. **Note the Vercel frontend domain** — you need it for Phases 65/66.

---

## Phase 65 — GitHub Actions secrets (CI/CD)

The workflows are already committed (`.github/workflows/test.yml`,
`deploy.yml`). Add these **GitHub repo secrets**
(Settings → Secrets and variables → Actions):

| Secret | Value |
|--------|-------|
| `RAILWAY_TOKEN` | Railway project/deploy token (Railway → Project → Settings → Tokens) |
| `RAILWAY_SERVICE_NAME` | the backend service name in Railway |
| `VERCEL_TOKEN` | Vercel token (Account Settings → Tokens) |
| `VERCEL_ORG_ID` | from `vercel link` or Vercel project settings |
| `VERCEL_PROJECT_ID` | from `vercel link` or Vercel project settings |

✅ Verify: a push runs the test gate; a merge to `main` runs tests then deploys
both targets.

---

## Phase 66 — Hardening + smoke test

1. On **Railway** prod env, set **`ALLOWED_ORIGINS`** to the Vercel frontend
   domain (e.g. `https://<app>.vercel.app`). This locks CORS — other origins are
   rejected. (No localhost in prod.)
2. *(Optional, recommended for a public host)* set
   **`MCP_DNS_REBINDING_PROTECTION=true`** on Railway to harden the public `/mcp`
   surface. Default is `false`; API-key auth is the primary defense either way.
3. Add **GitHub repo secrets** for the post-deploy smoke gate:
   - `PROD_BACKEND_URL` = the Railway backend domain (e.g. `https://<svc>.up.railway.app`)
   - `PROD_FRONTEND_URL` = the Vercel frontend domain
4. ✅ Verify: after the next merge-to-`main` deploy, the `smoke-test` job runs and
   passes (backend `/health` 200 + frontend loads). A failed smoke test fails the
   deploy.

---

## Quick local sanity checks (optional, no accounts needed)

- Backend build: `docker build -t sw-backend backend/` then
  `docker run -e PORT=9000 -e SECRET_KEY=x -e DATABASE_URL=... -p 9000:9000 sw-backend`
  → confirm it binds to `$PORT`.
- Frontend build: `cd frontend && npm run build` → `dist/` produced (already verified).
- Smoke test against any running pair:
  `BACKEND_URL=... FRONTEND_URL=... bash scripts/smoke_test.sh`.

---

*Generated 2026-06-14. In-repo work for phases 63–66 committed; these are the
remaining human-in-the-loop actions.*
