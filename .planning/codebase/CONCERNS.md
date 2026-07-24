# Codebase Concerns

**Analysis Date:** 2026-07-24

Full-stack screenwriting + production-breakdown assistant (React/Vite frontend, FastAPI/PostgreSQL backend, OpenAI/Anthropic AI). This document catalogs technical debt, risks, fragile areas, and scaling limits. It is an internal-tool audit — market/multi-tenant concerns are deliberately out of scope; the focus is script-writing and breakdown quality plus operational safety on the current Railway/Vercel deploy.

## Tech Debt

**Mock auth still wired into the request path (dev-gated):**
- Issue: `authenticate_token` and `validate_token` special-case the literal token `"mock-token"` and return a hardcoded user (UUID `12345678-...`) whenever `settings.ENVIRONMENT == "development"`. Real JWT + `sa_` API-key auth exist and are the production path, but the mock branch and `MockAuthService` remain in the codebase.
- Files: `backend/app/services/auth_service.py` (`MockAuthService`, `generate_mock_token`), `backend/app/api/dependencies.py:33` and `:124`
- Impact: If `ENVIRONMENT` is ever misconfigured to `development` in a public deploy, every request authenticates as the single mock owner — full data exposure. The whole test suite also depends on `Bearer mock-token`, so the branch cannot be deleted without reworking tests.
- Fix approach: Keep the env gate but add a startup assertion that refuses to boot with `ENVIRONMENT=development` when `DATABASE_URL` points at a managed/prod host; consider a dedicated `ALLOW_MOCK_AUTH` flag independent of `ENVIRONMENT` so tests and prod-safety are decoupled.

**Hardcoded localhost in production security headers (CSP):**
- Issue: `SecurityMiddleware` emits a static `Content-Security-Policy` that whitelists `http://localhost:4321` and `http://localhost:8000` and allows `'unsafe-inline'`/`'unsafe-eval'` for scripts. It is not derived from `ALLOWED_ORIGINS` or environment.
- Files: `backend/app/middleware.py:69-75`
- Impact: The CSP is meaningless/incorrect in production (points at localhost) and permissive (`unsafe-eval`). It provides no real XSS mitigation for the deployed app.
- Fix approach: Build the CSP from `settings.ALLOWED_ORIGINS` and drop `unsafe-eval`; skip or relax only in development.

**Growing service surface (26 service modules, several very large):**
- Issue: `backend/app/services/` now holds 26 modules. The largest single files in the codebase are services/endpoints, not tests: `template_ai_service.py` (1654 lines), `agent_service.py` (1203), `ai_chat.py` endpoint (1190), `schemas.py` (1183), `wizards.py` endpoint (847), `breakdown_service.py` (622), `vapai_service.py` (584).
- Files: `backend/app/services/template_ai_service.py`, `backend/app/services/agent_service.py`, `backend/app/api/endpoints/ai_chat.py`, `backend/app/api/endpoints/wizards.py`
- Impact: These files concentrate prompt-building, DB access, and orchestration in single modules, making them hard to test in isolation and easy to break during edits. No clear internal seams.
- Fix approach: Extract prompt templates and pure transforms out of the large AI services into smaller, unit-testable helpers; split `ai_chat.py`/`wizards.py` by concern (scene regen, keep-version, persistence).

**Frontend `api.tsx` is a 1650-line monolith:**
- Files: `frontend/src/lib/api.tsx`
- Impact: Every backend call funnels through one file; a single fetch-wrapper change touches everything. Hard to reason about which endpoints exist.
- Fix approach: Split per-domain API modules (projects, breakdown, shows, chat) sharing one fetch core.

**`print()` for error logging in review endpoint:**
- Files: `backend/app/api/endpoints/review.py:76` (`print(f"Review error: {str(e)}")`)
- Impact: Bypasses the structured logger; error not captured consistently in Railway logs.
- Fix approach: Replace with `logger.error(...)`.

## Known Bugs

**None confirmed at audit time.** No `TODO`/`FIXME`/`HACK` markers exist in `backend/app` or `frontend/src` (all `placeholder` hits are UI input attributes). The fragile areas below are latent-bug risks rather than open defects.

## Security Considerations

