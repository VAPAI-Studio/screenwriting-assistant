# Phase 44: API Gateway, Docs & Usage Tracking - Research

**Researched:** 2026-03-30
**Domain:** API documentation (OpenAPI/Swagger), usage tracking, per-key rate limiting
**Confidence:** HIGH

## Summary

Phase 44 builds on the existing Phase 43 API key infrastructure to add three capabilities: (1) comprehensive API documentation via FastAPI's built-in Swagger UI, (2) per-key request counting and usage tracking, and (3) per-key rate limiting with configurable limits. The codebase already has a functional `api_docs.py` module with a custom OpenAPI schema, Swagger UI exposed at `/docs`, and dual auth (JWT + API key) in `dependencies.py`. The work is primarily about enhancing what exists rather than building from scratch.

The most significant piece is adding a `request_count` column to the `api_keys` table (currently only `last_used_at` is tracked) and incrementing it atomically on each API key request. The per-key rate limiter is a new middleware or modification to the existing `RateLimitMiddleware` that keys off the API key identity rather than (or in addition to) client IP. The docs enhancement involves adding proper response schemas, examples, and tag descriptions to the existing `api_docs.py` module. The frontend update is small: add `request_count` display to the existing `ApiKeysPage.tsx`.

**Primary recommendation:** Add `request_count` column to ApiKey model, increment atomically in `get_current_user`, add per-key rate limiting as a new middleware class, enhance `api_docs.py` with complete endpoint documentation, and update the frontend ApiKeysPage to display usage stats.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AK-05 | API is fully documented via Swagger UI with correct schemas and examples | Enhance existing `api_docs.py` module, add tag descriptions for all router tags, ensure all endpoints have response_model set (most already do) |
| AK-06 | Per-key usage tracking (request_count, last_used_at) visible in UI with per-key rate limiting | Add `request_count` column to ApiKey model, atomic increment in `get_current_user`, new `ApiKeyRateLimitMiddleware`, update frontend ApiKeysPage |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.110.0 (installed) | OpenAPI schema generation, Swagger UI at /docs | Already in use; built-in support for all docs features |
| SQLAlchemy | 2.0.27 (installed) | Add request_count column, atomic increment | Already in use for all models |
| Pydantic v2 | 2.12.5 (installed) | Response schemas with examples for docs | Already in use |
| Starlette | (installed with FastAPI) | Custom middleware for per-key rate limiting | Already used via BaseHTTPMiddleware |
| React Query | @tanstack/react-query (installed) | Refetch API keys list to show updated counts | Already in use |

### Supporting
No new packages required. Everything needed is already installed.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory per-key rate limiter | Redis-backed rate limiter | Redis adds infrastructure complexity; in-memory is sufficient for single-server MVP |
| Atomic SQL increment in get_current_user | Separate middleware for counting | Counting in get_current_user is simpler since the key is already loaded there; separate middleware would require re-hashing and re-querying |
| Custom OpenAPI via api_docs.py | Per-endpoint OpenAPI decorators only | Custom schema function allows batch modifications (security schemes, tags) which is already the established pattern |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  api_docs.py              # Enhance: add all tag descriptions, examples for all endpoints
  middleware.py             # Add: ApiKeyRateLimitMiddleware class
  api/
    dependencies.py         # Modify: increment request_count atomically alongside last_used_at
  models/
    database.py             # Modify: add request_count column to ApiKey
    schemas.py              # Modify: add request_count to ApiKeyResponse
  migrations/
    delta/
      010_api_key_usage.sql # New: add request_count column + rate_limit column

frontend/src/
  types/index.ts            # Modify: add request_count to ApiKey interface
  components/
    Settings/
      ApiKeysPage.tsx        # Modify: display request_count and last_used_at
```

### Pattern 1: Atomic Request Count Increment
**What:** Use SQL `UPDATE ... SET request_count = request_count + 1` instead of Python-side read-modify-write to avoid race conditions.
**When to use:** Every API key authentication in `get_current_user`.
**Example:**
```python
# In dependencies.py get_current_user, after hash lookup:
from sqlalchemy import text

