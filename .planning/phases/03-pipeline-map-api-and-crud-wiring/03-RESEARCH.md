# Phase 3: Pipeline Map API and CRUD Wiring - Research

**Researched:** 2026-03-11
**Domain:** FastAPI endpoint + BackgroundTasks integration for pipeline re-composition on agent CRUD
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 (trigger side) | AI analyzes all agents and maps each to relevant pipeline steps when an agent is created, edited, or deleted | BackgroundTasks wiring in create/update/delete endpoints calls `compose_pipeline()` with fresh `SessionLocal()` session |
| COMP-03 (CRUD gate) | Re-composition only triggers when semantic fields change (system prompt, type), not cosmetic fields (name, icon, color) | `is_semantic_change()` helper already built in Phase 2; wire into update endpoint to gate background task dispatch |
| COMP-04 | GET endpoint exposes current pipeline mapping for frontend consumption | New `GET /api/agents/pipeline-map` route returning `PipelineMapResponse` schema with ORM-to-Pydantic conversion |
</phase_requirements>

---

## Summary

Phase 3 connects the Phase 2 pipeline composer service to the existing agent CRUD endpoints and exposes a new read-only GET endpoint. There are exactly four integration points: (1) a new GET endpoint in `agents.py`, (2) a background re-composition trigger on agent creation, (3) a semantic-gated background trigger on agent update, and (4) a cascade-aware background trigger on agent deletion.

The entire phase modifies one existing file (`backend/app/api/endpoints/agents.py`) and creates one new test file. No new dependencies are needed. All building blocks are already implemented: `pipeline_composer.compose_pipeline()` (Phase 2), `pipeline_composer.is_semantic_change()` (Phase 2), `AgentPipelineMap` ORM model with cascade delete (Phase 1), and `PipelineMapResponse`/`PipelineMapEntry` Pydantic schemas (Phase 1).

The critical implementation detail is database session management in BackgroundTasks. The request session from `get_db()` closes after the response is sent, so background tasks must create their own session via `SessionLocal()`. The project already demonstrates both patterns: `upload_book` (passes request `db` -- fragile), and `resume_book`/`retry_book` (pass string IDs, create `SessionLocal()` inside the task -- correct). Phase 3 must follow the `resume_book` pattern.

**Primary recommendation:** Add `BackgroundTasks` to create/update/delete endpoint signatures, define a standalone async helper `_recompose_pipeline_background(owner_id_str: str)` that creates its own `SessionLocal()`, and call `background_tasks.add_task()` conditionally based on `is_semantic_change()` for updates.

---

## Standard Stack

### Core (all already installed -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI `BackgroundTasks` | 0.109+ | Non-blocking re-composition after CRUD response | Already used in `books.py` for book processing |
| SQLAlchemy ORM | 2.0.27 | Query `AgentPipelineMap` rows for GET endpoint | Existing ORM layer |
| Pydantic v2 | >=2.10 | `PipelineMapResponse` schema for GET response | Phase 1 already defined the schemas |
| `pipeline_composer` service | Phase 2 | `compose_pipeline()` and `is_semantic_change()` | Phase 2 singleton service, ready to use |

### Supporting (Already in Project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `SessionLocal` from `db.py` | N/A | Create fresh DB session inside background task | Every background task that touches the DB |
| `get_current_user` dependency | N/A | Extract `owner_id` from auth | Every endpoint |

**Installation:**
```bash
# No new dependencies required -- everything is already in the project
```

---

## Architecture Patterns

### Recommended Changes

```
backend/app/api/endpoints/
    agents.py              # MODIFY: add GET /pipeline-map, wire BackgroundTasks into create/update/delete
backend/app/tests/
    test_pipeline_api.py   # CREATE: COMP-01/COMP-03/COMP-04 integration tests
```

### Pattern 1: GET Endpoint for Pipeline Map (COMP-04)

**What:** New route `GET /api/agents/pipeline-map` that queries all `AgentPipelineMap` rows for the authenticated user and returns them wrapped in `PipelineMapResponse`.

