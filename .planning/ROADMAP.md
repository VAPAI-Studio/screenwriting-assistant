# Roadmap: Screenwriting Assistant

## Milestones

- ✅ **v1.0 Agent Orchestration Pipeline** — Phases 1-8 (shipped 2026-03-12)
- ✅ **v2.0 Script Breakdown** — Phases 9-16 (shipped 2026-03-18)
- ✅ **v3.0 Shotlist & Production Breakdown** — Phases 17-25 (shipped 2026-03-20)
- ✅ **v3.1 AI Shotlist Generation** — Phases 26-28 (shipped 2026-03-21)
- 🚧 **v3.2 Storyboard Mode** — Phases 29-31 (planned)
- 🔮 **v4.0 Element Detail Pages & Script Linking** — Phases 32-34 (future)
- 🔮 **v5.0 User Management & API Access** — Phases 35-37 (future)

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

### ✅ v3.1 AI Shotlist Generation (Shipped 2026-03-21)

- [x] **Phase 26: AI Shotlist Generation Service** - Backend service that reads script content and generates a complete shotlist with smart merge (completed 2026-03-20)
- [x] **Phase 27: Generate Shotlist UI & AI Badge** - Frontend trigger button, generation progress, and visual distinction for AI-generated shots (completed 2026-03-21)
- [x] **Phase 28: UX Improvements** - Media deletion, drag-and-drop shot reorder, and scene reorder staleness fix (completed 2026-03-21)

#### Phase 26: AI Shotlist Generation Service
**Goal**: AI can generate a full shotlist from script content, assigning shots to scenes with all fields populated, and regeneration preserves user-edited shots
**Depends on**: Phase 25 (existing Shot CRUD, staleness infrastructure)
**Requirements**: AISG-01, AISG-02, AISG-03, AISG-04, AISG-05, AISG-06
**Success Criteria** (what must be TRUE):
  1. Calling the generation endpoint with a project ID produces shots covering all script scenes, with shot_size, camera_angle, camera_movement, description, and action fields populated
  2. Each generated shot is assigned to the correct scene (scene_item_id) and includes the source script passage in script_text
  3. Shots within each scene have a logical ordering (establishing shots before close-ups, action coverage before reactions)
  4. Regenerating the shotlist after a user has manually edited some shots preserves those edited shots unchanged while replacing/adding AI-generated ones
  5. The Shot model has a user_modified flag that is set to true on manual edit and an ai_generated flag that distinguishes AI-created shots from manual ones
**Plans:** 2/2 plans complete
Plans:
- [x] 26-01-PLAN.md — Schema foundation: delta migration, ORM + schema updates for user_modified/ai_generated, update endpoint flag
- [x] 26-02-PLAN.md — ShotlistGenerationService: AI context builder, structured output, smart merge, generate endpoint + tests

#### Phase 27: Generate Shotlist UI & AI Badge
**Goal**: Users can trigger shotlist generation from the breakdown panel and visually distinguish AI-generated shots from manually-created ones
**Depends on**: Phase 26
**Requirements**: AISG-01 (frontend trigger), AISG-07
**Success Criteria** (what must be TRUE):
  1. A "Generate Shotlist" button is visible in the shotlist panel and triggers the backend generation endpoint
  2. While generation is in progress, the UI shows a loading/progress state and the button is disabled
  3. After generation completes, the shotlist panel refreshes to show all generated shots grouped by scene
  4. AI-generated shots display a subtle sparkle icon badge that is not present on manually-created shots
**Plans:** 1/1 plans complete
Plans:
- [x] 27-01-PLAN.md — Type updates, API method, generate button + mutation, sparkle badge on AI shots

#### Phase 28: UX Improvements
**Goal**: Users can delete media assets, reorder shots by dragging, and scene reordering correctly flags the shotlist as stale
**Depends on**: Phase 25 (staleness infrastructure, existing shotlist panel)
**Requirements**: MDIA-01, SMGT-01, SYNC-01
**Success Criteria** (what must be TRUE):
  1. Each media asset in the assets panel has a delete button that removes the asset after confirmation
  2. Shots in the shotlist panel can be reordered by dragging and dropping (arrow buttons are removed)
  3. Drag-and-drop reorder persists the new sort_order to the backend and survives page refresh
  4. Reordering scenes in the screenplay editor marks the shotlist as stale (staleness banner appears in breakdown mode)
