# Phase 5: Agent Review Middleware - Research

**Researched:** 2026-03-11
**Domain:** Async Python middleware for AI agent review fan-out, merge, and pass-through
**Confidence:** HIGH

## Summary

Phase 5 builds the core middleware layer (`agent_review_middleware.py`) that intercepts wizard generation output, fans out to mapped agents for review in parallel, merges their feedback via an AI call, and returns refined output. When no agents are mapped, it passes through unchanged with zero LLM overhead.

The project already has all the building blocks in place from Phases 1-4: the `AgentPipelineMap` table stores agent-to-step mappings (Phase 1), the `PipelineComposer` populates those mappings (Phase 2-3), the `SessionFactory` pattern enables safe concurrent DB access under `asyncio.gather` (Phase 4), and the `ai_provider.chat_completion` function provides the unified LLM interface. The middleware is a new service module that composes these existing pieces into a single `review_step_output()` entry point.

The highest-risk area is the merge prompt engineering: synthesizing multiple agent reviews into a single refined wizard result that conforms to the expected JSON schema (e.g., `{"scenes": [...]}` for scene_wizard, `{"fields": {...}}` for idea_wizard, `{"screenplays": [...]}` for script_writer_wizard). The merge must apply conflict-resolution rules (most specific/actionable wins) rather than blending all suggestions. This is a prompt engineering challenge, not a code architecture challenge.

**Primary recommendation:** Build `agent_review_middleware.py` as a stateless service module with a single public function `review_step_output()`. Use the existing `SessionFactory` pattern from Phase 4 for parallel agent reviews. The merge call should use `json_mode=True` with explicit schema constraints in the prompt.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REVW-01 | Agent review middleware injected in `wizards.py` between `wizard_generate()` and `apply_wizard_result_to_db()` | Injection point identified in `wizards.py` line 92-98 (after `wizard_generate()` returns, before `wizard_run.result = result`). Actual injection is Phase 6 scope; Phase 5 builds the callable middleware. |
| REVW-02 | All agents mapped to a step review the generated output in parallel via `asyncio.gather` | Phase 4 established the `SessionFactory` pattern; Phase 5 reuses `_review_with_session()` style wrappers with `asyncio.gather(*tasks, return_exceptions=True)`. Confirmed pattern in `agent_service.py` lines 1078-1118. |
| REVW-03 | AI merge call synthesizes all agent feedback into refined output matching the expected wizard result schema | Three distinct wizard result schemas identified: idea (`{"fields": {...}}`), scene (`{"scenes": [...]}`), script (`{"screenplays": [...]}`). Merge prompt must specify target schema per wizard_type. |
| REVW-04 | If no agents are mapped to a step, generation passes through unchanged (zero-impact bypass) | Simple early return when `AgentPipelineMap` query returns zero rows for the given `(owner_id, phase, subsection_key)`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio (stdlib) | Python 3.11 | Parallel agent review fan-out | Already used in `agent_service.py` for `run_multi_agent_review` |
| SQLAlchemy | (existing) | Query `AgentPipelineMap` for agent lookup | Already the project's ORM |
| Pydantic v2 | (existing) | Type validation for merge results | Already used for all schemas |
| ai_provider | (project module) | `chat_completion()` for individual agent reviews and merge call | Unified LLM wrapper already supports OpenAI + Anthropic |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging (stdlib) | Python 3.11 | Structured logging for review pipeline | Every service uses `logging.getLogger(__name__)` |
| json (stdlib) | Python 3.11 | Parse merge call JSON output | Already standard across all AI service modules |
| typing (stdlib) | Python 3.11 | Type annotations including `SessionFactory` alias | Follows `agent_service.py` convention |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom middleware module | LangGraph/CrewAI | Project decision: "Build custom using only existing dependencies -- no LangGraph, CrewAI, or AutoGen" |
| `asyncio.gather` | `asyncio.TaskGroup` (3.11+) | TaskGroup cancels all on first failure; gather with `return_exceptions=True` is more fault-tolerant and matches existing patterns |
| Separate merge service | Inline merge in middleware | Keep merge logic within the middleware module for cohesion; extract later if complexity grows |

