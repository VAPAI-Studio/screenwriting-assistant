# Phase 6: Wizard Injection - Research

**Researched:** 2026-03-11
**Domain:** Wiring the Phase 5 `AgentReviewMiddleware` into the `wizards.py` generation endpoint and surfacing `agents_consulted` metadata in the response schema
**Confidence:** HIGH

## Summary

Phase 6 is a narrow integration phase. All the hard infrastructure work was completed in Phase 5: the `AgentReviewMiddleware` class with its `review_step_output()` entry point, parallel fan-out, AI merge, and zero-agent pass-through are fully built and tested (10 unit tests, all passing). Phase 6's job is to wire a single function call into `wizards.py`, propagate the metadata to the response, and prove it works end-to-end.

The injection point is clearly identified in `wizards.py` at lines 92-98 of the `run_wizard()` endpoint. After `template_ai_service.wizard_generate()` returns `result` on line 92-97, and before `wizard_run.result = result` on line 98, the middleware call must be inserted. The middleware returns `{"output": ..., "agents_consulted": [...], "review_applied": bool}` -- the `output` replaces `result` and the `agents_consulted` needs to be surfaced in the wizard run response.

The key decision point is how to propagate `agents_consulted` metadata. The current `WizardRun` database model has a `result` column (JSON) and no `agents_consulted` column. The `WizardRunResponse` Pydantic schema mirrors this with `result: Dict`. The cleanest approach is to embed `agents_consulted` inside the existing `result` JSON column (e.g., `result["_meta"]["agents_consulted"]`) rather than adding a new database column. This avoids a migration and keeps the response schema backward-compatible for frontends that don't know about agents.

**Primary recommendation:** Insert a single `review_step_output()` call in `run_wizard()` after `wizard_generate()` returns, replace `result` with the refined output, embed `agents_consulted` in the `result` JSON under a `_meta` key, and add `agents_consulted` as an optional top-level field on `WizardRunResponse` for direct access.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REVW-01 | Agent review middleware injected in `wizards.py` between `wizard_generate()` and `apply_wizard_result_to_db()` | Injection point identified at `wizards.py` lines 92-98. `review_step_output()` is fully implemented in `agent_review_middleware.py` with the exact signature needed. `SessionLocal` import pattern established in `chat.py` and `agents.py`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `agent_review_middleware` | (project module) | `review_step_output()` singleton from Phase 5 | Fully tested, 10 unit tests passing |
| `SessionLocal` | (project module from `db.py`) | Session factory for middleware's parallel tasks | Same pattern used in `chat.py` (line 163, 190) and `agents.py` (line 38) |
| Pydantic v2 | (existing) | `WizardRunResponse` schema update | Already the project's validation layer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging (stdlib) | Python 3.11 | Debug logging for injection path | Follows project convention `logger = logging.getLogger(__name__)` |
| typing (stdlib) | Python 3.11 | `Optional[List[Dict]]` for `agents_consulted` field | Standard type annotations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Embedding `agents_consulted` in `result` JSON | New DB column + migration | DB column is cleaner long-term but requires migration 009, ALTER TABLE, and schema changes. Embedding in JSON avoids all of this for v1. |
| Optional field on `WizardRunResponse` | Separate metadata endpoint | Extra endpoint is over-engineered for this data; the response already returns `result` JSON which naturally carries metadata |

**Installation:**
```bash
# No new dependencies needed -- all building blocks exist in the project
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/endpoints/wizards.py         # MODIFIED: add middleware call + imports
├── models/schemas.py                # MODIFIED: add agents_consulted to WizardRunResponse
├── services/agent_review_middleware.py  # UNCHANGED: Phase 5 output (read-only)
├── db.py                            # UNCHANGED: SessionLocal import source
└── tests/
    ├── test_agent_review_middleware.py  # UNCHANGED: Phase 5 tests
    └── test_wizard_injection.py        # NEW: Phase 6 integration tests
```

