# Phase 9: Data Foundation - Research

**Researched:** 2026-03-13
**Domain:** PostgreSQL migration, SQLAlchemy ORM models, Pydantic v2 schemas for script breakdown data layer
**Confidence:** HIGH

## Summary

Phase 9 creates the database foundation for the v2.0 Script Breakdown feature. This is a pure data-layer phase with no API endpoints, no frontend, and no AI logic -- just SQL migration, SQLAlchemy models, Pydantic schemas, and relationship wiring. The phase is well-scoped because the architecture was already specified in the v2.0 research (`.planning/research/ARCHITECTURE.md`) with exact SQL DDL, column definitions, and schema code.

The codebase has strong established patterns for all three deliverables: migration files follow a numbered `NNN_name.sql` convention (8 existing migrations), SQLAlchemy models live in a single `backend/app/models/database.py` file using `declarative_base()` with UUID primary keys and `sa_relationship()` for cascading, and Pydantic v2 schemas live in `backend/app/models/schemas.py` using `ConfigDict(from_attributes=True)` for ORM round-trips. Phase 9 follows these exact patterns with zero deviation.

**Primary recommendation:** Follow the existing codebase conventions exactly -- add migration `009_breakdown_tables.sql`, append new models to `database.py`, and append new schemas to `schemas.py`. The SQL DDL from ARCHITECTURE.md is the spec. The test pattern from `test_pipeline_map_schema.py` (model importability, ORM round-trip, schema validation) is the validation template.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BKDN-01 | `breakdown_elements` table with category column, JSONB metadata, `user_modified` flag, `is_deleted` soft-delete, unique constraint on `(project_id, category, name)` | SQL DDL from ARCHITECTURE.md; migration pattern from 008_agent_pipeline_maps.sql; SQLAlchemy model pattern from existing models in database.py |
| BKDN-02 | `element_scene_links` junction table linking breakdown elements to scene ListItems with context notes and source tracking | SQL DDL from ARCHITECTURE.md; FK cascade pattern from existing models; junction table pattern from `agent_books` |
| BKDN-03 | `breakdown_runs` audit table tracking extraction runs (status, element counts, errors, timestamps) | SQL DDL from ARCHITECTURE.md; follows `wizard_runs` pattern (status, config JSON, error_message, timestamps) |
| BKDN-04 | `breakdown_stale` boolean column on projects table, set when script content changes | ALTER TABLE pattern from 003_template_system.sql; new column on existing Project model |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.27 | ORM models with relationships and constraints | Already in requirements.txt, all existing models use it |
| Pydantic | >=2.10 | Request/response schemas with ORM validation | Already in requirements.txt, project uses v2 patterns throughout |
| PostgreSQL | 15 | Database with UUID, JSONB, TIMESTAMPTZ support | Already running via Docker Compose |
| psycopg2-binary | 2.9.9 | PostgreSQL adapter | Already in requirements.txt |
| pytest | 8.0.2 | Test framework | Already in requirements.txt, 14 existing test files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uuid-ossp (PG extension) | built-in | UUID generation in SQL | Already enabled in init_db.sql |
| pytest-asyncio | 0.23.5 | Async test support | Already in requirements.txt |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single database.py | Separate breakdown_models.py | Would break convention -- all models in one file; import less discoverable |
| Single schemas.py | Separate breakdown_schemas.py | ARCHITECTURE.md mentions this option; but current codebase has everything in schemas.py |
| Alembic migrations | Raw SQL migration files | Project uses raw SQL; Alembic would be an unnecessary dependency addition |

**Installation:**
No new packages needed. All dependencies already exist in `backend/requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── migrations/
│   └── 009_breakdown_tables.sql   # NEW - DDL for 3 tables + ALTER
├── app/
│   └── models/
│       ├── database.py            # MODIFY - append 3 new ORM models + update Project
│       └── schemas.py             # MODIFY - append 6 new Pydantic schemas
└── app/tests/
    └── test_breakdown_models.py   # NEW - model + schema tests
```

