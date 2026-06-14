# Project Research Summary

**Project:** Screenwriting Assistant — v8.0 MCP Server
**Domain:** Remote Streamable HTTP MCP server mounted inside the existing FastAPI app, authenticated by the v5.0 `sa_<key>` API-key gateway
**Researched:** 2026-06-11
**Confidence:** HIGH

## Executive Summary

v8.0 exposes the app's already-built screenwriting and production-breakdown capabilities (v6.0 generation, v7.0 breakdown extraction, shotlist, Phase 54 direct write, shows/episodes/bible) as agent-callable MCP tools over Streamable HTTP. This is **not greenfield** — every underlying capability exists. The work is a thin, curated MCP delivery surface bolted onto the existing FastAPI monolith, plus exactly one genuinely new component (a job registry + `job_status` poll tool). The consumers are Claude Code, Claude Desktop, and Hermes — all internal, no marketplace concerns.

The recommended approach is decisive: **mount the MCP ASGI sub-app in-process** (`app.mount("/mcp", ...)`) rather than running a separate service, so it reuses the existing DB pool, config, and (most of) the middleware stack for free; **authenticate with the existing static `Authorization: Bearer sa_<key>` header** rather than building OAuth — research confirms all three in-scope clients accept static headers (only the out-of-scope claude.ai *web connector* is OAuth-only); and **expose ~12 curated tools, all-tools-no-resources**, grouped screenwriting / breakdown / shotlist / management, deliberately omitting destructive and fat-workflow tools. The single biggest design constraint is that generation/extraction tools run 60s+, which exceeds common client timeouts — handled with a portable **job-id + poll** pattern over ordinary tool calls (no dependency on immature client `tasks`/progress support).

The risks are concentrated and front-loaded, which is why **Phase 1 carries almost all the integration danger**. Four failure modes all bite at scaffold time: the static-bearer-vs-OAuth client compatibility question (a go/no-go gate), the mounted sub-app silently bypassing FastAPI's `Depends`-based auth and `request_count` increment, the existing `BaseHTTPMiddleware` rate-limiter/logger breaking streaming responses, and the MCP session-manager lifespan not being composed into the parent app (`RuntimeError: Task group is not initialized`). Get Phase 1 right and the remaining tool-group phases are low-risk, parallelizable adapters over existing services.

## Key Findings

### Recommended Stack

The stack adds essentially **one runtime dependency** to a FastAPI/Python 3.11 app and reuses everything else (FastAPI, Starlette, Uvicorn, Pydantic v2, the v5.0 gateway). Transport is **Streamable HTTP** (SSE is deprecated — do not expose a `/sse` endpoint). Auth is static-bearer via a pluggable token-verification hook — **OAuth is optional, not required by the SDK**, so no Authorization Server, no `authlib`, no IdP. Tools are hand-written, curated adapters delegating to existing services — explicitly **not** `fastapi-mcp` auto-route-exposure, which would dump un-curated CRUD and muddy the auth boundary.

**Core technologies:**
- **MCP SDK / `FastMCP`** (pin `<2.0`; v2 is alpha) — MCP server primitives, tool JSON-schema generation, Streamable HTTP transport, header access, and the token-verification hook. *(See library-choice gap below — STACK.md recommends the official `mcp>=1.27.2` SDK; ARCHITECTURE.md recommends the standalone `fastmcp` for better inbound-header/mounting ergonomics. Pin the exact package + import paths at scaffold time.)*
- **FastAPI / Starlette / Uvicorn (existing)** — host app; the MCP ASGI sub-app mounts cleanly because FastAPI *is* Starlette. No new web framework.
- **v5.0 API-key gateway (existing)** — token verification, per-key identity, rate limiting, `request_count` accounting. Reuse via a shared `authenticate_token(token, db)` core, do not reinvent.
- **Pydantic v2 (existing)** — reuse existing schemas as tool argument/return models so MCP introspection matches the REST contract.

### Expected Features

