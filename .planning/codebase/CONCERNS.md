# Codebase Concerns

**Analysis Date:** 2026-03-11

## Tech Debt

**Duplicate Migration Files:**
- Issue: Two conflicting migration files exist for the template system (`003_template_system.sql` and `003_templates_overhaul.sql`), both with identical naming prefix. Only one will execute depending on run order, leaving database schema potentially inconsistent.
- Files: `backend/migrations/003_template_system.sql`, `backend/migrations/003_templates_overhaul.sql`
- Impact: Database schema inconsistencies, failed deployments, unpredictable table structure
- Fix approach: Consolidate into a single migration file, rename the second to `004_template_system.sql`, test migration order

**Manual SQL Migrations Without Schema Management:**
- Issue: Database schema uses raw SQL migrations in `backend/migrations/` without Alembic or formal migration tool. Comment in `backend/app/db.py:26` indicates awareness of this limitation but no action taken.
- Files: `backend/app/db.py`, `backend/migrations/*.sql`
- Impact: No automatic rollback capability, difficult to track schema versions, team coordination issues on schema changes
- Fix approach: Adopt Alembic for Python-based migration management with versioning

**Broad Exception Handling:**
- Issue: Many services use bare `except Exception as e:` blocks without specific error types, making debugging and error recovery difficult. Examples in `backend/app/services/openai_service.py:103`, `backend/app/services/agent_service.py:333`, `backend/app/services/template_ai_service.py:125` and many others.
- Files: `backend/app/services/openai_service.py:103`, `backend/app/services/agent_service.py:333`, `backend/app/services/template_ai_service.py:125`, `backend/app/services/knowledge_extraction_service.py:44,98,151,200,254`, `backend/app/api/endpoints/ai_chat.py:430,449,600,616,1100`, `backend/app/api/endpoints/chat.py:209,228`
- Impact: Exceptions are silently caught and generic fallback responses returned. Real errors buried. Production debugging nearly impossible.
- Fix approach: Replace with specific exception types (e.g., `except json.JSONDecodeError`, `except ValueError`, `except AIProviderError`). Re-raise or log with context.

**In-Memory Rate Limiting:**
- Issue: RateLimitMiddleware (`backend/app/middleware.py:89-132`) stores request history in memory without bounds. In production with sustained traffic, `self.requests` dict grows unbounded and never shrinks beyond the 60-second window cleanup.
- Files: `backend/app/middleware.py:95-108`
- Impact: Memory leak. High-traffic deployments will exhaust heap memory over hours/days. Rate limit becomes ineffective.
- Fix approach: Use Redis for distributed rate limiting, or add max bucket size with overflow eviction

**Unvalidated JSON Parsing:**
- Issue: 14+ instances of `json.loads()` without try/catch or validation (e.g., `backend/app/services/agent_service.py`, `backend/app/services/template_ai_service.py`, `backend/app/services/openai_service.py:87`). If AI response is malformed, entire endpoint crashes without graceful fallback.
- Files: `backend/app/services/agent_service.py`, `backend/app/services/template_ai_service.py:125,245,312,373,414,439,583,651,699`, `backend/app/services/openai_service.py:87`, `backend/app/services/knowledge_extraction_service.py:98`
- Impact: Crashes on malformed AI responses. User-facing 500 errors instead of fallback behavior.
- Fix approach: Wrap all JSON parsing in try/except blocks returning sensible defaults

**Mock Authentication Hardcoded:**
- Issue: Development mock auth token `"mock-token"` is hardcoded in production code path. `backend/app/api/dependencies.py:24` checks `if settings.ENVIRONMENT == "development"` to enable mock auth, but the string `'Bearer mock-token'` is also hardcoded in frontend (`frontend/src/lib/api.tsx:16`) as fallback, bypassing auth in production if token missing.
- Files: `backend/app/api/dependencies.py:24`, `frontend/src/lib/api.tsx:16`
- Impact: Production deployments without properly configured auth could allow unauthenticated access if client auth fails
- Fix approach: Remove mock token entirely from frontend fallback. Ensure production validation enforces valid JWT tokens.

## Known Bugs

**Print Statement Left in Production Code:**
- Symptom: Debug print statement outputs to stdout in API endpoint
- Files: `backend/app/api/endpoints/review.py`
- Location: Line with `print(f"Review error: {str(e)}")`
- Workaround: Logs will pollute stdout/container logs but requests still process
- Fix: Replace with `logger.error()` call

