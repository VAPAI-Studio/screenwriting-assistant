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
- ✅ **v6.0 Script Quality** — Phases 45-49 (shipped 2026-06-11) — continuity-aware generation, format fidelity, character voice, screenwriting craft, side-by-side eval. See [.planning/milestones/v6.0-ROADMAP.md](milestones/v6.0-ROADMAP.md)
- 📝 **v7.0 Breakdown Fidelity** — Phases 50-53 — deepen extraction (extract against scene text not summaries, per-appearance context, expanded categories, re-extract on change) — planned (requirements + roadmap defined 2026-06-06; execution gated on v6.0 close)
- ✅ **v8.0 MCP Server** — Phases 55-61 (shipped 2026-06-12) — 17 MCP tools over remote Streamable HTTP, authed by the v5.0 `sa_<key>` gateway; live UAT passed (Claude Code). See [.planning/milestones/v8.0-ROADMAP.md](milestones/v8.0-ROADMAP.md)
- 📝 **v9.0 Deploy (Railway + Vercel + CI/CD)** — Phases 62-66 — get the app running in production: backend + Postgres (pgvector) + `/media` volume on Railway, frontend on Vercel, migrations on boot, GitHub Actions tests-on-push + deploy-on-merge-to-`main`, public-deploy CORS/MCP hardening + post-deploy smoke test. Internal tool — scope is "deployed reliably." — planned (requirements + roadmap defined 2026-06-14)
- 🚧 **v10.0 Show Type / Episode Continuity** — Phases 67-71 — each Show declares a single `continuity_mode` (connected / anthology / standalone) that changes what prior context the AI gets when writing an episode; AI auto-summarizes each episode (invalidated on edit, regenerated lazily) and feeds prior summaries into connected-mode generation; show-creation wizard picks the mode via presets; review is mode-aware. Internal tool — scope is "episodes connect coherently." See [.planning/v10.0-SHOW-TYPE-VISION.md](v10.0-SHOW-TYPE-VISION.md) — in progress (requirements + roadmap defined 2026-06-17)

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

### ✅ v6.0 Script Quality (Phases 45-49) — SHIPPED 2026-06-11

All five phases complete. Full detail archived in [.planning/milestones/v6.0-ROADMAP.md](milestones/v6.0-ROADMAP.md).

- [x] Phase 45: Continuity-Aware Generation — prior scene text + running synopsis
- [x] Phase 46: Format Fidelity — native output adopted over json_mode wrapping
- [x] Phase 47: Character Voice Injection — voice profiles into the script prompt
- [x] Phase 48: Screenwriting Craft Guidance — subtext/economy/show-don't-tell block
- [x] Phase 49: Side-by-Side Quality Compare — regenerate + compare + keep (UAT confirmed)

### 📝 v8.0 MCP Server (Phases 55-61) — Planned

Expose the app's core capabilities as remote Streamable HTTP MCP tools, mounted in-process on the FastAPI app, authed via the v5.0 `sa_<key>` gateway. ~12 curated tools; no destructive (delete) tools; every tool owner-scoped. Foundation (55) carries nearly all the integration risk; tool groups (57-60) are parallelizable thin adapters over existing services.

- [x] **Phase 55: MCP Foundation — Mount, Auth, Lifespan & Client Spike** — `/mcp` mounted in-process, composed lifespan, `/mcp` exempt from `BaseHTTPMiddleware`, `authenticate_token` refactored out of `get_current_user` (with `request_count` increment moved in), a `whoami`/`ping` tool, and the static-bearer client-compatibility spike (Claude Code/Desktop/Hermes) as a GO/NO-GO gate — HIGHEST STAKES; needs a scaffold-time spike to pin the exact library
- [x] **Phase 56: Job Registry, `job_status` & First AI-Backed Tool** — job registry + generic `job_status` poll tool + the first long-running generator wired start-fast-return-job-id, establishing the `to_thread` + late-open/early-close DB-session pattern and pool tuning
- [x] **Phase 57: Management Tools (project / show / episode / bible)** — the agent's session entry point: list/create/read projects (+ show/episode/bible reads), with target-id normalization (`project_id` ≡ `episode_id`)
- [x] **Phase 58: Screenwriting Tools** — read a screenplay, write one directly (Phase 54 path), generate a scene via the v6.0 path (job-id)
- [x] **Phase 59: Breakdown Tools** — trigger v7.0 extraction (job-id) and read category-scoped elements with their per-scene appearances
- [x] **Phase 60: Shotlist Tools** — read the shotlist, create a shot, AI-generate a shotlist (job-id)
- [x] **Phase 61: Discovery Polish, Error Mapping & Client-Matrix UAT** — finalize tool names/descriptions/schemas + annotations, map app errors to clean MCP tool errors, and run the full client-matrix UAT (Claude Code, Desktop, Hermes)

### 📝 v9.0 Deploy (Railway + Vercel + CI/CD) (Phases 62-66) — Planned

