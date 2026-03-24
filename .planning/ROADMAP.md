# Roadmap: Screenwriting Assistant

## Milestones

- ✅ **v1.0 Agent Orchestration Pipeline** — Phases 1-8 (shipped 2026-03-12)
- ✅ **v2.0 Script Breakdown** — Phases 9-16 (shipped 2026-03-18)
- ✅ **v3.0 Shotlist & Production Breakdown** — Phases 17-25 (shipped 2026-03-20)
- ✅ **v3.1 AI Shotlist Generation** — Phases 26-28 (shipped 2026-03-21)
- 🚧 **v3.2 Storyboard Mode** — Phases 29-31 (planned)
- ✅ **v4.0 Element Detail Pages & Script Linking** — Phases 32-34 (shipped 2026-03-22)
- ✅ **v4.1 Real Authentication** — Phase 35 (shipped 2026-03-23)
- 🚧 **v4.2 TV Show Mode** — Phases 36-42 (in progress)
- 🔮 **v5.0 API Key Management & Gateway** — Phases 43-44 (future)

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

<details>
<summary>✅ v3.1 AI Shotlist Generation (Phases 26-28) — SHIPPED 2026-03-21</summary>

- [x] Phase 26: AI Shotlist Generation Service (2/2 plans) — completed 2026-03-20
- [x] Phase 27: Generate Shotlist UI & AI Badge (1/1 plan) — completed 2026-03-21
- [x] Phase 28: UX Improvements (3/3 plans) — completed 2026-03-21

</details>

### v3.2 Storyboard Mode (Planned)

- [ ] **Phase 29: Storyboard Data Model & Mode Shell** - DB model for storyboard frames, CRUD API, third mode toggle (deep purple/violet identity), project-level style setting
- [ ] **Phase 30: Storyboard Grid UI** - Grid of shot cards each with a frame slot, upload frames, mark one as selected/hero, multiple frames per shot gallery
- [ ] **Phase 31: AI Frame Generation (Google Imagen)** - Vertex AI / Imagen integration, per-shot "Generate Frame" button using shot fields as prompt, Photorealistic / Cinematic / Animated styles

<details>
<summary>✅ v4.0 Element Detail Pages & Script Linking (Phases 32-34) — SHIPPED 2026-03-22</summary>

- [x] Phase 32: Element Detail Pages (2/2 plans) — completed 2026-03-22
- [x] Phase 33: Script-to-Element Highlighting (1/1 plan) — completed 2026-03-22
- [x] Phase 34: Script-to-Shot Overlay (1/1 plan) — completed 2026-03-22

</details>

<details>
<summary>✅ v4.1 Real Authentication (Phase 35) — SHIPPED 2026-03-23</summary>

- [x] Phase 35: Real Authentication & User Model (2/2 plans) — completed 2026-03-23

</details>

### v4.2 TV Show Mode (In Progress)

- [x] **Phase 36: Show Data Model & CRUD API** - Show entity with DB model, delta migration, Pydantic schemas, full CRUD endpoints (completed 2026-03-24)
- [x] **Phase 37: Series Bible Data & API** - Bible sections and episode duration DB model, API endpoints for reading and writing bible content (completed 2026-03-24)
- [x] **Phase 38: Show Management UI** - Home page split (Shows vs Films), show detail page shell with bible editor and episode list area (completed 2026-03-24)
- [ ] **Phase 39: Episode Data Model & Linking** - Episode as Project with show_id FK, episode CRUD API, standalone project backward compatibility
- [ ] **Phase 40: Episode Management UI** - Episode list on show page, create/open/delete episodes, episode inherits full existing pipeline
- [ ] **Phase 41: Bible AI Injection** - Modify generation services to prepend bible content and duration when generating for an episode
- [ ] **Phase 42: Breadcrumb Navigation** - Episode views include breadcrumb trail back to parent show

## Phase Details

### Phase 36: Show Data Model & CRUD API
**Goal**: A Show entity exists in the database with full CRUD operations accessible via REST API
**Depends on**: Phase 35 (user model for owner_id FK)
**Requirements**: SHOW-01, SHOW-04
**Success Criteria** (what must be TRUE):
  1. A `shows` table exists with columns: id, title, description, owner_id (FK to users), created_at, updated_at
  2. POST /api/shows creates a new show and returns it with an id
  3. GET /api/shows returns all shows for the authenticated user
  4. PUT /api/shows/{id} updates a show's title and description
  5. DELETE /api/shows/{id} deletes a show and all associated data (bible, episodes)
