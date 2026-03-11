# Phase 1: DB Foundation - Research

**Researched:** 2026-03-11
**Domain:** PostgreSQL migration + SQLAlchemy ORM model + Pydantic v2 schemas
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-02 | Pipeline mappings stored in dedicated `agent_pipeline_maps` DB table with efficient lookup by phase/step | Migration creates table with composite index; ORM model with cascade; Pydantic schemas for read/response |

</phase_requirements>

---

## Summary

Phase 1 is a pure data-layer phase: write a SQL migration, add a SQLAlchemy model, and define two Pydantic schemas. No service logic. No API endpoints. No background tasks. All three plans are additive — nothing in the existing codebase is modified, only extended.

The `agent_pipeline_maps` table stores one row per agent-to-pipeline-step pairing. It is pre-computed by the Phase 2 composer and looked up at generation time by the Phase 5 review middleware. The table's value over a JSON column on `agents` is the composite index on `(owner_id, phase, subsection_key)` — enabling O(1) lookup at generation time without loading all agents.

The `pipeline_dirty` column belongs on the `agent_pipeline_maps` table per the ROADMAP success criterion. Practically this column controls whether a row's mapping is stale (needs re-computation). Phase 2 will read and clear this flag during composition.

**Primary recommendation:** Follow existing migration file patterns exactly (UUID primary key via `uuid_generate_v4()`, `TIMESTAMPTZ DEFAULT NOW()`, `IF NOT EXISTS` guards, explicit index naming). Follow existing SQLAlchemy model patterns exactly (`UUID(as_uuid=True)`, `func.now()`, `sa_relationship` alias). Follow Pydantic v2 patterns already present in `schemas.py` (`ConfigDict(from_attributes=True)`, `Field`, `Optional`).

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PostgreSQL 15 | 15 | Store `agent_pipeline_maps` rows | Existing DB — no choice |
| SQLAlchemy | 2.0.27 | ORM model for `AgentPipelineMap` | Existing ORM — matches all other models |
| Pydantic v2 | >=2.10 | `PipelineMapEntry`, `PipelineMapResponse` schemas | Existing validation layer — all schemas use Pydantic v2 |
| psycopg2-binary | 2.9.9 | PostgreSQL driver | Existing driver |

**Installation:** None required. All dependencies already in `backend/requirements.txt`.

---

## Architecture Patterns

### Migration File Convention

All migrations in `backend/migrations/` follow these conventions (verified by reading existing files):

1. Filename: `NNN_description.sql` — sequential number, underscore-separated description
2. Next migration number is **008** (latest is `007_snippets_table.sql`)
3. UUID primary key: `DEFAULT uuid_generate_v4()` (NOT `gen_random_uuid()` — existing files use `uuid_generate_v4`)
4. Timestamps: `TIMESTAMPTZ DEFAULT NOW()` (NOT `TIMESTAMP WITH TIME ZONE` — newer migrations use `TIMESTAMPTZ`)
5. `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` is already enabled; do NOT re-declare
6. Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` for idempotency
7. Place all indexes after the table definition, not inline
8. Foreign key references: `REFERENCES agents(id) ON DELETE CASCADE` (no schema qualifier needed)

### Exact Migration Template for `agent_pipeline_maps`

```sql
-- Migration 008: agent_pipeline_maps table for pipeline orchestration
-- Stores AI-computed mappings of agents to template pipeline steps.
-- One row per agent-step pairing. Looked up at generation time by phase/subsection_key.

CREATE TABLE IF NOT EXISTS agent_pipeline_maps (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id        UUID NOT NULL,
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    phase           VARCHAR(50) NOT NULL,
    subsection_key  VARCHAR(100) NOT NULL,
    confidence      FLOAT NOT NULL DEFAULT 0.0,
    rationale       TEXT,
    pipeline_dirty  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (owner_id, agent_id, phase, subsection_key)
);

-- Composite lookup index: used at generation time to find agents for a step
CREATE INDEX IF NOT EXISTS idx_pipeline_map_lookup
    ON agent_pipeline_maps (owner_id, phase, subsection_key);

