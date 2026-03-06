# Codebase Concerns

**Analysis Date:** 2026-03-06

## Tech Debt

**Mock Authentication in Production Path:**
- Issue: `get_current_user` in `backend/app/api/dependencies.py` returns a hardcoded mock user object even for valid JWT tokens (lines 38–42). The "production authentication flow" verifies the token but still returns `email="user@example.com"` and `created_at=datetime.utcnow()` rather than querying the real user from the database. The comment explicitly says "In production, you would query the user from database here — For MVP, return mock user".
- Files: `backend/app/api/dependencies.py`
- Impact: All authenticated requests share the same user identity data (email, created_at). Row-level security based on `owner_id` still works (UUID comes from the token), but user profile data is permanently fake.
- Fix approach: Add a `users` table, query it in `get_current_user` after token verification.

**No Database Migration Tool:**
- Issue: Migrations are plain SQL files with no tracking mechanism (no Alembic, no version table). Two conflicting `003_*.sql` files exist (`003_template_system.sql` and `003_templates_overhaul.sql`). There is no way to determine which migrations have been applied to a given database.
- Files: `backend/migrations/` (8 raw SQL files), `backend/app/db.py` (comment on line 25 acknowledges this)
- Impact: Database drift between environments is undetectable. Deploying to a new environment requires manually running files in the correct order. The duplicate `003_` files will cause errors or no-ops depending on execution order.
- Fix approach: Adopt Alembic with `alembic init`, convert existing SQL migrations to Alembic `upgrade`/`downgrade` pairs.

**Background Task Receives Request-Scoped DB Session:**
- Issue: `upload_book` in `backend/app/api/endpoints/books.py` passes the FastAPI-injected `db` session directly to a `BackgroundTask` (line 90). The request-scoped session is closed when the HTTP response is sent, but the background task continues to use it — this is a known pattern that causes "session closed" errors or silent data corruption.
- Files: `backend/app/api/endpoints/books.py` (lines 86–91), `backend/app/services/book_processing_service.py`
- Impact: `process_book` (the upload path) runs with a potentially closed/invalid session. The `resume_book` and `retry_book` paths correctly create their own sessions via `SessionLocal()` but `process_book` does not.
- Fix approach: Remove `db` from the `background_tasks.add_task` call in `upload_book`. Have `process_book` create its own session internally using `SessionLocal()` like `resume_book` does.

**Deprecated FastAPI Lifecycle Hooks:**
- Issue: `backend/app/main.py` uses `@app.on_event("startup")` and `@app.on_event("shutdown")` (lines 101, 109), which are deprecated in FastAPI >= 0.93 in favour of the `lifespan` context manager.
- Files: `backend/app/main.py`
- Impact: Will trigger deprecation warnings; these handlers may be removed in a future FastAPI version.
- Fix approach: Replace with `@asynccontextmanager` lifespan pattern and pass to `FastAPI(lifespan=lifespan)`.

**Duplicated System Prompt Construction:**
- Issue: The system prompt for book-based chat is built identically in both `chat` (non-streaming) and `chat_stream_prepare` (streaming) methods in `backend/app/services/agent_service.py`. Approximately 50 lines of f-string prompt construction are copy-pasted between them (lines ~387–410 and ~528–551).
- Files: `backend/app/services/agent_service.py`
- Impact: Any change to chat prompt logic must be applied in two places. The `chat` method also lacks the `list_creates_prompt` injection that `chat_stream_prepare` has (lines 582–583), creating a behavioural divergence between streaming and non-streaming modes.
- Fix approach: Extract prompt construction to a `_build_chat_system_prompt` helper method. Remove non-streaming `chat` if streaming is the canonical path.

**Hard-coded Quality Threshold as Local Variable:**
- Issue: `QUALITY_THRESHOLD = 0.5` is defined as a local variable inside `process_book` in `backend/app/services/book_processing_service.py` (line 145) rather than as a config setting.
- Files: `backend/app/services/book_processing_service.py`
- Impact: Changing the threshold requires a code deploy. The value is also referenced independently in `rag_service.py` (line 320).
- Fix approach: Add `CONCEPT_QUALITY_THRESHOLD: float = 0.5` to `backend/app/config.py` and reference `settings.CONCEPT_QUALITY_THRESHOLD` in both locations.

