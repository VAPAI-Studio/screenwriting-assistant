# Roadmap: Screenwriting Assistant

## Milestones

- ✅ **v1.0 Agent Orchestration Pipeline** — Phases 1-8 (shipped 2026-03-12)
- ✅ **v2.0 Script Breakdown** — Phases 9-16 (shipped 2026-03-18)
- ✅ **v3.0 Shotlist & Production Breakdown** — Phases 17-25 (shipped 2026-03-20)
- ✅ **v3.1 AI Shotlist Generation** — Phases 26-28 (shipped 2026-03-21)
- ✅ **v3.2 Storyboard Mode** — Phases 29-31 (shipped 2026-04-01)
- ✅ **v4.0 Element Detail Pages & Script Linking** — Phases 32-34 (shipped 2026-03-22)
- ✅ **v4.1 Real Authentication** — Phase 35 (shipped 2026-03-23)
- ✅ **v4.2 TV Show Mode** — Phases 36-42 (shipped 2026-03-24)
- ✅ **v5.0 API Key Management & Gateway** — Phases 43-44 (shipped 2026-04-01)
- 📝 **v6.0 Script Quality** — Phases 45-49 — deepen AI script-writing output (continuity-aware generation, format fidelity, character voice, screenwriting craft, side-by-side eval) — in progress
- 📝 **v7.0 Breakdown Fidelity** — Phases 50-53 — deepen extraction (extract against scene text not summaries, per-appearance context, expanded categories, re-extract on change) — planned (requirements + roadmap defined 2026-06-06; execution gated on v6.0 close)
- 📝 **v8.0 MCP Server** — expose write + breakdown capabilities as MCP tools for external agents; auth via existing API-key gateway — planned (after v6.0/v7.0)

> **Direction note (2026-06-05):** This is an **internal tool**. Roadmap focus is the quality of script-writing and breakdown only. Market features (industry export, collaboration, AI-previz, public API platform) are out of scope. The separate AI previz platform stays disconnected for now.

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

<details>
<summary>✅ v4.2 TV Show Mode (Phases 36-42) — SHIPPED 2026-03-24</summary>

- [x] Phase 36: Show Data Model & CRUD API (1/1 plans) — completed 2026-03-24
- [x] Phase 37: Series Bible Data & API (1/1 plans) — completed 2026-03-24
- [x] Phase 38: Show Management UI (2/2 plans) — completed 2026-03-24
- [x] Phase 39: Episode Data Model & Linking (1/1 plans) — completed 2026-03-24
- [x] Phase 40: Episode Management UI (1/1 plans) — completed 2026-03-24
- [x] Phase 41: Bible AI Injection (1/1 plans) — completed 2026-03-24
- [x] Phase 42: Breadcrumb Navigation (1/1 plans) — completed 2026-03-24

</details>

### v5.0 API Key Management & Gateway (Shipped 2026-04-01)

- [x] **Phase 43: API Key Management** - Users can create named API keys with optional scopes and expiry dates (completed 2026-03-27)
- [x] **Phase 44: API Gateway, Docs & Usage Tracking** - API documentation, unified auth middleware, and per-key usage tracking (completed 2026-04-01)

### v6.0 Script Quality (Planned)