### Pattern 1: Single Injection Point
**What:** Insert one function call between `wizard_generate()` return and `wizard_run.result = result` assignment
**When to use:** This is the only pattern needed for REVW-01 injection
**Example:**
```python
# wizards.py run_wizard() -- BEFORE (current state, lines 91-98):
try:
    result = await template_ai_service.wizard_generate(
        wizard_type=request.wizard_type,
        config=config,
        project_context=project_context,
        template_id=template_id
    )
    wizard_run.result = result
    wizard_run.status = "completed"

# wizards.py run_wizard() -- AFTER:
try:
    result = await template_ai_service.wizard_generate(
        wizard_type=request.wizard_type,
        config=config,
        project_context=project_context,
        template_id=template_id
    )

    # Phase 6: Agent review injection (REVW-01)
    review_result = await agent_review_middleware.review_step_output(
        phase=request.phase,
        subsection_key=request.wizard_type,
        raw_output=result,
        owner_id=str(current_user.id),
        session_factory=SessionLocal,
        wizard_type=request.wizard_type,
    )
    result = review_result["output"]
    agents_consulted = review_result["agents_consulted"]

    wizard_run.result = result
    wizard_run.result["_meta"] = {
        "agents_consulted": agents_consulted,
        "review_applied": review_result["review_applied"],
    }
    wizard_run.status = "completed"
```

### Pattern 2: Metadata Propagation via `result` JSON
**What:** Embed `agents_consulted` inside the existing `result` JSON column under a `_meta` key, plus add an optional top-level field on the response schema
**When to use:** When you need to surface metadata without a database migration
**Example:**
```python
# In schemas.py -- WizardRunResponse:
class WizardRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    wizard_type: str
    phase: str
    status: str
    config: Dict = Field(default_factory=dict)
    result: Dict = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    agents_consulted: List[Dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def extract_agents_consulted(self):
        """Extract agents_consulted from result._meta for convenient access."""
        if not self.agents_consulted and self.result:
            meta = self.result.get("_meta", {})
            self.agents_consulted = meta.get("agents_consulted", [])
        return self
```

### Pattern 3: SessionLocal as Session Factory
**What:** Import and pass `SessionLocal` directly as the `session_factory` argument
**When to use:** Established pattern across the codebase
**Example:**
```python
# Source: backend/app/api/endpoints/chat.py line 163
from ...db import SessionLocal

# In run_wizard():
review_result = await agent_review_middleware.review_step_output(
    ...
    session_factory=SessionLocal,
)
```

### Anti-Patterns to Avoid
- **Passing the request `db` session to middleware:** The middleware needs a factory, not a shared session. Passing `db` directly will cause `DetachedInstanceError` in parallel agent reviews. Use `SessionLocal` (the factory callable), not `db` (the instance).
- **Modifying `result` before passing to middleware:** Pass the raw `wizard_generate()` output unchanged. The middleware handles any transformation.
- **Adding a new DB column for `agents_consulted`:** Over-engineering for v1. The `result` JSON column can carry metadata. A dedicated column can be added in v2 if needed.
- **Catching middleware exceptions silently:** If the middleware fails, let it propagate to the existing `except Exception` handler in `run_wizard()`. Don't add a separate try/except that silently falls back -- the existing error handling already sets `wizard_run.status = "failed"`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Agent review pipeline | Custom review loop in `wizards.py` | `agent_review_middleware.review_step_output()` | Phase 5 built and tested this; 393 lines of proven code |
| Session management for parallel tasks | `db` session sharing or manual session creation | `SessionLocal` import from `db.py` | Established pattern; `chat.py` and `agents.py` already use it |
| Zero-agent detection | `if` check in `wizards.py` for whether agents exist | Middleware handles internally (REVW-04) | Pass-through logic is in the middleware; don't duplicate it |
| Metadata serialization | Custom JSON encoding for `agents_consulted` | Embed in `result["_meta"]` + Pydantic `model_validator` | Leverages existing JSON column; no migration needed |

**Key insight:** Phase 6 should add minimal code to `wizards.py`. The middleware encapsulates all complexity. The injection should be ~10 lines of new code in `run_wizard()` plus ~5 lines in the schema.

## Common Pitfalls

### Pitfall 1: Passing `db` Instead of `SessionLocal`
**What goes wrong:** The middleware's parallel agent reviews share one session, causing `DetachedInstanceError`.
**Why it happens:** The `run_wizard` endpoint already has `db: Session = Depends(get_db)` available. It's tempting to pass `db` or a lambda wrapping `db`.
**How to avoid:** Import `SessionLocal` from `db.py` and pass it directly. This is the identical pattern used in `chat.py` line 163: `session_factory=SessionLocal`.
**Warning signs:** Intermittent `DetachedInstanceError` or `MissingGreenlet` errors when agents are mapped.

