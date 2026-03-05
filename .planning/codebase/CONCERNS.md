# Codebase Concerns

**Analysis Date:** 2026-03-05

## Tech Debt

**Hardcoded Mock Authentication in Production Path:**
- Issue: Development-only mock authentication is hardcoded into production code path. Setting `ENVIRONMENT=development` accepts any Bearer token of `"mock-token"`, but this logic exists in production-bound code, not isolated to dev-only modules.
- Files: `backend/app/api/dependencies.py:24`, `backend/app/config.py:93`
- Impact: If production is accidentally configured as `development`, all authentication can be bypassed. This is a critical security regression vector.
- Fix approach: Move mock auth entirely to a separate mock auth module that is not imported in production builds. Use environment-based feature flags only for logging/debug output, not authentication logic.

**Manual Migration Management Without Alembic:**
- Issue: Database schema is managed via raw SQL migration files in `backend/migrations/` rather than using Alembic. Migration ordering relies on filename conventions and manual execution. Multiple conflicting migration files exist (`003_templates_overhaul.sql` vs `003_template_system.sql`).
- Files: `backend/migrations/`, `backend/app/db.py:19-28`
- Impact: Risk of schema inconsistency if migrations are applied in wrong order. No rollback mechanism. Difficult to track which migrations have been run. Team coordination overhead.
- Fix approach: Adopt Alembic for deterministic, reversible migrations. Generate current schema from ORM models. Clear up conflicting migration files and establish naming convention.

**Rate Limit Stored in Memory:**
- Issue: In-memory rate limiting middleware stores IP request timestamps in a dictionary that only exists for the lifetime of the server process.
- Files: `backend/app/middleware.py:89-132`
- Impact: Rate limits reset on each server restart. In distributed deployments with multiple servers, each instance has independent rate limit state—users can bypass limits by distributing requests across servers. No persistent enforcement.
- Fix approach: Migrate to Redis-backed rate limiting (e.g., using `slowapi` or `redis-py`) for distributed, persistent rate limit tracking.

**Type Annotations Using `any` Throughout Frontend:**
- Issue: Widespread use of `any` type in TypeScript code instead of proper type definitions. Examples: `Record<string, any>`, `error: any`, `phaseData: any`, `project: any`.
- Files: `frontend/src/lib/api.tsx:350,363,428,435,510,520,548,558,631,643,690,705,722,739,760,785`, `frontend/src/types/template.ts:138-139,150-151,173,182-183`, `frontend/src/components/Patterns/WizardView.tsx:13`, `frontend/src/components/Projects/ProjectList.tsx:97-100`, `frontend/src/components/Patterns/RepeatableCardsView.tsx:31,39`
- Impact: Loss of type safety. Runtime bugs that could be caught at compile time. Hard to refactor, unclear data contracts. ESLint allows this currently (no `@typescript-eslint/no-explicit-any` rule).
- Fix approach: Enable `"@typescript-eslint/no-explicit-any": "error"` in ESLint config. Create proper types for all API responses and component props. Use `unknown` type with type guards where truly generic behavior is needed.

**Default Secrets in Config:**
- Issue: Default `SECRET_KEY = "your-secret-key-replace-in-production"` is hardcoded in config.
- Files: `backend/app/config.py:27`
- Impact: If env var is not set in production, the app uses a known default secret. JWT tokens could be forged. Database encryption (if added) would use weak default key.
- Fix approach: Raise `ValueError` at startup if `SECRET_KEY` is default in any non-development environment. Require explicit secret generation for production deploys.

**Unstructured Error Handling in Services:**
- Issue: Multiple services catch generic exceptions and either suppress them, return defaults, or log without propagating. Examples: `RateLimitError` caught and re-raised differently, `json.JSONDecodeError` caught with generic recovery in `template_ai_service.py:608`.
- Files: `backend/app/services/agent_service.py:106`, `backend/app/services/template_ai_service.py:608`, `backend/app/services/embedding_service.py:59`
- Impact: Errors are hidden from observability. Root causes become hard to diagnose. Callers don't know if a returned value is a real result or a fallback due to error.
- Fix approach: Create a custom exception hierarchy (`AIServiceError`, `ValidationError`, `ExternalServiceError`). Propagate specific exceptions to API layer. Log with full traceback. Return explicit error responses rather than silent defaults.

---

## Security Considerations