**Installation:**
```bash
# No new dependencies needed -- all building blocks exist in the project
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
├── agent_review_middleware.py    # NEW: Phase 5 middleware
├── agent_service.py             # Existing: agent review + chat (has SessionFactory pattern)
├── pipeline_composer.py         # Existing: agent-to-step mapping
├── template_ai_service.py       # Existing: wizard_generate() (Phase 6 injection target)
└── ai_provider.py               # Existing: unified LLM wrapper
```

### Pattern 1: Stateless Service Module with Singleton
**What:** A module-level singleton service class with a single public entry point
**When to use:** Follows existing project convention (see `pipeline_composer.py`, `template_ai_service.py`)
**Example:**
```python
# backend/app/services/agent_review_middleware.py

import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..config import settings
from ..models.database import Agent, AgentPipelineMap
from .ai_provider import chat_completion

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


class AgentReviewMiddleware:
    """Intercepts wizard generation output and runs mapped agent reviews."""

    async def review_step_output(
        self,
        phase: str,
        subsection_key: str,
        raw_output: Dict,
        owner_id: UUID,
        session_factory: SessionFactory,
        wizard_type: Optional[str] = None,
    ) -> Dict:
        """Entry point. Returns refined output or raw_output unchanged."""
        ...


# Module singleton
agent_review_middleware = AgentReviewMiddleware()
```

### Pattern 2: Session-per-Task Fan-out (from Phase 4)
**What:** Each parallel agent task gets its own DB session via `session_factory()`
**When to use:** Any `asyncio.gather` site that touches the database
**Example:**
```python
# Reuses the exact pattern from agent_service.py Phase 4
async def _review_agent_with_session(
    self,
    agent: Agent,
    raw_output: Dict,
    phase: str,
    subsection_key: str,
    session_factory: SessionFactory,
) -> Dict:
    db = session_factory()
    try:
        return await self._single_agent_review(agent, raw_output, phase, subsection_key, db)
    finally:
        db.close()
```

### Pattern 3: Zero-Agent Pass-Through
**What:** Early return when no agents are mapped to the step
**When to use:** REVW-04 requirement -- avoids any LLM overhead when no agents care about a step
**Example:**
```python
# Inside review_step_output():
mapped_agents = self._lookup_mapped_agents(owner_id, phase, subsection_key, db)
if not mapped_agents:
    return {
        "output": raw_output,
        "agents_consulted": [],
        "review_applied": False,
    }
```

### Pattern 4: Merge with Schema Awareness
**What:** The merge AI call receives the target wizard result schema so it outputs conformant JSON
**When to use:** REVW-03 -- merge must produce output that matches what `apply_wizard_result_to_db()` expects
**Example:**
```python
WIZARD_RESULT_SCHEMAS = {
    "idea_wizard": '{"fields": {"genre": "...", "initial_idea": "...", "tone": "...", "target_audience": "..."}}',
    "scene_wizard": '{"scenes": [{"summary": "...", "arena": "...", ...10 fields per scene...}]}',
    "script_writer_wizard": '{"screenplays": [{"title": "...", "content": "...", "episode_index": N}]}',
}
```

### Anti-Patterns to Avoid
- **Shared session in gather:** Never pass a single `db` session to parallel `asyncio.gather` tasks. This causes `DetachedInstanceError`. Always use `session_factory()` per task. (Phase 4 lesson)
- **Blending merge strategy:** The merge prompt must NOT average or blend suggestions. "Most specific and actionable wins" is the conflict-resolution rule. Blending dilutes quality.
- **Modifying raw_output in place:** Always return a new dict from `review_step_output()`. Never mutate the input `raw_output` dict, as the caller may need the original for comparison or rollback.
- **Coupling to wizards.py:** The middleware should have no import dependency on `wizards.py`. It receives and returns plain dicts. Phase 6 handles the wiring.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel async execution | Custom thread pool or process pool | `asyncio.gather` with `return_exceptions=True` | Already proven in Phase 4; handles timeouts via `asyncio.wait_for` |
| Agent lookup by step | Manual SQL query | `db.query(AgentPipelineMap).filter(owner_id, phase, subsection_key)` | Table and indexes already exist from Phase 1 |
| LLM calls | Direct OpenAI/Anthropic SDK calls | `ai_provider.chat_completion()` | Provider-agnostic wrapper already handles both backends |
| JSON schema validation | Custom parser | `json_mode=True` in `chat_completion()` + `json.loads()` | Already standard across all AI service modules |
| Session factory type | New type alias | `SessionFactory = Callable[[], Session]` from `agent_service.py` | Already defined and tested in Phase 4 |