---

## Security Considerations

**Unsanitized Filename in File Upload:**
- Risk: `backend/app/api/endpoints/books.py` uses `file.filename` directly for the saved file path (line 67: `file_path = os.path.join(upload_dir, file.filename)`). A malicious client could supply a filename like `../../etc/cron.d/evil` to write files outside the upload directory (path traversal).
- Files: `backend/app/api/endpoints/books.py`
- Current mitigation: None. `os.path.join` does not prevent `..` traversal when the second argument starts with a relative path.
- Recommendations: Use `werkzeug.utils.secure_filename` or validate with `pathlib.Path(upload_dir, file.filename).resolve()` and assert it is within the upload directory. Add UUID prefix to filenames to avoid collisions.

**Development CSP Deployed to Production:**
- Risk: `SecurityMiddleware` in `backend/app/middleware.py` applies `'unsafe-inline'` and `'unsafe-eval'` in its CSP header unconditionally (lines 65–66). The comment says "More permissive CSP for development" but there is no environment-conditional logic — the same permissive policy applies in production.
- Files: `backend/app/middleware.py`
- Current mitigation: None.
- Recommendations: Branch on `settings.ENVIRONMENT`: use strict CSP (nonces, no unsafe directives) in production and the permissive policy only in development.

**Mock Token Endpoint Reachable in Any Environment:**
- Risk: `POST /api/auth/token/mock` in `backend/app/api/endpoints/auth.py` is registered unconditionally. The endpoint itself adds no guard. If `ENVIRONMENT` is misconfigured, the mock token endpoint is publicly accessible in production.
- Files: `backend/app/api/endpoints/auth.py`, `backend/app/api/dependencies.py`
- Current mitigation: `get_current_user` refuses `mock-token` in non-development environments, but the endpoint itself still responds.
- Recommendations: Add a startup guard that raises an error or removes the route when `ENVIRONMENT != "development"`.

**Rate Limit Set to 600 req/min:**
- Risk: `backend/app/main.py` sets `requests_per_minute=600` (line 44) with a comment "Rate limit generous for dev; tighten for production". This value has not been reduced. In-memory rate limiting does not survive restarts and is not shared across multiple workers.
- Files: `backend/app/main.py`, `backend/app/middleware.py`
- Current mitigation: None.
- Recommendations: Set rate limit via `settings.RATE_LIMIT_RPM`. Replace in-memory dict with Redis-backed sliding window for multi-worker deployments.

---

## Performance Bottlenecks

**N+1 Query in `get_concept_relationships`:**
- Problem: For each `ConceptRelationship` returned, the function issues two individual `db.query(Concept).filter(...)` calls to resolve source and target concept names (lines 100–101 in `backend/app/services/rag_service.py`).
- Files: `backend/app/services/rag_service.py`
- Cause: No JOIN or batch load. For a section with 10 concepts and 5 relationships each, this issues 100 individual queries.
- Improvement path: Use a JOIN in the `ConceptRelationship` query, or pre-load all relevant concepts in a single `WHERE id IN (...)` query before iterating.

**Full Table Scan on Concept Relevance Scoring:**
- Problem: `get_relevant_concepts` in `backend/app/services/rag_service.py` loads ALL concepts for an agent's books into Python memory (line 52: `.all()`) and sorts in-application code.
- Files: `backend/app/services/rag_service.py`
- Cause: No database-level ordering by `section_relevance`; the JSONB field could be queried as `(section_relevance->>:section_key)::float`.
- Improvement path: Push relevance scoring and ordering to SQL, apply `LIMIT` at the database level.

**In-Memory Caches Do Not Survive Restarts:**
- Problem: `OpenAIService` and `EmbeddingService` use in-memory `OrderedDict` LRU caches. Every restart causes a cold cache and re-costs API calls.
- Files: `backend/app/services/openai_service.py` (lines 17–18), `backend/app/services/embedding_service.py` (lines 19–20)
- Cause: MVP design choice; no external cache layer.
- Improvement path: Add Redis or a persistent cache (e.g. `diskcache`) for embedding results; review caches are cheap to regenerate.

