# Feature Landscape

**Domain:** AI agent orchestration pipeline for content generation (screenwriting context)
**Researched:** 2026-03-11
**Confidence:** HIGH (based on deep codebase analysis) / MEDIUM (for ecosystem patterns without web access)

---

## Context: What Already Exists

The codebase already has meaningful orchestration infrastructure. Understanding what exists avoids
rebuilding and informs which "table stakes" are already partially satisfied.

**Already implemented (do not rebuild):**
- `AgentService._select_relevant_agents()` — embedding-similarity agent selection
- `AgentService._orchestrate()` + `_orchestrate_stream_prepare()` — orchestrator agent that pulls
  from specialists and synthesizes in chat context
- `AgentService.run_multi_agent_review()` — parallel `asyncio.gather()` over multiple agents with
  per-agent timeout via `asyncio.wait_for()`
- Agent model with `agent_type` (book_based, tag_based, orchestrator), `system_prompt_template`,
  `description`, `tags_filter`, `is_active` flags
- `template_ai_service.py` — phase-by-phase generation pipeline (idea → story → scenes → write)
  with three wizard types: `idea_wizard`, `scene_wizard`, `script_writer_wizard`

**The gap this milestone fills:**
The existing multi-agent review and orchestrator only work in *chat*. The generation pipeline
(`template_ai_service.py` / `wizards.py`) runs without any agent participation. This milestone
bridges them: agents become active reviewers/refiners inside generation steps.

---

## Table Stakes

Features without which the orchestration system feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pipeline step mapping (agent-to-step) | Users expect agents they created to "do something" during generation, not just in chat | Medium | Core of the milestone. Map agent descriptions/types to template phases (idea, story, scenes, write) and subsection keys |
| Automatic mapping on agent CRUD | If mapping is manual, it's a burden — automatic makes it feel intelligent | Medium | Hook into `POST /api/agents/`, `PATCH /api/agents/{id}`, `DELETE /api/agents/{id}` to re-run mapping. Store result in DB. |
| Parallel agent review during generation | Users with 3+ agents expect no compounding latency — parallel is the only viable UX | Medium | `asyncio.gather()` pattern already exists in `run_multi_agent_review()`. Adapt for pipeline context |
| AI merge of parallel feedback | Without a merge step, N agent reviews produce N separate suggestions with no resolution — feels incomplete | High | New: a single synthesizer call that takes all agent outputs for a step and produces a merged refinement applied to the generated content |
| Tree view UI showing agent-to-step mappings | Without visibility, users cannot understand why their agents are or aren't having an effect | Medium | Collapsible tree: phase → subsection → [agent pills]. Read-only; informational |
| Agent review in both manual and YOLO flows | Agents that only activate in one mode feel inconsistent and confusing | Low | Same pipeline injection point works for both if the generation service is the shared path |
| Graceful degradation when no agents mapped | If zero agents map to a step, pipeline continues normally without error | Low | Guard clause in the pipeline injection layer |
| Per-step agent review visibility | User needs to see which agents ran during a specific generation step and what they contributed | Medium | Surface in generation result response: `agents_consulted: [{agent_id, name, color, summary}]` |

---

## Differentiators

Features that set this system apart. Not expected, but high value when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI-inferred step placement (not rule-based) | An agent named "Subtext Coach" gets placed at scene generation steps automatically — the system understands the agent's purpose from its description + system prompt, not just from `agent_type` enum | High | Use an AI classification call on agent save/edit. Pass agent name, description, personality, system_prompt_template; ask model to identify which template phases and subsection keys are relevant. Cache result as `pipeline_mapping` JSON on the Agent model. |
| Mapping confidence score per step | Show users not just "this agent maps here" but "this agent is a 90% fit for scene_list, 40% for core" — lets users understand why and tune their agent descriptions | Medium | Include confidence float (0-1) in the mapping JSON alongside each phase/subsection key |
| Mapping recomposition preview | When editing an agent, show a diff of "was mapped to X, will now map to Y" before saving | Medium | Frontend: fetch current mapping, run provisional save + mapping call, display diff before confirming |
| Step-level feedback attribution | In the tree view, expand a step to see agent A's specific suggestion vs. agent B's, alongside the merged result — full audit trail of how the final output was shaped | High | Requires storing per-agent review output alongside merged output in DB for each generation run |
| Selective agent activation per generation run | Allow user to temporarily exclude an agent from a single run without deleting the mapping | Low | Checkbox list in generation dialog. Each agent has `exclude` toggle for this run only. Stored in request body, not persisted. |
| Mapping staleness detection | If an agent's description/prompt changes significantly after mapping, flag it as "mapping may be outdated" | Low | Track `mapping_computed_at` timestamp vs `updated_at` on Agent. Surface badge in tree view. |

