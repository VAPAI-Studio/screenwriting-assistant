---
gsd_state_version: 1.0
milestone: v10.0
milestone_name: Show Type / Episode Continuity
status: executing
stopped_at: Completed 67-02-PLAN.md
last_updated: "2026-06-17T18:05:45.394Z"
last_activity: 2026-06-17
progress:
  total_phases: 36
  completed_phases: 1
  total_plans: 5
  completed_plans: 8
  percent: 3
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-24)

**Core value:** From blank page to production-ready breakdown -- AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 67 — continuity-data-model-migration

- Backend (Railway): https://web-production-73857.up.railway.app (/health 200)
- Frontend (Vercel): https://screenwriting-assistant-lake.vercel.app (verified working in browser)
- CORS locked to the Vercel domain. Postgres+pgvector live, migrations applied on boot.
- ONLY REMAINING: Phase 65 auto-deploy = generate Railway/Vercel deploy tokens → GitHub secrets (+ optional PROD_*_URL smoke secrets). Everything else done.

(old focus) v9.0 Deploy — repo-work complete for all 5 phases; awaiting manual deploy steps

## Current Position

Phase: 67 (continuity-data-model-migration) — EXECUTING
Plan: 3 of 3
Status: Ready to execute
Last activity: 2026-06-17

**v10.0 phase map (67-71):**

- Phase 67 Continuity Data Model & Migration — SCONT-01, ESUM-02 (shows.continuity_mode + episode_summary/_stale via delta migration)
- Phase 68 Mode-Aware Generation Context Injection — SCONT-02/03/04 (branch prior-context on mode; prior summaries ordered by episode_number)
- Phase 69 Auto Episode Summary & Lazy Regeneration — ESUM-01, ESUM-03 (AI auto-summary on completion; lazy regen of stale)
- Phase 70 Show Creation Wizard (mode + presets) — SWZ-01, SWZ-02 (presets are UI sugar over the single mode)
- Phase 71 Mode-Aware Review — SREV-01 (connected continuity review vs prior summaries; light scope)

**Locked decisions (do not re-ask):** single continuity_mode axis; AI auto-summary (not manual/full-script); stale-flag invalidation + lazy regen; scale stays metadata (episode_duration_minutes); presets are UI sugar.
**Deferred (no phases):** continuity-inconsistency detection; multi-season; hand-editable summaries; scale-as-behavior.
**Open questions for plan-phase (folded into phase notes, not blockers):** default continuity_mode on migration (P67); when the auto-summary fires (P69); token-budget cap for long connected seasons (P68).

## Performance Metrics

**Velocity:**

- Total plans completed: 59 (lifetime)
- Average duration: ~3min (recent)
- Total execution time: ~2.92 hours (lifetime)

**Recent Trend:**

- Last 5 plans: 51-01, 52-01 (~12min), 53-01 (~3min), 54-01 (~4min)
- Trend: Stable

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

Relevant to v4.2:

- Episodes reuse existing Project model with nullable show_id FK (not a separate table)
- Bible stored as columns on Show model (not separate table) for simplicity
- Bible injection modifies existing generation services, not a new service
- Standalone projects unaffected -- show_id = NULL means no bible context
- Used str() cast on UUID filters in shows router for SQLite/PostgreSQL compatibility
- Show model has no relationships yet -- Phase 37 adds bible columns, Phase 39 adds episodes
- Bible data accessed via dedicated /bible sub-resource endpoints, not mixed into ShowResponse
- Episode duration accepts any integer 1-480 (not restricted to presets)
- ShowCard displays hardcoded "0 episodes" -- actual count comes in Phase 39
- Home page split into "Shows" (indigo) and "Films" (amber) sections
- Show components live in frontend/src/components/Shows/ directory
- No query invalidation on bible mutation -- prevents refetch from overwriting local state
- Used loaded ref pattern for bible editor initial state
- Duration changes save immediately (select is discrete, not blur-based)
- [Phase 39]: Episodes reuse Project model with nullable show_id FK -- episode_number auto-increments via MAX+1
- [Phase 40]: Reuse deleteProject API for episode deletion since episodes are Projects with show_id FK
- [Phase 41]: Bible context built once in request handler, passed as string to background tasks (avoids DB re-fetch)
- [Phase 42]: Show title fetched with staleTime: Infinity in breadcrumb (stable within session)
- [Phase 42]: Breadcrumb height adjustment uses fixed 89px calc (56px header + 33px breadcrumb)
- [Phase 44]: Atomic SQL UPDATE for request_count avoids race conditions vs ORM-level increment
- [Phase 44]: Per-key rate limiter uses in-memory timestamp tracking (same pattern as IP rate limiter)
- [Phase 44]: rate_limit column defaults to NULL meaning use system default (1000 req/hour)
- [Phase 45]: Scene generation threads a running prose synopsis + the immediately-preceding scene's verbatim text into each later prompt; first/single scene gets no continuity block
- [Phase 45]: Synopsis re-summarized to a ~400-word cap per scene via a separate json_mode=False chat_completion call; advances only on success so a failed scene cannot poison continuity
- [Phase 45]: Final synopsis persisted into existing screenplay_editor PhaseData.content JSON via flag_modified — no migration; per-screenplay {title,content,episode_index} contract unchanged
- [Phase 46]: Scene-writing call switched to native output (json_mode=False) so JSON string-encoding no longer degrades screenplay formatting; title parsed off a TITLE: line with scene-summary fallback (never fails on missing title)
- [Phase 46]: Native path adopted outright (no runtime A/B toggle, D-46-04); Phase 45 {screenplays,synopsis} + per-screenplay {title,content,episode_index} contract and success-only continuity advance preserved byte-for-byte
- [Phase 46]: Continuity test mock routes scene-vs-synopsis by the positive 'YOUR TASK: Write scene' marker (both calls now json_mode=False); avoids ambiguous 'story so far' string
- [Phase 47]: run_wizard injection guard broadened to wizard_type in ('scene_wizard','script_writer_wizard') so character profiles reach _generate_scripts; persisted WizardRun.config=request.config split preserved (no _characters re-persisted)
- [Phase 47]: _generate_scripts injects a conditional character_block (reused _build_character_section + a 'distinct, consistent voice' instruction) that collapses to '' when _characters is empty/absent → byte-identical Phase 46 prompt; SCENE_MARKER, json_mode=False, return contract, continuity advance unchanged
- [Phase 47]: under-specified voices are derived + carried by the Phase 45 continuity block (no structured voice ledger), consistent with Phase 45's no-ledger decision
- [Phase 48]: _generate_scripts carries an UNCONDITIONAL '## Screenwriting Craft' block (subtext/on-the-nose, economical action, show-don't-tell + 'no internal or unfilmable description', white-space pacing) as a plain f-string literal — added equally to both character paths so Phase 47's byte-identical empty-vs-absent contract holds
- [Phase 48]: craft anchors chosen to NOT collide with continuity ('Story so far'/'Previous scene') or voice ('distinct, consistent voice') markers asserted ABSENT elsewhere; all 21 prior tests stay green; lines 394-462 untouched (additive only)
- [Phase 49]: extracted _generate_one_scene as the SINGLE shared per-scene prompt source; _generate_scripts loop + new regenerate_single_scene both delegate to it (no divergent prompt); 27 prior tests stay green byte-for-byte
- [Phase 49]: single-scene regenerate returns a PREVIEW (no DB write); keep persists only screenplays[episode_index] + the matching ScreenplayContent row and marks breakdown/shotlist stale; global synopsis left untouched on keep (D-49-05); episode_index is the implicit scene key (no migration, D-49-03)
- [Phase 49]: regenerate/keep owner filter uses str() coercion (codebase _verify_project_ownership convention), not run_wizard's raw-UUID compare — Postgres-safe AND SQLite-test-safe
- [Phase ?]: [Phase 50]: breakdown prompt restructured to per-scene '### Scene {i+1}' indexed text in the shared 1-based scene_index space; _align_screenplay_to_scenes never raises; full-coverage gate falls back to concatenated form; single AI call + on-screen rules preserved
- [Phase 52]: breakdown taxonomy expanded 5→10 (set_dressing, animal, sfx, makeup_hair, extras) additively across 6 lockstep sites (enum, schema regex gate, prompt CATEGORIES + ExtractedElement desc, FE union, FE constants); category stays String(50) so NO migration and existing rows valid (CATG-02)
- [Phase 52]: CRITICAL RULES + DEDUPLICATION prompt blocks preserved verbatim; new categories are on-screen-only with a precedence note (ridden horse → animal; set_dressing vs prop = handled/featured → prop else set_dressing); tsc exhaustiveness on Record<BreakdownCategory,...> maps is the FE build gate
- [Phase 53]: extract loop skips _reconcile_scene_links when db_element.user_modified is True (loop guard, D-53-01) — user-owned elements' scene links are left untouched on re-extract; element_map membership preserved; non-user_modified elements STILL reconcile (Test B proves the guard is scoped to user_modified only); additive guard only, no schema change/migration/FE change (D-53-03); REEX-01 full chain (stale→re-extract→preserve→clear) proven by an integration test (D-53-02)
- [Phase 54]: PATCH /phase-data is now a generic upsert (fetch-or-create, mirrors wizards.py) so the first save from an empty project no longer 404s (D-54-01); ScreenplayContent sync lives in a guarded branch `if phase=="write" and subsection_key=="screenplay_editor"` inside the generic PATCH (no new endpoint, no FE client change, D-54-05 option b) — delete-then-recreate scoped to project_id keeps repeated saves idempotent; formatted_content=sp preserves episode_index for v7.0 scene alignment; manual save REPLACES (wizard apply still APPENDS, unchanged); generic non-screenplay subsections never create ScreenplayContent (test-enforced)
- [Phase 54]: splitByHeadings is the pure zero-originals splitter (INT./EXT. slugline → one scene each; no heading → one "Untitled"; empty → []); title=slugline, content=body-after-slugline with the slugline STRIPPED because buildDocument re-prepends title.toUpperCase() (would double-render otherwise, D-54-03); after first save the existing title-anchor splitToScreenplays handles round-trips stably; empty editor is writable via a "Start writing" affordance (D-54-02)
- [Phase 67]: continuity_mode is VARCHAR(20) String default 'anthology' (D-03), NOT a PG Enum so new modes need no ALTER TYPE migration
- [Phase 67]: default 'anthology' = zero behavior change on upgrade (D-01); episode_summary_stale mirrors breakdown_stale/shotlist_stale; both ORM default + server_default set so non-ORM inserts default correctly
- [Phase ?]: [Phase 67]: ContinuityMode lives in schemas.py as a str-enum (app layer, D-03), VARCHAR column unchanged; Pydantic rejects out-of-enum continuity_mode with 422, default anthology = unchanged behavior
- [Phase ?]: [Phase 67]: update_show loop coerces Enum members to .value before setattr so the VARCHAR continuity_mode column stores 'standalone', not 'ContinuityMode.STANDALONE'

### Pending Todos

- **[Phase 62 — prerequisite]** Parametrize all three localhost hardcodes via env: `ALLOWED_ORIGINS` (config.py + docker-compose), `VITE_API_URL` (frontend — already reads `import.meta.env.VITE_API_URL || '/api'`), MCP base URL (`http://localhost:8001` AuthSettings issuer/resource_server_url in mcp_server/server.py). Wire `init_db`-on-boot to apply the idempotent `backend/migrations/delta/*.sql` (user chose this over a CI release step). Local `docker compose up` must still work with localhost defaults.
- **[Phase 63 — human-in-the-loop]** User logs in to Railway (VAPAI-Studio) and enters secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, generated `SECRET_KEY`) into Railway env — never the repo. Single Railway Postgres holds ALL data + pgvector RAG embeddings (not a separate agent DB); enable the `pgvector` extension; mount a PERSISTENT volume at `/media` so uploads survive redeploys. `Procfile`/`runtime.txt` already exist; serve on `$PORT`.
- **[Phase 64 — human-in-the-loop]** User logs in to Vercel (VAPAI-Studio), confirms the deployed domain, and `VITE_API_URL` is set to the Railway backend domain. Watch the pre-existing TypeScript build concerns noted in earlier milestones.
- **[Phase 65 — human-in-the-loop]** No `.github/workflows/` exists yet. User generates Railway/Vercel deploy tokens and enters them as GitHub repo secrets. Test gate runs ~399 tests; tolerate the 4 documented pre-existing flakes (don't let them block the pipeline). Deploy on merge to `main` = prod.
- **[Phase 66]** Lock `ALLOWED_ORIGINS` to the Vercel domain in prod; review `/mcp` DNS-rebinding protection (was off locally) now that `/mcp` is public; smoke test (`/health` + frontend loads) gates deploy success.
- **[Out of scope this milestone — known debt, do NOT add phases]** legacy `framework` Postgres enum bug; clean-`docker compose build` dependency-pin confirmation; Hermes static-header verification.

## Deferred Items

Items acknowledged and deferred at v6.0 milestone close on 2026-06-11:

| Category | Item | Status |
|----------|------|--------|
| verification_gap | phase-27 (v3.1 — shipped) | human_needed (pre-existing, old milestone) |
| verification_gap | phase-31 (v3.2 — shipped) | gaps_found (pre-existing, old milestone) |
| verification_gap | phase-33 (v4.0 — shipped) | human_needed (pre-existing, old milestone) |
| verification_gap | phase-34 (v4.0 — shipped) | human_needed (pre-existing, old milestone) |
| verification_gap | phase-54 (post-v7.0 standalone) | human_needed (3 visual UAT items, not v6.0) |
| tech_debt | ScreenplayContent duplicate-row accumulation per episode_index | deferred per D-49-03 (needs schema change) |
| tech_debt | test-suite isolation flakiness (yolo/session tests) | pre-existing, not a v6.0 regression |
| tech_debt | frontend npm run lint references non-existent ESLint config | tsc/build is the binding type gate |

These do not block v6.0; the v6.0 phase-48 gap was resolved by the 2026-06-11 UAT. The phase-27/31/33/34 gaps belong to already-shipped milestones (v3.1–v4.0).
| Phase 67 P01 | 4min | 2 tasks | 2 files |
| Phase 67 P02 | 5min | 2 tasks | 3 files |

### Blockers/Concerns

- None. Pre-existing TypeScript build errors in IndividualEditorView, RepeatableCardsView, SidebarChat were fixed in session following v4.2 completion.
- v5.0 phases renumbered from 36-37 to 43-44 to make room for v4.2

## Session Continuity

Last session: 2026-06-17T18:05:45.387Z
Stopped at: Completed 67-02-PLAN.md
Resume file: None