Get the app running in production. Config-parametrization first (prerequisite for everything), then backend + Postgres (pgvector) + `/media` volume on Railway with migrations applied via `init_db` on boot, then the Vercel frontend wired to the Railway backend domain, then GitHub Actions CI/CD (tests-on-push gate + deploy-on-merge-to-`main`), then public-deploy hardening + a post-deploy smoke test. Several steps are human-in-the-loop: the user logs in to Railway/Vercel (VAPAI-Studio), enters secrets directly into Railway (never the repo), and confirms domains. Internal tool — single Railway Postgres holds ALL data (projects, scripts, users, api_keys + pgvector RAG embeddings). Out of scope (known debt, not deploy blockers): legacy `framework` enum bug, clean-`docker compose build` dependency-pin confirmation, Hermes static-header verification.

- [x] **Phase 62: Config Parametrization & Migrations-on-Boot** — env-parametrize the three localhost hardcodes (`ALLOWED_ORIGINS` in config.py + docker-compose, `VITE_API_URL`, MCP base URL in mcp_server/server.py) and make `init_db` apply the idempotent `delta/*.sql` migrations on boot — the prerequisite that unblocks every later phase; no external account needed
- [x] **Phase 63: Backend + Postgres + Volume on Railway** — DONE & LIVE. Backend Online at https://web-production-73857.up.railway.app, `/health` → 200; Railway Postgres with pgvector 0.8.2 (30 tables, migrations 000-010 applied on boot), `/media` volume, secrets from Railway env. Deploy gotchas resolved: removed root Procfile + Custom Start Command (`cd` error), railway.json moved to backend/, targetPort=8000, PORT=8000, real OPENAI_API_KEY (embedding_service instantiates AsyncOpenAI at import).
- [x] **Phase 64: Frontend on Vercel** — DONE & LIVE. Vite app deployed on Vercel (souts team), HTTP 200, SPA rewrite works (/projects → 200), VITE_API_URL=`https://web-production-73857.up.railway.app/api` baked into the bundle. Vercel Deployment Protection was disabled (was returning 401 on all deploys). Pending: lock CORS to the Vercel domain (Phase 66) for end-to-end API calls.
- [~] **Phase 65: CI/CD with GitHub Actions** — a workflow runs the backend test suite on every push as a gate (~399 tests, 4 pre-existing flakes tolerated) and, on merge to `main`, deploys the backend to Railway and the frontend to Vercel — depends on both deploy targets being configured; human-in-the-loop (deploy tokens/secrets entered into GitHub) — REPO-SIDE DONE (.github/workflows test+deploy, rerun flake tolerance); manual GitHub secrets pending → checklist
- [~] **Phase 66: Public-Deploy Hardening & Post-Deploy Smoke Test** — CORS DONE & VERIFIED (ALLOWED_ORIGINS=["https://screenwriting-assistant-lake.vercel.app"] on Railway; preflight allows Vercel origin, rejects others with 400; end-to-end app verified working in browser). Repo-side smoke_test.sh + deploy gate + DNS-rebinding toggle done. Remaining: optional MCP_DNS_REBINDING_PROTECTION=true; PROD_BACKEND_URL/PROD_FRONTEND_URL GitHub secrets for the smoke gate (tied to Phase 65).

### 🚧 v10.0 Show Type / Episode Continuity (Phases 67-71) — In Progress

Each Show declares a single `continuity_mode` (`connected` / `anthology` / `standalone`) that changes what prior context the AI receives when writing an episode. Data model + idempotent `delta/*.sql` migration first (the `shows.continuity_mode` enum + `projects.episode_summary` + `projects.episode_summary_stale` columns, mirroring the existing `breakdown_stale`/`shotlist_stale` pattern), then mode-aware generation context injection (connected: season arc + prior-episode summaries ordered by `episode_number`, never positional; anthology: bible only; standalone: none), then AI auto-summary on episode completion with lazy regeneration of stale summaries before they feed later episodes, then the show-creation wizard (mode picked via Microserie / Serie conectada / Antología presets that are pure UI sugar over the single mode), then mode-aware review (connected checks continuity against prior summaries). Locked decisions (single axis, AI auto-summary, stale-flag invalidation, scale stays metadata, presets are UI sugar) per `.planning/v10.0-SHOW-TYPE-VISION.md`. Deferred (NOT this milestone): continuity-inconsistency detection, multi-season, hand-editable summaries, scale-as-behavior. Open questions folded into phase notes (default mode on migration, when the auto-summary fires, token-budget cap for long connected seasons) — resolved at plan-phase, not blockers.

