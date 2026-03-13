# Roadmap: Screenwriting Assistant

## Milestones

- [x] **v1.0 Agent Orchestration Pipeline** - Phases 1-8 (shipped 2026-03-12)
- [ ] **v2.0 Script Breakdown** - Phases 9-14 (in progress)

## Phases

<details>
<summary>v1.0 Agent Orchestration Pipeline (Phases 1-8) - SHIPPED 2026-03-12</summary>

- [x] **Phase 1: DB Foundation** - Create `agent_pipeline_maps` table, SQLAlchemy model, and Pydantic schemas
- [x] **Phase 2: Pipeline Composer Service** - Build `pipeline_composer.py` with AI mapping, hash-based cache, and dirty-flag gating
- [x] **Phase 3: Pipeline Map API and CRUD Wiring** - Expose GET endpoint and wire agent CRUD to trigger re-composition via BackgroundTasks
- [x] **Phase 4: Async Safety and Session Isolation** - Fix shared DB session bug in `run_multi_agent_review` for safe concurrent use
- [x] **Phase 5: Agent Review Middleware** - Build `agent_review_middleware.py` with parallel fan-out, merge AI call, and pass-through bypass
- [x] **Phase 6: Wizard Injection** - Inject review middleware into `wizards.py` generation path and surface `agents_consulted` metadata
- [x] **Phase 7: Frontend Pipeline Tree** - Build `AgentPipelineTree.tsx` collapsible tree component embedded in `AgentManager.tsx`
- [x] **Phase 8: YOLO Integration and Token Budget** - Wire YOLO auto-generation through review middleware with configurable agent budgets

</details>

### v2.0 Script Breakdown

**Milestone Goal:** AI-powered script breakdown that extracts production elements (characters, locations, props, wardrobe, vehicles) into master lists linked to scenes, with full bidirectional sync between breakdown and script.

- [ ] **Phase 9: Data Foundation** - Migration, SQLAlchemy models, Pydantic schemas for breakdown tables and staleness column
- [x] **Phase 10: Breakdown API** - CRUD endpoints for elements, scene links, manual creation, summary, and extraction trigger (completed 2026-03-13)
- [ ] **Phase 11: AI Extraction Service** - Structured output extraction with deduplication, user-modified protection, and scene link reconciliation
- [ ] **Phase 12: Staleness Hooks** - Wire save/generate paths to set breakdown_stale flag and clear it on re-extraction
- [ ] **Phase 13: Breakdown Page** - Dedicated frontend page with category tabs, master lists, inline editing, and scene chips
- [ ] **Phase 14: Reverse Sync** - User-initiated actions to push breakdown elements back to project data (e.g., "Add to Characters")

## Phase Details

### Phase 9: Data Foundation
**Goal**: The database schema for breakdown elements, scene links, audit runs, and staleness tracking exists and is ready for use by the API and service layers
**Depends on**: Nothing (first phase of v2.0; builds on existing projects and list_items tables)
**Requirements**: BKDN-01, BKDN-02, BKDN-03, BKDN-04
**Success Criteria** (what must be TRUE):
  1. Running the migration creates `breakdown_elements`, `element_scene_links`, and `breakdown_runs` tables with all columns, indexes, and constraints matching the architecture spec
  2. The `breakdown_elements` table enforces a unique constraint on `(project_id, category, name)` and supports the `user_modified` flag and `is_deleted` soft-delete
  3. The `projects` table has a `breakdown_stale` boolean column defaulting to FALSE
  4. SQLAlchemy models (`BreakdownElement`, `ElementSceneLink`, `BreakdownRun`) are importable, have cascade-delete relationships to `Project`, and `ElementSceneLink` cascades on `ListItem` deletion
  5. Pydantic request/response schemas (`BreakdownElementCreate`, `BreakdownElementUpdate`, `BreakdownElementResponse`, `BreakdownSummaryResponse`, `BreakdownRunResponse`, `SceneLinkCreate`) validate correctly and round-trip from ORM models
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md -- SQL migration for breakdown_elements, element_scene_links, breakdown_runs tables and breakdown_stale column on projects
- [ ] 09-02-PLAN.md -- SQLAlchemy models, Pydantic schemas, and relationship wiring

