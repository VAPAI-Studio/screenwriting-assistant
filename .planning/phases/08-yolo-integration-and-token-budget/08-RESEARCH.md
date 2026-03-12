# Phase 8: YOLO Integration and Token Budget - Research

**Researched:** 2026-03-12
**Domain:** Backend orchestration -- wiring YOLO auto-generation through agent review middleware with cost controls
**Confidence:** HIGH

## Summary

Phase 8 connects the existing YOLO auto-generation flow (in `ai_chat.py`) with the agent review middleware (built in Phases 5-6) and adds configurable budget controls (max agents per step, relevance threshold). The key insight is that the YOLO flow currently does NOT route through the review middleware -- the wizard strategy in `_yolo_run_wizard` calls `template_ai_service.wizard_generate()` directly and then `apply_wizard_result_to_db()`, completely bypassing the `agent_review_middleware.review_step_output()` call that Phase 6 injected into `wizards.py`'s `/run` endpoint. The non-wizard strategies (`_yolo_fill_blanks`, `_yolo_fill_items`, `_yolo_fill_repeatable`) also bypass agent review entirely.

The work decomposes into: (1) adding two new config values to `config.py`, (2) modifying the middleware's `_lookup_mapped_agents` to apply relevance-score gating and agent-count capping, (3) injecting review middleware calls into the four YOLO strategy functions in `ai_chat.py`, and (4) verifying LLM call counts match expectations. All changes are backend-only. No new dependencies are needed -- this phase uses existing patterns (Pydantic Settings, asyncio.gather session-per-task, agent_review_middleware singleton).

**Primary recommendation:** Add the two config values to Settings, implement gating logic in the middleware's agent lookup, then wire the middleware into each YOLO strategy function following the same pattern used in `wizards.py` run_wizard.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| YOLO-01 | Agent reviews fire during YOLO auto-generation flow through same middleware path | The YOLO flow currently bypasses the middleware entirely. `_yolo_run_wizard` calls `wizard_generate()` directly (line 929 of ai_chat.py) without routing through `agent_review_middleware.review_step_output()`. Must inject middleware calls into each YOLO strategy function. The exact same middleware singleton (`agent_review_middleware`) and `review_step_output()` entry point used in `wizards.py` run_wizard (line 102) should be called. |
| YOLO-02 | Token budget controls -- configurable max agents per step and relevance threshold | The `AgentPipelineMap.confidence` column (Float, 0.0-1.0) already stores relevance scores from pipeline composition. The middleware's `_lookup_mapped_agents` already queries with `.order_by(AgentPipelineMap.confidence.desc())`. Gating logic should filter by `AGENT_RELEVANCE_THRESHOLD` and cap at `MAX_AGENTS_PER_PIPELINE_STEP` -- both applied in the lookup method before fan-out. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | HTTP framework, streaming responses | Already in use |
| Pydantic Settings | existing | `config.py` Settings class for env-var config | Already in use for all config values |
| SQLAlchemy | existing | ORM for AgentPipelineMap queries | Already in use |
| asyncio | stdlib | `asyncio.gather` for parallel agent reviews | Already used in middleware fan-out |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + pytest-asyncio | existing | TDD for new gating logic and YOLO integration | All new tests |
| unittest.mock | stdlib | Mock chat_completion for deterministic tests | All LLM-calling tests |

### Alternatives Considered
None -- all work uses existing stack. No new dependencies required.

## Architecture Patterns

### Recommended Approach

The core architectural decision is WHERE to implement relevance gating. Two options:

**Option A (Recommended): Gating inside `_lookup_mapped_agents`**
The middleware's `_lookup_mapped_agents` already queries AgentPipelineMap ordered by confidence desc. Adding a `.filter(AgentPipelineMap.confidence >= threshold)` and `.limit(max_agents)` to this query is the most efficient approach -- it avoids fetching agents that will be discarded, and keeps the gating logic co-located with the lookup.

**Option B (Not recommended): Gating as a separate layer**
A separate "budget filter" function that post-processes the agent list. This creates unnecessary data transfer and separates related logic.

### Pattern: YOLO Middleware Injection

Follow the exact pattern from `wizards.py` run_wizard (lines 94-116):

```python
# In _yolo_run_wizard (and similarly in other strategies):
result = await template_ai_service.wizard_generate(...)

# YOLO-01: Route through agent review middleware (same as manual wizard path)
review_result = await agent_review_middleware.review_step_output(
    phase=phase,
    subsection_key=wizard_type,  # matches the subsection_key used in pipeline maps
    raw_output=result,
    owner_id=str(current_user.id),  # must be passed down from yolo_fill endpoint
    session_factory=SessionLocal,
    wizard_type=wizard_type,
)
result = review_result["output"]

# Then apply to DB as before
apply_result = apply_wizard_result_to_db(db, project, phase, wizard_type, result)
```