- [ ] **Phase 45: Continuity-Aware Generation** - Scene script calls receive prior scene text + a maintained running synopsis so tone/setup/payoff hold across scenes
- [x] **Phase 46: Format Fidelity (Native vs JSON Mode)** - Evaluate native screenplay output vs json_mode `{title, content}` wrapping; adopt the approach with better industry-standard formatting
- [x] **Phase 47: Character Voice Injection** - Per-character voice/diction profiles injected into the script-writing prompt so dialogue is distinct and consistent per character
- [x] **Phase 48: Screenwriting Craft Guidance** - Craft directives (subtext, action-line economy, show-don't-tell, page pacing/white space) added to the generation prompt
- [ ] **Phase 49: Side-by-Side Quality Compare** - User can regenerate a scene with the improved path and compare it against prior output to judge the improvement

## Phase Details

<details>
<summary>v4.2 Phase Details (36-42) — Shipped</summary>

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
**Plans:** 1/1 plans complete
Plans:
- [ ] 39-01-PLAN.md — Project model extension, EpisodeCreate schema, episode creation endpoint, migration 008, and tests

### Phase 40: Episode Management UI
**Goal**: Users can create, view, open, and delete episodes from the show detail page
**Depends on**: Phase 38 (Show detail page), Phase 39 (Episode API)
**Requirements**: EPIS-03
**Success Criteria** (what must be TRUE):
  1. The show detail page displays an episode list showing all episodes ordered by episode number (number, title, framework)
  2. A "New Episode" button opens a create dialog with episode number (auto-incremented) and title fields
  3. Clicking an episode navigates to the standard project editor (/projects/{id}) which renders the full pipeline
  4. Each episode row has a delete action that removes the episode after confirmation
**Plans:** 1/1 plans complete
Plans:
- [ ] 40-01-PLAN.md — GET episodes endpoint, EpisodeList and CreateEpisodeModal components, ShowDetail wiring

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
**Plans:** 1/1 plans complete
Plans:
- [ ] 41-01-PLAN.md — Bible context helper, service method threading, endpoint wiring, and tests

### Phase 42: Breadcrumb Navigation
**Goal**: Episode views provide clear navigation context showing the parent show hierarchy
**Depends on**: Phase 39 (Episode-show relationship), Phase 38 (Show detail page)
**Requirements**: EPIS-05
**Success Criteria** (what must be TRUE):
  1. When viewing an episode in the editor, a breadcrumb trail appears: Show Title > Episode N: Episode Title
  2. Clicking the show name in the breadcrumb navigates back to the show detail page
  3. The breadcrumb is visible in all episode modes (screenwriting, breakdown) — not just the editor
  4. Standalone film projects do not display any breadcrumb (no visual change for existing workflows)
**Plans:** 1/1 plans complete
Plans:
- [ ] 42-01-PLAN.md — EpisodeBreadcrumb component with integration into Editor, BreakdownLayout, and StoryboardView

</details>

<!-- v5.0 API Key Management & Gateway -->

### Phase 43: API Key Management
**Goal**: Users can create named API keys with optional scopes and expiry dates, and use them to authenticate any endpoint
**Depends on**: Phase 35 (real user model)
**Requirements**: AK-01, AK-02, AK-03, AK-04
**Success Criteria** (what must be TRUE):
  1. An `api_keys` table exists with: id, user_id (FK), name, key_prefix (8 chars, shown in UI), key_hash (SHA-256 of full key, never stored in plaintext), scopes (JSON array), expires_at (nullable), created_at, last_used_at, is_active
  2. POST /api/auth/api-keys creates a key, returns the full key string exactly once (format: `sa_<prefix>_<secret>`) — subsequent requests never return the secret again
  3. All protected endpoints accept `Authorization: Bearer sa_<key>` and authenticate via the key_hash lookup
  4. DELETE /api/auth/api-keys/{id} immediately revokes a key
  5. A /settings/api-keys page in the frontend lists all active keys (name, prefix, created, last used, expiry), with a "Create Key" button that shows the full key in a one-time copy modal, and a "Revoke" action per key
**Plans:** 2 plans
Plans:
- [ ] 43-01-PLAN.md — ApiKey model, migration, schemas, CRUD endpoints, dual-auth dependency, and tests
- [ ] 43-02-PLAN.md — Frontend types, API methods, ApiKeysPage component, route wiring, and human verification

### Phase 44: API Gateway, Docs & Usage Tracking
**Goal**: The API is fully documented and accessible externally, with per-key usage visible to users
**Depends on**: Phase 43 (API key auth)
**Requirements**: AK-05, AK-06
**Success Criteria** (what must be TRUE):
  1. FastAPI's built-in Swagger UI is exposed at /docs (authenticated via session or API key) with all endpoints documented, correct response schemas, and example payloads
  2. A unified auth middleware handles both `Bearer <jwt>` and `Bearer sa_<key>` transparently — no endpoint code changes required
  3. Each authenticated API key request increments the key's `request_count` counter and updates `last_used_at`
  4. The /settings/api-keys page shows request_count and last_used_at per key, updated in real time
  5. Rate limiting applies per API key (configurable per-key limit, default 1000 req/hour) with 429 response and Retry-After header when exceeded
**Plans:** 2/2 plans complete
Plans:
- [ ] 44-01-PLAN.md — Backend: migration, model, schema, atomic increment, rate limiter middleware, docs enhancement, tests
- [ ] 44-02-PLAN.md — Frontend: TypeScript types, ApiKeysPage usage display, auto-refresh, and human verification

<!-- v6.0 Script Quality -->

### Phase 45: Continuity-Aware Generation
**Goal**: Each scene's screenplay is generated with awareness of what was actually written before, so tone, voice, and setup/payoff stay consistent across the scene sequence
**Depends on**: Phase 44 (current generation path baseline)
**Requirements**: CONT-01, CONT-02, CONT-03
**Success Criteria** (what must be TRUE):
  1. When `_generate_scripts` writes a scene, the prompt includes the full generated text of the immediately preceding scene(s) — not just the one-line `scene_outline` summaries
  2. A running synopsis ("story so far") is built and updated after each scene and injected into subsequent scene calls, keeping context within token limits instead of pasting all prior scenes verbatim
  3. A generated scene does not contradict facts, objects, or character states established in an earlier generated scene (setups/payoffs stay consistent across the sequence)
  4. Existing single-scene / non-sequential generation still works unchanged when there is no prior scene
**Plans:** 1 plan
Plans:
- [x] 45-01-PLAN.md — Thread running synopsis + prev-scene text through _generate_scripts, add synopsis-update helper, persist synopsis, and continuity tests (completed 2026-06-06)

### Phase 46: Format Fidelity (Native vs JSON Mode)
**Goal**: Screenplay output preserves industry-standard formatting, with the generation call shape (native output vs json_mode `{title, content}`) settled to whichever yields better formatting
**Depends on**: Phase 45 (continuity rework settles the generation call shape)
**Requirements**: FMT-01, FMT-02
**Success Criteria** (what must be TRUE):
  1. The screenplay-generation path is evaluated both ways: native screenplay output vs the current json_mode `{title, content}` wrapping
  2. Generated output preserves scene headings, action lines, character cues, parentheticals, and dialogue formatting without JSON wrapping degrading it
  3. The better-formatting approach is adopted as the default generation path, and title/content are still captured correctly for storage in `ScreenplayContent`
  4. The chosen approach works for both OpenAI and Anthropic via the existing provider abstraction
**Plans**: 1 plan
- [x] 46-01-PLAN.md — Migrate scene-writing to native output (json_mode=False), TITLE-line title parsing, strengthened layout prompt; preserve Phase 45 contract/continuity/failure; update continuity tests + FMT assertions

### Phase 47: Character Voice Injection
**Goal**: Each character speaks in a distinct, consistent voice in generated dialogue because their voice profile reaches the script-writing prompt, not just scene planning
**Depends on**: Phase 46 (generation call shape settled), Phase 45 (continuity context)
**Requirements**: VOICE-01, VOICE-02, VOICE-03
**Success Criteria** (what must be TRUE):
  1. Per-character voice/diction profiles (from PhaseData story.characters ListItems) are injected into the script-writing prompt in `_generate_scripts`, not only into `_generate_scenes`
  2. When a character has no defined voice, the system derives or carries forward a consistent voice for them across scenes instead of defaulting to a uniform style
  3. In a scene with multiple characters, their dialogue is distinguishable — two characters do not sound interchangeable
  4. Voice profiles stay consistent for the same character across separate scene generations
**Plans**: 1 plan
- [x] 47-01-PLAN.md — Inject character voice profiles into the script-writing prompt (wizards.py guard + _generate_scripts) with no-regression tests

### Phase 48: Screenwriting Craft Guidance
**Goal**: Generated screenplays reflect explicit craft direction so action lines are visual and economical and dialogue carries subtext
**Depends on**: Phase 47 (voice profiles in the prompt), Phase 46 (settled call shape)
**Requirements**: CRAFT-01, CRAFT-02, CRAFT-03
**Success Criteria** (what must be TRUE):
  1. The screenplay-generation prompt includes explicit craft guidance covering subtext in dialogue, action-line economy, show-don't-tell, and page pacing / white space
  2. Action lines in generated output are visual and economical — present tense, no internal or unfilmable description
  3. Generated dialogue carries subtext rather than stating characters' intentions on-the-nose
  4. Craft guidance composes with the continuity context and voice profiles without bloating the prompt past token limits
**Plans**: 1 plan
- [x] 48-01-PLAN.md — Add an unconditional `## Screenwriting Craft` block (subtext, action economy, show-don't-tell, white space) to the _generate_scripts prompt + tests

### Phase 49: Side-by-Side Quality Compare
**Goal**: The user can directly compare a scene regenerated with the improved path against its prior output to judge the cumulative quality improvement
**Depends on**: Phase 48, Phase 47, Phase 46, Phase 45 (improved generation path complete)
**Requirements**: EVAL-01
**Success Criteria** (what must be TRUE):
  1. User can regenerate a scene's screenplay using the new (improved) generation path while preserving the prior output
  2. The prior output and the newly generated output are displayed side-by-side for the same scene
  3. User can choose which version to keep, with the kept version persisting to `ScreenplayContent`
**Plans**: 2 plans
- [x] 49-01-PLAN.md — Backend: _generate_one_scene helper + regenerate-scene (preview) & keep-scene-version (persist) endpoints + tests
- [~] 49-02-PLAN.md — Frontend: regenerateScene/keepSceneVersion client + SceneCompareModal + per-scene trigger — AUTO tasks (1-3) complete, build clean; Task 4 manual UAT PENDING USER
**UI hint**: yes

<!-- v7.0 Breakdown Fidelity (planned 2026-06-06 — execution gated on v6.0 close) -->

### Phase 50: Scene-Text Extraction
**Goal**: Breakdown extraction reads the full per-scene screenplay text (the richer v6.0 output) rather than one-line scene summaries, scene-scoped, while preserving the existing "physically present on screen" rules
**Depends on**: Phase 49 (improved/regenerated scene text persisted to ScreenplayContent); existing breakdown_service.py
**Requirements**: BFID-01, BFID-02, BFID-03
**Success Criteria** (what must be TRUE):
  1. Extraction context is built from `ScreenplayContent.content` per scene, not from one-line scene summaries
  2. Each scene's elements are extracted from that scene's own text (scene-scoped), enabling per-scene attribution
  3. The on-screen-only rules (no dialogue-only mentions, no abstractions) still hold on the fuller text
  4. Existing breakdown extraction tests/behavior do not regress

**Plans:** 1/1 plans complete

Plans:
- [x] 50-01-PLAN.md — Scene-scoped extraction prompt: deterministic SC ordering, episode_index alignment helper, per-scene indexed user prompt with graceful fallback (BFID-01/02/03)

### Phase 51: Per-Appearance Context
**Goal**: Each extracted element records which scene(s) it appears in and a short how/where context note, with cross-scene duplicates consolidated into one element with multiple appearances
**Depends on**: Phase 50 (scene-scoped extraction)
**Requirements**: APPR-01, APPR-02, APPR-03
**Success Criteria** (what must be TRUE):
  1. An extracted element carries its appearance scene(s), not just a flat global entry
  2. Each appearance has a short context note (the action/moment) surfaced in the breakdown UI
  3. The same element across multiple scenes is one element with multiple appearances, not duplicated rows
**Plans**: 1 plan
Plans:
- [x] 51-01-PLAN.md — Thread per-appearance context into ElementSceneLink.context + surface it on card scene chips (detail list already shows it); verify APPR-01/APPR-03

### Phase 52: Expanded Categories
**Goal**: The element taxonomy is broadened to cover additional production categories (wardrobe, makeup/hair, SFX/VFX, vehicles, animals, stunts, etc.), additively, with UI filter/group support
**Depends on**: Phase 50 (extraction path)
**Requirements**: CATG-01, CATG-02, CATG-03
**Success Criteria** (what must be TRUE):
  1. The extraction taxonomy includes the expanded categories (final list settled in discussion)
  2. Existing categories and previously extracted elements remain valid — additive, no destructive migration
  3. The breakdown UI displays and lets the user filter/group by the expanded categories
**Plans**: 1 plan
Plans:
- [x] 52-01-PLAN.md — Broaden breakdown taxonomy to 10 categories (+set_dressing, animal, sfx, makeup_hair, extras) across all 6 definition sites in lockstep + prompt guidance + tests; CategoryTabs auto-renders (CATG-01/02/03)

### Phase 53: Re-Extraction on Change
**Goal**: When a scene's screenplay changes (v6.0 regenerate-and-keep or a manual edit), the breakdown is flagged stale and re-extraction refreshes that scene's elements without discarding user-edited breakdown data
**Depends on**: Phase 50, Phase 51, Phase 49 (keep-scene-version + existing staleness flags)
**Requirements**: REEX-01, REEX-02
**Success Criteria** (what must be TRUE):
  1. A scene-text change flags the breakdown stale via the existing staleness mechanism
  2. Re-extraction refreshes against the changed scene text
  3. User-added/edited breakdown elements are preserved across re-extraction (merge policy settled in discussion)
**Plans**: 1 plan
Plans:
- [x] 53-01-PLAN.md — Guard the extract loop so user_modified elements' scene links are never churned on re-extract (D-53-01), plus REEX-02 link-preservation/scoping tests and the REEX-01 full stale->re-extract->preserve->clear chain test (D-53-02); backend-only, no schema/migration (REEX-01/02)

<!-- Phase 54 — standalone post-v7.0 enhancement (user-requested 2026-06-07) -->

### Phase 54: Direct Screenplay Writing
**Goal**: The user can write a screenplay directly in the Screenplay Editor from an empty project (no Script Writer Wizard prerequisite), split into scenes by INT./EXT. headings, persisted and fed into the breakdown like a generated one
**Depends on**: existing Screenplay Editor (ScreenplayEditorView), the phase-data PATCH endpoint, and the wizard's ScreenplayContent-creation pattern
**Requirements**: WRITE-01, WRITE-02, WRITE-03, WRITE-04
**Success Criteria** (what must be TRUE):
  1. From an empty project, the editor lets the user write and SAVE a screenplay (no wizard-only block, no 404 on first save)
  2. Saved text splits into scenes by scene headings (INT./EXT.); no-heading text saves as one "Untitled" scene (text never lost)
  3. save → reload → edit → save round-trips with no scene duplication or loss
  4. A hand-written screenplay (re)creates ScreenplayContent rows idempotently and marks breakdown/shotlist stale, so breakdown extraction works on it
**UI hint**: yes

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
| 29. Storyboard Data Model & Mode Shell | v3.2 | Complete    | 2026-04-01 | - |
| 30. Storyboard Grid UI | v3.2 | Complete    | 2026-04-01 | - |
| 31. AI Frame Generation (Google Imagen) | v3.2 | Complete    | 2026-04-01 | - |
| 32. Element Detail Pages | v4.0 | 2/2 | Complete | 2026-03-22 |
| 33. Script-to-Element Highlighting | v4.0 | 1/1 | Complete | 2026-03-22 |
| 34. Script-to-Shot Overlay | v4.0 | 1/1 | Complete | 2026-03-22 |
| 35. Real Authentication & User Model | v4.1 | 2/2 | Complete | 2026-03-23 |
| 36. Show Data Model & CRUD API | v4.2 | 1/1 | Complete | 2026-03-24 |
| 37. Series Bible Data & API | v4.2 | 1/1 | Complete | 2026-03-24 |
| 38. Show Management UI | v4.2 | 2/2 | Complete | 2026-03-24 |
| 39. Episode Data Model & Linking | v4.2 | 1/1 | Complete | 2026-03-24 |
| 40. Episode Management UI | v4.2 | 1/1 | Complete | 2026-03-24 |
| 41. Bible AI Injection | v4.2 | 1/1 | Complete | 2026-03-24 |
| 42. Breadcrumb Navigation | v4.2 | 1/1 | Complete | 2026-03-24 |
| 43. API Key Management | v5.0 | 2/2 | Complete | 2026-03-27 |
| 44. API Gateway, Docs & Usage Tracking | v5.0 | 2/2 | Complete | 2026-04-01 |
| 45. Continuity-Aware Generation | v6.0 | 0/1 | Planned | - |
| 46. Format Fidelity (Native vs JSON Mode) | v6.0 | 1/1 | Complete | 2026-06-06 |
| 47. Character Voice Injection | v6.0 | 1/1 | Complete | 47-01 |
| 48. Screenwriting Craft Guidance | v6.0 | 0/? | Not started | - |
| 49. Side-by-Side Quality Compare | v6.0 | 1/2 | In progress | - |
