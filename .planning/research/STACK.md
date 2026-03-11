# Technology Stack

**Project:** Agent Orchestration Pipeline — Screenwriting Assistant
**Researched:** 2026-03-11
**Confidence:** MEDIUM (training data only — external web tools unavailable during research session; codebase analysis is HIGH confidence)

---

## Core Verdict: Build Custom, Not Framework

**Do not adopt LangGraph, CrewAI, or AutoGen.** The existing codebase already has 80% of what is needed for the orchestration pipeline. The missing 20% is a pipeline mapping table, an orchestrator inference call, and wiring `asyncio.gather` into the generation path. Introducing a framework adds dependency weight, abstraction mismatch with the existing `ai_provider.py`, and a migration cost that exceeds the benefit for this specific use case.

**The use case is narrow and well-defined:**
- One AI call maps agents to pipeline steps (on CRUD)
- During generation, N agent review calls fire in parallel via `asyncio.gather`
- One AI call merges the N reviews into refined output
- Results are stored in PostgreSQL; tree view renders from stored mapping

This is a fan-out/fan-in pattern with two AI calls per step. That is not a complex graph. LangGraph's value is in cyclical, conditional graphs with state machines. CrewAI's value is in autonomous role-based task decomposition. AutoGen's value is in multi-turn agent-to-agent conversation. None of these match what is being built.

---

## Recommended Stack

### Orchestration Core

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python `asyncio` | stdlib (3.11) | Parallel agent review calls | Already used in `agent_service.py` (`asyncio.gather`, `asyncio.wait_for`). Zero new dependencies. Correct primitive for I/O-bound parallel LLM calls. |
| `asyncio.gather` with `return_exceptions=True` | stdlib | Fan-out N agent reviews per pipeline step | Pattern already proven in `AgentService.run_multi_agent_review()` and `_orchestrate_stream_prepare()`. Extend, don't replace. |
| `asyncio.wait_for` with timeout | stdlib | Per-agent timeout guard | Already in `run_multi_agent_review()` with `settings.AGENT_REVIEW_TIMEOUT` (90s). Keep as-is. |

**Confidence:** HIGH — pattern already present and working in `backend/app/services/agent_service.py` lines 1027-1063.

### Pipeline Mapping Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL 15 (existing) | 15 | Store agent-to-pipeline-step mapping | Mapping is pre-computed on agent CRUD. Persisting as a JSON column on a new `PipelineMapping` table avoids recomputing at generation time. Fits existing SQLAlchemy ORM pattern. |
| SQLAlchemy 2.0.27 (existing) | 2.0.27 | ORM model for `PipelineMapping` table | Already the ORM in use. New table follows exact pattern of existing models (`Agent`, `PhaseData`). |

**New table needed:** `pipeline_mappings` — one row per agent (or per owner, storing the full tree), with a `mapping` JSON column. See Architecture section below.

**Confidence:** HIGH — fits existing data model patterns exactly.

### Orchestrator Inference (Mapping Generation)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Existing `ai_provider.chat_completion()` | current | AI call that maps agents to pipeline steps | The existing provider abstraction already works with both OpenAI and Anthropic. The orchestrator mapping call is a single structured JSON-mode completion: given all agents + all template phases, return the mapping. No new AI client needed. |

**The mapping prompt pattern:**
```python
await chat_completion(
    messages=[
        {"role": "system", "content": ORCHESTRATOR_MAPPING_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({
            "agents": [agent_summary for agent in agents],
            "pipeline_steps": [step_summary for step in template_phases],
        })}
    ],
    json_mode=True,
    temperature=0.2,  # Low temp for deterministic mapping
    max_tokens=2000,
)
```

**Confidence:** HIGH — `chat_completion` with `json_mode=True` is already used extensively in `template_ai_service.py`.

