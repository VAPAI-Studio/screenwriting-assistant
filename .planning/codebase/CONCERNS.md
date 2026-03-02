# Codebase Concerns

**Analysis Date:** 2026-03-01

## Tech Debt

**Mock Authentication Hardcoded in Production Code:**
- Issue: Development mock auth token hardcoded in `dependencies.py` - allows any request with "mock-token" to pass auth checks in development environment
- Files: `backend/app/api/dependencies.py` (lines 24-25)
- Impact: Accidental deployment to production with mock auth enabled would expose entire API without real authentication
- Fix approach: Move mock auth to test-only utilities via environment check. Ensure `ENVIRONMENT=development` is never set in production. Consider separate test client factory

**Default Secret Key in Production:**
- Issue: Default `SECRET_KEY` in config is placeholder value "your-secret-key-replace-in-production"
- Files: `backend/app/config.py` (line 27)
- Impact: JWT tokens can be forged if not changed. Production validation exists (lines 96-98) but depends on env var being set
- Fix approach: Make SECRET_KEY required without default in production. Fail loudly if not provided

**Print Statements in Production Code:**
- Issue: Debug print statement in exception handler instead of proper logging
- Files: `backend/app/api/endpoints/review.py` (line 71)
- Impact: Debug output goes to stdout instead of logs; not captured by log aggregation systems
- Fix approach: Replace `print()` with `logger.error()` consistently

**Unsafe Logging of Security Headers:**
- Issue: CSP and security headers in middleware contain hardcoded localhost origins with `unsafe-eval` and `unsafe-inline`
- Files: `backend/app/middleware.py` (lines 62-67)
- Impact: Non-production security policy applied broadly; development settings will compromise security if not properly managed
- Fix approach: Environment-specific security headers. Use strict CSP in production with no unsafe directives

## Known Bugs

**Incomplete API Response Serialization:**
- Issue: Book upload endpoint returns dict directly instead of Pydantic model in some paths
- Files: `backend/app/api/endpoints/books.py` (line 97)
- Impact: Dict serialization inconsistent with schema validation; may return extra fields not in response_model
- Fix approach: Use response_model consistently; validate all returns against schema

**Exception Swallowing with Generic Catch-all:**
- Issue: Broad `except Exception` blocks swallow specific errors and return generic 500 response
- Files: `backend/app/api/endpoints/review.py` (lines 70-75), `backend/app/api/dependencies.py` (lines 44-49)
- Impact: Errors not propagated; client debugging difficult; logging may be missed
- Fix approach: Catch specific exception types. Log original error with traceback. Re-raise with proper HTTPException

**Missing Database Transaction Rollback:**
- Issue: No explicit rollback in exception handlers when database operations fail
- Files: `backend/app/api/endpoints/projects.py` (lines 37-58) - creates multiple related records in transaction
- Impact: Partial state could be committed if second db.add() fails after flush()
- Fix approach: Wrap multi-step DB operations in try/except with explicit db.rollback() on error

## Security Considerations

**File Upload Path Traversal Risk:**
- Risk: User-supplied filename directly used in file path construction without sanitization
- Files: `backend/app/api/endpoints/books.py` (line 39)
- Current mitigation: File type whitelist exists (line 28), but filename not validated
- Recommendations: Use secure filename generation (e.g., `werkzeug.utils.secure_filename`); store original filename separately in DB; generate UUID-based disk filenames

**Unvalidated File Processing:**
- Risk: Uploaded PDF/EPUB files passed directly to background processing without format validation
- Files: `backend/app/api/endpoints/books.py` (lines 58-63) - file passed to `book_processing_service`
- Current mitigation: File size limit (line 33)
- Recommendations: Validate file magic numbers; scan with virus checker before processing; isolate processing in sandboxed environment

**No Rate Limiting on Resource-Intensive Operations:**
- Risk: AI review, book upload, and agent review endpoints not separately rate limited despite high API cost
- Files: `backend/app/middleware.py` - global 60 req/min limit applies to all endpoints equally
- Current mitigation: Global rate limit only (60 req/min/IP)
- Recommendations: Per-endpoint rate limiting; higher limits for cheap operations, lower for AI-intensive ones; per-user rate limiting

**Sensitive Data in Error Messages:**
- Risk: Database errors and validation errors may leak schema/structure info
- Files: `backend/app/api/dependencies.py` (lines 47-48), various validators
- Current mitigation: Generic HTTP status codes used
- Recommendations: Catch database-specific errors; return sanitized messages to client; log full errors server-side only