### Phase 10: Breakdown API
**Goal**: The backend exposes a complete REST API for breakdown element CRUD, scene link management, extraction triggering, and summary queries
**Depends on**: Phase 9
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07
**Success Criteria** (what must be TRUE):
  1. `POST /api/breakdown/extract/{project_id}` accepts a request and returns a `BreakdownRunResponse` (extraction logic stubbed until Phase 11)
  2. `GET /api/breakdown/elements/{project_id}` returns elements filtered by category query param, excluding soft-deleted by default
  3. `PUT /api/breakdown/element/{element_id}` updates an element and sets `user_modified=true`; `DELETE` soft-deletes; `POST /api/breakdown/elements/{project_id}` creates with `source='user'`
  4. `POST/DELETE /api/breakdown/element/{element_id}/scenes` adds and removes scene links correctly
  5. `GET /api/breakdown/summary/{project_id}` returns staleness status, category counts, and last run info
**Plans**: 2 plans

Plans:
- [ ] 10-01-PLAN.md -- breakdown.py router with element CRUD endpoints (API-02 through API-05) and main.py mount
- [ ] 10-02-PLAN.md -- Scene link endpoints (API-06), summary endpoint (API-07), extraction trigger stub (API-01), and test suite

### Phase 11: AI Extraction Service
**Goal**: AI analyzes screenplay content and project data to produce structured JSON of production elements across 5 categories, with deduplication, user-modified protection, and scene link reconciliation
**Depends on**: Phase 10
**Requirements**: EXTR-01, EXTR-02, EXTR-03, EXTR-04, EXTR-05, SYNC-01, SYNC-02
**Success Criteria** (what must be TRUE):
  1. Calling `BreakdownService.extract(project_id)` gathers screenplay content and character names, sends a structured-output AI call, and persists elements to the database with scene links
  2. The extraction uses low temperature (0.1-0.2) and the prompt restricts output to elements physically present on screen (not mentioned in dialogue or backstory)
  3. The same element described differently across scenes (e.g., "GUN" and "revolver") maps to one master list entry with a canonical name
  4. Re-extraction preserves elements where `user_modified=true` (name, description, and metadata unchanged) and does not resurrect soft-deleted elements
  5. Each extracted element is linked to the scene ListItems where it appears via `element_scene_links` records
**Plans**: 3 plans

Plans:
- [ ] 11-01-PLAN.md -- BreakdownService skeleton, extraction context builder (screenplay + character names), and structured output schema
- [ ] 11-02-PLAN.md -- AI extraction call with structured outputs, response parsing, and element upsert with user_modified/is_deleted protection
- [ ] 11-03-PLAN.md -- Deduplication logic, scene link reconciliation, audit run recording, and integration tests

### Phase 12: Staleness Hooks
**Goal**: Saving screenplay content or regenerating scenes automatically sets the project's breakdown as stale, and re-extraction clears it
**Depends on**: Phase 11
**Requirements**: SYNC-03, SYNC-04
**Success Criteria** (what must be TRUE):
  1. Saving content via the phase_data PUT endpoint for write/scenes phases sets `project.breakdown_stale = true` when a breakdown exists
  2. Running `apply_wizard_result_to_db()` for `script_writer_wizard` sets `project.breakdown_stale = true`
  3. Creating, updating, or deleting scene ListItems sets `project.breakdown_stale = true`
  4. Running a successful extraction via `BreakdownService.extract()` clears `breakdown_stale` to false and creates a new `breakdown_runs` audit record
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md -- mark_breakdown_stale() utility and hooks in phase_data.py, wizards.py, and list_items.py
- [ ] 12-02-PLAN.md -- Wire extraction to clear stale flag, create audit run on completion, and integration tests

