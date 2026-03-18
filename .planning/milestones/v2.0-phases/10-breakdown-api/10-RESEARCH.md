# Phase 10: Breakdown API - Research

**Researched:** 2026-03-13
**Domain:** FastAPI REST API router, CRUD endpoints, SQLAlchemy queries, Pydantic response serialization for script breakdown elements
**Confidence:** HIGH

## Summary

Phase 10 creates the complete REST API layer for the v2.0 Script Breakdown feature. The data foundation (Phase 9) is complete -- all three tables (`breakdown_elements`, `element_scene_links`, `breakdown_runs`), ORM models, Pydantic schemas, and the `breakdown_stale` column on `projects` are in place and tested. This phase builds the `breakdown.py` router with 7 endpoint groups mapped to requirements API-01 through API-07, mounts it in `main.py`, and provides a comprehensive test suite.

The codebase has strong established patterns for every operation needed: project ownership verification (`list_items.py` helper pattern), CRUD with response_model serialization (`agents.py`, `list_items.py`), soft-delete (`is_deleted` flag pattern from snippets), unique constraint conflict handling (409 ConflictException from `exceptions.py`), and query parameter filtering. All Pydantic schemas needed for request/response were already created in Phase 9 (`BreakdownElementCreate`, `BreakdownElementUpdate`, `BreakdownElementResponse`, `BreakdownRunResponse`, `BreakdownSummaryResponse`, `SceneLinkCreate`). The extraction trigger endpoint (API-01) is stubbed -- it creates a `BreakdownRun` record with `status='pending'` and returns it without calling AI (the actual extraction service is Phase 11).

**Primary recommendation:** Follow the `list_items.py` ownership helper pattern (`_verify_project_ownership`) for all project-scoped endpoints, the `agents.py` CRUD pattern for element operations, and the `exceptions.py` hierarchy for error responses. Two plans: Plan 1 builds the router with element CRUD + main.py mount; Plan 2 adds scene link endpoints, summary endpoint, extraction stub, and the full test suite.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| API-01 | `POST /api/breakdown/extract/{project_id}` -- trigger AI extraction, return run result | Extraction logic stubbed (Phase 11); endpoint creates BreakdownRun with status='pending', returns BreakdownRunResponse. Pattern: `wizards.py` run creation |
| API-02 | `GET /api/breakdown/elements/{project_id}` -- list elements filtered by category, excluding soft-deleted by default | Query filter pattern from `list_items.py`; `?category=prop&include_deleted=false` query params; returns `List[BreakdownElementResponse]` |
| API-03 | `PUT /api/breakdown/element/{element_id}` -- update element, sets `user_modified=true` | Partial update pattern from `agents.py` PATCH; `model_dump(exclude_unset=True)` + setattr loop; auto-sets `user_modified=True` |
| API-04 | `POST /api/breakdown/elements/{project_id}` -- create element manually with `source='user'` | Create pattern from `list_items.py` POST; sets `source='user'`; must handle unique constraint conflict (check-and-restore soft-deleted) |
| API-05 | `DELETE /api/breakdown/element/{element_id}` -- soft-delete element | Sets `is_deleted=True` rather than DB delete; returns 200 with success message (matching project delete pattern) |
| API-06 | `POST/DELETE /api/breakdown/element/{element_id}/scenes` -- add/remove scene links | Junction table CRUD pattern from `agents.py` book linking; POST creates ElementSceneLink; DELETE removes by element_id+scene_item_id |
| API-07 | `GET /api/breakdown/summary/{project_id}` -- breakdown summary with staleness, category counts, last run info | Aggregation query; reads `project.breakdown_stale`, counts elements by category, finds latest BreakdownRun; returns `BreakdownSummaryResponse` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.110+ | API router, path/query params, dependency injection, response_model | Already the backend framework; all 16 existing routers use it |
| SQLAlchemy | 2.0.27 | ORM queries, filtering, aggregation | Already in use; all DB access goes through SQLAlchemy |
| Pydantic v2 | >=2.10 | Request body validation, response serialization | Already in use; schemas created in Phase 9 |
| pytest | 8.0.2 | API integration tests with TestClient | Already in use; 14 existing test files |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI TestClient | (via fastapi) | HTTP-level endpoint testing | All API tests use `client` fixture from conftest.py |
| sqlalchemy.func | (via sqlalchemy) | `func.count()` for category aggregation in summary endpoint | Summary query |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline query logic in endpoints | Dedicated service layer | YAGNI for CRUD; service layer needed for Phase 11 extraction but not for basic CRUD endpoints |
| `response_model` on every endpoint | Manual dict serialization | Some existing endpoints (agents.py) use manual dicts; but breakdown schemas exist and `response_model` is cleaner. Use `response_model` consistently |
| Separate `breakdown_schemas.py` | Schemas in existing `schemas.py` | Phase 9 already put all schemas in `schemas.py`; follow that convention |

