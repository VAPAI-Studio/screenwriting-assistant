# Phase 35: Real Authentication & User Model - Research

**Researched:** 2026-03-23
**Domain:** Authentication, JWT, Password Hashing, User Management (FastAPI + React)
**Confidence:** HIGH

## Summary

This phase replaces the MockAuthService with a production-ready authentication system. The existing codebase already has most of the infrastructure in place -- `python-jose` for JWT, `passlib[bcrypt]` for password hashing, an `AuthService` class with `create_access_token`/`verify_token`/`verify_password`/`get_password_hash` methods, and a `get_current_user` dependency that already handles real JWT verification (falling back to mock-token in development mode). The work is primarily: (1) add a `User` SQLAlchemy model + migration, (2) wire register/login endpoints that create real users and issue real JWTs, (3) update `get_current_user` to query the actual user from the database, (4) add frontend login/register pages and an auth guard, and (5) add a profile settings page.

The existing `schemas.User` Pydantic model has `id`, `email`, `created_at` -- it needs `display_name` added. The `get_current_user` dependency already accepts `db: Session` but returns a hardcoded mock user; it just needs to be updated to query the `users` table. All 20+ endpoints use `Depends(get_current_user)` consistently, so the transition should be seamless once the dependency returns a real database-backed user.

**Primary recommendation:** Add a `User` SQLAlchemy model with delta migration 005, expand the existing `AuthService` with register/login methods that use the already-implemented bcrypt hashing and JWT creation, and build a minimal React login/register flow with a protected route wrapper that checks localStorage for the JWT token.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UM-01 | Users can register with email + password and receive a JWT | Existing AuthService has `get_password_hash()` and `create_access_token()` -- wire into a new register endpoint that creates a User row |
| UM-02 | Users can log in and receive a JWT; passwords stored as bcrypt hashes | Existing AuthService has `verify_password()` and bcrypt context -- wire into login endpoint |
| UM-03 | A `users` table exists with id, email, hashed_password, display_name, created_at | Delta migration 005 creates the table; new SQLAlchemy User model in database.py |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-jose[cryptography] | 3.3.0 | JWT encode/decode | Already in requirements.txt and installed; used by existing AuthService |
| passlib[bcrypt] | 1.7.4 | Password hashing | Already in requirements.txt and installed; bcrypt CryptContext already configured |
| bcrypt | 4.3.0 | Bcrypt backend for passlib | Already installed as passlib dependency |
| email-validator | 2.2.0 | Email validation (Pydantic EmailStr) | Already installed; used by existing schemas |
| pydantic[email] | >=2.10 | Pydantic v2 with EmailStr support | Already in requirements.txt |

### Frontend (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-router-dom | ^6.21.3 | Client-side routing | Route guards, /login, /settings/profile |
| @tanstack/react-query | ^5.20.1 | Server state management | Auth mutation hooks |
| lucide-react | ^0.314.0 | Icons | Lock, Mail, User icons for forms |
| @radix-ui/react-dialog | ^1.0.5 | Modal primitives | Can use for profile edit if needed |

### No New Dependencies Required
This phase requires **zero new npm or pip packages**. Everything needed is already installed:
- Backend: python-jose, passlib, bcrypt, email-validator, SQLAlchemy, Pydantic
- Frontend: react-router-dom, react-query, Tailwind CSS, Radix UI primitives

**Installation:**
```bash
# No installation needed -- all dependencies already present
```

## Architecture Patterns

### Backend Changes

```
backend/
  app/
    models/
      database.py         # ADD: User model (SQLAlchemy)
      schemas.py          # UPDATE: UserCreate, UserResponse, LoginRequest, RegisterRequest, expand User
    services/
      auth_service.py     # UPDATE: add register_user(), authenticate_user() methods
    api/
      dependencies.py     # UPDATE: get_current_user queries real User from DB
      endpoints/
        auth.py           # REWRITE: register, login endpoints (replace mock/magic-link)
    config.py             # No changes needed (SECRET_KEY already exists)
  migrations/
    delta/
      005_users_table.sql # NEW: users table migration
```

### Frontend Changes

