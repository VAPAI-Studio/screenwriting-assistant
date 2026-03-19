# Roadmap: Screenwriting Assistant

## Milestones

- ✅ **v1.0 Agent Orchestration Pipeline** — Phases 1-8 (shipped 2026-03-12)
- ✅ **v2.0 Script Breakdown** — Phases 9-16 (shipped 2026-03-18)
- [ ] **v3.0 Shotlist & Production Breakdown** — Phases 17-25 (in progress)

## Phases

<details>
<summary>v1.0 Agent Orchestration Pipeline (Phases 1-8) — SHIPPED 2026-03-12</summary>

- [x] **Phase 1: DB Foundation** — Create `agent_pipeline_maps` table, SQLAlchemy model, and Pydantic schemas (completed 2026-03-11)
- [x] **Phase 2: Pipeline Composer Service** — Build `pipeline_composer.py` with AI mapping, hash-based cache, and dirty-flag gating (completed 2026-03-11)
- [x] **Phase 3: Pipeline Map API and CRUD Wiring** — Expose GET endpoint and wire agent CRUD to trigger re-composition via BackgroundTasks (completed 2026-03-11)
- [x] **Phase 4: Async Safety and Session Isolation** — Fix shared DB session bug in `run_multi_agent_review` for safe concurrent use (completed 2026-03-11)
- [x] **Phase 5: Agent Review Middleware** — Build `agent_review_middleware.py` with parallel fan-out, merge AI call, and pass-through bypass (completed 2026-03-12)
- [x] **Phase 6: Wizard Injection** — Inject review middleware into `wizards.py` generation path and surface `agents_consulted` metadata (completed 2026-03-12)
- [x] **Phase 7: Frontend Pipeline Tree** — Build `AgentPipelineTree.tsx` collapsible tree component embedded in `AgentManager.tsx` (completed 2026-03-12)
- [x] **Phase 8: YOLO Integration and Token Budget** — Wire YOLO auto-generation through review middleware with configurable agent budgets (completed 2026-03-12)

</details>

<details>
<summary>v2.0 Script Breakdown (Phases 9-16) — SHIPPED 2026-03-18</summary>

- [x] **Phase 9: Data Foundation** — Migration, SQLAlchemy models, Pydantic schemas for breakdown tables and staleness column (completed 2026-03-13)
- [x] **Phase 10: Breakdown API** — CRUD endpoints for elements, scene links, manual creation, summary, and extraction trigger (completed 2026-03-13)
- [x] **Phase 11: AI Extraction Service** — Structured output extraction with deduplication, user-modified protection, and scene link reconciliation (completed 2026-03-13)
- [x] **Phase 12: Staleness Hooks** — Wire save/generate paths to set breakdown_stale flag and clear it on re-extraction (completed 2026-03-14)
- [x] **Phase 13: Breakdown Page** — Dedicated frontend page with category tabs, master lists, inline editing, and scene chips (completed 2026-03-18)
- [x] **Phase 14: Reverse Sync** — User-initiated actions to push breakdown elements back to project data (completed 2026-03-18)
- [x] **Phase 15: Phase 13 Documentation Closure & UI-05 Fix** — Formal verification, UI-07/UI-08 documentation, scene chip route fix (completed 2026-03-18)
- [x] **Phase 16: Staleness Bug & Migration Upgrade Path** — Fix scene_wizard staleness hook; delta migration for Docker auto-upgrade (completed 2026-03-18)

</details>

### v3.0 Shotlist & Production Breakdown (In Progress)

**Milestone Goal:** Add interactive shotlist creation from script, media uploads for pre-production assets, and restructure the app into two distinct modes (Screenwriting / Script Breakdown).

- [x] **Phase 17: Data Foundation** - Shots table, asset_media table, shotlist_stale column, and delta migration (completed 2026-03-19)
- [ ] **Phase 18: Two-Mode UI Shell** - Top-level mode toggle, breakdown route, 3-panel layout skeleton with distinct visual identity
- [ ] **Phase 19: Shot CRUD API & Core Model** - Backend endpoints for shot creation, reading, updating, deleting, and freeform field schema
- [ ] **Phase 20: Shotlist Panel** - Frontend shotlist table with scene grouping, inline editing, reordering, and empty state
- [ ] **Phase 21: Script Read View & Text Selection** - Read-only script rendering with text selection, floating bar, and selection-to-shot creation
- [ ] **Phase 22: Media Upload Backend** - Upload endpoint with file validation, Pillow thumbnail generation, and media CRUD API
- [ ] **Phase 23: Assets Panel & Media Display** - Left panel script/assets toggle, breakdown element browsing, media thumbnails, and audio playback
- [ ] **Phase 24: AI Chat for Breakdown** - Extend SidebarChat with shotlist and breakdown context awareness, shot creation and modification via conversation
- [ ] **Phase 25: Staleness & Sync** - Shotlist staleness hooks on script save/generate, staleness banner, and character name propagation

## Phase Details

