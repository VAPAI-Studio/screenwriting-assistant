# Phase 43: API Key Management - Research

**Researched:** 2026-03-25
**Domain:** API key generation, secure hashing, dual-auth middleware, settings UI
**Confidence:** HIGH

## Summary

Phase 43 adds API key management to the screenwriting assistant. Users create named API keys (with optional scopes and expiry) that authenticate any existing endpoint alongside the current JWT flow. The backend needs a new `api_keys` database table, CRUD endpoints under `/api/auth/api-keys`, and a modification to the `get_current_user` dependency to detect `sa_<prefix>_<secret>` tokens and authenticate via SHA-256 hash lookup. The frontend needs a new `/settings/api-keys` page with key listing, creation (one-time secret display), and revocation.

This is a well-understood domain with no exotic dependencies. Python's `hashlib` and `secrets` standard library modules handle key generation and hashing. The only meaningful architecture decision is how to extend `get_current_user` in `dependencies.py` to handle both JWT and API key tokens transparently. The existing codebase already uses `HTTPBearer` which extracts the raw token string -- adding a prefix check (`sa_`) before JWT verification is straightforward.

**Primary recommendation:** Use Python stdlib (`hashlib.sha256`, `secrets.token_urlsafe`) for key operations. Modify the existing `get_current_user` dependency to branch on `sa_` prefix. No new pip packages needed.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AK-01 | User can create a named API key with optional scopes and expiry | DB model (api_keys table), POST endpoint, Pydantic schemas for create/response |
| AK-02 | API key is returned exactly once at creation time, never stored in plaintext | `secrets.token_urlsafe` for generation, `hashlib.sha256` for hashing, response schema shows full key only on create |
| AK-03 | Any protected endpoint accepts `Bearer sa_<key>` via hash lookup | Modified `get_current_user` dependency with `sa_` prefix detection, hash comparison |
| AK-04 | User can list and revoke API keys via settings UI | GET/DELETE endpoints, React settings page with key list and revoke action |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hashlib (stdlib) | Python 3.11 | SHA-256 hashing of API key secrets | Standard library, no dependencies, constant-time comparison via `hmac.compare_digest` |
| secrets (stdlib) | Python 3.11 | Cryptographically secure random token generation | Standard library, purpose-built for tokens |
| SQLAlchemy | 2.0.27 (installed) | ApiKey model with FK to users | Already in use for all models |
| FastAPI | 0.110.0 (installed) | New API endpoints | Already in use |
| Pydantic v2 | >=2.10 (installed) | Request/response schemas | Already in use |
| React Query | @tanstack/react-query (installed) | API key list fetching and mutations | Already in use for all data fetching |
| lucide-react | (installed) | Icons for key management UI | Already in use throughout frontend |

### Supporting
No new packages required. Everything needed is already installed or in the Python standard library.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hashlib.sha256 | bcrypt (passlib) | SHA-256 is correct for API keys (high entropy, no brute-force risk); bcrypt is for passwords (low entropy). SHA-256 is faster for lookup. |
| secrets.token_urlsafe | uuid4 | secrets provides cryptographically secure tokens; uuid4 is not designed for secrets |
| Manual prefix detection | Separate HTTPBearer schemes | Two schemes would require changes to every endpoint; prefix detection in one dependency is simpler |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  models/
    database.py          # Add ApiKey model
    schemas.py           # Add API key schemas
  api/
    endpoints/
      auth.py            # Add API key CRUD endpoints
    dependencies.py      # Modify get_current_user for dual auth
  migrations/
    delta/
      009_api_keys.sql   # New migration

frontend/src/
  types/index.ts         # Add ApiKey interface
  lib/api.tsx            # Add API key CRUD methods
  lib/constants.ts       # Add QUERY_KEYS.API_KEYS, ROUTES.API_KEYS
  components/
    Settings/
      ApiKeysPage.tsx    # Main settings page (list + create + revoke)
  App.tsx                # Add /settings/api-keys route
```

### Pattern 1: API Key Format
**What:** Keys follow the format `sa_<prefix>_<secret>` where `sa` is the app prefix, `<prefix>` is 8 random chars (stored in DB, shown in UI), and `<secret>` is 32 random chars (never stored, only hashed).
**When to use:** Every key creation.
**Example:**
```python
import secrets
import hashlib

