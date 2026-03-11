# Project Research Summary

**Project:** Agent Orchestration Pipeline — Screenwriting Assistant
**Domain:** Multi-agent review pipeline injected into template-based AI content generation
**Researched:** 2026-03-11
**Confidence:** HIGH (codebase-grounded) / MEDIUM (external ecosystem patterns)

## Executive Summary

This milestone bridges two already-built subsystems that currently have no connection: a template-based generation pipeline (`template_ai_service.py`) and a multi-agent review system (`agent_service.py`). The goal is to make agents active participants in generation — not just chat assistants. When a user runs a wizard to generate screenplay scenes, mapped agents review the output in parallel and a merge AI call synthesizes their feedback into a refined result. The core orchestration pattern (fan-out parallel reviews + fan-in merge) already exists in `run_multi_agent_review()` and needs to be adapted and wired into the generation path.

The recommended approach is to build custom, using only existing dependencies. Do not adopt LangGraph, CrewAI, or AutoGen — the use case is a narrow, non-cyclical fan-out/fan-in pattern that does not justify the dependency weight, abstraction mismatch, or migration cost of any of those frameworks. The entire implementation requires: one new DB table (`agent_pipeline_maps`), two new backend services (`pipeline_composer.py` and `agent_review_middleware.py`), one new API endpoint, and one new frontend tree component. No new Python packages or npm packages are needed.

The critical risks are all addressable at design time. The merge AI call must be engineered with explicit conflict-resolution rules or it will produce blander output than raw generation — this would undermine the feature's core value proposition. Pipeline re-composition must be gated on semantic field changes only (not cosmetic edits) to avoid thundering-herd LLM costs on every color picker interaction. The token budget for YOLO auto-generation with multiple agents must be capped before YOLO integration or a single run can consume 56+ LLM calls. All other pitfalls are mechanical and solvable with established patterns.

---

## Key Findings

### Recommended Stack

The existing stack covers 100% of what is needed. The orchestration pattern is a simple fan-out/fan-in: `asyncio.gather` fires N parallel agent reviews per generation step, then one `chat_completion(json_mode=True)` call merges the results. Both primitives are already in production use in `agent_service.py`. Pipeline re-composition on agent CRUD uses FastAPI `BackgroundTasks` (already available) to avoid blocking the HTTP response. Mapping data is stored in a new `agent_pipeline_maps` PostgreSQL table using the existing SQLAlchemy ORM pattern. The frontend tree view is a recursive Tailwind component using Lucide icons already installed.

**Core technologies:**
- `asyncio.gather` (Python stdlib): parallel agent review fan-out — already proven in `run_multi_agent_review()`, extend not replace
- `asyncio.wait_for` (Python stdlib): per-agent timeout guard — already in `run_multi_agent_review()` at `settings.AGENT_REVIEW_TIMEOUT`
- `ai_provider.chat_completion(json_mode=True)`: orchestrator mapping call + merge synthesis call — already used extensively in `template_ai_service.py`
- FastAPI `BackgroundTasks`: trigger pipeline re-composition after agent CRUD without blocking — built into FastAPI 0.110.0 already installed
- PostgreSQL 15 + SQLAlchemy 2.0.27: `agent_pipeline_maps` table with JSONB and indexed lookup — follows exact existing model patterns
- React Query v5.20 + Tailwind 3.4: frontend pipeline tree — all dependencies already installed

**What NOT to use:** LangGraph (no graph cycles in this use case), CrewAI (agent-to-agent comms are explicitly out of scope), AutoGen (multi-turn conversation model is architectural overkill), Celery/Redis (one short background task per CRUD does not justify a broker infrastructure).

### Expected Features

**Must have (table stakes):**
- Pipeline step mapping (agent-to-step): users expect agents they create to actively shape generation, not just assist in chat
- Automatic mapping on agent CRUD: manual mapping is a burden; AI-inferred placement from agent description + prompt is the correct UX
- Parallel agent review during generation: serial reviews would multiply latency; parallel is the only viable UX
- AI merge of parallel feedback: without merge, N reviews produce N unresolved suggestions — the pipeline feels incomplete
- Tree view UI showing agent-to-step mappings: without visibility users cannot know the pipeline exists or why their agents are or aren't having an effect
- Graceful degradation when no agents mapped: pipeline must continue normally with zero-overhead pass-through if no agents are assigned

**Should have (differentiators):**
- Mapping confidence score per step: lets users understand fit quality and tune agent descriptions purposefully
- Mapping staleness detection: badge in tree view when agent description changed after last mapping computation
- Per-step agent review visibility: `agents_consulted` metadata in generation response showing which agents ran and what they contributed
- Selective agent exclusion per run: checkbox toggle to temporarily skip an agent for a single run without deleting mapping

