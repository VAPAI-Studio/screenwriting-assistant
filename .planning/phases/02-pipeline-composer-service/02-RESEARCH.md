# Phase 2: Pipeline Composer Service - Research

**Researched:** 2026-03-11
**Domain:** AI-driven pipeline composition -- mapping agents to template pipeline steps
**Confidence:** HIGH

## Summary

Phase 2 builds `pipeline_composer.py`, a service that uses AI (via the existing `ai_provider.chat_completion()`) to analyze all of a user's agents and map them to wizard-pattern subsections in the active template. The Phase 1 foundation is complete: the `AgentPipelineMap` ORM model, the migration (008), and the `PipelineMapEntry`/`PipelineMapResponse` Pydantic schemas all exist and are tested.

The core challenge is well-scoped: a single service module that (1) reads template JSON to discover wizard-pattern targets, (2) fetches all agents for an owner, (3) calls the AI with a structured prompt at `temperature=0`, (4) parses the JSON response into `AgentPipelineMap` rows, and (5) uses hash-based caching to avoid redundant AI calls. The dirty flag mechanism detects semantic agent changes and is handled in the agent CRUD layer (Phase 3 wires the trigger; Phase 2 builds the detection logic).

**Primary recommendation:** Follow the existing singleton service pattern (`pipeline_composer = PipelineComposer()`), use `hashlib.sha256` for the cache key, and keep the composition prompt lean -- agent fields + template step descriptions only.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Map agents to **generation-capable subsections only** -- those with `ui_pattern` containing "wizard" (wizard, wizard_with_chat)
- Target steps for short_movie template: `idea_wizard`, `scene_wizard`, `script_writer_wizard`
- **Exclude** `import_project` -- it's a utility/alignment step, not a creative generation step
- **Dynamic resolution**: composer reads template JSON at runtime, resolves `$ref` references, and extracts wizard-pattern subsections. Adapts automatically if templates change.
- Filter mechanism: use existing `ui_pattern` field (contains "wizard"), no new template schema flags needed
- **Single batch AI call** per composition: one prompt with ALL agents + ALL target steps. AI sees the full picture for intelligent distribution.
- **Cap at 5 agents per batch call**. If user has >5 agents, split into multiple batch calls.
- **Simple merge** across batches: concatenate results, no cross-batch reconciliation or deduplication needed
- AI response format: **flat list** of `{agent_id, phase, subsection_key, confidence, rationale}` tuples
- **Store all mappings** the AI returns, regardless of confidence score. Downstream consumers filter at read time.
- Confidence scale: **0.0 to 1.0** float
- **Rationale always required** for every mapping
- **Full replace** on each re-composition: delete all existing mappings for the owner, insert fresh results
- Include per-agent: **system_prompt_template + description + agent_type**
- Include per-step: **subsection name + description** from the template JSON
- **Do NOT include** book titles, tags, or personality in the mapping prompt
- Cache key: `hash(system_prompt_template + description + agent_type)` for all agents combined
- Dirty flag triggers on: `system_prompt_template`, `description`, **and** `agent_type` changes
- Cosmetic fields (name, color, icon) do NOT trigger re-composition

### Claude's Discretion
- Exact composition prompt engineering and structure
- Hash algorithm choice for cache key
- Error handling and retry logic for failed AI calls
- Logging strategy and observability

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | AI analyzes all agents and maps each to relevant pipeline steps when an agent is created, edited, or deleted | Core `compose_pipeline()` function; template discovery; AI prompt with JSON mode; batch splitting at 5 agents; full-replace write strategy |
| COMP-03 | Re-composition only triggers when semantic fields change (system prompt, type), not cosmetic fields (name, icon, color) | Hash-based cache key on `system_prompt_template + description + agent_type`; `_is_semantic_change()` helper; dirty flag detection logic |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib` (stdlib) | Python 3.11 | SHA-256 hash for cache key | Already used in `openai_service.py` and `embedding_service.py` with MD5; SHA-256 is more collision-resistant for combined multi-field hashing |
| `json` (stdlib) | Python 3.11 | Parse AI JSON responses, serialize cache data | Already used throughout services |
| `logging` (stdlib) | Python 3.11 | Service observability | Every existing service uses `logging.getLogger(__name__)` |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ai_provider.chat_completion()` | N/A (project module) | AI calls with `json_mode=True`, `temperature=0` | The single AI call entry point for composition |
| `get_template()` from `templates.registry` | N/A (project module) | Load template JSON with `$ref` resolution | Discover wizard-pattern subsections dynamically |
| SQLAlchemy ORM | Already in project | Read/write `AgentPipelineMap` and `Agent` models | All DB operations |
| Pydantic v2 | Already in project | Validate AI response via schemas | Parse/validate composition results |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SHA-256 | MD5 (existing pattern) | MD5 is faster but has higher collision risk; SHA-256 is negligible overhead for this use case and more robust. Either works. |
| In-memory dict cache | Redis / DB-stored cache | Overkill for MVP. In-memory cache per process is sufficient -- same pattern as `openai_service.py`. Pipeline data is already persisted in `agent_pipeline_maps` table. |

