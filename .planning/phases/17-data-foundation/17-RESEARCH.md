# Phase 17: Data Foundation - Research

**Researched:** 2026-03-19
**Domain:** PostgreSQL migration, SQLAlchemy ORM models, Pydantic v2 schemas for shotlist and media data layer
**Confidence:** HIGH

## Summary

Phase 17 creates the database foundation for v3.0 Shotlist and Production Breakdown. This is a pure data-layer phase: SQL delta migration, SQLAlchemy models, Pydantic schemas, and relationship wiring. No API endpoints, no frontend, no services. The scope is tightly defined by CONTEXT.md with locked decisions on shot-element linking, media file organization, script text storage, and media target strategy.

This phase is a direct successor to v2.0 Phase 9 (Data Foundation), which established the breakdown_elements, element_scene_links, and breakdown_runs tables using the exact same workflow. Phase 17 follows identical patterns: numbered delta migration file (`002_shotlist_tables.sql`), models appended to `database.py`, schemas appended to `schemas.py`, and test file following the `test_breakdown_models.py` template. The codebase has strong, well-tested conventions for every deliverable in this phase.

The new tables are: `shots` (project-scoped shots with JSONB fields and script_range), `shot_elements` (junction table linking shots to breakdown elements), and `asset_media` (file metadata for images/audio attached to elements or shots). Additionally, a `shotlist_stale` boolean column is added to the existing `projects` table, following the identical pattern used for `breakdown_stale`.

**Primary recommendation:** Follow the v2.0 Phase 9 pattern exactly -- create `002_shotlist_tables.sql` delta migration, append Shot/ShotElement/AssetMedia models to `database.py`, append corresponding Pydantic schemas to `schemas.py`, update Project model with `shotlist_stale` column and new relationships, and validate with a test file modeled on `test_breakdown_models.py`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Create `shot_elements` junction table in this phase (not deferred)
- Simple link only: shot_id + element_id, no role/context field
- Shots use hard delete (not soft delete) -- user-created, no AI re-extraction concern
- Cascade deletes on junction rows when shot is deleted
- Per-project folders: `media/{project_id}/images/` and `media/{project_id}/audio/`
- Thumbnails alongside originals: `media/{project_id}/thumbnails/{uuid}_thumb.{ext}`
- No per-project total size limit for now -- rely on 20MB per-file limit only
- Separate Docker volume for media (distinct from existing `uploads/` for books)
- Store selected text + scene index + character offsets: `script_range` JSONB = `{scene_index, start_offset, end_offset, content_hash}`
- Include content hash of scene text at selection time -- enables stale offset detection
- `scene_item_id` FK (nullable, ON DELETE SET NULL) for relational queries, PLUS `scene_index` in JSONB for position data
- FK breaks gracefully if scenes are regenerated (SET NULL, not CASCADE)
- `asset_media` has both `element_id` and `shot_id` FKs (both nullable) -- media can attach to a breakdown element OR a specific shot

