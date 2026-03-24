# Phase 36: Show Data Model & CRUD API - Research

**Researched:** 2026-03-24
**Domain:** SQLAlchemy model + FastAPI CRUD for a new "Show" entity
**Confidence:** HIGH

## Summary

Phase 36 introduces a new `Show` entity to support TV show mode. This is a straightforward data model + CRUD phase that follows well-established patterns already used extensively in this codebase (Project, Shot, BreakdownElement all follow the same SQLAlchemy model + Pydantic schema + FastAPI router + delta migration pattern).

The Show model needs: `id`, `title`, `description`, `owner_id` (FK to users), `created_at`, `updated_at`. It must support cascade deletes for downstream data (bible columns added in Phase 37, episodes linked in Phase 39). The CRUD endpoints follow the exact same auth + ownership pattern as projects.py.

**Primary recommendation:** Follow the existing Project CRUD pattern exactly -- SQLAlchemy model in database.py, Pydantic schemas in schemas.py, router in a new `shows.py` endpoint file, delta migration `006_shows_table.sql`, and register the router in main.py under `/api/shows`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHOW-01 | User can create a new show with a title and description | POST /api/shows endpoint with ShowCreate schema (title + description fields), owner_id from authenticated user |
| SHOW-04 | User can edit a show's title and description, and delete a show | PUT /api/shows/{id} for update, DELETE /api/shows/{id} for deletion with cascade delete for future bible/episode data |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | (existing in project) | ORM model definition | Already used for all 15+ models in database.py |
| FastAPI | (existing in project) | REST endpoint router | Already used for all endpoint modules |
| Pydantic v2 | (existing in project) | Request/response schemas | Already used for all schemas in schemas.py |
| PostgreSQL 15 | (existing in project) | Database | Project standard, UUID primary keys |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + TestClient | (existing in project) | API integration tests | Test all CRUD operations using existing conftest.py fixtures |

### Alternatives Considered
None -- this phase uses only existing stack components. No new libraries needed.

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── models/
│   │   ├── database.py          # ADD: Show model (between User and SectionType)
│   │   └── schemas.py           # ADD: ShowCreate, ShowUpdate, ShowResponse schemas
│   ├── api/
│   │   └── endpoints/
│   │       └── shows.py         # NEW: Show CRUD router
│   ├── main.py                  # ADD: register shows router
│   └── tests/
│       └── test_shows_api.py    # NEW: Show CRUD tests
├── migrations/
│   └── delta/
│       └── 006_shows_table.sql  # NEW: delta migration
```

### Pattern 1: SQLAlchemy Model (follow User/Project pattern)
**What:** Define Show as a SQLAlchemy declarative model with UUID PK, owner_id FK, timestamps
**When to use:** This is the only data modeling pattern in this project
**Example:**
```python
# Source: existing database.py patterns (User, Project models)
class Show(Base):
    __tablename__ = "shows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships added by future phases:
    # - Phase 39 will add: episodes = sa_relationship("Project", back_populates="show", ...)
```

### Pattern 2: Pydantic v2 Schemas (follow Project schemas pattern)
**What:** Create/Update/Response schemas with field validators
**When to use:** All API request/response models
**Example:**
```python
# Source: existing schemas.py patterns (ProjectBase, ProjectCreate, Project)
class ShowCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(default="", max_length=5000)

    @field_validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty or just whitespace")
        return v.strip()

class ShowUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)

