# Phase 37: Series Bible Data & API - Research

**Researched:** 2026-03-24
**Domain:** Backend data modeling, REST API design (FastAPI + SQLAlchemy + Pydantic v2)
**Confidence:** HIGH

## Summary

Phase 37 extends the Show model (created in Phase 36) with four bible text fields and an episode duration setting, then exposes two new API endpoints for reading and writing bible content. This is a straightforward "add columns + add endpoints" phase with no new libraries, no new services, and no architectural novelty. The entire phase fits cleanly into the existing patterns established across 36 prior phases.

The Show model currently has: id, owner_id, title, description, created_at, updated_at. Phase 37 adds five new columns directly to this model (four Text columns for bible sections, one Integer for episode duration) and two new endpoints nested under the existing `/api/shows` router. No new tables, no new router files, no new dependencies.

**Primary recommendation:** Add bible columns directly to the Show SQLAlchemy model, create a delta migration (007_bible_columns.sql), add BibleUpdate/BibleResponse Pydantic schemas, and add GET/PUT `/api/shows/{id}/bible` endpoints to the existing shows router. Test with the same patterns used in test_shows_api.py.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BIBL-01 | Each show has four bible sections: Characters, World/Setting, Season Arc, Tone & Style | Add four Text columns to Show model: `bible_characters`, `bible_world_setting`, `bible_season_arc`, `bible_tone_style`. Default to empty string. Delta migration adds columns with `ADD COLUMN IF NOT EXISTS`. |
| BIBL-02 | User can write and edit each bible section as freeform text | PUT `/api/shows/{id}/bible` accepts partial updates via `exclude_unset=True` pattern already used in ShowUpdate. Each field is Optional[str] with max_length validation. |
| BIBL-03 | Each show has a target episode duration setting (10, 22, 44, 60, or custom) | Add `episode_duration_minutes` Integer column to Show model, nullable, default None. The API accepts any positive integer -- the preset values (10, 22, 44, 60) are a frontend/UI concern, not a backend constraint. Backend validates `ge=1, le=480` (8 hours max as sanity check). |
</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.110.0 | REST API framework | Already in use, provides routing, dependency injection, validation |
| SQLAlchemy | 2.0.27 | ORM / database models | Already in use, provides Column types, relationships |
| Pydantic v2 | >=2.10 | Request/response schemas | Already in use, provides field validators, model_dump |
| PostgreSQL | 15 | Database | Already in use, supports Text columns, Integer columns |
| pytest | 8.0.2 | Testing | Already in use with TestClient pattern |

### Supporting
No new libraries needed. This phase uses only existing stack components.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Text columns on Show | Separate `bible_sections` table with section_type enum | Unnecessary complexity for only 4 fixed sections. STATE.md explicitly decides "Bible stored as columns on Show model (not separate table) for simplicity." |
| Text columns | JSONB single column | Would lose individual column querying, adds serialization complexity. Four separate Text columns are simpler and directly addressable. |
| Integer for duration | Enum for duration presets | Would prevent custom values. The requirement explicitly says "custom integer entry" must be supported. Integer with validation is correct. |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure (changes only)
```
backend/
├── app/
│   ├── models/
│   │   ├── database.py          # ADD: bible + duration columns to Show model
│   │   └── schemas.py           # ADD: BibleUpdate, BibleResponse schemas
│   ├── api/endpoints/
│   │   └── shows.py             # ADD: GET/PUT /{show_id}/bible endpoints
│   └── tests/
│       └── test_shows_api.py    # ADD: TestBibleAPI test class
├── migrations/delta/
│   └── 007_bible_columns.sql    # NEW: alter shows table
```

### Pattern 1: Column Addition on Existing Model
**What:** Add new columns directly to the Show SQLAlchemy model and corresponding delta migration.
**When to use:** When extending an entity with fixed, known fields (not dynamic/variable-count data).
**Example:**
```python
# In database.py -- Show model
class Show(Base):
    __tablename__ = "shows"
    # ... existing columns ...

    # Bible sections (Phase 37)
    bible_characters = Column(Text, default="")
    bible_world_setting = Column(Text, default="")
    bible_season_arc = Column(Text, default="")
    bible_tone_style = Column(Text, default="")
    episode_duration_minutes = Column(Integer, nullable=True)
```