### Pattern 1: Migration File Convention
**What:** Numbered SQL files with descriptive names, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`
**When to use:** Every schema change
**Example:**
```sql
-- Source: backend/migrations/008_agent_pipeline_maps.sql (existing pattern)
-- Migration 009: breakdown tables for script breakdown feature
-- Creates breakdown_elements, element_scene_links, breakdown_runs tables
-- and adds breakdown_stale column to projects

CREATE TABLE IF NOT EXISTS breakdown_elements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    -- ...columns...
    CONSTRAINT uq_breakdown_element UNIQUE (project_id, category, name)
);

CREATE INDEX IF NOT EXISTS idx_breakdown_elements_project
    ON breakdown_elements(project_id);
```

### Pattern 2: SQLAlchemy Model with UniqueConstraint
**What:** ORM model using `Column()` definitions, `sa_relationship()` with cascade, `__table_args__` for constraints
**When to use:** Every new table mapped to an ORM class
**Example:**
```python
# Source: backend/app/models/database.py (existing PhaseData pattern)
class BreakdownElement(Base):
    __tablename__ = "breakdown_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    # ...

    project = sa_relationship("Project", back_populates="breakdown_elements")
    scene_links = sa_relationship("ElementSceneLink", back_populates="element",
                                  cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', 'category', 'name', name='uq_breakdown_element'),
    )
```

### Pattern 3: Pydantic v2 Response Schema with ORM Round-Trip
**What:** Pydantic BaseModel with `model_config = ConfigDict(from_attributes=True)` for direct ORM-to-schema conversion
**When to use:** Every response schema that reads from DB
**Example:**
```python
# Source: backend/app/models/schemas.py (existing PipelineMapEntry pattern)
class BreakdownElementResponse(BaseModel):
    id: UUID
    project_id: UUID
    category: str
    name: str
    description: str
    metadata: Dict = Field(default_factory=dict, validation_alias="metadata_")
    source: str
    user_modified: bool
    is_deleted: bool
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
```

### Pattern 4: Cascade-Delete Relationship Wiring
**What:** Parent model adds `sa_relationship()` with `back_populates` and `cascade="all, delete-orphan"`
**When to use:** When deleting a parent should delete children
**Example:**
```python
# Source: backend/app/models/database.py (existing Project pattern)
# In Project model:
breakdown_elements = sa_relationship("BreakdownElement", back_populates="project",
                                      cascade="all, delete-orphan")
breakdown_runs = sa_relationship("BreakdownRun", back_populates="project",
                                  cascade="all, delete-orphan")