### Merge / Synthesis Call

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Existing `ai_provider.chat_completion()` | current | Merge N agent reviews into refined output | Same provider abstraction. After `asyncio.gather` collects all agent reviews, one synthesis call combines them. This is already done conceptually in `_orchestrate` for chat — extend the same pattern to generation. |

**Confidence:** HIGH.

### Background Task Execution (Pipeline Re-composition on CRUD)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI `BackgroundTasks` | FastAPI 0.110.0 (existing) | Trigger pipeline re-mapping after agent create/edit/delete without blocking the HTTP response | Already available in the FastAPI version in use. No new dependency. Agent CRUD endpoints return immediately; mapping computation runs in background. |

**Rationale:** Pipeline re-mapping on agent CRUD takes 1-3 seconds (one AI call). The user should not wait for this on their create/edit request. `BackgroundTasks` is the correct FastAPI primitive — it runs after the response is sent, in the same worker process, with access to the DB session factory. This is appropriate for short tasks (< 30 seconds). Do not use Celery or a task queue for this scale.

**Confidence:** HIGH — FastAPI `BackgroundTasks` is well-documented for exactly this pattern.

### Frontend Tree View

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React 18.2 (existing) | 18.2 | Tree view component for pipeline mapping | No new UI library needed. The collapsible tree is a straightforward recursive component using existing Tailwind + Lucide icons. `ChevronDown`/`ChevronRight` from Lucide (already installed, 0.314) handle expand/collapse. |
| React Query v5.20 (existing) | 5.20 | Fetch and cache the pipeline mapping | `useQuery` on `GET /api/pipeline/mapping` follows existing pattern. Invalidate on agent CRUD mutations. |
| Tailwind CSS 3.4 (existing) | 3.4 | Tree styling | Indentation levels via `pl-4`, `pl-8` etc. No new CSS library needed. |

**Confidence:** HIGH — all dependencies already installed.

---

## What NOT to Use

### LangGraph