### Pattern 2: Sub-resource Endpoint on Existing Router
**What:** Add GET/PUT endpoints for a "virtual sub-resource" (bible) on the existing shows router, rather than creating a new router file.
**When to use:** When the sub-resource is tightly coupled to the parent (bible IS part of Show, not a separate entity).
**Example:**
```python
# In shows.py -- added to existing router
@router.get("/{show_id}/bible", response_model=schemas.BibleResponse)
async def get_bible(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    show = db.query(database.Show).filter(
        database.Show.id == str(show_id),
        database.Show.owner_id == str(current_user.id),
    ).first()
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return show  # BibleResponse picks the relevant fields via from_attributes
```

### Pattern 3: Partial Update with exclude_unset
**What:** Use Pydantic's `model_dump(exclude_unset=True)` to allow PATCH-like partial updates via PUT.
**When to use:** When the client should be able to update any subset of fields without sending all of them.
**Example:**
```python
@router.put("/{show_id}/bible", response_model=schemas.BibleResponse)
async def update_bible(
    show_id: UUID,
    body: schemas.BibleUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    show = db.query(database.Show).filter(
        database.Show.id == str(show_id),
        database.Show.owner_id == str(current_user.id),
    ).first()
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(show, field, value)
    db.commit()
    db.refresh(show)
    return show
```

### Pattern 4: Delta Migration with ADD COLUMN IF NOT EXISTS
**What:** Use idempotent SQL in the delta migration file.
**When to use:** Always -- the db_migrator pattern requires idempotent migrations.
**Example:**
```sql
-- Migration 007: Bible sections and episode duration on shows table (v4.2)
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_characters TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_world_setting TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_season_arc TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_tone_style TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS episode_duration_minutes INTEGER;
```

### Anti-Patterns to Avoid
- **Separate bible_sections table with rows per section:** Overengineered for 4 fixed sections. The project STATE.md explicitly decided against this.
- **JSONB blob for all bible data:** Would require manual serialization/deserialization, lose type safety on individual fields, and complicate partial updates.
- **Constraining duration to enum values only:** The requirement explicitly requires "custom integer entry." The preset values (10, 22, 44, 60) are UI suggestions, not database constraints.
- **Creating a new router file for bible endpoints:** The bible is a sub-resource of Show. Adding endpoints to the existing shows.py router keeps things cohesive and avoids router registration overhead.
- **Not using `str()` cast on UUID filters:** Phase 36 established that SQLite test compatibility requires `str(show_id)` and `str(current_user.id)` in SQLAlchemy filter clauses. This MUST be maintained.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Partial update logic | Custom diff/merge code | `model_dump(exclude_unset=True)` + setattr loop | Already used in ShowUpdate, handles Optional fields correctly |
| Schema validation | Manual field checks | Pydantic field validators + Field constraints | Pydantic already handles max_length, ge/le, Optional |
| DB migration | Manual ALTER TABLE in Python | Delta SQL migration file (007_bible_columns.sql) | db_migrator service handles execution, tracking, idempotency |
| Auth + ownership check | Custom middleware | `Depends(get_current_user)` + owner_id filter | Established pattern in every endpoint |

**Key insight:** This phase introduces zero new patterns. Every component (column addition, schema creation, endpoint creation, migration, testing) follows an exact precedent from Phase 36 or earlier phases.

## Common Pitfalls

### Pitfall 1: Forgetting str() Cast on UUID Filters
**What goes wrong:** SQLite tests fail with type mismatch errors when comparing UUID objects to string-stored UUIDs.
**Why it happens:** The conftest patches PostgreSQL UUID columns to String(36) for SQLite, but filter values still need explicit str() conversion.
**How to avoid:** Always use `database.Show.id == str(show_id)` and `database.Show.owner_id == str(current_user.id)` in queries.
**Warning signs:** Tests pass in PostgreSQL but fail in pytest (SQLite).

### Pitfall 2: BibleResponse Not Including Duration
**What goes wrong:** GET /bible returns four text sections but omits episode_duration_minutes.
**Why it happens:** Forgetting to add the duration field to the BibleResponse schema.
**How to avoid:** BibleResponse must include all five fields: bible_characters, bible_world_setting, bible_season_arc, bible_tone_style, episode_duration_minutes.

### Pitfall 3: ShowResponse Regression
**What goes wrong:** Existing GET /api/shows endpoints break because ShowResponse doesn't include new columns, or includes them unexpectedly.
**Why it happens:** Adding columns to the model without considering whether they should appear in ShowResponse.
**How to avoid:** Keep ShowResponse unchanged (it uses `from_attributes=True` so new columns are silently ignored unless explicitly added). The bible data is accessed via the separate `/bible` endpoint. If desired for Phase 38 (UI), bible fields can optionally be added to ShowResponse later, but for Phase 37 the dedicated bible endpoint is sufficient.

