# Architecture Patterns

**Domain:** Agent Orchestration Pipeline — integrating active agent reviews into existing template-based screenplay generation
**Researched:** 2026-03-11

---

## Existing Architecture (What We're Adding To)

The codebase has a clear layered backend with two parallel AI subsystems that the new pipeline must bridge:

**Subsystem A — Template Generation** (`template_ai_service.py` + `wizards.py`)
- Stateless: takes project context as a string, sends a prompt to `ai_provider.chat_completion()`, returns structured JSON
- No agent awareness — completely decoupled from the Agent model
- Entry point: `POST /api/wizards/run` → `WizardRun` record → `template_ai_service.wizard_generate()`
- Output persisted as `ListItem` rows (scenes), `PhaseData.content` (ideas, fields), or `ScreenplayContent` rows (scripts)

**Subsystem B — Agent Chat** (`agent_service.py` + `ai_chat.py`)
- Stateful: requires a `ChatSession` + `Agent` + project ownership
- RAG-aware: fetches concepts/chunks from `rag_service` before each call
- Entry point: `POST /api/ai/sessions/{id}/messages` → `agent_service.chat_stream_prepare()` → streaming response
- Has `run_multi_agent_review()` already built — runs agents in parallel via `asyncio.gather()`

**The Gap:** These two subsystems never talk to each other. Template generation produces output; agents sit idle. The orchestration pipeline connects them: when Subsystem A generates content, Subsystem B reviews and refines it.

---

## Recommended Architecture

The pipeline adds three new components to the existing service layer, with one new DB table and minimal changes to existing code:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Existing: Agent CRUD                                                │
│ POST/PATCH/DELETE /api/agents/{id}                                  │
│           │                                                         │
│           ▼  (on every create/edit/delete)                          │
│  ┌─────────────────────────────┐                                    │
│  │  NEW: PipelineComposer      │  ← Component 1                     │
│  │  pipeline_composer.py       │                                    │
│  │                             │                                    │
│  │  Input:  All active agents  │                                    │
│  │          + template phases  │                                    │
│  │  Output: AgentPipelineMap   │  ← New DB table                   │
│  │          (agent_id, phase,  │                                    │
│  │           subsection_key,   │                                    │
│  │           confidence_score) │                                    │
│  └─────────────────────────────┘                                    │
│                                                                     │
│ Existing: Template Generation                                       │
│ POST /api/wizards/run → template_ai_service.wizard_generate()       │
│           │                                                         │
│           ▼  (after generation, before DB persist)                  │
│  ┌─────────────────────────────┐                                    │
│  │  NEW: AgentReviewMiddleware │  ← Component 2                     │
│  │  agent_review_middleware.py │                                    │
│  │                             │                                    │
│  │  1. Look up AgentPipelineMap│                                    │
│  │     for this phase/subsect  │                                    │
│  │  2. Run mapped agents in    │                                    │
│  │     parallel (asyncio)      │                                    │
│  │  3. Merge feedback into     │                                    │
│  │     refined output          │                                    │
│  └─────────────────────────────┘                                    │
│           │                                                         │
│           ▼                                                         │
│ Existing: DB Persist (ListItem / PhaseData / ScreenplayContent)     │
│                                                                     │
│ NEW: Pipeline Map API                                               │
│ GET /api/agents/pipeline-map?owner_id=...                           │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────────────────────────┐                          │
│  │  NEW: PipelineTreeView (Frontend)    │  ← Component 3            │
│  │  frontend/src/components/            │                           │
│  │  Books/AgentPipelineTree.tsx         │                           │
│  │                                      │                           │
│  │  Collapsible tree: Phase > Step >    │                           │
│  │  Agent badges with confidence        │                           │
│  └──────────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### Component 1: PipelineComposer (`pipeline_composer.py`)

**Responsibility:** AI-driven mapping of agents to pipeline steps. Runs asynchronously after agent CRUD.

**Inputs:**
- All active agents for the user (from `Agent` table — `name`, `description`, `system_prompt_template`, `agent_type`, `tags_filter`)
- Template phase/subsection definitions (from `get_template()` — `phase`, `subsection_key`, `label`, description)
- Owner ID (for multi-tenant isolation)

