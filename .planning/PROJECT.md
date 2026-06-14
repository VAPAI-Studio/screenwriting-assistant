# Screenwriting Assistant

## What This Is

A full-stack screenwriting assistant that helps users create screenplays using story frameworks (Three-Act, Save the Cat, Hero's Journey) with AI-powered generation, multi-agent review, and production breakdown. The app has two distinct modes: **Screenwriting** (AI-assisted script writing with agent orchestration) and **Script Breakdown** (shotlist creation, media asset management, and AI chat for production planning).

## Core Value

From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## Requirements

### Validated

- ✓ Template-based project system with phases and subsections — v1.0
- ✓ Step-by-step generation pipeline (phase by phase) via `template_ai_service.py` — v1.0
- ✓ AI provider abstraction supporting OpenAI and Anthropic — v1.0
- ✓ Multi-agent system with user-created agents, pipeline mapping, and review middleware — v1.0
- ✓ RAG-based knowledge retrieval for agent context — v1.0
- ✓ Frontend pipeline tree with per-agent toggles — v1.0
- ✓ YOLO auto-generation with agent reviews and token budgets — v1.0
- ✓ Book processing with concept extraction and embeddings — v1.0
- ✓ AI analyzes script + project data to extract production elements — v2.0
- ✓ Dedicated breakdown page with master lists per category (Characters, Locations, Props, Wardrobe, Vehicles) — v2.0
- ✓ Each element links to the scenes where it appears — v2.0
- ✓ User can refine AI-generated breakdown (edit, add, remove elements) — v2.0
- ✓ Bidirectional sync between breakdown and script on save/generate — v2.0
- ✓ Reverse sync: user-initiated action pushes breakdown element back to project data — v2.0
- ✓ Two-mode UI: Screenwriting / Script Breakdown with distinct visual identity (amber vs steel-blue) — v3.0
- ✓ Interactive shotlist: highlight script text → Add Shot → freeform field entry — v3.0
- ✓ Shotlist data model and CRUD API with scene grouping, inline editing, reorder, delete — v3.0
- ✓ Media uploads backend: image/audio upload, WebP thumbnail generation, StaticFiles serving — v3.0
- ✓ Assets panel with breakdown elements grouped by category, media thumbnails, audio playback — v3.0
- ✓ AI chat in Breakdown mode with shotlist + element context awareness, shot create/modify via conversation — v3.0
- ✓ Bidirectional sync between screenplay and shotlist (staleness banner + acknowledge) — v3.0

### Active (v4.2 — complete)

- ✓ Show entity with create/edit/delete (SHOW-01, SHOW-02, SHOW-03, SHOW-04) — Validated in Phase 36/38: show-data-model-api + show-management-ui
- ✓ Series bible: Characters, World/Setting, Season Arc, Tone & Style (BIBL-01, BIBL-02) — Validated in Phase 37: series-bible-data-api
- ✓ Target episode duration setting per show (BIBL-03) — Validated in Phase 37: series-bible-data-api
- ✓ Bible + duration injected into all AI generation for episodes (BIBL-04) — Validated in Phase 41: bible-ai-injection
- ✓ Episode creation and management inside a show (EPIS-01, EPIS-02, EPIS-03, EPIS-04) — Validated in Phases 39/40: episodes + episode-management-ui
- ✓ Breadcrumb navigation from episode back to show (EPIS-05) — Validated in Phase 42: breadcrumb-navigation

### Deferred (v5.0+)

- [ ] Shot duplication and batch operations (AISG-09, AISG-10)
- [ ] YOLO auto-generation of shotlist on script save (AISG-08)

### Out of Scope

- Scheduling/calendar integration — different product domain
- Budget line items and cost tracking — different product domain
- Department assignments — deferred
- Export to industry formats (PDF breakdown sheets, Movie Magic) — deferred
- Real-time sync (changes propagate on save/generate, not as user types)
- Full 23-category Movie Magic parity — 5 core categories sufficient
- Offline mode — real-time connectivity assumed

## Context

Shipped v1.0 (agent orchestration, 2026-03-12), v2.0 (script breakdown, 2026-03-18), v3.0 (shotlist & production breakdown, 2026-03-20), v3.1 complete (2026-03-21) — AI shotlist generation + UX improvements. v4.2 complete (2026-03-24) — TV Show Mode.

**v4.2 additions:** Show entity with CRUD, series bible editor (characters, world, arc, tone), episode management per show, bible context injected into all AI generation for episodes, breadcrumb navigation from episode back to show.

**Current codebase:**
- Tech stack: FastAPI, PostgreSQL, SQLAlchemy, React, React Query, Tailwind, Radix UI, OpenAI/Anthropic
- 35 total phases shipped (phases 36–42 = v4.2 TV Show Mode)
- All v4.2 milestone requirements satisfied

Last updated: 2026-03-24

**Key files added in v3.0:**
- `backend/app/api/endpoints/shots.py` — Shot CRUD + reorder + staleness status/acknowledge
- `backend/app/api/endpoints/media.py` — File upload, thumbnail generation, list, delete
- `backend/app/api/endpoints/breakdown_chat.py` — Streaming AI chat with context injection + shot action extraction
- `backend/app/services/media_service.py` — Pillow thumbnail generation (300x300 WebP)
- `backend/migrations/delta/002_shotlist_tables.sql` — Idempotent shots/asset_media/shotlist_stale migration
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` — 3-panel root layout with mode class lifecycle
- `frontend/src/components/Breakdown/ShotlistPanel.tsx` — Scene-grouped shotlist with React Query mutations
- `frontend/src/components/Breakdown/ScriptReadView.tsx` — Read-only screenplay with text selection → shot creation
- `frontend/src/components/Breakdown/AssetsPanel.tsx` — Breakdown elements with media display + extract button
- `frontend/src/components/Breakdown/BreakdownChat.tsx` — AI chat with shot proposal confirmation flow
- `frontend/src/components/Breakdown/ShotlistStalenessBar.tsx` — Amber banner + dismiss

**Known tech debt:**
- Latent `selectinload` result discarded in breakdown create/update write endpoints (pre-v3.0)
- React Query `LIST_ITEMS` cache not invalidated after reverse sync — 5-min lag (pre-v3.0)
- `reorder_list_items` does not call `_mark_shotlist_stale` — scene reorder doesn't flag shotlist stale
- 3 pre-existing TypeScript build errors in unrelated files (IndividualEditorView, RepeatableCardsView, SidebarChat)

## Constraints

- **AI Provider**: Must work with both OpenAI and Anthropic via existing `ai_provider.py`
- **Existing Templates**: Must integrate with existing template phase system without breaking current workflows
- **Data Model**: All new tables use `delta/` idempotent migrations for Docker zero-downtime upgrades
- **Sync Pattern**: Staleness-flag pattern (save/generate triggers stale flag, user acknowledges) — not real-time

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agent reviews run in parallel, not sequential | Reduces latency when multiple agents map to same step | ✓ Good |
| AI merges feedback rather than chaining | Avoids compounding bias from sequential review | ✓ Good |
| Pipeline re-composes on agent CRUD, not at generation time | Pre-computed mapping avoids generation-time overhead | ✓ Good |
| Master list + scene links (not per-scene breakdown) | Gives production overview while preserving scene-level detail | ✓ Good |
| Bidirectional sync on save/generate (not real-time) | Simpler, avoids conflict resolution complexity | ✓ Good |
| AI generates, user refines | Reduces manual work while keeping user in control | ✓ Good |
| Breakdown is NOT a template phase | Cross-cutting derived view with dedicated tables, API, and page | ✓ Good |
| VARCHAR(50) category column (not PG ENUM) | Extensible without future migration | ✓ Good |
| Reverse sync is user-initiated only | Avoids circular sync loops; preserves screenplay as source of truth | ✓ Good |
| JSONB `fields` column for shot properties | Freeform schema without per-field columns; all 13 fields optional | ✓ Good |
| Two-mode UI via separate route + CSS class (not conditional render) | Clean separation; breakdown palette applied via `.breakdown-mode` on `<html>` | ✓ Good |
| Shot CRUD stores `script_text` as reference, not displayed column | Links shot to source material without cluttering grid UI | ✓ Good |
| `scene_item_id SET NULL` on scene delete | Shot survives scene deletion; can be reassigned | ✓ Good |
| StaticFiles mount at `/media` for uploaded files | Simple serving without additional infrastructure | ✓ Good |
| Two-phase AI call for breakdown chat (stream then extract action) | Streaming UX preserved; action extraction done post-stream | ✓ Good |

---

## Current Milestone: v9.0 Deploy (Railway + Vercel + CI/CD)

**Goal:** Get the app running in production — backend + Postgres on Railway, frontend on Vercel, with GitHub Actions running tests on push and deploying to prod on merge to `main`.

**Target features:**
- Production backend on Railway: FastAPI service (Dockerfile or Procfile+nixpacks), Railway Postgres with pgvector enabled, persistent volume mounted at `/media`, secrets loaded via Railway env (never in repo)
- Frontend on Vercel: `npm run build`, `VITE_API_URL` pointed at the Railway backend domain
- Parametrize localhost hardcodes → env vars: `ALLOWED_ORIGINS` (config.py + docker-compose), `VITE_API_URL`, and the MCP server base URL (`http://localhost:8001` in mcp_server/server.py — AuthSettings issuer/resource_server_url)
- Database migrations applied in prod: idempotent `backend/migrations/delta/*.sql` (or `init_db` on boot)
- GitHub Actions CI/CD: run tests on every push; deploy backend (Railway) + frontend (Vercel) on merge to `main`
- CORS/MCP hardening for public deploy: `ALLOWED_ORIGINS` set to the Vercel domain; review MCP DNS-rebinding protection now that `/mcp` is publicly reachable

**Key context:** User has Railway + Vercel (VAPAI-Studio) accounts and performs login/authorization steps when prompted. Secrets (OPENAI_API_KEY, ANTHROPIC_API_KEY, generated SECRET_KEY) loaded by the user directly into Railway. DB is a SINGLE Railway Postgres holding all data (projects, scripts, users, api_keys + pgvector RAG embeddings) — not a separate agent DB. `Procfile` and `runtime.txt` already exist; no `.github/workflows/` yet. ~399 tests pass (4 pre-existing flakes) — usable as CI gate. config.py already validates SECRET_KEY ≠ default in prod. Full decisions captured in `.planning/DEPLOY-MILESTONE-NOTES.md`. This is an internal tool — scope is "get it deployed reliably," not a public API platform.

**Out of scope (carried as known debt, does not block deploy):** legacy `framework` enum bug (pre-existing, broken in Postgres app-wide); confirming dependency pins with a clean `docker compose build`; Hermes static-header verification.

<details>
<summary>Previous: Current State (v8.0 shipped) — MCP Server</summary>

**Shipped:** v6.0 Script Quality (2026-06-11), v7.0 Breakdown Fidelity (2026-06-08), the standalone Phase 54 (direct screenplay writing), and **v8.0 MCP Server (2026-06-12)**. The AI script-writing path carries continuity, native formatting, per-character voice, and craft guidance with a side-by-side compare; breakdown extraction reads full per-scene text with per-appearance context across 10 categories. All of it is now exposed as **17 MCP tools** over a remote Streamable HTTP server mounted in-process at `/mcp`, authenticated by the v5.0 `sa_<key>` gateway — verified end-to-end live from Claude Code.

</details>

<details>
<summary>Previous: Current Milestone v8.0 — MCP Server (now shipped)</summary>

**Goal:** Expose the app's core capabilities (screenwriting, breakdown, shotlist, project/show management) as MCP tools so external MCP clients can drive the whole blank-page → production-breakdown flow conversationally, authenticated via the existing v5.0 API-key gateway.

**Consumers:** Claude Desktop / Claude Code (primary) and Hermes (secondary). Remote MCP clients → HTTP-based, not local stdio.

**Transport:** Remote Streamable HTTP MCP server, authed with v5.0 API keys (Bearer `sa_<key>`) — reuses the v5.0 auth + per-key rate limiting, supports multiple network clients.

</details>

**Target features:**
- MCP server scaffold over Streamable HTTP, mounted alongside the FastAPI app, authed via the v5.0 API-key gateway (per-key identity + rate limiting carried through)
- Screenwriting tools: read a project's screenplay, generate/regenerate scenes via the improved v6.0 path, write a screenplay directly (Phase 54 path)
- Breakdown tools: trigger extraction, read elements by category, read per-scene appearances + context (the v7.0 fidelity output)
- Shotlist tools: read/create/edit shots, AI-generate a shotlist
- Project/show management tools: create/list projects, create shows/episodes, read the series bible
- Tool discovery + schemas that a generic MCP client (Claude Desktop/Code, Hermes) can introspect and call without app-specific glue

**Scope note:** Internal tool. The MCP server is an internal integration surface, not a public API platform. Out of scope — industry export (.fdx/PDF), collaboration/multiplayer, public/marketplace MCP distribution, scheduling. The previz platform connection (vapai-studio) remains out of scope for this milestone; Hermes is the named secondary consumer. Roadmap order: ~~v6.0 Script Quality~~ → ~~v7.0 Breakdown Fidelity~~ → **v8.0 MCP Server**.

<details>
<summary>Current State (as of v8.0 start — v6.0 + v7.0 + Phase 54 shipped)</summary>

**Shipped:** v6.0 Script Quality (2026-06-11) and v7.0 Breakdown Fidelity (2026-06-08), plus the standalone Phase 54 (direct screenplay writing). The AI script-writing path now carries continuity (prior-scene text + running synopsis), native screenplay formatting, per-character voice profiles, and explicit craft guidance — with a side-by-side regenerate-and-compare flow for judging quality. The breakdown extraction reads full per-scene screenplay text, records per-appearance context, covers 10 element categories, and re-extracts on change while preserving user edits. Users can also write a screenplay by hand from an empty project and feed it into the breakdown.

</details>

<details>
<summary>Previous: Current Milestone v6.0 — Script Quality (now shipped)</summary>

**Goal:** Make the AI genuinely good at writing screenplays — improve the craft quality of generated scenes and scripts. This is an internal tool; the only thing that matters is output quality, not new feature surface.

**Target features:**
- Continuity-aware generation: each scene's script call sees the actual text (or running synopsis) of prior scenes, not just one-line summaries — so tone, voice, and setup/payoff hold across scenes
- Per-character voice profiles injected into the script-writing prompt so characters have distinct diction (not just into scene planning)
- Screenwriting craft guidance in prompts: subtext in dialogue, action-line economy, show-don't-tell, page pacing / white space
- Format fidelity: evaluate native screenplay output vs. the current json_mode-wrapped `{title, content}` to ensure JSON wrapping isn't degrading formatting

</details>

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

*Last updated: 2026-06-05 after milestone v6.0 started*
