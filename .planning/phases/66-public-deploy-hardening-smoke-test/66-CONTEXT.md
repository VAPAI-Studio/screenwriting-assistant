# Phase 66: Public-Deploy Hardening & Post-Deploy Smoke Test - Context

**Gathered:** 2026-06-14 (autonomous yolo — repo-work; manual prod-env step in final checklist)
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock the public deploy down for a public host and prove prod is live before a deploy counts as successful.

- **Repo-work (AUTONOMOUS):** make MCP DNS-rebinding protection configurable for a public host, post-deploy smoke test script + deploy-gate job, confirm CORS consumes `ALLOWED_ORIGINS`.
- **Manual (USER):** set `ALLOWED_ORIGINS` to the Vercel domain in Railway prod env; optionally set `MCP_DNS_REBINDING_PROTECTION=true`; add `PROD_BACKEND_URL`/`PROD_FRONTEND_URL` GitHub secrets for the smoke test.

**Depends on:** Phase 64 (Vercel domain to lock CORS to) + Phase 65 (the deploy pipeline the smoke test gates).
</domain>

<decisions>
## Implementation Decisions

### CORS lock (DSEC-01, CORS half)
- **D-01:** VERIFIED no code change — `main.py:99` already does `allow_origins=settings.ALLOWED_ORIGINS`. Locking CORS to the Vercel domain in prod is purely setting the `ALLOWED_ORIGINS` env var on Railway (manual), consuming the Phase 62 parametrization. Requests from other origins are then rejected by the existing CORSMiddleware. This is the deferred half of Phase 62's D-09 (warning-only there; the actual lock is here, via env).

### MCP DNS-rebinding (DSEC-01, MCP half)
- **D-02:** Found a latent bug: server.py read `getattr(settings, "MCP_DNS_REBINDING_PROTECTION", "false")` but that field did NOT exist on Settings, so the getattr ALWAYS fell to the `"false"` default — the toggle was unreachable. Fix: promote `MCP_DNS_REBINDING_PROTECTION: bool = False` to a real `config.py` Settings field, and read `settings.MCP_DNS_REBINDING_PROTECTION` (typed bool) in server.py. Now it is genuinely configurable by env for a public host.
- **D-03:** Default stays `False` — the server is API-key-gated (TokenVerifier is the primary defense) and enabling Host-allowlisting requires enumerating client hosts. Documented in config.py + .env.example how/when to enable on a public host. This satisfies the "reviewed and set appropriately" requirement: reviewed → made it a real, documented, env-settable toggle defaulting off, with guidance to turn on for a fixed public host.

### Smoke test (DVER-01)
- **D-04:** Add `scripts/smoke_test.sh` — checks backend `/health` (200) at `BACKEND_URL` and the frontend (200) at `FRONTEND_URL`, with retries for cold-start/propagation, exits non-zero on failure.
- **D-05:** Add a `smoke-test` job to `.github/workflows/deploy.yml` with `needs: [deploy-backend, deploy-frontend]` so it runs ONLY after both deploys and acts as the deploy success gate (not a manual afterthought). URLs come from `PROD_BACKEND_URL`/`PROD_FRONTEND_URL` GitHub secrets.

### Claude's Discretion
- Smoke retry counts/delays; exact job wiring.

</decisions>

<canonical_refs>
## Canonical References

### Phase definition & requirements
- `.planning/ROADMAP.md` §"### Phase 66" — goal, constraints, 3 success criteria.
- `.planning/REQUIREMENTS.md` — DSEC-01 (line 39), DVER-01 (line 43).

### Hardening + smoke artifacts
- `backend/app/main.py:98-99` — CORSMiddleware `allow_origins=settings.ALLOWED_ORIGINS` (DSEC-01 CORS).
- `backend/app/config.py` — `ALLOWED_ORIGINS`, new `MCP_DNS_REBINDING_PROTECTION: bool` field.
- `backend/app/mcp_server/server.py:26-29` — `_dns_protect` now reads the typed Settings field (DSEC-01 MCP).
- `scripts/smoke_test.sh` — post-deploy smoke test (DVER-01).
- `.github/workflows/deploy.yml` — `smoke-test` job gating deploy success.

### Prior phases
- `.planning/phases/62-...` — ALLOWED_ORIGINS + MCP_BASE_URL parametrization; D-09 deferred the CORS lock to here.
- `.planning/phases/64-...`, `65-...` — Vercel domain + deploy pipeline.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- CORSMiddleware already env-driven — CORS lock is config-only.
- Phase 65 deploy.yml — extended with the smoke gate rather than a new pipeline.

### Established Patterns
- "All config via Settings" — the DNS-rebinding toggle now follows it (was a broken getattr).
- "Prove prod before declaring success" — smoke test as a `needs:` gate.

### Integration Points
- Railway prod env `ALLOWED_ORIGINS` → CORSMiddleware → cross-origin policy.
- `MCP_DNS_REBINDING_PROTECTION` env → TransportSecuritySettings.
- deploy.yml smoke-test job → scripts/smoke_test.sh → /health + frontend.

</code_context>

<specifics>
## Specific Ideas
- The CORS lock is the realization of Phase 62's deferred D-09 (warning-only → enforced via prod env).

</specifics>

<deferred>
## Deferred Ideas
- Per-route rate-limit tuning for the public MCP surface — beyond "deploy reliably", not in scope.
- **MANUAL (user):** set `ALLOWED_ORIGINS`=Vercel domain in Railway prod; optionally `MCP_DNS_REBINDING_PROTECTION=true`; add `PROD_BACKEND_URL`/`PROD_FRONTEND_URL` GitHub secrets. In the final checklist.

</deferred>

---

*Phase: 66-Public-Deploy Hardening & Post-Deploy Smoke Test*
*Context gathered: 2026-06-14 (autonomous)*