- [ ] **Phase 67: Continuity Data Model & Migration** — add `shows.continuity_mode` (enum connected/anthology/standalone), `projects.episode_summary` (TEXT, nullable), `projects.episode_summary_stale` (Boolean default False) via a new idempotent `delta/NNN_*.sql`; expose set/edit of the mode on the Show API and set `episode_summary_stale=True` whenever an episode is edited (mirrors `breakdown_stale`/`shotlist_stale`) — the foundation every later phase reads
- [ ] **Phase 68: Mode-Aware Generation Context Injection** — episode-writing generation branches on `continuity_mode`: connected injects season arc + prior-episode `episode_summary` (ordered by `episode_number`); anthology injects only the shared bible; standalone injects no cross-episode context — mirrors the existing `bible_context` injection point
- [ ] **Phase 69: Auto Episode Summary & Lazy Regeneration** — the AI generates and stores `episode_summary` when an episode is completed, and a stale summary is regenerated before it is used as prior-episode context for a later episode (lazy regen via the `episode_summary_stale` flag)
- [ ] **Phase 70: Show Creation Wizard (mode + presets)** — the show create/edit flow lets the user pick the continuity mode via Microserie / Serie conectada / Antología presets (visual shortcuts that set the underlying single mode), and the flow adapts to the mode (connected surfaces the season-arc step; anthology hides cross-episode steps)
- [ ] **Phase 71: Mode-Aware Review** — in connected mode, episode review additionally considers continuity with prior episodes (character/plot coherence checked against the prior-episode summaries); lighter scope, no inconsistency-detection engine

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

<details>
<summary>✅ v6.0 Script Quality (Phases 45-49) — SHIPPED 2026-06-11 — full detail in milestones/v6.0-ROADMAP.md</summary>

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
- [x] 49-02-PLAN.md — Frontend: regenerateScene/keepSceneVersion client + SceneCompareModal + per-scene trigger — code complete (build clean); backend verified end-to-end 2026-06-11 (regenerate-scene preview confirmed working on a previously-failed scene: title+12.5K formatted content returned, no persist, no stale flip); runtime visual UAT confirmed by user 2026-06-11
**UI hint**: yes

</details>

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
**Plans:** 1/1 plans complete
Plans:
- [x] 54-01-PLAN.md — Upsert PATCH + screenplay-scoped ScreenplayContent reconcile (backend), writable empty state + heading splitter (frontend), and no-404/sync/idempotence/staleness tests

<!-- v8.0 MCP Server (planned 2026-06-11 — execution gated on v7.0 close) -->

### Phase 55: MCP Foundation — Mount, Auth, Lifespan & Client Spike
**Goal**: A remote Streamable HTTP MCP server is mounted in-process on the existing FastAPI app at `/mcp`, authenticated by the v5.0 `sa_<key>` gateway (per-key identity, usage accounting, and rate limiting carried through), and verified to round-trip from the real MCP clients — establishing the auth + transport foundation every tool depends on
**Depends on**: v5.0 API-key gateway (Phases 43-44), existing `get_current_user` / middleware stack / `main.py` lifespan
**Requirements**: MCPF-01, MCPF-02, MCPF-03, MCPF-04, MCPF-05
**Research/spike note**: HIGHEST STAKES — this phase carries Pitfalls 1-4. **Needs a scaffold-time research spike** to (a) pin the exact MCP library and import paths — STACK.md recommends the official `mcp` SDK, ARCHITECTURE.md recommends standalone `fastmcp` — decided against concrete needs (inbound `Authorization`-header access inside tools, sub-path mounting, lifespan composition, custom token verification, a single resolved Starlette version); and (b) verify Hermes static-header support (unverified). The static-bearer client-compatibility check is a **GO/NO-GO gate for the whole milestone** — run it before any tool work.
**Constraints to honor**: mount **in-process** (`app.mount("/mcp", ...)`), not a separate service; **exempt `/mcp` from `BaseHTTPMiddleware`** (rate-limiter/logger break streaming); compose the MCP session-manager lifespan into the app lifespan (else "Task group is not initialized"); every tool **owner-scoped** to the key's user (MCPF-04); read the inbound header fresh per call (no cached request context).
**Success Criteria** (what must be TRUE):
  1. A remote MCP client reaches `/mcp` over Streamable HTTP on the existing FastAPI app (no separate service/process) and completes `initialize` + tool-list
  2. A request with a valid `Authorization: Bearer sa_<key>` is authenticated via the shared gateway (prefix + SHA-256 lookup, scopes, expiry); an invalid/expired/missing key is rejected through the MCP endpoint
  3. An authenticated MCP call increments `request_count` / updates `last_used_at` and is subject to the per-key rate limit, exactly as REST calls are (verified via the MCP path, not just REST)
  4. The `whoami`/`ping` tool returns the resolved authenticated user, and a tool can only see resources owned by that user (no cross-user access)
  5. A static-header connection from Claude Code and Claude Desktop round-trips tool-list + one tool call; Hermes static-header support is verified in the same spike (if Hermes lacks static headers, v8.0 still ships for the Claude clients and Hermes is deferred to v8.1 — not a blocker)
**Plans**: TBD

