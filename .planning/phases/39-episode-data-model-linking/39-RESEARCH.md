# Phase 39: Episode Data Model & Linking - Research

**Researched:** 2026-03-24
**Domain:** SQLAlchemy schema extension, FastAPI nested resource endpoints, backward-compatible migration
**Confidence:** HIGH

## Summary

This phase extends the existing Project model with two nullable columns (`show_id` FK and `episode_number`) to support episodes as a specialized type of project linked to a show. The core architectural decision -- "Episode IS a Project" -- means the implementation is a straightforward schema extension with no new ORM models, no new tables, and zero impact on existing standalone project behavior.

The research confirms that every pattern needed already exists in the codebase: nullable FK columns (e.g., `Shot.scene_item_id`), idempotent delta migrations (007_bible_columns.sql), CASCADE delete FKs (006_shows_table.sql), nested sub-resource endpoints (shows.py bible endpoints), and Pydantic v2 optional fields. The implementation requires extending ~4 files and adding 1 migration file.

**Primary recommendation:** Extend the Project ORM model with two nullable columns, extend ProjectCreate/ProjectResponse schemas, add a `POST /api/shows/{show_id}/episodes` endpoint to the existing shows router, and write a single idempotent migration. Keep all existing project endpoints untouched.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Add `show_id` (nullable FK to shows.id, CASCADE DELETE) to projects table
- Add `episode_number` (nullable Integer) to projects table
- Both columns NULL for standalone projects (zero migration of existing data)
- Idempotent delta migration: `008_episode_columns.sql`
- `POST /api/shows/{show_id}/episodes` -- creates a new project linked to a show
  - Body: `{ title, episode_number, framework }` (framework optional, defaults to THREE_ACT)
  - Returns: standard ProjectResponse (same schema, show_id and episode_number populated)
- Episodes inherit the full project pipeline -- no special-casing in existing endpoints
- Existing project endpoints (GET, PUT, DELETE on /api/projects) work unchanged for episodes
- Episode IS a Project: same ORM model, same schema, same pipeline
- ProjectCreate schema: add optional `show_id` and `episode_number` fields
- ProjectResponse schema: add `show_id` and `episode_number` fields (nullable)
- No new ORM model needed -- extend existing Project model
- All existing project tests pass unchanged
- Standalone projects (show_id=NULL) are unaffected
- No breaking changes to any existing endpoint

### Claude's Discretion
- Episode number auto-increment logic: check max episode_number for show, suggest next
- Error message wording follows existing project error patterns

### Deferred Ideas (OUT OF SCOPE)
- Episode reordering -- Phase 40+
- Episode status (draft/published) -- not in requirements
- Season linking -- not in current scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EPIS-01 | User can create a new episode inside a show with an episode number and title | Covered by POST /api/shows/{show_id}/episodes endpoint pattern; auto-increment logic for episode_number documented in Architecture Patterns |
| EPIS-02 | Each episode has the full screenplay -> breakdown -> shotlist -> storyboard pipeline identical to standalone projects | Covered by "Episode IS a Project" model -- extending existing Project with show_id/episode_number means all relationships (sections, phase_data, breakdown_elements, shots, storyboard_frames) are inherited automatically |
| EPIS-04 | Existing standalone projects are unaffected -- no data migration required | Covered by nullable columns approach; both new columns default to NULL, zero data migration needed |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 1.4+ (already in project) | ORM model extension | Project already uses it; Column/ForeignKey pattern established |
| Pydantic v2 | 2.x (already in project) | Schema extension | Project already uses it; Optional field pattern established |
| FastAPI | 0.100+ (already in project) | Endpoint addition | Project already uses it; nested router pattern established |
| PostgreSQL 15 | (already in project) | Database | ALTER TABLE ADD COLUMN IF NOT EXISTS is idempotent |