### Phase 17: Data Foundation
**Goal**: Database schema exists to support shots, media uploads, and shotlist staleness tracking
**Depends on**: Phase 16 (v2.0 complete)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-06
**Success Criteria** (what must be TRUE):
  1. `shots` table exists with project_id, scene_item_id, shot_number, script_text, script_range (JSONB), fields (JSONB), sort_order, and source columns (DATA-01)
  2. `asset_media` table exists with project_id, element_id, shot_id, file_type, file_path, thumbnail_path, original_filename, file_size_bytes, and metadata columns (DATA-02)
  3. `shotlist_stale` boolean column exists on the projects table (DATA-03)
  4. Delta migration in `delta/` is idempotent and applies cleanly on existing Docker volumes without data loss (DATA-06)
**Plans**: 1 plan

Plans:
- [ ] 17-01-PLAN.md — Delta migration, ORM models, Pydantic schemas, and tests for shots, shot_elements, and asset_media tables

### Phase 18: Two-Mode UI Shell
**Goal**: Users can switch between Screenwriting and Script Breakdown modes with distinct visual identities
**Depends on**: Phase 17
**Requirements**: MODE-01, MODE-02, MODE-03, MODE-04, MODE-05
**Success Criteria** (what must be TRUE):
  1. Header contains a toggle that switches between "Screenwriting" and "Script Breakdown" modes (MODE-01)
  2. Selecting Screenwriting mode renders the existing workspace with zero changes to existing components (MODE-02)
  3. Selecting Script Breakdown mode renders a 3-panel layout skeleton: left panel, center shotlist area, right chat area (MODE-03)
  4. The two modes have visually distinct color schemes (warm vs cool) while sharing typography and component shapes (MODE-04)
  5. Switching modes preserves the current project context without data loss (MODE-05)
**Plans**: TBD

Plans:
- [ ] 18-01: ModeToggle component, breakdown route, and CSS variable scoping for dual visual identity
- [ ] 18-02: BreakdownLayout 3-panel skeleton with placeholder panels

### Phase 19: Shot CRUD API & Core Model
**Goal**: Backend API exists for creating, reading, updating, and deleting shots with freeform fields
**Depends on**: Phase 17
**Requirements**: DATA-04, SHOT-01, SHOT-02
**Success Criteria** (what must be TRUE):
  1. POST endpoint creates a shot with freeform text fields and returns the created shot (SHOT-01, SHOT-02)
  2. GET endpoint returns all shots for a project grouped by scene (DATA-04)
  3. PUT endpoint updates any combination of shot fields (DATA-04)
  4. DELETE endpoint removes a shot and returns success (DATA-04)
  5. Shot fields JSONB supports all standard fields: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes (SHOT-02)
**Plans**: TBD

Plans:
- [ ] 19-01: Shots API endpoints (list, create, get, update, delete, reorder) with tests

### Phase 20: Shotlist Panel
**Goal**: Users can view, create, edit, reorder, and delete shots in a table grouped by scene
**Depends on**: Phase 18, Phase 19
**Requirements**: SHOT-03, SHOT-04, SHOT-05, SHOT-06, SHOT-07, SHOT-08
**Success Criteria** (what must be TRUE):
  1. Shotlist displays as a table/grid in the center area of breakdown mode with scene headers grouping shots (SHOT-03, SHOT-07)
  2. User can edit shot fields inline by clicking on cells in the shotlist table (SHOT-04)
  3. User can delete a shot from the shotlist (SHOT-05)
  4. Shots have a visible order within each scene and can be reordered (SHOT-06)
  5. When no shots exist, the panel shows a clear call-to-action to create the first shot (SHOT-08)
**Plans**: TBD

Plans:
- [ ] 20-01: ShotlistPanel component with scene-grouped table, ShotRow with inline editing
- [ ] 20-02: Shot reordering, deletion, empty state CTA, and "Add Shot" button

### Phase 21: Script Read View & Text Selection
**Goal**: Users can view their script in breakdown mode and create shots by selecting text
**Depends on**: Phase 19, Phase 20
**Requirements**: SELC-01, SELC-02, SELC-03, SELC-04, SELC-05
**Success Criteria** (what must be TRUE):
  1. Left panel in breakdown mode renders the screenplay content as read-only text (SELC-01)
  2. User can highlight/select text in the script view and see a floating bar showing line count and "+ Add Shot" button (SELC-02, SELC-03)
  3. Clicking "+ Add Shot" creates a new shot pre-populated with the selected text and linked to the corresponding scene (SELC-04)
  4. The selection bar dismisses when clicking outside or pressing the X button (SELC-05)
**Plans**: TBD

Plans:
- [ ] 21-01: ScriptReadView component with text selection, SelectionBar, and selection-to-shot creation flow

