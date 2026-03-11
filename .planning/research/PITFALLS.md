# Domain Pitfalls: AI Agent Orchestration Pipeline

**Domain:** Multi-agent orchestration injected into an existing template-based generation pipeline
**Researched:** 2026-03-11
**Confidence:** HIGH — derived from direct codebase analysis of the existing implementation plus established patterns in multi-agent LLM system design

---

## Critical Pitfalls

Mistakes that require rewrites, break existing workflows, or make the feature unusable.

---

### Pitfall 1: The Merge LLM Produces Blander Output Than Any Single Agent

**What goes wrong:** When 3-5 agents each provide detailed, opinionated feedback on a screenplay beat, and a merge LLM is asked to "synthesize" them into a single refined output, the merge call has a strong tendency to hedge. It averages contradictory opinions instead of resolving them, strips the strongest language from each agent's contribution, and produces a generic middle-ground that is worse than what any individual agent would have written. The upstream generation output was good; the merge made it worse.

**Why it happens:** The merge prompt has no forcing function to choose or rank. Without explicit resolution instructions, the LLM treats all inputs as equally valid and blends them. Contradictions between a structure agent ("the protagonist's goal is unclear") and a dialogue agent ("the protagonist's voice is distinctive") become muted or dropped entirely. The merge also expands token count, causing the AI to fill space with qualifications.

**Consequences:** Users notice the "reviewed" output is less interesting than the raw generation. They distrust the agent pipeline, disable agents, and the core value proposition — "agents actively shape your screenplay" — is proven false.

**Prevention:**
- The merge prompt must include explicit conflict-resolution rules: "If agents disagree, choose the most specific and actionable suggestion, not a blend of both."
- Pass agent names and roles to the merge call so it can attribute credit: "Structure Coach says X; Dialogue Expert says Y. Apply both if non-contradictory, otherwise prioritize the one most relevant to this pipeline step."
- Cap the merge output to approximately the same token length as the original step output. Never let the merge expand the content.
- Run A/B validation: compare direct generation output vs. merged output on 10-20 screenplay sections before shipping. If merged output scores lower by human evaluation, the merge strategy needs redesign before launch.

**Detection:** Merge output consistently longer than input with hedging language ("it could be argued," "one might consider"). Users stop using agents after first generation run.

**Phase:** Address in the pipeline injection phase before any YOLO/auto-generation integration.

---

### Pitfall 2: Pipeline Re-Composition Triggers on Every Save, Creating a Thundering Herd

**What goes wrong:** The decision to "re-compose the pipeline on agent CRUD" sounds clean in planning, but CRUD in this codebase fires on every `PATCH /agents/{id}` call — including non-semantic changes like color, icon, and name updates. If the re-composition triggers an LLM call to re-analyze all agents and map them to pipeline steps, every cosmetic edit fires an expensive AI inference. With five agents, that is five embedding lookups plus an orchestration LLM call on every color picker interaction.

**Why it happens:** Agent edit endpoints (`PATCH /agents/{agent_id}`) do not distinguish between semantic changes (system_prompt, description, tags_filter) and cosmetic changes (color, icon, name). All fields go through the same update path.

**Consequences:** Unnecessary API cost on every agent UI interaction. Rate limit errors surface during agent setup. Pipeline mapping becomes inconsistent if concurrent saves race each other.

**Prevention:**
- Add a `pipeline_dirty` flag to the Agent model. Set it `true` only when `system_prompt_template`, `description`, or `tags_filter` change — not on cosmetic field updates.
- The re-composition job reads `pipeline_dirty=True` agents and runs asynchronously via a background task, not inline with the HTTP response.
- Store the pipeline mapping as a separate DB table (e.g., `agent_pipeline_mappings`) with a `computed_at` timestamp. Serve the cached mapping to the frontend tree view without re-computing on every GET.
- Use a debounce or queue: if three saves fire in 10 seconds for the same agent, only one re-composition runs.

**Detection:** API logs show `POST /pipeline/recompose` or equivalent firing on color picker interactions. OpenAI/Anthropic billing spikes during agent setup sessions.

**Phase:** Address in pipeline mapping storage schema design, before building the re-composition trigger logic.

---

### Pitfall 3: Parallel Agent Reviews Do Not Use the Same DB Session Safely