A ~12-tool MVP surface lets an external agent run the full blank-page → breakdown flow end-to-end and orient itself. **Everything is a tool; MCP Resources and Prompts are deferred** (client support is immature/inconsistent, and the flow is model-controlled dynamic reads, which are tools by definition). Standardize one **result envelope** — `{ summary, data, stale?, job_id? }` — so the model always gets a narratable summary plus structured data and any staleness signal. Normalize `project_id` and `episode_id` to a single "target id" so screenwriting/breakdown/shotlist tools work uniformly without doubling the toolset.

**Must have (table stakes, v8.0):**
- `job_status` (+ job registry) — without it, no long-running tool returns usable results. Infrastructure-critical, gates all three generators.
- `project_list` / `project_create` / `project_get` — discover and create a target to write into.
- `screenplay_read` — orient before writing/extracting (scoped by project/episode/scene).
- `screenplay_write` — direct hand-written path (fast, deterministic, easiest to validate).
- `screenplay_generate_scene` — the AI-writes-the-script core value (long-running → job-id).
- `breakdown_extract` — extract-everything-to-produce-it core value (long-running → job-id).
- `breakdown_read` (category-scoped) — read the extraction result.
- `shotlist_read` / `shot_create` / `shotlist_generate` — complete the production-breakdown arc.

**Should have (differentiators, v8.x after validation):**
- `screenplay_regenerate_scene` — iterative quality refinement.
- `breakdown_read_scene` — scene-scoped "what's in scene 4?" questions.
- `shot_update` — refine generated shots.
- `show_create` / `episode_create` / `show_read_bible` / `show_list` / `episode_list` — episodic/TV-show flows.

**Defer / anti-features (explicitly DO NOT expose):**
- **No delete tools** (`*_delete`) — destructive + irreversible via an autonomous agent; cascade deletes make one bad call catastrophic. Deletion stays a human web-UI action.
- **No fat `do_screenwriting_workflow` tool** — hides steps the agent must branch on; makes the long call un-pollable.
- **No synchronous/blocking generate/extract** — times out; use job-id + poll.
- **No raw DB tools, no `mark_stale`/`acknowledge_stale` tools, no media/storyboard/RAG/reverse-sync tools, no per-generator status tool** (one generic `job_status` only).
- MCP Resources, Prompts, native `tasks` primitive — revisit when client support matures or token bloat is observed.

### Architecture Approach