**Installation:**
No new packages needed. All dependencies already exist in `backend/requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/endpoints/
│   └── breakdown.py          # NEW - all breakdown API endpoints
├── models/
│   ├── database.py            # EXISTS - BreakdownElement, ElementSceneLink, BreakdownRun (Phase 9)
│   └── schemas.py             # EXISTS - all breakdown Pydantic schemas (Phase 9)
├── main.py                    # MODIFY - add 2 lines to mount breakdown router
└── tests/
    └── test_breakdown_api.py  # NEW - API integration tests
```

### Pattern 1: Project Ownership Verification Helper
**What:** A reusable helper function that verifies the current user owns the project, returning the project or raising 404
**When to use:** Every endpoint that takes `project_id` as a path parameter
**Example:**
```python
# Source: backend/app/api/endpoints/list_items.py (adapted)
def _verify_project_ownership(db: Session, project_id: UUID, user_id: UUID) -> database.Project:
    """Verify user owns the project. Returns project or raises 404."""
    project = db.query(database.Project).filter(
        database.Project.id == project_id,
        database.Project.owner_id == user_id
    ).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
```

### Pattern 2: Element Ownership Verification Helper
**What:** A helper that verifies the element exists and the user owns the parent project
**When to use:** Every endpoint that takes `element_id` as a path parameter (PUT, DELETE, scene link CRUD)
**Example:**
```python
# Source: backend/app/api/endpoints/list_items.py (_verify_item_ownership pattern)
def _verify_element_ownership(db: Session, element_id: UUID, user_id: UUID) -> database.BreakdownElement:
    """Verify user owns the project containing this element. Returns element or raises 404."""
    element = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.id == element_id
    ).first()
    if not element:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Element not found")

    _verify_project_ownership(db, element.project_id, user_id)
    return element
```

### Pattern 3: CRUD with response_model Serialization
**What:** Endpoints that use FastAPI's `response_model` parameter for automatic Pydantic serialization of ORM objects
**When to use:** All GET/POST/PUT endpoints that return data
**Example:**
```python
# Source: backend/app/api/endpoints/list_items.py
@router.get("/elements/{project_id}", response_model=List[schemas.BreakdownElementResponse])
async def list_elements(
    project_id: UUID,
    category: Optional[str] = None,
    include_deleted: bool = False,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_project_ownership(db, project_id, current_user.id)

    query = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.project_id == project_id
    )
    if not include_deleted:
        query = query.filter(database.BreakdownElement.is_deleted == False)
    if category:
        query = query.filter(database.BreakdownElement.category == category)

    return query.order_by(database.BreakdownElement.sort_order).all()
```

### Pattern 4: Unique Constraint Conflict with Soft-Delete Restore
**What:** When creating an element that conflicts with the unique constraint `(project_id, category, name)`, check if the existing element is soft-deleted and offer to restore it
**When to use:** POST create element endpoint (API-04)
**Example:**
```python
# Check for existing element (including soft-deleted) before insert
from sqlalchemy.exc import IntegrityError

existing = db.query(database.BreakdownElement).filter(
    database.BreakdownElement.project_id == project_id,
    database.BreakdownElement.category == body.category,
    database.BreakdownElement.name == body.name,
).first()

if existing and existing.is_deleted:
    # Restore soft-deleted element
    existing.is_deleted = False
    existing.description = body.description
    existing.metadata_ = body.metadata
    existing.source = "user"
    existing.user_modified = True
    db.commit()
    db.refresh(existing)
    return existing
elif existing:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Element '{body.name}' already exists in category '{body.category}'"
    )
```

### Pattern 5: Router Mount in main.py
**What:** Import the router module and mount with prefix and tags
**When to use:** Once, when the router is first created
**Example:**
```python
# Source: backend/app/main.py (existing pattern)
from .api.endpoints import breakdown as breakdown_ep
app.include_router(breakdown_ep.router, prefix="/api/breakdown", tags=["breakdown"])
```

