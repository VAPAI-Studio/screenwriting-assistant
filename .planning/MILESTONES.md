# Milestones

## v8.0 MCP Server (Shipped: 2026-06-12)

**Phases completed:** 7 phases (55-61), 14 commits
**Timeline:** 2026-06-11 → 2026-06-12

**Key accomplishments:**

1. Remote Streamable HTTP MCP server mounted in-process at `/mcp` on the existing FastAPI app — no separate service; authenticated by the existing v5.0 `sa_<key>` API-key gateway (static bearer, no OAuth) via a shared `authenticate_token` core that carries the per-key usage accounting; `/mcp` exempted from the BaseHTTPMiddleware stack; MCP session-manager lifespan composed into the app lifespan
2. 17 owner-scoped MCP tools across screenwriting, breakdown, shotlist, and project/show management — wrapping existing v6.0/v7.0/Phase-54 services without reimplementing them; no delete tools
3. In-memory job registry + generic `job_status` poll tool for long-running AI tools (scene generation, breakdown extraction, shotlist generation) — return a job-id immediately, run sessionless, poll to completion; 5 concurrent jobs run in parallel
4. Direct screenplay write tool (`screenplay_write`) with a server-side port of the Phase 54 INT./EXT. heading splitter; idempotent ScreenplayContent reconcile so breakdown extraction sees hand-written scenes
5. Clean tool discovery (all 17 tools introspect with descriptions + schemas) and error mapping (app errors → MCP tool errors, not opaque 500s)
6. **Verified end-to-end live from Claude Code** — connected over real HTTP with a static `sa_<key>` bearer, listed 17 tools, `whoami` returned the key owner

**Tech debt / flagged for review:**
- Legacy `framework` Postgres enum broken app-wide (uppercase ORM names vs lowercase PG labels) — worked around in MCP; worth a schema fix
- Dependency pinning (starlette/sse-starlette) to avoid a FastAPI bump — confirm with a clean `docker compose build`
- In-memory job registry is per-worker (single uvicorn worker assumed)
- `/mcp` needs a backend restart to activate if the process started before the v8.0 code
- Hermes static-header support unverified (defers to v8.1 if unsupported)

> Full detail in `.planning/milestones/v8.0-ROADMAP.md`; decision log in `.planning/v8.0-AUTONOMOUS-DECISIONS.md`.

---

## v6.0 Script Quality (Shipped: 2026-06-11)

**Phases completed:** 5 phases (45-49), 6 plans
**Timeline:** 2026-06-06 (build) → 2026-06-11 (UAT + close)
**Files changed:** 50 files, ~7,500 insertions

**Key accomplishments:**