Mount the MCP sub-app **inside** the existing FastAPI app, reusing the shared service layer (wrap, never reimplement) and the same DB/auth/config. A new `mcp/` module sits as a sibling of `api/` (`server.py`, `auth.py`, `session.py`, `errors.py`, `tools/{projects,screenwriting,breakdown,shotlist}.py`). The only structurally significant edits to existing code are in `main.py` (build/mount the sub-app, compose lifespan, migrate `init_db` off `on_event`) and `api/dependencies.py` (factor `authenticate_token(token, db)` out of `get_current_user` and move the `request_count` increment into it so MCP traffic is both auth'd and counted).

**Major components:**
1. **`mcp_app` (FastMCP ASGI)** — speaks MCP/JSON-RPC over Streamable HTTP, advertises tool schemas, dispatches to handlers; mounted at `/mcp`.
2. **MCP tool handlers (`mcp/tools/*`)** — thin adapters: parse args → authenticate → open DB session → call existing service → shape result. Never reimplement service logic.
3. **`authenticate_token(token, db)`** — auth core refactored out of `get_current_user`, shared by REST and MCP (single source of truth, carries the `request_count` increment).
4. **`mcp_session()` context manager** — per-tool-call DB session (not `Depends`); open late, close early, never held across the AI `await`.
5. **Job registry + `job_status`** — the one genuinely new build; gates all long-running tools.

### Critical Pitfalls

1. **Static-bearer vs OAuth client mismatch** — the milestone's named blocker. Claude Code (`claude mcp add --transport http ... --header "Authorization: Bearer sa_<key>"`) and Claude Desktop (manual remote-server config) accept static headers; claude.ai **web connector is OAuth-only and out of scope** (issue #112, closed "not planned"); Hermes is unverified. *Avoid:* run a 30-min hello-world spike connecting all three actual clients **before any tool work** — this is the Phase-1 go/no-go gate. Document "add via CLI/Desktop config, not the web connector." Fallback if a future client forces OAuth: thin OAuth shim mapping to `sa_` keys, or `mcp-remote` proxy — do not build now.
2. **Auth + `request_count` silently bypassed on the mounted sub-app** — mounted ASGI apps don't run FastAPI's `Depends` chain, so `get_current_user` (validation + the atomic usage increment) never fires; the endpoint is unauthed or stops counting usage. *Avoid:* authenticate inside the MCP server's own hook using the shared `authenticate_token`, perform the same atomic increment, and scope every query by the key's `user_id`.
3. **`BaseHTTPMiddleware` rate-limiter + logger break streaming** — those middlewares buffer responses with no backpressure, which leaks memory / stalls / truncates SSE streams. *Avoid:* **exempt `/mcp` from the `BaseHTTPMiddleware` stack** (short-circuit early, or apply MCP-path middleware via the sub-app); use pure-ASGI middleware for anything MCP-path needs. Tie this to the auth exemption so there's no double rate-limit/double-count per call.
4. **Lifespan not composed → "Task group is not initialized"** — the MCP session manager starts in the MCP app's lifespan, which never runs when mounted, 500-ing every call. *Avoid:* compose the existing app lifespan and the MCP session-manager lifespan into one combined async context manager.
5. **Long-running calls (60s+) vs client timeouts + sync-DB pool exhaustion** — generation tools exceed client wall-clock timeouts (progress notifications do **not** extend Claude Code's hard limit; there's also a 60s first-byte budget), and sync `SessionLocal` held across a 60s async AI call blocks the event loop and exhausts the pool, taking the web app down too. *Avoid:* job-id + poll for the slow tools; emit first byte fast; `to_thread` all sync DB work; open session late / close early (load → run AI sessionless → persist); raise pool size + `pool_pre_ping`. (Plus: sanitize outbound script/breakdown text to blunt indirect prompt injection.)

## Implications for Roadmap

Based on combined research, the build order is **foundation-first, then parallel tool groups, then integration polish**. The dependency is hard: scaffold + auth + lifespan + middleware-exemption must land before any tool group, and they carry nearly all the integration risk. Tool groups are mutually independent adapters and can parallelize or batch fast.

### Phase 1: MCP Scaffold + Auth + Lifespan + Middleware Exemption (HIGHEST STAKES)
**Rationale:** Four critical pitfalls (1–4) all bite here, and the static-bearer client-compatibility spike is a **go/no-go gate** for the whole milestone — discovering an auth/transport blocker after building 12 tools is the worst outcome. This is the cheapest insurance in the roadmap.
**Delivers:** `/mcp` mounted in-process; composed lifespan (MCP session manager + `init_db`); `/mcp` exempted from `BaseHTTPMiddleware`; `authenticate_token` refactored out of `get_current_user` with the `request_count` increment moved into it; an authenticated `whoami`/`ping` tool that round-trips a tool-list + one call from **Claude Code, Claude Desktop, and Hermes** with the static header.
**Addresses:** the auth + transport foundation every tool depends on.
**Avoids:** Pitfalls 1 (OAuth mismatch — spike gate), 2 (auth/`request_count` bypass), 3 (`BaseHTTPMiddleware` streaming break), 4 (lifespan), 7 (SSE-vs-Streamable confusion).

### Phase 2: Job Registry + `job_status` + First AI-Backed Tool
**Rationale:** The job registry is the one genuinely new component and it gates all three long-running generators — build and prove it against the first real AI tool. The first 60s+ call is also where the sync-DB/pool and client-timeout pitfalls first bite, so set the session pattern and pool sizing here and reuse it everywhere after.
**Delivers:** in-memory/TTL'd job registry; generic `job_status(job_id)` poll tool; `screenplay_generate_scene` (or `breakdown_extract`) wired as start-fast-return-job-id with first-byte-fast + progress; the canonical `to_thread` + late-open/early-close session pattern + pool tuning.
**Uses:** the MCP SDK transport + the existing v6.0/v7.0 service paths.
**Implements:** the job registry component and the long-running result envelope (`{ summary, data, job_id }`).
**Avoids:** Pitfalls 5 (sync DB / pool exhaustion), 6 (client timeout), 9 (output sanitization on first content-returning tool).

### Phase 3: Management Tools (project / show / episode / bible)
**Rationale:** Fast, deterministic, no long-running calls — the entry point for any agent session (`project_list` is where a session starts). Parallelizable adapter work once the foundation exists.
**Delivers:** `project_list` / `project_create` / `project_get` (table stakes), plus `show_create` / `episode_create` / `show_read_bible` / `show_list` / `episode_list` (differentiators); target-id normalization (`project_id` ≡ `episode_id`).

### Phase 4: Screenwriting Tools
**Rationale:** Reuses the Phase-2 job pattern for generation; pairs the fast direct-write path with the AI path. Parallelizable.
**Delivers:** `screenplay_read`, `screenplay_write` (Phase 54 path), `screenplay_generate_scene` / `screenplay_regenerate_scene` (v6.0 path, job-id). Keep hand-write and AI-write as two distinct tools, not a `mode:` param.

### Phase 5: Breakdown Tools
**Rationale:** Depends only on the foundation + job pattern; reads must be category-scoped to keep results small. Parallelizable.
**Delivers:** `breakdown_extract` (v7.0, job-id, idempotent re-extract), `breakdown_read` (category-scoped), `breakdown_read_scene` (per-appearance context).

### Phase 6: Shotlist Tools
**Rationale:** Same adapter pattern; completes the production-breakdown arc. Parallelizable.
**Delivers:** `shotlist_read`, `shot_create`, `shotlist_generate` (job-id), `shot_update`.

### Phase 7: Discovery Polish + Error Mapping + Client UAT
**Rationale:** Descriptions ARE the API for generic clients — finalize names/descriptions/schemas (state preconditions and long-running behavior), map app exceptions to MCP errors, and run the "Looks Done But Isn't" checklist end-to-end. Integration, so it closes the milestone.
**Delivers:** `mcp/errors.py`; `readOnlyHint`/`destructiveHint`/`idempotentHint` annotations; full client-matrix UAT (Claude Code, Desktop, Hermes); concurrency + long-call + ownership-scoping verification.

### Phase Ordering Rationale
- **Foundation gates everything:** scaffold + auth + lifespan + middleware-exemption must precede any tool; they also carry nearly all the integration risk (Pitfalls 1–4), so failing fast here is the point.
- **Job registry before generators:** all three long-running tools return job-ids and are useless without `job_status`; the first AI tool is where the sync-DB/timeout pitfalls surface, so the session/pool pattern is set once and reused.
- **Tool groups mirror the service layer** (management / screenwriting / breakdown / shotlist), are independent adapters, and parallelize cleanly — low risk by design.
- **Polish/UAT last** because discovery quality and the client matrix can only be finalized against the complete surface.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** the **exact library + import paths must be pinned** — STACK.md and ARCHITECTURE.md disagree (official `mcp` SDK vs. standalone `fastmcp`); resolve via the auth-hook + inbound-header-access + lifespan-composition + Starlette-version-resolution requirements. Also verify Hermes static-header support (unverified) in the spike.
- **Phase 2:** job-registry durability/TTL choice (in-memory vs. small table) and the `to_thread` + pool-sizing pattern under 3+ concurrent generations.

Phases with standard patterns (skip deep research):
- **Phases 3–6:** identical thin-adapter pattern over existing services; well-understood once Phase 1–2 establish the conventions.
- **Phase 7:** standard discovery/annotation/UAT work; checklist-driven.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official SDK docs + PyPI + Claude Code docs. Static-bearer viability verified server- and client-side. Lone gap: which `FastMCP` package — pin at scaffold. |
| Features | HIGH | MCP design best practices corroborated across many current sources; tool-to-service mapping verified against this repo's actual endpoints/services. |
| Architecture | HIGH on mount model / auth threading / build order; MEDIUM on exact FastMCP API surface (two competing libraries; import paths must be pinned against the installed version). |
| Pitfalls | HIGH on auth/transport/middleware/lifespan (verified against SDK/FastMCP issues, Starlette discussions, and the codebase); MEDIUM on security/prompt-injection (industry guidance, not vendor-specific). |

**Overall confidence:** HIGH

### Gaps to Address
- **Library choice (`mcp` SDK vs. standalone `fastmcp`):** the two research files diverge. ARCHITECTURE.md prefers `fastmcp` for `get_http_headers()` / `http_app(path=...)` ergonomics; STACK.md prefers the official `mcp` SDK to minimize dependencies/spec-drift. *Handle:* decide in Phase 1 against the concrete needs (inbound-header access inside tools, sub-path mounting, lifespan composition, custom token verification, single resolved Starlette version) and pin exact import paths.
- **Hermes static-header support:** unverified — treat as a Phase-1 spike discovery task before relying on it.
- **Starlette version resolution:** both FastAPI and the MCP package depend on Starlette; verify one resolved version with the startup smoke test after install.
- **Job-registry persistence:** in-memory + TTL vs. a small table — decide in Phase 2 based on whether jobs must survive a restart.
- **Multi-worker rate limiting:** the in-memory rate limiter is per-process; acceptable for a single-process internal deploy, revisit (shared store) only if scaled to multiple uvicorn workers.

## Sources

### Primary (HIGH confidence)
- `modelcontextprotocol/python-sdk` — Streamable HTTP transport, lifespan/session-manager pattern, `TokenVerifier` (OAuth optional). Issues #1367/#713 (mount/lifespan failure), #750 (header access in tools).
- PyPI `mcp` release metadata — latest 1.27.2, 1.27.x line, Python ≥3.10, v2 alpha pre-releases.
- Claude Code MCP docs (code.claude.com/docs/en/mcp) — `--header "Authorization: Bearer ..."`, `streamable-http` alias, SSE deprecated, per-tool hard wall-clock timeout + 60s first-byte budget.
- FastMCP (jlowin/PrefectHQ, gofastmcp.com) — FastAPI integration, `http_app(path=...)`, lifespan propagation, `get_http_headers()` / `get_http_request()`.
- Starlette (Kludex/starlette #1729/#2801/PR #2620) — `BaseHTTPMiddleware` unbounded-queue / no-backpressure streaming limitation; use pure ASGI.
- Codebase (ground truth) — `main.py`, `api/dependencies.py` (auth-as-dependency + atomic `request_count` increment), `middleware.py` (`BaseHTTPMiddleware`, in-memory window), `db.py` (sync SQLAlchemy), `services/ai_provider.py` (already async).
- MCP tool-design best practices — AWS Prescriptive Guidance, Speakeasy, Workato, philschmid, The New Stack.

### Secondary (MEDIUM confidence)
- anthropics/claude-ai-mcp #112 (closed "not planned") / #155 — claude.ai web connector is OAuth-only (out of scope).
- modelcontextprotocol #982, anthropics/claude-code #58687 — long-running/async tasks; clients don't reliably reset timeout on progress.
- jlowin/fastmcp #1233 / #596 — stale HTTP request context across calls in a session (re-read headers per call).
- MCP Resources vs Tools vs Prompts + client-support reality — Microsoft, Exo, Layered, WorkOS.
- MCP security — modelcontextprotocol.io, OWASP MCP cheat sheet, Microsoft indirect-injection guidance.

### Tertiary (LOW confidence)
- Community FastAPI+MCP mount/bearer walkthroughs (Medium, gofastmcp bearer auth, ekky.dev) — corroborating only, cross-checked against primary sources.

---
*Research completed: 2026-06-11*
*Ready for roadmap: yes*
