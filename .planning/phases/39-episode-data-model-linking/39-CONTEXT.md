# Phase 39: Episode Data Model & Linking - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds episode support to the backend: a nullable `show_id` FK and `episode_number` on the projects table, a POST endpoint to create episodes under a show, and full backward compatibility for standalone projects. No frontend changes — that's Phase 40.

</domain>

<decisions>
## Implementation Decisions

### Database Schema
- Add `show_id` (nullable FK to shows.id, CASCADE DELETE) to projects table
- Add `episode_number` (nullable Integer) to projects table
- Both columns NULL for standalone projects (zero migration of existing data)
- Idempotent delta migration: `008_episode_columns.sql`

### API Endpoints
- `POST /api/shows/{show_id}/episodes` — creates a new project linked to a show
  - Body: `{ title, episode_number, framework }` (framework optional, defaults to THREE_ACT)
  - Returns: standard ProjectResponse (same schema, show_id and episode_number populated)
- Episodes inherit the full project pipeline — no special-casing in existing endpoints
- Existing project endpoints (GET, PUT, DELETE on /api/projects) work unchanged for episodes

### Data Model
- Episode IS a Project: same ORM model, same schema, same pipeline
- ProjectCreate schema: add optional `show_id` and `episode_number` fields
- ProjectResponse schema: add `show_id` and `episode_number` fields (nullable)
- No new ORM model needed — extend existing Project model

### Backward Compatibility
- All existing project tests pass unchanged
- Standalone projects (show_id=NULL) are unaffected
- No breaking changes to any existing endpoint

### Tests
- Test POST /api/shows/{show_id}/episodes creates project with show_id set
- Test episode has full pipeline (sections created by framework)
- Test standalone projects still work (no regressions)
- Test 404 when show not found or not owned by user

### Claude's Discretion
- Episode number auto-increment logic: check max episode_number for show, suggest next
- Error message wording follows existing project error patterns

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/database.py` — Project model to extend with show_id + episode_number
- `backend/app/models/schemas.py` — ProjectCreate/ProjectResponse to extend
- `backend/app/api/endpoints/projects.py` — existing project CRUD to leave unchanged
- `backend/app/api/endpoints/shows.py` — add episodes sub-router here
- `backend/migrations/delta/007_bible_columns.sql` — pattern for idempotent migrations

### Established Patterns
- SQLAlchemy FK: `Column(Integer, ForeignKey("shows.id", ondelete="CASCADE"), nullable=True)`
- Pydantic v2 optional fields: `show_id: Optional[int] = None`
- Auth dependency: `current_user: User = Depends(get_current_user)`
- 404 pattern: `raise HTTPException(status_code=404, detail="Show not found")`

### Integration Points
- `backend/app/api/router.py` or `main.py` — shows router already registered
- `backend/app/models/database.py` — Project model
- `backend/app/models/schemas.py` — ProjectCreate, ProjectResponse

</code_context>

<specifics>
## Specific Ideas

- Episode creation should auto-calculate next episode_number (max + 1) if not provided
- The episode creation endpoint lives under /api/shows/{show_id}/episodes (RESTful nesting)

</specifics>

<deferred>
## Deferred Ideas

- Episode reordering — Phase 40+
- Episode status (draft/published) — not in requirements
- Season linking — not in current scope

</deferred>