```

### Anti-Patterns to Avoid
- **Separate model files:** Do NOT create `breakdown_models.py` -- the project puts all models in `database.py` and all schemas in `schemas.py`
- **Alembic autogenerate:** Do NOT add Alembic -- the project uses raw SQL migration files
- **Python enums for category:** Do NOT create a PostgreSQL ENUM type for breakdown categories -- use `VARCHAR(50)` so new categories can be added without migration (matches ARCHITECTURE.md design)
- **`metadata` column name collision:** SQLAlchemy's `MetaData` class can conflict with a column named `metadata` -- use `metadata_` as the Python attribute name with `Column("metadata", JSON, ...)` pattern (already used for `AIMessage.metadata_`)
- **Missing `IF NOT EXISTS`:** All `CREATE TABLE` and `CREATE INDEX` statements MUST use `IF NOT EXISTS` for idempotency (established pattern in all 8 existing migrations)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID primary keys | Custom ID generation | `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)` + `uuid_generate_v4()` in SQL | Already established pattern, handles SQLite test compatibility via conftest.py patching |
| ORM-to-schema conversion | Custom serializer | `ConfigDict(from_attributes=True)` + `model_validate()` | Pydantic v2 does this natively; all existing schemas use it |
| Cascade deletes | Application-level deletion code | `ON DELETE CASCADE` in SQL + `cascade="all, delete-orphan"` in relationships | Database enforces referential integrity; tested pattern throughout codebase |
| SQLite test compatibility | Test-specific model variants | Existing `conftest.py` `_patch_uuid_columns_for_sqlite()` | Automatically patches UUID, Enum, and Vector columns for SQLite test engine |

**Key insight:** This phase is entirely pattern-following. Every convention (migration naming, model structure, schema structure, test structure, FK cascade, unique constraints) has 2+ existing examples in the codebase. Zero novel patterns needed.

## Common Pitfalls

### Pitfall 1: SQLAlchemy `metadata` Column Name Clash
**What goes wrong:** Defining `metadata = Column(JSON, ...)` clashes with SQLAlchemy's `Table.metadata` attribute, causing subtle attribute access errors
**Why it happens:** `Base.metadata` is a reserved SQLAlchemy attribute; naming a column `metadata` shadows it
**How to avoid:** Use `metadata_ = Column("metadata", JSON, default=dict)` as the Python attribute name while keeping `metadata` as the DB column name. Then use `validation_alias="metadata_"` in the Pydantic schema. This pattern already exists in `AIMessage` (line 184 of database.py)
**Warning signs:** `AttributeError` when accessing the column, or metadata queries returning SQLAlchemy MetaData objects

### Pitfall 2: Missing Back-Populates on Project Model
**What goes wrong:** New relationships defined on `BreakdownElement` point to `Project`, but `Project` model lacks the `back_populates` relationship, causing SQLAlchemy warnings and broken cascade behavior
**Why it happens:** Forgetting to update the parent model when adding child relationships
**How to avoid:** Always add the corresponding `sa_relationship()` on the `Project` model when creating new child models. Check: `Project.breakdown_elements`, `Project.breakdown_runs`
**Warning signs:** SQLAlchemy relationship configuration warnings at startup

### Pitfall 3: ElementSceneLink Must Cascade on BOTH Parent Deletions
**What goes wrong:** Scene links cascade when a `BreakdownElement` is deleted, but not when a `ListItem` (scene) is deleted, leaving orphaned rows
**Why it happens:** Junction table has two foreign keys but only one cascade is wired
**How to avoid:** Both FKs in `element_scene_links` must specify `ON DELETE CASCADE` in SQL, and the SQLAlchemy model must have `ForeignKey("list_items.id", ondelete="CASCADE")`. Note: `ListItem` model does NOT need a back_populates for scene_links (it is not a direct parent in the ORM sense -- the link is navigated from `BreakdownElement.scene_links`)
**Warning signs:** IntegrityError when deleting scenes that have breakdown links

### Pitfall 4: Unique Constraint Requires Soft-Delete Consideration
**What goes wrong:** `UNIQUE(project_id, category, name)` prevents creating a new element with the same name after soft-deleting the original, because the soft-deleted row still occupies the unique slot
**Why it happens:** Soft-delete (`is_deleted=true`) keeps the row in the table, so the unique constraint still applies
**How to avoid:** Accept this behavior as correct for v2.0 -- soft-deleted elements should block recreation because they might be un-deleted. The API should check for soft-deleted duplicates and offer to restore them. Alternatively, could use a partial unique index `WHERE is_deleted = FALSE`, but the simpler approach (check-and-restore) is more robust
**Warning signs:** IntegrityError on element creation when a soft-deleted duplicate exists

### Pitfall 5: breakdown_stale Column on Existing Populated Projects Table
**What goes wrong:** ALTER TABLE on a large projects table with a NOT NULL constraint fails because existing rows have no value
**Why it happens:** Adding a NOT NULL column without a DEFAULT to a table with existing data
**How to avoid:** Always use `ADD COLUMN IF NOT EXISTS breakdown_stale BOOLEAN DEFAULT FALSE` -- the DEFAULT clause handles existing rows. This is already the pattern in `003_template_system.sql` for adding columns to projects

## Code Examples

Verified patterns from the existing codebase:

### Migration File Pattern (from 008_agent_pipeline_maps.sql)
```sql
-- Migration 009: breakdown tables for v2.0 Script Breakdown
-- Creates breakdown_elements, element_scene_links, breakdown_runs tables
-- Adds breakdown_stale column to projects table