**File Upload Path Traversal Risk:**
- Risk: File upload endpoint constructs file path from user-provided filename without sanitization.
- Files: `backend/app/api/endpoints/books.py:67`
- Current mitigation: File extension is validated (.pdf, .epub, .txt only). Filename could still contain path traversal sequences like `"../../etc/passwd.pdf"`.
- Recommendations: Sanitize filename using `pathlib.Path(filename).name` or generate a UUID-based filename. Never trust user-provided filenames for path construction.

**localStorage Token Storage (Frontend):**
- Risk: Authentication token stored in `localStorage` is vulnerable to XSS attacks. Any injected JavaScript can access `localStorage`.
- Files: `frontend/src/lib/api.tsx:13`, `frontend/src/components/Shared/SidebarChat.tsx:153,157`, `frontend/src/components/UI/ResizablePanel.tsx:22,66`
- Current mitigation: CSP headers are set but include `'unsafe-inline'` and `'unsafe-eval'` in development (overly permissive).
- Recommendations: Move tokens to HTTPOnly secure cookies (requires backend integration). If localStorage is retained, implement strict CSP for production. Add XSS input validation across all user-controllable content.

**Permissive CORS Configuration:**
- Risk: CORS allows `*` methods and headers, and includes `http://localhost` origins in production config.
- Files: `backend/app/main.py:50-56`, `backend/app/middleware.py:62-67`
- Current mitigation: Origins list is checked, but localhost origins would be present if `ENVIRONMENT=production` incorrectly.
- Recommendations: Remove localhost from production origins. Use explicit header whitelists instead of `allow_headers=["*"]`. Set `allow_methods=["GET", "POST", "PATCH", "DELETE"]` explicitly.

**SQL Injection Risk in RAG Service:**
- Risk: `RAGService` uses `.filter(...in_(...))` safely with SQLAlchemy, but raw SQL queries via `sql_text()` are used. If any dynamic SQL is added, injection risk exists.
- Files: `backend/app/services/rag_service.py:6`, `backend/app/db.py:28`
- Current mitigation: Only static SQL queries are used in `db.py`.
- Recommendations: Never use string concatenation for SQL. Always use parameterized queries. Document that `sql_text()` must only be used with hardcoded queries.

**Weak Email Validation:**
- Risk: Regex-based email validation in `validators.py` is overly permissive and doesn't match RFC 5322.
- Files: `backend/app/utils/validators.py:10-13`
- Impact: Invalid emails could be accepted. Real-world emails (e.g., with `+` addressing) might be rejected.
- Recommendations: Use `email-validator` package for RFC-compliant validation. Or use built-in Pydantic `EmailStr` type.

---

## Performance Bottlenecks

**In-Memory Rate Limit Dictionary Growth:**
- Problem: `self.requests` dictionary in `RateLimitMiddleware` grows unbounded as new IPs make requests. Only cleaned when entries expire.
- Files: `backend/app/middleware.py:95,105-109`
- Cause: Cleanup only removes old entries during new requests from that IP. A single request from a new IP doesn't trigger full cleanup. Dictionary can grow to thousands of entries.
- Improvement path: Add periodic cleanup task (e.g., every 60 seconds). Or use `collections.defaultdict` with TTL-based expiration. Better: use Redis.

**Book Processing Without Batching:**
- Problem: `book_processing_service.process_book()` embeds entire document in single batch via `embedding_service.embed_batch()`. If book is 10,000+ chunks, this could timeout or exhaust memory.
- Files: `backend/app/services/book_processing_service.py:66-68`
- Cause: No pagination or streaming. All embeddings requested at once.
- Improvement path: Batch embeddings in chunks of 100-500. Implement resume logic to recover from mid-processing failures. Add progress updates per batch.

**Vector Search Without Indexing:**
- Problem: `RAGService.get_relevant_concepts()` loads all concepts from a book into memory, filters in Python. No database-level vector similarity search.
- Files: `backend/app/services/rag_service.py:48-62`
- Cause: pgvector is installed but not used for efficient `<->` similarity queries.
- Improvement path: Add database indexes on embeddings. Use pgvector's cosine distance operator for server-side filtering. Pagination with `LIMIT`.

**Unresolved API Query N+1 Problem:**
- Problem: Many endpoints may trigger multiple database queries in loops. Example: iterating over relationships and querying source/target concepts separately.
- Files: `backend/app/services/rag_service.py:99-100`
- Cause: Lazy loading of relationships. SQLAlchemy does not auto-eager-load related data.
- Improvement path: Use `joinedload()` to eager-load relationships. Profile with `sqlalchemy.event.listen()` to log SQL queries.

---

## Fragile Areas

