# Roadmap: Screenwriting Assistant

## Milestones

- ✅ **v1.0 Agent Orchestration Pipeline** — Phases 1-8 (shipped 2026-03-12)
- ✅ **v2.0 Script Breakdown** — Phases 9-16 (shipped 2026-03-18)
- ✅ **v3.0 Shotlist & Production Breakdown** — Phases 17-25 (shipped 2026-03-20)
- 🚧 **v3.1 AI Shotlist Generation** — Phases 26-28 (in progress)

## Phases

<details>
<summary>✅ v1.0 Agent Orchestration Pipeline (Phases 1-8) — SHIPPED 2026-03-12</summary>

- [x] Phase 1: DB Foundation (3/3 plans) — completed 2026-03-11
- [x] Phase 2: Pipeline Composer Service (2/2 plans) — completed 2026-03-11
- [x] Phase 3: Pipeline Map API and CRUD Wiring (2/2 plans) — completed 2026-03-11
- [x] Phase 4: Async Safety and Session Isolation (1/1 plan) — completed 2026-03-11
- [x] Phase 5: Agent Review Middleware (2/2 plans) — completed 2026-03-12
- [x] Phase 6: Wizard Injection (1/1 plan) — completed 2026-03-12
- [x] Phase 7: Frontend Pipeline Tree (3/3 plans) — completed 2026-03-12
- [x] Phase 8: YOLO Integration and Token Budget (2/2 plans) — completed 2026-03-12

</details>

<details>
<summary>✅ v2.0 Script Breakdown (Phases 9-16) — SHIPPED 2026-03-18</summary>

- [x] Phase 9: Data Foundation (2/2 plans) — completed 2026-03-13
- [x] Phase 10: Breakdown API (2/2 plans) — completed 2026-03-13
- [x] Phase 11: AI Extraction Service (3/3 plans) — completed 2026-03-13
- [x] Phase 12: Staleness Hooks (2/2 plans) — completed 2026-03-14
- [x] Phase 13: Breakdown Page (3/3 plans) — completed 2026-03-18
- [x] Phase 14: Reverse Sync (2/2 plans) — completed 2026-03-18
- [x] Phase 15: Phase 13 Doc Closure & UI-05 Fix (1/1 plan) — completed 2026-03-18
- [x] Phase 16: Staleness Bug & Migration Upgrade (1/1 plan) — completed 2026-03-18

</details>

<details>
<summary>✅ v3.0 Shotlist & Production Breakdown (Phases 17-25) — SHIPPED 2026-03-20</summary>

- [x] Phase 17: Data Foundation (1/1 plan) — completed 2026-03-19
- [x] Phase 18: Two-Mode UI Shell (2/2 plans) — completed 2026-03-19
- [x] Phase 19: Shot CRUD API & Core Model (1/1 plan) — completed 2026-03-19
- [x] Phase 20: Shotlist Panel (2/2 plans) — completed 2026-03-19
- [x] Phase 21: Script Read View & Text Selection (1/1 plan) — completed 2026-03-19
- [x] Phase 22: Media Upload Backend (1/1 plan) — completed 2026-03-19
- [x] Phase 23: Assets Panel & Media Display (2/2 plans) — completed 2026-03-20
- [x] Phase 24: AI Chat for Breakdown (2/2 plans) — completed 2026-03-20
- [x] Phase 25: Staleness & Sync (2/2 plans) — completed 2026-03-20

</details>

### 🚧 v3.1 AI Shotlist Generation (In Progress)

- [x] **Phase 26: AI Shotlist Generation Service** - Backend service that reads script content and generates a complete shotlist with smart merge
- [ ] **Phase 27: Generate Shotlist UI & AI Badge** - Frontend trigger button, generation progress, and visual distinction for AI-generated shots
- [ ] **Phase 28: UX Improvements** - Media deletion, drag-and-drop shot reorder, and scene reorder staleness fix

## Phase Details