**Plans:** 1/1 plans complete
Plans:
- [ ] 36-01-PLAN.md — Show model, schemas, migration, CRUD router, and integration tests

### Phase 37: Series Bible Data & API
**Goal**: Each show has structured bible content (four sections) and a target episode duration, persisted and editable via API
**Depends on**: Phase 36 (Show model)
**Requirements**: BIBL-01, BIBL-02, BIBL-03
**Success Criteria** (what must be TRUE):
  1. Each show has four bible fields: characters, world_setting, season_arc, tone_style (text columns or JSONB, stored per show)
  2. GET /api/shows/{id}/bible returns all four sections and the episode duration
  3. PUT /api/shows/{id}/bible saves edits to any combination of bible sections and duration
  4. Episode duration supports preset values (10, 22, 44, 60 min) and custom integer entry
**Plans:** 1/1 plans complete
Plans:
- [ ] 37-01-PLAN.md — Bible columns, schemas, migration, GET/PUT endpoints, and tests

### Phase 38: Show Management UI
**Goal**: Users can see their shows and films as separate sections on the home page, and can open a show to view its bible and episode list
**Depends on**: Phase 37 (Bible API), Phase 36 (Show CRUD)
**Requirements**: SHOW-02, SHOW-03, BIBL-01, BIBL-02, BIBL-03
**Success Criteria** (what must be TRUE):
  1. The home page displays a "Shows" section listing all shows (title, description, episode count) and a "Films" section listing standalone projects
  2. Clicking a show navigates to a show detail page at /shows/{id}
  3. The show detail page displays the show title, description, and an editable series bible with four sections (Characters, World/Setting, Season Arc, Tone & Style) and the episode duration selector
  4. The show detail page has an episode list area (empty until Phase 40 wires episode management)
  5. Bible edits auto-save and persist on page refresh
**Plans:** 2/2 plans complete
Plans:
- [ ] 38-01-PLAN.md — Types, API methods, constants, home page split with ShowCard and CreateShowModal
- [ ] 38-02-PLAN.md — ShowDetail page with BibleEditor, EpisodeDurationPicker, and route wiring

### Phase 39: Episode Data Model & Linking
**Goal**: Episodes are projects that belong to a show, with the existing project pipeline fully intact and standalone projects unaffected
**Depends on**: Phase 36 (Show model)
**Requirements**: EPIS-01, EPIS-02, EPIS-04
**Success Criteria** (what must be TRUE):
  1. The projects table has a nullable show_id FK and an episode_number integer column (both null for standalone projects)
  2. POST /api/shows/{show_id}/episodes creates a new project linked to the show with an episode number and title
  3. An episode project has the full screenplay, breakdown, shotlist, and storyboard pipeline — identical to standalone projects
  4. Existing standalone projects (show_id = NULL) continue to work exactly as before with zero data migration
**Plans**: TBD

### Phase 40: Episode Management UI
**Goal**: Users can create, view, open, and delete episodes from the show detail page
**Depends on**: Phase 38 (Show detail page), Phase 39 (Episode API)
**Requirements**: EPIS-03
**Success Criteria** (what must be TRUE):
  1. The show detail page displays an episode list showing all episodes ordered by episode number (number, title, framework)
  2. A "New Episode" button opens a create dialog with episode number (auto-incremented) and title fields
  3. Clicking an episode navigates to the standard project editor (/projects/{id}) which renders the full pipeline
  4. Each episode row has a delete action that removes the episode after confirmation
**Plans**: TBD

### Phase 41: Bible AI Injection
**Goal**: All AI generation for episodes automatically includes the show's bible content and target duration as context
**Depends on**: Phase 37 (Bible data), Phase 39 (Episode linking)
**Requirements**: BIBL-04
**Success Criteria** (what must be TRUE):
  1. When generating screenplay content for an episode, the AI prompt includes all four bible sections (characters, world/setting, season arc, tone & style) as context
  2. When generating screenplay content for an episode, the AI prompt includes the target episode duration (e.g., "Target runtime: 22 minutes")
  3. Agent reviews for episodes also receive bible context in their review prompts
  4. Breakdown extraction for episodes receives bible context (so the AI knows which characters/locations are series regulars)
  5. Standalone film projects are unaffected — no bible context is injected for projects without a show_id
