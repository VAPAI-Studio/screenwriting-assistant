# Phase 66 — Repo-Work Summary (autonomous)

**Status:** Repo-side COMPLETE. Manual prod-env steps deferred to the final checklist.

## What was done (in-repo, committed)

| Req | Change | File |
|-----|--------|------|
| DSEC-01 (CORS) | VERIFIED `allow_origins=settings.ALLOWED_ORIGINS` already wired. CORS lock to Vercel = setting the prod env var (manual). Realizes Phase 62's deferred D-09. | `backend/app/main.py:99` |
| DSEC-01 (MCP) | **Bug fix:** `MCP_DNS_REBINDING_PROTECTION` was read via `getattr` but never existed on Settings (toggle was unreachable, always false). Promoted it to a real `bool` Settings field; server.py now reads the typed value. Default `False` (API-key auth primary); documented how to enable on a public host. | `backend/app/config.py`, `backend/app/mcp_server/server.py` |
| DVER-01 | Added `scripts/smoke_test.sh` — backend `/health` + frontend load checks with retries, fails non-zero. | `scripts/smoke_test.sh` |
| DVER-01 | Added `smoke-test` job to deploy.yml, `needs: [deploy-backend, deploy-frontend]` — the deploy success gate. | `.github/workflows/deploy.yml` |
| docs | Documented `MCP_DNS_REBINDING_PROTECTION` in `.env.example.txt`. | `backend/.env.example.txt` |

## Verification done
- `config.py` loads; `MCP_DNS_REBINDING_PROTECTION` resolves to `bool False`.
- deploy.yml valid YAML; smoke_test.sh valid bash syntax + executable.
- Pre-existing Pyright diagnostics on server.py (str→AnyHttpUrl, headers-on-None) are NOT introduced by this phase — they predate it (Phase 62 / earlier); behavior-preserving.

## Manual steps required (user) — see final checklist
1. Railway prod env: `ALLOWED_ORIGINS` = the Vercel frontend domain (locks CORS; other origins rejected).
2. Optionally `MCP_DNS_REBINDING_PROTECTION=true` on the public host.
3. GitHub secrets `PROD_BACKEND_URL` (Railway domain) + `PROD_FRONTEND_URL` (Vercel domain) for the smoke gate.

## Self-Check: PASSED (repo-side)
- DNS toggle now functional + typed; smoke test + deploy gate in place; CORS env-driven; env docs updated.