### Pitfall 4: Migration Not Idempotent
**What goes wrong:** Migration fails on second run or in environments where it was partially applied.
**Why it happens:** Using `ALTER TABLE ADD COLUMN` without `IF NOT EXISTS`.
**How to avoid:** Always use `ADD COLUMN IF NOT EXISTS` in PostgreSQL delta migrations.

### Pitfall 5: Duration Validation Too Restrictive
**What goes wrong:** Users cannot enter custom duration values that don't match presets.
**Why it happens:** Using an enum or set of allowed values instead of an integer range.
**How to avoid:** Use `Optional[int] = Field(None, ge=1, le=480)` in the schema. The UI will offer presets but the API accepts any positive integer.

## Code Examples

Verified patterns from the existing codebase:

### Database Model Extension
```python
# Source: backend/app/models/database.py (existing Show model pattern)
class Show(Base):
    __tablename__ = "shows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Bible sections (Phase 37)
    bible_characters = Column(Text, default="")
    bible_world_setting = Column(Text, default="")
    bible_season_arc = Column(Text, default="")
    bible_tone_style = Column(Text, default="")
    episode_duration_minutes = Column(Integer, nullable=True)
```

### Pydantic Schemas
```python
# Source: follows existing ShowUpdate/ShowResponse pattern in schemas.py

class BibleUpdate(BaseModel):
    """Request body for PUT /api/shows/{id}/bible. All fields optional for partial updates."""
    bible_characters: Optional[str] = Field(None, max_length=50000)
    bible_world_setting: Optional[str] = Field(None, max_length=50000)
    bible_season_arc: Optional[str] = Field(None, max_length=50000)
    bible_tone_style: Optional[str] = Field(None, max_length=50000)
    episode_duration_minutes: Optional[int] = Field(None, ge=1, le=480)


class BibleResponse(BaseModel):
    """Response for GET/PUT /api/shows/{id}/bible."""
    show_id: UUID
    bible_characters: str = ""
    bible_world_setting: str = ""
    bible_season_arc: str = ""
    bible_tone_style: str = ""
    episode_duration_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
```

Note: BibleResponse needs a `show_id` field mapped from Show's `id` field. This can be handled either by a model_validator or by constructing the response explicitly in the endpoint rather than relying solely on `from_attributes`.

### Delta Migration
```sql
-- Source: follows pattern from 006_shows_table.sql
-- Migration 007: Bible sections and episode duration on shows table (v4.2)
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_characters TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_world_setting TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_season_arc TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_tone_style TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS episode_duration_minutes INTEGER;
```

### Endpoint Pattern (Sub-resource)
```python
# Source: follows existing shows.py CRUD pattern
@router.get("/{show_id}/bible", response_model=schemas.BibleResponse)
async def get_bible(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return schemas.BibleResponse(
        show_id=show.id,
        bible_characters=show.bible_characters or "",
        bible_world_setting=show.bible_world_setting or "",
        bible_season_arc=show.bible_season_arc or "",
        bible_tone_style=show.bible_tone_style or "",
        episode_duration_minutes=show.episode_duration_minutes,
    )
```