### Phase 56: Job Registry, `job_status` & First AI-Backed Tool
**Goal**: Long-running (AI) tools return a job id immediately instead of blocking past the client timeout, a single generic `job_status` tool lets the agent poll and retrieve the result, and the first AI-backed generator proves the canonical `to_thread` + late-open/early-close DB-session pattern and pool tuning under concurrency
**Depends on**: Phase 55 (mounted, authed transport)
**Research note**: Decide job-registry durability (in-memory + TTL vs. a small table — survive restart?) and validate the `to_thread` + pool-sizing pattern under 3+ concurrent generations (Pitfalls 5-6).
**Constraints to honor**: long-running tools return **job-ids** (MCPJ-01); exactly **one** generic `job_status` tool (no per-generator status tools); never hold a sync DB session across the 60s+ AI `await` (load → run AI sessionless → persist); emit first byte fast; sanitize outbound script/breakdown text (first content-returning tool).
**Success Criteria** (what must be TRUE):
  1. A long-running tool (AI generation/extraction) returns a job identifier immediately rather than blocking the call past the client timeout
  2. A single generic `job_status(job_id)` tool returns a job's status and, when finished, its result
  3. Fast (non-AI) tools return their result synchronously in the same call (no job indirection)
  4. 3+ concurrent generation calls do not exhaust the DB pool or stall each other (event loop stays responsive; the web app stays up)
**Plans**: TBD

### Phase 57: Management Tools (project / show / episode / bible)
**Goal**: An agent can orient itself and create a target to write into — list/create/read the authenticated user's projects (plus read shows/episodes/bible) — the entry point for any MCP session
**Depends on**: Phase 55 (auth/session), Phase 56 (envelope conventions). Parallelizable with Phases 58-60.
**Requirements**: MCPP-01, MCPP-02, MCPP-03
**Constraints to honor**: thin adapter over existing services (wrap, never reimplement); all tools **owner-scoped** (MCPF-04 — never trust a `project_id` arg without an ownership check); **no delete tools**; target-id normalization so `project_id` ≡ `episode_id` for downstream tools.
**Success Criteria** (what must be TRUE):
  1. An agent can list the authenticated user's projects via a tool (id, title, framework), scoped to that user only
  2. An agent can create a project via a tool (title, framework) and receives the new project
  3. An agent can read a single project's metadata via a tool (the target to write into / extract from)
  4. No management tool can read or mutate another user's project/show
**Plans**: TBD

### Phase 58: Screenwriting Tools
**Goal**: An agent can read a project's screenplay, write one directly (the Phase 54 hand-written path), and generate a scene via the improved v6.0 generation path — completing the write side of the blank-page flow
**Depends on**: Phase 55 (auth/session), Phase 56 (job pattern for generation). Parallelizable with Phases 57, 59, 60.
**Requirements**: MCPW-01, MCPW-02, MCPW-03
**Constraints to honor**: wrap existing services (v6.0 generation path + Phase 54 write/split), never reimplement; the AI generate tool returns a **job-id** (MCPJ-01); keep hand-write and AI-generate as **distinct tools** (not a `mode:` param); owner-scoped; outbound script text sanitized.
**Success Criteria** (what must be TRUE):
  1. An agent can read a project's screenplay via a tool, scoped by project/episode and optionally by scene, returning the scene text
  2. An agent can write a screenplay directly via a tool (text split into scenes, persisted, breakdown/shotlist marked stale) — the Phase 54 path
  3. An agent can generate a screenplay scene via a tool using the v6.0 path (continuity, character voice, craft), returning a job id that `job_status` can resolve
**Plans**: TBD
**UI hint**: yes

### Phase 59: Breakdown Tools
**Goal**: An agent can trigger breakdown extraction (the v7.0 fidelity path) and read the resulting elements, category-scoped, with their per-scene appearances and context
**Depends on**: Phase 55 (auth/session), Phase 56 (job pattern for extraction). Parallelizable with Phases 57, 58, 60.
**Requirements**: MCPB-01, MCPB-02
**Constraints to honor**: wrap the existing v7.0 `breakdown_service` (idempotent re-extract, preserve user edits), never reimplement; extraction returns a **job-id** (MCPJ-01); reads are **category-scoped/filterable** to keep results small; owner-scoped; outbound element/context text sanitized.
**Success Criteria** (what must be TRUE):
  1. An agent can trigger breakdown extraction for a project via a tool using the v7.0 path, returning a job id that `job_status` can resolve
  2. An agent can read a project's breakdown elements via a tool, scoped/filterable by category, returning the elements and their per-scene appearances + context
  3. Reading the breakdown of a project the key does not own is rejected
**Plans**: TBD

### Phase 60: Shotlist Tools
**Goal**: An agent can read a project's shotlist, create a shot, and AI-generate a shotlist — completing the production-breakdown arc
**Depends on**: Phase 55 (auth/session), Phase 56 (job pattern for AI generation). Parallelizable with Phases 57, 58, 59.
**Requirements**: MCPS-01, MCPS-02, MCPS-03
**Constraints to honor**: wrap the existing shotlist services (CRUD + AI shotlist path), never reimplement; the AI-generate tool returns a **job-id** (MCPJ-01); fast reads/creates return synchronously (MCPJ-03); **no delete tools**; owner-scoped.
**Success Criteria** (what must be TRUE):
  1. An agent can read a project's shotlist via a tool, with shots grouped by scene
  2. An agent can create a shot via a tool (returned synchronously)
  3. An agent can generate a shotlist via a tool using the AI shotlist path, returning a job id that `job_status` can resolve