**Installation:**
```bash
# No new dependencies required -- everything is stdlib or already in the project
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
    pipeline_composer.py       # NEW: PipelineComposer class + singleton
backend/app/services/
    agent_service.py           # EXISTING: no changes in Phase 2
backend/app/models/
    database.py                # EXISTING: AgentPipelineMap already defined
    schemas.py                 # EXISTING: PipelineMapEntry/PipelineMapResponse already defined
backend/app/config.py          # ADD: PIPELINE_BATCH_SIZE setting
```

### Pattern 1: Singleton Service (follow existing convention)
**What:** Module-level singleton instance, same as `agent_service = AgentService()` and `openai_service = OpenAIService()`.
**When to use:** Always -- this is the project convention for stateful services.
**Example:**
```python
# backend/app/services/pipeline_composer.py
class PipelineComposer:
    def __init__(self):
        self._cache: Dict[str, List[Dict]] = {}  # hash -> composition result

    async def compose_pipeline(self, owner_id: UUID, db: Session) -> List[AgentPipelineMap]:
        ...

pipeline_composer = PipelineComposer()
```

### Pattern 2: Template Target Discovery
**What:** Read template JSON at runtime, filter subsections where `ui_pattern` contains "wizard", exclude `import_project`.
**When to use:** Every composition call, to dynamically adapt to template changes.
**Example:**
```python
def _get_wizard_targets(self, template_id: str = "short_movie") -> List[Dict]:
    """Extract generation-capable subsections from template."""
    template = get_template(template_id)
    targets = []
    for phase in template.get("phases", []):
        for sub in phase.get("subsections", []):
            if "wizard" in sub.get("ui_pattern", "") and sub["key"] != "import_project":
                targets.append({
                    "phase": phase["id"],
                    "subsection_key": sub["key"],
                    "name": sub["name"],
                    "description": sub.get("description", ""),
                })
    return targets
```

**Verified targets for `short_movie` template:**
| Phase | Subsection Key | Name | ui_pattern |
|-------|---------------|------|------------|
| idea | idea_wizard | Idea Wizard | wizard_with_chat |
| scenes | scene_wizard | Scene Wizard | wizard |
| write | script_writer_wizard | Script Writer Wizard | wizard |

Note: `import_project` has `ui_pattern: "import_wizard"` -- it DOES contain "wizard" but is explicitly excluded per user decision.

### Pattern 3: Hash-Based Cache Key
**What:** Concatenate all agents' semantic fields, hash with SHA-256 to produce a cache key. Skip AI call if cache hit.
**When to use:** Before every AI composition call.
**Example:**
```python
def _compute_cache_key(self, agents: List[Agent]) -> str:
    """Deterministic hash of all agents' semantic fields."""
    # Sort by agent ID for determinism
    sorted_agents = sorted(agents, key=lambda a: str(a.id))
    parts = []
    for agent in sorted_agents:
        parts.append(f"{agent.id}:{agent.system_prompt_template}:{agent.description or ''}:{agent.agent_type.value}")
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()
```

### Pattern 4: Full-Replace Write Strategy
**What:** Delete all existing mappings for the owner, insert fresh results from AI.
**When to use:** Every successful composition.
**Example:**
```python
# Inside compose_pipeline, after getting AI results:
db.query(AgentPipelineMap).filter(AgentPipelineMap.owner_id == owner_id).delete()
for entry in ai_results:
    db.add(AgentPipelineMap(
        owner_id=owner_id,
        agent_id=entry["agent_id"],
        phase=entry["phase"],
        subsection_key=entry["subsection_key"],
        confidence=entry["confidence"],
        rationale=entry["rationale"],
        pipeline_dirty=False,
    ))
db.commit()
```

### Pattern 5: Batch Splitting for >5 Agents
**What:** If user has more than 5 agents, split into batches of 5 and make separate AI calls. Merge results by concatenation.
**When to use:** Rare case -- most users will have fewer than 5 agents.
**Example:**
```python
BATCH_SIZE = 5  # from settings

async def _compose_batched(self, agents, targets):
    all_results = []
    for i in range(0, len(agents), BATCH_SIZE):
        batch = agents[i:i + BATCH_SIZE]
        results = await self._call_ai_composition(batch, targets)
        all_results.extend(results)
    return all_results
```