**Default `SECRET_KEY` only warns in non-production:**
- Risk: JWT signing key defaults to `"your-secret-key-replace-in-production"`. Production boot hard-fails (`config.py:160`), but staging/development only log a warning, so JWTs can be forged with the well-known default outside prod.
- Files: `backend/app/config.py:27`, `:134-138`, `:159-161`
- Current mitigation: Production `__init__` raises if the default is unchanged.
- Recommendation: Also fail in `staging`; never allow the literal default when `DATABASE_URL` is non-local.

**Shared-secret bearer to vapai MCP + broad exception swallowing:**
- Risk: `vapai_service` authenticates to the external vapai-studio MCP with a single shared `VAPAI_MCP_API_KEY`. `json.JSONDecodeError` is silently `pass`ed while parsing MCP responses (`vapai_service.py:129`), and `ai_provider.py:183` swallows all exceptions in usage logging.
- Files: `backend/app/services/vapai_service.py:112-130`, `backend/app/services/ai_provider.py:178-184`
- Current mitigation: Feature is disabled when `VAPAI_MCP_URL` is empty (returns 424); downstream failures map to 502.
- Recommendation: Log the swallowed decode error at debug level; rotate the shared key; confirm the key is never echoed in 502 detail messages.

**CORS bound to an explicit origin list (deploy constraint, not a hole):**
- Risk: `ALLOWED_ORIGINS` is an explicit allowlist with `allow_credentials=True`. The deployed frontend lives at `guion.vapai.studio` (Vercel); any origin not listed fails with "Failed to fetch". This is correct security posture but a brittle operational coupling — a Vercel preview-URL or domain change silently breaks the app until `ALLOWED_ORIGINS` is updated on Railway.
- Files: `backend/app/main.py:110-117`, `backend/app/config.py:36`, `:162`
- Current mitigation: Production warns if `localhost` is in the list.
- Recommendation: Document the exact prod origin in deploy notes; consider a regex allow for Vercel preview domains if previews are used.