**Key insight:** This phase composes existing proven components. The only genuinely new code is the merge prompt engineering and the `_build_pipeline_system_prompt()` that translates phase/subsection_key into agent-understandable context.

## Common Pitfalls

### Pitfall 1: Merge Output Schema Mismatch
**What goes wrong:** The merge AI call returns JSON that doesn't match what `apply_wizard_result_to_db()` expects (e.g., returns `{"result": {...}}` instead of `{"scenes": [...]}`).
**Why it happens:** The merge prompt doesn't specify the exact output schema expected by the downstream consumer.
**How to avoid:** Include the exact expected JSON schema in the merge prompt, with field-level examples. Use `json_mode=True`. Validate the parsed output has the expected top-level key before returning.
**Warning signs:** `apply_wizard_result_to_db()` returns `{"items_created": 0}` when items were expected.

### Pitfall 2: Agent Review Prompt Missing Context
**What goes wrong:** Individual agent reviews provide generic feedback because they lack context about what the generated output IS and what phase/step it was generated for.
**Why it happens:** The agent's `system_prompt_template` expects template variables like `{concept_cards}`, `{framework}`, `{section_type}` from the legacy review system, but the pipeline review context is different.
**How to avoid:** Build `_build_pipeline_system_prompt()` that translates phase/subsection_key into meaningful context for the agent. Don't try to reuse the legacy `_build_system_prompt()` from `agent_service.py` which is designed for Section-based reviews.
**Warning signs:** Agent review output says "I need more context" or provides generic advice not related to the actual generated content.

### Pitfall 3: Timeout Cascade Under Load
**What goes wrong:** With 5+ agents mapped to a step, the total review time exceeds the HTTP timeout, causing a 504 to the user.
**Why it happens:** Parallel fan-out is still bounded by the slowest agent + the merge call. Each LLM call takes 3-10s.
**How to avoid:** Use `asyncio.wait_for()` with `settings.AGENT_REVIEW_TIMEOUT` (90s) per agent, plus a reasonable total timeout. The existing `AGENT_REVIEW_TIMEOUT=90` in config.py is generous for individual calls.
**Warning signs:** Wizard runs start timing out after agents are mapped.

### Pitfall 4: ORM Attribute Expiry After Commit
**What goes wrong:** Accessing agent attributes (e.g., `agent.name`, `agent.system_prompt_template`) after a `db.commit()` raises `DetachedInstanceError`.
**Why it happens:** SQLAlchemy expires ORM instances after commit. In the session-per-task pattern, each task's session commits independently.
**How to avoid:** Capture all needed agent attributes into plain Python dicts before entering the gather phase. Alternatively, use `db.expire_on_commit = False` on task-local sessions. The existing codebase uses the "capture before commit" pattern (see `agent_service.py` line 601: `sid = session.id`).
**Warning signs:** Intermittent `DetachedInstanceError` on agent attribute access inside parallel tasks.

### Pitfall 5: Empty Agent Reviews Polluting Merge
**What goes wrong:** An agent that fails or times out produces an empty/error review result, and the merge call tries to synthesize "nothing" alongside real reviews.
**Why it happens:** `asyncio.gather(return_exceptions=True)` returns Exception objects alongside valid results.
**How to avoid:** Filter out failed/error results before passing to the merge call. Only merge results with `status == "completed"`. If all agents failed, return `raw_output` unchanged.
**Warning signs:** Merge output contains phrases like "No feedback was provided" or "Agent X had no suggestions."

## Code Examples

### Agent Lookup by Pipeline Step
```python
# Source: Existing AgentPipelineMap model + Phase 1 schema
def _lookup_mapped_agents(
    self,
    owner_id: UUID,
    phase: str,
    subsection_key: str,
    db: Session,
) -> List[Agent]:
    """Fetch agents mapped to this pipeline step, ordered by confidence desc."""
    maps = (
        db.query(AgentPipelineMap)
        .filter(
            AgentPipelineMap.owner_id == str(owner_id),
            AgentPipelineMap.phase == phase,
            AgentPipelineMap.subsection_key == subsection_key,
        )
        .order_by(AgentPipelineMap.confidence.desc())
        .all()
    )
    if not maps:
        return []

    agent_ids = [str(m.agent_id) for m in maps]
    agents = (
        db.query(Agent)
        .filter(Agent.id.in_(agent_ids), Agent.is_active == True)
        .all()
    )
    # Preserve confidence ordering
    agent_map = {str(a.id): a for a in agents}
    return [agent_map[aid] for aid in agent_ids if aid in agent_map]
```