### Pitfall 2: `_meta` Key Colliding with Wizard Output
**What goes wrong:** If a wizard generates a result that already has a `_meta` key, injecting metadata overwrites it.
**Why it happens:** The wizard result schemas (`{"fields": {...}}`, `{"scenes": [...]}`, `{"screenplays": [...]}`) don't use `_meta`, but future wizard types might.
**How to avoid:** Use `_meta` (underscore prefix) as a convention for system metadata. Check that none of the 3 current wizard result schemas use this key (they don't -- verified in `WIZARD_RESULT_SCHEMAS` in `agent_review_middleware.py`).
**Warning signs:** Missing wizard data after injection.

### Pitfall 3: `subsection_key` Mismatch Between Wizard and Pipeline Map
**What goes wrong:** The middleware queries `AgentPipelineMap` by `(owner_id, phase, subsection_key)`. If the `subsection_key` passed from `wizards.py` doesn't match what the pipeline composer stored, zero agents are found and the middleware passes through.
**Why it happens:** The pipeline composer maps agents using template subsection keys. The wizard endpoint has `request.wizard_type` (e.g., `"idea_wizard"`, `"scene_wizard"`, `"script_writer_wizard"`). These must match the subsection keys used in the pipeline maps.
**How to avoid:** Pass `request.wizard_type` as both the `subsection_key` and `wizard_type` parameters. The pipeline composer's template discovery already uses these exact wizard_type values as subsection keys (verified in `WIZARD_RESULT_SCHEMAS`).
**Warning signs:** Middleware always returns pass-through even when agents are mapped.

### Pitfall 4: Breaking `apply_wizard_result_to_db` with `_meta`
**What goes wrong:** The `apply_wizard_result_to_db` function reads specific keys from `result` (e.g., `result.get("fields", {})`, `result.get("scenes", [])`, `result.get("screenplays", [])`). If `_meta` is injected into `result`, it doesn't break anything because `apply_wizard_result_to_db` only reads known keys.
**Why it happens:** Not really a pitfall, but worth verifying.
**How to avoid:** Verify that `apply_wizard_result_to_db` ignores unknown keys. Reading the code confirms it only reads `"fields"`, `"scenes"`, `"screenplays"` via `.get()` calls. The `_meta` key is safely ignored.
**Warning signs:** None expected -- but test to confirm.

### Pitfall 5: Existing Tests Expecting Exact `result` Shape
**What goes wrong:** If any test asserts the exact structure of `wizard_run.result`, the added `_meta` key could cause a test failure.
**Why it happens:** Tests might do `assert result == {"fields": {...}}` which would fail with the extra `_meta` key.
**How to avoid:** Check: there are currently zero wizard endpoint tests (confirmed by grep). The only wizard-related tests are in `test_agent_review_middleware.py` (which test the middleware in isolation) and `test_pipeline_composer.py` (which test mapping). So success criterion #4 ("existing wizard generation tests pass without modification") is trivially satisfied -- there are no such tests to break.
**Warning signs:** None -- no existing wizard endpoint tests exist.

## Code Examples

### Complete Injection in `run_wizard()` (verified pattern)
```python
# Source: Adapted from chat.py SessionLocal pattern + middleware API from Phase 5
# In wizards.py:

from ...db import SessionLocal
from ...services.agent_review_middleware import agent_review_middleware

# Inside run_wizard(), after wizard_generate() returns:
try:
    result = await template_ai_service.wizard_generate(
        wizard_type=request.wizard_type,
        config=config,
        project_context=project_context,
        template_id=template_id
    )

    # REVW-01: Route through agent review middleware
    review_result = await agent_review_middleware.review_step_output(
        phase=request.phase,
        subsection_key=request.wizard_type,
        raw_output=result,
        owner_id=str(current_user.id),
        session_factory=SessionLocal,
        wizard_type=request.wizard_type,
    )
    result = review_result["output"]

    # Embed review metadata in result JSON
    if "_meta" not in result:
        result["_meta"] = {}
    result["_meta"]["agents_consulted"] = review_result["agents_consulted"]
    result["_meta"]["review_applied"] = review_result["review_applied"]

    wizard_run.result = result
    wizard_run.status = "completed"
except Exception as e:
    wizard_run.status = "failed"
    wizard_run.error_message = str(e)
```

### WizardRunResponse Schema Update
```python
# Source: schemas.py, following existing model_validator patterns
from pydantic import model_validator

class WizardRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    wizard_type: str
    phase: str
    status: str
    config: Dict = Field(default_factory=dict)
    result: Dict = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    agents_consulted: List[Dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def extract_agents_consulted(self):
        """Extract agents_consulted from result._meta for convenient access."""
        if not self.agents_consulted and self.result:
            meta = self.result.get("_meta", {})
            self.agents_consulted = meta.get("agents_consulted", [])
        return self
```

### End-to-End Integration Test Pattern
```python
# Source: Following test_agent_review_middleware.py patterns
import json
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.database import Agent, AgentPipelineMap, AgentType, WizardRun

@pytest.mark.asyncio
async def test_wizard_injection_with_agents(db_session, owner_id):
    """When agents are mapped to the wizard step, the wizard result
    is refined and agents_consulted metadata is embedded."""
    # Create agent + pipeline map
    agent = Agent(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        name="Story Expert",
        system_prompt_template="You are a helpful screenwriting assistant.",
        agent_type=AgentType.BOOK_BASED,
        is_active=True,
        is_default=False,
    )
    db_session.add(agent)
    db_session.flush()

    mapping = AgentPipelineMap(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        agent_id=str(agent.id),
        phase="idea",
        subsection_key="idea_wizard",
        confidence=0.9,
        rationale="Test",
        pipeline_dirty=False,
    )
    db_session.add(mapping)
    db_session.flush()

    # Mock wizard_generate + middleware AI calls
    raw_output = {"fields": {"genre": "drama", "initial_idea": "A story"}}
    review_resp = json.dumps({"issues": [], "suggestions": ["add conflict"]})
    merge_resp = json.dumps({"fields": {"genre": "thriller", "initial_idea": "refined"}})

    # Verify middleware is called and result is replaced
    with patch("app.services.agent_review_middleware.chat_completion",
               new_callable=AsyncMock, side_effect=[review_resp, merge_resp]):
        from app.services.agent_review_middleware import agent_review_middleware
        result = await agent_review_middleware.review_step_output(
            phase="idea",
            subsection_key="idea_wizard",
            raw_output=raw_output,
            owner_id=owner_id,
            session_factory=lambda: db_session,
            wizard_type="idea_wizard",
        )

    assert result["review_applied"] is True
    assert len(result["agents_consulted"]) == 1
    assert result["output"]["fields"]["genre"] == "thriller"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Wizard generates output directly to DB | Wizard output routes through agent review before DB write | Phase 6 (this phase) | Agents influence all wizard-generated content |
| No review metadata in wizard response | `agents_consulted` embedded in result + extracted to response | Phase 6 (this phase) | Frontend can show which agents reviewed output |
| `WizardRunResponse` has no agent metadata | `agents_consulted` field added via `model_validator` | Phase 6 (this phase) | Backward-compatible schema enhancement |

## Injection Point Analysis

### Exact Location
**File:** `backend/app/api/endpoints/wizards.py`
**Function:** `run_wizard()` (line 54)
**Between:** Line 97 (`result = await template_ai_service.wizard_generate(...)`) and line 98 (`wizard_run.result = result`)

### Call Flow Before Phase 6
```
HTTP POST /api/wizards/run
  -> run_wizard()
    -> wizard_generate() --> result (dict)
    -> wizard_run.result = result
    -> db.commit()
    -> return wizard_run (serialized via WizardRunResponse)
```

### Call Flow After Phase 6
```
HTTP POST /api/wizards/run
  -> run_wizard()
    -> wizard_generate() --> raw_result (dict)
    -> review_step_output(raw_result) --> {"output": refined, "agents_consulted": [...]}
    -> result = review_result["output"]
    -> result["_meta"] = {"agents_consulted": [...], "review_applied": bool}
    -> wizard_run.result = result
    -> db.commit()
    -> return wizard_run (serialized via WizardRunResponse with agents_consulted extracted)
```

### Arguments for `review_step_output()`
| Parameter | Value Source | Notes |
|-----------|-------------|-------|
| `phase` | `request.phase` | From the wizard run request body |
| `subsection_key` | `request.wizard_type` | Maps to the pipeline map subsection keys |
| `raw_output` | `result` from `wizard_generate()` | The raw AI generation output |
| `owner_id` | `str(current_user.id)` | String cast for cross-DB compatibility (Phase 2 pattern) |
| `session_factory` | `SessionLocal` (imported from `db.py`) | Factory callable, NOT the request `db` session |
| `wizard_type` | `request.wizard_type` | Used by merge to select correct output schema |

## Open Questions

1. **`_meta` key stripping before `apply_wizard_result_to_db`**
   - What we know: `apply_wizard_result_to_db` reads only known keys (`fields`, `scenes`, `screenplays`) via `.get()` and ignores unknown keys.
   - What's unclear: Should `_meta` be stripped from the result before it's stored in the DB, or is it acceptable to persist it?
   - Recommendation: Keep `_meta` in the stored result. It serves as an audit trail of which agents influenced the output. It doesn't interfere with `apply_wizard_result_to_db`.

2. **`flag_modified` needed for nested JSON update?**
   - What we know: SQLAlchemy sometimes doesn't detect in-place JSON mutation.
   - What's unclear: Since `wizard_run.result = result` is a full assignment (not in-place mutation), `flag_modified` should not be needed. The assignment happens before `db.commit()`.
   - Recommendation: No `flag_modified` needed -- the pattern is `wizard_run.result = result` (full replacement), not mutation of an existing dict.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` (existing) |
| Quick run command | `cd backend && python -m pytest app/tests/test_wizard_injection.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVW-01 | Middleware called between wizard_generate and DB write; result is refined | integration | `pytest app/tests/test_wizard_injection.py::test_wizard_injection_with_mapped_agents -x` | Wave 0 |
| REVW-01 | `agents_consulted` surfaced in wizard run response | integration | `pytest app/tests/test_wizard_injection.py::test_agents_consulted_in_response -x` | Wave 0 |
| REVW-01 | Zero agents = pass-through, identical to pre-injection behavior | integration | `pytest app/tests/test_wizard_injection.py::test_wizard_passthrough_no_agents -x` | Wave 0 |
| REVW-01 | Existing middleware tests still pass (regression) | unit | `pytest app/tests/test_agent_review_middleware.py -x` | Exists (10 tests) |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_wizard_injection.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_wizard_injection.py` -- covers REVW-01 injection, metadata propagation, and pass-through
- [ ] No new framework install needed
- [ ] No new conftest fixtures needed -- existing `db_session`, `mock_auth_headers`, and `owner_id` patterns are sufficient

## Sources

### Primary (HIGH confidence)
- **Codebase inspection:** `backend/app/api/endpoints/wizards.py` -- exact injection point at lines 92-98, `run_wizard()` function structure, `apply_wizard_result_to_db()` key-reading pattern
- **Codebase inspection:** `backend/app/services/agent_review_middleware.py` -- `review_step_output()` signature and return shape, `WIZARD_RESULT_SCHEMAS`, zero-agent pass-through
- **Codebase inspection:** `backend/app/api/endpoints/chat.py` -- `SessionLocal` import and usage pattern (lines 10, 163, 190)
- **Codebase inspection:** `backend/app/db.py` -- `SessionLocal` factory definition
- **Codebase inspection:** `backend/app/models/schemas.py` -- current `WizardRunResponse` schema (lines 473-485)
- **Codebase inspection:** `backend/app/models/database.py` -- `WizardRun` model columns (lines 190-202), no `agents_consulted` column
- **Codebase inspection:** `backend/app/tests/test_agent_review_middleware.py` -- 10 existing tests (all passing per Phase 5 verification)
- **Phase 5 verification:** `05-VERIFICATION.md` -- confirms REVW-01 partial status and Phase 6 injection as planned next step

### Secondary (MEDIUM confidence)
- **STATE.md decisions:** "Session-per-task pattern required for asyncio.gather", "Build custom using only existing dependencies"
- **REQUIREMENTS.md:** REVW-01 definition and Phase 5+6 traceability mapping
- **ROADMAP.md:** Phase 6 success criteria and plan outlines

### Tertiary (LOW confidence)
- None -- all findings are based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist, zero new dependencies, established patterns
- Architecture: HIGH -- injection point exactly identified, return shape fully documented, schema pattern proven
- Pitfalls: HIGH -- all potential issues identified from codebase inspection; the `db` vs `SessionLocal` pitfall is the most critical and is well-documented in Phase 4/5 history
- Testing: HIGH -- no existing wizard endpoint tests to break; new integration tests follow established patterns

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependency changes expected)