# Atomic increment -- no race condition under concurrent requests
db.execute(
    text("UPDATE api_keys SET request_count = request_count + 1, last_used_at = :now WHERE id = :id"),
    {"now": datetime.utcnow(), "id": str(api_key.id)}
)
db.commit()
```

### Pattern 2: Per-Key Rate Limiting Middleware
**What:** A new middleware class that extracts the Bearer token, checks if it starts with `sa_`, looks up the key's rate limit, and enforces it using an in-memory sliding window per key hash.
**When to use:** Every incoming request with an API key Bearer token.
**Example:**
```python
class ApiKeyRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-API-key rate limiting (default 1000 req/hour)."""

    def __init__(self, app, default_rate_limit: int = 1000):
        super().__init__(app)
        self.default_rate_limit = default_rate_limit
        self.window_size = 3600  # 1 hour
        self.requests = {}  # key_hash -> [timestamps]
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer sa_"):
            return await call_next(request)

        token = auth_header.split(" ", 1)[1]
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        current_time = time.time()

        async with self._lock:
            if key_hash not in self.requests:
                self.requests[key_hash] = []

            # Filter to window
            valid = [t for t in self.requests[key_hash] if t > current_time - self.window_size]

            if len(valid) >= self.default_rate_limit:
                retry_after = int(self.window_size - (current_time - valid[0]))
                return Response(
                    content='{"detail": "API key rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(max(1, retry_after))}
                )

            valid.append(current_time)
            self.requests[key_hash] = valid

        return await call_next(request)
```

### Pattern 3: Enhanced OpenAPI Documentation
**What:** Extend the existing `api_docs.py` to include tag descriptions for ALL router tags (not just the original 4), add example payloads for key endpoints, and ensure the security scheme description mentions both JWT and API key formats.
**When to use:** On app startup (custom_openapi function).
**Example:**
```python
# In api_docs.py, update the tags list:
openapi_schema["tags"] = [
    {"name": "auth", "description": "Authentication: register, login, API key management"},
    {"name": "projects", "description": "Project CRUD operations"},
    {"name": "sections", "description": "Section and checklist operations"},
    {"name": "review", "description": "AI review operations"},
    {"name": "books", "description": "Book upload and processing"},
    {"name": "agents", "description": "Agent management and pipeline mapping"},
    {"name": "chat", "description": "Agent chat sessions"},
    {"name": "templates", "description": "Project template listing"},
    {"name": "phase-data", "description": "Template phase data CRUD"},
    {"name": "list-items", "description": "Phase list items CRUD"},
    {"name": "wizards", "description": "AI wizard operations"},
    {"name": "ai", "description": "AI generation actions"},
    {"name": "breakdown", "description": "Script breakdown extraction and elements"},
    {"name": "shots", "description": "Shotlist CRUD and reordering"},
    {"name": "media", "description": "Media file upload and management"},
    {"name": "breakdown-chat", "description": "AI chat for breakdown mode"},
    {"name": "storyboard", "description": "Storyboard frame management"},
    {"name": "shows", "description": "TV show management with bible and episodes"},
]

# Update security scheme to mention both auth types:
openapi_schema["components"]["securitySchemes"] = {
    "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT or API Key",
        "description": "Use a JWT token or an API key (format: sa_<prefix>_<secret>)"
    }
}
```

### Anti-Patterns to Avoid
- **Read-modify-write for request_count:** Using Python-side `api_key.request_count += 1` followed by commit is racy under concurrent requests. Use SQL atomic increment instead.
- **Hashing the key twice per request:** The per-key rate limiter must hash the token to identify the key, and `get_current_user` also hashes it. This is acceptable -- SHA-256 is fast (~microseconds), and the alternative (passing state between middleware and dependency) adds complexity for negligible gain.
- **Storing per-key rate limit in the middleware's in-memory dict:** Store the configurable rate limit in the database column (`rate_limit` on ApiKey model) so users can potentially have different limits. The middleware reads the default; the dependency can check the per-key override.
- **Blocking /docs behind authentication:** The Swagger UI at `/docs` should remain publicly accessible (it already is). Authentication is only required when actually calling endpoints via the "Try it out" feature, which uses the Authorization header.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAPI schema generation | Manual JSON schema construction | FastAPI's built-in `get_openapi()` + `response_model` on endpoints | FastAPI auto-generates schemas from Pydantic models; manual is error-prone |
| Swagger UI | Custom API docs frontend | FastAPI's built-in `/docs` (Swagger UI) and `/redoc` (ReDoc) | Already configured and working; zero additional code needed |
| Rate limiting algorithm | Custom token bucket implementation | Simple sliding window (already used in `RateLimitMiddleware`) | Matches existing codebase pattern; sufficient for MVP |
| Atomic counter | Application-level locking/mutex | SQL `SET request_count = request_count + 1` | Database handles concurrency correctly; no application-side coordination needed |

**Key insight:** The codebase already has all the infrastructure. This phase is enhancement and extension, not greenfield development.

## Common Pitfalls

### Pitfall 1: Non-Atomic Request Count Increment
**What goes wrong:** Two concurrent requests read the same count, both increment to N+1, losing one count.
**Why it happens:** Python-side `api_key.request_count += 1` with ORM is not atomic.
**How to avoid:** Use raw SQL: `UPDATE api_keys SET request_count = request_count + 1 WHERE id = :id`.
**Warning signs:** Request counts that seem lower than actual usage.

### Pitfall 2: Rate Limiter Memory Leak
**What goes wrong:** The in-memory `requests` dict grows unbounded with old key hashes.
**Why it happens:** Expired timestamps are cleaned per-key but abandoned keys are never removed.
**How to avoid:** Periodic cleanup in the dispatch method: remove any key_hash entry where all timestamps are outside the window. The existing `RateLimitMiddleware` already does this pattern (line 105-109 of middleware.py).
**Warning signs:** Increasing memory usage over time.

### Pitfall 3: Missing request_count Default in Migration
**What goes wrong:** Existing rows have NULL request_count after adding the column.
**Why it happens:** ALTER TABLE ADD COLUMN without DEFAULT clause.
**How to avoid:** Use `ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS request_count INTEGER NOT NULL DEFAULT 0`.
**Warning signs:** NoneType errors when displaying request_count in the frontend.

### Pitfall 4: Swagger UI Security Scheme Not Matching Actual Auth
**What goes wrong:** Users try to authenticate in Swagger UI but the format doesn't work.
**Why it happens:** Security scheme says "JWT" but API keys use `sa_` prefix format.
**How to avoid:** Update the security scheme description to explain both auth methods. Add examples showing both JWT and API key formats.
**Warning signs:** Users confused about how to authenticate in Swagger UI.

### Pitfall 5: Rate Limit Not Returning Proper 429 Response
**What goes wrong:** Rate-limited responses don't include required `Retry-After` header or return plain text instead of JSON.
**Why it happens:** Middleware returns raw Response without proper headers/content type.
**How to avoid:** Return JSON body with `detail` field and include `Retry-After` header with seconds until window reset. Use `media_type="application/json"`.
**Warning signs:** Clients can't programmatically detect rate limiting or know when to retry.

### Pitfall 6: Middleware Ordering Conflict
**What goes wrong:** The per-key rate limiter fires before CORS middleware, blocking preflight OPTIONS requests.
**Why it happens:** Incorrect middleware ordering in `main.py`.
**How to avoid:** Add `ApiKeyRateLimitMiddleware` ABOVE `RateLimitMiddleware` in the middleware stack (which means it executes after CORS but before rate limiting). The middleware should also skip non-authenticated requests (no Bearer token) and OPTIONS requests.
**Warning signs:** CORS errors in the browser when API keys are used.

## Code Examples

### Database Migration (010_api_key_usage.sql)
```sql
-- Migration 010: Add request_count and rate_limit to api_keys (v5.0 -- Phase 44)
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS request_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS rate_limit INTEGER DEFAULT NULL;
-- rate_limit NULL means "use default" (1000 req/hour)
```

### Updated ApiKey Model
```python
# In backend/app/models/database.py, update ApiKey class:
class ApiKey(Base):
    __tablename__ = "api_keys"
    # ... existing columns ...
    request_count = Column(Integer, nullable=False, default=0)
    rate_limit = Column(Integer, nullable=True)  # NULL = use default
```

### Updated ApiKeyResponse Schema
```python
# In backend/app/models/schemas.py:
class ApiKeyResponse(BaseModel):
    """Returned on list/get -- NO secret."""
    id: UUID
    name: str
    key_prefix: str
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    request_count: int = 0
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
```

### Atomic Increment in get_current_user
```python
# In dependencies.py, replace the existing last_used_at update:
from sqlalchemy import text

# Instead of:
#   api_key.last_used_at = datetime.utcnow()
#   db.commit()

# Use atomic increment:
db.execute(
    text(
        "UPDATE api_keys SET request_count = request_count + 1, "
        "last_used_at = :now WHERE id = :id"
    ),
    {"now": datetime.utcnow(), "id": str(api_key.id)}
)
db.commit()
```

### Frontend ApiKey Type Update
```typescript
// In frontend/src/types/index.ts, update ApiKey interface:
export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  request_count: number;
  is_active: boolean;
}
```

### Frontend Usage Display
```typescript
// In ApiKeysPage.tsx, update the key card to show request_count:
<div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
  <span>Created: {formatDate(key.created_at)}</span>
  <span>Last used: {formatDate(key.last_used_at)}</span>
  <span>Requests: {key.request_count.toLocaleString()}</span>
  <span>Expires: {key.expires_at ? formatDate(key.expires_at) : 'Never expires'}</span>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| IP-only rate limiting | Per-key rate limiting (in addition to IP) | Industry standard for API platforms | Prevents key abuse independently of IP rotation |
| No usage tracking | Per-key request counting with last_used_at | Standard for API key dashboards | Users can monitor their API usage |
| Partial Swagger docs (4 tags) | Complete docs with all 18 router tags | This phase | External API consumers can discover all endpoints |

**Deprecated/outdated:**
- Manually writing API documentation: FastAPI auto-generates from Pydantic models
- Storing usage metrics in application memory: Database-backed counters survive restarts

## Open Questions

1. **Per-key configurable rate limits**
   - What we know: Success criteria says "configurable per-key limit, default 1000 req/hour." The simplest approach is a nullable `rate_limit` column on ApiKey where NULL means "use default."
   - What's unclear: Whether users should be able to set their own rate limit (UI), or if this is admin-only.
   - Recommendation: Add the `rate_limit` column but do NOT expose it in the create/update UI for now. Admin can set it directly in the database. The middleware reads the per-key override if present, otherwise uses the default 1000/hour.

2. **"Updated in real time" for the frontend**
   - What we know: Success criteria #4 says request_count and last_used_at should be "updated in real time."
   - What's unclear: Whether this means WebSocket push or just frequent polling.
   - Recommendation: Use React Query with a short refetchInterval (e.g., 30 seconds) on the API keys page. True real-time (WebSocket) is overkill for a settings page. The data updates on every page visit and auto-refreshes while the page is open.

3. **Swagger UI authentication**
   - What we know: Success criteria #1 says "/docs authenticated via session or API key." Currently /docs is publicly accessible (no auth wall).
   - What's unclear: Whether "authenticated" means the docs page itself requires auth, or just that the "Try it out" feature uses auth.
   - Recommendation: Keep /docs publicly accessible (standard practice). The "authenticated" part refers to the security scheme in Swagger UI -- users enter their Bearer token to test endpoints. This is already how it works.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | None (pytest runs from backend directory) |
| Quick run command | `cd backend && python -m pytest app/tests/test_api_keys.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AK-05 | /docs endpoint returns 200 with valid OpenAPI schema | integration | `pytest app/tests/test_api_gateway.py::TestSwaggerDocs::test_docs_accessible -x` | Wave 0 |
| AK-05 | OpenAPI schema has all router tags documented | integration | `pytest app/tests/test_api_gateway.py::TestSwaggerDocs::test_all_tags_documented -x` | Wave 0 |
| AK-05 | Security scheme mentions both JWT and API key | integration | `pytest app/tests/test_api_gateway.py::TestSwaggerDocs::test_security_scheme_dual_auth -x` | Wave 0 |
| AK-06 | request_count increments on API key usage | integration | `pytest app/tests/test_api_gateway.py::TestUsageTracking::test_request_count_increments -x` | Wave 0 |
| AK-06 | request_count visible in list endpoint response | integration | `pytest app/tests/test_api_gateway.py::TestUsageTracking::test_request_count_in_list -x` | Wave 0 |
| AK-06 | Per-key rate limiter returns 429 with Retry-After header | integration | `pytest app/tests/test_api_gateway.py::TestPerKeyRateLimit::test_rate_limit_returns_429 -x` | Wave 0 |
| AK-06 | Per-key rate limiter allows requests under limit | integration | `pytest app/tests/test_api_gateway.py::TestPerKeyRateLimit::test_under_limit_allowed -x` | Wave 0 |
| AK-06 | JWT requests bypass per-key rate limiter | integration | `pytest app/tests/test_api_gateway.py::TestPerKeyRateLimit::test_jwt_bypasses_key_limiter -x` | Wave 0 |
| AK-06 | Frontend TypeScript types compile with request_count | build | `cd frontend && npx tsc --noEmit` | Existing |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_api_gateway.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_api_gateway.py` -- covers AK-05, AK-06 across TestSwaggerDocs, TestUsageTracking, TestPerKeyRateLimit
- [ ] No new framework install needed -- pytest already in requirements.txt
- [ ] No conftest changes needed -- existing fixtures (client, db_session, mock_auth_headers) sufficient

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/api_docs.py` -- existing custom OpenAPI schema generation (25 lines, 4 tag descriptions)
- Codebase inspection: `backend/app/main.py` -- current middleware stack and router registration (18 routers with tags)
- Codebase inspection: `backend/app/middleware.py` -- existing RateLimitMiddleware with sliding window pattern
- Codebase inspection: `backend/app/api/dependencies.py` -- current dual auth (JWT + API key) with last_used_at update
- Codebase inspection: `backend/app/models/database.py` -- ApiKey model (no request_count column yet)
- Codebase inspection: `backend/app/models/schemas.py` -- ApiKeyResponse schema (no request_count field yet)
- Codebase inspection: `frontend/src/components/Settings/ApiKeysPage.tsx` -- existing key list UI
- Codebase inspection: `frontend/src/types/index.ts` -- existing ApiKey interface (no request_count field)
- Codebase inspection: `backend/app/tests/test_api_keys.py` -- existing test patterns
- FastAPI 0.110.0 (installed): docs_url="/docs" already configured, get_openapi() for custom schema

### Secondary (MEDIUM confidence)
- Industry best practice: SHA-256 is fast enough to hash twice per request (middleware + dependency)
- Industry best practice: Sliding window rate limiting is standard for single-server deployments

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or installed package capabilities

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new packages, all existing
- Architecture: HIGH -- clear extension of existing patterns (middleware, dependency, schema)
- Pitfalls: HIGH -- well-known patterns (atomic increment, sliding window, middleware ordering)
- Frontend: HIGH -- minimal change to existing ApiKeysPage component

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, no fast-moving dependencies)