### Phase 26: AI Shotlist Generation Service
**Goal**: AI can generate a full shotlist from script content, assigning shots to scenes with all fields populated, and regeneration preserves user-edited shots
**Depends on**: Phase 25 (existing Shot CRUD, staleness infrastructure)
**Requirements**: AISG-01, AISG-02, AISG-03, AISG-04, AISG-05, AISG-06
**Success Criteria** (what must be TRUE):
  1. Calling the generation endpoint with a project ID produces shots covering all script scenes, with shot_size, camera_angle, camera_movement, description, and action fields populated
  2. Each generated shot is assigned to the correct scene (scene_item_id) and includes the source script passage in script_text
  3. Shots within each scene have a logical ordering (establishing shots before close-ups, action coverage before reactions)
  4. Regenerating the shotlist after a user has manually edited some shots preserves those edited shots unchanged while replacing/adding AI-generated ones
  5. The Shot model has a user_modified flag that is set to true on manual edit and an ai_generated flag that distinguishes AI-created shots from manual ones
**Plans:** 2/2 plans executed
Plans:
- [x] 26-01-PLAN.md — Schema foundation: delta migration, ORM + schema updates for user_modified/ai_generated, update endpoint flag
- [x] 26-02-PLAN.md — ShotlistGenerationService: AI context builder, structured output, smart merge, generate endpoint + tests

### Phase 27: Generate Shotlist UI & AI Badge
**Goal**: Users can trigger shotlist generation from the breakdown panel and visually distinguish AI-generated shots from manually-created ones
**Depends on**: Phase 26
**Requirements**: AISG-01 (frontend trigger), AISG-07
**Success Criteria** (what must be TRUE):
  1. A "Generate Shotlist" button is visible in the shotlist panel and triggers the backend generation endpoint
  2. While generation is in progress, the UI shows a loading/progress state and the button is disabled
  3. After generation completes, the shotlist panel refreshes to show all generated shots grouped by scene
  4. AI-generated shots display a subtle sparkle icon badge that is not present on manually-created shots
**Plans**: TBD

### Phase 28: UX Improvements
**Goal**: Users can delete media assets, reorder shots by dragging, and scene reordering correctly flags the shotlist as stale
**Depends on**: Phase 25 (staleness infrastructure, existing shotlist panel)
**Requirements**: MDIA-01, SMGT-01, SYNC-01
**Success Criteria** (what must be TRUE):
  1. Each media asset in the assets panel has a delete button that removes the asset after confirmation
  2. Shots in the shotlist panel can be reordered by dragging and dropping (arrow buttons are removed)
  3. Drag-and-drop reorder persists the new sort_order to the backend and survives page refresh
  4. Reordering scenes in the screenplay editor marks the shotlist as stale (staleness banner appears in breakdown mode)
**Plans**: TBD

## Progress

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
| 9. Data Foundation | v2.0 | 2/2 | Complete | 2026-03-13 |
| 10. Breakdown API | v2.0 | 2/2 | Complete | 2026-03-13 |
| 11. AI Extraction Service | v2.0 | 3/3 | Complete | 2026-03-13 |
| 12. Staleness Hooks | v2.0 | 2/2 | Complete | 2026-03-14 |
| 13. Breakdown Page | v2.0 | 3/3 | Complete | 2026-03-18 |
| 14. Reverse Sync | v2.0 | 2/2 | Complete | 2026-03-18 |
| 15. Phase 13 Doc Closure & UI-05 Fix | v2.0 | 1/1 | Complete | 2026-03-18 |
| 16. Staleness Bug & Migration Upgrade | v2.0 | 1/1 | Complete | 2026-03-18 |
| 17. Data Foundation | v3.0 | 1/1 | Complete | 2026-03-19 |
| 18. Two-Mode UI Shell | v3.0 | 2/2 | Complete | 2026-03-19 |
| 19. Shot CRUD API & Core Model | v3.0 | 1/1 | Complete | 2026-03-19 |
| 20. Shotlist Panel | v3.0 | 2/2 | Complete | 2026-03-19 |
| 21. Script Read View & Text Selection | v3.0 | 1/1 | Complete | 2026-03-19 |
| 22. Media Upload Backend | v3.0 | 1/1 | Complete | 2026-03-19 |
| 23. Assets Panel & Media Display | v3.0 | 2/2 | Complete | 2026-03-20 |
| 24. AI Chat for Breakdown | v3.0 | 2/2 | Complete | 2026-03-20 |
| 25. Staleness & Sync | v3.0 | 2/2 | Complete | 2026-03-20 |
| 26. AI Shotlist Generation Service | v3.1 | 2/2 | Complete | 2026-03-20 |
| 27. Generate Shotlist UI & AI Badge | v3.1 | 0/? | Not started | - |
| 28. UX Improvements | v3.1 | 0/? | Not started | - |