### Supporting
No additional libraries needed. Everything required is already in the dependency tree.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Extending Project model | Separate Episode table | Would require duplicating all project relationships and pipelines -- rejected by CONTEXT.md |
| Nullable FK columns | Polymorphic inheritance | Over-engineered for two nullable columns -- rejected |

**Installation:**
```bash
# No new dependencies required
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
  app/
    models/
      database.py          # MODIFY: Add show_id + episode_number to Project
      schemas.py           # MODIFY: Extend ProjectCreate + Project response
    api/
      endpoints/
        shows.py           # MODIFY: Add POST /{show_id}/episodes endpoint
  migrations/
    delta/
      008_episode_columns.sql  # NEW: Idempotent ALTER TABLE migration
  app/tests/
    test_shows_api.py      # MODIFY: Add episode endpoint tests
```

### Pattern 1: Nullable FK Column on Existing Model
**What:** Add optional foreign key to an existing model without affecting existing rows.
**When to use:** When an entity gains an optional relationship to another entity.
**Example:**
```python
# Source: Existing pattern in database.py (Shot.scene_item_id is nullable FK)
class Project(Base):
    __tablename__ = "projects"
    # ... existing columns ...
    show_id = Column(UUID(as_uuid=True), ForeignKey("shows.id", ondelete="CASCADE"), nullable=True, index=True)
    episode_number = Column(Integer, nullable=True)
```

**Key details:**
- `nullable=True` means existing rows keep NULL (standalone projects)
- `ondelete="CASCADE"` means deleting a show deletes its episodes (matches existing pattern from 006_shows_table.sql FK on users)
- `index=True` on show_id enables efficient "list episodes for show" queries
- No relationship on Show model is needed for this phase (query directly)

### Pattern 2: Nested Sub-resource Endpoint
**What:** Create a resource under a parent resource's URL namespace.
**When to use:** When creating a child entity that belongs to a parent.
**Example:**
```python
# Source: Existing pattern in shows.py (bible endpoints)
@router.post("/{show_id}/episodes", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_episode(
    show_id: UUID,
    body: schemas.EpisodeCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Verify show exists and is owned by user
    show = db.query(database.Show).filter(
        database.Show.id == str(show_id),
        database.Show.owner_id == str(current_user.id),
    ).first()
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))

    # 2. Auto-calculate episode number if not provided
    if body.episode_number is None:
        max_num = db.query(func.max(database.Project.episode_number)).filter(
            database.Project.show_id == str(show_id)
        ).scalar()
        body.episode_number = (max_num or 0) + 1

    # 3. Create project with show linkage
    db_project = database.Project(
        title=body.title,
        framework=body.framework,
        show_id=str(show_id),
        episode_number=body.episode_number,
        owner_id=str(current_user.id),
    )
    db.add(db_project)
    db.flush()

    # 4. Create default sections (same as project creation)
    # ... section creation logic (reuse from projects.py) ...

    db.commit()
    db.refresh(db_project)
    return db_project
```

### Pattern 3: Idempotent Delta Migration
**What:** SQL migration that uses `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` to be safely re-runnable.
**When to use:** Every schema change in this project.
**Example:**
```sql
-- Migration 008: Episode columns on projects table (v4.2)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS show_id UUID REFERENCES shows(id) ON DELETE CASCADE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS episode_number INTEGER;
CREATE INDEX IF NOT EXISTS ix_projects_show_id ON projects(show_id);
```

### Pattern 4: Pydantic v2 Schema Extension with Optional Fields
**What:** Add optional fields to existing create/response schemas without breaking existing consumers.
**When to use:** When extending an API contract while maintaining backward compatibility.
**Example:**
```python
# Dedicated episode creation schema (lives under shows endpoint)
class EpisodeCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    episode_number: Optional[int] = Field(None, ge=1)
    framework: Framework = Framework.THREE_ACT

    @field_validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty or just whitespace")
        return v.strip()

# Extend existing response schema
class Project(ProjectBase):
    # ... existing fields ...
    show_id: Optional[UUID] = None
    episode_number: Optional[int] = None
```

