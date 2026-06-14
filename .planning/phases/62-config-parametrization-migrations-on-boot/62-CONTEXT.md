# Phase 62: Config Parametrization & Migrations-on-Boot - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Make every production-environment-specific value env-driven (no hardcoded localhost) and have a fresh or upgraded Postgres reach the current schema automatically on boot — the in-repo groundwork that lets phases 63-66 target a real host (Railway/Vercel) with no external account required.

Three known hardcodes are in scope: `ALLOWED_ORIGINS`, the MCP base URL, and `VITE_API_URL` (the last is already done). Plus migrations-on-boot via `init_db` → `run_migrations`.

**Out of scope:** locking CORS to the actual Vercel domain (Phase 66), enabling pgvector / provisioning the Railway DB (Phase 63), reviewing MCP DNS-rebinding protection for a public host (Phase 66). This phase only parametrizes and makes boot self-sufficient; it does not deploy.

</domain>

<decisions>
## Implementation Decisions

### Migrations on a fresh DB (DMIG-01)
- **D-01:** `run_migrations` runs `backend/migrations/init_db.sql` as **step 0** (baseline schema) when the DB is truly fresh. `init_db.sql` is the single source of truth for the baseline (494 lines: extensions + all tables + inserts `000_baseline`). No new "convert baseline to delta" restructuring; no separate Railway release step.
- **D-02:** Trigger condition for step 0 = **the `projects` table is absent** (reuse the existing `information_schema` check already in `db_migrator.py`). Combined with `000_baseline` not yet recorded. An existing pre-tracking DB (projects exist, no migrations row) keeps using the current baseline-detection branch — it does NOT re-run `init_db.sql`.
- **D-03:** No double-run risk in the Docker flow: the entrypoint hook (`docker-entrypoint-initdb.d/001_init_db.sql`) already creates `projects` before the app boots, so step 0 is skipped there. Railway has no entrypoint hook, so step 0 fires once on the first boot against the empty managed Postgres.
- **D-04:** If `init_db.sql` fails (e.g., `CREATE EXTENSION vector`/`uuid-ossp` not yet enabled on the fresh DB), **fail hard — let the exception propagate and crash boot.** A loud Railway-log failure is preferred over a half-migrated DB or a booted app that 500s on missing tables. (Note: pgvector enablement itself is a Phase 63 concern; this phase just doesn't swallow the error.)
- **D-05:** Guard the whole migration run with a **Postgres advisory lock** (`pg_advisory_lock` / matching unlock) so concurrent instances — Railway scaling to 2 replicas or a redeploy overlap — can't race on the same DDL. Other instances wait, then find nothing to apply.

### Delta migration safety (DMIG-01)
- **D-06:** Keep the existing **per-migration commit** pattern (each `NNN_*.sql` runs and commits individually). On any delta failure, **fail hard** — raise so boot crashes. Already-applied migrations stay recorded; the failing one is retried on the next boot. No all-in-one-transaction wrapping; no skip-and-continue.

### MCP base URL (DCFG-02)
- **D-07:** Add a **`MCP_BASE_URL`** setting to `backend/app/config.py` (`Settings`), default `"http://localhost:8001"`. `mcp_server/server.py` reads `settings.MCP_BASE_URL` for both `issuer_url` and `resource_server_url`, replacing the hardcoded `_BASE_URL`. Follows the project convention "all config lives in config.py / pydantic Settings" — not a bare `os.getenv` and not derived from another value.

### ALLOWED_ORIGINS (DCFG-01)
- **D-08:** Already env-readable (pydantic `Settings` list + docker-compose `${ALLOWED_ORIGINS:-[...localhost...]}`). **Keep as-is.** Local `docker compose up` must still work with the localhost default.
- **D-09:** In production, leaving localhost in `ALLOWED_ORIGINS` stays a **warning only** (current behavior in `config.py.__init__`). Do NOT fail-hard and do NOT default to empty in prod here — the hard CORS lock to the Vercel domain is **Phase 66's** dedicated scope. This phase only ensures no prod origin is hardcoded in the repo (already true).

### VITE_API_URL
- **D-10:** Already satisfied — frontend reads `import.meta.env.VITE_API_URL || '/api'` and docker-compose sets `VITE_API_URL=/api`. No change needed; success criterion #4 is already met.

### Claude's Discretion
- Exact advisory-lock key/id and the precise placement of the lock acquire/release within `run_migrations`.
- Whether step 0 reads `init_db.sql` via the existing `DELTA_DIR`-style `Path` resolution or a sibling path constant.
- Log message wording for the fresh-DB-baseline path.
- The `MCP_BASE_URL` env var's exact field ordering within `Settings`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` §"Phase 62" (lines ~504-514) — goal, depends-on, constraints to honor, success criteria.
- `.planning/REQUIREMENTS.md` — DCFG-01 (line 25), DCFG-02 (line 26), DMIG-01 (line 30).

### Migrations-on-boot (the consequential area)
- `backend/app/db.py` — `init_db()` delegates to `run_migrations(engine)`.
- `backend/app/services/db_migrator.py` — `run_migrations()`; existing tracking-table creation, baseline-detection branch, and per-migration-commit loop. **This is the file step-0 + advisory-lock changes go into.**
- `backend/migrations/init_db.sql` — the 494-line baseline (extensions + all tables + `INSERT 000_baseline`). Becomes step 0's input on a fresh DB.
- `backend/migrations/delta/*.sql` — `001`…`010` idempotent deltas applied after baseline. MUST stay idempotent.
- `backend/app/main.py` §lifespan (lines ~50-70) — where `init_db()` is invoked on boot (two call sites: `SKIP_MCP_LIFESPAN` and normal).

### Config parametrization
- `backend/app/config.py` — `Settings`; `ALLOWED_ORIGINS` (line 30), prod-guard `__init__` (lines ~110-114). Add `MCP_BASE_URL` here.
- `backend/app/mcp_server/server.py` — `_BASE_URL` (line 19), used at `issuer_url`/`resource_server_url` (lines 35-36).
- `docker-compose.yml` — `ALLOWED_ORIGINS` env interpolation (line 27), `VITE_API_URL=/api` (line 44), `init_db.sql` entrypoint mount (line 16).
- `backend/.env.example.txt` — env-var documentation surface (add `MCP_BASE_URL`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db_migrator.run_migrations()`: already creates `schema_migrations`, has an `information_schema` check for the `projects` table, and a per-file commit loop. Step 0 + advisory lock extend this — minimal new surface.
- `init_db.sql`: already fully idempotent (`CREATE ... IF NOT EXISTS`, `INSERT ... ON CONFLICT DO NOTHING` for `000_baseline`) — safe to invoke from `run_migrations` without restructuring.
- pydantic `Settings` in `config.py`: env-var loading + `.env` file + per-field validators already established; `MCP_BASE_URL` slots in like every other setting.

### Established Patterns
- "All config in config.py / Settings" — new env vars get a typed field + default, not bare `os.getenv` (already the norm; only `MCP_DNS_REBINDING_PROTECTION` uses `getattr(settings, ...)`).
- "Migrations are idempotent and applied on boot" — the migrator philosophy is documented in `db_migrator.py`'s header comment; honor it.
- "Fail hard on misconfiguration in production" — `config.py.__init__` already raises on default `SECRET_KEY` in prod; the migration fail-hard decision (D-04, D-06) matches this stance.

### Integration Points
- `main.py` lifespan → `init_db()` → `run_migrations(engine)`: boot-time entry point. No change to the call chain; behavior changes live inside `run_migrations`.
- `mcp_server/server.py` `AuthSettings(issuer_url=..., resource_server_url=...)`: the single consumer of the MCP base URL.

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose migrations-on-boot via `init_db` over a CI/release-step approach (carried from milestone decisions and ROADMAP constraints).
- One source of truth for the baseline schema (`init_db.sql`) — reused for both Docker and Railway rather than duplicated or split.

</specifics>

<deferred>
## Deferred Ideas

- **Hard CORS lock to the Vercel domain** (fail-hard / empty-default on prod localhost) — belongs to **Phase 66** (Public-Deploy Hardening). Considered and explicitly deferred here.
- **Enabling pgvector / provisioning the Railway Postgres** — **Phase 63**. This phase only ensures boot fails loudly if extensions are missing; it does not install them.
- **Reviewing MCP DNS-rebinding protection for a public host** — **Phase 66**.
- **Retry-with-backoff on migration for cold-start DB-not-ready races** — considered for D-04 but rejected in favor of fail-hard for this milestone. Could revisit if Railway cold-start timing proves flaky.

</deferred>

---

*Phase: 62-Config Parametrization & Migrations-on-Boot*
*Context gathered: 2026-06-14*