**When to use:** Frontend needs current pipeline mappings for the Phase 7 tree view, and the generation layer needs them for Phase 5 review middleware.

**Example:**
```python
# Source: Existing patterns in agents.py + Phase 1 PipelineMapResponse schema
from ...models.database import AgentPipelineMap
from ...models.schemas import PipelineMapEntry, PipelineMapResponse

@router.get("/pipeline-map")
async def get_pipeline_map(
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current pipeline mapping for the authenticated user."""
    maps = (
        db.query(AgentPipelineMap)
        .filter(AgentPipelineMap.owner_id == current_user.id)
        .all()
    )
    entries = [PipelineMapEntry.model_validate(m) for m in maps]
    return PipelineMapResponse(
        owner_id=current_user.id,
        entries=entries,
        total_mappings=len(entries),
    )
```

**Critical:** This endpoint MUST be registered BEFORE the `GET /{agent_id}` route (if one exists) to avoid FastAPI interpreting `"pipeline-map"` as an `{agent_id}` path parameter. In the current `agents.py`, the existing routes are `GET /`, `POST /`, `GET /tags`, `PATCH /{agent_id}`, `DELETE /{agent_id}`, etc. The `GET /pipeline-map` should be placed after `GET /tags` and before `PATCH /{agent_id}` to avoid routing conflicts.

### Pattern 2: Background Re-composition Helper

**What:** A standalone async function that creates its own DB session and calls `compose_pipeline()`. This function is the target for `background_tasks.add_task()`.

**When to use:** Called from create, update (when semantic), and delete endpoints.

**Example:**
```python
# Source: resume_book pattern in books.py (creates own SessionLocal)
from ...db import SessionLocal
from ...services.pipeline_composer import pipeline_composer

async def _recompose_pipeline_background(owner_id_str: str):
    """Background task: re-compose pipeline mappings for an owner.

    Creates its own DB session (the request session closes after response).
    Follows the resume_book/retry_book pattern from books.py.
    """
    db = SessionLocal()
    try:
        await pipeline_composer.compose_pipeline(owner_id_str, db)
    except Exception as e:
        logger.error("Background pipeline recomposition failed for owner %s: %s", owner_id_str, e)
    finally:
        db.close()
```

**Key design decision:** Pass `owner_id` as a string (not UUID object), matching the `resume_book` pattern. The `compose_pipeline()` function already handles string-to-UUID conversion internally (Phase 2 used string UUIDs throughout for SQLite compatibility).

### Pattern 3: Semantic Gate on Update (COMP-03 trigger side)

**What:** Before dispatching a background re-composition on agent update, check if any semantic fields changed using `is_semantic_change()`.

**When to use:** In the `PATCH /{agent_id}` endpoint, after applying the update but before returning.

**Example:**
```python
from fastapi import BackgroundTasks
from ...services.pipeline_composer import pipeline_composer

@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    agent_data: schemas.AgentUpdate,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id, Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)

    # Only trigger re-composition if semantic fields changed
    if pipeline_composer.is_semantic_change(update_data):
        background_tasks.add_task(
            _recompose_pipeline_background, str(current_user.id)
        )

    return agent
```

### Pattern 4: Create Endpoint Wiring (COMP-01 trigger side)

**What:** Agent creation always triggers re-composition (a new agent always has semantic fields).

**Example:**
```python
@router.post("/")
async def create_agent(
    agent_data: schemas.AgentCreate,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ... existing create logic ...
    db.commit()
    db.refresh(agent)

    # Always trigger re-composition on new agent
    background_tasks.add_task(
        _recompose_pipeline_background, str(current_user.id)
    )

    return { ... }
```

### Pattern 5: Delete Endpoint Wiring (cascade + re-composition)

**What:** Agent deletion cascades to remove `agent_pipeline_maps` rows (via `ON DELETE CASCADE` in SQL + `cascade="all, delete-orphan"` in ORM). After the cascade, trigger re-composition of remaining agents.