**Sequential Chapter Processing During Book Upload:**
- Problem: `process_book` in `backend/app/services/book_processing_service.py` processes chapters sequentially in a `for` loop (line 110), with multiple AI calls per chapter through `knowledge_extraction_service`.
- Files: `backend/app/services/book_processing_service.py`
- Cause: Sequential by design to support checkpoint-based pause/resume.
- Improvement path: Consider small-batch parallelism (e.g. `asyncio.gather` over windows of 3–5 chapters) while preserving checkpoint granularity.

---

## Fragile Areas

**`_active_tasks` Module-Level Dict in Book Processing:**
- Files: `backend/app/services/book_processing_service.py`
- Why fragile: `_active_tasks: Dict[str, asyncio.Task]` is a module-level global (line 20). In a multi-worker deployment (e.g. Gunicorn with multiple workers), tasks are tracked per-process. Cancelling a task from worker B when it was started by worker A will silently fail — `_active_tasks.get(book_id)` returns `None` and `pause_book` returns `False`, leaving the book status unchanged.
- Safe modification: Only modify inside `BookProcessingService` methods. Do not reference `_active_tasks` from other modules.
- Test coverage: No test covers pause/resume across worker boundaries.

**Regex-Based JSON Extraction from AI Output:**
- Files: `backend/app/services/agent_service.py` (`_extract_book_refs`, `_extract_field_updates`, `_extract_list_item_creates`)
- Why fragile: All three methods use `re.search` with `re.DOTALL` to find embedded JSON blobs in free-text AI output. The patterns (`\{[^{}]*"key"\s*:.*?\}`) do not handle nested JSON or values containing `{}` or `[]`. A concept name containing braces will break the match silently.
- Safe modification: Use `json.decoder.JSONDecoder.raw_decode` for position-aware parsing, or constrain AI output structure (always last line, delimited).
- Test coverage: Minimal unit tests for these extraction functions.

**`agent_service.py` at 1066 Lines (Single Class):**
- Files: `backend/app/services/agent_service.py`
- Why fragile: The file contains review mode, chat mode (streaming and non-streaming), orchestrator mode, agent scoring, and list item creation in a single 1066-line class. Changes in one path routinely affect others; the duplication between streaming/non-streaming makes it easy to create diverging behaviour without noticing.
- Safe modification: Extract `_orchestrate` and `_orchestrate_stream_prepare` to a separate `OrchestratorService`. Extract prompt-building helpers to a `PromptBuilder` utility.
- Test coverage: No dedicated unit tests for `AgentService`.

**Template Registry Cache Is Process-Local:**
- Files: `backend/app/templates/registry.py`
- Why fragile: `_cache: Dict[str, dict]` at module level loads JSON template files once per process (line 7). If template files are updated on disk during a rolling deployment, running workers will continue to serve the old cached config until restarted.
- Safe modification: Add a cache-invalidation mechanism or simply remove the cache (templates are small JSON files — disk I/O cost is negligible).
- Test coverage: Not directly tested.

---

## Known Bugs

**Book Upload DB Session Used After Request Completes:**
- Symptoms: Sporadic `sqlalchemy.exc.InvalidRequestError: Session is closed` or `DetachedInstanceError` errors logged during book processing after upload.
- Files: `backend/app/api/endpoints/books.py` (line 90), `backend/app/services/book_processing_service.py`
- Trigger: Upload a book; the background task may attempt DB writes after the HTTP response has been sent and the session has been closed by the FastAPI dependency lifecycle.
- Workaround: None currently. `resume_book` and `retry_book` avoid this bug by creating a fresh session internally.

**Duplicate `003_` Migration Files:**
- Symptoms: Running `003_templates_overhaul.sql` on a database that has `003_template_system.sql` applied will fail with `ERROR: type "template_type" already exists` (no `IF NOT EXISTS` guard in the overhaul file).
- Files: `backend/migrations/003_template_system.sql`, `backend/migrations/003_templates_overhaul.sql`
- Trigger: Initialising a fresh database and running both files, or running the overhaul file on an already-migrated database.
- Workaround: Run only `003_template_system.sql`; it has `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object` guards.