class ShowResponse(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
```

### Pattern 3: CRUD Router (follow projects.py pattern)
**What:** FastAPI router with ownership-scoped CRUD endpoints
**When to use:** All entity endpoints that belong to a user
**Example:**
```python
# Source: existing projects.py and shots.py patterns
router = APIRouter()

@router.post("/", response_model=ShowResponse, status_code=status.HTTP_201_CREATED)
async def create_show(
    body: ShowCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_show = database.Show(
        title=body.title,
        description=body.description,
        owner_id=current_user.id,
    )
    db.add(db_show)
    db.commit()
    db.refresh(db_show)
    return db_show

@router.get("/", response_model=List[ShowResponse])
async def list_shows(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    shows = db.query(database.Show).filter(
        database.Show.owner_id == current_user.id
    ).order_by(database.Show.created_at.desc()).all()
    return shows
```

### Pattern 4: Delta Migration (follow 005_users_table.sql pattern)
**What:** Idempotent SQL migration file auto-applied on startup
**When to use:** All schema changes
**Example:**
```sql
-- Migration 006: Shows table for TV show mode
CREATE TABLE IF NOT EXISTS shows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_shows_owner_id ON shows(owner_id);
```

### Pattern 5: Router Registration (follow main.py pattern)
**What:** Import and register the router in main.py with prefix and tags
**When to use:** Every new endpoint module
**Example:**
```python
# In main.py
from .api.endpoints import shows as shows_ep
app.include_router(shows_ep.router, prefix="/api/shows", tags=["shows"])
```

### Anti-Patterns to Avoid
- **Alembic migrations:** This project does NOT use Alembic. Use the delta migration system in `backend/migrations/delta/`.
- **Separate service layer for simple CRUD:** The projects endpoint handles CRUD directly in the router -- no service class needed for basic create/read/update/delete.
- **Using PATCH for updates:** The success criteria specifies PUT for show updates. Use PUT (full update of title + description), not PATCH.
- **Forgetting owner_id scoping:** Every query MUST filter by `owner_id == current_user.id` to enforce data isolation.
- **Using `str(uuid)` in queries:** The codebase inconsistently uses `str()` wrapping for UUIDs in queries (see shots.py). For consistency with the Show model, follow the same pattern used in the projects endpoint which does NOT wrap -- let SQLAlchemy handle UUID comparison.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth + user extraction | Custom auth middleware | `Depends(get_current_user)` from dependencies.py | Already handles JWT + mock-token, returns schemas.User |
| UUID primary keys | String IDs or auto-increment | `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)` | Consistent with all 15+ existing models |
| Cascade deletes | Manual deletion logic | SQLAlchemy `cascade="all, delete-orphan"` on relationships | Will be added when episodes (Phase 39) link to shows |
| Input validation | Manual if/else checks | Pydantic field validators + Field constraints | Consistent with existing schemas |
| DB session management | Manual open/close | `Depends(get_db)` from dependencies.py | Handles session lifecycle automatically |

**Key insight:** This phase is 100% following existing patterns. Zero new concepts or libraries are needed.

## Common Pitfalls

### Pitfall 1: Forgetting to add ForeignKey to users table
**What goes wrong:** owner_id column exists but has no FK constraint, allowing orphaned shows
**Why it happens:** The existing Project model's owner_id does NOT have a ForeignKey -- it's just a plain UUID column. The Show model should do better since Phase 35 now has a real users table.
**How to avoid:** Add `ForeignKey("users.id")` in the model AND in the migration SQL (`REFERENCES users(id)`)
**Warning signs:** Shows persist after user deletion

### Pitfall 2: Not planning for cascade deletes from shows to future children
**What goes wrong:** Phase 37 (bible) and Phase 39 (episodes) will add child data to shows. If delete doesn't cascade, orphaned data remains.
**Why it happens:** Cascade relationships need to be planned when the parent is created
**How to avoid:** Design the Show model with placeholder comments for future relationships. The actual cascade setup happens in Phase 37/39 when child tables are added. The DELETE endpoint should work correctly NOW (just deletes the show row) and will cascade LATER when relationships are added.
**Warning signs:** Orphaned bible/episode rows after show deletion

### Pitfall 3: Missing index on owner_id
**What goes wrong:** GET /api/shows (list all for user) becomes slow as data grows
**Why it happens:** Forgetting to add index in migration
**How to avoid:** Add `index=True` on the SQLAlchemy column AND `CREATE INDEX IF NOT EXISTS` in the migration
**Warning signs:** Slow list queries

### Pitfall 4: Inconsistent HTTP method for update
**What goes wrong:** Success criteria says PUT but implementation uses PATCH
**Why it happens:** PATCH is more common for partial updates, but the success criteria explicitly says PUT
**How to avoid:** Use `@router.put()` as specified. Both title and description can be provided; update whichever fields are present.
**Warning signs:** Test failures against success criteria

### Pitfall 5: SQLite test compatibility
**What goes wrong:** Tests fail because SQLite handles UUIDs and timestamps differently than PostgreSQL
**Why it happens:** conftest.py patches UUID columns to String(36) for SQLite, but new models need to be compatible
**How to avoid:** The existing conftest.py `_patch_uuid_columns_for_sqlite()` iterates ALL tables in `Base.metadata` -- so adding Show to database.py is automatically covered. Just ensure the model uses standard column types.
**Warning signs:** Test failures with type errors

## Code Examples

Verified patterns from the existing codebase:

### Complete CRUD endpoint pattern (derived from projects.py + shots.py)
```python
# Source: backend/app/api/endpoints/projects.py (create, list, get, update, delete)
# This is the exact pattern every CRUD router in the project follows.

# Create: POST /
@router.post("/", response_model=schemas.ShowResponse, status_code=201)
async def create_show(body: schemas.ShowCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    db_show = database.Show(title=body.title, description=body.description, owner_id=current_user.id)
    db.add(db_show)
    db.commit()
    db.refresh(db_show)
    return db_show

# List: GET / (owner-scoped)
@router.get("/", response_model=List[schemas.ShowResponse])
async def list_shows(current_user=Depends(get_current_user), db=Depends(get_db)):
    return db.query(database.Show).filter(
        database.Show.owner_id == current_user.id
    ).order_by(database.Show.created_at.desc()).all()

# Get: GET /{show_id}
@router.get("/{show_id}", response_model=schemas.ShowResponse)
async def get_show(show_id: UUID, current_user=Depends(get_current_user), db=Depends(get_db)):
    show = db.query(database.Show).filter(
        database.Show.id == show_id, database.Show.owner_id == current_user.id
    ).first()
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return show

# Update: PUT /{show_id}
@router.put("/{show_id}", response_model=schemas.ShowResponse)
async def update_show(show_id: UUID, body: schemas.ShowUpdate, current_user=Depends(get_current_user), db=Depends(get_db)):
    show = db.query(database.Show).filter(
        database.Show.id == show_id, database.Show.owner_id == current_user.id
    ).first()
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(show, field, value)
    db.commit()
    db.refresh(show)
    return show

# Delete: DELETE /{show_id}
@router.delete("/{show_id}")
async def delete_show(show_id: UUID, current_user=Depends(get_current_user), db=Depends(get_db)):
    show = db.query(database.Show).filter(
        database.Show.id == show_id, database.Show.owner_id == current_user.id
    ).first()
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    db.delete(show)
    db.commit()
    return {"status": "success", "message": "Show deleted"}
```

### Test pattern (derived from test_auth.py + test_shots_api.py)
```python
# Source: backend/app/tests/test_auth.py, test_shots_api.py

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"

class TestShowsAPI:
    def test_create_show(self, client, mock_auth_headers):
        resp = client.post("/api/shows/", json={"title": "Breaking Bad", "description": "A chemistry teacher..."}, headers=mock_auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Breaking Bad"
        assert "id" in data

    def test_list_shows(self, client, mock_auth_headers):
        # Create two shows, verify list returns both
        client.post("/api/shows/", json={"title": "Show 1"}, headers=mock_auth_headers)
        client.post("/api/shows/", json={"title": "Show 2"}, headers=mock_auth_headers)
        resp = client.get("/api/shows/", headers=mock_auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_show(self, client, mock_auth_headers):
        create_resp = client.post("/api/shows/", json={"title": "Old Title"}, headers=mock_auth_headers)
        show_id = create_resp.json()["id"]
        update_resp = client.put(f"/api/shows/{show_id}", json={"title": "New Title"}, headers=mock_auth_headers)
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "New Title"

    def test_delete_show(self, client, mock_auth_headers):
        create_resp = client.post("/api/shows/", json={"title": "Doomed Show"}, headers=mock_auth_headers)
        show_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/shows/{show_id}", headers=mock_auth_headers)
        assert del_resp.status_code == 200
        # Verify gone
        get_resp = client.get(f"/api/shows/{show_id}", headers=mock_auth_headers)
        assert get_resp.status_code == 404
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mock auth only | Real JWT auth (Phase 35) | 2026-03-23 | Show endpoints use `get_current_user` which handles both JWT and mock-token |
| No FK on owner_id | FK to users table | Phase 35 added users | Show can now have a real FK to users.id |
| Manual schema migrations | Delta migration runner | Phase 16 | Use `backend/migrations/delta/006_*.sql` pattern |

**Deprecated/outdated:**
- Mock auth is still supported for dev but real JWT is the primary auth mechanism since Phase 35

## Open Questions

1. **Should DELETE cascade to bible/episodes now or later?**
   - What we know: Phase 37 adds bible columns (on Show table itself), Phase 39 adds episode FK from projects
   - What's unclear: Whether to add cascade delete logic now or wait
   - Recommendation: Add cascade relationships as they are created in later phases. For now, DELETE just removes the show row. Bible columns (Phase 37) will be on the Show table itself so they delete with the row. Episode cascade (Phase 39) will be added when the FK is created.

2. **Should the response include episode_count or bible status?**
   - What we know: Phase 38 success criteria mentions "episode count" in the home page list
   - What's unclear: Whether to add computed fields to the response now
   - Recommendation: Keep ShowResponse simple for Phase 36. Phase 38/39 can extend the response schema when those features exist.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with FastAPI TestClient |
| Config file | backend/app/tests/conftest.py (session-scoped SQLite engine, per-function db_session, mock_auth_headers) |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHOW-01 | Create show with title and description | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_create_show -x` | No -- Wave 0 |
| SHOW-01 | Created show has id, owner_id, timestamps | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_create_show_fields -x` | No -- Wave 0 |
| SHOW-01 | Validation rejects empty title | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_create_show_empty_title -x` | No -- Wave 0 |
| SHOW-04 | List shows returns user's shows only | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_list_shows -x` | No -- Wave 0 |
| SHOW-04 | Update show title and description | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_update_show -x` | No -- Wave 0 |
| SHOW-04 | Delete show removes it from DB | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_delete_show -x` | No -- Wave 0 |
| SHOW-04 | Delete nonexistent show returns 404 | integration | `pytest app/tests/test_shows_api.py::TestShowsAPI::test_delete_show_not_found -x` | No -- Wave 0 |
| SC-1 | shows table exists with correct columns | unit (model) | `pytest app/tests/test_shows_api.py::TestShowModel::test_show_model_columns -x` | No -- Wave 0 |
| SC-5 | DELETE removes associated data | integration | Deferred to Phase 37/39 when child data exists | N/A |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -x`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_shows_api.py` -- covers SHOW-01, SHOW-04 (model test + all CRUD tests)
- No framework install needed (pytest already configured)
- No conftest changes needed (existing fixtures cover shows via Base.metadata)

## Sources

### Primary (HIGH confidence)
- `backend/app/models/database.py` -- existing model patterns (User, Project, Shot, etc.)
- `backend/app/models/schemas.py` -- existing Pydantic v2 schema patterns
- `backend/app/api/endpoints/projects.py` -- CRUD router pattern for user-owned entities
- `backend/app/api/endpoints/shots.py` -- another CRUD router pattern with ownership verification
- `backend/app/api/dependencies.py` -- get_current_user dependency pattern
- `backend/app/services/db_migrator.py` -- delta migration system
- `backend/migrations/delta/005_users_table.sql` -- latest migration file format
- `backend/app/tests/conftest.py` -- test infrastructure (SQLite, fixtures)
- `backend/app/tests/test_auth.py` -- test patterns for new models
- `backend/app/main.py` -- router registration pattern

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` -- SHOW-01, SHOW-04 requirement definitions
- `.planning/STATE.md` -- architectural decisions (bible on Show model, episodes reuse Project)

### Tertiary (LOW confidence)
- None -- all findings based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uses only existing project dependencies, no new libraries
- Architecture: HIGH -- follows exact same patterns as 15+ existing models/endpoints
- Pitfalls: HIGH -- derived from direct codebase inspection of existing patterns and their edge cases

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependencies to become stale)