**What goes wrong:** The existing `run_multi_agent_review` in `agent_service.py` already uses `asyncio.gather` with a shared `db: Session`. SQLAlchemy sessions are not thread-safe and have limited safety in async contexts. When multiple `review_section` coroutines execute concurrently on the same session object, the `db.query()` calls from different coroutines interleave. One coroutine's `db.query()` may return results partially modified by another's concurrent ORM state changes or `db.commit()` call.

**Why it happens:** The existing code passes a single `Session` object into all parallel tasks in `run_multi_agent_review`. Each `review_section` call does RAG queries against this same session. If any coroutine triggers a lazy-load, flush, or expiry while another is mid-query, ORM state becomes inconsistent.

**Consequences:** Intermittent `DetachedInstanceError`, stale reads in RAG results, or data written to wrong sessions. These bugs are non-deterministic and very hard to reproduce in testing but surface in production under load.

**Prevention:**
- Each parallel agent review task must receive its own `Session` instance. Use a session factory (already available via `get_db` dependency) to create isolated sessions per task.
- Pattern: `async with session_factory() as db: result = await review_section(agent, section, project, db)` inside each gather task.
- The existing `run_multi_agent_review` signature must change from accepting a single `db: Session` to accepting a `session_factory` callable.
- Write tests that fire 3-5 concurrent reviews and assert each returns independent results — this catches session sharing bugs before they reach production.

**Detection:** `DetachedInstanceError` or `sqlalchemy.exc.InvalidRequestError` in logs during parallel generation. Inconsistent RAG results across consecutive runs of the same pipeline step.

**Phase:** Address in parallel review infrastructure, before wiring into the generation pipeline.

---

### Pitfall 4: The Orchestrator LLM Mapping Is Non-Deterministic Across Re-Compositions

**What goes wrong:** The AI orchestrator that maps agents to pipeline steps is asked to make judgment calls: "Does this character-development agent belong at the Story/Characters step or also at the Story/Core step?" Every re-composition may produce a different answer because LLM inference at non-zero temperature is non-deterministic. An agent that mapped to 3 steps yesterday now maps to 2 steps after the user edits a description, even if the description change was minor. The tree view UI shows the mapping changing in ways the user did not intend.

**Why it happens:** The mapping prompt uses generative inference rather than rule-based matching. Temperature > 0 on the mapping call means identical input can produce different output across runs.

**Consequences:** Users lose trust in the tree view ("why did my agent disappear from Scene Creation?"). Debugging is impossible — the same agent description produces different mappings. Users edit descriptions to try to "fix" mappings and inadvertently change their agent's behavior.

**Prevention:**
- Run the orchestrator mapping call at `temperature=0` to maximize determinism.
- Use structured output (JSON mode) with a fixed schema listing every pipeline step as a boolean field: `{"story_core": true, "story_characters": false, ...}`. This constrains the output space.
- Cache the mapping keyed on a hash of the agent's semantic fields (`system_prompt_template + description + tags_filter`). If the hash has not changed, serve the cached mapping without re-running inference.
- Show the user the mapping reasoning in the tree view tooltip (not just the result) so they can understand why an agent mapped where it did and adjust their description purposefully.

**Detection:** Tree view shows different agent placement across page refreshes with no agent edits. Users report "my agent disappeared from a step."

**Phase:** Address in mapping computation design, before building the tree view UI.

---

### Pitfall 5: Token Budget Explosion During YOLO Auto-Generation

**What goes wrong:** The YOLO flow runs every phase in sequence automatically. Each phase step now also fires N parallel agent review calls plus one merge call. A single full YOLO run with 5 agents and 8 pipeline steps becomes: 8 generation calls + (5 agents × 8 steps) = 40 parallel review calls + 8 merge calls = 56 total LLM calls per generation run. At current `MAX_TOKENS=4000` per call, a full YOLO run can consume 224,000 output tokens in addition to the input context for every call (each carrying full project context + agent system prompt + RAG chunks).

**Why it happens:** The cost model for agent reviews is per-step, not per-run. Parallel execution hides the latency cost but not the token cost. Project context (`_build_project_context`) grows as earlier phases complete, making later steps have longer inputs.

**Consequences:** A YOLO run with 5 agents costs 5-10x more than a run without agents. Users hit OpenAI rate limits mid-generation. Cost per generation run becomes prohibitive at scale. The app becomes unusable for users with many agents.