### Phase 13: Breakdown Page
**Goal**: Users can view, filter, edit, and manage their script breakdown from a dedicated page in the project workspace
**Depends on**: Phase 10, Phase 11, Phase 12
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06, UI-07, UI-08
**Success Criteria** (what must be TRUE):
  1. A "Breakdown" tab appears in the project workspace navigation (separate from phase tabs) and navigates to a dedicated breakdown page
  2. The page shows category tabs (Characters, Locations, Props, Wardrobe, Vehicles) with count badges reflecting the number of elements per category
  3. Each element in the master list displays its name, description, scene count, source badge (AI/User), and user-modified indicator, with inline editing for name and description
  4. Scene chips on each element show linked scenes and are clickable to navigate to the scene in the workspace
  5. "Extract Breakdown" button triggers first extraction; a staleness banner with "Refresh" button appears when the breakdown is outdated; empty state shows a clear CTA when no breakdown exists
  6. The "Add Element" dialog allows manually creating new elements with category, name, and description
**Plans**: 3 plans

Plans:
- [ ] 13-01-PLAN.md -- TypeScript types, API client functions, React Query hooks, route in App.tsx, and breakdown tab in PhaseNavigation.tsx
- [ ] 13-02-PLAN.md -- BreakdownPage layout with CategoryTabs, ElementList, ElementCard (inline editing, source badges, scene chips), and staleness banner
- [ ] 13-03-PLAN.md -- AddElementDialog, empty state, extraction trigger UX, and soft-delete with optimistic updates

### Phase 14: Reverse Sync
**Goal**: Users can push breakdown elements back to project data through explicit actions, keeping the screenplay as source of truth
**Depends on**: Phase 13
**Requirements**: SYNC-05
**Success Criteria** (what must be TRUE):
  1. An "Add to Characters" button on character elements in the breakdown creates a corresponding ListItem in the `story.characters` PhaseData
  2. The action only appears for elements not already present in the characters list (duplicate detection by name)
  3. After adding, the breakdown element shows a "Synced" indicator and the character appears in the project's characters phase
**Plans**: 2 plans

Plans:
- [ ] 14-01-PLAN.md -- Backend endpoint for reverse sync (character element to ListItem creation) with duplicate detection
- [ ] 14-02-PLAN.md -- Frontend "Add to Characters" button, synced indicator, and integration with existing characters phase

## Progress

**Execution Order:**
Phases execute in numeric order: 9 -> 10 -> 11 -> 12 -> 13 -> 14

Note: Phase 13 (Frontend) depends on Phases 10, 11, and 12. Frontend API client/types work (Plan 13-01) can begin once Phase 10 is complete.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. DB Foundation | v1.0 | 3/3 | Complete | 2026-03-11 |
| 2. Pipeline Composer Service | v1.0 | 2/2 | Complete | 2026-03-11 |
| 3. Pipeline Map API and CRUD Wiring | v1.0 | 2/2 | Complete | 2026-03-11 |
| 4. Async Safety and Session Isolation | v1.0 | 1/1 | Complete | 2026-03-11 |
| 5. Agent Review Middleware | v1.0 | 2/2 | Complete | 2026-03-12 |
| 6. Wizard Injection | v1.0 | 1/1 | Complete | 2026-03-12 |
| 7. Frontend Pipeline Tree | v1.0 | 3/3 | Complete | 2026-03-12 |
| 8. YOLO Integration and Token Budget | v1.0 | 2/2 | Complete | 2026-03-12 |
| 9. Data Foundation | v2.0 | 0/2 | Not started | - |
| 10. Breakdown API | 2/2 | Complete    | 2026-03-13 | - |
| 11. AI Extraction Service | 2/3 | In Progress|  | - |
| 12. Staleness Hooks | v2.0 | 0/2 | Not started | - |
| 13. Breakdown Page | v2.0 | 0/3 | Not started | - |
| 14. Reverse Sync | v2.0 | 0/2 | Not started | - |