-- Secondary index: used by Phase 2 composer to find dirty rows per owner
CREATE INDEX IF NOT EXISTS idx_pipeline_map_dirty
    ON agent_pipeline_maps (owner_id, pipeline_dirty)
    WHERE pipeline_dirty = TRUE;
```

**Note on `pipeline_dirty` placement:** The ROADMAP success criterion explicitly lists it as a column in `agent_pipeline_maps`, not on the `agents` table. Placing it here means: when the Phase 2 composer successfully re-computes a mapping row, it sets `pipeline_dirty = FALSE` on that row. When an agent's semantic fields change, the Phase 3 CRUD wiring sets `pipeline_dirty = TRUE` on all `agent_pipeline_maps` rows for that agent, or inserts new rows with `pipeline_dirty = TRUE`. This is consistent with the row being the unit of stale tracking.

### SQLAlchemy Model Convention

Verified from `backend/app/models/database.py`:

1. File: add `AgentPipelineMap` class to `database.py` — the single file for all ORM models
2. Imports already present: `Column`, `String`, `DateTime`, `ForeignKey`, `Text`, `func`, `Boolean`, `Float`, `UniqueConstraint`; `UUID` from `sqlalchemy.dialects.postgresql`; `relationship as sa_relationship`; `uuid`
3. Primary key: `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)` — matches all other models
4. Foreign key column: `Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)`
5. Timestamps: `Column(DateTime(timezone=True), server_default=func.now())` for `created_at`; `Column(DateTime(timezone=True), onupdate=func.now())` for `updated_at`
6. Relationship naming: use `sa_relationship` alias (NOT `relationship` — the file aliases it)
7. Table args: use `__table_args__` tuple with `UniqueConstraint` (matches `PhaseData` pattern)
8. The `Agent` model already exists. Add a back-reference relationship `pipeline_maps` to `Agent`, pointing to `AgentPipelineMap`

### Exact SQLAlchemy Model

```python
class AgentPipelineMap(Base):
    __tablename__ = "agent_pipeline_maps"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id        = Column(UUID(as_uuid=True), nullable=False, index=True)
    agent_id        = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    phase           = Column(String(50), nullable=False)
    subsection_key  = Column(String(100), nullable=False)
    confidence      = Column(Float, nullable=False, default=0.0)
    rationale       = Column(Text)
    pipeline_dirty  = Column(Boolean, nullable=False, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    agent = sa_relationship("Agent", back_populates="pipeline_maps")

    __table_args__ = (
        UniqueConstraint(
            "owner_id", "agent_id", "phase", "subsection_key",
            name="uq_pipeline_map_lookup"
        ),
    )
```

Then add to the `Agent` model:
```python
# Add inside Agent class after existing relationships:
pipeline_maps = sa_relationship(
    "AgentPipelineMap",
    back_populates="agent",
    cascade="all, delete-orphan",
)
```

**Critical:** The `cascade="all, delete-orphan"` on the SQLAlchemy relationship mirrors the `ON DELETE CASCADE` in SQL — both are required. The SQL FK handles DB-level cascade; the ORM cascade handles ORM-level operations (e.g., `session.delete(agent)` without `db.commit()` yet).

### Pydantic Schema Convention

Verified from `backend/app/models/schemas.py`:

1. File: add new schemas to `schemas.py` — the single schemas file
2. Import section at top already includes `from .database import ... AgentType` — add new model class if needed (for `from_attributes` to work the ORM class doesn't need to be imported, just used at runtime)
3. All read/response schemas use `model_config = ConfigDict(from_attributes=True)` — required for ORM-to-Pydantic conversion
4. UUID fields: `UUID` type from `uuid` stdlib (already imported at top of schemas.py)
5. Optional fields: `Optional[str] = None` pattern
6. Datetime fields: `Optional[datetime] = None` pattern

### Exact Pydantic Schemas

```python
# ============================================================
# Pipeline Map schemas (Phase 1 — DB Foundation)
# ============================================================

class PipelineMapEntry(BaseModel):
    """Single agent-to-step mapping row. Used for ORM round-trips and list items."""
    id: UUID
    owner_id: UUID
    agent_id: UUID
    phase: str
    subsection_key: str
    confidence: float = 0.0
    rationale: Optional[str] = None
    pipeline_dirty: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PipelineMapResponse(BaseModel):
    """Response shape for GET /api/agents/pipeline-map (Phase 3).
    Nested by phase then subsection_key for tree rendering."""
    owner_id: UUID
    entries: List[PipelineMapEntry] = Field(default_factory=list)
    total_mappings: int = 0

    model_config = ConfigDict(from_attributes=True)
```

**Schema naming rationale:** `PipelineMapEntry` maps 1:1 to an ORM row (enables `from_attributes=True` round-trips). `PipelineMapResponse` is the API-level response wrapper that Phase 3 will return from the GET endpoint; defined now so the planner can reference it in Phase 3.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom UUID logic | `uuid_generate_v4()` in SQL + `uuid.uuid4` in ORM | Already the pattern in all 8 existing migrations and all ORM models |
| ON DELETE CASCADE | Manual deletion queries | `ON DELETE CASCADE` in FK + `cascade="all, delete-orphan"` in relationship | One source of truth; avoids orphan rows if ORM-level delete is used |
| Idempotent migration | Manual "does table exist?" checks | `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS` | Already the pattern in migrations 004-007; safe to re-run |
| Schema validation | Manual isinstance checks | Pydantic `Field()` constraints | Existing pattern throughout schemas.py |

---

## Common Pitfalls

### Pitfall 1: Using `gen_random_uuid()` Instead of `uuid_generate_v4()`

**What goes wrong:** PostgreSQL has two UUID functions. `gen_random_uuid()` is available in PG 13+ without an extension. But ALL existing migrations use `uuid_generate_v4()` with the `uuid-ossp` extension (enabled in `init_db.sql`). Using `gen_random_uuid()` would work but is inconsistent.

**How to avoid:** Use `uuid_generate_v4()` in the migration SQL. The extension is already enabled.

---

### Pitfall 2: Missing `cascade="all, delete-orphan"` on SQLAlchemy Relationship

**What goes wrong:** If the SQL FK has `ON DELETE CASCADE` but the SQLAlchemy relationship does NOT have `cascade="all, delete-orphan"`, then:
- DB-level deletes (e.g., raw SQL `DELETE FROM agents`) will cascade correctly
- ORM-level deletes (e.g., `session.delete(agent)` then `session.commit()`) will NOT cascade — SQLAlchemy will try to set `agent_id = NULL` before delete, causing a NOT NULL constraint violation since `agent_id` is `nullable=False`

**How to avoid:** Always set both. SQL: `ON DELETE CASCADE`. ORM relationship on `Agent`: `cascade="all, delete-orphan"`.

---

### Pitfall 3: Forgetting to Import `AgentPipelineMap` in `database.py` Consumers

**What goes wrong:** `AgentPipelineMap` will be used by Phase 2's `pipeline_composer.py` and Phase 5's review middleware. If those files import from `models.database` but `AgentPipelineMap` is not registered in `Base.metadata` (by being defined in `database.py`), SQLAlchemy won't include it in `Base.metadata.create_all()` and tests using SQLite in-memory DB will fail.

**How to avoid:** Define `AgentPipelineMap` in `database.py` (not a separate file). The test's `conftest.py` calls `Base.metadata.create_all(bind=engine)` which picks up all models defined in `database.py` automatically.

---

### Pitfall 4: SQLite Test Engine Doesn't Support `FLOAT` or `BOOLEAN` Natively

**What goes wrong:** The test suite (`conftest.py`) uses SQLite in-memory via a patching mechanism that replaces `PG_UUID` → `String(36)`, `SAEnum` → `String(50)`, and `SafeVector` → `VectorAsText`. However, SQLite **does** support `FLOAT` and `BOOLEAN` natively (as REAL and INTEGER respectively), so no additional patches are needed for `confidence: Float` or `pipeline_dirty: Boolean`.

**How to avoid:** No action needed. Confirm by running `pytest` — if SQLite rejects these types, add a patch in `conftest.py` following the existing `_patch_uuid_columns_for_sqlite()` pattern.

---

### Pitfall 5: `pipeline_dirty` Placement Discrepancy

**What goes wrong:** The PITFALLS research document says "Add a `pipeline_dirty` flag to the Agent model." The ROADMAP success criterion says `agent_pipeline_maps` must have a `pipeline_dirty` column. These are different locations.

**Resolution:** Follow the ROADMAP. Place `pipeline_dirty` on `agent_pipeline_maps`. Rationale: the flag tracks staleness of a specific mapping row, not staleness of an agent globally. When an agent's semantic fields change, the Phase 3 CRUD wiring should set `pipeline_dirty = TRUE` on all `agent_pipeline_maps` rows for that `agent_id` (or let the Phase 2 composer handle re-insertion). This is cleaner than a separate flag on `Agent` because:
1. The mapping row is the unit being re-composed
2. When all rows for an agent are re-composed, the flag is cleared row-by-row — no separate Agent update needed
3. Phase 2 success criterion #3 says "semantic edit DOES set `pipeline_dirty=True`" — this makes more sense as setting it on the existing mapping rows

---

### Pitfall 6: Test Infrastructure Gap — `AgentPipelineMap` Not in SQLite Patch

**What goes wrong:** The `conftest.py` `_patch_uuid_columns_for_sqlite()` function iterates `Base.metadata.tables.values()` and patches UUID/Enum/Vector columns. Since `AgentPipelineMap` is a new model, its UUID columns will be patched automatically (the loop covers all tables in `Base.metadata`). However, if `AgentPipelineMap` is defined AFTER `conftest.py` creates the engine, the table won't be in `Base.metadata` yet.

**How to avoid:** The `test_engine` fixture calls `_patch_uuid_columns_for_sqlite()` and then `Base.metadata.create_all(bind=engine)`. The patch function must run after ALL models are imported. Since `conftest.py` imports `from app.models.database import Base` (which imports the entire module), all models defined in `database.py` are available. As long as `AgentPipelineMap` is in `database.py`, it's automatically covered.

---

## Code Examples

### Pattern: UniqueConstraint in __table_args__ (from `PhaseData`)

```python
# Source: backend/app/models/database.py — PhaseData model
__table_args__ = (UniqueConstraint('project_id', 'phase', 'subsection_key', name='uq_phase_data_lookup'),)
```

Note: the trailing comma after `UniqueConstraint(...)` is required when it's the only element — makes it a tuple.

---

### Pattern: Relationship with cascade (from `Project`)

```python
# Source: backend/app/models/database.py — Project model
phase_data = sa_relationship("PhaseData", back_populates="project", cascade="all, delete-orphan")
```

---

### Pattern: Float column (from `Concept`)

```python
# Source: backend/app/models/database.py — Concept model
quality_score = Column(Float, nullable=True)
```

---

### Pattern: Boolean column (from `BookChunk`)

```python
# Source: backend/app/models/database.py — BookChunk model
is_deleted = Column(Boolean, default=False, nullable=False)
```

---

### Pattern: Pydantic schema with from_attributes (from `AgentResponse`)

```python
# Source: backend/app/models/schemas.py — AgentResponse
class AgentResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

### Pattern: Pydantic list response wrapper (from `SnippetListResponse`)

```python
# Source: backend/app/models/schemas.py — SnippetListResponse
class SnippetListResponse(BaseModel):
    items: List[SnippetResponse]
    total: int
    page: int
    per_page: int
    pages: int
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TIMESTAMP WITH TIME ZONE` | `TIMESTAMPTZ` | Early migrations used long form; migrations 004+ use `TIMESTAMPTZ` | Use `TIMESTAMPTZ` in new migration |
| `uuid_generate_v4()` (requires extension) | Same — extension already enabled | N/A | Keep using `uuid_generate_v4()` for consistency |
| Pydantic v1 `class Config:` | Pydantic v2 `model_config = ConfigDict(...)` | Current codebase is fully Pydantic v2 | Use `ConfigDict(from_attributes=True)` |

---

## Open Questions

1. **Does the `pipeline_dirty` flag on `agent_pipeline_maps` rows mean the composer must handle the case where no rows exist yet?**
   - What we know: A newly created agent has no `agent_pipeline_maps` rows. The Phase 2 composer creates them on first composition.
   - What's unclear: Should new rows start with `pipeline_dirty = TRUE` to signal "never computed" vs. the composer simply inserting fresh rows?
   - Recommendation: Default `pipeline_dirty = FALSE` in the schema (per the migration). The Phase 2 composer always inserts or upserts — a missing row and a `pipeline_dirty = TRUE` row are both "needs composition." The distinction matters in Phase 2, not Phase 1.

2. **Should `PipelineMapResponse` be defined in Phase 1 or Phase 3?**
   - What we know: `PipelineMapResponse` is only used by the Phase 3 GET endpoint.
   - What's unclear: If defined in Phase 1, does the Phase 3 planner know to use it without re-defining it?
   - Recommendation: Define both schemas in Phase 1 to make the data contract explicit. The `PipelineMapResponse` wrapper is simple enough that it won't change shape when Phase 3 builds the endpoint. Mark with a comment linking to Phase 3.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | None — pytest invoked directly |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/test_pipeline_map_schema.py -x` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-02 | `AgentPipelineMap` model is importable and mapped to correct table | unit | `pytest app/tests/test_pipeline_map_schema.py::test_model_importable -x` | Wave 0 |
| COMP-02 | `PipelineMapEntry` schema validates a valid ORM row round-trip | unit | `pytest app/tests/test_pipeline_map_schema.py::test_pipeline_map_entry_roundtrip -x` | Wave 0 |
| COMP-02 | `PipelineMapResponse` schema instantiates with empty entry list | unit | `pytest app/tests/test_pipeline_map_schema.py::test_pipeline_map_response_empty -x` | Wave 0 |
| COMP-02 | `AgentPipelineMap` is present in `Base.metadata.tables` | unit | `pytest app/tests/test_pipeline_map_schema.py::test_model_in_metadata -x` | Wave 0 |
| COMP-02 | Migration SQL creates table (verified via `\d agent_pipeline_maps`) | manual | N/A — run migration and inspect in psql | N/A |

### Sampling Rate

- **Per task commit:** `pytest app/tests/test_pipeline_map_schema.py -x`
- **Per wave merge:** `pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/app/tests/test_pipeline_map_schema.py` — covers all COMP-02 schema/model tests above; does not exist yet, must be created in Plan 01-03

*(Existing test infrastructure covers `conftest.py`, `test_engine`, `db_session`, `client` fixtures — no new fixture infrastructure needed for this phase's unit tests)*

---

## Sources

### Primary (HIGH confidence)

- Direct file read: `backend/app/models/database.py` — all ORM model patterns verified
- Direct file read: `backend/app/models/schemas.py` — all Pydantic v2 schema patterns verified
- Direct file read: `backend/migrations/002_knowledge_graph.sql` through `007_snippets_table.sql` — migration conventions verified
- Direct file read: `backend/app/tests/conftest.py` — SQLite test patching mechanism fully understood
- Direct file read: `.planning/ROADMAP.md` — authoritative Phase 1 success criteria and column list
- Direct file read: `.planning/research/ARCHITECTURE.md` — `agent_pipeline_maps` table schema design
- Direct file read: `backend/requirements.txt` — confirmed SQLAlchemy 2.0.27, Pydantic >=2.10, pytest 8.0.2

### Secondary (MEDIUM confidence)

- Direct file read: `.planning/research/PITFALLS.md` — `pipeline_dirty` flag design (placement discrepancy resolved by ROADMAP)
- Direct file read: `.planning/research/STACK.md` — confirmed no new dependencies needed

### Tertiary (LOW confidence)

None — all claims verified from codebase files directly.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all dependencies confirmed in `requirements.txt`
- Architecture: HIGH — all patterns verified from existing models and migrations
- Pitfalls: HIGH — derived from direct codebase analysis plus ROADMAP/PITFALLS research docs
- Schema design: HIGH — column names and types taken verbatim from ROADMAP success criteria and ARCHITECTURE.md

**Research date:** 2026-03-11
**Valid until:** Stable (no external dependencies; all findings from local codebase)