### Pattern 6: Semantic Change Detection
**What:** Compare incoming update fields against the semantic field set to determine if recomposition is needed.
**When to use:** In the agent CRUD layer (Phase 3 wires this; Phase 2 provides the helper).
**Example:**
```python
SEMANTIC_FIELDS = {"system_prompt_template", "description", "agent_type"}

def is_semantic_change(self, update_fields: Dict) -> bool:
    """Check if any updated fields are semantic (trigger recomposition)."""
    return bool(set(update_fields.keys()) & SEMANTIC_FIELDS)
```

### Anti-Patterns to Avoid
- **Streaming the composition call:** Composition uses `json_mode=True` which requires the full response. Do not use `chat_completion_stream()`.
- **Caching in the database:** The `agent_pipeline_maps` table IS the persistent cache. The in-memory hash cache just prevents redundant AI calls within the same process lifetime. Don't add a separate cache table.
- **Including all agent fields in the prompt:** Per user decision, only `system_prompt_template + description + agent_type` go into the prompt. Adding personality, books, or tags bloats the prompt without improving mapping quality.
- **Partial updates to mappings:** Always full-replace. Partial merge logic is complex and error-prone for something that costs one AI call.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON response parsing | Custom regex parser | `json.loads()` + Pydantic validation | AI returns JSON via `json_mode=True`; standard parsing handles it |
| Template discovery | Hardcoded list of wizard steps | `get_template()` + `ui_pattern` filter | Templates may change; dynamic discovery is future-proof |
| Cache invalidation | Custom timestamp/version tracking | Hash of semantic fields | Hash naturally invalidates when content changes |
| AI provider switching | Direct OpenAI/Anthropic calls | `chat_completion()` from `ai_provider.py` | Already abstracts both providers with `temperature` and `json_mode` params |

**Key insight:** The existing codebase already solves provider abstraction, template loading with `$ref` resolution, and JSON-mode AI calls. The composer is pure orchestration logic on top of these.

## Common Pitfalls

### Pitfall 1: Non-Deterministic AI Output Despite temperature=0
**What goes wrong:** Even at `temperature=0`, different AI providers may produce slightly different JSON key ordering or whitespace, breaking string-based equality checks.
**Why it happens:** `temperature=0` makes token selection deterministic, but doesn't guarantee byte-identical output across calls, especially with Anthropic vs OpenAI.
**How to avoid:** Parse JSON and compare structured data, never raw strings. The hash cache key is on INPUT (agent fields), not output. Success criterion SC2 ("identical output") should be validated at the parsed level (same agent_id/phase/subsection_key/confidence tuples), not raw string equality.
**Warning signs:** Tests comparing raw AI response strings.

### Pitfall 2: Agent ID Type Mismatch in AI Response
**What goes wrong:** AI returns `agent_id` as a string, but the DB model expects `UUID`. Or AI returns a hallucinated agent ID.
**Why it happens:** AI sees agent IDs in the prompt and may reformat them.
**How to avoid:** Validate AI-returned `agent_id` values against the set of actual agent IDs passed in. Convert strings to UUIDs explicitly. Discard any mappings with unknown agent IDs.
**Warning signs:** `DataError` or `IntegrityError` on insert.

### Pitfall 3: Empty Agent List Edge Case
**What goes wrong:** `compose_pipeline` called for a user with zero agents; code tries to build a prompt with no agents and gets unexpected AI response.
**Why it happens:** New users or users who deleted all agents.
**How to avoid:** Early return with empty result when `len(agents) == 0`. Delete any existing mappings (full replace with nothing). This is SC4.
**Warning signs:** AI error responses, empty prompt sections.

### Pitfall 4: Background Task DB Session Lifetime
**What goes wrong:** In Phase 3, `compose_pipeline` will be called via `BackgroundTasks`. The `db` session from `get_db()` may close before the background task finishes.
**Why it happens:** FastAPI's `get_db` generator closes after the response is sent. Background tasks run after.
**How to avoid:** Phase 2 should design `compose_pipeline` to accept an explicit `Session` parameter. The Phase 3 integration should create a fresh session inside the background task using `SessionLocal()` from `db.py`, not reuse the request session. Document this in the function docstring.
**Warning signs:** `DetachedInstanceError`, `InvalidRequestError: This session is closed`.

