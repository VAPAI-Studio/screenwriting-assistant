# Phase 19: Shot CRUD API & Core Model - Research

**Researched:** 2026-03-19
**Domain:** FastAPI CRUD endpoints for Shot model (backend only)
**Confidence:** HIGH

## Summary

Phase 19 is a straightforward backend CRUD implementation. The Shot model, ShotElement junction table, Pydantic schemas (ShotCreate, ShotUpdate, ShotResponse), and the database migration already exist from Phase 17. This phase creates a single new file (`backend/app/api/endpoints/shots.py`), registers it in `main.py`, and writes tests in a new test file.

The project has two well-established CRUD endpoint patterns: `breakdown.py` (the primary template) and `list_items.py` (for reorder logic). Both use the same `_verify_project_ownership()` helper, `selectinload` for eager-loading relationships, and standard HTTP status codes (201 for create, 204 for delete). The reorder endpoint in `list_items.py` already uses the `ReorderRequest` / `ReorderItem` schemas that can be reused for shot reordering.

**Primary recommendation:** Clone the `breakdown.py` endpoint structure, adapting it for shots. Reuse `ReorderRequest` schema from `schemas.py` for the reorder endpoint. Follow `test_breakdown_api.py` test organization exactly (class-per-feature, `_create_project_via_api` helper).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- GET list format: Flat list response `[{shot}, {shot}, ...]` sorted by `scene_item_id` + `sort_order`. Frontend groups by `scene_item_id` client-side. Shots with `scene_item_id = null` (unattached) are included.
- Reorder endpoint: `POST /shots/{project_id}/reorder` with body `[{id: uuid, sort_order: int}, ...]`. Bulk array. Server validates all shot IDs belong to the project; returns 403 for foreign shots.
- shot_number behavior: User-supplied on create (defaults to 1 if omitted). Server does NOT auto-assign or re-number. Whatever client sends is stored as-is.
- Test coverage: Happy paths for create (201), list (200), get single (200), update (200), delete (204), reorder (200). Auth/ownership errors: 404 for wrong project, 401 for unauthenticated. Mirrors existing `test_api.py` test class pattern.

### Claude's Discretion
- URL structure for single-shot endpoints (`/shots/{project_id}/{shot_id}` vs `/shot/{shot_id}`) -- follow existing breakdown.py pattern
- Whether to add a `scene_item_id` query param filter to the list endpoint (can add if obviously useful)
- selectinload strategy for related data in responses
- Exact test class name and fixture setup

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-04 | Shot CRUD API endpoints exist (GET list, POST create, GET single, PUT update, DELETE) | All 5 CRUD endpoints follow `breakdown.py` patterns with Shot model and ShotCreate/ShotUpdate/ShotResponse schemas already defined in schemas.py |
| SHOT-01 | User can create a shot manually with freeform text fields | POST endpoint accepts ShotCreate schema which has `fields: Dict` (JSONB) for all freeform content |
| SHOT-02 | Shots have freeform text fields: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes | The `fields` JSONB column on Shot model stores all these as arbitrary keys; no enum constraint needed |
</phase_requirements>

## Standard Stack

### Core (all pre-existing -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API framework | Already in use; APIRouter pattern |
| SQLAlchemy | existing | ORM | Shot model already defined |
| Pydantic v2 | existing | Request/response validation | ShotCreate/ShotUpdate/ShotResponse already defined |
| pytest | existing | Testing | test_breakdown_api.py pattern established |

### Supporting (all pre-existing)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy.orm.selectinload | existing | Eager loading | Load shot_elements relationship if needed |
| fastapi.status | existing | HTTP status constants | HTTP_201_CREATED, HTTP_204_NO_CONTENT |
| uuid.UUID | stdlib | Path parameter type | Shot and project IDs |

### Alternatives Considered
None -- this is a continuation of established patterns with no new technology choices.

**Installation:**
```bash
# No new packages required
```