**Password field validation issue in schemas:**
- Symptom: `backend/app/models/schemas.py` lines 29, 48, 79 have empty `pass` statements in class bodies, suggesting incomplete schema definitions
- Files: `backend/app/models/schemas.py:29,48,79`
- Trigger: Schema validation or serialization of these objects
- Workaround: None currently visible — schemas may have incomplete validators
- Fix: Review and complete schema definitions

**CSP Headers Conflict with Development:**
- Symptom: `backend/app/middleware.py:62-67` sets `Content-Security-Policy` with `'unsafe-inline'` and `'unsafe-eval'` for development. These are overly permissive and conflict with production security requirements.
- Files: `backend/app/middleware.py:62-67`
- Impact: Headers are identical for all environments. Production deployments will have insecure CSP.
- Fix: Move CSP configuration to `config.py` with environment-specific policies

## Security Considerations

**Unencrypted Default Secret Key:**
- Risk: `backend/app/config.py:27` has default `SECRET_KEY = "your-secret-key-replace-in-production"`. Production validation (`backend/app/config.py:96-98`) will raise error if unchanged, but development environment silently accepts it.
- Files: `backend/app/config.py:27,96-98`
- Current mitigation: Production validation enforces change. Development allows default.
- Recommendations: Add pre-startup check that logs warning if SECRET_KEY matches default in any environment

**CORS Allows Localhost Wildcards:**
- Risk: `backend/app/config.py:30` includes `http://localhost:*` in ALLOWED_ORIGINS. If config is copied to staging, localhost remains accessible from outside network.
- Files: `backend/app/config.py:30`
- Current mitigation: Relies on environment variable override in deployment
- Recommendations: Add validation that rejects localhost origins in non-development environments

**AI Provider Keys in Environment:**
- Risk: `backend/app/config.py:19,23` loads OPENAI_API_KEY and ANTHROPIC_API_KEY from environment without encryption. If environment variables leak (container logs, error dumps), keys are exposed.
- Files: `backend/app/config.py:19,23`
- Current mitigation: None
- Recommendations: Use secrets management system (AWS Secrets Manager, HashiCorp Vault). Never log config values.

**No Input Sanitization on Frontend:**
- Risk: Frontend sends unsanitized user input to backend (e.g., in `frontend/src/lib/api.tsx` all POST bodies). Backend `backend/app/utils/validators.py` has HTML sanitization but it's not clear if all endpoints use it.
- Files: `frontend/src/lib/api.tsx`, `backend/app/utils/validators.py`
- Current mitigation: Pydantic v2 basic validation
- Recommendations: Audit all endpoints to ensure `sanitize_html()` is called on user-provided text fields

## Performance Bottlenecks

**Large AI Service Files:**
- Problem: `backend/app/api/endpoints/ai_chat.py` is 1,108 lines and `backend/app/services/template_ai_service.py` is 705 lines. Both contain multiple concerns (session management, message handling, prompting, streaming).
- Files: `backend/app/api/endpoints/ai_chat.py:1-1108`, `backend/app/services/template_ai_service.py:1-705`
- Cause: No separation of concerns. AI prompt building, API calls, database operations, streaming response handling all in single files.
- Improvement path: Split `template_ai_service.py` into: `prompt_builder.py` (strategy pattern), `streaming_handler.py`, `result_parser.py`. Extract session logic to dedicated service.

**In-Memory OpenAI Cache with No TTL Enforcement:**
- Problem: `backend/app/services/openai_service.py:17-18` implements LRU cache with max_cache_size=100 but no time-based expiration. Cache entries stay in memory indefinitely until evicted by size limit.
- Files: `backend/app/services/openai_service.py:17-99`
- Cause: OrderedDict-based cache doesn't check timestamp. Old entries served to users even if section content changed.
- Improvement path: Use `functools.lru_cache` with `@cache` decorator instead, or implement TTL check on retrieval (`backend/app/config.py:37` CACHE_TTL=900 is ignored)

**N+1 Query in Project Context Building:**
- Problem: `backend/app/api/endpoints/ai_chat.py:24-44` builds project context by querying ALL phase_data, then looping to fetch list_items. If project has many phases/subsections, this is O(n) database queries.
- Files: `backend/app/api/endpoints/ai_chat.py:26-28,38-41`
- Cause: Missing `.options(joinedload(...))` to eager-load relationships
- Improvement path: Use SQLAlchemy `joinedload('phase_data').joinedload('list_items')` to fetch in single query