### Parallel Fan-out with Session-per-Task
```python
# Source: Pattern from agent_service.py run_multi_agent_review (Phase 4)
async def _fan_out_reviews(
    self,
    agents: List[Agent],
    raw_output: Dict,
    phase: str,
    subsection_key: str,
    session_factory: SessionFactory,
) -> List[Dict]:
    """Run all agent reviews in parallel, each with its own DB session."""
    tasks = [
        asyncio.wait_for(
            self._review_agent_with_session(
                agent, raw_output, phase, subsection_key, session_factory
            ),
            timeout=settings.AGENT_REVIEW_TIMEOUT,
        )
        for agent in agents
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    reviews = []
    for agent, result in zip(agents, results):
        if isinstance(result, Exception):
            logger.error(f"Agent {agent.name} review failed: {result}")
            continue  # Skip failed reviews in merge
        reviews.append(result)
    return reviews
```

### Merge Prompt Structure
```python
# Source: Project conventions from template_ai_service.py
MERGE_SYSTEM_PROMPT = """You are a screenplay review synthesizer.

You have received the original AI-generated output for a {wizard_type} step,
along with feedback from {agent_count} specialist agents.

## Your Task
Refine the original output by incorporating the most valuable agent feedback.

## Conflict Resolution Rules
1. When agents disagree, prefer the MOST SPECIFIC and ACTIONABLE suggestion
2. Do NOT blend or average suggestions -- pick the best version
3. If an agent's suggestion contradicts the project context, discard it
4. Preserve the original structure; only modify content within fields
5. If all agent feedback is generic or unhelpful, return the original unchanged

## Required Output Schema
{schema_description}

Return ONLY the refined output as valid JSON matching the schema above.
Do NOT include any commentary, explanations, or wrapper objects."""


async def _merge_reviews(
    self,
    raw_output: Dict,
    reviews: List[Dict],
    wizard_type: str,
) -> Dict:
    """Merge agent reviews into refined output via AI call."""
    schema_desc = WIZARD_RESULT_SCHEMAS.get(wizard_type, "Same schema as the input")

    reviews_text = "\n\n".join(
        f"### Agent: {r['agent_name']}\n{json.dumps(r.get('feedback', {}), indent=2)}"
        for r in reviews
    )

    system_prompt = MERGE_SYSTEM_PROMPT.format(
        wizard_type=wizard_type,
        agent_count=len(reviews),
        schema_description=schema_desc,
    )

    user_prompt = f"""## Original Output
{json.dumps(raw_output, indent=2)}

## Agent Reviews
{reviews_text}

Produce the refined output JSON."""

    text = await chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,  # Low temperature for deterministic merge
        max_tokens=settings.MAX_TOKENS,
        json_mode=True,
    )
    return json.loads(text)
```

### Individual Agent Review for Pipeline
```python
# Source: Adapted from agent_service.review_section pattern
async def _single_agent_review(
    self,
    agent: Agent,
    raw_output: Dict,
    phase: str,
    subsection_key: str,
    db: Session,
) -> Dict:
    """Single agent reviews the generated output for a pipeline step."""
    system_prompt = self._build_pipeline_system_prompt(agent, phase, subsection_key, db)

    text = await chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Review this generated output:\n\n{json.dumps(raw_output, indent=2)}"},
        ],
        temperature=0.7,
        max_tokens=settings.MAX_TOKENS,
        json_mode=True,
    )

    result = json.loads(text)
    return {
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "agent_color": agent.color,
        "feedback": result,
        "status": "completed",
    }
```

