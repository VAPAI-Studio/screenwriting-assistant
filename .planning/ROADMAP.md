# Roadmap: Agent Orchestration Pipeline

## Overview

This milestone wires two already-built subsystems — the template-based generation pipeline and the multi-agent review system — into a unified orchestration pipeline. The work progresses in four natural layers: data foundation, backend review infrastructure, frontend visibility, and YOLO integration. Each phase delivers a coherent, independently verifiable capability. Phases follow hard sequential dependencies: the DB table must exist before mapping logic can write to it; mapping must be computed before the review middleware can look anything up; the review middleware must be proven stable with manual generation before YOLO amplifies its volume.

## Phases

- [ ] **Phase 1: DB Foundation** - Create `agent_pipeline_maps` table, SQLAlchemy model, and Pydantic schemas
- [ ] **Phase 2: Pipeline Composer Service** - Build `pipeline_composer.py` with AI mapping, hash-based cache, and dirty-flag gating
- [ ] **Phase 3: Pipeline Map API and CRUD Wiring** - Expose GET endpoint and wire agent CRUD to trigger re-composition via BackgroundTasks
- [ ] **Phase 4: Async Safety and Session Isolation** - Fix shared DB session bug in `run_multi_agent_review` for safe concurrent use
- [ ] **Phase 5: Agent Review Middleware** - Build `agent_review_middleware.py` with parallel fan-out, merge AI call, and pass-through bypass
- [ ] **Phase 6: Wizard Injection** - Inject review middleware into `wizards.py` generation path and surface `agents_consulted` metadata
- [ ] **Phase 7: Frontend Pipeline Tree** - Build `AgentPipelineTree.tsx` collapsible tree component embedded in `AgentManager.tsx`
- [ ] **Phase 8: YOLO Integration and Token Budget** - Wire YOLO auto-generation through review middleware with configurable agent budgets

## Phase Details

### Phase 1: DB Foundation
**Goal**: The `agent_pipeline_maps` table and its ORM layer exist and are ready for writes
**Depends on**: Nothing (first phase)
**Requirements**: COMP-02
**Success Criteria** (what must be TRUE):
  1. Running the migration creates `agent_pipeline_maps` table with `owner_id`, `agent_id`, `phase`, `subsection_key`, `confidence`, `rationale`, and `pipeline_dirty` columns
  2. The composite index on `(owner_id, phase, subsection_key)` exists and can be confirmed via `\d agent_pipeline_maps` in psql
  3. The `AgentPipelineMap` SQLAlchemy model is importable and its relationship to the `Agent` model includes `ON DELETE CASCADE`
  4. `PipelineMapEntry` and `PipelineMapResponse` Pydantic schemas validate correctly and can round-trip from the ORM model
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — SQL migration for `agent_pipeline_maps` table and indexes
- [ ] 01-02-PLAN.md — `AgentPipelineMap` SQLAlchemy model with cascade relationship to Agent
- [ ] 01-03-PLAN.md — `PipelineMapEntry` / `PipelineMapResponse` Pydantic schemas + COMP-02 test suite

### Phase 2: Pipeline Composer Service
**Goal**: An AI orchestrator can analyze all user agents and produce a stable, deterministic mapping to pipeline steps
**Depends on**: Phase 1
**Requirements**: COMP-01, COMP-03
**Success Criteria** (what must be TRUE):
  1. Calling `compose_pipeline(owner_id, db)` produces `agent_pipeline_maps` rows for each agent-to-step pairing with confidence scores
  2. Running `compose_pipeline` twice with identical agent descriptions produces identical output (temperature=0 + hash-based cache)
  3. A cosmetic agent edit (name, color, icon) does NOT trigger re-composition; a semantic edit (system_prompt_template, description) DOES set `pipeline_dirty=True`
  4. The composer handles the case where a user has zero agents without error (returns empty mapping)
  5. The composition prompt embeds all phase/subsection_key values from the active template system
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Core pipeline_composer.py service with AI mapping, template discovery, batch splitting, and COMP-01 TDD tests
- [ ] 02-02-PLAN.md — Hash-based cache and semantic change detection with COMP-03 TDD tests

### Phase 3: Pipeline Map API and CRUD Wiring
**Goal**: The frontend and generation layer can retrieve current pipeline mappings, and agent CRUD automatically triggers re-composition in the background
**Depends on**: Phase 2
**Requirements**: COMP-01 (trigger side), COMP-03 (CRUD gate), COMP-04
**Success Criteria** (what must be TRUE):
  1. `GET /api/agents/pipeline-map` returns the current mapping for the authenticated user in the `PipelineMapResponse` schema
  2. Creating an agent triggers background re-composition; the mapping updates within seconds without blocking the POST response
  3. Editing an agent's `system_prompt_template` triggers re-composition; editing only the agent's name does not
  4. Deleting an agent removes its `agent_pipeline_maps` rows via cascade and triggers a fresh composition of remaining agents
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Schema expansion, GET /pipeline-map endpoint, BackgroundTasks wiring into create/update/delete
- [ ] 03-02-PLAN.md — Integration test suite (6 tests) for COMP-01/COMP-03/COMP-04

### Phase 4: Async Safety and Session Isolation
**Goal**: Parallel async agent review tasks each operate on their own DB session, eliminating intermittent `DetachedInstanceError` failures
**Depends on**: Phase 3
**Requirements**: REVW-05
**Success Criteria** (what must be TRUE):
  1. Running `run_multi_agent_review` with 3+ agents concurrently via `asyncio.gather` produces no `DetachedInstanceError` or `MissingGreenlet` exceptions
  2. The function signature accepts a `session_factory` callable instead of a shared `Session`, and each parallel task creates and closes its own session
  3. Existing callers of `run_multi_agent_review` in `agent_service.py` pass the session factory correctly and all existing tests continue to pass
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md — TDD refactor of all 3 asyncio.gather sites to session-per-task pattern with session_factory callable