**Prevention:**
- Implement per-pipeline-run agent budgeting: a configurable `MAX_AGENTS_PER_PIPELINE_STEP` (already exists in config as `MAX_AGENTS_PER_REVIEW: 5`) — but also add `MAX_STEPS_WITH_AGENT_REVIEW` to limit which steps get reviewed.
- Use agent relevance scoring (the existing `_select_relevant_agents` pattern) to only fire agent reviews on steps where the agent's relevance score exceeds a threshold. A dialogue agent should not review the Idea phase.
- Trim agent context for pipeline reviews: in chat mode, agents receive full RAG context (concepts + chunks). In pipeline review mode, limit to top 3 concepts, no book chunks. Pipeline reviews should be fast assessments, not deep consultations.
- Surface a cost estimate to the user before YOLO runs: "This run will use approximately N active agents across M steps."

**Detection:** YOLO runs taking > 60 seconds with agents enabled. Rate limit (429) errors appearing mid-generation. Cost per run is 5x higher with agents than without.

**Phase:** Address token budget strategy before YOLO integration. Do not add YOLO agent support until per-step agent budgeting is implemented.

---

### Pitfall 6: Agent Prompt Conflicts Produce Contradictory Field Updates

**What goes wrong:** When two agents review the same pipeline step and both output `field_updates` JSON blocks (as the existing chat mode already supports), their updates may directly contradict each other. A "tighten the dialogue" agent proposes: `{"dialogue": "Brief, clipped exchange."}` A "expand character interiority" agent proposes: `{"dialogue": "Long reflective monologue."}` The merge step receives both and must arbitrate. If the merge prompt does not explicitly address conflicting `field_updates`, it will typically apply the last one it processes or produce a garbled blend.

**Why it happens:** The existing field update mechanism was designed for single-agent chat interactions, not multi-agent parallel review. There is no arbitration protocol for contradictory field-level changes.

**Consequences:** Field content becomes garbled or one agent's output is silently dropped. The user sees a field value that doesn't reflect any coherent intent.

**Prevention:**
- Separate "review feedback" (issues + suggestions) from "direct field writes" in the pipeline context. During pipeline steps, agents should produce structured feedback JSON (`{"issues": [], "suggestions": [], "confidence": 0.8}`), not raw field updates. The merge step decides what field updates to apply based on the aggregated feedback.
- Reserve direct `field_updates` for chat-mode interactions where a single agent is explicitly asked to edit content.
- The merge LLM receives the original field values, all agent feedback structs, and then decides the final field update — it is the only writer.

**Detection:** Field values in pipeline output contain contradictory or incoherent content. Users report "the AI seems confused about what it's trying to do."

**Phase:** Address in agent review output schema design, before any field-writing in the pipeline is implemented.

---

## Moderate Pitfalls

---

### Pitfall 7: Tree View Goes Stale After Agent CRUD Without Invalidation

**What goes wrong:** The React frontend tree view displays which agents are mapped to which pipeline steps. This data comes from the backend `agent_pipeline_mappings` table. When an agent is created, edited, or deleted, the re-composition runs asynchronously in the background. During the gap between the CRUD operation and the background job completing, the tree view shows stale data. Worse: React Query caches the mapping response, so even after the background job completes, the frontend does not update until the cache TTL expires.

**Why it happens:** The mapping is stored and served from the DB, but React Query's cache (currently 5-minute stale time per CLAUDE.md) does not know the mapping was invalidated by an agent CRUD event.

**Prevention:**
- The agent CRUD API response should include a `pipeline_mapping_status: "recomputing" | "ready"` field.
- The frontend should optimistically mark the tree view as "updating" immediately after any agent CRUD, then poll or use the status field to refresh.
- React Query invalidation: after `mutate` on `PATCH /agents/:id`, explicitly call `queryClient.invalidateQueries(['pipeline-mappings'])`.

**Detection:** Tree view shows deleted agent still mapped to steps. Users see outdated mapping for 5 minutes after editing an agent.

**Phase:** Address during tree view UI implementation.

---

### Pitfall 8: The `system_prompt_template` Format String Breaks in Pipeline Context

**What goes wrong:** The existing `_build_system_prompt` in `agent_service.py` calls `agent.system_prompt_template.format(concept_cards=..., concept_relationships=..., book_chunks=..., framework=..., section_type=..., project_context=...)`. These six named placeholders are required. In pipeline review mode, agents are being used outside their original chat context — the `framework` and `section_type` parameters map to the old `Section` model (three-act sections like `INCITING_INCIDENT`), not the new template-based pipeline steps (phases like `story/characters`).