**Plans:** 3/3 plans complete
Plans:
- [x] 28-01-PLAN.md — Media asset deletion UI: trash button overlay on MediaThumbnail + AudioPlayer, window.confirm guard, deleteMedia mutation
- [x] 28-02-PLAN.md — Drag-and-drop shot reorder: install @hello-pangea/dnd, replace ReorderControls with DnD in SceneGroup, wire reorderMutation on drop
- [x] 28-03-PLAN.md — Scene reorder staleness fix: add _mark_shotlist_stale call to reorder_list_items endpoint

### 🚧 v3.2 Storyboard Mode (Planned)

- [ ] **Phase 29: Storyboard Data Model & Mode Shell** - DB model for storyboard frames, CRUD API, third mode toggle (deep purple/violet identity), project-level style setting
- [ ] **Phase 30: Storyboard Grid UI** - Grid of shot cards each with a frame slot, upload frames, mark one as selected/hero, multiple frames per shot gallery
- [ ] **Phase 31: AI Frame Generation (Google Imagen)** - Vertex AI / Imagen integration, per-shot "Generate Frame" button using shot fields as prompt, Photorealistic / Cinematic / Animated styles

#### Phase 29: Storyboard Data Model & Mode Shell
**Goal**: A third "Storyboard" mode exists in the app (deep purple/violet identity), backed by a StoryboardFrame model that links frames to shots
**Depends on**: Phase 19 (Shot model), Phase 22 (media upload infrastructure)
**Requirements**: SB-01, SB-02
**Success Criteria** (what must be TRUE):
  1. The mode toggle has three options: Screenwriting / Breakdown / Storyboard, with Storyboard using a deep purple/violet accent color
  2. A StoryboardFrame model exists with fields: shot_id, file_path, thumbnail_path, file_type (image/video), is_selected, generation_source (user/ai), generation_style
  3. Full CRUD API exists for storyboard frames (create, list by project/shot, update is_selected, delete)
  4. Each project has a storyboard_style setting (photorealistic / cinematic / animated)
  5. The Storyboard page renders with correct purple identity (empty state acceptable)
**Plans:** 2 plans
Plans:
- [ ] 29-01-PLAN.md — StoryboardFrame model, delta migration, schemas, CRUD API + tests (SB-02)
- [ ] 29-02-PLAN.md — Three-mode toggle, purple CSS theme, StoryboardView shell, TypeScript types + API methods (SB-01)

#### Phase 30: Storyboard Grid UI
**Goal**: Users can view all shots as a grid of frame cards, upload images/video per shot, and mark one frame as the selected/hero frame
**Depends on**: Phase 29
**Requirements**: SB-03, SB-04, SB-05
**Success Criteria** (what must be TRUE):
  1. Storyboard page shows a grid of cards — one per shot — ordered by scene then shot_number
  2. Each card shows: scene label, shot number, shot description (truncated), and the selected frame image (or empty frame placeholder)
  3. Clicking a card opens a frame gallery modal showing all frames for that shot with upload button and "mark as selected" action
  4. Uploaded frames appear as thumbnails; the selected frame is visually highlighted
  5. Empty shots show a placeholder frame with "Upload" and "Generate with AI" (disabled until Phase 31) actions
**Plans:** 2 plans
Plans:
- [ ] 30-01-PLAN.md — ShotCard component and StoryboardView grid layout grouped by scene (SB-03, SB-04)
- [ ] 30-02-PLAN.md — FrameGalleryModal with upload, mark-as-selected, delete, and disabled AI generate button (SB-04, SB-05)

