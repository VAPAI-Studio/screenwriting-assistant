# Phase 19: Shot CRUD API & Core Model - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend API endpoints for Shot CRUD. The `Shot` model, `ShotElement` junction, Pydantic schemas (`ShotCreate`, `ShotUpdate`, `ShotResponse`), and delta migration are already complete from Phase 17. Phase 19 creates `backend/app/api/endpoints/shots.py`, registers it in `main.py` at `/api/shots`, and covers: list, create, get single, update, delete, and reorder. No frontend work.

</domain>

<decisions>
## Implementation Decisions

### GET list format
- Flat list response: `[{shot}, {shot}, ...]` sorted by `scene_item_id` + `sort_order`
- Frontend groups by `scene_item_id` client-side (follows breakdown.py list pattern)
- Shots with `scene_item_id = null` (unattached) are included in the list; `scene_item_id` is null in response

### Reorder endpoint
- `POST /shots/{project_id}/reorder` with body `[{id: uuid, sort_order: int}, ...]`
- Bulk array — client sends new positions for all affected shots; server updates all in one transaction
- Server validates that every shot ID in the array belongs to the project; returns 403 if any foreign shot is included

### shot_number behavior
- User-supplied on create (defaults to 1 if omitted via schema default)
- Server does NOT auto-assign or re-number on create or delete
- Whatever the client sends is stored as-is

### Test coverage
- Happy paths: create (201), list (200), get single (200), update (200), delete (204), reorder (200)
- Auth/ownership errors: 404 for wrong project, 401 for unauthenticated requests
- Mirrors existing `test_api.py` test class pattern

### Claude's Discretion
- URL structure for single-shot endpoints (`/shots/{project_id}/{shot_id}` vs `/shot/{shot_id}`) — follow existing breakdown.py pattern
- Whether to add a `scene_item_id` query param filter to the list endpoint (can add if obviously useful)
- selectinload strategy for related data in responses
- Exact test class name and fixture setup

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing API patterns
- `backend/app/api/endpoints/breakdown.py` — Direct pattern to follow: `_verify_project_ownership()` helper, `selectinload`, response model usage, route naming conventions
- `backend/app/api/endpoints/projects.py` — Secondary pattern reference

### Data model
- `backend/app/models/database.py` lines 542–573 — `Shot`, `ShotElement` models (already complete)
- `backend/app/models/schemas.py` lines 731–776 — `ShotCreate`, `ShotUpdate`, `ShotResponse`, `ShotElementCreate`, `ShotElementResponse` (already complete)

### Router registration
- `backend/app/main.py` lines 81–97 — Where to add `include_router` for shots (follows breakdown pattern at line 97)

### Test patterns
- `backend/app/tests/test_api.py` — Existing test class structure, fixtures, mock-token auth header pattern

### Requirements
- `DATA-04` — Shot CRUD API endpoints (GET list, POST create, GET single, PUT update, DELETE)
- `SHOT-01` — User can create a shot with freeform text fields
- `SHOT-02` — Shots have freeform text fields: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_verify_project_ownership()` in `breakdown.py`: copy this helper into `shots.py` — same project ownership check pattern
- `breakdown.py` list/create/update/delete routes: direct implementation template for shots CRUD
- All Pydantic schemas: `ShotCreate`, `ShotUpdate`, `ShotResponse` already defined in `schemas.py` — no schema work needed

### Established Patterns
- UUID primary keys as strings in DB queries: `filter(Shot.id == str(shot_id))`
- `selectinload` for related collections (e.g., `shot_elements`)
- `status.HTTP_201_CREATED` for POST, `status.HTTP_204_NO_CONTENT` for DELETE
- Bearer mock-token auth in tests: `headers={"Authorization": "Bearer mock-token"}`
- `db.commit(); db.refresh(obj)` pattern after create/update

### Integration Points
- `main.py`: Add `from .api.endpoints import shots as shots_ep` and `app.include_router(shots_ep.router, prefix="/api/shots", tags=["shots"])`
- `database.py`: `Shot` model has `project` relationship via `back_populates="shots"` — Project model already has this wired from Phase 17
- `test_api.py`: Add `TestShotsAPI` class following existing `TestProjectsAPI` / `TestBreakdownAPI` patterns

</code_context>

<specifics>
## Specific Ideas

- No specific references — follow existing breakdown.py pattern closely

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-shot-crud-api-core-model*
*Context gathered: 2026-03-19*