### Test Pattern
```python
# Source: follows existing TestShowsAPI pattern in test_shows_api.py
class TestBibleAPI:
    def _create_show(self, client, mock_auth_headers):
        resp = client.post("/api/shows/", json={"title": "Bible Test Show"}, headers=mock_auth_headers)
        return resp.json()["id"]

    def test_get_bible_defaults(self, client, mock_auth_headers):
        show_id = self._create_show(client, mock_auth_headers)
        resp = client.get(f"/api/shows/{show_id}/bible", headers=mock_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["bible_characters"] == ""
        assert data["bible_world_setting"] == ""
        assert data["bible_season_arc"] == ""
        assert data["bible_tone_style"] == ""
        assert data["episode_duration_minutes"] is None

    def test_update_bible_partial(self, client, mock_auth_headers):
        show_id = self._create_show(client, mock_auth_headers)
        resp = client.put(
            f"/api/shows/{show_id}/bible",
            json={"bible_characters": "Walter White - chemistry teacher turned drug lord"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["bible_characters"] == "Walter White - chemistry teacher turned drug lord"
        assert resp.json()["bible_world_setting"] == ""  # unchanged
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Alembic migrations | Custom delta migration runner (db_migrator.py) | Project inception | Use numbered SQL files in migrations/delta/ instead of alembic commands |
| Separate table per entity feature | Columns on parent model | STATE.md decision | Bible is columns on Show, not a separate table |
| Strict enum for duration | Integer with validation | Phase 37 requirement | Supports both preset and custom duration values |

**Deprecated/outdated:**
- None -- this is standard CRUD extension work with no deprecation concerns.

## Open Questions

1. **Should ShowResponse also include bible fields?**
   - What we know: Phase 37 requires dedicated GET/PUT bible endpoints. Phase 38 (UI) will need bible data when rendering the show detail page.
   - What's unclear: Whether Phase 38 will fetch bible separately or expect it in the show response.
   - Recommendation: Keep ShowResponse unchanged for Phase 37. The dedicated /bible endpoint satisfies requirements BIBL-01/02/03. Phase 38 can extend ShowResponse if needed, or use the separate endpoint.

2. **Max length for bible text fields?**
   - What we know: Existing section user_notes use max_length=10000. Bible sections are "freeform text" with no explicit size requirement.
   - What's unclear: How long bible sections might realistically be.
   - Recommendation: Use 50000 characters (about 10,000-12,000 words) per section. This is generous for a series bible section while still preventing abuse. The database column is unbounded Text; the validation limit is only in the Pydantic schema.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | backend/pytest.ini (if exists) or default discovery |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -x -q` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BIBL-01 | Show model has four bible text fields with defaults | unit | `pytest app/tests/test_shows_api.py::TestBibleModel -x` | No -- Wave 0 |
| BIBL-01 | GET /bible returns all four sections | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_get_bible_defaults -x` | No -- Wave 0 |
| BIBL-02 | PUT /bible updates any combination of sections | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_update_bible_partial -x` | No -- Wave 0 |
| BIBL-02 | PUT /bible full update round-trip | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_update_bible_full -x` | No -- Wave 0 |
| BIBL-03 | GET /bible returns episode_duration_minutes | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_get_bible_defaults -x` | No -- Wave 0 |
| BIBL-03 | PUT /bible sets custom duration | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_update_duration_custom -x` | No -- Wave 0 |
| BIBL-03 | PUT /bible sets preset duration (22 min) | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_update_duration_preset -x` | No -- Wave 0 |
| BIBL-03 | PUT /bible rejects invalid duration (0 or negative) | integration | `pytest app/tests/test_shows_api.py::TestBibleAPI::test_update_duration_invalid -x` | No -- Wave 0 |
| ALL | Existing show CRUD tests still pass (no regression) | regression | `pytest app/tests/test_shows_api.py::TestShowsAPI -x` | Yes |
| ALL | Full test suite passes | regression | `pytest app/tests/ -x -q` | Yes |

### Sampling Rate
- **Per task commit:** `pytest app/tests/test_shows_api.py -x -q`
- **Per wave merge:** `pytest app/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_shows_api.py` -- needs TestBibleModel and TestBibleAPI test classes added (file exists, new classes needed)
- No new test files needed -- tests belong in existing test_shows_api.py
- No framework install needed -- pytest already configured
- No new fixtures needed -- existing `client`, `db_session`, `mock_auth_headers` from conftest.py are sufficient

## Sources

### Primary (HIGH confidence)
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/models/database.py` -- current Show model, column patterns
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/models/schemas.py` -- current ShowCreate/ShowUpdate/ShowResponse patterns
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/api/endpoints/shows.py` -- current CRUD endpoint patterns
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/tests/test_shows_api.py` -- current test patterns
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/services/db_migrator.py` -- delta migration runner
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/migrations/delta/006_shows_table.sql` -- migration file pattern
- `/Users/yvesfogel/Desktop/screenwriting-assistant/.planning/STATE.md` -- "Bible stored as columns on Show model" decision
- `/Users/yvesfogel/Desktop/screenwriting-assistant/.planning/REQUIREMENTS.md` -- BIBL-01, BIBL-02, BIBL-03 definitions

### Secondary (MEDIUM confidence)
- None needed -- all patterns are directly observable in the existing codebase.

### Tertiary (LOW confidence)
- None -- no external research was needed for this phase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, everything already in use
- Architecture: HIGH -- exact same patterns as Phase 36, with explicit STATE.md decision on bible storage approach
- Pitfalls: HIGH -- all pitfalls are observable from existing code patterns (UUID str cast, migration idempotency)

**Research date:** 2026-03-24
**Valid until:** Indefinite -- this is internal codebase knowledge, not library versioning