**No Database Connection Pooling Limits:**
- Problem: `backend/app/db.py:6` creates SQLAlchemy engine without pool configuration. Under high concurrent load, connection pool grows unbounded and PostgreSQL max connections (default 100) is quickly exhausted.
- Files: `backend/app/db.py:6`
- Cause: Default pool_size=5, max_overflow=10 insufficient for production with multiple workers
- Improvement path: Set `pool_size=20, max_overflow=40, pool_recycle=3600` based on worker count and expected concurrency

## Fragile Areas

**AI Response Parsing Regex:**
- Files: `backend/app/services/agent_service.py:95-96`
- Why fragile: Complex regex `r'\{[^{}]*"field_updates"\s*:\s*\{.*?\}\s*\}'` with DOTALL flag is fragile to:
  - Nested JSON with multiple `{}` blocks (regex will match first complete outer block only, potentially truncating data)
  - AI returning slightly malformed JSON (extra spaces, different key order)
  - Edge case where field_updates is null or empty object
- Safe modification: Use JSON parsing with try/catch instead of regex extraction. Ask AI to always return `field_updates` as top-level key, validate with Pydantic schema.
- Test coverage: No tests visible for this parsing logic

**Template System Routing Without Type Checking:**
- Files: `backend/app/api/endpoints/ai_chat.py:43,50,54`, `backend/app/templates/__init__.py` (not read but referenced)
- Why fragile: Phase and subsection keys are strings with no enum validation. Template JSON has no schema validation. If template JSON structure changes, code breaks silently.
- Safe modification: Define Pydantic model for template structure. Validate on load in `backend/app/templates/__init__.py`. Return typed objects from `get_template()` instead of dicts.
- Test coverage: No visible tests for template loading or subsection lookup

**Frontend Auto-Save Timers Without Cleanup:**
- Files: `frontend/src/components/Patterns/WizardView.tsx`, `frontend/src/components/Patterns/CardGridView.tsx`, `frontend/src/components/Patterns/StructuredFormView.tsx`, `frontend/src/components/Patterns/IndividualEditorView.tsx`
- Why fragile: Multiple setTimeout/setInterval calls for auto-save without visible cleanup on component unmount. Can lead to:
  - Saves firing after component destroyed (race condition)
  - Memory leaks from lingering timers
  - Multiple saves queued if user rapidly changes fields
- Safe modification: Always clear timers in useEffect cleanup functions. Use useRef to track timer IDs. Test unmount scenarios.
- Test coverage: No tests visible for cleanup behavior

**Response Streaming Without Backpressure Handling:**
- Files: `frontend/src/lib/api.tsx:352-405`, `backend/app/api/endpoints/ai_chat.py` (streaming endpoints)
- Why fragile: Frontend reads response stream with `reader.read()` in tight loop without checking if data can be consumed (backpressure). If client network is slow:
  - Response body buffer fills up
  - Server waits for client to drain
  - Timeout fires (CHAT_TIMEOUT=30s) and request aborts mid-stream
- Safe modification: Implement exponential backoff in stream read loop. Add metric for bytes buffered. Consider reducing CHAT_TIMEOUT for streaming responses.
- Test coverage: No visible load/streaming tests

## Scaling Limits

**SQLAlchemy Session Not Thread-Safe:**
- Current capacity: Single worker/thread
- Limit: Multiple FastAPI workers (uvicorn --workers=4) will fail because SQLAlchemy SessionLocal is not thread-safe by default
- Scaling path: Either (a) ensure each worker thread has its own SessionLocal (already done via dependency injection), (b) use thread pool with thread-local sessions, or (c) switch to async-safe database driver (asyncpg instead of psycopg2)

**Synchronous Database Calls Blocking Event Loop:**
- Current capacity: <10 concurrent AI requests before event loop blocks
- Limit: Any long-running query blocks all other async operations. PostgreSQL query timeouts not set.
- Scaling path: Migrate to async SQLAlchemy (sqlalchemy+asyncpg) or use thread pool for sync operations

**Fixed Rate Limit Per IP:**
- Current capacity: 600 requests/minute (line 44 in main.py, set generously for dev)
- Limit: No differentiation by endpoint. AI endpoints should have lower limits. Broadcast endpoints need higher limits.
- Scaling path: Implement per-endpoint rate limiting. Track API cost (token usage for AI calls) not just request count.

**No Caching Layer for Template Configs:**
- Current capacity: Every template load calls `get_template()` which likely reads from disk/database
- Limit: High-traffic scenarios reload same templates repeatedly
- Scaling path: Cache template configs in memory with 1-hour TTL. Invalidate on template updates.

## Dependencies at Risk