## Architecture Patterns

### File Structure
```
backend/app/
  api/endpoints/
    shots.py              # NEW -- shot CRUD + reorder endpoints
  models/
    database.py           # EXISTING -- Shot, ShotElement models (lines 542-573)
    schemas.py            # EXISTING -- ShotCreate, ShotUpdate, ShotResponse (lines 731-776)
                          #             ReorderItem, ReorderRequest (lines 415-421)
  main.py                 # MODIFY -- add shots router registration
  tests/
    test_shots_api.py     # NEW -- shot CRUD tests
```

### Pattern 1: Project-Scoped CRUD Endpoints (from breakdown.py)

**What:** All shot endpoints are scoped under a project_id path parameter. A `_verify_project_ownership()` helper validates that the authenticated user owns the project before any operation.

**When to use:** Every endpoint in shots.py.

**Example:**
```python
# Source: backend/app/api/endpoints/breakdown.py lines 46-54
def _verify_project_ownership(db: Session, project_id: UUID, user_id: UUID) -> database.Project:
    """Verify user owns the project. Returns project or raises 404."""
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(user_id)
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
```

### Pattern 2: URL Structure Decision

**What:** The breakdown.py module uses two URL patterns:
- Collection endpoints: `/elements/{project_id}` (list, create)
- Single-item endpoints: `/element/{element_id}` (update, delete) -- note: element_id only, no project_id

**Recommendation for shots:** Use `/shots/{project_id}` for list and create, `/shots/{project_id}/{shot_id}` for get-single, update, delete. Including project_id in single-shot routes enables ownership verification without a separate join and is consistent with the CONTEXT.md reorder URL `POST /shots/{project_id}/reorder`.

### Pattern 3: Partial Update with model_dump(exclude_unset=True)

**What:** The update endpoint uses Pydantic's `model_dump(exclude_unset=True)` to only apply fields the client explicitly sent, enabling partial updates.

**Example:**
```python
# Source: backend/app/api/endpoints/breakdown.py lines 164-191
update_data = body.model_dump(exclude_unset=True)
for field, value in update_data.items():
    setattr(shot, field, value)
db.commit()
db.refresh(shot)
```

### Pattern 4: Reorder via Bulk Array (from list_items.py)

**What:** The reorder endpoint receives a `ReorderRequest` with an array of `{id, sort_order}` pairs. Each item is updated in a single transaction. The existing `ReorderRequest` / `ReorderItem` schemas in `schemas.py` (lines 415-421) can be reused directly.

**Adaptation for shots:** Add validation that every shot ID belongs to the target project. The CONTEXT.md specifies returning 403 for foreign shot IDs (unlike list_items.py which silently ignores non-matching IDs due to the `phase_data_id` filter).

**Example:**
```python
# Source: backend/app/api/endpoints/list_items.py lines 171-188
@router.post("/{project_id}/reorder")
async def reorder_shots(
    project_id: UUID,
    reorder: schemas.ReorderRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_project_ownership(db, project_id, current_user.id)

    # Validate all shot IDs belong to this project
    shot_ids = [str(item.id) for item in reorder.items]
    owned_count = db.query(database.Shot).filter(
        database.Shot.id.in_(shot_ids),
        database.Shot.project_id == str(project_id)
    ).count()
    if owned_count != len(shot_ids):
        raise HTTPException(status_code=403, detail="One or more shot IDs do not belong to this project")

    for item in reorder.items:
        db.query(database.Shot).filter(
            database.Shot.id == str(item.id)
        ).update({"sort_order": item.sort_order})
    db.commit()
    return {"status": "success", "message": "Shots reordered"}
```

### Pattern 5: Router Registration (from main.py)

**What:** Each endpoint module is imported and registered with `app.include_router()` with a prefix and tags.

