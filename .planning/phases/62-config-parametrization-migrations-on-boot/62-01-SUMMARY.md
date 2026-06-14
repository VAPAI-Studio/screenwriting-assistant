---
phase: 62-config-parametrization-migrations-on-boot
plan: 01
subsystem: backend-config
tags: [config, mcp, cors, deploy, env]
requires:
  - backend/app/config.py (Settings class)
  - backend/app/mcp_server/server.py (AuthSettings consumer)
provides:
  - settings.MCP_BASE_URL (parametrized MCP base URL, localhost default)
  - documented MCP_BASE_URL env var
affects:
  - Phases 63-66 (deploy) can now target a real host via MCP_BASE_URL
tech-stack:
  added: []
  patterns:
    - "pydantic Settings typed-field-with-default for all config (no bare os.getenv)"
key-files:
  created: []
  modified:
    - backend/app/config.py
    - backend/app/mcp_server/server.py
    - backend/.env.example.txt
decisions:
  - "MCP base URL sourced from settings.MCP_BASE_URL (pydantic field), not a module-level constant — consistent with every other setting"
  - "MCP_BASE_URL is metadata-only (issuer/resource_server_url); static-bearer auth in TokenVerifier is unaffected (T-62-01 accepted)"
  - "ALLOWED_ORIGINS warning-only prod guard left intact — hard CORS lock deferred to Phase 66 (T-62-02 accepted/deferred per D-09)"
  - "VITE_API_URL and ALLOWED_ORIGINS were already env-driven — VERIFIED only, not re-implemented"
metrics:
  duration: ~11min
  completed: 2026-06-14T23:04:16Z
  tasks: 2
  files: 3
---

# Phase 62 Plan 01: Config Parametrization (MCP Base URL) Summary

Parametrized the MCP server base URL via a new `settings.MCP_BASE_URL` pydantic field (localhost default), wired `mcp_server/server.py` AuthSettings to it, documented it in `.env.example.txt`, and verified ALLOWED_ORIGINS + VITE_API_URL were already env-driven with safe localhost fallbacks — removing the last hardcoded localhost in the MCP server while keeping local `docker compose up` behavior byte-for-byte unchanged.

## What Was Built

### Task 1 — MCP_BASE_URL Settings field + server.py wiring (commit 59168c2)
- Added `MCP_BASE_URL: str = "http://localhost:8001"` to `Settings` in `config.py`, placed in the Server section next to `PORT`, following the typed-field-with-default convention (no bare `os.getenv`).
- Removed the module-level `_BASE_URL = "http://localhost:8001"` constant from `mcp_server/server.py`.
- Wired both `issuer_url=` and `resource_server_url=` in the `AuthSettings(...)` call to `settings.MCP_BASE_URL` (`settings` was already imported from `..config`).
- Preserved the metadata-only comment intent and left the `MCP_DNS_REBINDING_PROTECTION` logic untouched (Phase 66 scope).

### Task 2 — .env.example documentation + verify-only confirmations (commit 8fa0538)
- Added `MCP_BASE_URL=http://localhost:8001` with a metadata-only comment to `backend/.env.example.txt`, grouped under the Server section.
- VERIFIED (no change): `config.py` reads `ALLOWED_ORIGINS` as a `List[str]` env field with localhost default; the production localhost check at `__init__` is `logger.warning(...)` (line 120), not a raise — left intact per D-09.
- VERIFIED (no change): `docker-compose.yml` interpolates `ALLOWED_ORIGINS` with a localhost default (line 27) and sets `VITE_API_URL=/api` (line 44).
- VERIFIED (no change): `frontend/src/lib/constants.ts` line 7 uses `import.meta.env.VITE_API_URL || '/api'`.

## Verification Results

- `python -c "...config..."` → `settings.MCP_BASE_URL` == `http://localhost:8001` ✓
- `grep -v '^#' backend/app/mcp_server/server.py | grep -c '"http://localhost:8001"'` → `0` (no hardcoded URL literal in code) ✓
- `grep "MCP_BASE_URL" backend/.env.example.txt` → returns the documented line ✓
- `grep -c "import.meta.env.VITE_API_URL || '/api'" frontend/src/lib/constants.ts` → `1` (unchanged) ✓
- `settings.MCP_BASE_URL` appears twice in `server.py` (issuer_url + resource_server_url); `_BASE_URL` constant assignment removed ✓

### Verification environment note
The plan's `import app.main` smoke test could not be executed in this worktree: (1) the project `venv` is gitignored and not present in the worktree (only in the main checkout), and (2) an unrelated global `app` package on this dev machine's site-packages shadows the backend's namespace `app` package (which has no `__init__.py`). Both are dev-machine/worktree artifacts, NOT code defects — in Docker (`PYTHONPATH=/app`) and the real venv the import path works. To verify correctness despite this, `config.py` was loaded directly via `importlib.util.spec_from_file_location` (confirming the field default loads) and all `server.py` / `.env.example.txt` criteria were confirmed via grep. Required dependencies (`pydantic_settings`, `mcp`, `fastapi`) are present in the global environment and import cleanly.

## Deviations from Plan

None — plan executed exactly as written. Both VERIFY-only items (ALLOWED_ORIGINS, VITE_API_URL) were confirmed already-correct with no source changes; the only file changes are the three specified in the plan frontmatter.

## Threat Surface

No new security-relevant surface introduced. `MCP_BASE_URL` is operator-controlled env metadata only (T-62-01/T-62-03 accepted in plan threat model); static-bearer auth in `ApiKeyTokenVerifier` is unchanged. ALLOWED_ORIGINS permissive-in-prod risk (T-62-02) remains accepted/deferred to Phase 66 per D-09 — no change made here.

## Known Stubs

None.

## Self-Check: PASSED
- FOUND: backend/app/config.py (MCP_BASE_URL field)
- FOUND: backend/app/mcp_server/server.py (settings.MCP_BASE_URL x2)
- FOUND: backend/.env.example.txt (MCP_BASE_URL= line)
- FOUND commit: 59168c2 (Task 1)
- FOUND commit: 8fa0538 (Task 2)