**Outputs:**
- Upserts `AgentPipelineMap` rows in PostgreSQL (one row per agent-step pair)
- Returns serialized pipeline map as `Dict[str, List[AgentMapping]]` keyed by `"{phase}.{subsection_key}"`

**Communicates with:**
- `Agent` model (reads)
- `AgentPipelineMap` model (writes)
- `ai_provider.chat_completion()` (one call to map all agents to all steps)
- `get_template()` (reads template config)

**Trigger:** Called from `agents.py` endpoint after create/update/delete — as a background task via `BackgroundTasks` (FastAPI), not blocking the HTTP response.

**Key Design Decision:** One AI call maps ALL agents to ALL steps simultaneously (not per-agent). The prompt gives the AI the full agent roster and all pipeline steps and asks it to produce a JSON mapping. This is more token-efficient than N calls.

---

### Component 2: AgentReviewMiddleware (`agent_review_middleware.py`)

**Responsibility:** Intercept generation output, run parallel agent reviews, merge feedback into refined content. This is not HTTP middleware — it is a service-layer function called explicitly from the wizard endpoint.

**Inputs:**
- `project_id` — to look up `AgentPipelineMap` and load project context
- `phase` + `subsection_key` — to find mapped agents for this step
- `generated_content: Dict` — the raw output from `template_ai_service`
- `owner_id` — for agent ownership filtering
- `db: Session`

**Outputs:**
- `refined_content: Dict` — same shape as `generated_content`, with agent-suggested improvements applied
- `agent_reviews: List[Dict]` — metadata about which agents ran (for frontend display, stored in `WizardRun.result`)

**Communicates with:**
- `AgentPipelineMap` model (reads — which agents map to this step)
- `agent_service.run_multi_agent_review()` (already exists — runs agents in parallel)
- `ai_provider.chat_completion()` (one additional AI call to merge feedback)
- `template_ai_service` (does NOT call back — receives output from it)

**Integration Point:** Called from `wizards.py` `run_wizard()` between `wizard_generate()` and the DB persist step. The existing `apply_wizard_result_to_db()` function receives the refined output.

**Bypass Condition:** If no agents are mapped to the current step, the function returns the original content unchanged with zero latency overhead.

---

### Component 3: AgentPipelineTree (`AgentPipelineTree.tsx`)

**Responsibility:** Read-only collapsible tree showing which agents activate at which pipeline steps.

**Inputs:**
- `GET /api/agents/pipeline-map` response — nested structure of phases → steps → agents
- Agent data from `QUERY_KEYS.AGENTS` (for color/icon display)

**Outputs:** Visual tree in the existing `AgentManager` page (or as a tab/section within it)

**Communicates with:**
- Backend `GET /api/agents/pipeline-map` (new endpoint)
- React Query cache via `QUERY_KEYS.PIPELINE_MAP`
- `AgentManager.tsx` parent component (embedded or co-located)

---

## New Data Model: AgentPipelineMap

```sql
CREATE TABLE agent_pipeline_maps (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    UUID NOT NULL,
    agent_id    UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    phase       VARCHAR(50) NOT NULL,       -- e.g. "idea", "story", "scenes", "write"
    subsection_key VARCHAR(100) NOT NULL,   -- e.g. "scene_list", "idea_wizard"
    confidence  FLOAT NOT NULL DEFAULT 0.0, -- 0.0 to 1.0, from AI mapping call
    rationale   TEXT,                       -- AI explanation for this mapping
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (owner_id, agent_id, phase, subsection_key)
);

CREATE INDEX idx_pipeline_map_lookup
    ON agent_pipeline_maps (owner_id, phase, subsection_key);
```

**Why a dedicated table over JSON on Agent:** Enables efficient lookup by `(owner_id, phase, subsection_key)` at generation time without loading all agents. Also allows per-mapping confidence scores and rationale.

**Cascade delete:** `ON DELETE CASCADE` from `agents.id` ensures maps are cleaned up when an agent is deleted. Re-composition runs after delete to update remaining mappings.

---

## Data Flow

### Flow 1: Agent Created/Updated (Pipeline Composition)

```
User creates agent in AgentManager.tsx
    → POST /api/agents/ (agents.py)
    → Agent row inserted in DB
    → HTTP 200 returned immediately
    → BackgroundTasks: pipeline_composer.recompose(owner_id, db)
        → Fetch all active agents for owner
        → Fetch template phase/subsection definitions
        → One AI call: "Map these agents to these steps"
        → Upsert AgentPipelineMap rows
    (Background completes ~2-5s later)
```