### Claude's Discretion
- Exact Pydantic schema field names and validation
- Index strategy on new tables
- Column type choices (VARCHAR lengths, etc.)
- Delta migration numbering (next after 001)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | `shots` table exists with project_id, scene_item_id, shot_number, script_text, script_range (JSONB), fields (JSONB), sort_order, source | SQL DDL follows breakdown_elements pattern; JSONB columns follow established `metadata` / `content` column patterns; FK to list_items with ON DELETE SET NULL (locked decision); shot_number as Integer; source as VARCHAR(20) matching existing convention |
| DATA-02 | `asset_media` table exists with project_id, element_id, shot_id, file_type, file_path, thumbnail_path, original_filename, file_size_bytes, metadata (JSONB) | Both element_id and shot_id nullable FKs (locked decision); file_size_bytes as BigInteger (matches Book model pattern); metadata_ alias pattern from AIMessage/BreakdownElement |
| DATA-03 | `shotlist_stale` boolean column exists on the projects table | Identical pattern to `breakdown_stale` column added in 001_breakdown_tables.sql; `ALTER TABLE projects ADD COLUMN IF NOT EXISTS` |
| DATA-06 | Delta migration in `delta/` is idempotent and applies cleanly on existing Docker volumes without data loss | `db_migrator.py` auto-applies NNN_*.sql files from delta/ on startup; uses schema_migrations tracking table; all SQL must use IF NOT EXISTS / IF NOT EXIST guards |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.27 | ORM models with relationships and constraints | Already in requirements.txt; all existing models use declarative_base pattern |
| Pydantic | >=2.10 | Request/response schemas with ORM validation | Already in requirements.txt; project uses v2 ConfigDict throughout |
| PostgreSQL | 15 | Database with UUID, JSONB, TIMESTAMPTZ support | Already running via pgvector/pgvector:pg15 Docker image |
| psycopg2-binary | 2.9.9 | PostgreSQL adapter | Already in requirements.txt |
| pytest | 8.0.2 | Test framework | Already in requirements.txt; 18 existing test files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid-ossp (PG extension) | built-in | UUID generation in SQL via uuid_generate_v4() | Already enabled in init_db.sql |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single database.py | Separate shot_models.py | Would break convention -- all models live in one file |
| Single schemas.py | Separate shot_schemas.py | Would break convention -- all schemas live in one file |
| Alembic migrations | Raw SQL delta files | Project uses raw SQL; Alembic would add unnecessary dependency |
| PG ENUM for source column | VARCHAR(20) | VARCHAR is project convention for extensible category-like columns |

**Installation:**
No new packages needed. All dependencies already exist in `backend/requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── migrations/
│   └── delta/
│       ├── 001_breakdown_tables.sql   # EXISTING
│       └── 002_shotlist_tables.sql    # NEW - DDL for shots, shot_elements, asset_media + ALTER
├── app/
│   └── models/
│       ├── database.py                # MODIFY - append 3 new ORM models + update Project
│       └── schemas.py                 # MODIFY - append new Pydantic schemas
└── app/tests/
    └── test_shotlist_models.py        # NEW - model + schema tests
```

### Pattern 1: Delta Migration File Convention
**What:** Numbered SQL files in `delta/` directory with `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for idempotency.
**When to use:** Every schema change.
**Source:** `backend/migrations/delta/001_breakdown_tables.sql` (existing pattern)
**Example:**
```sql
-- Migration 002: shotlist tables for v3.0 Shotlist & Production Breakdown
-- Creates shots, shot_elements, asset_media tables
-- Adds shotlist_stale column to projects table

CREATE TABLE IF NOT EXISTS shots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_item_id   UUID REFERENCES list_items(id) ON DELETE SET NULL,
    shot_number     INTEGER NOT NULL DEFAULT 1,
    script_text     TEXT DEFAULT '',
    script_range    JSONB DEFAULT '{}',
    fields          JSONB DEFAULT '{}',
    sort_order      INTEGER DEFAULT 0,
    source          VARCHAR(20) DEFAULT 'user',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS shotlist_stale BOOLEAN DEFAULT FALSE;