**Defer (v2+):**
- Mapping recomposition preview (diff before saving): adds a provisional API round-trip; defer until users report confusion
- Step-level feedback attribution (per-agent audit trail): adds DB schema complexity; defer until MVP usage confirms demand
- Agent-to-agent communication: explicitly out of scope per PROJECT.md; would create compounding bias and unpredictable recursion

### Architecture Approach

Three new components are added to the existing service layer with minimal changes to existing files. The architecture is intentionally surgical: `template_ai_service.py` stays agent-unaware (generation only), `agent_service.py` is reused as-is (its `run_multi_agent_review()` is called by the new middleware). The injection point is `wizards.py` between `wizard_generate()` and `apply_wizard_result_to_db()` — a single function call that is a no-op when no agents are mapped.

**Major components:**
1. `pipeline_composer.py` (new) — AI-driven mapping of all agents to all pipeline steps in one batch call; runs as a background task after agent CRUD; upserts `agent_pipeline_maps` rows
2. `agent_review_middleware.py` (new) — intercepts generation output, looks up mapped agents for the current phase/subsection_key, runs parallel reviews via `asyncio.gather`, fires one merge AI call, returns refined content with `agent_reviews` metadata
3. `AgentPipelineTree.tsx` (new) — read-only collapsible React tree showing phase → subsection → agent badge mappings; powered by `GET /api/agents/pipeline-map`; embedded in `AgentManager.tsx`

**New data model:** `agent_pipeline_maps` table with `(owner_id, agent_id, phase, subsection_key, confidence, rationale)`. Indexed on `(owner_id, phase, subsection_key)` for O(1) lookup at generation time. `ON DELETE CASCADE` from `agents.id` keeps it clean.

**Build order (dependency-driven):**
1. DB migration + SQLAlchemy model + Pydantic schemas
2. `pipeline_composer.py` + agent CRUD endpoint wiring + `GET /api/agents/pipeline-map`
3. `agent_review_middleware.py` + `wizards.py` injection
4. Frontend tree component

### Critical Pitfalls

1. **Merge call produces blander output than raw generation** — The merge LLM averages contradictory agent opinions instead of resolving them, stripping the strongest contributions and producing generic hedged output. Prevention: explicit conflict-resolution rules in the merge prompt ("choose the most specific and actionable suggestion, not a blend"), cap merge output to original token length, A/B validate merged vs. raw output before shipping.

2. **Thundering herd on cosmetic agent edits** — Every `PATCH /agents/{id}` call (including color and icon changes) triggers a re-composition LLM call if not gated. Prevention: `pipeline_dirty` flag set only on semantic field changes (`system_prompt_template`, `description`, `tags_filter`); debounce concurrent saves; serve cached mapping to frontend without recomputing on GET.

3. **Token budget explosion during YOLO auto-generation** — 5 agents + 8 pipeline steps = 56 total LLM calls per YOLO run at potentially 224,000 output tokens. Prevention: `MAX_AGENTS_PER_PIPELINE_STEP` config (default 3); relevance scoring gates — only fire reviews where agent relevance exceeds threshold; trim agent context for pipeline reviews (no book chunks); cost estimate surface before YOLO runs.

4. **Non-deterministic pipeline mapping across re-compositions** — LLM at temperature > 0 produces different mappings for identical agent descriptions across re-compositions. Prevention: `temperature=0` for mapping call, JSON-mode structured output with fixed schema, hash-based cache keyed on semantic fields to skip re-inference when description hasn't changed.

5. **Shared SQLAlchemy session across async parallel review tasks** — `asyncio.gather` over a shared `db: Session` produces intermittent `DetachedInstanceError` and stale reads. Prevention: each parallel task receives its own session from the session factory; change `run_multi_agent_review()` signature to accept `session_factory` callable instead of a single `Session`.

6. **Agent `system_prompt_template` format string mismatch in pipeline context** — The existing `_build_system_prompt` expects `section_type: SectionType` (legacy three-act model), not `phase/subsection_key` from the new template system. Prevention: add separate `_build_pipeline_system_prompt()` method accepting `phase: str, subsection_key: str`; map legacy `{section_type}` placeholder to `subsection_key` as fallback.

---

## Implications for Roadmap

Based on research, the architecture has clear sequential dependencies that dictate phase ordering. The DB table must exist before any service writes to it; the mapping must be computed before the review middleware can look anything up; the review middleware must work before YOLO integration adds volume.