**JWT Token Expiration Too Long:**
- Risk: Access token TTL set to 7 days - excessive exposure window if token leaked
- Files: `backend/app/services/auth_service.py` (line 20)
- Impact: Compromised token valid for 1 week; no ability to revoke without separate blacklist
- Fix approach: Reduce to 1 hour; implement refresh token mechanism; add token revocation list

## Performance Bottlenecks

**In-Memory Cache with No Persistence:**
- Problem: OpenAI review responses cached in memory only; lost on restart; scales with max_cache_size=100
- Files: `backend/app/services/openai_service.py` (lines 17-18)
- Cause: OrderedDict cache for 15-min TTL responses; no distributed cache
- Improvement path: Use Redis for distributed caching; implement cache warming; add cache metrics

**Synchronous Database Queries in Async Handler:**
- Problem: SQLAlchemy ORM queries block event loop in async endpoints
- Files: `backend/app/api/endpoints/projects.py` (lines 33-59) - multiple sequential queries with flushes
- Cause: Using synchronous `Session` not `AsyncSession`
- Improvement path: Migrate to SQLAlchemy AsyncSession; use async ORM queries; batch queries with joinedload

**Background Task No Error Handling:**
- Problem: Book processing runs in background_tasks with no error recovery or retry logic
- Files: `backend/app/api/endpoints/books.py` (lines 58-63)
- Cause: BackgroundTasks executes tasks synchronously; no celery or job queue
- Improvement path: Migrate to task queue (Celery/RQ); add retry logic; implement dead-letter queue for failed books

**Vector Search Query Inefficiency:**
- Problem: Large N-way vector similarity joins without pagination or result limiting
- Files: `backend/app/services/rag_service.py` (lines likely doing full table scans)
- Cause: No index on embeddings column; no distance threshold filtering
- Improvement path: Add pgvector HNSW index; implement MIN_SIMILARITY threshold; paginate results

## Fragile Areas

**Complex Project Creation Logic:**
- Files: `backend/app/api/endpoints/projects.py` (lines 63-100+)
- Why fragile: `create_project_v2` creates project and auto-scaffolds phase_data for all subsections in sequence. If template system changes, logic breaks
- Safe modification: Abstract template subsection logic to separate service; add integration tests covering all template types; validate subsection count
- Test coverage: No dedicated tests for v2 endpoint visible; gaps in template mutation testing

**Knowledge Graph Relationship Management:**
- Files: `backend/app/models/database.py` (lines 313-323)
- Why fragile: ConceptRelationship model uses self-referential foreign keys with cascade delete; easy to accidentally delete dependent concepts
- Safe modification: Add soft-delete flag before hard deletes; validate relationships before deletion; write tests for cascade behavior
- Test coverage: No visible tests for cascade delete scenarios

**AI Session Context Building:**
- Files: `backend/app/api/endpoints/ai_chat.py` (lines 23-35)
- Why fragile: `_get_project_context` manually traverses phase_data and builds context string; template changes break this
- Safe modification: Use template service to build context structure; validate context against schema; add schema validation before AI call
- Test coverage: Gaps in context building tests for edge cases (missing phases, malformed content)

**Database Connection Dependency Injection:**
- Files: `backend/app/db.py` (lines 12-17)
- Why fragile: Simple try/finally with no connection validation; no health check or recovery
- Safe modification: Add connection retry logic; implement circuit breaker; validate connection before yielding
- Test coverage: No tests for connection failure scenarios

## Scaling Limits

**Single PostgreSQL Instance:**
- Current capacity: Configured for single DB connection (no explicit pool settings)
- Limit: Default pool_size (SQLAlchemy) is 5; 5 concurrent requests max before queueing
- Scaling path: Configure explicit pool_size, max_overflow in db.py; enable read replicas for analytics; shard by project_id if needed

**In-Memory Rate Limit Dictionary:**
- Current capacity: Stores all client IPs in memory; `self.requests` dict grows unbounded
- Limit: Memory leak - old entries only cleaned when accessed; can exhaust memory with botnet traffic
- Scaling path: Use Redis for rate limit state; implement TTL-based cleanup; add metrics for request tracking

**Sequential AI API Calls:**
- Current capacity: Agent service makes sequential API calls to AI provider
- Files: `backend/app/services/agent_service.py` (uses `asyncio.gather` but may still be sequential)
- Limit: N agents × 90s timeout = 450s+ total for 5 agents; timeout brittle
- Scaling path: Implement concurrent API calls with proper timeout; batch requests; add fallback agents