### Flow 2: Generation with Agent Review (Both Manual and YOLO)

```
User triggers wizard (e.g. scene_wizard)
    → POST /api/wizards/run (wizards.py)
    → WizardRun record created (status: "running")
    → template_ai_service.wizard_generate() called
        → Returns generated_content (e.g. {scenes: [...]})
    → agent_review_middleware.review_and_refine() called    ← NEW
        → AgentPipelineMap lookup: agents for (owner_id, phase, subsection_key)
        → If no agents mapped: return generated_content unchanged
        → asyncio.gather: run_multi_agent_review for each mapped agent
            → Each agent: RAG fetch → prompt build → ai_provider.chat_completion()
        → Merge AI call: "Given original output + agent feedback, produce refined output"
        → Returns (refined_content, agent_reviews)
    → WizardRun.result = {**refined_content, "agent_reviews": agent_reviews}
    → WizardRun.status = "completed"
    → apply_wizard_result_to_db() receives refined_content (unchanged interface)
```

### Flow 3: Pipeline Map Display

```
User opens AgentManager or dedicated Pipeline tab
    → GET /api/agents/pipeline-map (new endpoint)
    → Queries AgentPipelineMap grouped by phase/subsection_key
    → Returns: { "scenes.scene_list": [{agent_id, name, color, confidence, rationale}], ... }
    → React Query caches under QUERY_KEYS.PIPELINE_MAP
    → AgentPipelineTree renders collapsible tree
        → Phase nodes (idea, story, scenes, write)
        → Step nodes (subsection_key labels)
        → Agent leaf nodes (color dot, name, confidence badge)
```

### Flow 4: Agent Deleted (Pipeline Recomposition)

```
User deletes agent
    → DELETE /api/agents/{id}
    → Agent soft-deleted or hard-deleted
    → CASCADE deletes AgentPipelineMap rows for this agent
    → BackgroundTasks: pipeline_composer.recompose(owner_id, db)
        → Re-maps remaining agents
        → Upserts AgentPipelineMap (remaining agents may shift)
```

---

## Patterns to Follow

### Pattern 1: Background Recomposition via FastAPI BackgroundTasks

Use `BackgroundTasks` (built into FastAPI, no Celery needed) to run pipeline composition without blocking the CRUD response.

```python
from fastapi import BackgroundTasks

@router.post("/")
async def create_agent(
    agent_data: schemas.AgentCreate,
    background_tasks: BackgroundTasks,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = Agent(owner_id=current_user.id, ...)
    db.add(agent)
    db.commit()

    background_tasks.add_task(
        pipeline_composer.recompose,
        owner_id=current_user.id,
    )
    return agent
```

**Why BackgroundTasks over Celery:** No new infrastructure. The composition task is fast (one AI call, ~2s). BackgroundTasks runs in the same process after the response is sent.

**Limitation:** If the server restarts during a background task, the recomposition is lost. Acceptable for MVP — the next agent CRUD or a manual refresh endpoint will trigger recomposition.

---

### Pattern 2: Merge-Not-Chain for Agent Feedback

After parallel agent reviews, use a single merge AI call rather than chaining agent outputs sequentially.

```python
async def _merge_feedback(
    original_content: Dict,
    agent_reviews: List[Dict],
    step_context: str,
) -> Dict:
    """Merge parallel agent feedback into refined content."""
    reviews_text = "\n\n".join(
        f"## {r['agent_name']}\n"
        f"Issues: {r.get('issues', [])}\n"
        f"Suggestions: {r.get('suggestions', [])}"
        for r in agent_reviews if r.get("status") == "completed"
    )
    # One AI call: original + all feedback → refined output
    return await chat_completion(
        messages=[...],
        json_mode=True,
    )
```