### Phase 1: Data Foundation and Mapping Infrastructure
**Rationale:** Every downstream component depends on the `agent_pipeline_maps` table and the AI mapping call. No other phase can proceed without this. Also the right time to address Pitfalls 2, 4, and 10 (thundering herd, non-determinism, user-scoping of default agents) — all are schema-level decisions that are costly to reverse later.
**Delivers:** DB migration, `AgentPipelineMap` SQLAlchemy model, `PipelineMapEntry` / `PipelineMapResponse` Pydantic schemas, `pipeline_composer.py` with `temperature=0` + hash-based cache + `pipeline_dirty` flag logic, agent CRUD endpoints wired to `BackgroundTasks`, `GET /api/agents/pipeline-map` endpoint
**Addresses:** Pipeline step mapping (table stakes), automatic mapping on agent CRUD (table stakes)
**Avoids:** Pitfall 2 (thundering herd), Pitfall 4 (non-deterministic mapping), Pitfall 10 (default agent user-scoping)

### Phase 2: Parallel Review and Merge Infrastructure
**Rationale:** This is the highest-risk phase — it modifies the generation path and introduces the merge call. Must be built and validated in isolation before wiring into YOLO. The merge prompt engineering (Pitfall 1) and session isolation fix (Pitfall 3) must be addressed here, not deferred. Build and A/B test the merge strategy before wiring to production generation.
**Delivers:** `agent_review_middleware.py` with per-task session factory, merge AI call with conflict-resolution rules, `agents_consulted` metadata in wizard run response, `wizards.py` injection point between `wizard_generate()` and `apply_wizard_result_to_db()`, `_build_pipeline_system_prompt()` separate from legacy `_build_system_prompt()`
**Addresses:** Parallel agent review during generation (table stakes), AI merge of parallel feedback (table stakes), per-step agent review visibility (should-have)
**Avoids:** Pitfall 1 (bland merge output), Pitfall 3 (shared DB session), Pitfall 6 (conflicting field updates), Pitfall 8 (system_prompt format mismatch), Pitfall 12 (streaming interleave)

### Phase 3: Frontend Pipeline Tree
**Rationale:** Can be built in parallel with Phase 2 once Phase 1's API endpoint is live. Read-only component with low risk. Ships the visibility surface that makes agents feel real to users. React Query invalidation (Pitfall 7) and empty-state handling (Pitfall 11) must be included — they're trivial to add at build time but painful to retrofit.
**Delivers:** `AgentPipelineTree.tsx` collapsible tree component, `getPipelineMap()` API function, `QUERY_KEYS.PIPELINE_MAP` constant, React Query invalidation on agent mutations, empty state ("Create agents to see how they map to your pipeline"), embedded in `AgentManager.tsx`
**Addresses:** Tree view UI showing agent-to-step mappings (table stakes)
**Avoids:** Pitfall 7 (stale tree view after agent CRUD), Pitfall 11 (empty tree with no agents)

### Phase 4: YOLO Auto-Generation Integration and Token Budget Controls
**Rationale:** The review middleware from Phase 2 works for manual generation. YOLO chains all phases in sequence, multiplying the token cost. Per-step agent budgeting (Pitfall 5) and minimum relevance gating (Pitfall 13) must be implemented before YOLO integration or a single run can consume 56+ LLM calls. Do not integrate YOLO until Phase 2 has been validated with real usage data.
**Delivers:** `MAX_AGENTS_PER_PIPELINE_STEP` config, `MAX_STEPS_WITH_AGENT_REVIEW` config, relevance score gating in pipeline dispatcher, context trimming for pipeline reviews (no book chunks), cost estimate surface before YOLO run, YOLO flow wired to review middleware
**Addresses:** Agent review in YOLO flow (table stakes), graceful degradation (table stakes)
**Avoids:** Pitfall 5 (token budget explosion), Pitfall 9 (asyncio timeout orphaning HTTP connections), Pitfall 13 (agents with no relevant context still firing)

### Phase Ordering Rationale

- **Phase 1 before everything**: The `agent_pipeline_maps` table is a hard dependency for Phase 2 and 3. Schema decisions (composite key, confidence column, user-scoping) cannot be changed cheaply after data is written.
- **Phase 2 before Phase 4**: YOLO integration amplifies the cost and risk of any defect in the review middleware. Validate the review+merge pattern with manual generation first.
- **Phase 3 can overlap Phase 2**: The tree view only reads from the Phase 1 API endpoint. Frontend work can proceed once Phase 1's `GET /api/agents/pipeline-map` is live.
- **Phase 4 last**: Token budgeting and YOLO are the highest-volume code path. Instrument it carefully after the core pipeline is proven.

### Research Flags