#### Phase 31: AI Frame Generation (Google Imagen)
**Goal**: Users can generate a storyboard frame for any shot using Google Imagen, with the result stored and displayable in the grid
**Depends on**: Phase 30
**Requirements**: SB-06, SB-07
**Success Criteria** (what must be TRUE):
  1. A Google Vertex AI / Imagen client exists in the backend (google-cloud-aiplatform SDK)
  2. POST /api/storyboard/{project_id}/shots/{shot_id}/generate triggers image generation and stores the result as a StoryboardFrame with generation_source=ai
  3. The generation prompt is built from shot fields: description, action, camera_angle, shot_size, scene context, and project storyboard_style
  4. "Generate with AI" button in the frame gallery fires the endpoint, shows a spinner, and displays the result when done
  5. Generated frames are automatically set as selected if no frame was previously selected for that shot
**Plans:** 2 plans
Plans:
- [ ] 31-01-PLAN.md — ImagenService with prompt builder, generate endpoint + tests (SB-06)
- [ ] 31-02-PLAN.md — Frontend: api.generateFrame method, enable Generate button with loading/error states (SB-07)

### 🔮 v4.0 Element Detail Pages & Script Linking (Future)

- [x] **Phase 32: Element Detail Pages** - Dedicated full page per character/prop/location with extended fields (bio, notes, costume, specs) and reference image gallery beyond the current assets panel (completed 2026-03-22)
- [ ] **Phase 33: Script-to-Element Highlighting** - In the script read view, every appearance of a breakdown element (character name, prop mention, location) is highlighted; clicking navigates to the element detail page
- [ ] **Phase 34: Script-to-Shot Overlay** - Low-opacity framing/highlight in the script view showing which passages are covered by shots in the shotlist; clicking a covered passage navigates to that shot

#### Phase 32: Element Detail Pages
**Goal**: Each breakdown element (character, prop, location, etc.) has a dedicated full page with extended fields and a reference image gallery
**Depends on**: Phase 13 (Breakdown Page), Phase 23 (Assets Panel)
**Requirements**: EDP-01, EDP-02
**Success Criteria** (what must be TRUE):
  1. Clicking any element in the breakdown page navigates to a dedicated element detail page
  2. The detail page shows: name, category, description, all scenes where it appears, and an extended fields section (character: bio/age/role; location: address/type/notes; prop: specs/owner/status)
  3. A full reference image gallery (larger than the current assets panel view) shows all uploaded media with upload, delete, and expand actions
  4. Changes to extended fields are saved and persist on refresh
**Plans:** 2/2 plans complete
Plans:
- [ ] 32-01-PLAN.md — GET single-element endpoint with enriched scene titles, SceneLinkResponse scene_title field, backend tests (EDP-01)
- [ ] 32-02-PLAN.md — Element detail page frontend: routing, extended fields form, scene list, reference image gallery with lightbox (EDP-01, EDP-02)

#### Phase 33: Script-to-Element Highlighting
**Goal**: In the script read view, every mention of a breakdown element is highlighted and links to its detail page
**Depends on**: Phase 21 (Script Read View), Phase 32 (Element Detail Pages)
**Requirements**: SEL-01
**Success Criteria** (what must be TRUE):
  1. Character names, prop mentions, and location headings in the script are highlighted with a color-coded underline matching their element category
  2. Hovering a highlight shows a tooltip with the element name and category
  3. Clicking a highlight navigates to that element's detail page

#### Phase 34: Script-to-Shot Overlay
**Goal**: The script read view shows low-opacity framing marks indicating which passages are covered by shots in the shotlist
**Depends on**: Phase 21 (Script Read View), Phase 20 (Shotlist)
**Requirements**: SSO-01
**Success Criteria** (what must be TRUE):
  1. Script passages that are referenced by a shot (via script_text field) are highlighted with a low-opacity background tint in the script read view
  2. The highlight color matches the breakdown mode steel-blue accent
  3. Clicking a highlighted passage opens a popover showing the linked shot(s) with their fields
  4. Shots with no script_text reference do not create any highlight

### 🔮 v5.0 User Management & API Access (Future)

- [ ] **Phase 35: Real Authentication & User Model** - Replace mock auth with proper JWT registration/login, persistent user records, bcrypt passwords, and email verification flow
- [ ] **Phase 36: API Key Management** - Per-user API key generation (prefix+secret, hashed storage), scopes, optional expiry, revocation, and a management UI in user settings
- [ ] **Phase 37: API Gateway, Docs & Usage Tracking** - Unified auth middleware that accepts both session JWTs and API keys for all endpoints, Swagger/OpenAPI docs exposed at `/docs`, per-key request count and last-used tracking