```
frontend/src/
  components/
    Auth/
      LoginPage.tsx         # NEW: email + password login form
      RegisterPage.tsx      # NEW: email + password + display_name register form
      ProtectedRoute.tsx    # NEW: wrapper that redirects to /login if no token
    Settings/
      ProfilePage.tsx       # NEW: show email, display_name, edit form
  lib/
    api.tsx                 # UPDATE: add register(), login(), getProfile(), updateProfile()
    auth.ts                 # NEW: auth helpers (isAuthenticated, logout, getToken)
    constants.ts            # UPDATE: add QUERY_KEYS for auth
  types/
    index.ts               # UPDATE: expand User type, add LoginRequest, RegisterResponse
  App.tsx                   # UPDATE: add /login, /register, /settings/profile routes; wrap existing routes with ProtectedRoute
```

### Pattern 1: User SQLAlchemy Model
**What:** A `User` database model that mirrors the `users` table
**When to use:** This is the foundation -- all auth flows create or query User records
**Example:**
```python
# backend/app/models/database.py
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Pattern 2: Updated get_current_user Dependency
**What:** Replace mock user return with real DB query
**When to use:** This is the single point of auth for all endpoints
**Example:**
```python
# backend/app/api/dependencies.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> schemas.User:
    # Keep mock-token support for development/tests
    if settings.ENVIRONMENT == "development" and credentials.credentials == "mock-token":
        # Return mock user OR find/create a dev user in DB
        return mock_auth_service.get_current_user()

    user_id = auth_service.verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = db.query(database.User).filter(database.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return schemas.User(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
    )
```

### Pattern 3: Frontend Auth Guard (ProtectedRoute)
**What:** A wrapper component that checks for JWT in localStorage and redirects to /login if missing
**When to use:** Wrap all authenticated routes
**Example:**
```typescript
// frontend/src/components/Auth/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { AUTH_TOKEN_KEY } from '../../lib/constants';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
```

### Pattern 4: Login/Register API Flow
**What:** Frontend calls POST /api/auth/register or /api/auth/login, stores returned JWT in localStorage
**When to use:** Login and register pages
**Example:**
```typescript
// frontend/src/lib/api.tsx additions
async register(data: { email: string; password: string; display_name?: string }) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await response.text());
  const result = await response.json();
  localStorage.setItem(AUTH_TOKEN_KEY, result.access_token);
  return result;
},