### Phase 22: Media Upload Backend
**Goal**: Backend supports uploading, storing, thumbnailing, and managing image and audio files for breakdown elements
**Depends on**: Phase 17
**Requirements**: DATA-05, MDIA-01, MDIA-02, MDIA-05, MDIA-06, MDIA-07
**Success Criteria** (what must be TRUE):
  1. POST endpoint accepts image uploads (JPEG, PNG, WebP) and audio uploads (MP3, WAV, M4A) linked to breakdown elements (MDIA-01, MDIA-02)
  2. Image uploads generate server-side thumbnails via Pillow (MDIA-06)
  3. Upload endpoint enforces file type validation and rejects files over 20MB (MDIA-07)
  4. DELETE endpoint removes the media record and deletes the file from disk (MDIA-05)
  5. GET endpoint lists all media for a project or element (DATA-05)
**Plans**: TBD

Plans:
- [ ] 22-01: Media upload endpoint with Pillow thumbnails, file validation, size limits, and CRUD API with tests

### Phase 23: Assets Panel & Media Display
**Goal**: Users can browse breakdown elements with attached media and upload new files from the assets panel
**Depends on**: Phase 18, Phase 22
**Requirements**: ASST-01, ASST-02, ASST-03, ASST-04, ASST-05, MDIA-03, MDIA-04
**Success Criteria** (what must be TRUE):
  1. Left panel has a toggle between "Script" view and "Assets" view (ASST-01)
  2. Assets view shows existing breakdown elements grouped by category (Characters, Locations, Props, Wardrobe, Vehicles) (ASST-02)
  3. Each element displays its attached images as thumbnails and audio files with playable controls (play, pause, stop) (ASST-03, MDIA-03, MDIA-04)
  4. User can upload media directly from the assets panel via drag-and-drop or file picker (ASST-04)
  5. Toggling between Script and Assets preserves panel state including scroll position and expanded items (ASST-05)
**Plans**: TBD

Plans:
- [ ] 23-01: Left panel toggle (Script/Assets), AssetsPanel with category-grouped elements
- [ ] 23-02: MediaThumbnail, audio player controls, drag-and-drop upload zone

### Phase 24: AI Chat for Breakdown
**Goal**: Users can converse with AI in breakdown mode to create and modify shots
**Depends on**: Phase 19, Phase 20
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05
**Success Criteria** (what must be TRUE):
  1. Right sidebar in breakdown mode shows the AI chat by extending the existing SidebarChat component (CHAT-01)
  2. AI chat responses reflect awareness of the current project's shotlist data (CHAT-02)
  3. AI chat responses reflect awareness of the current project's breakdown elements (CHAT-03)
  4. User can ask AI to create a new shot and sees a preview/confirmation before it is created (CHAT-04)
  5. User can ask AI to modify existing shot fields and sees proposed changes before they are applied (CHAT-05)
**Plans**: TBD

Plans:
- [ ] 24-01: Extend SidebarChat with breakdown mode context injection (shotlist + elements)
- [ ] 24-02: AI shot creation and modification tool-use with user confirmation flow

### Phase 25: Staleness & Sync
**Goal**: Script changes are detected and the shotlist is flagged as stale, keeping breakdown mode in sync with screenplay edits
**Depends on**: Phase 17, Phase 18
**Requirements**: SYNC-01, SYNC-02, SYNC-03, SYNC-04
**Success Criteria** (what must be TRUE):
  1. Saving or generating script content sets `shotlist_stale = true` on the project (SYNC-01)
  2. Breakdown mode displays a visible staleness banner when the shotlist is stale (SYNC-02)
  3. Character name changes in Screenwriting mode propagate to Breakdown via the existing staleness pattern (SYNC-03)
  4. Staleness hooks are placed in the same code locations as the existing v2.0 breakdown_stale hooks (SYNC-04)
**Plans**: TBD

Plans:
- [ ] 25-01: Shotlist staleness hooks in save/generate paths, staleness banner in breakdown mode

## Progress

**Execution Order:**
Phases execute in numeric order: 17 -> 18 -> 19 -> 20 -> 21 -> 22 -> 23 -> 24 -> 25

Note: Phase 19 and Phase 22 can execute in parallel (both depend only on Phase 17). Phase 18 can proceed concurrently with Phase 19. Phase 20 requires both 18 and 19. Phase 23 requires both 18 and 22. Phase 24 requires 19 and 20. Phase 25 requires 17 and 18.

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
| 17. Data Foundation | 1/1 | Complete   | 2026-03-19 | - |
| 18. Two-Mode UI Shell | v3.0 | 0/2 | Not started | - |
| 19. Shot CRUD API & Core Model | v3.0 | 0/1 | Not started | - |
| 20. Shotlist Panel | v3.0 | 0/2 | Not started | - |
| 21. Script Read View & Text Selection | v3.0 | 0/1 | Not started | - |
| 22. Media Upload Backend | v3.0 | 0/1 | Not started | - |
| 23. Assets Panel & Media Display | v3.0 | 0/2 | Not started | - |
| 24. AI Chat for Breakdown | v3.0 | 0/2 | Not started | - |
| 25. Staleness & Sync | v3.0 | 0/1 | Not started | - |