### Phase 5: Agent Review Middleware
**Goal**: A middleware layer can intercept any generation step output, run mapped agents in parallel, merge their feedback into a refined result, and pass through unchanged when no agents are mapped
**Depends on**: Phase 4
**Requirements**: REVW-01, REVW-02, REVW-03, REVW-04
**Success Criteria** (what must be TRUE):
  1. Calling `review_step_output(phase, subsection_key, raw_output, owner_id, session_factory)` returns refined output when agents are mapped to that step
  2. When multiple agents are mapped to the same step, their reviews execute concurrently (confirmed via timing: N agents take ~1x not N×x time)
  3. The merge AI call returns output matching the expected wizard result JSON schema with explicit conflict-resolution rules applied (most specific and actionable suggestion wins, not a blend)
  4. When zero agents are mapped to a step, the function returns `raw_output` unchanged and makes zero additional LLM calls
  5. The response includes `agents_consulted` metadata listing which agents ran and their contribution summary
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — Core middleware with review_step_output entry point, agent lookup, parallel fan-out, session-per-task, and zero-agent pass-through (TDD)
- [ ] 05-02-PLAN.md — AI merge call with conflict-resolution prompt, schema validation per wizard_type, and agents_consulted summaries (TDD)

### Phase 6: Wizard Injection
**Goal**: Manual screenplay generation through the wizard automatically routes through agent review at each step, with review metadata surfaced in the response
**Depends on**: Phase 5
**Requirements**: REVW-01 (injection point)
**Success Criteria** (what must be TRUE):
  1. Running a wizard generation step for a phase that has mapped agents returns refined output visibly different from (or equal to, with justification) the raw generation
  2. The wizard run response includes `agents_consulted` showing which agents reviewed the step
  3. Running a wizard step for a phase with no mapped agents completes without error and returns raw output identical to pre-injection behavior
  4. Existing wizard generation tests pass without modification after injection
**Plans**: 1 plan

Plans:
- [ ] 06-01-PLAN.md — Wire review middleware into wizards.py, update WizardRunResponse schema with agents_consulted, and integration tests

### Phase 7: Frontend Pipeline Tree
**Goal**: Users can see exactly which agents are mapped to which pipeline steps, and can toggle individual agents in or out of the pipeline
**Depends on**: Phase 3
**Requirements**: TREE-01, TREE-02, TREE-03
**Success Criteria** (what must be TRUE):
  1. The pipeline tree renders inside `AgentManager.tsx` showing a collapsible hierarchy of phases, subsections, and agent badges
  2. Creating, editing, or deleting an agent causes the tree to refresh automatically without a page reload (React Query invalidation)
  3. An empty state message ("Create agents to see how they map to your pipeline") renders when the user has no agents
  4. Clicking the toggle on an individual agent badge excludes that agent from pipeline reviews; the toggle state persists and the tree reflects the exclusion visually
**Plans**: TBD

Plans:
- [ ] 07-01: Add `getPipelineMap()` API function and `QUERY_KEYS.PIPELINE_MAP` constant
- [ ] 07-02: Build `AgentPipelineTree.tsx` collapsible tree with phase → subsection → agent badge hierarchy
- [ ] 07-03: Add React Query invalidation for `PIPELINE_MAP` on all agent mutation hooks
- [ ] 07-04: Add empty state rendering and loading skeleton for the tree component
- [ ] 07-05: Build per-agent toggle UI and wire to backend exclude/include state

### Phase 8: YOLO Integration and Token Budget
**Goal**: YOLO auto-generation fires agent reviews at each step within configurable token and agent-count budgets, preventing cost explosion while preserving review quality
**Depends on**: Phase 6
**Requirements**: YOLO-01, YOLO-02
**Success Criteria** (what must be TRUE):
  1. Running a full YOLO auto-generation with 3 agents mapped fires agent reviews at each matching pipeline step without error
  2. Setting `MAX_AGENTS_PER_PIPELINE_STEP=2` limits reviews to the 2 highest-relevance agents even when 5 are mapped to a step
  3. Agents below the `AGENT_RELEVANCE_THRESHOLD` do not fire for steps where their relevance score is below the threshold
  4. A YOLO run with zero mapped agents completes at the same speed as pre-orchestration (no overhead introduced)
**Plans**: TBD

Plans:
- [ ] 08-01: Add `MAX_AGENTS_PER_PIPELINE_STEP` and `AGENT_RELEVANCE_THRESHOLD` config values to `config.py`
- [ ] 08-02: Implement relevance-score gating in the review middleware pipeline dispatcher
- [ ] 08-03: Confirm YOLO auto-generation flow routes through the same review middleware path as manual generation
- [ ] 08-04: Performance test a full YOLO run with 3 agents and verify total LLM call count matches expectations

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

Note: Phase 7 (Frontend) depends only on Phase 3, so it can proceed in parallel with Phases 4-6 once Phase 3 is complete.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. DB Foundation | 0/3 | Not started | - |
| 2. Pipeline Composer Service | 0/2 | Not started | - |
| 3. Pipeline Map API and CRUD Wiring | 0/2 | Not started | - |
| 4. Async Safety and Session Isolation | 0/1 | Not started | - |
| 5. Agent Review Middleware | 0/2 | Not started | - |
| 6. Wizard Injection | 0/1 | Not started | - |
| 7. Frontend Pipeline Tree | 0/5 | Not started | - |
| 8. YOLO Integration and Token Budget | 0/4 | Not started | - |