#### Phase 35: Real Authentication & User Model
**Goal**: Replace the MockAuthService with a production-ready auth system so users can register, log in, and own their data securely
**Depends on**: Phase 1 (DB foundation), existing mock auth pattern
**Requirements**: UM-01, UM-02, UM-03
**Success Criteria** (what must be TRUE):
  1. Users can register with email + password via POST /api/auth/register and receive a JWT on success
  2. Users can log in via POST /api/auth/login and receive a JWT; passwords are stored as bcrypt hashes, never plaintext
  3. A `users` table exists with: id, email (unique), hashed_password, display_name, created_at
  4. All existing protected endpoints continue to work — the JWT from login is accepted everywhere mock-token was accepted
  5. The frontend login/register flow is accessible at /login; authenticated users are redirected to /projects
  6. A user profile page at /settings/profile shows email and display name with an edit form

#### Phase 36: API Key Management
**Goal**: Users can create named API keys with optional scopes and expiry dates, and use them to authenticate any endpoint
**Depends on**: Phase 35 (real user model)
**Requirements**: AK-01, AK-02, AK-03, AK-04
**Success Criteria** (what must be TRUE):
  1. An `api_keys` table exists with: id, user_id (FK), name, key_prefix (8 chars, shown in UI), key_hash (SHA-256 of full key, never stored in plaintext), scopes (JSON array), expires_at (nullable), created_at, last_used_at, is_active
  2. POST /api/auth/api-keys creates a key, returns the full key string exactly once (format: `sa_<prefix>_<secret>`) — subsequent requests never return the secret again
  3. All protected endpoints accept `Authorization: Bearer sa_<key>` and authenticate via the key_hash lookup
  4. DELETE /api/auth/api-keys/{id} immediately revokes a key
  5. A /settings/api-keys page in the frontend lists all active keys (name, prefix, created, last used, expiry), with a "Create Key" button that shows the full key in a one-time copy modal, and a "Revoke" action per key

#### Phase 37: API Gateway, Docs & Usage Tracking
**Goal**: The API is fully documented and accessible externally, with per-key usage visible to users
**Depends on**: Phase 36 (API key auth)
**Requirements**: AK-05, AK-06
**Success Criteria** (what must be TRUE):
  1. FastAPI's built-in Swagger UI is exposed at /docs (authenticated via session or API key) with all endpoints documented, correct response schemas, and example payloads
  2. A unified auth middleware handles both `Bearer <jwt>` and `Bearer sa_<key>` transparently — no endpoint code changes required
  3. Each authenticated API key request increments the key's `request_count` counter and updates `last_used_at`
  4. The /settings/api-keys page shows request_count and last_used_at per key, updated in real time
  5. Rate limiting applies per API key (configurable per-key limit, default 1000 req/hour) with 429 response and Retry-After header when exceeded

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
| 26. AI Shotlist Generation Service | v3.1 | Complete | 2026-03-20 | 2026-03-20 |
| 27. Generate Shotlist UI & AI Badge | v3.1 | Complete | 2026-03-21 | 2026-03-21 |
| 28. UX Improvements | v3.1 | Complete | 2026-03-21 | 2026-03-21 |
| 29. Storyboard Data Model & Mode Shell | v3.2 | 0/2 | Planned | - |
| 30. Storyboard Grid UI | v3.2 | 0/2 | Planned | - |
| 31. AI Frame Generation (Google Imagen) | v3.2 | 0/2 | Planned | - |
| 32. Element Detail Pages | 2/2 | Complete   | 2026-03-22 | - |
| 33. Script-to-Element Highlighting | v4.0 | 0/? | Future | - |
| 34. Script-to-Shot Overlay | v4.0 | 0/? | Future | - |
| 35. Real Authentication & User Model | v5.0 | 0/? | Future | - |
| 36. API Key Management | v5.0 | 0/? | Future | - |
| 37. API Gateway, Docs & Usage Tracking | v5.0 | 0/? | Future | - |