```

### Pattern 2: SQLAlchemy Model with JSONB and Nullable FK
**What:** ORM model using `Column()` definitions with nullable FK using `ondelete="SET NULL"`, JSONB via `JSON` type.
**When to use:** Tables with optional parent references that should survive parent deletion.
**Source:** `backend/app/models/database.py` -- BreakdownElement pattern + AISession.context_item_id pattern
**Example:**
```python
class Shot(Base):
    __tablename__ = "shots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    scene_item_id = Column(UUID(as_uuid=True), ForeignKey("list_items.id", ondelete="SET NULL"), nullable=True, index=True)
    shot_number = Column(Integer, nullable=False, default=1)
    script_text = Column(Text, default="")
    script_range = Column(JSON, default=dict)
    fields = Column(JSON, default=dict)
    sort_order = Column(Integer, default=0)
    source = Column(String(20), default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = sa_relationship("Project", back_populates="shots")
    shot_elements = sa_relationship("ShotElement", back_populates="shot",
                                     cascade="all, delete-orphan")
    media = sa_relationship("AssetMedia", back_populates="shot",
                             cascade="all, delete-orphan")
```

### Pattern 3: Junction Table with Simple Link (No Extra Fields)
**What:** Two-FK junction table with cascade delete from the owning side.
**When to use:** Many-to-many relationships. shot_elements links shots to breakdown_elements.
**Source:** `backend/app/models/database.py` -- AgentBook pattern (simple two-FK junction)
**Example:**
```python
class ShotElement(Base):
    __tablename__ = "shot_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shot_id = Column(UUID(as_uuid=True), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("breakdown_elements.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shot = sa_relationship("Shot", back_populates="shot_elements")
    element = sa_relationship("BreakdownElement")

    __table_args__ = (
        UniqueConstraint('shot_id', 'element_id', name='uq_shot_element'),
    )
```

### Pattern 4: Pydantic v2 Response Schema with metadata_ Alias
**What:** Pydantic BaseModel with `ConfigDict(from_attributes=True)` and `validation_alias` for aliased ORM columns.
**When to use:** Response schemas for models with `metadata_` column alias.
**Source:** `backend/app/models/schemas.py` -- BreakdownElementResponse pattern
**Example:**
```python
class AssetMediaResponse(BaseModel):
    id: UUID
    project_id: UUID
    element_id: Optional[UUID] = None
    shot_id: Optional[UUID] = None
    file_type: str
    file_path: str
    thumbnail_path: Optional[str] = None
    original_filename: str
    file_size_bytes: int
    metadata: Dict = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
```

### Anti-Patterns to Avoid
- **Separate model files:** Do NOT create `shot_models.py` -- the project puts all models in `database.py` and all schemas in `schemas.py`
- **Alembic autogenerate:** Do NOT add Alembic -- the project uses raw SQL migration files in `delta/`
- **Python enums for source column:** Do NOT create a PostgreSQL ENUM for shot source -- use `VARCHAR(20)` for extensibility (existing convention)
- **`metadata` column name collision:** Use `metadata_ = Column("metadata", JSON, default=dict)` as the Python attribute name with `Column("metadata", ...)` pattern (already used for `AIMessage.metadata_` and `Book.metadata_`)
- **Missing `IF NOT EXISTS`:** All `CREATE TABLE`, `CREATE INDEX`, and `ALTER TABLE ADD COLUMN` statements MUST use `IF NOT EXISTS` for idempotency
- **CASCADE on scene_item_id FK:** User locked decision is ON DELETE SET NULL, not CASCADE -- shots survive scene regeneration
- **Soft delete on shots:** User locked decision is hard delete -- shots are user-created, no need for soft delete pattern
- **NOT NULL on scene_item_id:** This FK must be nullable -- shots can exist without being linked to a scene, and SET NULL requires nullable column
- **Forgetting back_populates on Project:** Must add `shots`, `asset_media` relationships on Project model, plus `shotlist_stale` column

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID primary keys | Custom ID generation | `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)` + `uuid_generate_v4()` in SQL | Established pattern; conftest.py patches handle SQLite test compat |
| ORM-to-schema conversion | Custom serializer | `ConfigDict(from_attributes=True)` + `model_validate()` | Pydantic v2 does this natively |
| Cascade deletes | Application-level deletion code | `ON DELETE CASCADE` in SQL + `cascade="all, delete-orphan"` in relationships | Database enforces referential integrity |
| Migration tracking | Custom migration logic | Existing `db_migrator.py` with `schema_migrations` table | Already implemented and battle-tested |
| SQLite test compatibility | Test-specific model variants | Existing `conftest.py` `_patch_uuid_columns_for_sqlite()` | Auto-patches UUID, Enum, and Vector columns |
| JSONB validation | Custom JSON validators | Pydantic nested models or `Dict` type | Pydantic handles JSON validation at API boundary |

**Key insight:** This phase is entirely pattern-following. Phase 9 (v2.0 Data Foundation) is the exact template. Every convention (migration naming, model structure, schema structure, test structure, FK cascade, unique constraints) has 2+ existing examples in the codebase.

## Common Pitfalls

### Pitfall 1: SQLAlchemy `metadata` Column Name Clash
**What goes wrong:** Defining `metadata = Column(JSON, ...)` clashes with SQLAlchemy's `Table.metadata` attribute.
**Why it happens:** `Base.metadata` is a reserved SQLAlchemy attribute.
**How to avoid:** Use `metadata_ = Column("metadata", JSON, default=dict)` as the Python attribute, keeping `metadata` as the DB column name. Use `validation_alias="metadata_"` in the Pydantic schema. This pattern exists in `AIMessage` (line 198 of database.py) and `Book` (line 281).
**Warning signs:** `AttributeError` when accessing the column, or metadata queries returning SQLAlchemy MetaData objects.

### Pitfall 2: Missing Back-Populates on Project Model
**What goes wrong:** New relationships defined on Shot/AssetMedia point to Project, but Project model lacks the `back_populates` relationship, causing SQLAlchemy warnings and broken cascade behavior.
**Why it happens:** Forgetting to update the parent model when adding child relationships.
**How to avoid:** Add `shots`, `asset_media` relationships on the Project model. Also add `shotlist_stale` column. Check all 3 additions are present.
**Warning signs:** SQLAlchemy relationship configuration warnings at startup.

### Pitfall 3: ON DELETE SET NULL Requires Nullable Column
**What goes wrong:** `scene_item_id` FK with `ON DELETE SET NULL` fails if the column is `NOT NULL`.
**Why it happens:** PostgreSQL cannot set a NOT NULL column to NULL when the referenced row is deleted.
**How to avoid:** Ensure `scene_item_id` is `nullable=True` in both SQL (`UUID REFERENCES list_items(id) ON DELETE SET NULL` without NOT NULL) and SQLAlchemy (`nullable=True`).
**Warning signs:** `IntegrityError` when deleting list_items that are referenced by shots.

### Pitfall 4: Dual-Nullable FKs on asset_media Need Clear Semantics
**What goes wrong:** Both `element_id` and `shot_id` are nullable on `asset_media`, allowing rows with neither FK set (orphaned media).
**Why it happens:** No CHECK constraint enforcing that at least one FK is set.
**How to avoid:** Accept this for now -- media can be uploaded before being attached. The API layer (Phase 22) will enforce attachment at upload time. Optionally add a CHECK constraint `CHECK (element_id IS NOT NULL OR shot_id IS NOT NULL)` but this could block legitimate workflows where media is uploaded first and linked later. Recommendation: skip the CHECK constraint for flexibility.
**Warning signs:** Orphaned media rows with both FKs null -- handle at API layer.

### Pitfall 5: shot_elements Cascade Direction
**What goes wrong:** Deleting a shot should cascade to junction rows, but deleting a breakdown element should also cascade to junction rows.
**Why it happens:** Junction table has two parent FKs, both need CASCADE.
**How to avoid:** Both FKs in `shot_elements` must specify `ON DELETE CASCADE` in SQL. In SQLAlchemy, `Shot.shot_elements` uses `cascade="all, delete-orphan"`, but `BreakdownElement` does NOT need a back_populates for shot_elements (navigate from Shot side only, matching the pattern where ElementSceneLink is only navigated from BreakdownElement side).
**Warning signs:** IntegrityError when deleting breakdown elements that are linked to shots.

### Pitfall 6: init_db.sql Must Also Be Updated
**What goes wrong:** Delta migration applies to existing databases, but fresh Docker deployments use `init_db.sql`. If `init_db.sql` is not updated, fresh databases lack the new tables.
**Why it happens:** Two sources of truth for schema: `init_db.sql` (fresh installs) and `delta/` (upgrades).
**How to avoid:** After creating `002_shotlist_tables.sql`, also append the same DDL to `backend/migrations/init_db.sql` so fresh installs get the complete schema. Add tables, indexes, and triggers. This is the same pattern used when 001_breakdown_tables.sql was created alongside updating init_db.sql.
**Warning signs:** Fresh docker compose up creates a database missing shots/shot_elements/asset_media tables.

### Pitfall 7: Docker Volume for Media Not Wired
**What goes wrong:** Media files stored to `media/{project_id}/` path have no Docker volume, so files are lost on container restart.
**Why it happens:** CONTEXT.md specifies "separate Docker volume for media" but docker-compose.yml needs updating.
**How to avoid:** Add a new `media_uploads` volume to `docker-compose.yml` mounted at `/app/media` on the backend service. This is distinct from the existing `book_uploads` volume at `/app/uploads`. Note: the volume definition is part of this phase's infrastructure, even though media upload endpoints are Phase 22.
**Warning signs:** Media files vanish after `docker compose down && docker compose up`.

## Code Examples

Verified patterns from the existing codebase:

### Delta Migration: 002_shotlist_tables.sql
```sql
-- Source: follows pattern of backend/migrations/delta/001_breakdown_tables.sql
-- Migration 002: shotlist tables for v3.0 Shotlist & Production Breakdown
-- Creates shots, shot_elements, asset_media tables
-- Adds shotlist_stale column to projects table
--
-- shots: per-project shots with freeform JSONB fields and script range tracking
-- shot_elements: junction table linking shots to breakdown elements
-- asset_media: file metadata for images/audio attached to elements or shots