**Do not use.** LangGraph (LangChain's graph execution framework) is built for stateful, cyclical agent graphs — loops, conditional branching, human-in-the-loop checkpoints. This project's pipeline is:

1. Mapping step: one LLM call, deterministic output stored in DB.
2. Review step: N parallel LLM calls + one merge call.

Neither step requires a state machine. LangGraph would add `langgraph`, `langchain-core`, and `langchain-community` as dependencies — a large surface area that conflicts with the intentional `ai_provider.py` abstraction. The abstraction exists precisely to avoid LangChain lock-in.

**Confidence:** HIGH — LangGraph's own docs describe it as for "stateful, multi-actor applications with cycles." This use case has no cycles.

### CrewAI

**Do not use.** CrewAI abstracts agents as autonomous role-playing entities that decompose tasks and communicate with each other. The project spec explicitly states: "Agent-to-agent communication is out of scope — agents review independently, don't talk to each other." CrewAI's architecture is built around exactly this communication pattern. Using CrewAI here would mean adopting its agent execution model while suppressing its primary feature.

Additionally, CrewAI wraps OpenAI/Anthropic clients in its own way, which would conflict with `ai_provider.py`.

**Confidence:** MEDIUM — based on training data understanding of CrewAI's design; unable to verify current CrewAI version docs.

### AutoGen (Microsoft)

**Do not use.** AutoGen is designed for conversational multi-agent systems where agents send messages to each other over multiple turns. This is a review pipeline with no conversation between agents. AutoGen's overhead — its GroupChat, ConversableAgent, and runtime concepts — is architectural overkill.

**Confidence:** MEDIUM — training data only; unable to verify against current AutoGen docs.

### Celery / Redis / Task Queues

**Do not use for this milestone.** Celery requires Redis or RabbitMQ as a broker, a separate worker process, and infrastructure changes to Docker Compose. For pipeline re-composition (one short AI call triggered on CRUD), FastAPI `BackgroundTasks` is sufficient. Celery becomes worth considering if background tasks exceed 60 seconds, need retry logic across process restarts, or need to scale to many concurrent users. None of those conditions apply to this milestone.

**Confidence:** HIGH.

### Server-Sent Events (SSE) for Pipeline Mapping Progress

**Do not add.** Pipeline re-mapping is fast (1-3 seconds, one AI call). The frontend should poll `GET /api/pipeline/mapping` with React Query's `refetchInterval` for 5-10 seconds after a mutation, then stop. SSE adds streaming infrastructure for a sub-5-second operation.

**Confidence:** HIGH.

---

## Supporting Libraries (New)

No new Python packages are needed for the backend orchestration logic. All required capabilities exist in the current stack.

For the frontend, no new npm packages are needed. The tree view uses existing Lucide icons and Tailwind utilities.

### Optional — If background tasks become unreliable

If `BackgroundTasks` proves insufficient (e.g., the mapping AI call starts timing out under load, or the server restarts mid-computation), the upgrade path is:

| Library | Version | Why then |
|---------|---------|---------|
| `anyio` task groups | stdlib via anyio (FastAPI already uses anyio internally) | Structured concurrency for background tasks without Celery |

Do not add this preemptively.

---

## Integration Points with Existing Code

### What Already Exists (Do Not Rewrite)

| Existing Component | How It's Reused |
|-------------------|-----------------|
| `AgentService.run_multi_agent_review()` | Direct call — already does `asyncio.gather` over agents with timeout. Extend signature to accept `pipeline_step` context. |
| `AgentService._orchestrate_stream_prepare()` | Pattern source — shows how to fan-out to agents and collect results. |
| `ai_provider.chat_completion(json_mode=True)` | Used for both the mapping call and the synthesis/merge call. |
| `Agent` SQLAlchemy model | Read-only in pipeline mapping — no changes to existing model needed. |
| `PhaseData` + `ListItem` | Pipeline steps map to existing phases + subsection keys from template config. |
| FastAPI `BackgroundTasks` | Wire into `POST /api/agents/` and `PATCH /api/agents/{id}` and `DELETE /api/agents/{id}`. |
| React Query invalidation pattern | After agent CRUD mutation, invalidate `QUERY_KEYS.PIPELINE_MAPPING`. |

### What Needs to Be Added

| New Component | Location | Purpose |
|--------------|----------|---------|
| `PipelineMapping` SQLAlchemy model | `backend/app/models/database.py` | Persist the computed agent-to-step mapping |
| `pipeline_mapping_service.py` | `backend/app/services/` | `compute_mapping(owner_id, db)` and `get_mapping(owner_id, db)` |
| `GET/POST /api/pipeline/mapping` | `backend/app/api/endpoints/pipeline.py` | Expose mapping to frontend, trigger recompute |
| `PipelineMappingTree.tsx` | `frontend/src/components/Workspace/` | Collapsible tree view for pipeline mapping |
| Migration SQL | `backend/migrations/` | `pipeline_mappings` table |

---

## Data Schema Recommendation

### `pipeline_mappings` Table

```sql
CREATE TABLE pipeline_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    template_id VARCHAR(100) NOT NULL,
    mapping JSONB NOT NULL DEFAULT '{}',
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE (owner_id, template_id)
);
```

**`mapping` JSON shape:**
```json
{
  "phases": {
    "idea": {
      "subsections": {
        "idea_overview": {
          "agents": [
            {
              "agent_id": "uuid",
              "agent_name": "Story Structure Coach",
              "agent_color": "#6366f1",
              "rationale": "Matches because agent's prompt focuses on story concept development"
            }
          ]
        }
      }
    },
    "story": {
      "subsections": {
        "beats": {
          "agents": [...]
        }
      }
    }
  }
}
```

This shape mirrors the existing template phase/subsection hierarchy, making tree rendering trivial — iterate `mapping.phases`, then `subsections`, then `agents`.

---

## Generation Integration Pattern

The pipeline review injection into `template_ai_service.py` generation follows this pattern:

```python
# In TemplateAIService (or a new PipelineAwareGenerationService)

async def generate_with_agent_review(
    self,
    step_output: str,
    phase: str,
    subsection_key: str,
    owner_id: UUID,
    db: Session,
) -> str:
    """Inject agent reviews after a generation step."""
    # 1. Get mapped agents for this step
    mapping = pipeline_mapping_service.get_mapping(owner_id, db)
    agents = mapping.get_agents_for_step(phase, subsection_key)

    if not agents:
        return step_output  # No agents mapped — pass through unchanged

    # 2. Fan-out: run all mapped agents in parallel
    tasks = [
        asyncio.wait_for(
            self._run_agent_review(agent, step_output, phase, subsection_key, db),
            timeout=settings.AGENT_REVIEW_TIMEOUT,
        )
        for agent in agents
    ]
    reviews = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Filter out errors
    valid_reviews = [r for r in reviews if not isinstance(r, Exception)]
    if not valid_reviews:
        return step_output

    # 4. Fan-in: one synthesis call to merge feedback
    refined = await self._merge_reviews(step_output, valid_reviews)
    return refined
```

This keeps `TemplateAIService` as the generation coordinator. No new service class needed — extend the existing one.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Orchestration approach | Custom `asyncio.gather` | LangGraph | No graph cycles needed; adds LangChain dependency surface; conflicts with `ai_provider.py` abstraction |
| Orchestration approach | Custom `asyncio.gather` | CrewAI | Designed for agent-to-agent comms which is explicitly out of scope; own AI client wrapping conflicts |
| Background tasks | FastAPI `BackgroundTasks` | Celery + Redis | Requires broker infrastructure; overkill for 1-3 second tasks |
| Mapping storage | PostgreSQL JSONB column | Separate graph database (Neo4j) | The mapping is a simple tree, not a property graph; Neo4j is unjustified complexity |
| Tree view | Custom Tailwind component | react-arborist or react-d3-tree | Small component; adding a tree library for a collapsible list is excess dependency |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Build custom vs. frameworks | HIGH | Codebase analysis is conclusive — existing patterns already cover the core need |
| `asyncio.gather` fan-out pattern | HIGH | Already in production use in `agent_service.py` lines 649-653 and 843-847 |
| FastAPI `BackgroundTasks` suitability | HIGH | Standard FastAPI pattern, well-documented |
| LangGraph unsuitability | HIGH | Design mismatch is structural, not opinion |
| CrewAI unsuitability | MEDIUM | Training data only; could not verify current CrewAI API surface |
| AutoGen unsuitability | MEDIUM | Training data only; could not verify current AutoGen API surface |
| `PipelineMapping` JSONB schema | MEDIUM | Logical fit with existing models; schema may need adjustment once template structure is fully enumerated |
| Library versions (frameworks) | LOW | Could not fetch current PyPI versions — verify before pinning |

---

## Installation

No new Python packages are required for this milestone. The full stack is already installed.

If you later choose to add structured retry logic:

```bash
# Only if needed — do not add preemptively
pip install tenacity==8.2.3
```

`tenacity` provides `@retry` decorators for AI call retries with exponential backoff. Useful if agent review calls show transient failures in production. Do not pin it now.

---

## Sources

- Codebase analysis: `backend/app/services/agent_service.py` (lines 1027-1063, 649-653, 843-847) — HIGH confidence
- Codebase analysis: `backend/app/services/ai_provider.py` — HIGH confidence
- Codebase analysis: `backend/app/models/database.py` (Agent, PhaseData models) — HIGH confidence
- Codebase analysis: `backend/requirements.txt` — HIGH confidence
- FastAPI BackgroundTasks documentation (training data, pattern is stable) — HIGH confidence
- LangGraph design rationale (training data, cyclical graph focus) — MEDIUM confidence
- CrewAI design rationale (training data) — MEDIUM confidence
- AutoGen design rationale (training data) — MEDIUM confidence

*Stack research: 2026-03-11*