### Pattern: Config Values in Settings

Follow existing patterns in `config.py`:

```python
# Agent pipeline budget
MAX_AGENTS_PER_PIPELINE_STEP: int = 3
AGENT_RELEVANCE_THRESHOLD: float = 0.3
```

### Pattern: Gating in Middleware Lookup

```python
def _lookup_mapped_agents(
    self,
    owner_id: str,
    phase: str,
    subsection_key: str,
    db: Session,
) -> List[Dict[str, Any]]:
    """Query AgentPipelineMap for active agents mapped to this step,
    filtered by relevance threshold and capped at max per step."""
    query = (
        db.query(AgentPipelineMap)
        .filter(
            AgentPipelineMap.owner_id == str(owner_id),
            AgentPipelineMap.phase == phase,
            AgentPipelineMap.subsection_key == subsection_key,
            AgentPipelineMap.confidence >= settings.AGENT_RELEVANCE_THRESHOLD,
        )
        .order_by(AgentPipelineMap.confidence.desc())
        .limit(settings.MAX_AGENTS_PER_PIPELINE_STEP)
        .all()
    )
    # ... rest unchanged
```

### Critical: Passing owner_id Through YOLO Functions

The current YOLO helper functions (`_yolo_fill_blanks`, `_yolo_run_wizard`, etc.) do NOT receive `owner_id` or `current_user` as parameters. The `yolo_fill` endpoint has access to `current_user` but does not pass it through. Each YOLO helper's signature must be extended to accept `owner_id: str` (or the full `current_user`).

### Critical: Non-Wizard YOLO Strategies

The requirement says "agent reviews fire during YOLO auto-generation flow through same middleware path." The `_yolo_run_wizard` strategy is the obvious match (it produces wizard-type output). But the other three strategies (`fill_blanks`, `fill_items`, `fill_repeatable`) also produce AI-generated content. The question is whether they should ALSO route through agent review.

**Analysis:**
- `_yolo_run_wizard`: Calls `wizard_generate()` which is identical to manual wizard flow. Agent review is the direct equivalent of what Phase 6 wired for manual generation. **Must integrate.**
- `_yolo_fill_blanks`: Calls `template_ai_service.fill_blanks()` -- generates structured form content. This is a different AI service entry point. The middleware expects wizard-type output schemas. These steps ARE in the pipeline map targets (structured_form subsections). **Should integrate**, but the merge step may not have a matching schema in `WIZARD_RESULT_SCHEMAS`.
- `_yolo_fill_items` / `_yolo_fill_repeatable`: Generate per-item content. These are granular sub-step fills. Routing each individual item through agent review would multiply LLM calls dramatically (N items x M agents per item). **Consider whether to integrate or skip for v1.**

**Recommendation for v1:** Only integrate `_yolo_run_wizard` with the middleware, since (a) it matches the requirement wording "same middleware path as manual generation," (b) it uses `wizard_generate()` which is the same function the manual wizard endpoint uses, and (c) `fill_blanks`/`fill_items`/`fill_repeatable` don't produce wizard-type output so the merge schema validation would need extension. The non-wizard strategies can be deferred to v2 (YOLO-03/YOLO-04).

### Anti-Patterns to Avoid
- **DO NOT create a separate review layer for YOLO** -- reuse the existing `agent_review_middleware.review_step_output()` singleton
- **DO NOT fetch all agents and filter in Python** -- apply threshold and limit at the SQL query level
- **DO NOT pass db session into middleware** -- pass SessionLocal factory as established in Phase 4/6
- **DO NOT modify the middleware's public API** -- the gating is internal to `_lookup_mapped_agents`; callers do not need to know about budget controls

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Agent relevance gating | Custom filter function | SQLAlchemy `.filter().limit()` in existing lookup | Database-level filtering is more efficient; keeps logic co-located |
| Config management | Hardcoded constants | Pydantic Settings fields in `config.py` | Env-var override, type validation, consistent with project convention |
| Parallel review execution | Manual thread management | Existing `asyncio.gather` in middleware `_fan_out_reviews` | Already proven stable in Phase 4/5 |

**Key insight:** The entire agent review pipeline is already built and tested. Phase 8 is pure wiring -- connecting the YOLO code path to the existing middleware, and adding two SQL filter clauses.

## Common Pitfalls