async login(data: { email: string; password: string }) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await response.text());
  const result = await response.json();
  localStorage.setItem(AUTH_TOKEN_KEY, result.access_token);
  return result;
},
```

### Anti-Patterns to Avoid
- **Storing plaintext passwords:** Never store or log raw passwords. Always bcrypt hash before DB write. The existing `pwd_context.hash()` handles this.
- **JWT in cookies for this app:** The codebase consistently uses `Authorization: Bearer` header from localStorage. Don't switch to cookie-based auth -- it would break all existing API calls.
- **Breaking mock-token during transition:** Tests use `Bearer mock-token` extensively. Keep the mock-token path in `get_current_user` for `ENVIRONMENT == "development"` to avoid breaking 100+ test cases.
- **Hardcoded user IDs in mock service:** The mock auth returns `UUID("12345678-1234-5678-1234-567812345678")`. If we add a real users table, we should ensure this UUID exists as a dev seed user, or tests will fail when queries join on user_id.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | `passlib[bcrypt]` CryptContext (already configured) | Bcrypt handles salting, work factor, timing-safe comparison |
| JWT creation/verification | Custom token format | `python-jose` (already configured) | Handles expiry, signing, algorithm selection |
| Email validation | Regex-based validation | Pydantic `EmailStr` (already used) | RFC-compliant validation including MX checks |
| Form validation (frontend) | Manual state + regex | HTML5 `required` + `type="email"` + simple state | No need for react-hook-form for 2 simple forms |
| Auth state management | Redux/Context auth store | localStorage + React Query invalidation | Matches existing pattern; React Query already handles cache invalidation |

**Key insight:** The existing codebase already has 90% of the auth infrastructure. This phase is about wiring existing pieces together, not building new crypto or auth primitives.

## Common Pitfalls

### Pitfall 1: Breaking Existing Tests
**What goes wrong:** Tests use `Bearer mock-token` header. If mock-token support is removed, all tests fail.
**Why it happens:** Eager removal of mock auth before tests are updated.
**How to avoid:** Keep mock-token check in `get_current_user` conditional on `settings.ENVIRONMENT == "development"`. This is already the pattern -- just don't remove it.
**Warning signs:** Any test using `mock_auth_headers` fixture starts failing.

### Pitfall 2: User Schema Mismatch
**What goes wrong:** The `schemas.User` Pydantic model is used throughout all endpoints as the return type of `get_current_user`. Adding `display_name` to it without making it Optional breaks endpoints that construct User objects without display_name.
**Why it happens:** The mock auth service constructs `User(id=..., email=..., created_at=...)` without display_name.
**How to avoid:** Add `display_name: Optional[str] = None` to `schemas.User`. This is backward-compatible.
**Warning signs:** Pydantic validation errors on startup or in tests.

### Pitfall 3: Migration Sequence
**What goes wrong:** The `users` table references `UUID` primary key type. If migration 005 runs before the table is properly defined with PostgreSQL UUID support, it fails.
**Why it happens:** Attempting to add foreign keys from existing tables to users before users table exists.
**How to avoid:** Migration 005 should ONLY create the `users` table. Do NOT add FK constraints from `projects.owner_id` to `users.id` in this migration -- the existing owner_id column works fine without a FK constraint since it's just a UUID filter. Adding an FK would require backfilling all existing projects with valid user IDs, which is complex and unnecessary for this phase.
**Warning signs:** Migration errors referencing foreign key violations.

### Pitfall 4: Token Payload Structure
**What goes wrong:** The existing `AuthService.create_access_token` puts data in `sub` claim. New register/login must use the same `{"sub": str(user_id)}` format, or `verify_token()` won't extract the user_id correctly.
**Why it happens:** Inconsistent JWT payload structure between old and new code.
**How to avoid:** Always pass `{"sub": str(user.id)}` as the token data. The existing `verify_token()` already does `payload.get("sub")`.
**Warning signs:** `verify_token` returns None for newly issued tokens.

### Pitfall 5: bcrypt + passlib Version Compatibility
**What goes wrong:** passlib 1.7.4 has a known deprecation warning with bcrypt >= 4.1 (`AttributeError: module 'bcrypt' has no attribute '__about__'`).
**Why it happens:** passlib hasn't been updated since 2020; bcrypt 4.x changed its internal API.
**How to avoid:** The app already runs with these versions (bcrypt 4.3.0 + passlib 1.7.4), so it's a working combination. If warnings appear, they're non-fatal. Do NOT upgrade passlib -- it's abandoned. If needed in the future, switch to `bcrypt` directly, but for now passlib works.
**Warning signs:** Deprecation warnings in logs about `bcrypt.__about__`.

### Pitfall 6: Frontend 401 Redirect Loop
**What goes wrong:** The ProtectedRoute redirects to /login on missing token. If /login itself is inside ProtectedRoute, infinite redirect loop.
**Why it happens:** Wrapping ALL routes including /login in the auth guard.
**How to avoid:** /login and /register routes must be OUTSIDE the ProtectedRoute wrapper. Only authenticated routes (/, /projects, etc.) should be protected.
**Warning signs:** Browser tab crashes or shows blank page.

## Code Examples

### Delta Migration 005: Users Table
```sql
-- Migration 005: Users table for real authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);
```

### Register Endpoint
```python
# backend/app/api/endpoints/auth.py
@router.post("/register", response_model=Token)
async def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    # Check if email already exists
    existing = db.query(database.User).filter(database.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password and create user
    hashed = auth_service.get_password_hash(data.password)
    user = database.User(
        email=data.email,
        hashed_password=hashed,
        display_name=data.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Issue JWT
    token = auth_service.create_access_token({"sub": str(user.id)})
    return Token(access_token=token)
```

### Login Endpoint
```python
@router.post("/login", response_model=Token)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(database.User).filter(database.User.email == data.email).first()
    if not user or not auth_service.verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = auth_service.create_access_token({"sub": str(user.id)})
    return Token(access_token=token)
```

### Pydantic Schemas for Auth
```python
# backend/app/models/schemas.py additions
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=255)

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

# Update existing User schema:
class User(BaseModel):
    id: UUID
    email: EmailStr
    display_name: Optional[str] = None  # NEW - Optional for backward compat
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Frontend Auth Helper
```typescript
// frontend/src/lib/auth.ts
import { AUTH_TOKEN_KEY } from './constants';

export function isAuthenticated(): boolean {
  return !!localStorage.getItem(AUTH_TOKEN_KEY);
}

export function logout(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  window.location.href = '/login';
}

export function getToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mock auth with hardcoded `Bearer mock-token` | Real JWT with bcrypt passwords | This phase | All users get unique identities; data is properly scoped |
| `MockAuthService.get_current_user()` returns static User | `get_current_user()` queries DB User table | This phase | Real user lookup on every authenticated request |
| No registration flow | POST /api/auth/register with email + password | This phase | New users can create accounts |
| Magic link stubs (non-functional) | Email/password login | This phase | Replaces non-functional magic link endpoints |

**Deprecated/outdated:**
- `MockAuthService` class: Still needed for development/tests but no longer the production path
- `/api/auth/token/mock` endpoint: Keep for development convenience but not used in production
- `/api/auth/magic-link` and `/api/auth/verify-magic-link` endpoints: Remove or leave as dead code -- they were never functional

## Open Questions

1. **Should we add FK from projects.owner_id to users.id?**
   - What we know: owner_id is currently a plain UUID with no FK constraint. All existing data has the mock user UUID.
   - What's unclear: Adding a FK constraint would require backfilling all existing records with a real user ID, or creating a seed user with the mock UUID.
   - Recommendation: Do NOT add FK constraint in this phase. It works fine as a filter column. Phase 36+ can add FK if needed after data migration strategy is decided.

2. **Should email verification be included?**
   - What we know: The phase description mentions "email verification flow" but the success criteria don't require it.
   - What's unclear: Whether email verification is a hard requirement or aspirational.
   - Recommendation: Skip email verification in this phase. It requires an email provider (SendGrid, SES), which is infrastructure complexity outside the phase scope. Registration works without it -- just create the user immediately.

3. **What happens to existing data when switching from mock to real auth?**
   - What we know: All existing projects, books, agents have `owner_id = "12345678-1234-5678-1234-567812345678"` (the mock user ID).
   - What's unclear: Whether we need a data migration to reassign ownership.
   - Recommendation: Create a seed user in migration 005 with the mock UUID and email "user@example.com" so existing data automatically belongs to a real user. The mock auth can continue to return this user in development mode.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | None (uses conftest.py in backend/app/tests/) |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_auth.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UM-01 | Register with email+password returns JWT | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_register_success -x` | No -- Wave 0 |
| UM-01 | Register with existing email returns 400 | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_register_duplicate_email -x` | No -- Wave 0 |
| UM-01 | Register with weak password returns 422 | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_register_weak_password -x` | No -- Wave 0 |
| UM-02 | Login with valid credentials returns JWT | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_login_success -x` | No -- Wave 0 |
| UM-02 | Login with wrong password returns 401 | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_login_wrong_password -x` | No -- Wave 0 |
| UM-02 | Login with non-existent email returns 401 | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_login_nonexistent_user -x` | No -- Wave 0 |
| UM-03 | User table has correct columns | unit | `pytest app/tests/test_auth.py::TestUserModel::test_user_model_columns -x` | No -- Wave 0 |
| UM-03 | JWT from register is accepted by protected endpoints | integration | `pytest app/tests/test_auth.py::TestAuthAPI::test_jwt_accepted_by_endpoints -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_auth.py -x`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_auth.py` -- covers UM-01, UM-02, UM-03 (register, login, user model, JWT integration)
- [ ] Existing conftest.py needs User model added to SQLite test schema (handled automatically by `Base.metadata.create_all`)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/services/auth_service.py` -- existing AuthService with JWT + bcrypt
- Codebase inspection: `backend/app/api/dependencies.py` -- existing get_current_user with mock-token path
- Codebase inspection: `backend/app/models/database.py` -- no User model yet, but pattern established
- Codebase inspection: `backend/app/models/schemas.py` -- existing User Pydantic schema
- Codebase inspection: `backend/requirements.txt` -- python-jose, passlib already listed
- Codebase inspection: `backend/app/services/db_migrator.py` -- delta migration pattern
- Codebase inspection: `backend/app/tests/conftest.py` -- test setup with SQLite + mock-token

### Secondary (MEDIUM confidence)
- Package versions verified via `pip show`: python-jose 3.3.0, passlib 1.7.4, bcrypt 4.3.0, email-validator 2.2.0

### Tertiary (LOW confidence)
- None -- all findings verified from codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and used in codebase
- Architecture: HIGH - extending existing patterns (SQLAlchemy model, Pydantic schema, FastAPI dependency, delta migration)
- Pitfalls: HIGH - based on direct code inspection of mock auth path, test fixtures, and schema usage

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no external dependencies or fast-moving APIs)
