# Requirements: Screenwriting Assistant

**Defined:** 2026-03-24 (v4.2) · updated 2026-06-17 (v10.0 — Show Type / Episode Continuity)
**Active Milestone:** v10.0 — Show Type / Episode Continuity. v9.0 Deploy shipped & live.
**Core Value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## v10.0 Requirements — Show Type / Episode Continuity

**Defined:** 2026-06-17 · Each Show declares a single `continuity_mode` that changes what prior context the AI receives when writing an episode: connected series/microseries carry continuity (season arc + auto-generated summaries of prior episodes), anthologies stay independent, standalone is a single feature. Builds on the existing Show/Episode model (episodes are `Project` rows with `show_id` + `episode_number`). Full decisions + deferred items in `.planning/v10.0-SHOW-TYPE-VISION.md`. Note: prefix `CONT` is taken by v6.0 (Script Continuity); this milestone uses `SCONT` (Show Continuity).

### Show continuity mode + generation (SCONT)

- [x] **SCONT-01**: User can set a Show's continuity mode (`connected` / `anthology` / `standalone`) when creating or editing the show
- [x] **SCONT-02**: In `connected` mode, generating an episode feeds the AI the season arc plus the summaries of prior episodes, ordered by `episode_number` (never positional)
- [x] **SCONT-03**: In `anthology` mode, episode generation receives only the shared bible (world/tone), with no other-episode context
- [x] **SCONT-04**: In `standalone` mode, no cross-episode context is injected (feature-film behavior)

### Auto episode summary + invalidation (ESUM)

- [x] **ESUM-01**: When an episode is completed, the AI generates and stores a summary of that episode (`episode_summary`)
- [x] **ESUM-02**: Editing an episode marks its summary stale (`episode_summary_stale`), mirroring the `breakdown_stale`/`shotlist_stale` pattern
- [x] **ESUM-03**: A stale episode summary is regenerated before it is used as context for later episodes (lazy regeneration)

### Show creation wizard (SWZ)

- [x] **SWZ-01**: User picks the continuity mode at show creation, with presets (Microserie / Serie conectada / Antología) as visual shortcuts that set the underlying mode
- [x] **SWZ-02**: The creation flow adapts to the mode (connected surfaces the season-arc step; anthology hides cross-episode steps)

### Mode-aware review (SREV)

- [x] **SREV-01**: In `connected` mode, episode review considers continuity with prior episodes (character/plot coherence against the prior-episode summaries)

## v9.0 Requirements — Deploy (Railway + Vercel + CI/CD)

**Defined:** 2026-06-14 · Get the app running in production: backend + Postgres on Railway, frontend on Vercel, with GitHub Actions running tests on push and deploying to prod on merge to `main`. Internal tool — scope is "deployed reliably," not a public API platform. Full decisions in `.planning/DEPLOY-MILESTONE-NOTES.md`.

### Backend on Railway (DBKD)