**Example:**
```python
# Source: backend/app/main.py lines 11, 97
from .api.endpoints import shots as shots_ep
# ... after the breakdown line (line 97):
app.include_router(shots_ep.router, prefix="/api/shots", tags=["shots"])
```

### Anti-Patterns to Avoid
- **N+1 queries in list:** Do NOT iterate shots and separately query relationships. Use `selectinload(Shot.shot_elements)` if elements are needed in the response. However, since `ShotResponse` does not include `shot_elements`, selectinload may not be needed for the list endpoint.
- **Hard-coding user IDs in tests:** Use the `_create_project_via_api()` helper pattern (from `test_breakdown_api.py`) so the mock auth user ID is correctly stored as owner_id.
- **Using `db.delete()` for shots:** Use hard delete (not soft delete) since Shot has no `is_deleted` column. This differs from breakdown elements which use soft delete.
- **Forgetting `str()` on UUID comparisons:** SQLite test engine stores UUIDs as strings. Always use `filter(Shot.id == str(shot_id))`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reorder schema | Custom request body class | `schemas.ReorderRequest` + `schemas.ReorderItem` | Already defined at schemas.py lines 415-421 |
| Project ownership check | Inline query per endpoint | `_verify_project_ownership()` helper | Established pattern; keeps code DRY |
| Partial update logic | Manual field-by-field checking | `model_dump(exclude_unset=True)` + `setattr` loop | Pydantic v2 built-in; handles Optional fields correctly |
| Auth dependency | Custom auth check | `Depends(get_current_user)` | Already wired; returns `schemas.User` with mock support |
| Test DB setup | Manual SQLAlchemy session | `conftest.py` fixtures (`client`, `db_session`, `mock_auth_headers`) | Session-scoped engine with SQLite; function-scoped rollback |

**Key insight:** This phase introduces zero new patterns. Every building block exists. The value is in correctly assembling existing pieces.

## Common Pitfalls

### Pitfall 1: UUID String Conversion in SQLite Tests
**What goes wrong:** Tests fail with type mismatch errors when filtering by UUID.
**Why it happens:** conftest.py patches PostgreSQL UUID columns to String(36) for SQLite. All ORM filters must compare `str(uuid_value)`, not raw UUID objects.
**How to avoid:** Always use `Shot.id == str(shot_id)` in queries, never `Shot.id == shot_id`.
**Warning signs:** `sqlalchemy.exc.OperationalError` or empty query results in tests.

### Pitfall 2: Delete Status Code Mismatch
**What goes wrong:** Test expects 204 but gets 200, or vice versa.
**Why it happens:** breakdown.py delete returns 200 with a JSON body (soft delete). For shots, the CONTEXT.md specifies 204 (HTTP_204_NO_CONTENT), meaning no response body.
**How to avoid:** Use `status_code=status.HTTP_204_NO_CONTENT` on the delete route decorator AND return `Response(status_code=status.HTTP_204_NO_CONTENT)`.
**Warning signs:** Test assertion failures on status code.

### Pitfall 3: ShotResponse.fields JSONB vs SQLite JSON
**What goes wrong:** JSONB columns work differently in SQLite tests vs PostgreSQL production.
**Why it happens:** SQLite stores JSON as text. SQLAlchemy's JSON type handles serialization, but edge cases with empty dict defaults can vary.
**How to avoid:** Use `Field(default_factory=dict)` in Pydantic schemas (already done in ShotCreate/ShotResponse). In tests, explicitly pass `fields={}` or `fields={"shot_size": "Wide"}` to validate JSONB round-trip.
**Warning signs:** `None` appearing where `{}` is expected.

### Pitfall 4: Reorder 403 vs 404
**What goes wrong:** Returning wrong error code when foreign shot IDs are submitted.
**Why it happens:** CONTEXT.md specifically says 403 for foreign shot IDs in reorder, which differs from the typical 404 pattern used elsewhere.
**How to avoid:** Explicitly check that all submitted IDs belong to the project. Return 403 (Forbidden) with a clear message, not 404.
**Warning signs:** Review the CONTEXT.md decision carefully before implementing.