### Full Entry Point Skeleton
```python
async def review_step_output(
    self,
    phase: str,
    subsection_key: str,
    raw_output: Dict,
    owner_id: UUID,
    session_factory: SessionFactory,
    wizard_type: Optional[str] = None,
) -> Dict:
    """Main entry point: review wizard output through mapped agents.

    Returns:
        {
            "output": <refined or raw dict>,
            "agents_consulted": [{"agent_id": "...", "name": "...", "summary": "..."}],
            "review_applied": bool,
        }
    """
    # 1. Lookup mapped agents
    db = session_factory()
    try:
        agents = self._lookup_mapped_agents(owner_id, phase, subsection_key, db)
    finally:
        db.close()

    # 2. Zero-agent pass-through (REVW-04)
    if not agents:
        return {
            "output": raw_output,
            "agents_consulted": [],
            "review_applied": False,
        }

    # 3. Parallel fan-out (REVW-02)
    reviews = await self._fan_out_reviews(
        agents, raw_output, phase, subsection_key, session_factory
    )

    # 4. Filter successful reviews
    if not reviews:
        return {
            "output": raw_output,
            "agents_consulted": [],
            "review_applied": False,
        }

    # 5. Merge AI call (REVW-03)
    refined_output = await self._merge_reviews(raw_output, reviews, wizard_type or subsection_key)

    # 6. Build agents_consulted metadata
    agents_consulted = [
        {
            "agent_id": r["agent_id"],
            "name": r["agent_name"],
            "summary": _summarize_feedback(r.get("feedback", {})),
        }
        for r in reviews
    ]

    return {
        "output": refined_output,
        "agents_consulted": agents_consulted,
        "review_applied": True,
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sequential agent reviews | Parallel fan-out via `asyncio.gather` | Phase 4 | N agents in ~1x time instead of Nx time |
| Shared DB session in gather | Session-per-task via `SessionFactory` | Phase 4 | Eliminates `DetachedInstanceError` |
| Agent reviews only in chat context | Agent reviews injected in generation pipeline | Phase 5 (this phase) | Agents influence output, not just chat |
| No pipeline mapping | AI-composed `AgentPipelineMap` | Phase 1-3 | Agents automatically mapped to relevant steps |

## Wizard Result Schema Reference

The middleware MUST output JSON conforming to these schemas (consumed by `apply_wizard_result_to_db()`):

| Wizard Type | Top-level Key | Structure | Source |
|-------------|---------------|-----------|--------|
| `idea_wizard` | `fields` | `{"fields": {"genre": str, "initial_idea": str, "tone": str, "target_audience": str}}` | `template_ai_service.py:_generate_idea` |
| `scene_wizard` | `scenes` | `{"scenes": [{"summary": str, "arena": str, "inciting_incident": str, "goal": str, "subtext": str, "turning_point": str, "crisis": str, "climax": str, "fallout": str, "push_forward": str}]}` | `template_ai_service.py:_generate_scenes` |
| `script_writer_wizard` | `screenplays` | `{"screenplays": [{"title": str, "content": str, "episode_index": int}]}` | `template_ai_service.py:_generate_scripts` |

**Critical:** The merge call MUST preserve these exact schema shapes. Validation should check for the expected top-level key before returning.

## Agent System Prompt Considerations

The existing `agent_service._build_system_prompt()` uses template variables that assume a Section-based review context:
- `{concept_cards}`, `{concept_relationships}`, `{book_chunks}` -- RAG-based knowledge
- `{framework}`, `{section_type}` -- legacy framework concepts
- `{project_context}` -- formatted project data

For pipeline reviews, we need a NEW `_build_pipeline_system_prompt()` that:
1. Uses RAG context (concepts/chunks) relevant to the agent's knowledge base
2. Replaces `{framework}`/`{section_type}` with pipeline-relevant context (phase name, subsection description from template)
3. Instructs the agent to review generated JSON output rather than user-written notes
4. Tells the agent to output structured feedback (issues, suggestions, refined fields)

The agent's `system_prompt_template` may contain template variables. Plan 05-03 should define which variables are populated for pipeline reviews and handle missing variables gracefully (e.g., using `.format_map(defaultdict(str))` to avoid KeyError).

## Open Questions

1. **Token budget for merge call**
   - What we know: Each agent review is up to `MAX_TOKENS` (4000) tokens. The merge call receives raw_output + N reviews.
   - What's unclear: With 5 agents, the merge prompt could exceed input token limits (~20K+ tokens).
   - Recommendation: Truncate each agent review to a configurable max (e.g., 1000 tokens) before passing to merge. Add a `MERGE_MAX_INPUT_TOKENS` setting.

2. **Agent review prompt: review vs. rewrite**
   - What we know: Agents should provide feedback on generated output.
   - What's unclear: Should agents output full rewritten content, or structured feedback (issues/suggestions)?
   - Recommendation: Agents output structured feedback (`{"issues": [...], "suggestions": [...], "refined_fields": {...}}`). The merge call synthesizes these into the final output. This gives the merge call more control and avoids conflicting full rewrites.

3. **Confidence threshold for agent inclusion**
   - What we know: `AgentPipelineMap.confidence` stores a 0-1 score per mapping. Phase 8 will add `AGENT_RELEVANCE_THRESHOLD`.
   - What's unclear: Should Phase 5 already filter by confidence, or include all mapped agents?
   - Recommendation: Phase 5 includes all mapped agents. Phase 8 adds the threshold filter. This keeps Phase 5 simpler and avoids premature optimization.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` or pyproject.toml (existing) |