**Secrets handling — clean:**
- No `.env`/secret/key files are git-tracked; only `.env.docker.example`, `backend/.env.example.txt`, `frontend/.env.example.txt` are committed. All keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SECRET_KEY`, `VAPAI_MCP_API_KEY`, `GOOGLE_CLOUD_PROJECT`) load from env via Pydantic Settings. No inline secrets found.

## Performance Bottlenecks

**Synchronous single-scene regeneration can exceed API timeout:**
- Problem: `regenerate-single-scene` is a blocking LLM call (`max_tokens=4000`) with no background-task plumbing; the frontend must use a 120s timeout (CHAT_TIMEOUT) instead of the default 30s.
- Files: `backend/app/api/endpoints/wizards.py:716-771`, `frontend/src/lib/api.tsx`
- Cause: Deliberate design decision (D-49-02) to avoid background-job complexity for a single scene.
- Improvement path: Acceptable for one scene; if batch regen is added, move to a job/queue rather than lengthening HTTP timeouts.

**In-process book processing tasks tie long jobs to one worker:**
- Problem: Book ingestion (extract → chunk → embed → KG extract via GPT-4) runs as an `asyncio.Task` registered in a module-level `_active_tasks` dict inside the web process.
- Files: `backend/app/services/book_processing_service.py:20`, `:32-47`
- Cause: No external task queue; processing shares the API event loop and memory.
- Improvement path: Move to a dedicated worker/queue (the vapai prod side already runs a separate worker). At minimum, cap concurrency so a large upload can't starve request handling.

## Fragile Areas

**ScreenplayContent / screenplays[] ordering — the #1 recurring bug source:**
- Files: `backend/app/models/database.py:398-408` (`ScreenplayContent` has NO order column — only `list_item_id`, `created_at`, `version`), `backend/app/api/endpoints/wizards.py:725-847`, `backend/app/api/endpoints/phase_data.py:358`
- Why fragile: There is no reliable positional order for screenplay content rows. Regeneration can leave duplicate rows per episode, so `keep_scene_version` must locate the target by `formatted_content.episode_index`, falling back to reverse-index heuristics (`wizards.py:833-839`). The documented ALIGNMENT ASSUMPTION (D-49-03) is that `episode_index` indexes BOTH the `sort_order`-ordered scene list AND `screenplays[]` 1:1. This exact class of bug has bitten twice historically (v6.0 WR-01, v7.0 ph50 — see project memory).
- Safe modification: NEVER join screenplay content to episodes positionally. Always match on `episode_index` (from `formatted_content` or the sort_order-ordered list). Any new code that reads/writes `screenplays[]` or `ScreenplayContent` must bounds-check and match by index, never by array position or `created_at`.
- Test coverage: `test_scene_compare.py` covers compare/keep flows, but the duplicate-row-per-episode fallback path is heuristic and under-tested.

**Boot-time migration runner (`db_migrator.py`):**
- Files: `backend/app/services/db_migrator.py`, invoked via `init_db()` in the app lifespan (`backend/app/main.py:63-84`)
- Why fragile: All schema DDL runs on every app start, guarded by a single Postgres advisory lock (`MIGRATION_LOCK_KEY = 8273461928374651`) so overlapping Railway replicas serialize. A failing delta crashes boot loudly (intended fail-hard). Risks: (1) a long-running migration blocks all replicas behind the advisory lock during a rolling deploy; (2) a non-idempotent delta that half-applies before commit will retry-fail every boot; (3) baseline detection keys off the `projects` table existing — a partially-created schema could misclassify as "fresh" and run `init_db.sql`.
- Safe modification: Every new `migrations/delta/NNN_*.sql` MUST be idempotent (`ADD COLUMN IF NOT EXISTS`, `ON CONFLICT DO NOTHING`) and small. Test locally against a copy before deploy. Do not reorder or renumber existing delta files.
- Test coverage: `backend/app/tests/test_db_migrator.py` exists; verify it covers the fresh-DB vs pre-tracking-baseline branches.

**In-memory caches and rate limiters (horizontal-scaling ceiling):**
- Files: `backend/app/middleware.py:108-214` (`RateLimitMiddleware.requests`, `ApiKeyRateLimitMiddleware.requests` — plain dicts), `backend/app/services/openai_service.py:17` (OrderedDict, max 100), `backend/app/services/embedding_service.py:23` (OrderedDict, max 500), `backend/app/services/template_ai_service.py` prompt/response caching
- Why fragile: All rate-limit state and AI-response/embedding caches live in a single process's memory. Correct for one Railway replica; the moment the app scales to 2+ instances, rate limits become per-instance (effectively N× the configured limit) and cache hit rates drop. The advisory-lock migration design anticipates multiple replicas, but the rate limiters do not.
- Safe modification: Treat single-replica as a hard assumption today. Before enabling horizontal scaling, move rate limiting and caches to Redis (or accept per-instance semantics explicitly).
- Note: A test-suite gotcha exists — new test files with several client POSTs can 429 unrelated later tests because rate-limit state is shared in-process; an autouse rate-limiter-reset fixture is required (project memory).

**vapai-studio MCP bridge coupling:**
- Files: `backend/app/services/vapai_service.py` (584 lines), config `VAPAI_MCP_URL`/`VAPAI_MCP_API_KEY`/`VAPAI_WEB_URL` in `backend/app/config.py:112-121`
- Why fragile: "Send to vapai-studio" pushes a finished screenplay into a SEPARATE production app (vapai-studio on Railway) over its FastMCP JSON-RPC HTTP endpoint, calling `create_project` → `create_episode` → `create_script`. This app hard-depends on vapai's tool names, argument shapes, and response envelope (it manually digs the object out of `tools/call` results at `vapai_service.py:111`). Any change on the vapai side (tool rename, arg change, auth rotation) silently breaks the bridge with a 502.
- Safe modification: Version or contract-test the MCP tool interface; keep the 424-when-unconfigured guard so a missing URL degrades gracefully rather than erroring. Do not assume `ScreenplayContent` order when assembling the per-episode payload — join by `episode_index`.
- Test coverage: No integration test can exercise the live vapai MCP; the bridge is only unit-tested against mocked responses.

**Local filesystem storage on an ephemeral host:**
- Files: `backend/app/config.py:84-85` (`UPLOAD_DIR`, `MEDIA_DIR` under the app dir), `backend/app/api/endpoints/books.py:75`, `media.py:71`, `storyboard.py:81`
- Why fragile: Uploaded books and generated media/storyboard frames are written to the container's local disk. On Railway, container filesystems are ephemeral unless a volume is mounted (phase 63 addressed the Postgres volume, but uploads/media persistence depends on the same volume being configured).
- Safe modification: Confirm a persistent volume backs `UPLOAD_DIR`/`MEDIA_DIR` in production, or move media to object storage before relying on it.

## Scaling Limits

**Single-replica assumption (rate limiting + caches):**
- Current capacity: Correct behavior at 1 web replica.
- Limit: Breaks at 2+ replicas — rate limits multiply per instance, caches fragment.
- Scaling path: Externalize rate-limit and cache state to Redis before scaling out.

**AI-bound throughput:**
- Current capacity: Request throughput is gated by upstream OpenAI/Anthropic latency and the in-process critique/rewrite/polish loop (`SCREENPLAY_CRITIQUE_ENABLED` trades ~3× tokens for quality).
- Limit: Concurrent heavy generations (full-screenplay polish, multi-agent review with `MAX_AGENTS_PER_REVIEW=5`, `AGENT_REVIEW_TIMEOUT=90`) compete for the same event loop and provider rate limits.
- Scaling path: Offload long generations to a worker; add per-provider concurrency caps.

## Dependencies at Risk

**Pinned/fragile Python toolchain (from project memory):**
- Risk: The backend test venv needs `mcp` installed to collect the full pytest suite, but installing it can bump `starlette` past the working pin — it must be re-pinned to `starlette<0.37`. Python 3.14 breaks SQLAlchemy/tiktoken; **use Python 3.11**.
- Impact: A missing `mcp` dep or wrong Python version blocks the ENTIRE test suite from collecting, not just MCP tests.
- Migration plan: Document the exact venv setup (python3.11, `mcp` installed, `starlette<0.37`) in backend README; consider a constraints file.

**Dual AI provider abstraction:**
- Risk: `AI_PROVIDER` toggles openai/anthropic (`config.py:15-24`); both SDKs are dependencies and both code paths must stay working. Model defaults (`claude-opus-4-8`, `gpt-4o`, `gpt-4` for KG extraction) are hardcoded defaults that drift as providers deprecate models.
- Files: `backend/app/services/ai_provider.py`, `backend/app/config.py:16-24`, `:69`
- Migration plan: Centralize model names in config (mostly done); add a smoke test per provider path.

## Missing Critical Features

**No production observability / error tracking:**
- Problem: Errors surface via `logging` (and one stray `print`). No Sentry/error-tracking integration was found.
- Blocks: Diagnosing the recurring ordering bugs and vapai-bridge 502s in production relies on scraping Railway logs.

**No CI-enforced frontend tests:**
- Problem: `find frontend/src -name "*.test.*"` returns zero test files. The frontend (18.5k lines, including the 1650-line `api.tsx` and complex scene/breakdown views) has no automated tests.
- Blocks: Regressions in the master-detail scene fusion, wizard flows, and breakdown UI can only be caught manually.

## Test Coverage Gaps

**Frontend — no tests at all:**
- What's not tested: Entire React app — `api.tsx` fetch wrapper, scene editor/compare, breakdown, shows/season-map, sidebar chat.
- Files: all of `frontend/src/`
- Risk: High. Silent UI regressions; the ordering contract (episode_index) is enforced on the backend but consumed positionally in many frontend list renders.
- Priority: High

**Backend — strong but heuristic paths under-covered:**
- What's not tested: The duplicate-ScreenplayContent-row fallback in `keep_scene_version` (`wizards.py:833-839`), the vapai bridge against a real MCP, and the db_migrator fresh-vs-baseline misclassification edge.
- Files: `backend/app/api/endpoints/wizards.py`, `backend/app/services/vapai_service.py`, `backend/app/services/db_migrator.py`
- Risk: Medium — 54 backend test files exist (`test_scene_compare.py`, `test_seasons_api.py`, `test_breakdown_*`, `test_db_migrator.py`, etc.), so happy paths are covered; the heuristic ordering fallbacks are the gap.
- Priority: Medium

---

*Concerns audit: 2026-07-24*