### Pitfall 5: Forgetting Router Registration
**What goes wrong:** All tests pass but the endpoint is unreachable in the running app.
**Why it happens:** New endpoint file is created but not imported/registered in `main.py`.
**How to avoid:** Add both the import line and `app.include_router()` call in `main.py`.
**Warning signs:** 404 on all shots endpoints in manual testing.

## Code Examples

Verified patterns from existing codebase:

### Complete Shot Create Endpoint
```python
# Adapted from: backend/app/api/endpoints/breakdown.py lines 110-161
@router.post("/{project_id}", response_model=schemas.ShotResponse, status_code=status.HTTP_201_CREATED)
async def create_shot(
    project_id: UUID,
    body: schemas.ShotCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new shot for the project."""
    _verify_project_ownership(db, project_id, current_user.id)

    db_shot = database.Shot(
        project_id=str(project_id),
        scene_item_id=str(body.scene_item_id) if body.scene_item_id else None,
        shot_number=body.shot_number,
        script_text=body.script_text,
        script_range=body.script_range or {},
        fields=body.fields or {},
        sort_order=body.sort_order if body.sort_order is not None else 0,
        source=body.source,
    )
    db.add(db_shot)
    db.commit()
    db.refresh(db_shot)
    return db_shot
```

### Complete Shot List Endpoint
```python
# Adapted from: backend/app/api/endpoints/breakdown.py lines 69-107
@router.get("/{project_id}", response_model=List[schemas.ShotResponse])
async def list_shots(
    project_id: UUID,
    scene_item_id: Optional[UUID] = None,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List shots for a project, sorted by scene_item_id + sort_order."""
    _verify_project_ownership(db, project_id, current_user.id)

    query = db.query(database.Shot).filter(
        database.Shot.project_id == str(project_id)
    )

    if scene_item_id is not None:
        query = query.filter(database.Shot.scene_item_id == str(scene_item_id))

    shots = query.order_by(
        database.Shot.scene_item_id,
        database.Shot.sort_order
    ).all()
    return shots
```