### Anti-Patterns to Avoid
- **Creating a separate Episode ORM model:** The whole point is Episode IS a Project. A separate model would require duplicating all 6+ relationships (sections, phase_data, breakdown_elements, shots, asset_media, storyboard_frames).
- **Making show_id NOT NULL:** This would break all existing standalone projects and require data migration.
- **Adding episode logic to existing project endpoints:** The episode creation endpoint should be on the shows router, not the projects router. Existing project endpoints should remain untouched.
- **Forgetting to create sections for episodes:** Episodes need the same section scaffolding as standalone projects. Reuse the section creation logic from `create_project()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Episode number auto-increment | Custom sequence tracking | `func.max()` query on episode_number per show | Simple, correct, no race conditions in single-user MVP |
| Section scaffolding for episodes | New section creation logic | Same logic from `create_project()` in projects.py | Must create identical pipeline |
| Show ownership validation | Custom auth middleware | Same `NotFoundException` pattern from shows.py | Consistent error responses |

**Key insight:** The most important thing in this phase is NOT building new infrastructure. Everything should reuse existing patterns. The only truly new code is the `POST /api/shows/{show_id}/episodes` endpoint and the schema extensions.

## Common Pitfalls

### Pitfall 1: Forgetting Section Scaffolding
**What goes wrong:** Episode is created as a bare project without sections, breaking the screenplay pipeline.
**Why it happens:** The episode creation endpoint is separate from `create_project()`, and it's easy to forget the section creation step.
**How to avoid:** Copy the section creation logic from `create_project()` (lines 41-57 of projects.py) into the episode creation endpoint, or extract it into a shared helper function.
**Warning signs:** Episode loads in the editor but shows no sections.

### Pitfall 2: UUID String Casting
**What goes wrong:** SQLAlchemy queries fail because UUID objects are compared against string columns.
**Why it happens:** The test database uses SQLite with String(36) columns for UUIDs, while FastAPI path parameters parse as Python UUID objects.
**How to avoid:** Use `str(show_id)` and `str(current_user.id)` in all SQLAlchemy filters, exactly as the existing shows.py endpoints do.
**Warning signs:** Tests pass locally with PostgreSQL but fail in CI (SQLite).

### Pitfall 3: Breaking ProjectCreate Schema
**What goes wrong:** Adding `show_id` and `episode_number` to ProjectCreate causes existing project creation to fail validation.
**Why it happens:** If fields are added as required instead of optional, existing POST /api/projects/ calls break.
**How to avoid:** Use a dedicated `EpisodeCreate` schema for the new endpoint. Keep `ProjectCreate` unchanged. Only add `show_id` and `episode_number` to the `Project` response schema.
**Warning signs:** Existing project creation tests fail with 422 errors.

### Pitfall 4: CASCADE DELETE Direction
**What goes wrong:** Deleting an episode cascades up and deletes the show, or deleting a show doesn't clean up episodes.
**Why it happens:** Confusion about ON DELETE CASCADE direction.
**How to avoid:** `ForeignKey("shows.id", ondelete="CASCADE")` on the projects.show_id column means: when a **show** is deleted, all projects with that show_id are also deleted. Deleting an episode (project) does NOT affect the show.
**Warning signs:** Deleting a show leaves orphaned episodes in the database, or deleting an episode deletes the parent show.

### Pitfall 5: Episode Number Collisions
**What goes wrong:** Two episodes in the same show get the same episode_number.
**Why it happens:** The auto-increment logic queries max(episode_number) and adds 1, but there's no unique constraint.
**How to avoid:** For the MVP, this is acceptable -- a unique constraint on (show_id, episode_number) can be added later. The auto-increment logic prevents accidental collisions, and manual episode_number is a user choice. Do NOT add a unique constraint now (it complicates reordering in Phase 40+).
**Warning signs:** Two episodes with the same number appear in the show.

## Code Examples

### Migration SQL (008_episode_columns.sql)
```sql
-- Migration 008: Episode columns on projects table (v4.2)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS show_id UUID REFERENCES shows(id) ON DELETE CASCADE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS episode_number INTEGER;
CREATE INDEX IF NOT EXISTS ix_projects_show_id ON projects(show_id);
```

### ORM Model Extension (database.py)
```python
class Project(Base):
    __tablename__ = "projects"
    # ... existing columns unchanged ...

    # Episode linking (Phase 39, v4.2)
    show_id = Column(UUID(as_uuid=True), ForeignKey("shows.id", ondelete="CASCADE"), nullable=True, index=True)
    episode_number = Column(Integer, nullable=True)

    # ... existing relationships unchanged ...