**Pydantic v2 Migration Incomplete:**
- Risk: `backend/requirements.txt:5` pins `pydantic[email]>=2.10` but code uses both `pydantic.v1` (if imported) and new v2 APIs. Frontend has no type validation layer — Pydantic is backend-only.
- Impact: If codebase is forced to use older Pydantic (e.g., dependency conflict), validation breaks. No runtime schema validation on frontend.
- Migration plan: Audit all imports to ensure v2 APIs only. Add `json_schema_extra` decorators to schemas for better API docs.

**OpenAI SDK Version Pinned Narrowly:**
- Risk: `backend/requirements.txt:9` pins `openai==1.12.0`. Future versions may change API. Also supporting Anthropic with `anthropic>=0.39.0` (loose bound).
- Impact: OpenAI updates require code changes. Anthropic version mismatch can introduce bugs.
- Migration plan: Loosen bounds to `openai>=1.12,<2.0` and `anthropic>=0.39,<1.0`. Pin exact versions only in lock files.

**FastAPI Async Compatibility Risk:**
- Risk: Some middleware (e.g., `backend/app/middleware.py:LoggingMiddleware`) uses async/await. If any dependency is not async-safe, the entire stack blocks.
- Impact: Slow requests block event loop. App becomes unresponsive.
- Migration plan: Audit all dependencies for async safety. Use `asyncio.to_thread()` for sync operations.

**pgvector Version May Conflict:**
- Risk: `backend/requirements.txt:16` uses `pgvector==0.3.6`. Custom `SafeVector` type in `backend/app/models/database.py:12-46` wraps pgvector's behavior. If pgvector API changes, custom type breaks.
- Impact: Vector operations fail. Knowledge graph searches return errors.
- Migration plan: Version lock pgvector. Add tests for vector serialization/deserialization edge cases.

## Missing Critical Features

**No API Documentation for New Endpoints:**
- Problem: New endpoints added for template system (`/api/ai/*`, `/api/templates/*`, `/api/wizards/*`) but no OpenAPI/Swagger documentation visible
- Blocks: Client library generation, integration testing, external API consumers
- Fix: Add response_model to all endpoints. Run `fastapi.openapi.utils.get_openapi()` to verify schema completeness.

**No Error Recovery Strategy:**
- Problem: If AI API call fails (timeout, rate limit, 500 error), no retry mechanism exists. Request fails immediately.
- Blocks: Production reliability. Transient failures cause user-visible errors.
- Fix: Implement exponential backoff retry decorator with max attempts=3, backoff multiplier=2.

**No Data Retention Policy:**
- Problem: Chat messages, wizard runs, AI sessions accumulate indefinitely in database. No archival or deletion policy.
- Blocks: Compliance (GDPR right to be forgotten), database growth unbounded
- Fix: Add data retention settings to config. Implement cron job to soft-delete old records.

## Test Coverage Gaps

**AI Streaming Response Handling Untested:**
- What's not tested: Frontend streaming decoders for `data:` events. Backend streaming response generators.
- Files: `frontend/src/lib/api.tsx:352-405,582-638`, `backend/app/api/endpoints/ai_chat.py` (streaming endpoints)
- Risk: Malformed AI responses, network interruptions mid-stream not caught until production
- Priority: High — streaming is core feature, users see failures directly

**Database Migration Compatibility Untested:**
- What's not tested: Running migrations in order. Rolling back migrations. Data integrity after migrations.
- Files: `backend/migrations/*.sql`
- Risk: Duplicate migration files cause schema mismatches. No way to test before deploying to production.
- Priority: High — affects all deployments

**Frontend Error Boundary Coverage:**
- What's not tested: Component failures, API errors, timeout handling in UI
- Files: `frontend/src/App.tsx`, all route components
- Risk: Unhandled promise rejections, blank screens, no error message to users
- Priority: Medium — affects UX but not data integrity

**Rate Limiting Under Load:**
- What's not tested: RateLimitMiddleware behavior under sustained high traffic (memory leak, effectiveness)
- Files: `backend/app/middleware.py:89-132`
- Risk: Rate limiter becomes ineffective or crashes server under DDoS
- Priority: Medium — production resilience

**Template System Edge Cases:**
- What's not tested: Missing phases, unknown field types, null/empty content, subsection lookup failures
- Files: `backend/app/templates/`, `backend/app/api/endpoints/ai_chat.py:47-55`
- Risk: Uncaught KeyError or AttributeError in template processing
- Priority: Medium — affects template-based workflows

---

*Concerns audit: 2026-03-11*