**Why it happens:** The `Section` model and `SectionType` enum are legacy constructs from the original three-act framework. The new template system uses `PhaseData` with `phase` (enum) + `subsection_key` (string). The `_build_system_prompt` method has no equivalent for `phase/subsection_key` routing.

**Consequences:** Pipeline reviews either pass wrong section type metadata to agents (confusing them) or crash with a `KeyError` if new placeholders are added without updating all existing agent prompt templates.

**Prevention:**
- Add a `_build_pipeline_system_prompt` method separate from `_build_system_prompt`. It accepts `phase: str` and `subsection_key: str` instead of `section_type: SectionType`.
- Default agent prompt templates must be validated to not assume a three-act section structure. Add a lint step that verifies all `{placeholder}` variables in a template are in the supported set.
- Keep backward compatibility: if an agent prompt template uses the old `{section_type}` placeholder, map it to the `subsection_key` string as a fallback.

**Detection:** `KeyError: 'section_type'` in logs when pipeline reviews fire. Agent review results contain nonsensical section references like "For this Inciting Incident section..." when reviewing a character-development phase.

**Phase:** Address during the pipeline injection wiring phase.

---

### Pitfall 9: `asyncio.wait_for` Timeouts Do Not Cancel Underlying HTTP Requests

**What goes wrong:** The existing `run_multi_agent_review` wraps each review in `asyncio.wait_for(..., timeout=settings.AGENT_REVIEW_TIMEOUT)`. When a timeout fires, `asyncio.wait_for` raises `asyncio.TimeoutError` and the gather continues. However, the underlying HTTP request to OpenAI/Anthropic is still in-flight. The `aiohttp` or `httpx` connection is consuming a socket and will eventually complete — it just has no one to return the result to. Under load, this creates socket exhaustion: many "abandoned" HTTP connections pile up while the app returns timeout errors to users.

**Why it happens:** `asyncio.wait_for` cancels the coroutine's Python execution but does not close the underlying network connection. The HTTP client library's connection pool fills with these orphaned requests.

**Prevention:**
- Use proper cancellation: wrap the `chat_completion` call in a try/except that catches `asyncio.CancelledError` and explicitly closes the HTTP client connection.
- Configure the AI provider's HTTP client with its own request-level timeout (distinct from the asyncio timeout) so the HTTP layer also enforces time limits.
- Log orphaned request counts. Alert if more than 10% of agent review calls time out in a session — it signals systemic latency issues.

**Detection:** Growing number of open sockets in `netstat` during load. Memory usage climbing during YOLO runs. `ConnectionPool exhausted` errors in the AI provider client.

**Phase:** Address during parallel review infrastructure implementation.

---

### Pitfall 10: Agent Mapping Stored Per-User But Default Agents Are Shared

**What goes wrong:** Default agents (`is_default=True`) are owned by the system but visible to all users. If pipeline mappings are stored as `agent_id + pipeline_step + user_id`, this works correctly. But if mappings are stored as just `agent_id + pipeline_step` (without user scoping), one user's mapping update for a default agent overwrites everyone else's mapping for that agent.

**Why it happens:** Default agents do not have individual `owner_id` per user — they are shared. The mapping table design decision will determine whether this is a problem: user-scoped mappings (correct) vs. global mappings (breaks multi-user).

**Prevention:**
- The `agent_pipeline_mappings` table must always include `user_id` (or `owner_id`) as part of the composite key, even for default agents.
- On first access, compute and store a user-specific copy of the default agent's mapping.
- Index on `(user_id, agent_id)` to ensure fast lookup per user.

**Detection:** User A editing a default agent's pipeline mapping overwrites User B's mapping for the same agent.

**Phase:** Address in the pipeline mapping schema migration, before any data is written.

---

## Minor Pitfalls

---

### Pitfall 11: Tree View Renders All Steps Even When Pipeline Has No Agents

**What goes wrong:** The tree view UI iterates over all pipeline steps and shows which agents are assigned. If a user has no agents, the tree view renders an empty tree — potentially 20-30 empty step nodes with no agents. This creates visual noise and confusion ("why is there a whole tree of empty boxes?").