### Anti-Patterns to Avoid
- **Creating a service layer for CRUD:** Do NOT create `breakdown_service.py` in this phase. The extraction service belongs to Phase 11. CRUD endpoints are simple enough to have query logic inline (matching `list_items.py` and `agents.py` patterns)
- **Hard-deleting elements:** The DELETE endpoint MUST soft-delete (`is_deleted=True`), never `db.delete()`. This is required by SYNC-01/SYNC-02 (Phase 11) -- re-extraction must not resurrect deleted elements
- **Returning 204 for DELETE:** The existing codebase pattern returns 200 with `{"status": "success", "message": "..."}` for deletes (see `projects.py` line 205, `list_items.py` line 134). Follow this pattern, not 204 No Content
- **Ignoring the metadata alias:** `BreakdownElement.metadata_` maps to DB column `metadata`. The `BreakdownElementResponse` schema handles this with `validation_alias="metadata_"`. Do NOT try to rename the column or use a different attribute name
- **Missing ownership checks:** Every endpoint MUST verify the current user owns the project. Even element-level endpoints must trace back to project ownership. This prevents cross-user data access

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Project ownership verification | Custom per-endpoint auth checks | Shared `_verify_project_ownership` helper (pattern from `list_items.py`) | Consistency, single point of change, tested once |
| Response serialization | Manual dict construction | `response_model=schemas.BreakdownElementResponse` | Pydantic v2 handles ORM-to-JSON including metadata alias |
| Category validation | If/else chains in endpoint | `BreakdownElementCreate.category` regex pattern (`^(character\|location\|prop\|wardrobe\|vehicle)$`) | Schema already validates; endpoint just receives valid data |
| Error responses | Custom error dict construction | `HTTPException` and `exceptions.py` hierarchy (`NotFoundException`, `ConflictException`) | Consistent error format across all endpoints |
| Query parameter parsing | Manual request.query_params | FastAPI query param declaration (`category: Optional[str] = None`) | Type-safe, auto-documented in OpenAPI |

**Key insight:** Phase 9 already created all the schemas. Phase 10 is pure router wiring -- create endpoints that accept those schemas, run SQLAlchemy queries, and return ORM objects that Pydantic serializes. No novel patterns needed.

## Common Pitfalls

### Pitfall 1: Soft-Delete Filter Missing on List Endpoint
**What goes wrong:** `GET /elements/{project_id}` returns soft-deleted elements by default, confusing the frontend
**Why it happens:** Forgetting to add `is_deleted == False` filter, or adding it but not making it the default
**How to avoid:** Default behavior MUST exclude soft-deleted. Use `include_deleted: bool = False` query parameter. Only return soft-deleted when explicitly requested
**Warning signs:** Frontend shows elements the user previously deleted

### Pitfall 2: Unique Constraint IntegrityError on Create
**What goes wrong:** `POST /elements/{project_id}` returns 500 when user tries to create an element with a name that already exists (including soft-deleted names)
**Why it happens:** The `UNIQUE(project_id, category, name)` constraint includes soft-deleted rows. Blindly inserting raises `IntegrityError`
**How to avoid:** Check for existing element FIRST (including soft-deleted). If soft-deleted, restore it instead of creating new. If active, return 409. Never let the IntegrityError propagate as 500
**Warning signs:** 500 errors on element creation when a soft-deleted duplicate exists

### Pitfall 3: Missing user_modified=True on PUT
**What goes wrong:** User edits an element via PUT, but `user_modified` stays `False`. Next AI re-extraction (Phase 11) overwrites the user's edits
**Why it happens:** Forgetting to set `user_modified=True` alongside the field updates
**How to avoid:** PUT handler MUST set `element.user_modified = True` unconditionally. This is a core requirement (API-03)
**Warning signs:** No immediate symptoms -- the bug manifests when Phase 11 extraction runs

### Pitfall 4: Scene Link Duplicate Creates 500
**What goes wrong:** `POST /element/{id}/scenes` with a scene_item_id that already has a link raises `IntegrityError` (500)
**Why it happens:** `UNIQUE(element_id, scene_item_id)` constraint on `element_scene_links` table
**How to avoid:** Check for existing link first. If it exists, return 200 with the existing link (idempotent). Or return 409 with a clear message
**Warning signs:** 500 error when adding a scene link that already exists