CREATE TABLE IF NOT EXISTS shots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_item_id   UUID REFERENCES list_items(id) ON DELETE SET NULL,
    shot_number     INTEGER NOT NULL DEFAULT 1,
    script_text     TEXT DEFAULT '',
    script_range    JSONB DEFAULT '{}',
    fields          JSONB DEFAULT '{}',
    sort_order      INTEGER DEFAULT 0,
    source          VARCHAR(20) DEFAULT 'user',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shots_project
    ON shots(project_id);
CREATE INDEX IF NOT EXISTS idx_shots_scene
    ON shots(scene_item_id);
CREATE INDEX IF NOT EXISTS idx_shots_project_sort
    ON shots(project_id, sort_order);

CREATE TABLE IF NOT EXISTS shot_elements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shot_id         UUID NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
    element_id      UUID NOT NULL REFERENCES breakdown_elements(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_shot_element UNIQUE (shot_id, element_id)
);

CREATE INDEX IF NOT EXISTS idx_shot_elements_shot
    ON shot_elements(shot_id);
CREATE INDEX IF NOT EXISTS idx_shot_elements_element
    ON shot_elements(element_id);

CREATE TABLE IF NOT EXISTS asset_media (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id        UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    element_id        UUID REFERENCES breakdown_elements(id) ON DELETE SET NULL,
    shot_id           UUID REFERENCES shots(id) ON DELETE SET NULL,
    file_type         VARCHAR(20) NOT NULL,
    file_path         VARCHAR(1000) NOT NULL,
    thumbnail_path    VARCHAR(1000),
    original_filename VARCHAR(500) NOT NULL,
    file_size_bytes   BIGINT NOT NULL DEFAULT 0,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_asset_media_project
    ON asset_media(project_id);
CREATE INDEX IF NOT EXISTS idx_asset_media_element
    ON asset_media(element_id);
CREATE INDEX IF NOT EXISTS idx_asset_media_shot
    ON asset_media(shot_id);

-- Add staleness tracking for shotlist
ALTER TABLE projects ADD COLUMN IF NOT EXISTS shotlist_stale BOOLEAN DEFAULT FALSE;
```

### SQLAlchemy Models (append to database.py after BreakdownRun)
```python
# Source: follows patterns from BreakdownElement, ElementSceneLink, AISession

# ============================================================
# Shotlist models (v3.0 -- Phase 17 Data Foundation)
# ============================================================

class Shot(Base):
    __tablename__ = "shots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    scene_item_id = Column(UUID(as_uuid=True), ForeignKey("list_items.id", ondelete="SET NULL"), nullable=True, index=True)
    shot_number = Column(Integer, nullable=False, default=1)
    script_text = Column(Text, default="")
    script_range = Column(JSON, default=dict)
    fields = Column(JSON, default=dict)
    sort_order = Column(Integer, default=0)
    source = Column(String(20), default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = sa_relationship("Project", back_populates="shots")
    shot_elements = sa_relationship("ShotElement", back_populates="shot",
                                     cascade="all, delete-orphan")
    media = sa_relationship("AssetMedia", back_populates="shot",
                             cascade="all, delete-orphan")


class ShotElement(Base):
    __tablename__ = "shot_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shot_id = Column(UUID(as_uuid=True), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("breakdown_elements.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shot = sa_relationship("Shot", back_populates="shot_elements")
    element = sa_relationship("BreakdownElement")

    __table_args__ = (
        UniqueConstraint('shot_id', 'element_id', name='uq_shot_element'),
    )


class AssetMedia(Base):
    __tablename__ = "asset_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    element_id = Column(UUID(as_uuid=True), ForeignKey("breakdown_elements.id", ondelete="SET NULL"), nullable=True, index=True)
    shot_id = Column(UUID(as_uuid=True), ForeignKey("shots.id", ondelete="SET NULL"), nullable=True, index=True)
    file_type = Column(String(20), nullable=False)
    file_path = Column(String(1000), nullable=False)
    thumbnail_path = Column(String(1000), nullable=True)
    original_filename = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = sa_relationship("Project", back_populates="asset_media")
    element = sa_relationship("BreakdownElement")
    shot = sa_relationship("Shot", back_populates="media")
```

### Project Model Updates (additions needed)
```python
# Source: follows breakdown_stale / breakdown_elements pattern in Project model

# In Project class, add these lines:
# Column (alongside existing breakdown_stale):
shotlist_stale = Column(Boolean, default=False)

# Relationships (after existing breakdown_runs relationship):
shots = sa_relationship("Shot", back_populates="project",
                         cascade="all, delete-orphan")
asset_media = sa_relationship("AssetMedia", back_populates="project",
                               cascade="all, delete-orphan")
```

### Pydantic Schemas (append to schemas.py)
```python
# Source: follows BreakdownElementCreate/Response patterns

# ============================================================
# Shotlist Schemas (v3.0 -- Phase 17 Data Foundation)
# ============================================================

class ScriptRange(BaseModel):
    """JSONB shape for shot script_range field."""
    scene_index: int = 0
    start_offset: int = 0
    end_offset: int = 0
    content_hash: str = ""


class ShotCreate(BaseModel):
    scene_item_id: Optional[UUID] = None
    shot_number: int = Field(default=1, ge=1)
    script_text: str = ""
    script_range: Optional[Dict] = Field(default_factory=dict)
    fields: Dict = Field(default_factory=dict)
    sort_order: Optional[int] = None
    source: str = Field(default="user", pattern="^(user|ai)$")


class ShotUpdate(BaseModel):
    scene_item_id: Optional[UUID] = None
    shot_number: Optional[int] = Field(None, ge=1)
    script_text: Optional[str] = None
    script_range: Optional[Dict] = None
    fields: Optional[Dict] = None
    sort_order: Optional[int] = None


class ShotResponse(BaseModel):
    id: UUID
    project_id: UUID
    scene_item_id: Optional[UUID] = None
    shot_number: int
    script_text: str = ""
    script_range: Dict = Field(default_factory=dict)
    fields: Dict = Field(default_factory=dict)
    sort_order: int = 0
    source: str = "user"
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ShotElementCreate(BaseModel):
    element_id: UUID


class ShotElementResponse(BaseModel):
    id: UUID
    shot_id: UUID
    element_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssetMediaCreate(BaseModel):
    element_id: Optional[UUID] = None
    shot_id: Optional[UUID] = None
    file_type: str = Field(..., pattern="^(image|audio)$")
    original_filename: str = Field(..., min_length=1, max_length=500)
    file_size_bytes: int = Field(..., ge=0)


class AssetMediaResponse(BaseModel):
    id: UUID
    project_id: UUID
    element_id: Optional[UUID] = None
    shot_id: Optional[UUID] = None
    file_type: str
    file_path: str
    thumbnail_path: Optional[str] = None
    original_filename: str
    file_size_bytes: int
    metadata: Dict = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
```

### Docker Compose Volume Addition
```yaml
# Source: follows book_uploads volume pattern in docker-compose.yml

# In services.backend.volumes, add:
- media_uploads:/app/media

# In top-level volumes, add:
media_uploads:
```

### Test Pattern (from test_breakdown_models.py)
```python
# New file: backend/app/tests/test_shotlist_models.py
# Follows exact pattern of test_breakdown_models.py

import uuid
import pytest
from app.models.database import (
    Base, Shot, ShotElement, AssetMedia, Project,
    BreakdownElement, PhaseData, ListItem,
)

def test_shot_importable():
    assert Shot.__tablename__ == "shots"

def test_shot_element_importable():
    assert ShotElement.__tablename__ == "shot_elements"

def test_asset_media_importable():
    assert AssetMedia.__tablename__ == "asset_media"

def test_tables_in_metadata():
    tables = Base.metadata.tables
    assert "shots" in tables
    assert "shot_elements" in tables
    assert "asset_media" in tables

def test_project_shotlist_stale(db_session):
    project = Project(id=uuid.uuid4(), owner_id=uuid.uuid4(), title="Test Stale")
    db_session.add(project)
    db_session.flush()
    db_session.refresh(project)
    assert project.shotlist_stale is False

def test_shot_orm_roundtrip(db_session):
    project = Project(id=uuid.uuid4(), owner_id=uuid.uuid4(), title="Shot Test")
    db_session.add(project)
    db_session.flush()

    shot = Shot(
        id=uuid.uuid4(), project_id=project.id,
        shot_number=1, script_text="EXT. PARK - DAY",
        source="user",
    )
    db_session.add(shot)
    db_session.commit()
    db_session.refresh(shot)

    assert shot.shot_number == 1
    assert shot.source == "user"
    assert shot.sort_order == 0

# ... additional tests for cascade, junction table, schema validation
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `class Config: orm_mode = True` | Pydantic v2 `model_config = ConfigDict(from_attributes=True)` | Pydantic 2.0 (2023) | Project already uses v2 throughout |
| SQLAlchemy 1.x declarative_base() | SQLAlchemy 2.0 declarative_base() (compatible) | SQLAlchemy 2.0 (2023) | Project uses 2.0.27 but with 1.x-style import; follow existing convention |
| `declarative_base()` from `sqlalchemy.ext.declarative` | `DeclarativeBase` from `sqlalchemy.orm` | SQLAlchemy 2.0 | Project uses old import throughout -- do NOT modernize |

**Deprecated/outdated:**
- `sqlalchemy.ext.declarative.declarative_base()` is technically deprecated but project uses it everywhere -- follow existing convention for consistency

## Open Questions

1. **asset_media ON DELETE behavior for element_id and shot_id**
   - What we know: Both FKs are nullable. CONTEXT.md says media can attach to element OR shot. The locked decision specifies both as nullable.
   - What's unclear: Should deleting an element or shot also delete its media, or just orphan it? CASCADE would delete media files from the filesystem (requires service logic). SET NULL keeps media rows but orphans them.
   - Recommendation: Use `ON DELETE SET NULL` for both. Media files are valuable user uploads -- better to orphan the DB row than lose the file reference. The API layer can handle cleanup. This matches the conservative approach for user-created content.

2. **script_range JSONB shape enforcement**
   - What we know: CONTEXT.md locks shape to `{scene_index, start_offset, end_offset, content_hash}`.
   - What's unclear: Whether to enforce shape at DB level (CHECK constraint with jsonb operators) or only at API level (Pydantic schema).
   - Recommendation: Enforce at Pydantic level only (ScriptRange nested model). No DB-level CHECK constraint -- keeps migration simple, and JSONB flexibility is a feature. The ScriptRange model serves as documentation and validation.

3. **Triggers for updated_at on new tables**
   - What we know: init_db.sql has `update_updated_at_column()` trigger function and applies it to projects, sections, agents, etc.
   - What's unclear: Whether the delta migration should also create triggers for the new tables, or rely on SQLAlchemy's `onupdate=func.now()`.
   - Recommendation: Add triggers in the delta migration for consistency with init_db.sql pattern. SQLAlchemy's `onupdate` only fires on ORM updates, not raw SQL updates. Having both is harmless (trigger takes precedence). Add triggers for `shots` and `asset_media` tables. `shot_elements` does not need one (no updated_at column).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest app/tests/test_shotlist_models.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | shots table created with all columns, indexes | unit | `pytest app/tests/test_shotlist_models.py::test_shot_importable -x` | Wave 0 |
| DATA-01 | Shot ORM round-trip with fields JSONB and script_range JSONB | unit | `pytest app/tests/test_shotlist_models.py::test_shot_orm_roundtrip -x` | Wave 0 |
| DATA-01 | scene_item_id SET NULL on list_item deletion | unit | `pytest app/tests/test_shotlist_models.py::test_shot_scene_set_null -x` | Wave 0 |
| DATA-01 | Shot hard delete cascades to shot_elements | unit | `pytest app/tests/test_shotlist_models.py::test_shot_cascade_delete -x` | Wave 0 |
| DATA-02 | asset_media table created with all columns | unit | `pytest app/tests/test_shotlist_models.py::test_asset_media_importable -x` | Wave 0 |
| DATA-02 | AssetMedia ORM round-trip with metadata_ alias | unit | `pytest app/tests/test_shotlist_models.py::test_asset_media_orm_roundtrip -x` | Wave 0 |
| DATA-03 | shotlist_stale column on projects defaults to FALSE | unit | `pytest app/tests/test_shotlist_models.py::test_project_shotlist_stale -x` | Wave 0 |
| DATA-06 | All 3 new tables in Base.metadata | unit | `pytest app/tests/test_shotlist_models.py::test_tables_in_metadata -x` | Wave 0 |
| ALL | Pydantic schemas validate correctly (ShotCreate, ShotResponse, AssetMediaResponse) | unit | `pytest app/tests/test_shotlist_models.py::test_shot_schema_validation -x` | Wave 0 |
| ALL | ShotResponse.model_validate(orm_shot) round-trip | unit | `pytest app/tests/test_shotlist_models.py::test_shot_response_from_orm -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_shotlist_models.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_shotlist_models.py` -- covers DATA-01 through DATA-06 (model importability, ORM round-trips, cascade behavior, SET NULL behavior, schema validation, metadata alias)
- [ ] No new framework install needed (pytest already configured)
- [ ] No new conftest fixtures needed (existing `db_session`, `client`, `mock_auth_headers` sufficient; `_patch_uuid_columns_for_sqlite()` auto-handles new models)

## Sources

### Primary (HIGH confidence)
- `backend/app/models/database.py` -- all existing ORM model patterns (Project, BreakdownElement, ElementSceneLink, BreakdownRun, AIMessage, Book)
- `backend/app/models/schemas.py` -- all existing Pydantic v2 schema patterns (BreakdownElementResponse, BreakdownElementCreate)
- `backend/migrations/delta/001_breakdown_tables.sql` -- delta migration pattern for v2.0 breakdown
- `backend/migrations/init_db.sql` -- consolidated schema baseline with all tables, indexes, triggers
- `backend/app/services/db_migrator.py` -- migration runner logic (reads delta/ directory, uses schema_migrations tracking)
- `backend/app/tests/conftest.py` -- SQLite test engine setup with UUID/Enum/Vector patching
- `backend/app/tests/test_breakdown_models.py` -- model + schema test pattern (Phase 9 deliverable)
- `docker-compose.yml` -- volume configuration pattern (book_uploads volume)
- `.planning/phases/17-data-foundation/17-CONTEXT.md` -- locked implementation decisions

### Secondary (MEDIUM confidence)
- `.planning/milestones/v2.0-phases/09-data-foundation/09-RESEARCH.md` -- Phase 9 research (identical phase type, established workflow)
- `.planning/REQUIREMENTS.md` -- DATA-01 through DATA-06 requirement definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all patterns established with 2+ existing examples
- Architecture: HIGH -- direct successor to Phase 9 (v2.0 Data Foundation), identical workflow, locked CONTEXT.md decisions
- Pitfalls: HIGH -- metadata column clash, cascade/SET NULL semantics, init_db.sql sync requirement all verified against existing code

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- no external dependencies to change)