**Plans**: TBD

### Phase 42: Breadcrumb Navigation
**Goal**: Episode views provide clear navigation context showing the parent show hierarchy
**Depends on**: Phase 39 (Episode-show relationship), Phase 38 (Show detail page)
**Requirements**: EPIS-05
**Success Criteria** (what must be TRUE):
  1. When viewing an episode in the editor, a breadcrumb trail appears: Show Title > Episode N: Episode Title
  2. Clicking the show name in the breadcrumb navigates back to the show detail page
  3. The breadcrumb is visible in all episode modes (screenwriting, breakdown) — not just the editor
  4. Standalone film projects do not display any breadcrumb (no visual change for existing workflows)
**Plans**: TBD

### v5.0 API Key Management & Gateway (Future)

#### Phase 43: API Key Management
**Goal**: Users can create named API keys with optional scopes and expiry dates, and use them to authenticate any endpoint
**Depends on**: Phase 35 (real user model)
**Requirements**: AK-01, AK-02, AK-03, AK-04
**Success Criteria** (what must be TRUE):
  1. An `api_keys` table exists with: id, user_id (FK), name, key_prefix (8 chars, shown in UI), key_hash (SHA-256 of full key, never stored in plaintext), scopes (JSON array), expires_at (nullable), created_at, last_used_at, is_active
  2. POST /api/auth/api-keys creates a key, returns the full key string exactly once (format: `sa_<prefix>_<secret>`) — subsequent requests never return the secret again
  3. All protected endpoints accept `Authorization: Bearer sa_<key>` and authenticate via the key_hash lookup
  4. DELETE /api/auth/api-keys/{id} immediately revokes a key
  5. A /settings/api-keys page in the frontend lists all active keys (name, prefix, created, last used, expiry), with a "Create Key" button that shows the full key in a one-time copy modal, and a "Revoke" action per key

#### Phase 44: API Gateway, Docs & Usage Tracking
**Goal**: The API is fully documented and accessible externally, with per-key usage visible to users
**Depends on**: Phase 43 (API key auth)
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
| 26. AI Shotlist Generation Service | v3.1 | 2/2 | Complete | 2026-03-20 |
| 27. Generate Shotlist UI & AI Badge | v3.1 | 1/1 | Complete | 2026-03-21 |
| 28. UX Improvements | v3.1 | 3/3 | Complete | 2026-03-21 |
| 29. Storyboard Data Model & Mode Shell | v3.2 | 0/2 | Planned | - |
| 30. Storyboard Grid UI | v3.2 | 0/2 | Planned | - |
| 31. AI Frame Generation (Google Imagen) | v3.2 | 0/2 | Planned | - |
| 32. Element Detail Pages | v4.0 | 2/2 | Complete | 2026-03-22 |
| 33. Script-to-Element Highlighting | v4.0 | 1/1 | Complete | 2026-03-22 |
| 34. Script-to-Shot Overlay | v4.0 | 1/1 | Complete | 2026-03-22 |
| 35. Real Authentication & User Model | v4.1 | 2/2 | Complete | 2026-03-23 |
| 36. Show Data Model & CRUD API | v4.2 | 1/1 | Complete | 2026-03-24 |
| 37. Series Bible Data & API | v4.2 | 1/1 | Complete | 2026-03-24 |
| 38. Show Management UI | 2/2 | Complete    | 2026-03-24 | - |
| 39. Episode Data Model & Linking | v4.2 | 0/? | Not started | - |
| 40. Episode Management UI | v4.2 | 0/? | Not started | - |
| 41. Bible AI Injection | v4.2 | 0/? | Not started | - |
| 42. Breadcrumb Navigation | v4.2 | 0/? | Not started | - |
| 43. API Key Management | v5.0 | 0/? | Future | - |
| 44. API Gateway, Docs & Usage Tracking | v5.0 | 0/? | Future | - |