### Pitfall 5: Summary Endpoint N+1 Queries
**What goes wrong:** Summary endpoint makes separate queries for each category count, plus a separate query for the latest run, resulting in 7+ queries
**Why it happens:** Naive implementation queries each category individually
**How to avoid:** Use a single aggregation query with `func.count()` grouped by category. Use `db.query(database.BreakdownRun).filter(...).order_by(BreakdownRun.created_at.desc()).first()` for latest run. Total: 3 queries (project, element counts, latest run)
**Warning signs:** Slow response on summary endpoint, excessive DB queries in logs

### Pitfall 6: scene_item_id FK Validation
**What goes wrong:** `POST /element/{id}/scenes` accepts any UUID for `scene_item_id`, even if the ListItem doesn't exist, resulting in FK violation 500
**Why it happens:** Not validating that the scene_item_id references a real ListItem
**How to avoid:** Query `ListItem` by ID before creating the link. Return 404 if not found. This also ensures the link is to an actual scene, not an arbitrary ListItem
**Warning signs:** 500 errors when linking to non-existent scenes

## Code Examples

Verified patterns from the existing codebase:

### Router Structure and Imports
```python
# Source: backend/app/api/endpoints/list_items.py + agents.py (composite pattern)
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ...models import schemas, database
from ..dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
```

### Element CRUD Endpoint (PUT with user_modified)
```python
# Source: adapted from agents.py PATCH pattern
@router.put("/element/{element_id}", response_model=schemas.BreakdownElementResponse)
async def update_element(
    element_id: UUID,
    body: schemas.BreakdownElementUpdate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    element = _verify_element_ownership(db, element_id, current_user.id)

    update_data = body.model_dump(exclude_unset=True)

    # Map 'metadata' field name to 'metadata_' ORM attribute
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")

    for field, value in update_data.items():
        setattr(element, field, value)

    element.user_modified = True  # Always set on user edit (API-03)

    db.commit()
    db.refresh(element)
    return element
```

### Summary Aggregation Query
```python
# Source: adapted from SQLAlchemy func.count pattern
@router.get("/summary/{project_id}", response_model=schemas.BreakdownSummaryResponse)
async def get_summary(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _verify_project_ownership(db, project_id, current_user.id)

    # Category counts (single query with GROUP BY)
    counts = (
        db.query(database.BreakdownElement.category, func.count(database.BreakdownElement.id))
        .filter(
            database.BreakdownElement.project_id == project_id,
            database.BreakdownElement.is_deleted == False,
        )
        .group_by(database.BreakdownElement.category)
        .all()
    )
    counts_by_category = {cat: count for cat, count in counts}
    total_elements = sum(counts_by_category.values())

    # Latest run
    last_run = (
        db.query(database.BreakdownRun)
        .filter(database.BreakdownRun.project_id == project_id)
        .order_by(database.BreakdownRun.created_at.desc())
        .first()
    )

    return schemas.BreakdownSummaryResponse(
        project_id=project_id,
        is_stale=project.breakdown_stale or False,
        total_elements=total_elements,
        counts_by_category=counts_by_category,
        last_run=schemas.BreakdownRunResponse.model_validate(last_run) if last_run else None,
    )
```

### Scene Link Add/Remove Pattern
```python
# Source: adapted from agents.py book link pattern
@router.post("/element/{element_id}/scenes", status_code=status.HTTP_201_CREATED)
async def add_scene_link(
    element_id: UUID,
    body: schemas.SceneLinkCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    element = _verify_element_ownership(db, element_id, current_user.id)

    # Validate scene exists
    scene = db.query(database.ListItem).filter(
        database.ListItem.id == body.scene_item_id
    ).first()
    if not scene:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")

    # Check for existing link (idempotent)
    existing = db.query(database.ElementSceneLink).filter(
        database.ElementSceneLink.element_id == element_id,
        database.ElementSceneLink.scene_item_id == body.scene_item_id,
    ).first()
    if existing:
        return {"message": "Scene link already exists", "id": str(existing.id)}

    link = database.ElementSceneLink(
        element_id=element_id,
        scene_item_id=body.scene_item_id,
        context=body.context,
        source="user",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"message": "Scene linked", "id": str(link.id)}
```