Phases likely needing deeper research or design review during planning:
- **Phase 2:** The merge prompt engineering is the highest-uncertainty area in the entire system. No research file can fully de-risk it — the right prompt strategy emerges from A/B testing with real screenplay content. Plan explicit validation time before declaring Phase 2 complete.
- **Phase 2:** The `_build_pipeline_system_prompt()` implementation requires careful mapping of existing agent template variables to the new phase/subsection_key system. Audit all existing agent templates before designing the new method signature.
- **Phase 4:** Token cost per YOLO run is highly sensitive to the number of agents, template structure, and project context length. Establish a cost model (estimated tokens per step × agents × steps) before committing to config defaults.

Phases with standard, well-documented patterns (can skip research-phase):
- **Phase 1:** DB migration, SQLAlchemy model, Pydantic schema, BackgroundTasks wiring — all follow established patterns already present in the codebase. No new patterns needed.
- **Phase 3:** React Query + collapsible tree component — standard frontend patterns with no novel elements. Existing codebase already has `AgentManager.tsx` as the parent context.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings derived from direct codebase analysis; no new dependencies required — confidence is near-certain |
| Features | HIGH | Table stakes derived from codebase analysis + PROJECT.md validated requirements; differentiators are MEDIUM (ecosystem patterns without external source verification) |
| Architecture | HIGH | Component boundaries, data flow, and integration points are all grounded in actual code paths and SQLAlchemy model analysis; pattern recommendations are MEDIUM |
| Pitfalls | HIGH | All critical pitfalls are derived from direct codebase analysis of existing code paths (not theoretical risks); minor pitfalls have lighter grounding |

**Overall confidence:** HIGH for the core implementation approach; MEDIUM for merge prompt strategy and token cost projections.

### Gaps to Address

- **Merge prompt strategy**: The research identifies the risk (bland output) and prevention principles, but the exact prompt design for conflict resolution must be validated empirically with real screenplay content before Phase 2 is declared done. Build in evaluation time.
- **Template vocabulary completeness**: The mapping call prompt must embed all phase/subsection_key values from the template system. Confirm this list is stable before pinning it in the composition prompt — if new templates are added, the prompt must update.
- **Default agent ownership model**: The research flags that default agents (`is_default=True`) are shared across users, and per-user mappings must scope by `owner_id`. Validate this assumption against the actual Agent model's `is_default` + `owner_id` logic before writing the migration.
- **`asyncio.wait_for` HTTP socket cleanup**: Pitfall 9 notes that asyncio cancellation does not close underlying HTTP connections. Verify the current `ai_provider.py` HTTP client library's cancellation behavior before assuming the existing timeout pattern is safe under load.
- **`BackgroundTasks` lifetime with async DB sessions**: FastAPI `BackgroundTasks` runs after the response is sent but within the request lifecycle. Confirm that the `db: Session` from `get_db` is still valid inside a background task, or switch to a new `session_factory()` call within the background function.

---

## Sources

### Primary (HIGH confidence)
- `backend/app/services/agent_service.py` — parallel review patterns, `asyncio.gather`, `run_multi_agent_review()`, `_build_system_prompt()`, `_select_relevant_agents()`, timeout handling
- `backend/app/services/template_ai_service.py` — generation pipeline structure, wizard types, phase/subsection vocabulary, streaming architecture
- `backend/app/api/endpoints/wizards.py` — `run_wizard()`, `apply_wizard_result_to_db()` integration point, WizardRun lifecycle
- `backend/app/api/endpoints/agents.py` — CRUD trigger structure, semantic vs. cosmetic field distinction (current absence of)
- `backend/app/models/database.py` — Agent model, `is_default` flag, `AgentType` enum, `PhaseData`, `WizardRun`
- `backend/app/config.py` — `MAX_AGENTS_PER_REVIEW: 5`, `AGENT_REVIEW_TIMEOUT: 90`, `MAX_TOKENS: 4000`
- `backend/app/templates/short_movie.json` — pipeline step structure (phase IDs, subsection keys)
- `.planning/PROJECT.md` — validated requirements, out-of-scope decisions, key constraints

### Secondary (MEDIUM confidence)
- FastAPI BackgroundTasks documentation (training data; pattern is stable and well-documented)
- SQLAlchemy async session safety patterns (training data; session-per-task is established best practice)
- LLM merge prompt design (training data; conflict-resolution prompt engineering is empirically validated domain)

### Tertiary (LOW confidence)
- LangGraph, CrewAI, AutoGen design rationale — training data only; current API surfaces could not be verified; confidence in unsuitability conclusions remains HIGH despite LOW source confidence
- Token cost projections for YOLO runs — calculated from `MAX_TOKENS` config and agent count assumptions; real-world numbers will vary based on project context size

---
*Research completed: 2026-03-11*
*Ready for roadmap: yes*