**Example:**
```python
@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(
        Agent.id == agent_id, Agent.owner_id == current_user.id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(agent)
    db.commit()
    # Cascade already removed this agent's pipeline_maps rows.
    # Re-compose with remaining agents to get a fresh mapping.
    background_tasks.add_task(
        _recompose_pipeline_background, str(current_user.id)
    )

    return {"message": "Agent deleted"}
```

### Anti-Patterns to Avoid

- **Passing the request `db` session to `background_tasks.add_task()`:** The `get_db()` generator closes the session after the response. The background task will get a `DetachedInstanceError` or `This session is closed`. Always create a fresh `SessionLocal()` inside the background task. (The `upload_book` endpoint in `books.py` does this incorrectly; `resume_book`/`retry_book` do it correctly.)
- **Importing `get_db` inside the background task:** `get_db()` is a generator dependency designed for FastAPI's DI. Use `SessionLocal()` directly for standalone code.
- **Blocking the response to wait for re-composition:** The entire point of `BackgroundTasks` is that the HTTP response returns immediately. Never `await compose_pipeline()` in the request handler.
- **Triggering re-composition on cosmetic-only updates:** Always gate with `is_semantic_change()` first.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic change detection | Custom field diffing logic | `pipeline_composer.is_semantic_change(update_data)` | Already built and tested in Phase 2 with COMP-03 test coverage |
| Pipeline composition | Custom mapping logic in the endpoint | `pipeline_composer.compose_pipeline(owner_id, db)` | Complete AI orchestration service from Phase 2 |
| ORM-to-Pydantic conversion | Manual dict construction | `PipelineMapEntry.model_validate(orm_instance)` | Pydantic v2 `from_attributes=True` handles it automatically |
| Background session management | Passing request session | `SessionLocal()` with try/finally/close | Proven pattern from `resume_book`/`retry_book` in `book_processing_service.py` |
| Cascade delete of pipeline maps | Manual `DELETE FROM agent_pipeline_maps WHERE agent_id = ...` | SQL `ON DELETE CASCADE` + ORM `cascade="all, delete-orphan"` | Already configured in Phase 1 migration + model |

**Key insight:** Phase 3 is pure integration/wiring. Every building block exists. The risk is not in the logic but in the session management and route ordering.

---

## Common Pitfalls

### Pitfall 1: Background Task Gets Closed Session

**What goes wrong:** `compose_pipeline()` is called in a BackgroundTask using the request `db` session. The session is already closed because FastAPI's `get_db()` generator ran its `finally: db.close()` after sending the response.
**Why it happens:** BackgroundTasks execute after the response is sent, but `Depends(get_db)` sessions are closed in the response lifecycle.
**How to avoid:** Create a fresh `SessionLocal()` inside the background task function. Pass only primitive values (string owner_id) to the background task, not ORM objects or sessions.
**Warning signs:** `DetachedInstanceError`, `InvalidRequestError: This session is closed`, `StatementError: (sqlalchemy.exc.ResourceClosedError)`.

### Pitfall 2: Route Ordering Conflict

**What goes wrong:** `GET /api/agents/pipeline-map` is registered after `GET /api/agents/{agent_id}` or `PATCH /api/agents/{agent_id}`. FastAPI tries to parse `"pipeline-map"` as a UUID path parameter, returning 422 Unprocessable Entity.
**Why it happens:** FastAPI routes are matched in registration order. Path parameters are greedy.
**How to avoid:** Register `GET /pipeline-map` before any `{agent_id}` routes in the router. In the current file, place it after `GET /tags` and before `PATCH /{agent_id}`.
**Warning signs:** 422 errors when calling `GET /api/agents/pipeline-map`, error message about UUID validation.

### Pitfall 3: AgentUpdate Schema Missing Semantic Fields