**Plans**: TBD

### Phase 61: Discovery Polish, Error Mapping & Client-Matrix UAT
**Goal**: The tool surface is introspectable by a generic MCP client without app-specific glue (clear names/descriptions/schemas, long-running tools flagged), app errors map to clean MCP tool errors instead of raw stack traces, and the complete surface is verified end-to-end across the client matrix
**Depends on**: Phases 57, 58, 59, 60 (the full tool surface must exist to finalize discovery and run UAT)
**Requirements**: MCPD-01, MCPD-02
**Constraints to honor**: descriptions ARE the API for generic clients — state preconditions and which tools are long-running (job-returning); `readOnlyHint` / `idempotentHint` annotations on reads; map not-found/unauthorized/validation/generation-failure to clear MCP errors (`mcp/errors.py`); re-verify ownership-scoping and concurrent long-call behavior end-to-end.
**Success Criteria** (what must be TRUE):
  1. Each tool advertises a clear name, description, and input schema so Claude Code / Desktop / Hermes can introspect and call it without app-specific glue, including stating which tools are long-running (job-returning)
  2. App errors (not found, unauthorized, validation, generation failure) are returned as clear MCP tool errors rather than raw stack traces or opaque 500s
  3. A full client-matrix UAT (Claude Code, Desktop, Hermes) drives the blank-page → screenplay → breakdown → shotlist flow end-to-end, including a 60s+ generation that completes without client timeout and a cross-key ownership-denial check
**Plans**: TBD