| Quick run command | `cd backend && python -m pytest app/tests/test_agent_review_middleware.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVW-01 | `review_step_output()` returns refined output when agents are mapped | unit | `pytest app/tests/test_agent_review_middleware.py::test_review_returns_refined_output -x` | -- Wave 0 |
| REVW-02 | Multiple agents review concurrently (session_factory called N times, sessions closed) | unit | `pytest app/tests/test_agent_review_middleware.py::test_parallel_fanout_uses_session_factory -x` | -- Wave 0 |
| REVW-03 | Merge AI call returns output matching wizard result JSON schema | unit | `pytest app/tests/test_agent_review_middleware.py::test_merge_preserves_wizard_schema -x` | -- Wave 0 |
| REVW-04 | Zero agents = pass-through, zero LLM calls | unit | `pytest app/tests/test_agent_review_middleware.py::test_zero_agents_passthrough -x` | -- Wave 0 |
| REVW-01 | Response includes `agents_consulted` metadata | unit | `pytest app/tests/test_agent_review_middleware.py::test_agents_consulted_metadata -x` | -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_agent_review_middleware.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_agent_review_middleware.py` -- covers REVW-01 through REVW-04
- [ ] No new framework install needed -- pytest and pytest-asyncio already present
- [ ] No new conftest fixtures needed -- existing `db_session`, `make_agent`, and mock patterns from `test_session_isolation.py` and `test_pipeline_composer.py` are sufficient

## Sources

### Primary (HIGH confidence)
- **Codebase inspection:** `backend/app/services/agent_service.py` -- SessionFactory pattern, run_multi_agent_review, _review_with_session
- **Codebase inspection:** `backend/app/services/pipeline_composer.py` -- AgentPipelineMap query patterns, compose_pipeline
- **Codebase inspection:** `backend/app/api/endpoints/wizards.py` -- wizard_generate/apply_wizard_result_to_db flow, injection point
- **Codebase inspection:** `backend/app/services/template_ai_service.py` -- wizard result schemas per wizard_type
- **Codebase inspection:** `backend/app/services/ai_provider.py` -- chat_completion interface, json_mode support
- **Codebase inspection:** `backend/app/models/database.py` -- AgentPipelineMap model, Agent model
- **Codebase inspection:** `backend/app/config.py` -- AGENT_REVIEW_TIMEOUT, MAX_TOKENS, MAX_AGENTS_PER_REVIEW settings
- **Codebase inspection:** `backend/app/tests/test_session_isolation.py` -- test patterns for session-per-task validation
- **Codebase inspection:** `backend/app/tests/test_pipeline_composer.py` -- test patterns for mocked AI calls

### Secondary (MEDIUM confidence)
- **STATE.md decisions:** "Build custom using only existing dependencies", "Session-per-task pattern required for asyncio.gather"
- **REQUIREMENTS.md:** REVW-01 through REVW-04 requirement definitions

### Tertiary (LOW confidence)
- None -- all findings are based on direct codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components exist in the codebase, no new dependencies
- Architecture: HIGH -- follows established patterns (singleton service, session-per-task, chat_completion)
- Pitfalls: HIGH -- identified from direct Phase 4 experience and codebase review
- Merge prompt engineering: MEDIUM -- requires iteration during implementation; schema shapes are known but optimal prompt wording needs testing

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependency changes expected)