### Pitfall 1: Missing owner_id in YOLO Helper Functions
**What goes wrong:** The YOLO helper functions (`_yolo_run_wizard`, etc.) don't currently accept `owner_id`. Calling the middleware requires it.
**Why it happens:** The helpers were written before agent review integration was planned.
**How to avoid:** Add `owner_id: str` parameter to each helper function and pass `str(current_user.id)` from the `yolo_fill` endpoint.
**Warning signs:** TypeError on missing parameter; middleware returns zero agents (wrong owner_id).

### Pitfall 2: SessionLocal Not Imported in ai_chat.py
**What goes wrong:** The middleware requires a `session_factory` callable (e.g., `SessionLocal`). The `ai_chat.py` file may not import it.
**Why it happens:** `wizards.py` imports SessionLocal but `ai_chat.py` may not.
**How to avoid:** Verify import exists: `from ...db import SessionLocal`.
**Warning signs:** ImportError or NameError at runtime.

### Pitfall 3: YOLO SSE Stream Timing
**What goes wrong:** Agent review adds latency to each YOLO step (N agent LLM calls + 1 merge call). The SSE stream may appear frozen to the frontend.
**Why it happens:** The YOLO flow is sequential -- each step must complete before the next begins.
**How to avoid:** The existing SSE event pattern already sends "running" status before each step. No additional frontend changes needed -- the user sees which step is in progress.
**Warning signs:** Frontend timeout on long YOLO runs with many agents.

### Pitfall 4: Zero Overhead When No Agents Mapped
**What goes wrong:** Success criterion 4 requires "zero mapped agents completes at same speed." If the middleware call itself has measurable overhead (DB query, session creation/teardown), this could fail.
**Why it happens:** Even the zero-agent code path creates a DB session, runs a query, and closes the session.
**How to avoid:** The middleware's zero-agent path is already optimized (single DB query, early return). The overhead is a single SELECT query per step -- negligible compared to LLM call time. For a truly zero-overhead path, could add a pre-check before calling the middleware, but this risks code divergence from the manual wizard path. **Recommendation:** Accept the negligible DB query overhead; it satisfies "same speed" in practice.
**Warning signs:** Performance test showing >100ms added per step with zero agents (actual expected: <10ms per step).

### Pitfall 5: Gating Applied Globally vs Per-Call
**What goes wrong:** If `MAX_AGENTS_PER_PIPELINE_STEP` and `AGENT_RELEVANCE_THRESHOLD` are applied as global constants at import time, they cannot be overridden in tests.
**Why it happens:** Reading `settings.X` at module import vs. at call time.
**How to avoid:** Read `settings.MAX_AGENTS_PER_PIPELINE_STEP` and `settings.AGENT_RELEVANCE_THRESHOLD` inside `_lookup_mapped_agents` at call time, not at module level.
**Warning signs:** Tests cannot mock config values; changing env vars has no effect.

## Code Examples

Verified patterns from the existing codebase:

### Config Values (from config.py lines 52-57)
```python
# Pipeline composition (existing)
PIPELINE_BATCH_SIZE: int = 5
PIPELINE_COMPOSITION_MAX_TOKENS: int = 2000

# Agent pipeline budget (new -- Phase 8)
MAX_AGENTS_PER_PIPELINE_STEP: int = 3
AGENT_RELEVANCE_THRESHOLD: float = 0.3
```

### Middleware Call Pattern (from wizards.py lines 94-116)
```python
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
```

### Existing Middleware Lookup (from agent_review_middleware.py lines 147-194)
```python
def _lookup_mapped_agents(self, owner_id, phase, subsection_key, db):
    mappings = (
        db.query(AgentPipelineMap)
        .filter(
            AgentPipelineMap.owner_id == str(owner_id),
            AgentPipelineMap.phase == phase,
            AgentPipelineMap.subsection_key == subsection_key,
        )
        .order_by(AgentPipelineMap.confidence.desc())
        .all()
    )
    # ... then fetches Agent objects by ID
```

### LLM Call Count Formula

For a YOLO run with W wizard steps and A agents mapped per step (after gating):
- Without agents: W LLM calls (one per wizard_generate)
- With agents: W * (1 + A + 1) LLM calls = W * (A + 2)
  - 1 = wizard_generate
  - A = agent review fan-out (parallel)
  - 1 = merge call

Example: 3 wizard steps, 3 agents each = 3 * (3 + 2) = 15 LLM calls.
With MAX_AGENTS_PER_PIPELINE_STEP=2: 3 * (2 + 2) = 12 LLM calls.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| YOLO generates without agent review | YOLO routes through review middleware (Phase 8) | This phase | Agents influence all generation paths |
| All mapped agents review every step | Relevance threshold + count cap (Phase 8) | This phase | Cost control, quality preservation |

