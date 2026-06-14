# Phase 64: Frontend on Vercel - Context

**Gathered:** 2026-06-14 (autonomous yolo — repo-work; manual Vercel steps in final checklist)
**Status:** Ready for planning

<domain>
## Phase Boundary

The Vite/React frontend is live on Vercel and talks to the production Railway backend via `VITE_API_URL`.

- **Repo-work (AUTONOMOUS):** Vercel build config (`vercel.json`), confirm `npm run build` passes, confirm `VITE_API_URL` consumption.
- **Manual (USER):** Vercel (VAPAI-Studio) login, set `VITE_API_URL` env to the Railway backend domain, confirm the deployed domain. Depends on Phase 63's Railway domain existing.

**Out of scope:** CORS lock to this Vercel domain (Phase 66), deploy automation (Phase 65).
</domain>

<decisions>
## Implementation Decisions

### Build (DFND-01)
- **D-01:** VERIFIED `npm run build` (`tsc && vite build`) passes clean — `tsc --noEmit` 0 errors, vite build exit 0, `dist/` produced. The "pre-existing TypeScript build concerns" noted in earlier milestones no longer reproduce; NO TS fixes needed. Only a non-blocking chunk-size warning (>500kB) remains — left as-is (code-splitting is a perf nicety, out of scope for "deploy reliably").

### Vercel config
- **D-02:** Add `frontend/vercel.json`: framework=vite, buildCommand=`npm run build`, outputDirectory=`dist`, installCommand=`npm install`, and an SPA rewrite `/(.*) → /index.html`. The rewrite is REQUIRED because the app uses `BrowserRouter` (App.tsx) — without it, a hard refresh on `/projects/:id` 404s on Vercel.
- **D-03:** The Vercel project's **Root Directory must be set to `frontend`** (manual, dashboard) so `vercel.json` and the Vite app resolve correctly.

### API wiring (DFND-02)
- **D-04:** VERIFIED no code change — `frontend/src/lib/constants.ts:7` reads `import.meta.env.VITE_API_URL || '/api'`; `vite-env.d.ts` types it. The Railway backend domain is supplied via Vercel env `VITE_API_URL` (manual). This consumes the Phase 62 parametrization.

### Claude's Discretion
- vercel.json schema specifics; whether to add a `dist` .gitignore entry (already covered by root .gitignore).

</decisions>

<canonical_refs>
## Canonical References

### Phase definition & requirements
- `.planning/ROADMAP.md` §"### Phase 64" — goal, constraints, 3 success criteria.
- `.planning/REQUIREMENTS.md` — DFND-01 (line 20), DFND-02 (line 21).

### Frontend build & API layer
- `frontend/package.json` — `"build": "tsc && vite build"`.
- `frontend/vercel.json` — Vercel build + SPA rewrite (created this phase).
- `frontend/src/App.tsx` — `BrowserRouter` routing (why the SPA rewrite is needed).
- `frontend/src/lib/constants.ts:7` — `API_BASE_URL = import.meta.env.VITE_API_URL || '/api'` (DFND-02).
- `frontend/src/vite-env.d.ts` — `VITE_API_URL` typing.

### Prior phases
- `.planning/phases/62-...` — VITE_API_URL parametrization (already done).
- `.planning/phases/63-...` — Railway backend domain that VITE_API_URL points at.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Build already green; `VITE_API_URL` already consumed — phase is mostly config + manual.

### Established Patterns
- Vite env vars (`import.meta.env.VITE_*`) with `/api` dev fallback.

### Integration Points
- Vercel env `VITE_API_URL` → build-time inlined → fetch layer (`api.tsx` via `API_BASE_URL`).
- Vercel SPA rewrite → BrowserRouter client routes.

</code_context>

<specifics>
## Specific Ideas
- Deploy under the VAPAI-Studio Vercel account (per ROADMAP).

</specifics>

<deferred>
## Deferred Ideas
- Bundle code-splitting to silence the >500kB chunk warning — perf nicety, not deploy-blocking.
- CORS lock to the Vercel domain → Phase 66.
- **MANUAL (user):** Vercel login, Root Directory=`frontend`, set `VITE_API_URL`=Railway domain, confirm deployed domain. In the final checklist.

</deferred>

---

*Phase: 64-Frontend on Vercel*
*Context gathered: 2026-06-14 (autonomous)*