**Database Cascade Delete Chains:**
- Files: `backend/app/models/database.py:92-93,106,139-140,173-174`
- Why fragile: Multiple models use `cascade="all, delete-orphan"`. If a Project is deleted, it cascades to Sections → ChecklistItems → (eventually) AIMessages, ChatMessages, etc. A bug in one delete handler could orphan dependent records.
- Safe modification: Always wrap bulk deletes in transaction with savepoint. Write explicit tests for cascade behavior. Consider soft-deletes (is_deleted flag) for non-ephemeral data.
- Test coverage: No explicit cascade delete tests in `backend/app/tests/`. Only basic CRUD tests exist.

**Template System JSON Fields:**
- Files: `backend/app/models/database.py:88,102,132-133,152-153,198,213`, `backend/app/api/endpoints/ai_chat.py:28-35`
- Why fragile: `content`, `ai_suggestions`, `config`, `result` are all JSON columns without schema validation. Code assumes certain keys exist (e.g., `pd.content['some_key']`) but doesn't enforce structure.
- Safe modification: Add Pydantic models for JSON schema. Validate on insert/update. Document expected structure. Use `field_validator` on schemas.
- Test coverage: Template system integration tests missing. Only shallow API tests exist.

**AI Service Prompt Injection Risk:**
- Files: `backend/app/services/agent_service.py:43-87,141-150`, `backend/app/services/template_ai_service.py`
- Why fragile: User text (`user_notes`, section content) is embedded directly into system prompts without escaping. A malicious user could inject prompt-breaking sequences like `\n\nIgnore previous instructions:`.
- Safe modification: Never interpolate user text directly. Use placeholders and structured formats. Separate user input from prompt structure.
- Test coverage: No adversarial prompt injection tests.

**Chat Session / Project Ownership Not Enforced:**
- Files: `backend/app/api/endpoints/chat.py`, `backend/app/api/endpoints/agents.py`
- Why fragile: Some endpoints check `project.owner_id == current_user.id` but not all. If an endpoint is added without this check, a user could access another user's data.
- Safe modification: Create a reusable dependency `async def verify_project_ownership()` that all endpoints use. Add tests that verify auth across all endpoints.
- Test coverage: No cross-user access tests. Tests use mock user only.

---

## Known Bugs

**Duplicate Migration Files:**
- Symptoms: Two `003_*.sql` files exist, creating ambiguity about which is the current schema.
- Files: `backend/migrations/003_template_system.sql`, `backend/migrations/003_templates_overhaul.sql`
- Trigger: Both were created during template system development without renaming one to `004_*.sql`.
- Workaround: Clear database and rerun all migrations in sequence. Developers must manually choose which `003_*.sql` to apply.

**Mock Auth Bypass:**
- Symptoms: In development mode, any request with `Authorization: Bearer mock-token` is accepted as valid.
- Files: `backend/app/api/dependencies.py:24`
- Trigger: Set `ENVIRONMENT=development` and send requests with mock token.
- Workaround: Use a separate test client with mock user, not real API.

**Missing Error Boundary in Frontend:**
- Symptoms: React uncaught errors crash the entire app without user-visible recovery.
- Files: `frontend/src/App.tsx`
- Trigger: Any unhandled promise rejection in components.
- Workaround: Manually reload page or restart dev server.

---

## Scaling Limits

**Single-Process Rate Limiting:**
- Current capacity: ~60-600 requests per minute per server instance (configurable).
- Limit: Across distributed deployments with N instances, limit is multiplied by N (each instance has independent state).
- Scaling path: Migrate to Redis-backed rate limiting. All instances check against shared Redis store.

**Book Embedding Pipeline Single-Threaded:**
- Current capacity: ~100 chunks per book (typical). Embedding 1000+ chunks takes 5+ minutes sequentially.
- Limit: If user uploads 10 large books simultaneously, system blocks on sequential embedding.
- Scaling path: Implement async task queue (Celery + Redis). Process multiple books in parallel. Add priority queue for user-initiated vs. background tasks.

**In-Memory Chunk Vectors:**
- Current capacity: All concept embeddings fit in server memory (assume <100 books × 1000 chunks × 1536 dims ≈ 150MB).
- Limit: Beyond 500+ books, RAM becomes constrained. Vector search becomes slow without proper indexing.
- Scaling path: Use pgvector extensions for on-disk vector storage. Add vector index (ivfflat or hnsw).

**API Rate Limit for AI Calls:**
- Current capacity: 600 requests/min. Each AI review call 1 request. Each chat message 1 request.
- Limit: Production API quotas from OpenAI/Anthropic are the real bottleneck (not app-level rate limit).
- Scaling path: Implement token-bucket rate limiting per user (not global). Queue AI calls. Cache responses.