---

## Anti-Features

Features to deliberately NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Agent-to-agent communication during pipeline | Agents reviewing each other's output creates compounding bias and unpredictable recursion. Already explicitly out of scope per PROJECT.md. | Agents review the primary generation output independently, in parallel |
| User approval gates for each agent review | Interrupts generation flow, turns automated pipeline into a manual process. Kills the YOLO experience entirely. | Pipeline is automatic. Users see results after the fact via the tree view and generation response |
| Custom pipeline step ordering by users | AI determines optimal placement. User-ordering creates maintenance burden and requires a drag-and-drop ordering UI with unclear semantics. | Informational tree view only. AI mapping is authoritative. |
| Per-flow agent toggle (manual vs. YOLO) | Inconsistency confuses users: "why did my agent run on YOLO but not manual?" | Agents activate equally in both flows |
| Sequential agent chaining (A reviews B reviews C) | Latency is additive (3 agents = 3x slowdown). Compounding bias from each agent building on the last. | Parallel fan-out + single merge call. Fixed latency ceiling = max(slowest agent, merge call) |
| Dynamic pipeline topologies per project | Different users having different pipeline structures creates testing and debugging complexity disproportionate to value | One mapping structure per user (agents → global step mapping). Project-specific overrides add scope without clear user demand |
| Storing full agent review history per generation run (V1) | Adds DB schema complexity and storage costs before value is proven | Start with just the merged output. Add per-agent audit trail as a differentiator in a later phase if users request it |
| Real-time streaming of per-agent review progress | Complex SSE fan-out implementation. Users don't need to watch 3 agents think simultaneously. | Show a loading state during pipeline + agent review, then show complete result |

---

## Feature Dependencies

```
AI orchestrator mapping call
  → requires: Agent model (exists)
  → requires: Agent description/system_prompt_template (exists)
  → requires: Template phase/subsection key vocabulary (exists in short_movie.json)
  → produces: pipeline_mapping JSON stored on Agent

Pipeline injection in template_ai_service.py
  → requires: pipeline_mapping on Agent (new, from above)
  → requires: generation output (exists — wizard_generate returns content)
  → requires: asyncio.gather() parallel review (pattern exists in run_multi_agent_review())
  → produces: refined generation output

AI merge step
  → requires: N parallel agent review outputs (new, from above)
  → requires: original generation output (exists)
  → produces: single merged/refined content replacing the original output

Tree view UI
  → requires: pipeline_mapping endpoint (new — GET /api/agents/pipeline-mapping)
  → requires: agent list with color/name (exists — GET /api/agents/)
  → requires: template phase/subsection structure (exists — GET /api/templates/)
  → produces: collapsible visualization

Agent-to-step visibility in generation response
  → requires: merge step execution (from above)
  → produces: augmented wizard run response with agents_consulted metadata
```

**Critical path:**
1. `pipeline_mapping` DB field + AI mapping call on agent CRUD (backend)
2. Pipeline injection point in `template_ai_service.py` — pass mapped agents into wizard generation
3. Parallel review + merge call within the injection point
4. `GET /api/agents/pipeline-mapping` endpoint for UI
5. Tree view component (frontend)

Steps 1-3 are sequential and constitute the core. Steps 4-5 can be built in parallel with 3.