**Why:** Sequential chaining (agent A refines → agent B refines agent A's output) compounds each agent's bias. Parallel reviews + single merge preserves independence while still synthesizing all perspectives.

---

### Pattern 3: Backward-Compatible Middleware Injection

The `review_and_refine()` function wraps generation output without changing the `apply_wizard_result_to_db()` interface.

```python
# wizards.py — minimal change to existing code
result = await template_ai_service.wizard_generate(...)

# NEW: inject review pass (no-op if no agents mapped)
result, agent_reviews = await agent_review_middleware.review_and_refine(
    project_id=project.id,
    owner_id=current_user.id,
    phase=request.phase,
    subsection_key=...,  # derived from wizard_type
    generated_content=result,
    db=db,
)

# Existing: unchanged
wizard_run.result = {**result, "agent_reviews": agent_reviews}
apply_wizard_result_to_db(db, project, phase, wizard_type, result)
```

**Why:** Existing wizard behavior is preserved if zero agents are mapped. `apply_wizard_result_to_db()` receives the same content shape regardless of whether review ran.

---

### Pattern 4: Confidence Threshold Filtering

Only agents with `confidence >= threshold` (recommend 0.5) activate for a given step. Store confidence in `AgentPipelineMap`, filter at lookup time.

```python
mapped_agents = db.query(AgentPipelineMap).filter(
    AgentPipelineMap.owner_id == owner_id,
    AgentPipelineMap.phase == phase,
    AgentPipelineMap.subsection_key == subsection_key,
    AgentPipelineMap.confidence >= settings.PIPELINE_CONFIDENCE_THRESHOLD,
).all()
```

**Why:** Prevents noisy agents (low confidence) from adding latency and degrading output quality. Threshold is a config value, not hardcoded.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous Composition on Every CRUD

**What:** Run `pipeline_composer.recompose()` synchronously within the HTTP request handler.

**Why bad:** Composition requires one AI API call (~1-3s latency). The agent CRUD response would stall while waiting. User experience degrades to "agent creation feels slow."

**Instead:** Use `BackgroundTasks`. Return the HTTP response immediately, compose in background. Pipeline map may be stale for ~3s — acceptable for an informational UI.

---

### Anti-Pattern 2: Per-Step Composition at Generation Time

**What:** Run composition at generation time ("which agents should review this step?") rather than pre-computing on agent CRUD.

**Why bad:** Adds 1 AI call latency to every generation step. YOLO generation chains many steps — this compounds into N extra AI calls per run.

**Instead:** Pre-compute mappings when agents change. Look up from DB at generation time (fast index scan, not an AI call).

---

### Anti-Pattern 3: Sequential Agent Review Chain

**What:** Review agent 1 → feed output to agent 2 → feed to agent 3 → final output.

**Why bad:** Each agent reviews the previous agent's modifications, not the original content. Agents compound each other's stylistic biases. Latency scales linearly with agent count instead of being bounded by the slowest single agent.

**Instead:** All mapped agents review the original generated content in parallel (`asyncio.gather`). One AI merge call synthesizes all feedback. Total latency = max(single agent time) + merge time.

---

### Anti-Pattern 4: Mutating `template_ai_service` Directly

**What:** Add agent review logic directly inside `template_ai_service.py` methods.

**Why bad:** Merges two concerns (content generation and quality review) into a single service. Makes testing harder. Future changes to agent routing affect generation logic.

**Instead:** Implement `agent_review_middleware.py` as a separate service that the wizard endpoint calls. `TemplateAIService` stays stateless and agent-unaware.

---

### Anti-Pattern 5: Storing Pipeline Map in Agent.metadata

**What:** Store step mappings as a JSON column on `Agent` rather than a separate table.

**Why bad:** Cannot efficiently query "which agents map to phase=scenes, step=scene_list" without loading all agents. No per-mapping confidence scores or rationale. Deleting a step from a phase requires scanning all agents.

**Instead:** Dedicated `agent_pipeline_maps` table with `(owner_id, phase, subsection_key)` index for O(1) lookup.

---

## Component Build Order (Dependencies)

The components have explicit build dependencies. Build in this order:

```
Phase 1: Data Foundation
├── DB migration: agent_pipeline_maps table
├── SQLAlchemy model: AgentPipelineMap
└── Pydantic schema: PipelineMapRead, PipelineMapEntry

Phase 2: Backend Pipeline Core
├── pipeline_composer.py (depends on: AgentPipelineMap model, get_template, ai_provider)
├── Update agents.py CRUD endpoints (add BackgroundTasks trigger)
└── GET /api/agents/pipeline-map endpoint

Phase 3: Review Integration
├── agent_review_middleware.py
│   (depends on: AgentPipelineMap, agent_service.run_multi_agent_review, ai_provider)
└── Update wizards.py to call review_and_refine() after wizard_generate()

Phase 4: Frontend Tree
├── api.tsx: add getPipelineMap()
├── constants.ts: add QUERY_KEYS.PIPELINE_MAP
└── AgentPipelineTree.tsx component
    └── Wire into AgentManager.tsx (new tab or accordion section)
```

**Dependency rationale:**
- The DB table must exist before any service code that writes to it
- `pipeline_composer.py` must exist and be tested before wiring into agent CRUD endpoints
- `agent_review_middleware.py` depends on `AgentPipelineMap` rows existing (from Phase 2)
- Frontend tree is purely read-only — no backend changes required after Phase 2 API endpoint is built
- Phase 3 (review integration) is the highest-risk step because it modifies the generation path — build and test in isolation first

---

## Integration Points with Existing Code

| Existing File | Change Required | Risk |
|---|---|---|
| `backend/app/api/endpoints/agents.py` | Add `BackgroundTasks` parameter and `background_tasks.add_task()` call in create/update/delete handlers | Low — additive change |
| `backend/app/api/endpoints/wizards.py` | Call `agent_review_middleware.review_and_refine()` between `wizard_generate()` and `apply_wizard_result_to_db()` | Medium — modifies generation path |
| `backend/app/models/database.py` | Add `AgentPipelineMap` SQLAlchemy model | Low — additive |
| `backend/app/models/schemas.py` | Add `PipelineMapEntry`, `PipelineMapResponse` schemas | Low — additive |
| `backend/app/config.py` | Add `PIPELINE_CONFIDENCE_THRESHOLD: float = 0.5`, `PIPELINE_MAX_AGENTS_PER_STEP: int = 3` | Low |
| `frontend/src/lib/api.tsx` | Add `getPipelineMap()` function | Low |
| `frontend/src/lib/constants.ts` | Add `QUERY_KEYS.PIPELINE_MAP` | Low |
| `frontend/src/components/Books/AgentManager.tsx` | Embed or link to `AgentPipelineTree` component | Low — additive |

**No changes required to:**
- `template_ai_service.py` — stays generation-only, agent-unaware
- `agent_service.py` — `run_multi_agent_review()` already exists and will be called as-is
- `rag_service.py` — agents already use this for context retrieval; no changes needed
- `ai_provider.py` — used as-is for composition and merge calls

---

## Scalability Considerations

| Concern | Current (1-3 agents) | Future (10+ agents) | Mitigation |
|---|---|---|---|
| Composition latency | ~2s, runs in background | ~2s still (one AI call covers all) | N agents does not add N AI calls — single batch prompt |
| Review latency | Max(single agent time) ~3-5s | Max(single agent time) ~3-5s | Parallel via asyncio.gather — does not scale with agent count |
| Review cost | N agents × 1 call per step | Use PIPELINE_MAX_AGENTS_PER_STEP cap (default 3) | Only top-confidence agents activate per step |
| DB reads at generation time | 1 index scan per step | 1 index scan per step | Indexed on (owner_id, phase, subsection_key) |
| Stale pipeline maps | Fresh within seconds of agent CRUD | Fresh within seconds of agent CRUD | Background recomposition on every CRUD |

---

## Sources

**Confidence: HIGH** — Based on direct codebase analysis of:
- `backend/app/services/agent_service.py` — `run_multi_agent_review()`, `_select_relevant_agents()`, parallel gather pattern
- `backend/app/services/template_ai_service.py` — `wizard_generate()`, generation pipeline structure
- `backend/app/api/endpoints/wizards.py` — `run_wizard()`, `apply_wizard_result_to_db()` integration point
- `backend/app/models/database.py` — `Agent`, `PhaseData`, `WizardRun` model shapes
- `backend/app/api/endpoints/agents.py` — CRUD trigger points for background recomposition
- `.planning/PROJECT.md` — Requirements, constraints, key decisions

**Confidence: MEDIUM** — Architecture pattern recommendations (parallel-then-merge, pre-computed mapping, BackgroundTasks over Celery) based on established FastAPI async patterns and the specific constraints in PROJECT.md.

---

*Architecture analysis: 2026-03-11*