CREATE TABLE IF NOT EXISTS breakdown_elements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    category        VARCHAR(50) NOT NULL,
    name            VARCHAR(500) NOT NULL,
    description     TEXT DEFAULT '',
    metadata        JSONB DEFAULT '{}',
    source          VARCHAR(20) DEFAULT 'ai',
    user_modified   BOOLEAN DEFAULT FALSE,
    is_deleted      BOOLEAN DEFAULT FALSE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_breakdown_element UNIQUE (project_id, category, name)
);

CREATE INDEX IF NOT EXISTS idx_breakdown_elements_project
    ON breakdown_elements(project_id);
CREATE INDEX IF NOT EXISTS idx_breakdown_elements_category
    ON breakdown_elements(project_id, category);
-- Partial index: active elements lookup (excludes soft-deleted)
CREATE INDEX IF NOT EXISTS idx_breakdown_elements_active
    ON breakdown_elements(project_id, category) WHERE is_deleted = FALSE;

CREATE TABLE IF NOT EXISTS element_scene_links (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    element_id      UUID NOT NULL REFERENCES breakdown_elements(id) ON DELETE CASCADE,
    scene_item_id   UUID NOT NULL REFERENCES list_items(id) ON DELETE CASCADE,
    context         TEXT DEFAULT '',
    source          VARCHAR(20) DEFAULT 'ai',
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_element_scene UNIQUE (element_id, scene_item_id)
);

CREATE INDEX IF NOT EXISTS idx_element_scene_element
    ON element_scene_links(element_id);
CREATE INDEX IF NOT EXISTS idx_element_scene_scene
    ON element_scene_links(scene_item_id);

CREATE TABLE IF NOT EXISTS breakdown_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'pending',
    config          JSONB DEFAULT '{}',
    result_summary  JSONB DEFAULT '{}',
    error_message   TEXT,
    elements_created INTEGER DEFAULT 0,
    elements_updated INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_breakdown_runs_project
    ON breakdown_runs(project_id);

-- Add staleness tracking to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS breakdown_stale BOOLEAN DEFAULT FALSE;
```

### SQLAlchemy Model Pattern (from database.py)
```python
# Append to backend/app/models/database.py

class BreakdownCategory(str, enum.Enum):
    CHARACTER = "character"
    LOCATION = "location"
    PROP = "prop"
    WARDROBE = "wardrobe"
    VEHICLE = "vehicle"

class BreakdownElement(Base):
    __tablename__ = "breakdown_elements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, default="")
    metadata_ = Column("metadata", JSON, default=dict)
    source = Column(String(20), default="ai")
    user_modified = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = sa_relationship("Project", back_populates="breakdown_elements")
    scene_links = sa_relationship("ElementSceneLink", back_populates="element",
                                  cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', 'category', 'name', name='uq_breakdown_element'),
    )


class ElementSceneLink(Base):
    __tablename__ = "element_scene_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    element_id = Column(UUID(as_uuid=True), ForeignKey("breakdown_elements.id"), nullable=False, index=True)
    scene_item_id = Column(UUID(as_uuid=True), ForeignKey("list_items.id", ondelete="CASCADE"), nullable=False, index=True)
    context = Column(Text, default="")
    source = Column(String(20), default="ai")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    element = sa_relationship("BreakdownElement", back_populates="scene_links")

    __table_args__ = (
        UniqueConstraint('element_id', 'scene_item_id', name='uq_element_scene'),
    )


class BreakdownRun(Base):
    __tablename__ = "breakdown_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    status = Column(String(20), default="pending")
    config = Column(JSON, default=dict)
    result_summary = Column(JSON, default=dict)
    error_message = Column(Text)
    elements_created = Column(Integer, default=0)
    elements_updated = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    project = sa_relationship("Project", back_populates="breakdown_runs")
```

### Project Model Updates (additions needed)
```python
# In Project class, add these relationship lines after existing ones:
breakdown_elements = sa_relationship("BreakdownElement", back_populates="project",
                                      cascade="all, delete-orphan")