### Pitfall 5: import_project False Positive on "wizard" Filter
**What goes wrong:** `import_project` has `ui_pattern: "import_wizard"`, which contains "wizard", so it gets included as a target step.
**Why it happens:** Naive string matching on `ui_pattern`.
**How to avoid:** Explicitly exclude `import_project` by key, OR tighten the filter to only match `ui_pattern` values of exactly "wizard" or "wizard_with_chat". The user decision explicitly says to exclude `import_project`.
**Warning signs:** AI maps agents to `import_project` step.

### Pitfall 6: SQLAlchemy Bulk Delete + Insert in Same Transaction
**What goes wrong:** After `db.query(...).delete()`, new inserts in the same transaction may hit unique constraint violations if the delete hasn't been flushed.
**Why it happens:** SQLAlchemy's unit-of-work may not flush the delete before processing the inserts.
**How to avoid:** Call `db.flush()` after the delete, before the inserts. Or use `synchronize_session='fetch'` on the delete query.
**Warning signs:** `IntegrityError: duplicate key violates unique constraint "uq_pipeline_map_lookup"`.

## Code Examples

Verified patterns from the existing codebase:

### AI Call with JSON Mode (from template_ai_service.py / agent_service.py)
```python
# Source: backend/app/services/agent_service.py lines 300-308
text = await chat_completion(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0,        # Deterministic for composition
    max_tokens=settings.MAX_TOKENS,
    json_mode=True,       # Forces JSON response
)
result = json.loads(text)
```

### Template Loading with $ref Resolution (from templates/registry.py)
```python
# Source: backend/app/templates/registry.py
from ..templates import get_template

template = get_template("short_movie")
# Returns full dict with $ref phases resolved
# template["phases"][3] is write phase, fully expanded from shared/write_phase.json
```

### Singleton Service Pattern (from agent_service.py)
```python
# Source: backend/app/services/agent_service.py line 1066
class AgentService:
    ...

agent_service = AgentService()
```

### Hash-Based Caching (from openai_service.py)
```python
# Source: backend/app/services/openai_service.py lines 20-23
import hashlib
def _generate_cache_key(self, section_id: str, text: str, framework: str) -> str:
    content = f"{section_id}:{text}:{framework}"
    return hashlib.md5(content.encode()).hexdigest()
```

### Agent Query Pattern (from agent_service.py)
```python
# Source: backend/app/services/agent_service.py lines 628-635
specialist_agents = (
    db.query(Agent)
    .filter(
        (Agent.owner_id == owner_id) | (Agent.is_default == True),
        Agent.is_active == True,
        Agent.agent_type.in_([AgentType.BOOK_BASED, AgentType.TAG_BASED]),
    )
    .all()
)
```

### BackgroundTasks Pattern (from books.py)
```python
# Source: backend/app/api/endpoints/books.py lines 46, 86-90
from fastapi import BackgroundTasks

async def upload_book(
    background_tasks: BackgroundTasks,
    ...
    db: Session = Depends(get_db),
):
    ...
    background_tasks.add_task(
        book_processing_service.process_book,
        book.id,
        file_path,
        db,
    )
```

### Composition Prompt Design (Claude's Discretion)

The composition prompt should follow this structure:

```python
COMPOSITION_SYSTEM_PROMPT = """You are a pipeline composition engine for a screenwriting assistant.

Your task: analyze the user's AI agents and map each agent to the pipeline steps where it would be most relevant and helpful.

## Pipeline Steps (target steps for agent mapping)
{steps_section}

## Rules
- Map each agent to EVERY step where it has meaningful relevance (an agent CAN map to multiple steps)
- Assign a confidence score (0.0-1.0) for each mapping based on how relevant the agent is to that step
- Provide a brief rationale for each mapping
- Agent type is a hint, not a binding constraint -- judge by the agent's system prompt and description
- Return ALL plausible mappings; downstream consumers will filter by confidence threshold

## Required Output Format
Return a JSON object with a single key "mappings" containing a list of objects:
{{"mappings": [
  {{"agent_id": "<uuid>", "phase": "<phase_id>", "subsection_key": "<key>", "confidence": 0.85, "rationale": "Brief explanation"}}
]}}
"""

COMPOSITION_USER_PROMPT = """Map these agents to the pipeline steps:

## Agents
{agents_section}

Return the mappings JSON."""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded agent-to-step mapping | AI-inferred mapping via composition prompt | This phase | Agents automatically find their best fit without manual configuration |
| No pipeline awareness | Hash-cached, deterministic composition | This phase | Cost-efficient (one AI call per semantic change) and reproducible |

**Deprecated/outdated:**
- The `run_multi_agent_review` in `agent_service.py` has a known bug (shared DB session in `asyncio.gather`). Phase 4 addresses this. Phase 2 does NOT interact with this code.

## Open Questions

1. **AgentUpdate Schema Gap**
   - What we know: `AgentUpdate` currently includes `description` but NOT `system_prompt_template` or `agent_type`. So `system_prompt_template` and `agent_type` can only be set at creation time.
   - What's unclear: Should Phase 2 add these to `AgentUpdate`? Or should the dirty flag only trigger on create/delete plus `description` edits?
   - Recommendation: Phase 2 should build the `is_semantic_change()` helper to check all three fields. If `AgentUpdate` is expanded later (or in Phase 3), the logic is ready. For now, agent creation always triggers composition, agent deletion always triggers composition, and agent edits trigger only if `description` changes.

2. **Template ID Resolution**
   - What we know: Currently only `short_movie` template exists. The composer needs a `template_id` to call `get_template()`.
   - What's unclear: How does the composer know which template to use? Agents are per-owner, not per-project.
   - Recommendation: Hardcode `"short_movie"` for now (only template) with a TODO comment. When multi-template support arrives, the composer may need to compose per-template or use a default. This is a known simplification.

3. **Max Tokens for Composition Response**
   - What we know: With 5 agents and 3 target steps, the AI could return up to 15 mapping objects. Each is ~100 tokens. Total: ~1500 tokens.
   - What's unclear: Exact token budget needed.
   - Recommendation: Use `max_tokens=2000` (default in `chat_completion`) which provides comfortable headroom. Add a config setting `PIPELINE_COMPOSITION_MAX_TOKENS` for tunability.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | None -- pytest runs from `backend/` with `app/tests/` autodiscovery |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py -x` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | compose_pipeline produces agent_pipeline_maps rows for each agent-to-step pairing | unit (mock AI) | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_compose_produces_mappings -x` | No -- Wave 0 |
| COMP-01 | compose_pipeline handles zero agents without error | unit | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_compose_zero_agents -x` | No -- Wave 0 |
| COMP-01 | composition prompt embeds all wizard-pattern subsection_key values | unit | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_prompt_includes_all_wizard_targets -x` | No -- Wave 0 |
| COMP-01 | batch splitting works for >5 agents | unit (mock AI) | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_batch_splitting -x` | No -- Wave 0 |
| COMP-03 | identical agent descriptions produce identical output (cache hit) | unit (mock AI) | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_cache_hit_deterministic -x` | No -- Wave 0 |
| COMP-03 | cosmetic edit does NOT trigger recomposition | unit | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_cosmetic_change_no_recompose -x` | No -- Wave 0 |
| COMP-03 | semantic edit (description) DOES change cache key | unit | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py::test_semantic_change_invalidates_cache -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py -x`
- **Per wave merge:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_pipeline_composer.py` -- covers COMP-01, COMP-03 (all tests above)
- [ ] Mock fixture for `chat_completion` -- needed to test composition without live AI calls (similar to existing `mock_embed` fixture pattern in conftest.py)

## Sources

### Primary (HIGH confidence)
- `backend/app/models/database.py` -- AgentPipelineMap model definition (lines 434-455)
- `backend/app/models/schemas.py` -- PipelineMapEntry/PipelineMapResponse schemas (lines 610-633)
- `backend/app/services/ai_provider.py` -- `chat_completion()` API (lines 36-58)
- `backend/app/templates/registry.py` -- `get_template()` with `$ref` resolution (lines 30-40)
- `backend/app/templates/short_movie.json` -- template structure showing wizard subsections
- `backend/app/templates/shared/write_phase.json` -- script_writer_wizard definition
- `backend/app/services/agent_service.py` -- singleton pattern, agent query patterns
- `backend/app/services/openai_service.py` -- hash-based cache pattern (lines 17-23)
- `backend/app/config.py` -- Settings class pattern
- `backend/app/db.py` -- `SessionLocal` for background task sessions
- `backend/app/api/endpoints/agents.py` -- current agent CRUD (no dirty flag yet)
- `backend/app/tests/conftest.py` -- test infrastructure (SQLite, fixtures)
- `backend/app/tests/test_pipeline_map_schema.py` -- existing Phase 1 tests
- `backend/migrations/008_agent_pipeline_maps.sql` -- DB schema with indexes

### Secondary (MEDIUM confidence)
- None needed -- all research is from first-party codebase sources

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns verified in existing codebase
- Architecture: HIGH -- clear singleton service pattern, all integration points verified with code
- Pitfalls: HIGH -- identified from actual codebase patterns (BackgroundTasks session issue, import_project filter, SQLAlchemy flush ordering)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no external dependencies to drift)