1. Continuity-aware generation — each scene's prompt receives the verbatim text of the immediately-preceding scene plus a maintained running synopsis ("story so far"), re-summarized under a word cap; synopsis advances only on success so a failed scene cannot poison continuity (no migration — persisted into existing PhaseData.content JSON)
2. Format fidelity — scene-writing switched to native output (json_mode=False) outright; JSON string-encoding was degrading screenplay formatting. Title parsed off a TITLE: line with scene-summary fallback. Works for both OpenAI and Anthropic
3. Character voice injection — per-character voice/diction profiles routed into the script-writing prompt (not only scene planning); conditional block collapses to '' when absent → byte-identical empty-vs-absent contract; under-specified voices derived and carried via the continuity block
4. Screenwriting craft guidance — an unconditional `## Screenwriting Craft` prompt block (subtext, action-line economy, show-don't-tell, white-space pacing) whose anchors avoid colliding with continuity/voice markers
5. Side-by-side quality compare — `_generate_one_scene` is the single shared per-scene prompt source (batch loop + single-scene regenerate both delegate, can never diverge); regenerate-scene returns a preview (no write), keep-scene-version persists + marks breakdown/shotlist stale. Frontend SceneCompareModal: two-pane current-vs-regenerated with keep-current (no-op) / keep-new (persist). Backend verified end-to-end + runtime UAT confirmed by user 2026-06-11

**Tech debt carried forward:**

- ScreenplayContent accumulates duplicate rows per episode_index (batch-generate appends, never deletes — pre-dates v6.0); robust fix needs a schema change, deferred per D-49-03
- Pre-existing test-suite isolation flakiness (test_yolo_integration / test_session_isolation — not a v6.0 regression)
- Frontend `npm run lint` references a non-existent ESLint config; tsc/build is the binding type gate

> Note: v6.0 (Script Quality) and v7.0 (Breakdown Fidelity) were developed in close sequence; v6.0 deepened the *script*, v7.0 the *breakdown* extracted from it. See ROADMAP.md and .planning/milestones/ for full detail.

---

## v5.0 API Key Management & Gateway (Shipped: 2026-04-01)

**Phases completed:** 2 phases (43-44), 4 plans

**Key accomplishments:**

1. API key management — users create named API keys with optional scopes and expiry dates; secure hashing and one-time secret reveal
2. API gateway & docs — unified auth middleware accepting API keys, enhanced API documentation
3. Per-key usage tracking — atomic SQL request-count increment (race-safe), per-key in-memory rate limiter (defaults to 1000 req/hour), last-used timestamps
4. Usage stats UI — request count and last-used display on the API keys settings page with 30-second auto-refresh polling

> Note: This index skips v3.1–v4.2 (file was not maintained between v3.0 and v5.0). See ROADMAP.md for the complete shipped-milestone list.

---

## v3.0 Shotlist & Production Breakdown (Shipped: 2026-03-20)

**Phases completed:** 9 phases, 14 plans, 0 tasks

**Key accomplishments:**

- (none recorded)

---

## v2.0 Script Breakdown (Shipped: 2026-03-18)

**Phases completed:** 8 phases (9-16), 16 plans
**Timeline:** 2026-03-01 → 2026-03-18 (17 days)
**Files changed:** 91 files, 16,745 insertions

**Key accomplishments:**

1. AI extraction service — GPT-4/Claude structured output extraction identifies 5 production element categories (characters, locations, props, wardrobe, vehicles) from screenplay content with deduplication and scene link reconciliation
2. Full CRUD REST API — 7 breakdown endpoints with 22 integration tests; scene link management; extraction trigger; summary with staleness and category counts
3. Breakdown page — React frontend with category tabs, master lists, inline editing, scene chips with deep-link navigation, Add Element dialog, empty state CTA
4. Staleness hooks — all script save/generate paths set `breakdown_stale=True`; re-extraction clears it atomically; user_modified elements preserved across re-extractions
5. Reverse sync — user-initiated "Add to Characters" creates ListItem in story.characters phase; idempotent across calls
6. Migration upgrade path — `delta/001_breakdown_tables.sql` lets existing Docker deployments apply v2.0 schema on restart without volume wipe

**Tech debt carried forward:**

- Latent `selectinload` result discarded in create/update write endpoints (masked on new elements)
- React Query `LIST_ITEMS` cache not invalidated after reverse sync (5-min lag)
- 14/16 phases have partial Nyquist compliance; Phase 11 missing VALIDATION.md

---

## v1.0 Agent Orchestration Pipeline (Shipped: 2026-03-12)

**Phases completed:** 8 phases (1-8), 16 plans

**Key accomplishments:**

1. Multi-agent pipeline system — AI maps user-created agents to generation steps; agents review wizard output in parallel via asyncio.gather
2. Agent review middleware — parallel fan-out, AI merge call, zero-impact bypass when no agents mapped; injected into wizards.py generation path
3. Frontend pipeline tree — collapsible AgentPipelineTree.tsx showing per-step agent assignments with per-agent toggles
4. YOLO auto-generation — agent reviews fire through same middleware in YOLO mode with configurable token budgets

---