- [ ] **DBKD-01**: The FastAPI backend runs as a Railway service built reproducibly (production Dockerfile or Procfile + nixpacks), serving on Railway's injected `$PORT`
- [ ] **DBKD-02**: A Railway Postgres instance with the `pgvector` extension enabled backs the app, with `DATABASE_URL` wired automatically into the backend service
- [ ] **DBKD-03**: A Railway persistent volume is mounted at `/media` so uploaded images/audio survive restarts and redeploys (not ephemeral)
- [ ] **DBKD-04**: Application secrets (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SECRET_KEY`) are supplied via Railway environment variables and never committed to the repo

### Frontend on Vercel (DFND)

- [ ] **DFND-01**: The Vite/React frontend builds (`npm run build`) and deploys on Vercel
- [ ] **DFND-02**: The deployed frontend reaches the backend via `VITE_API_URL` pointed at the Railway backend domain (no hardcoded localhost)

### Configuration parametrization (DCFG)

- [ ] **DCFG-01**: `ALLOWED_ORIGINS` is configurable via environment (config.py + docker-compose) instead of hardcoded localhost, and is set to the Vercel frontend domain in prod
- [ ] **DCFG-02**: The MCP server base URL (AuthSettings issuer / resource_server_url, currently `http://localhost:8001` in mcp_server/server.py) is parametrized via environment for the public deploy

### Production migrations (DMIG)

- [ ] **DMIG-01**: The idempotent `backend/migrations/delta/*.sql` migrations are applied automatically in production via `init_db` on boot, so a fresh or upgraded Railway Postgres reaches the current schema without manual steps

### CI/CD with GitHub Actions (DCICD)

- [ ] **DCICD-01**: A GitHub Actions workflow runs the backend test suite on every push, acting as a gate (the ~399 passing tests; 4 pre-existing flakes tolerated)
- [ ] **DCICD-02**: On merge to `main`, GitHub Actions deploys the backend to Railway and the frontend to Vercel automatically

### Public-deploy hardening (DSEC)

- [ ] **DSEC-01**: CORS is locked to the Vercel frontend domain in production via `ALLOWED_ORIGINS`, and the now-public `/mcp` endpoint's DNS-rebinding protection is reviewed and set appropriately for a public host

### Post-deploy verification (DVER)

- [ ] **DVER-01**: A post-deploy smoke test confirms production is live — the backend `/health` endpoint responds and the deployed frontend loads — before a deploy is considered successful

---

## v8.0 Requirements — MCP Server

**Defined:** 2026-06-11 · Expose the app's core capabilities as MCP tools so external MCP clients (Claude Code, Claude Desktop, Hermes) can drive the blank-page → production-breakdown flow conversationally. Internal tool. Remote Streamable HTTP transport, authenticated by the existing v5.0 `sa_<key>` API-key gateway (static bearer — no OAuth). MVP scope ~12 tools; no destructive (delete) tools exposed.

### Server Foundation (MCPF)

- [x] **MCPF-01**: A remote MCP server over Streamable HTTP is mounted in-process on the existing FastAPI app (e.g. at `/mcp`), reachable by remote MCP clients without a separate service or process
- [x] **MCPF-02**: The MCP server authenticates each request with the existing v5.0 API-key gateway — a `sa_<key>` static bearer in the `Authorization` header is verified (prefix + SHA-256 lookup, scopes, expiry), and an invalid/expired/missing key is rejected
- [x] **MCPF-03**: MCP tool calls reuse the existing per-key usage accounting and rate limiting — each authenticated call increments `request_count` / updates `last_used_at` and is subject to the per-key rate limit, exactly as REST calls are
- [x] **MCPF-04**: Every MCP tool is scoped to the authenticated key's user — a tool can only read or write projects/shows owned by that user (no cross-user access)
- [x] **MCPF-05**: Connection from Claude Code and Claude Desktop using a static `Authorization: Bearer sa_<key>` header is verified working (tool list + at least one tool call round-trips). Hermes static-header support is verified in the same spike; if Hermes does not support a static header, v8.0 still ships for the Claude clients and Hermes support is deferred to v8.1 (not a milestone blocker)

### Long-Running Calls (MCPJ)

- [x] **MCPJ-01**: Long-running tools (AI scene generation, breakdown extraction, AI shotlist generation — each ~60s+) return a job identifier immediately instead of blocking the call past the client timeout
- [x] **MCPJ-02**: A single generic `job_status` tool lets the agent poll a job by id and retrieve its status and, when finished, its result
- [x] **MCPJ-03**: Fast (non-AI) tools (reads, direct writes, CRUD) return their result synchronously in the same call (no job indirection)

### Screenwriting Tools (MCPW)

- [x] **MCPW-01**: An agent can read a project's screenplay via a tool (scoped by project/episode, optionally by scene), returning the scene text
- [x] **MCPW-02**: An agent can write a screenplay directly via a tool (the Phase 54 hand-written path — text split into scenes, persisted, breakdown/shotlist marked stale)
- [x] **MCPW-03**: An agent can generate a screenplay scene via a tool using the improved v6.0 generation path (continuity, character voice, craft), returning a job id (per MCPJ-01)

### Breakdown Tools (MCPB)

- [x] **MCPB-01**: An agent can trigger breakdown extraction for a project via a tool using the v7.0 extraction path, returning a job id (per MCPJ-01)
- [x] **MCPB-02**: An agent can read a project's breakdown elements via a tool, scoped/filterable by category, returning the elements and their scene appearances

### Shotlist Tools (MCPS)

- [x] **MCPS-01**: An agent can read a project's shotlist via a tool (shots grouped by scene)
- [x] **MCPS-02**: An agent can create a shot via a tool
- [x] **MCPS-03**: An agent can generate a shotlist via a tool using the AI shotlist path, returning a job id (per MCPJ-01)

### Project Management Tools (MCPP)

- [x] **MCPP-01**: An agent can list the authenticated user's projects via a tool (id, title, framework)
- [x] **MCPP-02**: An agent can create a project via a tool (title, framework), returning the new project
- [x] **MCPP-03**: An agent can read a single project's metadata via a tool (the target to write into / extract from)

### Tool Discovery & Errors (MCPD)

- [x] **MCPD-01**: Each tool advertises a clear name, description, and input schema so a generic MCP client (Claude Code / Desktop / Hermes) can introspect and call it without app-specific glue, including stating which tools are long-running (job-returning)
- [x] **MCPD-02**: App errors (not found, unauthorized, validation, generation failure) are mapped to clear MCP tool errors rather than raw stack traces or opaque 500s

## Phase 54 Requirements — Direct Screenplay Writing (standalone enhancement)

**Defined:** 2026-06-07 · User-requested: write a screenplay directly in the editor without first running the Script Writer Wizard. Internal tool.

### Direct Writing (WRITE)

- [x] **WRITE-01**: From an empty project, the user can write a screenplay directly in the Screenplay Editor (no Script Writer Wizard prerequisite) and save it
- [x] **WRITE-02**: A hand-written screenplay is split into scenes by scene headings (INT./EXT. sluglines); a document with no recognizable heading saves as a single "Untitled" scene (text never lost)
- [x] **WRITE-03**: Saving from an empty project creates the screenplay_editor data (no 404); save→reload→edit→save round-trips without scene duplication or loss
- [x] **WRITE-04**: A hand-written screenplay feeds the breakdown the same as a generated one — saving (re)creates ScreenplayContent rows (idempotently, no duplicate accumulation) and marks breakdown/shotlist stale

## v7.0 Requirements — Breakdown Fidelity

**Defined:** 2026-06-06 · Internal tool — focus is the FIDELITY of the production breakdown (the AI extraction of physical on-screen elements from the script). Symmetric with v6.0: v6.0 deepened the *script*, v7.0 deepens the *breakdown* extracted from it. No market/export/collab features.

**Premise:** v6.0 made generated scene text richer (continuity, voice, craft). The breakdown extraction in `backend/app/services/breakdown_service.py` should now read that actual per-scene screenplay text rather than one-line scene summaries, capture where/how each element appears, cover a broader element taxonomy, and refresh when a scene changes.

### Scene-Text Extraction (BFID)

- [x] **BFID-01**: Breakdown extraction runs against the full per-scene screenplay text (from `ScreenplayContent.content`), not one-line scene summaries — so elements present in action/dialogue are caught
- [x] **BFID-02**: Extraction is scene-scoped — each scene's elements are extracted from that scene's text, so an element can be attributed to the scene(s) it actually appears in
- [x] **BFID-03**: Existing "physically present on screen" extraction rules are preserved (no elements merely mentioned in dialogue/backstory, no abstract concepts) while operating on the fuller scene text

### Per-Appearance Context (APPR)

- [x] **APPR-01**: Each extracted element records the scene(s) it appears in (per-appearance context), not just a flat global element list
- [x] **APPR-02**: For each appearance, a short context note captures how/where the element appears (the action or moment), surfaced in the breakdown UI
- [x] **APPR-03**: The same element appearing across multiple scenes is consolidated into one element with multiple appearances (not duplicated)

### Expanded Categories (CATG)

- [x] **CATG-01**: The element taxonomy is broadened beyond the current set to cover additional production-relevant categories (e.g. wardrobe, makeup/hair, SFX/VFX, vehicles, animals, stunts) — exact final list settled during phase discussion
- [x] **CATG-02**: Existing breakdown categories and existing extracted data remain valid — new categories are additive, no data migration that drops prior elements
- [x] **CATG-03**: The breakdown UI displays and lets the user filter/group by the expanded categories

### Re-Extraction on Change (REEX)

- [x] **REEX-01**: When a scene's screenplay changes (regenerate-and-keep from v6.0, or a manual script edit), the breakdown is flagged stale via the existing staleness mechanism
- [x] **REEX-02**: Re-extraction refreshes the breakdown against the changed scene text without discarding user-added/edited breakdown elements (preserve manual edits where feasible — exact merge policy settled during phase discussion)

## v6.0 Requirements — Script Quality

**Defined:** 2026-06-05 · Internal tool — focus is craft quality of generated scripts, no market/export/collab features.

### Continuity (CONT)

- [x] **CONT-01**: When generating a scene's screenplay, the AI receives the full text of the immediately preceding generated scene(s) as context, not just one-line summaries
- [x] **CONT-02**: A running synopsis / "story so far" is maintained across scene generations so later scenes stay consistent with established events without exceeding context limits
- [x] **CONT-03**: Setups and payoffs (objects, facts, character states introduced earlier) remain consistent across the generated scene sequence — a generated scene does not contradict an earlier generated scene

### Character Voice (VOICE)

- [x] **VOICE-01**: Per-character voice/diction profiles are injected into the script-writing prompt (not only scene planning), so each character's dialogue reflects their defined voice
- [x] **VOICE-02**: When a character has no defined voice, the system derives or maintains a consistent voice for them across scenes rather than defaulting to a uniform style
- [x] **VOICE-03**: Generated dialogue is distinguishable between characters — two characters in the same scene do not sound interchangeable

### Screenwriting Craft (CRAFT)

- [x] **CRAFT-01**: The screenplay-generation prompt includes explicit craft guidance — subtext in dialogue, action-line economy, show-don't-tell, and page pacing / white space
- [x] **CRAFT-02**: Action lines in generated output are visual and economical (present tense, no internal/unfilmable description) per the craft guidance
- [x] **CRAFT-03**: Dialogue carries subtext rather than stating intentions on-the-nose, per the craft guidance

### Format Fidelity (FMT)

- [x] **FMT-01**: Screenplay output is produced in a way that preserves industry-standard formatting (scene headings, action, character cues, parentheticals, dialogue) without JSON-wrapping degrading it
- [x] **FMT-02**: The screenplay-generation path is evaluated native-output vs. json_mode-wrapped, and the better-formatting approach is adopted

### Quality Evaluation (EVAL)

- [x] **EVAL-01**: User can regenerate a scene's screenplay with the new (improved) generation path and compare it side-by-side against the prior output, to judge the quality improvement (UAT confirmed by user 2026-06-11)

## v4.2 Requirements

### Show Management

- [x] **SHOW-01**: User can create a new show with a title and description
- [x] **SHOW-02**: Home page displays Shows and standalone Films as separate sections
- [x] **SHOW-03**: User can open a show to view its series bible and episode list
- [x] **SHOW-04**: User can edit a show's title and description, and delete a show

### Series Bible

- [x] **BIBL-01**: Each show has four bible sections: Characters, World/Setting, Season Arc, Tone & Style
- [x] **BIBL-02**: User can write and edit each bible section as freeform text
- [x] **BIBL-03**: Each show has a target episode duration setting (10 min, 22 min, 44 min, 60 min, or custom)
- [x] **BIBL-04**: Bible content (all four sections) and episode duration are automatically injected into AI context for episode script generation, agent reviews, and breakdown extraction

### Episodes

- [x] **EPIS-01**: User can create a new episode inside a show with an episode number and title
- [x] **EPIS-02**: Each episode has the full screenplay → breakdown → shotlist → storyboard pipeline identical to standalone projects
- [x] **EPIS-03**: User can view, open, and delete episodes from the show page
- [x] **EPIS-04**: Existing standalone projects are unaffected — no data migration required
- [x] **EPIS-05**: Episode views include breadcrumb navigation back to the parent show (Show > Episode N: Title)

## v5.0 Requirements (Deferred)

### AI Shotlist Generation (deferred from v3.1)

- **AISG-08**: AI auto-generates shotlist on script save (YOLO mode)
- **AISG-09**: Shot duplication — user can duplicate an existing shot
- **AISG-10**: Batch shot operations (select multiple, bulk delete/move)

## Out of Scope

| Feature | Reason |
|---------|--------|
| PDF/print breakdown export | Different product domain — scheduling/budgeting tools handle this |
| Department assignments per shot | Production management feature, out of MVP scope |
| Real-time AI suggestions while typing | Too complex, staleness-flag pattern is sufficient |
| Movie Magic / Final Draft export | Industry format integration deferred indefinitely |
| Cross-episode shared breakdown elements | High complexity, per-episode breakdown is sufficient for v4.2 |
| Episode scheduling / production calendar | Different product domain |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCONT-01 | Phase 67 | Complete |
| ESUM-02 | Phase 67 | Complete |
| SCONT-02 | Phase 68 | Complete |
| SCONT-03 | Phase 68 | Complete |
| SCONT-04 | Phase 68 | Complete |
| ESUM-01 | Phase 69 | Complete |
| ESUM-03 | Phase 69 | Complete |
| SWZ-01 | Phase 70 | Complete |
| SWZ-02 | Phase 70 | Complete |
| SREV-01 | Phase 71 | Complete |
| DCFG-01 | Phase 62 | Pending |
| DCFG-02 | Phase 62 | Pending |
| DMIG-01 | Phase 62 | Pending |
| DBKD-01 | Phase 63 | Pending |
| DBKD-02 | Phase 63 | Pending |
| DBKD-03 | Phase 63 | Pending |
| DBKD-04 | Phase 63 | Pending |
| DFND-01 | Phase 64 | Pending |
| DFND-02 | Phase 64 | Pending |
| DCICD-01 | Phase 65 | Pending |
| DCICD-02 | Phase 65 | Pending |
| DSEC-01 | Phase 66 | Pending |
| DVER-01 | Phase 66 | Pending |
| MCPF-01 | Phase 55 | Complete |
| MCPF-02 | Phase 55 | Complete |
| MCPF-03 | Phase 55 | Complete |
| MCPF-04 | Phase 55 | Complete |
| MCPF-05 | Phase 55 | Complete |
| MCPJ-01 | Phase 56 | Complete |
| MCPJ-02 | Phase 56 | Complete |
| MCPJ-03 | Phase 56 | Complete |
| MCPP-01 | Phase 57 | Complete |
| MCPP-02 | Phase 57 | Complete |
| MCPP-03 | Phase 57 | Complete |
| MCPW-01 | Phase 58 | Complete |
| MCPW-02 | Phase 58 | Complete |
| MCPW-03 | Phase 58 | Complete |
| MCPB-01 | Phase 59 | Complete |
| MCPB-02 | Phase 59 | Complete |
| MCPS-01 | Phase 60 | Complete |
| MCPS-02 | Phase 60 | Complete |
| MCPS-03 | Phase 60 | Complete |
| MCPD-01 | Phase 61 | Complete |
| MCPD-02 | Phase 61 | Complete |
| CONT-01 | Phase 45 | Complete |
| CONT-02 | Phase 45 | Complete |
| CONT-03 | Phase 45 | Complete |
| FMT-01 | Phase 46 | Complete |
| FMT-02 | Phase 46 | Complete |
| VOICE-01 | Phase 47 | Complete |
| VOICE-02 | Phase 47 | Complete |
| VOICE-03 | Phase 47 | Complete |
| CRAFT-01 | Phase 48 | Complete |
| CRAFT-02 | Phase 48 | Complete |
| CRAFT-03 | Phase 48 | Complete |
| EVAL-01 | Phase 49 | Complete |
| BFID-01 | Phase 50 | Complete |
| BFID-02 | Phase 50 | Complete |
| BFID-03 | Phase 50 | Complete |
| APPR-01 | Phase 51 | Complete |
| APPR-02 | Phase 51 | Complete |
| APPR-03 | Phase 51 | Complete |
| CATG-01 | Phase 52 | Complete |
| CATG-02 | Phase 52 | Complete |
| CATG-03 | Phase 52 | Complete |
| REEX-01 | Phase 53 | Complete |
| REEX-02 | Phase 53 | Complete |
| WRITE-01 | Phase 54 | Complete |
| WRITE-02 | Phase 54 | Complete |
| WRITE-03 | Phase 54 | Complete |
| WRITE-04 | Phase 54 | Complete |
| SHOW-01 | Phase 36 | Complete |
| SHOW-02 | Phase 38 | Complete |
| SHOW-03 | Phase 38 | Complete |
| SHOW-04 | Phase 36 | Complete |
| BIBL-01 | Phase 37 | Complete |
| BIBL-02 | Phase 37 | Complete |
| BIBL-03 | Phase 37 | Complete |
| BIBL-04 | Phase 41 | Complete |
| EPIS-01 | Phase 39 | Complete |
| EPIS-02 | Phase 39 | Complete |
| EPIS-03 | Phase 40 | Complete |
| EPIS-04 | Phase 39 | Complete |
| EPIS-05 | Phase 42 | Complete |

**Coverage:**
- v10.0 requirements: 10 total (SCONT 4 / ESUM 3 / SWZ 2 / SREV 1) — Mapped to phases 67-71: 10/10 (67: SCONT-01, ESUM-02 / 68: SCONT-02,03,04 / 69: ESUM-01, ESUM-03 / 70: SWZ-01,02 / 71: SREV-01) — roadmap created 2026-06-17
- v9.0 requirements: 13 total (DBKD 4 / DFND 2 / DCFG 2 / DMIG 1 / DCICD 2 / DSEC 1 / DVER 1) — Mapped to phases 62-66: 13/13 — Shipped & live 2026-06-15
- v8.0 requirements: 21 total (MCPF 5 / MCPJ 3 / MCPW 3 / MCPB 2 / MCPS 3 / MCPP 3 / MCPD 2) — Mapped to phases 55-61: 21/21 — Pending (roadmap defined 2026-06-12)
- v7.0 requirements: 12 total (BFID/APPR/CATG/REEX) — Mapped to phases 50-53: 12/12 — Planned (execution gated on v6.0 close)
- v6.0 requirements: 12 total
- Mapped to phases: 12/12
- Unmapped: 0
- v4.2 requirements: 13 total — Mapped to phases: 13/13 (shipped)

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-06-17 after v10.0 roadmap creation*