**What goes wrong:** The `AgentUpdate` Pydantic schema does NOT include `system_prompt_template` or `agent_type`. So `is_semantic_change()` will only ever match on `description` for update operations, even though `system_prompt_template` and `agent_type` are semantic fields.
**Why it happens:** The original `AgentUpdate` was designed before pipeline composition existed.
**How to avoid:** Expand `AgentUpdate` to include `system_prompt_template: Optional[str] = Field(None, min_length=50)` and `agent_type: Optional[AgentType] = None`. This makes all three semantic fields editable and detectable by `is_semantic_change()`.
**Warning signs:** Editing `system_prompt_template` via the API returns 422 (field not allowed) or silently ignores the field.

### Pitfall 4: String vs UUID Type Mismatch in GET Query

**What goes wrong:** `current_user.id` is a `UUID` object, but `AgentPipelineMap.owner_id` stores string UUIDs in the SQLite test environment (due to the Phase 2 decision to use `str(owner_id)` for cross-DB compatibility). The query `AgentPipelineMap.owner_id == current_user.id` may return zero results in tests.
**Why it happens:** Phase 2 decided to store `owner_id` as a string in `compose_pipeline()` for SQLite compatibility. But the GET endpoint receives a UUID object from `get_current_user()`.
**How to avoid:** In the GET query, cast to string: `.filter(AgentPipelineMap.owner_id == str(current_user.id))`. Or better: use a consistent approach. Since PostgreSQL auto-casts both ways, the string approach only matters for SQLite tests. In the test, ensure the mock user ID matches what `compose_pipeline` stored.
**Warning signs:** GET endpoint returns empty `entries: []` despite valid pipeline maps in the database.

### Pitfall 5: Background Task Exception Swallowed Silently

**What goes wrong:** If `compose_pipeline()` raises an exception in the background task, it's swallowed silently because there's no active request context to return an error response.
**Why it happens:** Background tasks run after the response is sent. Unhandled exceptions are logged by the ASGI server but not surfaced to the client.
**How to avoid:** Wrap the background task body in try/except with explicit logging. The existing `book_processing_service` handles this well.
**Warning signs:** Pipeline maps don't update after agent CRUD, but no error is visible in the API response.

---

## Code Examples

Verified patterns from the existing codebase:

### BackgroundTasks with Fresh Session (from book_processing_service.py)
```python
# Source: backend/app/services/book_processing_service.py lines 289-300
async def resume_book(self, book_id: str, owner_id: str) -> None:
    """Resume processing a paused book from its last checkpoint."""
    db = SessionLocal()
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        # ... processing logic ...
    finally:
        db.close()  # Always close, even on exception
```

### BackgroundTasks Endpoint Parameter (from books.py)
```python
# Source: backend/app/api/endpoints/books.py lines 140-163
async def resume_book(
    book_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ... validation logic ...
    # Pass IDs only -- the background task creates its own DB session
    background_tasks.add_task(
        book_processing_service.resume_book,
        str(book_id),
        str(current_user.id),
    )
    return {"message": "Resuming..."}
```

### Agent Query Pattern (from agents.py)
```python
# Source: backend/app/api/endpoints/agents.py lines 100-104
agent = (
    db.query(Agent)
    .filter(Agent.id == agent_id, Agent.owner_id == current_user.id)
    .first()
)
```

### ORM-to-Pydantic Conversion (from test_pipeline_map_schema.py)
```python
# Source: backend/app/tests/test_pipeline_map_schema.py lines 47-48
entry = PipelineMapEntry.model_validate(mapping)
assert str(entry.id) == str(mapping.id)
```

### compose_pipeline() Signature (from pipeline_composer.py)
```python
# Source: backend/app/services/pipeline_composer.py lines 77-78
async def compose_pipeline(
    self, owner_id: UUID, db: Session
) -> List[AgentPipelineMap]:
```