**File Upload Directory Structure:**
- Current capacity: Files stored in flat structure under `uploads/{owner_id}/`
- Limit: Single directory with thousands of files causes filesystem performance degradation
- Scaling path: Use S3/cloud storage; implement hierarchical folder structure by date; prune old uploads

## Dependencies at Risk

**pgvector CustomType Implementation:**
- Risk: Custom SafeVector type handles both string and list values - fragile workaround for psycopg2 adapter variance
- Files: `backend/app/models/database.py` (lines 12-46)
- Impact: If pgvector psycopg2 behavior changes, embedding storage/retrieval breaks
- Migration plan: Monitor pgvector releases; consider migration to standard pgvector SQLAlchemy type once stable; add integration tests for embedding round-trips

**Hardcoded AI Provider Configuration:**
- Risk: Config allows switching between OpenAI and Anthropic (line 16), but services hardcoded to specific providers
- Files: `backend/app/config.py` (line 16 - AI_PROVIDER setting), but `backend/app/services/openai_service.py` hardcoded
- Impact: Switching providers requires code changes, not just config
- Migration plan: Create abstraction layer for AI provider (chat_completion via provider registry); implement both OpenAI and Anthropic adapters; test both providers in CI

**Legacy Framework Model Still Used:**
- Risk: Project model has both `framework` (legacy) and `template` (new); code inconsistently uses both
- Files: `backend/app/models/database.py` (line 85), `/projects/create` uses framework, `/projects/v2/create` uses template
- Impact: Two competing schema versions; data migration path unclear; confusion in client code
- Migration plan: Pick one schema; create migration script; deprecate old endpoint; update all code paths to new schema

## Missing Critical Features

**No Audit Logging:**
- Problem: No tracking of who changed what and when; only timestamps on models, no change log
- Blocks: Compliance audits; user dispute resolution; debugging unauthorized changes
- Recommendation: Add audit log table; log all mutations; implement audit endpoint with filtering

**No Concurrent Edit Detection:**
- Problem: Two users editing same project simultaneously could lose changes (last-write-wins)
- Blocks: Multi-user collaboration; team projects
- Recommendation: Implement optimistic locking (version field); add conflict resolution UI

**No Backup/Export Feature:**
- Problem: Projects trapped in database; no way for users to export screenplay content
- Blocks: Data portability; external tool integration; self-hosting
- Recommendation: Add JSON export endpoint; implement backup service; support import from formats

**No API Documentation Versioning:**
- Problem: OpenAPI docs don't reflect breaking changes; v1 and v2 endpoints mixed
- Blocks: Third-party integrations; API contract clarity
- Recommendation: Version API endpoints explicitly; separate v1 and v2 in docs; document deprecation timeline

## Test Coverage Gaps

**AI Integration Tests Missing:**
- What's not tested: Actual calls to OpenAI/Anthropic; prompt consistency across frameworks; response parsing
- Files: `backend/app/services/openai_service.py`, `backend/app/services/template_ai_service.py`
- Risk: AI responses could change format unexpectedly; JSON parsing could fail on edge cases
- Priority: High (directly impacts core feature)

**Database Migration Tests:**
- What's not tested: Database schema initialization; migration from old framework model to new template model
- Files: `backend/migrations/init_db.sql` (SQL migration not version controlled)
- Risk: Schema could be inconsistent; foreign key constraints could fail silently
- Priority: High (data integrity critical)

**Concurrent Request Tests:**
- What's not tested: Race conditions in multi-threaded/async scenarios; simultaneous updates
- Files: `backend/app/api/endpoints/` - all endpoints
- Risk: Concurrent edits, rate limit bypasses, cache inconsistencies undetected
- Priority: Medium (scales to multi-user)

**File Upload Security Tests:**
- What's not tested: Path traversal; malicious file content; file size limits at boundary
- Files: `backend/app/api/endpoints/books.py`
- Risk: Security vulnerabilities in file handling undetected
- Priority: High (security-critical)

**Frontend API Timeout Tests:**
- What's not tested: Behavior when API timeout occurs (30s threshold in constants)
- Files: `frontend/src/lib/api.tsx` (line 25)
- Risk: UI state inconsistency on timeout; user doesn't know if action succeeded
- Priority: Medium (UX impact)

---

*Concerns audit: 2026-03-01*