### Extraction Stub (Phase 11 will replace)
```python
# Source: adapted from wizard run creation pattern in wizards.py
@router.post("/extract/{project_id}", response_model=schemas.BreakdownRunResponse)
async def extract_breakdown(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI extraction. Extraction logic stubbed until Phase 11."""
    _verify_project_ownership(db, project_id, current_user.id)

    run = database.BreakdownRun(
        project_id=project_id,
        status="pending",
        config={},
        result_summary={"message": "Extraction not yet implemented"},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
```

### main.py Router Mount
```python
# Source: backend/app/main.py (add alongside existing imports and mounts)
# Import:
from .api.endpoints import breakdown as breakdown_ep

# Mount (add after existing routers):
app.include_router(breakdown_ep.router, prefix="/api/breakdown", tags=["breakdown"])
```

### Test Pattern (API Integration with TestClient)
```python
# Source: backend/app/tests/test_pipeline_api.py (adapted pattern)
import uuid
import pytest
from app.models.database import Project, BreakdownElement, BreakdownRun

MOCK_USER_ID = "12345678-1234-5678-1234-567812345678"


def _make_project(db_session, title="Test Project"):
    """Create and flush a minimal Project, returning it."""
    project = Project(
        id=str(uuid.uuid4()),
        owner_id=MOCK_USER_ID,
        title=title,
    )
    db_session.add(project)
    db_session.flush()
    return project


def _make_element(db_session, project_id, category="prop", name="Test Item"):
    """Create and flush a BreakdownElement."""
    elem = BreakdownElement(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category=category,
        name=name,
        source="ai",
    )
    db_session.add(elem)
    db_session.flush()
    return elem


def test_list_elements(client, db_session, mock_auth_headers):
    project = _make_project(db_session)
    _make_element(db_session, project.id, "prop", "Revolver")
    _make_element(db_session, project.id, "character", "John")
    db_session.commit()

    response = client.get(
        f"/api/breakdown/elements/{project.id}",
        headers=mock_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_list_elements_filter_by_category(client, db_session, mock_auth_headers):
    project = _make_project(db_session)
    _make_element(db_session, project.id, "prop", "Revolver")
    _make_element(db_session, project.id, "character", "John")
    db_session.commit()

    response = client.get(
        f"/api/breakdown/elements/{project.id}?category=prop",
        headers=mock_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "prop"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `.dict()` | Pydantic v2 `.model_dump(exclude_unset=True)` | Pydantic 2.0 (2023) | Use `model_dump` for partial updates, not `dict` |
| FastAPI manual response dicts | `response_model` with `ConfigDict(from_attributes=True)` | Best practice (stable) | Some older endpoints in codebase use manual dicts; new endpoints should use `response_model` |
| Hard deletes | Soft delete with `is_deleted` flag | v2.0 design decision | Enables re-extraction to respect user deletions |

**Deprecated/outdated:**
- `pydantic.BaseModel.dict()` is deprecated in Pydantic v2; use `model_dump()` instead. Some older endpoints still use `.dict()` but new code should use `model_dump()`

## Open Questions

1. **Should the extraction stub return 202 Accepted or 200 OK?**
   - What we know: The stub creates a run with `status='pending'` -- it does not actually perform extraction
   - What's unclear: Whether 202 is more semantically correct for an async-style operation that will be fulfilled later
   - Recommendation: Use 200 OK for now. The stub is synchronous (creates a DB record and returns). Phase 11 may change to 202 if extraction becomes async/background. Matching the existing wizard run pattern (200 with immediate response)

2. **Should DELETE scene link use `/{element_id}/scenes/{scene_item_id}` or accept body?**
   - What we know: The requirement says `POST/DELETE /api/breakdown/element/{element_id}/scenes`
   - What's unclear: Whether the scene_item_id for DELETE comes from the path or request body
   - Recommendation: Use path parameter `DELETE /element/{element_id}/scenes/{scene_item_id}` -- this matches RESTful convention (DELETE with body is technically allowed but unconventional) and matches the `agents.py` book unlink pattern (`DELETE /{agent_id}/books/{book_id}`)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 with FastAPI TestClient |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest app/tests/test_breakdown_api.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-01 | POST /extract/{project_id} creates BreakdownRun with status='pending' | integration | `pytest app/tests/test_breakdown_api.py::test_extract_creates_pending_run -x` | Wave 0 |
| API-01 | POST /extract returns BreakdownRunResponse shape | integration | `pytest app/tests/test_breakdown_api.py::test_extract_response_shape -x` | Wave 0 |
| API-02 | GET /elements/{project_id} returns elements, excludes soft-deleted | integration | `pytest app/tests/test_breakdown_api.py::test_list_elements_excludes_deleted -x` | Wave 0 |
| API-02 | GET /elements with ?category= filters correctly | integration | `pytest app/tests/test_breakdown_api.py::test_list_elements_filter_by_category -x` | Wave 0 |
| API-03 | PUT /element/{id} updates fields and sets user_modified=true | integration | `pytest app/tests/test_breakdown_api.py::test_update_element_sets_user_modified -x` | Wave 0 |
| API-04 | POST /elements/{project_id} creates with source='user' | integration | `pytest app/tests/test_breakdown_api.py::test_create_element_source_user -x` | Wave 0 |
| API-04 | POST /elements with duplicate name returns 409 or restores soft-deleted | integration | `pytest app/tests/test_breakdown_api.py::test_create_element_duplicate_conflict -x` | Wave 0 |
| API-05 | DELETE /element/{id} soft-deletes (is_deleted=True) | integration | `pytest app/tests/test_breakdown_api.py::test_delete_element_soft_deletes -x` | Wave 0 |
| API-06 | POST /element/{id}/scenes creates scene link | integration | `pytest app/tests/test_breakdown_api.py::test_add_scene_link -x` | Wave 0 |
| API-06 | DELETE /element/{id}/scenes/{scene_id} removes link | integration | `pytest app/tests/test_breakdown_api.py::test_remove_scene_link -x` | Wave 0 |
| API-07 | GET /summary/{project_id} returns staleness, counts, last run | integration | `pytest app/tests/test_breakdown_api.py::test_summary_returns_counts -x` | Wave 0 |
| ALL | Unauthorized requests return 401/403 | integration | `pytest app/tests/test_breakdown_api.py::test_no_auth_returns_403 -x` | Wave 0 |
| ALL | Non-existent project returns 404 | integration | `pytest app/tests/test_breakdown_api.py::test_nonexistent_project_404 -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_breakdown_api.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_breakdown_api.py` -- covers API-01 through API-07 (endpoint integration tests using TestClient + mock auth)
- [ ] `backend/app/api/endpoints/breakdown.py` -- the router itself (must exist for tests to import)
- [ ] No new conftest fixtures needed (existing `client`, `db_session`, `mock_auth_headers` fixtures sufficient)
- [ ] No new framework install needed

## Sources

### Primary (HIGH confidence)
- `backend/app/api/endpoints/list_items.py` -- CRUD endpoint pattern with ownership verification helpers
- `backend/app/api/endpoints/agents.py` -- CRUD with junction table link/unlink pattern (book linking), partial update with `model_dump(exclude_unset=True)`
- `backend/app/api/endpoints/projects.py` -- project ownership filter pattern, delete response pattern
- `backend/app/main.py` -- router mounting convention
- `backend/app/models/database.py` -- BreakdownElement, ElementSceneLink, BreakdownRun ORM models (Phase 9)
- `backend/app/models/schemas.py` -- BreakdownElementCreate/Update/Response, BreakdownRunResponse, BreakdownSummaryResponse, SceneLinkCreate (Phase 9)
- `backend/app/exceptions.py` -- NotFoundException, ConflictException, HTTPException hierarchy
- `backend/app/tests/conftest.py` -- test fixtures (client, db_session, mock_auth_headers)
- `backend/app/tests/test_pipeline_api.py` -- API integration test pattern with helper functions
- `backend/app/tests/test_breakdown_models.py` -- Phase 9 model/schema tests (confirms schemas work)
- `.planning/research/ARCHITECTURE.md` -- API endpoint specification, schema design, router mount convention

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` -- API-01 through API-07 requirement definitions
- `.planning/STATE.md` -- v2.0 architectural decisions (breakdown not a phase, check-and-restore for soft-deleted duplicates)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all patterns established in 16 existing routers
- Architecture: HIGH -- all schemas exist from Phase 9, all endpoint patterns have 2+ existing examples in codebase
- Pitfalls: HIGH -- unique constraint + soft-delete interaction documented in Phase 9 research and STATE.md decisions

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable -- no external dependencies to change)