---

## MVP Recommendation

### Prioritize (must ship together — they're interdependent):

1. **AI mapping call on agent CRUD** — fires on create/edit/delete, stores `pipeline_mapping` JSON
   on Agent (or in a separate `AgentPipelineMapping` table). Pipeline without mapping data is
   inert.

2. **Pipeline injection in `template_ai_service.py`** — before returning wizard output, look up
   which agents map to the current phase/subsection. If any, run parallel review + merge call.
   Augment the returned result with `agents_consulted` metadata.

3. **Tree view UI** — without this, users have no way to know the pipeline exists or what it does.
   Complexity is low (read-only, informational). Should ship with the first backend release.

### Defer:

- **Mapping confidence scores** — valuable but adds complexity to the mapping call prompt. Do in
  pass two when iterating on mapping quality.

- **Mapping recomposition preview** — nice UX, but the diff comparison adds a round-trip API call.
  Defer until users report confusion about mapping changes.

- **Step-level feedback attribution (per-agent audit trail)** — adds DB schema changes and a
  complex UI. Defer until MVP usage confirms users want transparency into per-agent contributions.

- **Selective agent exclusion per run** — low complexity but requires UI surface in the generation
  dialog. Defer until core flow is stable.

---

## Domain-Specific Notes for This Codebase

### The "mapping vocabulary" problem
The AI mapping call needs to know which phases/subsection keys exist in templates. The current
template system defines phases (`idea`, `story`, `scenes`, `write`) and subsection keys
(`idea_wizard`, `core`, `characters`, `scene_list`, `scene_detail`, `screenplay_editor`, etc.).
The mapping call must either (a) embed this vocabulary in its prompt, or (b) retrieve it
dynamically from the template config. Option (b) is correct — it ensures new templates
automatically get mapped without prompt changes.

### The "agent type as hint" design decision
The existing `AgentType` enum (`book_based`, `tag_based`, `orchestrator`) is the current
categorization axis. The new orchestrator should use `agent_type` as a *hint* but derive
placement from the agent's `description` and `system_prompt_template`. A `book_based` agent
whose prompt says "I analyze character arcs and emotional beats" clearly maps to `story/core`
and `story/characters`, not `scenes/scene_list`. Type alone cannot capture this.

### The merge call design
The merge call takes: (1) original generated content, (2) N agent review outputs (issues +
suggestions). It should produce a refined version of the original content that incorporates
non-conflicting suggestions and flags conflicts. This is different from the existing
`_orchestrate()` pattern which synthesizes agent *knowledge* rather than agent *critiques of
existing content*.

### Token budget
Each agent review is a full AI call. For 3 agents + 1 merge call on a single wizard step:
- Worst case (scene_wizard with 10 scenes): 3 agents × 10 scenes × review = 30 calls + 10 merge
  calls = 40 calls on top of the 10 generation calls.
- Practical mitigation: only agents mapped to the current subsection key fire. Most steps will
  have 1-2 mapped agents, not all agents.
- Recommendation: add a `max_agents_per_step` config (default: 3) to cap token spend.

---

## Sources

- Codebase analysis: `backend/app/services/agent_service.py` (multi-agent patterns, parallel
  review via asyncio.gather, orchestrator pattern)
- Codebase analysis: `backend/app/services/template_ai_service.py` (generation pipeline
  structure, wizard types, phase/subsection vocabulary)
- Codebase analysis: `backend/app/models/database.py` (Agent model, AgentType enum, PhaseData
  model, WizardRun model)
- Codebase analysis: `backend/app/api/endpoints/wizards.py` (generation flow entry points,
  apply_wizard_result_to_db)
- Project spec: `.planning/PROJECT.md` (validated requirements, out-of-scope items, key decisions)
- Architecture: `.planning/codebase/ARCHITECTURE.md` (service layer, data flow patterns)
- Confidence: HIGH for table stakes (derived from PROJECT.md validated requirements + codebase
  analysis). MEDIUM for differentiators (ecosystem patterns without external source verification).