### is_semantic_change() Usage (from test_pipeline_composer.py)
```python
# Source: backend/app/tests/test_pipeline_composer.py lines 276-291
composer = PipelineComposer()
assert composer.is_semantic_change({"name": "New Name"}) is False
assert composer.is_semantic_change({"color": "#ff0000"}) is False
assert composer.is_semantic_change({"description": "new desc"}) is True
assert composer.is_semantic_change({"system_prompt_template": "new prompt"}) is True
assert composer.is_semantic_change({"name": "X", "description": "Y"}) is True
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `upload_book` passes request `db` to background task | `resume_book`/`retry_book` pass string IDs, create `SessionLocal()` inside task | Later `books.py` endpoints fixed the pattern | Phase 3 MUST follow the newer (correct) pattern |
| `AgentUpdate` has no semantic fields (`system_prompt_template`, `agent_type`) | Phase 3 should expand `AgentUpdate` | This phase | Without expansion, `is_semantic_change()` can only detect `description` changes via PATCH |

**Deprecated/outdated:**
- The `upload_book` pattern of passing request `db` to `background_tasks.add_task()` is fragile and should not be replicated. Use the `resume_book` pattern instead.

---

## Open Questions

1. **Should `AgentUpdate` be expanded in this phase or treated as a separate concern?**
   - What we know: `AgentUpdate` currently lacks `system_prompt_template` and `agent_type`. Without them, PATCH cannot modify these fields, so `is_semantic_change()` will only match on `description`.
   - What's unclear: Is expanding `AgentUpdate` in scope for this phase, or is it a separate schema concern?
   - Recommendation: Expand `AgentUpdate` in this phase. The Phase 3 success criteria explicitly state "Editing an agent's `system_prompt_template` triggers re-composition" -- this is impossible without adding the field to `AgentUpdate`. This is a necessary prerequisite, not scope creep.

2. **Should `seed-defaults` also trigger re-composition?**
   - What we know: The `POST /seed-defaults` endpoint creates default agents. These are `is_default=True` agents.
   - What's unclear: Are default agents included in pipeline composition? The composer queries `Agent.is_active == True` but does not filter on `is_default`.
   - Recommendation: Leave `seed-defaults` unchanged for now. Default agents would be included in composition (they match `is_active == True` and the owner query). If this becomes an issue, it's a Phase 8 concern (token budget). Not blocking for Phase 3.

3. **How to handle concurrent background re-compositions?**
   - What we know: If a user rapidly creates multiple agents, multiple `compose_pipeline` calls could overlap. The full-replace write pattern (delete all + insert) makes this safe from a data perspective (last write wins) but could waste AI calls.
   - What's unclear: Should there be debouncing or deduplication?
   - Recommendation: No debouncing for v1. The hash-based cache in `compose_pipeline` already prevents redundant AI calls if the agent set hasn't changed between calls. If two calls run with different agent sets, both AI calls are necessary. Cost is minimal (one AI call per unique agent state).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 (with pytest-asyncio for async tests) |
| Config file | None -- pytest invoked directly from `backend/` |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_api.py -x` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-04 | GET /api/agents/pipeline-map returns PipelineMapResponse with entries | integration (TestClient) | `pytest app/tests/test_pipeline_api.py::test_get_pipeline_map_returns_entries -x` | Wave 0 |
| COMP-04 | GET /api/agents/pipeline-map returns empty entries for user with no mappings | integration (TestClient) | `pytest app/tests/test_pipeline_api.py::test_get_pipeline_map_empty -x` | Wave 0 |
| COMP-01 | Creating an agent triggers background re-composition | unit (mock background_tasks) | `pytest app/tests/test_pipeline_api.py::test_create_agent_triggers_recomposition -x` | Wave 0 |
| COMP-03 | Editing agent system_prompt_template triggers re-composition | unit (mock background_tasks) | `pytest app/tests/test_pipeline_api.py::test_update_semantic_field_triggers_recomposition -x` | Wave 0 |
| COMP-03 | Editing only agent name does NOT trigger re-composition | unit (mock background_tasks) | `pytest app/tests/test_pipeline_api.py::test_update_cosmetic_field_no_recomposition -x` | Wave 0 |
| COMP-01 | Deleting an agent removes its pipeline_maps via cascade and triggers re-composition | integration (TestClient) | `pytest app/tests/test_pipeline_api.py::test_delete_agent_cascades_and_recomposes -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_api.py -x`
- **Per wave merge:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/app/tests/test_pipeline_api.py` -- covers all COMP-01 (trigger side), COMP-03 (CRUD gate), COMP-04 tests above
- [ ] Test approach: Use `TestClient` from conftest for integration tests; mock `pipeline_composer.compose_pipeline` to avoid live AI calls; verify `background_tasks.add_task` was called (or not called) with correct arguments

### Testing Strategy Notes

**Verifying BackgroundTasks dispatch:** FastAPI's `TestClient` runs synchronously, so background tasks execute inline during tests. This means:
1. Integration tests with `TestClient` will actually run the background task before returning
2. To verify that `background_tasks.add_task` was called (vs. not called for cosmetic updates), mock the `_recompose_pipeline_background` function and check `mock.call_count`
3. For cascade delete verification, insert `AgentPipelineMap` rows for an agent, delete the agent via API, then query to confirm the pipeline map rows are gone

**String UUID consistency in tests:** Phase 2 established that `compose_pipeline` stores `owner_id` as a string. Tests must ensure the mock user ID (from `get_current_user`) and the stored pipeline map `owner_id` are compared consistently. The conftest `client` fixture already overrides `get_db` but not `get_current_user`. Tests may need to override `get_current_user` to return a user with a known string-format ID.

---

## Sources

### Primary (HIGH confidence)

- Direct file read: `backend/app/api/endpoints/agents.py` -- current CRUD endpoints, route structure, response patterns (lines 1-223)
- Direct file read: `backend/app/services/pipeline_composer.py` -- `compose_pipeline()` signature, `is_semantic_change()`, `SEMANTIC_FIELDS` (lines 1-341)
- Direct file read: `backend/app/models/database.py` -- `AgentPipelineMap` model with cascade, `Agent` model with `pipeline_maps` relationship (lines 361-455)
- Direct file read: `backend/app/models/schemas.py` -- `AgentUpdate` (missing `system_prompt_template`/`agent_type`), `PipelineMapEntry`, `PipelineMapResponse` (lines 202-633)
- Direct file read: `backend/app/db.py` -- `SessionLocal` factory for fresh sessions (lines 1-28)
- Direct file read: `backend/app/api/endpoints/books.py` -- BackgroundTasks patterns: `upload_book` (passes db), `resume_book`/`retry_book` (creates own session) (lines 44-191)
- Direct file read: `backend/app/services/book_processing_service.py` -- `SessionLocal()` usage in background tasks (lines 11, 289-318)
- Direct file read: `backend/app/tests/conftest.py` -- test infrastructure, fixtures, SQLite patching (lines 1-133)
- Direct file read: `backend/app/tests/test_pipeline_composer.py` -- Phase 2 tests confirming `is_semantic_change()` behavior (lines 1-323)
- Phase 1 research and summaries: migration patterns, ORM patterns, Pydantic patterns
- Phase 2 research and summaries: composer service design, cache strategy, session management warnings

### Secondary (MEDIUM confidence)

- [FastAPI BackgroundTasks documentation](https://fastapi.tiangolo.com/tutorial/background-tasks/) -- confirms background tasks run after response, session lifetime implications
- [FastAPI GitHub discussion #8502](https://github.com/fastapi/fastapi/discussions/8502) -- accessing dependencies in background tasks, session management best practices

### Tertiary (LOW confidence)

None -- all claims verified from codebase files and official FastAPI documentation.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH -- no new dependencies, all patterns verified in existing codebase
- Architecture: HIGH -- all integration points read directly from source code; both correct and incorrect BackgroundTasks patterns identified
- Pitfalls: HIGH -- session lifetime issue verified via two contrasting patterns in the same codebase (`upload_book` vs `resume_book`); route ordering is standard FastAPI knowledge; AgentUpdate gap confirmed by reading schema definition
- Testing: HIGH -- conftest fixtures, TestClient patterns, and mock strategies all verified from existing test files

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependencies to drift; all findings from local codebase)