### Test Helper Pattern
```python
# Adapted from: backend/app/tests/test_breakdown_api.py lines 25-33
def _create_project_via_api(client, mock_auth_headers, title="Test Project"):
    """Create a project through the API so owner_id is stored correctly for SQLite."""
    resp = client.post(
        "/api/projects/",
        json={"title": title, "framework": "three_act"},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200, f"Project creation failed: {resp.json()}"
    return resp.json()["id"]


def _make_shot(db_session, project_id, shot_number=1, fields=None, scene_item_id=None, sort_order=0):
    """Create a Shot directly in the DB for test setup."""
    shot = Shot(
        id=str(uuid.uuid4()),
        project_id=project_id,
        scene_item_id=str(scene_item_id) if scene_item_id else None,
        shot_number=shot_number,
        fields=fields or {},
        sort_order=sort_order,
        source="user",
    )
    db_session.add(shot)
    db_session.flush()
    return shot
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Normalized shot field columns | JSONB `fields` column | v3.0 design (Phase 17) | Extensible, no migrations for new fields |
| Soft delete for all entities | Hard delete for shots | v3.0 design | Shot has no is_deleted column; use `db.delete()` |
| Per-item reorder | Bulk array reorder | Existing list_items.py pattern | Single transaction, client sends complete new ordering |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | backend/pytest.ini or pyproject.toml (existing) |
| Quick run command | `cd backend && python -m pytest app/tests/test_shots_api.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-04 | POST creates shot (201) | unit | `pytest app/tests/test_shots_api.py::TestCreateShot -x` | No -- Wave 0 |
| DATA-04 | GET lists shots (200) | unit | `pytest app/tests/test_shots_api.py::TestListShots -x` | No -- Wave 0 |
| DATA-04 | GET single shot (200) | unit | `pytest app/tests/test_shots_api.py::TestGetShot -x` | No -- Wave 0 |
| DATA-04 | PUT updates shot (200) | unit | `pytest app/tests/test_shots_api.py::TestUpdateShot -x` | No -- Wave 0 |
| DATA-04 | DELETE removes shot (204) | unit | `pytest app/tests/test_shots_api.py::TestDeleteShot -x` | No -- Wave 0 |
| DATA-04 | POST reorder (200) | unit | `pytest app/tests/test_shots_api.py::TestReorderShots -x` | No -- Wave 0 |
| SHOT-01 | Create with freeform fields | unit | `pytest app/tests/test_shots_api.py::TestCreateShot::test_create_shot_with_fields -x` | No -- Wave 0 |
| SHOT-02 | Fields JSONB stores all standard keys | unit | `pytest app/tests/test_shots_api.py::TestCreateShot::test_create_shot_all_standard_fields -x` | No -- Wave 0 |
| -- | Auth: no token returns 401/403 | unit | `pytest app/tests/test_shots_api.py::TestCrossCutting::test_no_auth -x` | No -- Wave 0 |
| -- | Ownership: wrong project returns 404 | unit | `pytest app/tests/test_shots_api.py::TestCrossCutting::test_wrong_project -x` | No -- Wave 0 |
| -- | Reorder: foreign shot IDs returns 403 | unit | `pytest app/tests/test_shots_api.py::TestReorderShots::test_reorder_foreign_shot_403 -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_shots_api.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_shots_api.py` -- covers DATA-04, SHOT-01, SHOT-02
- [ ] `backend/app/api/endpoints/shots.py` -- the endpoint file itself
- [ ] Router registration in `backend/app/main.py` -- import + include_router

*(No framework install needed -- pytest and test fixtures already exist in conftest.py)*

## Open Questions

1. **Should ShotResponse include shot_elements?**
   - What we know: `ShotResponse` in schemas.py does NOT include a `shot_elements` field. The `Shot` model has a `shot_elements` relationship.
   - What's unclear: Whether future phases will need shot_elements in the list response.
   - Recommendation: Do NOT add shot_elements to the response now. Keep ShotResponse as-is. If needed later, add `selectinload(Shot.shot_elements)` and extend the response schema in a future phase.

2. **scene_item_id filter on list endpoint**
   - What we know: CONTEXT.md leaves this to Claude's discretion ("can add if obviously useful").
   - Recommendation: Add an optional `scene_item_id` query parameter to the list endpoint. It is obviously useful for the Phase 20 frontend (SHOT-03: shots grouped by scene). Costs one `if` statement and simplifies the frontend.

## Sources

### Primary (HIGH confidence)
- `backend/app/api/endpoints/breakdown.py` -- full CRUD pattern template (lines 46-206)
- `backend/app/api/endpoints/list_items.py` -- reorder pattern (lines 171-188)
- `backend/app/models/database.py` -- Shot model (lines 542-559), ShotElement (lines 562-573)
- `backend/app/models/schemas.py` -- ShotCreate/ShotUpdate/ShotResponse (lines 731-776), ReorderItem/ReorderRequest (lines 415-421)
- `backend/app/tests/test_breakdown_api.py` -- complete test pattern for CRUD endpoints
- `backend/app/tests/conftest.py` -- test fixtures (SQLite engine, TestClient, mock_auth_headers)
- `backend/app/main.py` -- router registration pattern (lines 80-97)
- `backend/app/api/dependencies.py` -- get_current_user dependency

### Secondary (MEDIUM confidence)
- None needed -- all patterns verified from codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies; all existing
- Architecture: HIGH -- direct copy of established patterns (breakdown.py, list_items.py)
- Pitfalls: HIGH -- identified from actual codebase patterns and known SQLite/PostgreSQL differences

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- backend patterns unchanged)