```

### Schema Extension (schemas.py)
```python
# New schema for episode creation (in Show schemas section)
class EpisodeCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    episode_number: Optional[int] = Field(None, ge=1)
    framework: Framework = Framework.THREE_ACT

    @field_validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty or just whitespace")
        return v.strip()

# Extend Project response schema (add to existing Project class)
class Project(ProjectBase):
    # ... existing fields ...
    show_id: Optional[UUID] = None
    episode_number: Optional[int] = None
    # ... rest unchanged ...
```

### Endpoint (shows.py addition)
```python
from sqlalchemy import func

@router.post("/{show_id}/episodes", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
async def create_episode(
    show_id: UUID,
    body: schemas.EpisodeCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new episode (project) under a show."""
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id), database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))

    # Auto-calculate episode number if not provided
    episode_number = body.episode_number
    if episode_number is None:
        max_num = (
            db.query(func.max(database.Project.episode_number))
            .filter(database.Project.show_id == str(show_id))
            .scalar()
        )
        episode_number = (max_num or 0) + 1

    db_project = database.Project(
        title=body.title,
        framework=body.framework,
        show_id=str(show_id),
        episode_number=episode_number,
        owner_id=str(current_user.id),
    )
    db.add(db_project)
    db.flush()

    # Create default sections (identical to project creation)
    section_types = [
        database.SectionType.INCITING_INCIDENT,
        database.SectionType.PLOT_POINT_1,
        database.SectionType.MIDPOINT,
        database.SectionType.PLOT_POINT_2,
        database.SectionType.CLIMAX,
        database.SectionType.RESOLUTION,
    ]
    for section_type in section_types:
        db.add(database.Section(
            project_id=db_project.id,
            type=section_type,
            ai_suggestions={"issues": [], "suggestions": []},
        ))

    db.commit()
    db.refresh(db_project)
    return db_project
```

### Test Pattern (test_shows_api.py addition)
```python
class TestEpisodesAPI:
    """Test episode creation under shows."""

    def _create_show(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/",
            json={"title": "Test Show"},
            headers=mock_auth_headers,
        )
        return resp.json()["id"]

    def test_create_episode(self, client, mock_auth_headers):
        show_id = self._create_show(client, mock_auth_headers)
        resp = client.post(
            f"/api/shows/{show_id}/episodes",
            json={"title": "Pilot", "episode_number": 1},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Pilot"
        assert data["show_id"] == show_id
        assert data["episode_number"] == 1
        assert len(data["sections"]) == 6  # Full pipeline

    def test_create_episode_auto_number(self, client, mock_auth_headers):
        show_id = self._create_show(client, mock_auth_headers)
        # First episode gets auto-number 1
        resp = client.post(
            f"/api/shows/{show_id}/episodes",
            json={"title": "Episode A"},
            headers=mock_auth_headers,
        )
        assert resp.json()["episode_number"] == 1
        # Second gets 2
        resp = client.post(
            f"/api/shows/{show_id}/episodes",
            json={"title": "Episode B"},
            headers=mock_auth_headers,
        )
        assert resp.json()["episode_number"] == 2

    def test_create_episode_show_not_found(self, client, mock_auth_headers):
        resp = client.post(
            "/api/shows/00000000-0000-0000-0000-000000000000/episodes",
            json={"title": "Orphan"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 404

    def test_standalone_projects_unaffected(self, client, mock_auth_headers):
        resp = client.post(
            "/api/projects/",
            json={"title": "My Film", "framework": "three_act"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["show_id"] is None
        assert data["episode_number"] is None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Episode as separate table | Episode IS a Project with show_id FK | Phase 39 design decision | Zero code duplication, full pipeline reuse |
| Required FK columns | Nullable FK columns | Design decision | No data migration needed for existing projects |

**Deprecated/outdated:**
- None -- this is a new feature addition, not replacing anything.

## Open Questions

1. **Should we add a `GET /api/shows/{show_id}/episodes` endpoint in this phase?**
   - What we know: CONTEXT.md lists only POST as the new endpoint. EPIS-03 (view/delete episodes from show page) is Phase 40.
   - What's unclear: Phase 40 will need to list episodes, but that could be done via the existing GET /api/projects/ with a filter.
   - Recommendation: Add the listing endpoint in Phase 40 as specified. For now, episodes are retrievable through the normal GET /api/projects/ endpoint (they appear as regular projects with show_id populated). This matches the CONTEXT.md boundary.

2. **Should the existing `GET /api/projects/` filter out episodes?**
   - What we know: The current endpoint returns all projects for the user. After this phase, episodes will also appear in that list.
   - What's unclear: Whether the frontend home page needs to distinguish episodes from standalone projects.
   - Recommendation: Do NOT filter episodes out. The home page already separates "Shows" and "Films" (Phase 38). The existing project list shows standalone projects in the "Films" section. Episodes will appear in both lists temporarily until Phase 40 adds proper UI filtering. No backend change needed -- the frontend handles display logic.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | `backend/app/tests/conftest.py` |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_shows_api.py -x -q` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EPIS-01 | Create episode with title and episode_number under a show | unit | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_create_episode -x` | Wave 0 |
| EPIS-01 | Episode number auto-increment when not provided | unit | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_create_episode_auto_number -x` | Wave 0 |
| EPIS-01 | 404 when show not found or not owned by user | unit | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_create_episode_show_not_found -x` | Wave 0 |
| EPIS-02 | Episode has full section pipeline (6 sections created) | unit | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_create_episode -x` (checks sections count) | Wave 0 |
| EPIS-04 | Standalone projects unaffected (show_id=None) | unit | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_standalone_projects_unaffected -x` | Wave 0 |
| EPIS-04 | All existing project tests still pass | regression | `pytest app/tests/test_api.py -x` | Existing |

### Sampling Rate
- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_shows_api.py -x -q`
- **Per wave merge:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_shows_api.py::TestEpisodesAPI` -- new test class for episode creation (EPIS-01, EPIS-02, EPIS-04)

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/models/database.py` -- current Project model, Show model, all FK patterns
- Codebase: `backend/app/models/schemas.py` -- current ProjectCreate/Project schemas, ShowCreate pattern
- Codebase: `backend/app/api/endpoints/shows.py` -- existing show CRUD and bible endpoints
- Codebase: `backend/app/api/endpoints/projects.py` -- project creation with section scaffolding
- Codebase: `backend/migrations/delta/007_bible_columns.sql` -- idempotent migration pattern
- Codebase: `backend/app/tests/test_shows_api.py` -- existing test patterns for shows
- Codebase: `backend/app/tests/conftest.py` -- test infrastructure (SQLite, mock auth)

### Secondary (MEDIUM confidence)
- None needed -- all patterns are established in the codebase.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing libraries
- Architecture: HIGH -- every pattern already exists in codebase (nullable FK, nested endpoints, idempotent migrations, optional Pydantic fields)
- Pitfalls: HIGH -- pitfalls are derived from observed patterns in the codebase (UUID string casting, section scaffolding, CASCADE direction)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- this is codebase-intrinsic research, not external library research)