breakdown_runs = sa_relationship("BreakdownRun", back_populates="project",
                                  cascade="all, delete-orphan")

# Add this column alongside existing columns:
breakdown_stale = Column(Boolean, default=False)
```

### Pydantic Schema Pattern (from schemas.py)
```python
# Append to backend/app/models/schemas.py

class BreakdownElementCreate(BaseModel):
    category: str = Field(..., pattern="^(character|location|prop|wardrobe|vehicle)$")
    name: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    metadata: Dict = Field(default_factory=dict)

class BreakdownElementUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    metadata: Optional[Dict] = None

class BreakdownElementResponse(BaseModel):
    id: UUID
    project_id: UUID
    category: str
    name: str
    description: str
    metadata: Dict = Field(default_factory=dict, validation_alias="metadata_")
    source: str
    user_modified: bool
    is_deleted: bool
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BreakdownSummaryResponse(BaseModel):
    project_id: UUID
    is_stale: bool
    total_elements: int
    counts_by_category: Dict[str, int] = Field(default_factory=dict)
    last_run: Optional["BreakdownRunResponse"] = None

class BreakdownRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    config: Dict = Field(default_factory=dict)
    result_summary: Dict = Field(default_factory=dict)
    elements_created: int = 0
    elements_updated: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class SceneLinkCreate(BaseModel):
    scene_item_id: UUID
    context: str = ""
```

### Test Pattern (from test_pipeline_map_schema.py)
```python
# New file: backend/app/tests/test_breakdown_models.py

import uuid
import pytest
from app.models.database import BreakdownElement, ElementSceneLink, BreakdownRun, Base
from app.models.schemas import (
    BreakdownElementCreate, BreakdownElementUpdate,
    BreakdownElementResponse, BreakdownRunResponse,
    BreakdownSummaryResponse, SceneLinkCreate,
)


def test_breakdown_element_importable():
    assert BreakdownElement.__tablename__ == "breakdown_elements"

def test_element_scene_link_importable():
    assert ElementSceneLink.__tablename__ == "element_scene_links"

def test_breakdown_run_importable():
    assert BreakdownRun.__tablename__ == "breakdown_runs"

def test_tables_in_metadata():
    tables = Base.metadata.tables
    assert "breakdown_elements" in tables
    assert "element_scene_links" in tables
    assert "breakdown_runs" in tables

def test_element_orm_roundtrip(db_session):
    from app.models.database import Project
    project = Project(id=uuid.uuid4(), owner_id=uuid.uuid4(), title="Test")
    db_session.add(project)
    db_session.flush()

    elem = BreakdownElement(
        id=uuid.uuid4(), project_id=project.id,
        category="prop", name="Revolver",
        description="Smith & Wesson .38", source="ai",
    )
    db_session.add(elem)
    db_session.commit()
    db_session.refresh(elem)

    response = BreakdownElementResponse.model_validate(elem)
    assert response.name == "Revolver"
    assert response.category == "prop"
    assert response.user_modified is False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `class Config: orm_mode = True` | Pydantic v2 `model_config = ConfigDict(from_attributes=True)` | Pydantic 2.0 (2023) | Project already uses v2 throughout |
| SQLAlchemy 1.x declarative_base() | SQLAlchemy 2.0 declarative_base() (compatible) | SQLAlchemy 2.0 (2023) | Project uses 2.0.27 but with 1.x-style declarative_base(); functional and supported |
| `declarative_base()` from `sqlalchemy.ext.declarative` | `DeclarativeBase` from `sqlalchemy.orm` | SQLAlchemy 2.0 | Project uses the older import path; follow existing convention, do NOT modernize |

**Deprecated/outdated:**
- `sqlalchemy.ext.declarative.declarative_base()` is technically deprecated in favor of `sqlalchemy.orm.DeclarativeBase`, but the project uses the old import throughout -- follow existing convention for consistency

## Open Questions