def generate_api_key() -> tuple[str, str, str]:
    """Generate an API key, returning (full_key, prefix, key_hash)."""
    prefix = secrets.token_urlsafe(6)[:8]  # 8-char prefix
    secret = secrets.token_urlsafe(24)      # 32-char secret
    full_key = f"sa_{prefix}_{secret}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash
```

### Pattern 2: Dual Auth in get_current_user
**What:** The existing `get_current_user` dependency checks if the Bearer token starts with `sa_`. If yes, look up by hash. If no, proceed with JWT verification as before.
**When to use:** Every authenticated request.
**Example:**
```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> schemas.User:
    token = credentials.credentials

    # Mock auth (development only)
    if settings.ENVIRONMENT == "development" and token == "mock-token":
        return mock_auth_service.get_current_user()

    # API key auth
    if token.startswith("sa_"):
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        api_key = db.query(database.ApiKey).filter(
            database.ApiKey.key_hash == key_hash,
            database.ApiKey.is_active == True,
        ).first()
        if not api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="API key expired")
        # Update last_used_at
        api_key.last_used_at = datetime.utcnow()
        db.commit()
        # Return the user associated with this key
        user = db.query(database.User).filter(database.User.id == api_key.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return schemas.User(
            id=user.id, email=user.email,
            display_name=user.display_name, created_at=user.created_at,
        )

    # JWT auth (existing flow)
    user_id = auth_service.verify_token(token)
    # ... existing JWT flow ...
```

### Pattern 3: One-Time Secret Display (Frontend)
**What:** The POST response returns the full key. The frontend shows it in a modal with a copy button. Once the modal is closed, the key is never retrievable. The GET list endpoint only returns prefix, name, timestamps.
**When to use:** Key creation flow.
**Example:**
```typescript
// On create success:
const [newKeySecret, setNewKeySecret] = useState<string | null>(null);

const createMutation = useMutation({
  mutationFn: (data: ApiKeyCreate) => api.createApiKey(data),
  onSuccess: (result) => {
    setNewKeySecret(result.key); // Show in modal
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.API_KEYS] });
  },
});
// Modal displays newKeySecret with copy-to-clipboard
// On modal close: setNewKeySecret(null) -- gone forever
```

### Anti-Patterns to Avoid
- **Storing the full key in the database:** Never store the plaintext key. Only store the SHA-256 hash. The full key is returned exactly once at creation.
- **Using bcrypt for API key hashing:** bcrypt is designed for low-entropy passwords. API keys are high-entropy random strings; SHA-256 is appropriate and much faster for lookup.
- **Creating a second HTTPBearer dependency:** This would require changing every endpoint's dependencies. Instead, handle both auth types in the single existing `get_current_user` function.
- **Checking scopes in the dependency:** For this phase, scopes are stored but not enforced. Enforcement comes in Phase 44 if needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cryptographic random tokens | Custom random string generator | `secrets.token_urlsafe()` | Purpose-built for security tokens; uses OS entropy source |
| Hash comparison | `==` string comparison | `hmac.compare_digest()` | Prevents timing attacks on hash comparison |
| Copy to clipboard | Manual DOM APIs | `navigator.clipboard.writeText()` | Browser standard, handles permissions |

**Key insight:** The Python `secrets` module and `hashlib` are specifically designed for this use case. Do not use `random`, `uuid`, or custom implementations.

## Common Pitfalls

### Pitfall 1: Timing Attack on Hash Lookup
**What goes wrong:** Using `==` to compare hashes in Python allows timing attacks.
**Why it happens:** String comparison short-circuits on first mismatched character, leaking information about the hash.
**How to avoid:** Use `hmac.compare_digest(a, b)` for hash comparison, or rely on SQL `WHERE key_hash = :hash` (database comparison is not timing-vulnerable in practice since it uses index lookup, not byte-by-byte comparison).
**Warning signs:** Direct `if stored_hash == provided_hash` in Python code.

### Pitfall 2: Returning the Secret After Creation
**What goes wrong:** The full key secret is accidentally included in GET /api/auth/api-keys responses.
**Why it happens:** Using the same response schema for create and list endpoints.
**How to avoid:** Use separate schemas: `ApiKeyCreateResponse` (includes `key` field) and `ApiKeyResponse` (only `id`, `name`, `key_prefix`, `scopes`, `expires_at`, `created_at`, `last_used_at`, `is_active`).
**Warning signs:** A `key` or `secret` field in the list endpoint response.

### Pitfall 3: Not Handling Expired Keys
**What goes wrong:** Expired keys continue to authenticate.
**Why it happens:** Forgetting to check `expires_at` during auth.
**How to avoid:** Add explicit expiry check in `get_current_user` after hash lookup: `if api_key.expires_at and api_key.expires_at < datetime.utcnow()`.
**Warning signs:** Missing datetime comparison in the API key auth branch.

### Pitfall 4: SQLite JSON Column in Tests
**What goes wrong:** The `scopes` JSON column may behave differently in SQLite (test env) vs PostgreSQL (prod).
**Why it happens:** SQLite stores JSON as TEXT. The existing test infrastructure already handles this (see conftest.py patching).
**How to avoid:** Use SQLAlchemy's `JSON` type (already used throughout the codebase for other JSON columns). The existing conftest.py patches handle SQLite compatibility.
**Warning signs:** Test failures when querying or filtering on the scopes column.

### Pitfall 5: Frontend Copy-to-Clipboard
**What goes wrong:** `navigator.clipboard.writeText()` fails in non-HTTPS or non-localhost contexts.
**Why it happens:** Clipboard API requires secure context.
**How to avoid:** Development runs on localhost (secure context). Add a fallback with `document.execCommand('copy')` or just rely on the fact that both localhost and HTTPS work. Display a clear "copied" confirmation.
**Warning signs:** Clipboard copy silently fails on certain browsers.

## Code Examples

### Database Model (ApiKey)
```python
# backend/app/models/database.py
class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    scopes = Column(JSON, default=list)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
```

### Delta Migration (009_api_keys.sql)
```sql
-- Migration 009: API keys table for API key authentication (v5.0)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    scopes JSONB DEFAULT '[]'::jsonb,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_api_keys_user_id ON api_keys(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_api_keys_key_hash ON api_keys(key_hash);
```

### Pydantic Schemas
```python
# backend/app/models/schemas.py

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None

class ApiKeyCreateResponse(BaseModel):
    """Returned ONLY on creation -- includes the full key."""
    id: UUID
    name: str
    key: str  # The full sa_<prefix>_<secret> -- shown exactly once
    key_prefix: str
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ApiKeyResponse(BaseModel):
    """Returned on list/get -- NO secret."""
    id: UUID
    name: str
    key_prefix: str
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
```

### Frontend TypeScript Interface
```typescript
// frontend/src/types/index.ts
export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

export interface ApiKeyCreate {
  name: string;
  scopes?: string[];
  expires_at?: string | null;
}

export interface ApiKeyCreateResponse extends ApiKey {
  key: string; // Full key, shown once
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Store API keys in plaintext | Hash with SHA-256, store only hash | Industry standard since ~2015 | Prevents key exposure if database is compromised |
| Single auth method per endpoint | Unified auth dependency handling multiple token types | Common pattern in FastAPI | No endpoint code changes needed |
| bcrypt for all secrets | SHA-256 for high-entropy keys, bcrypt for passwords | Always been best practice | Performance: SHA-256 is ~1000x faster than bcrypt for lookups |

**Deprecated/outdated:**
- Storing API keys in plaintext: security risk, never acceptable
- Using `random.choices()` for token generation: not cryptographically secure

## Open Questions

1. **Scope enforcement timing**
   - What we know: The `scopes` column stores a JSON array of strings. Phase 43 creates and stores scopes.
   - What's unclear: Whether scopes should be enforced in Phase 43 or deferred to Phase 44. The success criteria mention "optional scopes" but don't require enforcement.
   - Recommendation: Store scopes but do NOT enforce them in Phase 43. Phase 44 (API Gateway) is the natural place for scope enforcement since it adds rate limiting and usage tracking.

2. **Maximum keys per user**
   - What we know: No limit specified in requirements.
   - What's unclear: Whether to cap the number of active keys per user.
   - Recommendation: No limit in Phase 43. Can add a configurable limit later if needed.

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
| AK-01 | POST /api/auth/api-keys creates key with name, scopes, expiry | integration | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_create_api_key -x` | Wave 0 |
| AK-01 | ApiKey model stores all required columns | unit | `pytest app/tests/test_api_keys.py::TestApiKeyModel::test_api_key_model_columns -x` | Wave 0 |
| AK-01 | Create with invalid name (empty, too long) returns 422 | integration | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_create_api_key_validation -x` | Wave 0 |
| AK-02 | Create response includes full key string in `sa_<prefix>_<secret>` format | integration | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_create_returns_full_key_once -x` | Wave 0 |
| AK-02 | List endpoint does NOT return the secret | integration | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_list_does_not_expose_secret -x` | Wave 0 |
| AK-02 | Key hash stored in DB matches SHA-256 of full key | unit | `pytest app/tests/test_api_keys.py::TestApiKeyModel::test_key_hash_matches_sha256 -x` | Wave 0 |
| AK-03 | Bearer sa_<key> authenticates successfully | integration | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_api_key_authenticates_endpoint -x` | Wave 0 |
| AK-03 | Expired API key returns 401 | integration | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_expired_key_rejected -x` | Wave 0 |
| AK-03 | Revoked (is_active=false) API key returns 401 | integration | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_revoked_key_rejected -x` | Wave 0 |
| AK-03 | Invalid/garbled sa_ token returns 401 | integration | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_invalid_key_rejected -x` | Wave 0 |
| AK-03 | JWT auth still works alongside API key auth | integration | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_jwt_still_works -x` | Wave 0 |
| AK-03 | last_used_at updated on API key usage | integration | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_last_used_at_updated -x` | Wave 0 |
| AK-04 | GET /api/auth/api-keys lists user's keys | integration | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_list_api_keys -x` | Wave 0 |
| AK-04 | DELETE /api/auth/api-keys/{id} revokes key | integration | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_revoke_api_key -x` | Wave 0 |
| AK-04 | Frontend TypeScript types compile | build | `cd frontend && npx tsc --noEmit` | Existing |

### Estimated Test Count and Runtime
- **Backend tests:** ~15 tests (model: 3, API CRUD: 6, auth: 6)
- **Frontend build check:** 1 (TypeScript compilation)
- **Estimated runtime:** < 10 seconds for backend tests, < 30 seconds for frontend tsc

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_api_keys.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_api_keys.py` -- covers AK-01, AK-02, AK-03, AK-04
- [ ] No new framework install needed -- pytest already in requirements.txt
- [ ] No conftest changes needed -- existing fixtures (client, db_session, mock_auth_headers) sufficient

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/api/dependencies.py` -- current auth flow (lines 17-59)
- Codebase inspection: `backend/app/services/auth_service.py` -- JWT token handling
- Codebase inspection: `backend/app/models/database.py` -- all existing SQLAlchemy models
- Codebase inspection: `backend/app/models/schemas.py` -- all existing Pydantic schemas
- Codebase inspection: `backend/app/tests/conftest.py` -- test infrastructure with SQLite patching
- Codebase inspection: `backend/migrations/delta/005_users_table.sql` -- migration pattern
- Codebase inspection: `backend/app/tests/test_shows_api.py` -- test pattern for CRUD endpoints
- Python docs: `hashlib` module -- SHA-256 hashing (stdlib)
- Python docs: `secrets` module -- cryptographic token generation (stdlib)

### Secondary (MEDIUM confidence)
- Industry best practice: SHA-256 for high-entropy API keys vs bcrypt for passwords

### Tertiary (LOW confidence)
- None -- all findings verified against codebase or Python stdlib docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages already installed, only stdlib additions
- Architecture: HIGH -- clear extension of existing auth dependency pattern
- Pitfalls: HIGH -- well-known domain with established best practices
- Frontend: HIGH -- follows exact same pattern as ProfilePage (settings route + React Query)

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (stable domain, no fast-moving dependencies)