### Phase 62: Config Parametrization & Migrations-on-Boot
**Goal**: Every production-environment-specific value is supplied via env vars (no hardcoded localhost), and a fresh or upgraded Postgres reaches the current schema automatically on boot — the prerequisite groundwork that lets every later phase target a real host
**Depends on**: Nothing (first phase of v9.0; runs entirely in-repo, no external account)
**Requirements**: DCFG-01, DCFG-02, DMIG-01
**Constraints to honor**: parametrize all three known localhost hardcodes — `ALLOWED_ORIGINS` (config.py + docker-compose), `VITE_API_URL` (frontend, already reads `import.meta.env.VITE_API_URL || '/api'`), and the MCP base URL (`http://localhost:8001` AuthSettings issuer/resource_server_url in mcp_server/server.py); migrations apply via `init_db` on boot (user's chosen approach over a CI release step) and MUST stay idempotent against the existing `backend/migrations/delta/*.sql`; local `docker compose up` must still work with sensible defaults.
**Success Criteria** (what must be TRUE):
  1. `ALLOWED_ORIGINS` is read from the environment in config.py (and docker-compose), defaulting to localhost for local dev, with no hardcoded prod origin in the repo
  2. The MCP server's issuer / resource_server_url is read from an env var instead of the hardcoded `http://localhost:8001`
  3. Starting the backend against an empty Postgres runs all `delta/*.sql` via `init_db` and reaches the current schema with no manual step; starting it again is a no-op (idempotent)
  4. The frontend build consumes `VITE_API_URL` with `/api` as the local-dev fallback (no hardcoded backend host)
**Plans**: 2 plans
- [x] 62-01-PLAN.md — Parametrize MCP base URL via Settings (DCFG-02); verify+document ALLOWED_ORIGINS & VITE_API_URL env-readability (DCFG-01)
- [x] 62-02-PLAN.md — Migrations-on-boot: fresh-DB init_db.sql step 0 + advisory lock + fail-hard delta loop + tests (DMIG-01)

### Phase 63: Backend + Postgres + Volume on Railway
**Goal**: The FastAPI backend runs live on Railway against a Railway Postgres with pgvector and a persistent `/media` volume, with all secrets supplied through Railway env
**Depends on**: Phase 62 (env parametrization + migrations-on-boot must exist so the service boots cleanly against a fresh Railway Postgres)
**Requirements**: DBKD-01, DBKD-02, DBKD-03, DBKD-04
**Constraints to honor**: single Railway Postgres holds ALL data (projects, scripts, users, api_keys + pgvector RAG embeddings) — not a separate agent DB; `pgvector` extension must be enabled (tables concepts/book_chunks/agent_books need it); the `/media` volume must be persistent so uploads survive redeploys (StaticFiles mount is at `/media`); build reproducibly via the existing `Procfile` (+ nixpacks) or a production Dockerfile, serving on Railway's injected `$PORT`; secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SECRET_KEY`) are entered by the user into Railway env and never committed — config.py already rejects the default `SECRET_KEY` in prod. **Human-in-the-loop**: user performs Railway login/authorization and enters the secrets.
**Success Criteria** (what must be TRUE):
  1. The backend `/health` endpoint responds successfully at the Railway-assigned domain
  2. The app connects to the Railway Postgres via the auto-injected `DATABASE_URL`, with the `pgvector` extension enabled (vector-backed tables function)
  3. A file uploaded via the media endpoint survives a backend redeploy (the `/media` volume is persistent, not ephemeral)
  4. The backend runs with secrets sourced from Railway env (no secret in the repo) and boots without the default-`SECRET_KEY` prod guard firing
**Plans**: TBD

### Phase 64: Frontend on Vercel
**Goal**: The frontend is live on Vercel and talks to the production Railway backend
**Depends on**: Phase 63 (the Railway backend domain must exist to point `VITE_API_URL` at it)
**Requirements**: DFND-01, DFND-02
**Constraints to honor**: build with `npm run build` (`tsc && vite build`) — there are pre-existing TypeScript build concerns noted in earlier milestones; `VITE_API_URL` is set in Vercel to the Railway backend domain (no hardcoded localhost), consuming the Phase 62 parametrization; CORS on the backend will be locked to this Vercel domain in Phase 66. **Human-in-the-loop**: user performs Vercel (VAPAI-Studio) login/authorization and confirms the deployed domain.
**Success Criteria** (what must be TRUE):
  1. The frontend builds on Vercel via `npm run build` and serves at a Vercel domain
  2. The deployed frontend issues API calls to the Railway backend domain (via `VITE_API_URL`), not to localhost
  3. A user can load the app in the browser and complete an end-to-end action (e.g. list/open a project) against the production backend
**Plans**: TBD
**UI hint**: yes

### Phase 65: CI/CD with GitHub Actions
**Goal**: Pushes are gated by the test suite and merges to `main` deploy both targets automatically
**Depends on**: Phase 63 and Phase 64 (both deploy targets must be configured before the deploy workflow can target them)
**Requirements**: DCICD-01, DCICD-02
**Constraints to honor**: no `.github/workflows/` exists yet — this phase creates them; the test job runs the backend suite (~399 tests) as a gate, tolerating the 4 documented pre-existing flakes (do not let known flakes block the pipeline); deploy fires on merge to `main` = prod (backend → Railway, frontend → Vercel); deploy credentials (Railway/Vercel tokens) are stored as GitHub secrets, never in the repo. **Human-in-the-loop**: user generates and enters the Railway/Vercel deploy tokens into GitHub repo secrets.
**Success Criteria** (what must be TRUE):
  1. A push to any branch triggers a GitHub Actions run of the backend test suite, and a failing test (beyond the tolerated flakes) fails the run
  2. A merge to `main` triggers an automatic deploy of the backend to Railway
  3. A merge to `main` triggers an automatic deploy of the frontend to Vercel
  4. Deploy credentials live in GitHub secrets, with none committed to the repo
**Plans**: TBD

### Phase 66: Public-Deploy Hardening & Post-Deploy Smoke Test
**Goal**: The public deploy is locked down for a public host and a smoke test proves prod is actually live before a deploy counts as successful
**Depends on**: Phase 64 (the Vercel domain must exist to lock CORS to it) and Phase 65 (the deploy pipeline the smoke test gates)
**Requirements**: DSEC-01, DVER-01
**Constraints to honor**: `ALLOWED_ORIGINS` set to the Vercel frontend domain in prod (consuming Phase 62 parametrization); `/mcp` is now publicly reachable — review and set DNS-rebinding protection appropriately for a public host (it was off for local) and confirm CORS posture for the public MCP surface; the post-deploy smoke test (backend `/health` + frontend loads) must run as the success gate of a deploy, not a manual afterthought.
**Success Criteria** (what must be TRUE):
  1. In production, cross-origin requests from the Vercel domain are allowed and requests from other origins are rejected (CORS locked via `ALLOWED_ORIGINS`)
  2. The now-public `/mcp` endpoint's DNS-rebinding protection has been reviewed and set appropriately for a public host
  3. A post-deploy smoke test confirms the backend `/health` responds at the Railway domain AND the deployed frontend loads, and this check gates deploy success
**Plans**: TBD

### Phase 67: Continuity Data Model & Migration
**Goal**: A Show can declare its `continuity_mode` and every episode can carry an AI summary that is automatically invalidated when the episode changes — the data foundation the generation, summary, wizard, and review phases all read
**Depends on**: Nothing (first phase of v10.0; pure schema + API groundwork)
**Requirements**: SCONT-01, ESUM-02
**Constraints to honor**: add `shows.continuity_mode` (enum `connected` | `anthology` | `standalone`), `projects.episode_summary` (TEXT, nullable), and `projects.episode_summary_stale` (Boolean, default False) via a NEW idempotent `backend/migrations/delta/NNN_*.sql` applied on boot (Phase 62 mechanism) — never an in-place ALTER that breaks re-runs; the stale flag mirrors the existing `breakdown_stale`/`shotlist_stale` pattern exactly; editing an episode (its screenplay/content) must set `episode_summary_stale=True`; standalone projects (`show_id` NULL) are unaffected. **Open question (resolve at plan-phase, not a blocker)**: the default `continuity_mode` applied to existing shows on migration — `connected` preserves the implicit "season" intent, `anthology` is the safest no-behavior-change default; decide here.
**Success Criteria** (what must be TRUE):
  1. A Show can be created or edited with a `continuity_mode` of `connected`, `anthology`, or `standalone`, and the value persists and is readable via the Show API
  2. Starting the backend against an existing database applies the new `delta/NNN_*.sql` once and is a no-op on re-run (idempotent), with existing shows/episodes still valid and standalone projects unchanged
  3. Each episode (Project) has an `episode_summary` (initially empty/null) and an `episode_summary_stale` flag defaulting to False
  4. Editing an episode sets its `episode_summary_stale` to True, exactly as a script change sets `breakdown_stale`/`shotlist_stale`
**Plans**: 3 plans
- [x] 67-01-PLAN.md — Schema foundation: idempotent delta 011 + Show/Project model columns
- [x] 67-02-PLAN.md — Show continuity_mode API (enum + ShowCreate/Update/Response + tests)
- [x] 67-03-PLAN.md — Episode summary stale hook + read-only flag surface + tests

### Phase 68: Mode-Aware Generation Context Injection
**Goal**: When the AI writes an episode, the prior context it receives is determined by the show's `continuity_mode` — connected carries continuity, anthology stays bible-only, standalone is fully independent
**Depends on**: Phase 67 (the `continuity_mode` column and `episode_summary` storage must exist for generation to branch on them)
**Requirements**: SCONT-02, SCONT-03, SCONT-04
**Constraints to honor**: branch at the existing `bible_context` assembly point (`breakdown_service.py:312` shows the pattern to mirror) inside the episode-writing prompt builders (`openai_service.py` / anthropic); in `connected` mode inject the season arc PLUS the `episode_summary` of prior episodes ordered by `episode_number` (the reliable key — NEVER positional, see the ScreenplayContent ordering bug that bit twice); in `anthology` inject only the shared bible (world/tone); in `standalone` inject no cross-episode context (feature-film behavior); standalone projects with `show_id` NULL keep their current behavior unchanged. This phase only READS summaries — it does not generate or regenerate them (that is Phase 69), so a missing/stale summary must degrade gracefully (e.g. skip that episode's contribution) rather than fail generation. **Open question (resolve at plan-phase, not a blocker)**: the token-budget / truncation policy when a connected season has many prior summaries — summaries are bounded but still need a cap.
**Success Criteria** (what must be TRUE):
  1. Generating an episode in a `connected` show feeds the prompt the season arc plus the summaries of prior episodes, ordered by `episode_number` (not positional)
  2. Generating an episode in an `anthology` show feeds the prompt only the shared bible (world/tone) — no other-episode plot context
  3. Generating an episode in a `standalone` show (or a standalone project) injects no cross-episode context
  4. A connected episode with one or more missing/empty prior summaries still generates without error (degrades gracefully)
**Plans:** 1/1 plans complete
- [x] 68-01-PLAN.md — Branch build_bible_context on continuity_mode: connected injects ordered (episode_number.asc), most-recent-8-capped, stale-tagged prior-episode summaries; anthology/standalone bible-only; show_id NULL unchanged + TestContinuityModeInjection (SCONT-02/03/04)

### Phase 69: Auto Episode Summary & Lazy Regeneration
**Goal**: Each episode gets an AI-generated summary automatically, and a stale summary is refreshed before it is ever used as context for a later episode — so connected generation never reads an out-of-date summary
**Depends on**: Phase 67 (the `episode_summary` / `episode_summary_stale` columns) and Phase 68 (the connected-mode injection that consumes the summaries)
**Requirements**: ESUM-01, ESUM-03
**Constraints to honor**: the summary is AI-AUTO-generated, not hand-written and not the full prior script (locked decision D2 — full scripts blow up tokens, manual summaries break the "magic"); it is stored on the episode (Project.`episode_summary`); regeneration is LAZY — a summary marked stale (Phase 67 flag) is regenerated just-in-time before Phase 68 reads it for a later episode, not eagerly on every edit; embeddings are OpenAI-only but summary text gen can use OpenAI or Anthropic via the existing provider abstraction. **Open question (resolve at plan-phase, not a blocker)**: exactly where the auto-summary first fires — on an explicit "complete episode" action vs. on the first request for a later episode's context — which affects cost and UX; decide here.
**Success Criteria** (what must be TRUE):
  1. Completing an episode generates an `episode_summary` via the AI and stores it on the episode
  2. A summary whose `episode_summary_stale` flag is True is regenerated before it is used as prior-episode context for a later connected episode, and the flag is cleared after a successful regeneration
  3. Regenerating one episode's stale summary does not regenerate or disturb other episodes' up-to-date summaries
**Plans**: TBD

### Phase 70: Show Creation Wizard (mode + presets)
**Goal**: At show creation (and edit), the user picks how episodes relate via friendly presets, and the flow adapts to that choice — making continuity mode a first-class, understandable setup step
**Depends on**: Phase 67 (the `continuity_mode` the wizard writes must exist on the Show model/API)
**Requirements**: SWZ-01, SWZ-02
**Constraints to honor**: presets (Microserie / Serie conectada / Antología) are PURE UI SUGAR over the single `continuity_mode` (locked decision D5) — they set the mode (+ optionally a sensible default `episode_duration_minutes`, which stays metadata, NOT part of the type per D4); the model stores only `continuity_mode`, never the preset label; the flow adapts to the mode (connected surfaces the season-arc bible step; anthology hides cross-episode steps); editing an existing show can change the mode (reuses the Phase 67 set/edit API).
**Success Criteria** (what must be TRUE):
  1. When creating a show, the user can pick a continuity mode via the Microserie / Serie conectada / Antología presets, and the chosen preset sets the underlying `continuity_mode`
  2. The creation flow adapts to the selected mode — connected surfaces the season-arc step, anthology hides cross-episode steps
  3. The persisted show carries only the resulting `continuity_mode` (presets leave no separate stored field), and a later edit can change the mode
**Plans**: TBD
**UI hint**: yes

### Phase 71: Mode-Aware Review
**Goal**: Episode review understands the show's continuity mode — connected episodes are reviewed for coherence with what came before, without standing up a full inconsistency-detection engine
**Depends on**: Phase 68 (mode-aware context) and Phase 69 (prior-episode summaries must exist and be fresh to review against)
**Requirements**: SREV-01
**Constraints to honor**: scope is deliberately LIGHT — in `connected` mode, review additionally considers character/plot coherence against the prior-episode summaries; this is NOT the deferred automatic continuity-inconsistency detection ("character X is dead in ep2 but appears in ep4") — that stays out of this milestone; reuse the prior-episode summaries from Phase 69 as the coherence reference (ordered by `episode_number`); anthology/standalone review keeps its current standalone-quality scope (no cross-episode checks).
**Success Criteria** (what must be TRUE):
  1. In a `connected` show, episode review surfaces continuity considerations checked against the prior-episode summaries (character/plot coherence)
  2. In `anthology` and `standalone` modes, review does not perform cross-episode continuity checks (standalone-quality scope preserved)
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
| 45. Continuity-Aware Generation | v6.0 | 1/1 | Complete | 2026-06-06 |
| 46. Format Fidelity (Native vs JSON Mode) | v6.0 | 1/1 | Complete | 2026-06-06 |
| 47. Character Voice Injection | v6.0 | 1/1 | Complete | 2026-06-06 |
| 48. Screenwriting Craft Guidance | v6.0 | 1/1 | Complete | 2026-06-06 |
| 49. Side-by-Side Quality Compare | v6.0 | 2/2 | Complete | 2026-06-06 |
| 50. Scene-Text Extraction | v7.0 | 1/1 | Complete | 2026-06-08 |
| 51. Per-Appearance Context | v7.0 | 1/1 | Complete | 2026-06-08 |
| 52. Expanded Categories | v7.0 | 1/1 | Complete | 2026-06-08 |
| 53. Re-Extraction on Change | v7.0 | 1/1 | Complete | 2026-06-08 |
| 54. Direct Screenplay Writing | (standalone) | 1/1 | Complete | 2026-06-11 |
| 55. MCP Foundation — Mount, Auth, Lifespan & Client Spike | v8.0 | 0/? | Not started | - |
| 56. Job Registry, job_status & First AI-Backed Tool | v8.0 | 0/? | Not started | - |
| 57. Management Tools | v8.0 | 0/? | Not started | - |
| 58. Screenwriting Tools | v8.0 | 0/? | Not started | - |
| 59. Breakdown Tools | v8.0 | 0/? | Not started | - |
| 60. Shotlist Tools | v8.0 | 0/? | Not started | - |
| 61. Discovery Polish, Error Mapping & Client-Matrix UAT | v8.0 | 0/? | Not started | - |
| 62. Config Parametrization & Migrations-on-Boot | v9.0 | 2/2 | Complete   | 2026-06-14 |
| 63. Backend + Postgres + Volume on Railway | v9.0 | 0/? | Not started | - |
| 64. Frontend on Vercel | v9.0 | 0/? | Not started | - |
| 65. CI/CD with GitHub Actions | v9.0 | 0/? | Not started | - |
| 66. Public-Deploy Hardening & Post-Deploy Smoke Test | v9.0 | 0/? | Not started | - |
| 67. Continuity Data Model & Migration | v10.0 | 3/3 | Complete   | 2026-06-17 |
| 68. Mode-Aware Generation Context Injection | v10.0 | 1/1 | Complete   | 2026-06-17 |
| 69. Auto Episode Summary & Lazy Regeneration | v10.0 | 0/? | Not started | - |
| 70. Show Creation Wizard (mode + presets) | v10.0 | 0/? | Not started | - |
| 71. Mode-Aware Review | v10.0 | 0/? | Not started | - |