**Naive `datetime.utcnow()` in Auth Service:**
- Symptoms: JWT token `exp` claims and `User.created_at` fields use timezone-naive datetimes (deprecated in Python 3.12+; raises `DeprecationWarning`).
- Files: `backend/app/services/auth_service.py` (lines 34, 36, 58, 78, 94), `backend/app/api/dependencies.py` (line 41)
- Trigger: Any request that creates or validates a token.
- Workaround: None currently; will become an error in a future Python release.
- Fix: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`.

---

## Test Coverage Gaps

**No Tests for Agent Service Core Logic:**
- What's not tested: `AgentService.review_section`, `AgentService.chat`, `AgentService.chat_stream_prepare`, `_orchestrate`, agent scoring, `_extract_field_updates`, `_extract_book_refs`, `_extract_list_item_creates`.
- Files: `backend/app/services/agent_service.py`, `backend/app/tests/`
- Risk: Changes to prompt construction, orchestration logic, or JSON extraction silently break agent behaviour.
- Priority: High

**No Tests for Template AI Service:**
- What's not tested: All wizard generation methods (`_generate_idea`, `_generate_episodes`, `_generate_scenes`, `_generate_beats`, `_generate_scripts`), `fill_blanks`, `give_notes`, `analyze_structure`, `chat_action_extract_updates`.
- Files: `backend/app/services/template_ai_service.py`, `backend/app/tests/`
- Risk: Regression in AI-driven feature generation goes undetected until user-facing.
- Priority: High

**No Tests for Book Processing Pipeline:**
- What's not tested: `BookProcessingService.process_book`, pause/resume/retry flows, quality filtering, concept-chunk linking, `_active_tasks` management.
- Files: `backend/app/services/book_processing_service.py`, `backend/app/tests/`
- Risk: The longest-running server operation has no automated regression protection.
- Priority: High

**No Frontend Tests:**
- What's not tested: All React components and hooks. Zero test files exist under `frontend/src/`.
- Files: `frontend/src/`
- Risk: UI behaviour changes and regressions are only caught manually.
- Priority: Medium

---

## Scaling Limits

**In-Memory Rate Limiter:**
- Current capacity: Single process; state lost on restart.
- Limit: Does not work correctly with multiple Gunicorn workers — each worker has its own counter, so the effective limit is `workers x 600` req/min per IP.
- Scaling path: Replace `RateLimitMiddleware` with Redis-backed sliding window (e.g. `slowapi` with Redis backend).

**File Storage on Local Disk:**
- Current capacity: Files saved to `backend/uploads/{user_id}/{filename}`.
- Limit: Does not work in containerised multi-replica deployments; uploaded books are unavailable on replicas that did not handle the upload request.
- Scaling path: Move uploads to object storage (S3, GCS) and store a URL or key reference in the `Book.filename` column.

---

## Dependencies at Risk

**`tiktoken` Hardcoded to GPT-4 Encoding:**
- Risk: `backend/app/api/endpoints/snippet_manager.py` calls `tiktoken.encoding_for_model("gpt-4")` hardcoded (line 27). If the project switches to a model with a different tokenizer, token counts will be silently wrong.
- Files: `backend/app/api/endpoints/snippet_manager.py`
- Impact: Incorrect token counts displayed to the user; could affect RAG context window sizing.
- Migration plan: Use a fixed tokenizer encoding like `cl100k_base` or derive from `settings.OPENAI_MODEL`.

**`declarative_base()` Deprecated in SQLAlchemy 2.x:**
- Risk: `backend/app/models/database.py` uses `from sqlalchemy.ext.declarative import declarative_base` (line 6), which is the SQLAlchemy 1.x import path. SQLAlchemy 2.x moves this to `sqlalchemy.orm.DeclarativeBase`.
- Files: `backend/app/models/database.py`
- Impact: Produces deprecation warnings; import path may be removed in future SQLAlchemy releases.
- Migration plan: Replace with `from sqlalchemy.orm import DeclarativeBase` and update `Base = DeclarativeBase()`.

---

*Concerns audit: 2026-03-06*