---

## Dependencies at Risk

**Pydantic v2 Compatibility:**
- Risk: Some type hints use old Pydantic v1 patterns. `pydantic-settings` requires explicit `BaseSettings` setup. Code uses `@field_validator` (v2) but some older code might expect `@validator` (v1).
- Impact: Subtle type coercion bugs. Validation might not trigger as expected.
- Migration plan: Audit all model validators. Replace `@validator` with `@field_validator`. Test extensively before upgrading.

**pgvector Without Version Pin:**
- Risk: `pgvector==0.3.6` may have breaking changes in future versions. Custom `SafeVector` type may not work with 0.4.x.
- Impact: Embeddings could become unloadable after dependency update.
- Migration plan: Pin `pgvector>=0.3.6,<0.4.0` in `requirements.txt`. Track pgvector releases. Pre-test major version upgrades.

**OpenAI SDK Deprecation:**
- Risk: `openai==1.12.0` is relatively recent. Older features may deprecate. Async support in 1.x is incomplete in some methods.
- Impact: Code using older patterns could break. Streaming might fail.
- Migration plan: Monitor OpenAI SDK releases. Test CI pipeline with `openai>=1.15.0`. Document required version range.

**tiktoken Tokenizer Mismatch:**
- Risk: `tiktoken==0.7.0` encodes tokens. If model changes (e.g., GPT-4 Turbo uses different tokenizer), token counts become inaccurate.
- Impact: Chunk size validation (`CHUNK_SIZE_TOKENS`) becomes wrong. Books truncated incorrectly.
- Migration plan: Add integration tests that verify token counts match actual API. Use `encoding_for_model(model_name)` API from tiktoken, not hardcoded encoding.

---

## Test Coverage Gaps

**No Database Cascade Tests:**
- What's not tested: Deleting a project and verifying all related records (sections, checklist, phase_data, chat sessions, etc.) are deleted.
- Files: `backend/app/tests/`, no test for cascade delete
- Risk: Silent orphaned records, data corruption.
- Priority: High - core data integrity

**No Cross-User Access Tests:**
- What's not tested: Attempting to view/edit another user's project/book/agent.
- Files: `backend/app/tests/test_api.py`
- Risk: Authorization bypass, data leakage.
- Priority: High - security critical

**No Concurrent Request Tests:**
- What's not tested: Two simultaneous requests updating the same resource.
- Risk: Lost updates, inconsistent state.
- Priority: Medium

**No Book Processing Failure Recovery:**
- What's not tested: Simulating API timeout, file corruption, or partial processing and verifying resume logic.
- Files: `backend/app/tests/`, no integration tests for background task
- Risk: Stuck processing state, unretrievable books.
- Priority: Medium

**No Frontend Error Boundary Tests:**
- What's not tested: React error recovery, network error handling.
- Files: `frontend/src/` - no test files
- Risk: Silent crashes, poor user experience.
- Priority: Low (frontend is simple, but should have at least smoke tests)

**No Rate Limit Tests:**
- What's not tested: Rate limit behavior, cleanup, distributed rate limits.
- Files: `backend/app/tests/`
- Risk: Rate limit bypass, DoS vulnerability.
- Priority: Medium

---

## Missing Critical Features

**No Database Connection Pooling Configuration:**
- Problem: Database engine is created with default pool settings. No control over max connections, pool recycle, overflow.
- Blocks: Scaling to production loads (100+ concurrent requests).
- Files: `backend/app/db.py:6`
- Solution: Configure engine with `pool_size=20, max_overflow=40, pool_recycle=3600`.

**No API Versioning Strategy:**
- Problem: All endpoints are `/api/v0` or unversioned. No versioning scheme for breaking changes.
- Blocks: Rolling out backwards-incompatible changes without breaking clients.
- Solution: Adopt URL versioning (`/api/v1/`, `/api/v2/`) or header versioning. Plan deprecation path.

**No Monitoring/Logging Aggregation:**
- Problem: Logs only go to stdout. No structured logging, no remote aggregation.
- Blocks: Debugging production issues, performance analysis.
- Solution: Integrate ELK stack, Datadog, or New Relic. Use Python `logging` JSON formatter.

**No API Documentation Auto-Generation:**
- Problem: FastAPI serves `/docs` but schema is incomplete for complex types.
- Blocks: Frontend developers uncertain about actual API contracts.
- Solution: Ensure all endpoints have proper response_model. Add docstrings with examples.

---

*Concerns audit: 2026-03-05*