**Key files to modify:**
- `backend/app/config.py` -- add 2 config values
- `backend/app/services/agent_review_middleware.py` -- add gating to `_lookup_mapped_agents`
- `backend/app/api/endpoints/ai_chat.py` -- wire middleware into YOLO helpers
- `backend/app/tests/test_yolo_integration.py` -- new test file

## Open Questions

1. **Should non-wizard YOLO strategies (fill_blanks, fill_items, fill_repeatable) also route through agent review?**
   - What we know: The requirement says "same middleware path as manual generation." Manual generation only goes through the wizard endpoint. Fill_blanks/fill_items are YOLO-only strategies with no manual equivalent.
   - What's unclear: Whether the user expects agent review on ALL YOLO-generated content or only wizard-generated content.
   - Recommendation: Implement only for `_yolo_run_wizard` in v1. The middleware's merge schema validation is designed for wizard output types. Extending to fill_blanks would require new schema definitions.

2. **Default values for MAX_AGENTS_PER_PIPELINE_STEP and AGENT_RELEVANCE_THRESHOLD**
   - What we know: STATE.md blocker says "Establish token cost model (tokens per step x agents x steps) before committing to config defaults."
   - What's unclear: Exact cost model depends on template step count and typical agent count.
   - Recommendation: Use `MAX_AGENTS_PER_PIPELINE_STEP=3` (matches `MAX_AGENTS_PER_REVIEW=5` minus merge overhead margin) and `AGENT_RELEVANCE_THRESHOLD=0.3` (filters clearly irrelevant agents while keeping borderline ones). Both are env-var overridable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_yolo_integration.py -x` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| YOLO-01 | `_yolo_run_wizard` calls `review_step_output` with correct params | unit | `pytest app/tests/test_yolo_integration.py::test_yolo_wizard_routes_through_middleware -x` | Wave 0 |
| YOLO-01 | Zero-agent YOLO wizard passes through unchanged | unit | `pytest app/tests/test_yolo_integration.py::test_yolo_wizard_zero_agents_passthrough -x` | Wave 0 |
| YOLO-02 | MAX_AGENTS_PER_PIPELINE_STEP limits agents returned by lookup | unit | `pytest app/tests/test_yolo_integration.py::test_max_agents_per_step_limits_lookup -x` | Wave 0 |
| YOLO-02 | AGENT_RELEVANCE_THRESHOLD filters low-confidence agents | unit | `pytest app/tests/test_yolo_integration.py::test_relevance_threshold_filters_agents -x` | Wave 0 |
| YOLO-01+02 | Full YOLO run with 3 agents fires correct LLM call count | integration | `pytest app/tests/test_yolo_integration.py::test_yolo_full_run_llm_call_count -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_yolo_integration.py -x`
- **Per wave merge:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_yolo_integration.py` -- covers YOLO-01, YOLO-02 (new file)
- [ ] No new framework install needed -- pytest + pytest-asyncio already configured

## Sources

### Primary (HIGH confidence)
- `backend/app/api/endpoints/ai_chat.py` lines 828-1108 -- existing YOLO flow (yolo_fill endpoint, _determine_yolo_strategy, _yolo_run_wizard, _yolo_fill_blanks, _yolo_fill_items, _yolo_fill_repeatable)
- `backend/app/services/agent_review_middleware.py` -- full middleware implementation with _lookup_mapped_agents, _fan_out_reviews, _merge_reviews
- `backend/app/api/endpoints/wizards.py` lines 94-116 -- Phase 6 middleware injection pattern (the pattern to replicate)
- `backend/app/config.py` -- existing Settings class and config value conventions
- `backend/app/models/database.py` lines 434-455 -- AgentPipelineMap model with confidence column
- `backend/app/tests/test_agent_review_middleware.py` -- existing test patterns for mocking chat_completion
- `backend/app/tests/test_wizard_injection.py` -- existing test patterns for middleware integration

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` -- YOLO-01 and YOLO-02 requirement definitions
- `.planning/STATE.md` -- Blocker about token cost model for config defaults

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all existing dependencies, no new installs
- Architecture: HIGH -- pattern is clearly established by Phase 6 wizard injection; this is replication
- Pitfalls: HIGH -- identified from direct code inspection of both source and target files
- Config defaults: MEDIUM -- reasonable defaults but the STATE.md blocker about cost model is still open

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable -- pure internal wiring, no external dependency changes)