**Prevention:** Gate the tree view on `agents.length > 0`. Show an empty state ("Create agents to see how they map to your pipeline") instead of an empty tree.

**Phase:** Address during tree view UI implementation.

---

### Pitfall 12: Streaming Generation Breaks When Agent Review Is Injected Mid-Stream

**What goes wrong:** The existing generation uses `chat_completion_stream` which yields text chunks. If agent reviews are injected after the stream completes (collect full output → review → merge → return), this is fine. But if the implementation tries to stream the merge output directly, the frontend SSE event handler receives interleaved chunk events from the base generation and the merge pass, producing garbled output.

**Prevention:** Never stream the merged output. Always: (1) buffer full base generation output, (2) run agent reviews on the complete buffer, (3) run merge on the complete reviews, (4) return the merged result as a single non-streaming response or as a fresh streaming pass. The generation step and review+merge step must be sequential, not concurrent.

**Phase:** Address during pipeline injection wiring.

---

### Pitfall 13: Agents With No Relevant RAG Context Still Fire Review Calls

**What goes wrong:** An agent with no books and no relevant concept matches for a given pipeline step still gets included in the parallel review batch if it is mapped to that step. It fires an API call with empty `concept_cards` and empty `book_chunks`, producing generic advice that adds no value. The cost is paid, the latency is added, the output contributes nothing.

**Prevention:** Add a minimum relevance score gate in the pipeline dispatcher. If an agent's relevance score for the current step falls below 0.2 (the threshold already used in `review_section` for concept filtering), skip that agent for that step entirely. Log it as "agent skipped — no relevant context."

**Phase:** Address during pipeline dispatcher implementation.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Pipeline mapping schema design | User-scoping of default agent mappings (Pitfall 10) | Include `user_id` in composite key from day one |
| Mapping computation trigger | Thundering herd on cosmetic agent edits (Pitfall 2) | `pipeline_dirty` flag gated on semantic field changes only |
| Mapping LLM call | Non-deterministic mapping across re-compositions (Pitfall 4) | `temperature=0`, JSON mode, hash-based cache |
| Parallel review infrastructure | Shared DB session across async tasks (Pitfall 3) | Per-task session factory pattern |
| Parallel review infrastructure | Timeout orphaning HTTP connections (Pitfall 9) | HTTP-level timeout in addition to asyncio timeout |
| Agent review output schema | Conflicting field updates from multiple agents (Pitfall 6) | Agents output feedback structs only; merge LLM is sole writer |
| Merge strategy | Blander output than single agent (Pitfall 1) | Conflict-resolution rules in merge prompt; A/B validate before shipping |
| Pipeline injection wiring | `system_prompt_template` format string mismatch (Pitfall 8) | Separate `_build_pipeline_system_prompt` method |
| YOLO auto-generation | Token budget explosion (Pitfall 5) | Per-step relevance gating + context trimming before YOLO support |
| Tree view UI | Stale mapping after agent CRUD (Pitfall 7) | React Query invalidation on agent mutation |
| Tree view UI | Empty tree with no agents (Pitfall 11) | Gate rendering on `agents.length > 0` |
| Streaming generation | Interleaved SSE chunks if merge streams (Pitfall 12) | Buffer-then-merge pattern, never concurrent stream |

---

## Sources

- Direct analysis of `/backend/app/services/agent_service.py` — existing `run_multi_agent_review`, `_build_system_prompt`, `asyncio.gather` usage, `asyncio.wait_for` timeout handling
- Direct analysis of `/backend/app/services/template_ai_service.py` — existing pipeline generation patterns, field update mechanism, streaming architecture
- Direct analysis of `/backend/app/models/database.py` — Agent model fields, `is_default` flag, `AgentType` enum, `PhaseData`/`Section` dual-model reality
- Direct analysis of `/backend/app/api/endpoints/agents.py` — CRUD endpoint structure, lack of semantic vs. cosmetic field differentiation
- Direct analysis of `/backend/app/config.py` — `MAX_AGENTS_PER_REVIEW: 5`, `AGENT_REVIEW_TIMEOUT: 90`, `MAX_TOKENS: 4000`
- Direct analysis of `/backend/app/templates/short_movie.json` — pipeline step structure (phase IDs, subsection keys)
- `.planning/PROJECT.md` — milestone requirements, key decisions, constraints