1. **Partial unique index vs. full unique constraint for soft-deleted elements**
   - What we know: `UNIQUE(project_id, category, name)` blocks recreation after soft-delete
   - What's unclear: Whether users will want to "re-add" soft-deleted elements frequently
   - Recommendation: Use full unique constraint (as specified in ARCHITECTURE.md). API should check for soft-deleted duplicates and offer restore. This is safer and simpler. Can switch to partial index later if needed.

2. **BreakdownCategory enum in Python vs. plain string**
   - What we know: ARCHITECTURE.md uses VARCHAR(50) in SQL (not a PG ENUM), but Python code benefits from a str enum for validation
   - What's unclear: Whether the Pydantic schema pattern regex (`^(character|location|...)$`) is sufficient without a DB enum
   - Recommendation: Define `BreakdownCategory(str, enum.Enum)` in Python for code-level validation, but keep VARCHAR(50) in PostgreSQL for extensibility. The Pydantic schema uses a regex pattern for the same validation. This matches the existing approach where some enums are PG-level (like `phase_type`) and some are Python-only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest app/tests/test_breakdown_models.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKDN-01 | breakdown_elements table created with all columns, indexes, unique constraint | unit | `pytest app/tests/test_breakdown_models.py::test_breakdown_element_importable -x` | Wave 0 |
| BKDN-01 | user_modified flag and is_deleted soft-delete work correctly | unit | `pytest app/tests/test_breakdown_models.py::test_element_soft_delete -x` | Wave 0 |
| BKDN-02 | element_scene_links junction table with cascade on both FKs | unit | `pytest app/tests/test_breakdown_models.py::test_scene_link_cascade -x` | Wave 0 |
| BKDN-03 | breakdown_runs audit table with status, counts, timestamps | unit | `pytest app/tests/test_breakdown_models.py::test_breakdown_run_importable -x` | Wave 0 |
| BKDN-04 | breakdown_stale column on projects defaults to FALSE | unit | `pytest app/tests/test_breakdown_models.py::test_project_breakdown_stale -x` | Wave 0 |
| ALL | Pydantic schemas validate correctly and round-trip from ORM | unit | `pytest app/tests/test_breakdown_models.py::test_element_orm_roundtrip -x` | Wave 0 |
| ALL | All 3 tables registered in Base.metadata | unit | `pytest app/tests/test_breakdown_models.py::test_tables_in_metadata -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_breakdown_models.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_breakdown_models.py` -- covers BKDN-01 through BKDN-04 (model importability, ORM round-trips, cascade behavior, schema validation)
- [ ] No new framework install needed (pytest already configured)
- [ ] No new conftest fixtures needed (existing `db_session`, `client`, `mock_auth_headers` fixtures sufficient; `_patch_uuid_columns_for_sqlite()` auto-handles new models)

## Sources

### Primary (HIGH confidence)
- `backend/app/models/database.py` -- existing ORM model patterns (Project, PhaseData, ListItem, AgentPipelineMap)
- `backend/app/models/schemas.py` -- existing Pydantic v2 schema patterns (PipelineMapEntry, WizardRunResponse)
- `backend/migrations/008_agent_pipeline_maps.sql` -- latest migration pattern
- `backend/migrations/003_template_system.sql` -- ALTER TABLE pattern for adding columns to projects
- `backend/app/tests/conftest.py` -- SQLite test engine setup with UUID/Enum/Vector patching
- `backend/app/tests/test_pipeline_map_schema.py` -- model + schema test pattern
- `.planning/research/ARCHITECTURE.md` -- SQL DDL spec, schema design, relationship diagram
- `.planning/research/PITFALLS.md` -- metadata column clash, soft-delete + unique constraint interaction, cascade concerns

### Secondary (MEDIUM confidence)
- `.planning/research/SUMMARY.md` -- synthesized architecture decisions
- `.planning/REQUIREMENTS.md` -- BKDN-01 through BKDN-04 requirement definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all patterns established
- Architecture: HIGH -- SQL DDL already specified in ARCHITECTURE.md research, codebase patterns are clear
- Pitfalls: HIGH -- metadata column clash and cascade requirements verified against existing code

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable -- no external dependencies to change)
