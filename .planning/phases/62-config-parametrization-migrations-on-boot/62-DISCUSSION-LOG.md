# Phase 62: Config Parametrization & Migrations-on-Boot - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 62-Config Parametrization & Migrations-on-Boot
**Areas discussed:** Migrations on fresh DB, MCP base URL env var, ALLOWED_ORIGINS in prod, Migration idempotency/safety

---

## Migrations on fresh DB — baseline strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Run init_db.sql as step 0 | run_migrations executes init_db.sql first when fresh, then deltas. One source of truth. | ✓ |
| Convert baseline to delta 000 | Move init_db.sql into delta/000_baseline.sql; flows through normal loop. | |
| Keep entrypoint, add Railway pre-deploy | Leave init_db.sql Docker-only; separate Railway release step for baseline. | |

**User's choice:** Run init_db.sql as step 0
**Notes:** Keeps one source of truth; works on both Railway (no entrypoint hook) and Docker.

---

## Migrations on fresh DB — trigger condition

| Option | Description | Selected |
|--------|-------------|----------|
| When projects table is absent | Reuse existing information_schema check; absent + no 000_baseline → fresh → run init_db.sql. | ✓ |
| When schema_migrations is empty | Zero rows → fresh. Risk: pre-tracking existing DB triggers wrongly. | |
| Always run init_db.sql | Run every boot (idempotent). Wasteful; noisy logs. | |

**User's choice:** When projects table is absent
**Notes:** Dovetails with the existing baseline-detection branch; no double-run in Docker (projects already exists by app boot).

---

## Migrations on fresh DB — failure behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fail hard, crash boot | Let exception propagate; loud in Railway logs; no half-migrated DB. | ✓ |
| Log and continue | App boots but 500s on missing tables. Hides root cause. | |
| Retry with backoff | Retry a few times for cold-start races before failing hard. | |

**User's choice:** Fail hard, crash boot
**Notes:** Matches existing prod fail-hard stance (SECRET_KEY guard). Retry-with-backoff noted as a possible future revisit if cold-start timing proves flaky.

---

## MCP base URL env var

| Option | Description | Selected |
|--------|-------------|----------|
| New MCP_BASE_URL setting | Add to config.py Settings (default localhost:8001); server.py reads it. | ✓ |
| Reuse os.getenv directly | server.py reads os.getenv without adding to Settings. | |
| Derive from ALLOWED_ORIGINS/host | Compute from an existing value. Couples unrelated config. | |

**User's choice:** New MCP_BASE_URL setting
**Notes:** Consistent with the "all config in config.py / pydantic Settings" convention.

---

## ALLOWED_ORIGINS in prod

| Option | Description | Selected |
|--------|-------------|----------|
| Keep warning only | Log a warning but boot; defer hard lock to Phase 66. | ✓ |
| Fail hard in prod | Raise if localhost in ALLOWED_ORIGINS when production. | |
| Default to empty in prod | Force explicit CORS config in prod. | |

**User's choice:** Keep warning only
**Notes:** The hard CORS lock to the Vercel domain is Phase 66's dedicated scope — don't pre-empt it. This phase only ensures no prod origin is hardcoded (already true).

---

## Migration idempotency/safety — delta failure

| Option | Description | Selected |
|--------|-------------|----------|
| Per-migration commit, fail hard | Keep current pattern; raise on failure; failing migration retries next boot. | ✓ |
| Wrap all deltas in one transaction | All-or-nothing rollback. Heavy DDL; diverges from current design. | |
| Skip-and-continue | Log and move on. Risks inconsistent schema. | |

**User's choice:** Per-migration commit, fail hard
**Notes:** Matches existing db_migrator.py code.

---

## Migration idempotency/safety — concurrency

| Option | Description | Selected |
|--------|-------------|----------|
| Postgres advisory lock | pg_advisory_lock so only one instance migrates; others wait then no-op. | ✓ |
| Rely on idempotency only | No lock; trust IF NOT EXISTS + UNIQUE + ON CONFLICT. | |
| Out of scope — single instance | Assume one replica; defer locking. | |

**User's choice:** Postgres advisory lock
**Notes:** Cheap, robust, standard for migrate-on-boot; covers Railway replica scaling and redeploy overlap.

---

## Claude's Discretion

- Exact advisory-lock key/id and placement of acquire/release within run_migrations.
- How step 0 resolves the init_db.sql path (DELTA_DIR-style Path vs sibling constant).
- Log message wording for the fresh-DB-baseline path.
- Field ordering of MCP_BASE_URL within Settings.

## Deferred Ideas

- Hard CORS lock to the Vercel domain → Phase 66.
- Enabling pgvector / provisioning Railway Postgres → Phase 63.
- Reviewing MCP DNS-rebinding protection for a public host → Phase 66.
- Retry-with-backoff on migration cold-start races → considered, rejected for now; possible future revisit.
