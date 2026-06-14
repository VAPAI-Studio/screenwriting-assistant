# Feature Research

**Domain:** MCP server tool surface for an existing screenwriting + production-breakdown app (wrapping built capabilities as agent-callable tools)
**Researched:** 2026-06-11
**Confidence:** HIGH (MCP design best practices verified across multiple current sources; tool-to-service mapping verified against this repo's existing endpoints/services)

---

## Scope Of This Research

This is a SUBSEQUENT milestone. The underlying capabilities (write/generate screenplay, breakdown extraction, shotlist, project/show/episode management) **already exist** and are not re-researched. This file answers: **how to shape those capabilities into MCP tools an external agent (Claude Desktop/Code, Hermes) can introspect and drive**, and **what the right minimal-yet-complete tool surface is** for the blank-page → breakdown flow.

The four research questions map to sections below:
1. Tool-design best practices → "Design Principles" + "Tool Surface" tables
2. Resources vs tools vs prompts → "Resource-vs-Tool Decision"
3. Table-stakes vs differentiator tool set → "Feature Landscape" tables
4. Anti-features + long-running handling → "Anti-Features" + "Long-Running Tool Calls"

---

## Design Principles (from current MCP best practice)

These principles drive every per-tool decision below. Confidence HIGH — corroborated by Anthropic/MCP docs, AWS Prescriptive Guidance, Speakeasy, Workato, philschmid, The New Stack.

1. **Granularity = "self-contained useful result," not 1:1 with REST.** A good tool returns something the agent can reason about without needing to know the next call. Too granular (forces orchestration in the LLM's context) and too fat (hides steps the agent may want to branch on) are both failures. *Implication: do the multi-step orchestration that exists inside our services in our code, expose one tool per agent-meaningful outcome.*
2. **`service_action_resource` naming.** Consistent, greppable, disambiguates as the catalog grows. We use `screenplay_*`, `breakdown_*`, `shot_*`, `project_*`/`show_*`/`episode_*` prefixes.
3. **Few, focused tools beat many.** Too many tools → the model mis-selects and hallucinates sequences. Target a surface in the low-to-mid teens, not 30+. Prefer one parameterized tool over several near-duplicates.
4. **Descriptions are the API.** The model selects purely from name + description + input schema. Each tool needs a one-line "use this when…" and explicit parameter docs. Bad descriptions are the #1 cause of "MCP doesn't work."
5. **Structured results, with a prose summary.** Return structured JSON (so the agent can act on it) but include a short human-readable summary field for the model to narrate. Avoid dumping giant blobs — return IDs + a digest, let the agent fetch detail on demand.
6. **Write tools must be idempotent / explicit.** This app already uses idempotent upserts (WRITE-04, ScreenplayContent keyed by `episode_index`); surface that property and require explicit target IDs rather than "current project" ambient state.
7. **Read before write, narrow before broad.** Provide cheap read tools so the agent can orient before mutating, and scope reads (by category, by scene) so results stay small.

---

## Resource-vs-Tool Decision (Question 2)

**Verdict: expose everything as TOOLS for v8.0. Defer MCP Resources.** Confidence HIGH.

The textbook rule says "read-only context → Resource, side-effecting action → Tool." By that rule, "read a screenplay" / "read a breakdown" look like Resources. **But two practical facts override the textbook:**

- **Client support for Resources is immature and inconsistent.** Claude Desktop has partial Resource support (user attaches them via "+"); Claude Code's Resource support is notably weaker; Hermes is a custom client with unknown Resource UX. Resources are "the overlooked primitive" precisely because hosts haven't built the UX. A tool call works in **every** MCP client.
- **Resources are application/user-controlled, not model-controlled.** A Resource is something the *user* attaches as context; the *model* cannot decide "I need to read scene 4's breakdown right now" and pull a Resource autonomously. Our flow is agent-driven ("read the screenplay, then extract breakdown, then list props") — that is exactly model-controlled reads, which are **tools**, not resources.

So our read operations are *model-controlled dynamic reads keyed by project/episode/scene/category* → **tools** (`screenplay_read`, `breakdown_read`, etc.). This also matches granularity principle #7 (scoped reads).

**Prompts:** Out of scope for v8.0. MCP Prompts are user-selected templates surfaced in the client UI (e.g. a "/breakdown-this-script" slash command). They are a nice differentiator later but add a second integration surface the consumers (esp. Hermes) may not render. One candidate prompt is noted in Differentiators.

**Revisit trigger:** If the consumers report token bloat from re-reading large screenplays through tool results, promote `screenplay_read` to *also* be exposed as a Resource (tools and resources can coexist for the same data). Not v8.0.

---

## Long-Running Tool Calls (Question 4 — the hard constraint)

Generation/extraction tools run ~60s+. This is the single biggest design risk: MCP clients impose request timeouts (commonly ~60s; `MCP error -32001` = request timeout is the most-reported MCP failure), and a blocked synchronous call ties up the session.

Three handling options, current as of 2026:

| Option | How | Reliability today | Verdict for v8.0 |
|--------|-----|-------------------|------------------|
| **Block + progress notifications** | Tool stays open, emits `notifications/progress` to reset the idle timer | Spec supports it, but client support is buggy — several clients (incl. reported Claude Code/Cowork cases) do **not** reset their timeout on progress, so calls still time out | Risky. Use as a *secondary* keep-alive only |
| **MCP `tasks` primitive (async task-augmented requests)** | Tool returns a `taskId`; client polls `tasks/get` until terminal | This is the "right" long-term answer and the spec direction, but it is **new** and not yet broadly implemented by Claude Desktop/Code or arbitrary clients | Defer — don't depend on client `tasks` support in v8.0 |
| **App-level job + poll tool (recommended)** | Long tool returns *fast* with `{ job_id, status: "running" }`; a separate cheap `*_status` / `*_result` tool the agent polls | Works on **every** client because it's just ordinary tool calls; the agent's own loop does the polling | **Adopt.** Portable, no client feature dependency |

**Recommended pattern for v8.0:** the **job-id + poll** pattern, implemented over plain tools.

- `screenplay_generate_scene`, `breakdown_extract`, `shotlist_generate` each **start** the work and return immediately with `{ job_id, status }` (Confidence HIGH this is the portable choice).
- A small number of generic poll tools (`job_status(job_id)` → running/done/failed + result-or-summary) let the agent drive completion in its own turn loop.
- Optionally *also* emit progress notifications as a keep-alive nicety where the client honors them — but never rely on them for correctness.
- **Avoid one job-status tool per generator** (that's needless tool-count bloat) — a single `job_status` keyed by `job_id` is cleaner. If job kinds need different result shapes, return a `kind` discriminator in the result.

This requires a lightweight job registry on the server (job_id → state/result, TTL'd in memory or a small table). That is the main **new** infrastructure v8.0 introduces beyond wrapping existing services; flag it for the roadmap.

---

## Feature Landscape (Tool Surface)

Grouped by domain. Each tool: **R/W**, **long-running?**, **table-stakes / differentiator / anti-feature**, and the **existing service/endpoint** it depends on.

### Group A — Screenwriting

#### Table Stakes
| Tool | R/W | Long-running | Why expected | Depends on (existing) |
|------|-----|--------------|--------------|-----------------------|
| `screenplay_read` | R | No | Agent must orient before it can write/extract; the whole flow starts here. Scope by `project_id`/`episode_id`, optional `scene`/`episode_index` | `ScreenplayContent` rows (read), screenplay editor data |
| `screenplay_write` | W | No (save is fast) | Direct hand-written screenplay path (Phase 54). Agent supplies full text; server splits by sluglines, upserts idempotently, marks breakdown/shotlist stale | Phase 54 save path (WRITE-01..04), heading splitter, `ScreenplayContent` upsert |
| `screenplay_generate_scene` | W | **Yes (~60s+)** | The v6.0 AI path (continuity, voice, craft). The core "AI writes the script" value. Returns `job_id` | `template_ai_service.py` v6.0 generation path |

#### Differentiators
| Tool | R/W | Long-running | Value | Depends on |
|------|-----|--------------|-------|------------|
| `screenplay_regenerate_scene` | W | **Yes** | v6.0 regenerate-and-compare; lets an agent iterate on a weak scene. Distinct from generate because it targets an existing scene and can return the prior text alongside | v6.0 regenerate path (EVAL-01) |

**Note:** `screenplay_write` and `screenplay_generate_scene` are sibling write paths (hand vs AI). Keep them as **two named tools**, not one `mode:` param — the agent's intent ("write this text" vs "AI, write me a scene") is cleaner as distinct tools, and they have different long-running profiles.

### Group B — Breakdown

#### Table Stakes
| Tool | R/W | Long-running | Why expected | Depends on |
|------|-----|--------------|--------------|------------|
| `breakdown_extract` | W | **Yes (~60s+)** | The "extract everything to produce it" core value; v7.0 fidelity path. Returns `job_id`. Idempotent re-extract preserving user edits (REEX-02) | `breakdown_service.py` (v7.0), per-scene extraction |
| `breakdown_read` | R | No | Read elements; **scope by category** (one of the 10) to keep results small (principle #7). Returns elements + per-appearance context (APPR) | breakdown read endpoints, element/appearance tables |

#### Differentiators
| Tool | R/W | Long-running | Value | Depends on |
|------|-----|--------------|-------|------------|
| `breakdown_read_scene` | R | No | Read all elements for a single scene with per-appearance context notes — supports a "what's in scene 4?" agent question without pulling the whole breakdown | v7.0 appearance/context data (APPR-01/02) |

### Group C — Shotlist

#### Table Stakes
| Tool | R/W | Long-running | Why expected | Depends on |
|------|-----|--------------|--------------|------------|
| `shotlist_read` | R | No | Read shots (scene-grouped). Orientation before edit | `shots.py` CRUD |
| `shot_create` | W | No | Create a shot (JSONB freeform fields). Core shotlist value | `shots.py` create |
| `shotlist_generate` | W | **Yes** | AI shotlist generation; returns `job_id` | `shotlist_generation_service.py` |

#### Differentiators
| Tool | R/W | Long-running | Value | Depends on |
|------|-----|--------------|-------|------------|
| `shot_update` | W | No | Edit an existing shot's fields. Completes the CRUD loop for agent-driven refinement | `shots.py` update |

### Group D — Project / Show / Episode Management

#### Table Stakes
| Tool | R/W | Long-running | Why expected | Depends on |
|------|-----|--------------|--------------|------------|
| `project_list` | R | No | Agent must discover what exists before acting. The entry point for any session | `projects.py` list |
| `project_create` | W | No | Create a standalone project to write into — required for blank-page flow | `projects.py` create |
| `project_get` | R | No | Read one project's metadata/structure (framework, sections) so the agent knows the shape it's writing into | `projects.py` get, sections |

#### Differentiators
| Tool | R/W | Long-running | Value | Depends on |
|------|-----|--------------|-------|------------|
| `show_create` | W | No | Create a TV show (v4.2). Enables episodic flows for the agent | `shows.py` create |
| `episode_create` | W | No | Create an episode inside a show; episodes carry the full pipeline | `shows.py`/episodes |
| `show_read_bible` | R | No | Read the series bible (characters/world/arc/tone). High-value context for an agent about to generate episode scenes — feeds the agent the same context BIBL-04 feeds generation | series-bible read (BIBL-01/02) |
| `show_list` / `episode_list` | R | No | Discover shows/episodes (parallel to `project_list`) | `shows.py` list |

---

## Anti-Features (Question 4 — explicitly DO NOT expose)

| Tool / pattern | Why it's tempting | Why problematic | Instead |
|----------------|-------------------|-----------------|---------|
| **`project_delete` / `show_delete` / `episode_delete` / `shot_delete`** | "CRUD should be complete" | Destructive + irreversible via an autonomous agent with no UI confirmation. Cascade deletes (Project→Section→ChecklistItem; episodes; shots) make a single bad call catastrophic. Internal tool ≠ needs agent-driven deletion | Omit from MCP surface. Deletion stays a human action in the web UI. If ever needed, gate behind a separate explicitly-flagged tool with a `confirm` token |
| **`screenplay_write_full_project` overwrite without scoping** | "Let the agent rewrite the whole script in one call" | Silent clobber of existing scenes; agent can't tell what it destroyed | Keep writes scene/episode-scoped and idempotent; surface staleness flags in the result so the agent knows what it invalidated |
| **A single fat `do_screenwriting_workflow` tool** | "One tool for the whole blank-page→breakdown flow" | Hides the steps the agent needs to branch on (review a scene before extracting; the flow is inherently multi-turn). Also makes the one long-running call un-pollable | Keep the per-stage tools above; let the agent orchestrate the flow across turns |
| **Synchronous (blocking) generate/extract tools** | Simpler to implement | Times out (~60s clients), blocks the session, no cancellation | Job-id + poll pattern (see Long-Running section) |
| **Raw/atomic DB tools (`run_sql`, `update_table`)** | Maximum flexibility | Bypasses all validation/sync/staleness logic; lets the agent corrupt state. Classic MCP anti-pattern | Only expose intent-level tools that route through existing services |
| **One status/poll tool per generator** | Mirrors each generator | Tool-count bloat → model mis-selection | Single generic `job_status(job_id)` |
| **Media upload / thumbnail tools, storyboard/imagen tools** | They exist in the app | Binary upload over MCP is awkward; out of the blank-page→breakdown critical path; expands surface and confusion | Defer. Not v8.0 |
| **Breakdown reverse-sync / agent-review-pipeline / RAG / book-processing tools** | Powerful existing capabilities | Internal-mechanism tools, not agent-meaningful outcomes; explode the catalog and require app-specific glue the consumers shouldn't need | Out of scope for v8.0 |
| **Exposing `mark_stale` / `acknowledge_stale` as tools** | Sync plumbing is real | Staleness is an internal side-effect of writes; an agent toggling it directly is meaningless and error-prone | Don't expose. Instead, *report* staleness in write-tool results and reads so the agent reacts to it |

---

## Feature Dependencies

```
project_list / project_create / project_get
        └──enables──> screenplay_write / screenplay_generate_scene  (need a project_id)
                              └──enables──> breakdown_extract  (needs screenplay text)
                                                  └──enables──> breakdown_read / breakdown_read_scene
                              └──enables──> shotlist_generate / shot_create
                                                  └──enables──> shotlist_read / shot_update

screenplay_generate_scene / breakdown_extract / shotlist_generate
        └──requires──> job_status  (poll loop; long-running results)

show_create ──requires──> (then) episode_create ──behaves-as──> project_*  (episode = project-with-pipeline)
show_read_bible ──enhances──> screenplay_generate_scene  (bible context improves episode generation)

screenplay_write / *_generate_* ──side-effect──> staleness flags
        └──surfaced-in──> tool results so agent knows to re-run breakdown_extract / shotlist_generate
```

### Dependency Notes
- **All generation/extraction tools require `job_status`:** they return job_ids; without the poll tool the agent can't retrieve results. `job_status` is therefore table-stakes infrastructure, not optional.
- **breakdown_extract requires screenplay content:** extraction reads `ScreenplayContent.content` (BFID-01). The agent must `screenplay_write` or `screenplay_generate_scene` first. Tool descriptions should state this precondition.
- **episode_create depends on show_create:** episodes live inside shows; an episode then behaves like a standalone project for all screenplay/breakdown/shotlist tools (EPIS-02). The MCP tools should accept either a `project_id` or an `episode_id` as the writing target (or normalize both to a single "target id"), so the agent doesn't need two parallel toolsets.
- **show_read_bible enhances generation:** giving the agent the bible mirrors what BIBL-04 already injects server-side; lets the agent reason about continuity/tone before requesting scenes.
- **Staleness is a result field, not a tool:** writes invalidate downstream breakdown/shotlist; surfacing this in results lets the agent self-correct without a stale-management tool.

---

## MVP Definition

### Launch With (v8.0) — the minimal usable blank-page → breakdown surface
Essential = an external agent can run the full flow end-to-end and orient itself.

- [ ] `job_status` — without it, no long-running tool returns usable results (infrastructure-critical)
- [ ] `project_list`, `project_create`, `project_get` — discover + create a target to write into
- [ ] `screenplay_read` — orient before writing/extracting
- [ ] `screenplay_write` — direct write path (fast, deterministic, easiest to validate)
- [ ] `screenplay_generate_scene` — the AI-writes core value (long-running → job-id)
- [ ] `breakdown_extract` — the "extract everything to produce it" core value (long-running → job-id)
- [ ] `breakdown_read` (category-scoped) — read the extraction result
- [ ] `shotlist_read`, `shot_create`, `shotlist_generate` — complete the production-breakdown arc

This is ~12 tools — within the "low-to-mid teens" target that keeps model tool-selection reliable.

### Add After Validation (v8.x)
Add once the core flow is proven and the consumers ask for it.

- [ ] `screenplay_regenerate_scene` — trigger: agents want iterative quality refinement
- [ ] `breakdown_read_scene` — trigger: agents ask scene-scoped breakdown questions
- [ ] `shot_update` — trigger: agents want to refine generated shots
- [ ] `show_create`, `episode_create`, `show_read_bible`, `show_list`/`episode_list` — trigger: episodic/TV-show flows requested by a consumer (Hermes likely)

### Future Consideration (v9+)
- [ ] Promote `screenplay_read`/`breakdown_read` to **MCP Resources** (in addition to tools) — defer until client Resource support matures and/or token bloat is observed
- [ ] MCP **Prompt** templates (e.g. `/blank-page-to-breakdown`, `/extract-this-script`) — defer until a consumer renders prompts
- [ ] Adopt native MCP **`tasks`** primitive for long-running calls — defer until Claude Desktop/Code + Hermes reliably support it; the job-id pattern bridges until then
- [ ] Media / storyboard / imagen tools — defer indefinitely; outside the breakdown critical path

---

## Feature Prioritization Matrix

| Tool | Agent Value | Impl Cost | Priority |
|------|-------------|-----------|----------|
| `job_status` (+ job registry) | HIGH | MEDIUM (new infra) | P1 |
| `project_list` / `project_create` / `project_get` | HIGH | LOW (wrap existing) | P1 |
| `screenplay_read` | HIGH | LOW | P1 |
| `screenplay_write` | HIGH | LOW | P1 |
| `screenplay_generate_scene` | HIGH | MEDIUM (job-id wrap) | P1 |
| `breakdown_extract` | HIGH | MEDIUM (job-id wrap) | P1 |
| `breakdown_read` | HIGH | LOW | P1 |
| `shotlist_read` / `shot_create` / `shotlist_generate` | MEDIUM | LOW–MEDIUM | P1 |
| `screenplay_regenerate_scene` | MEDIUM | MEDIUM | P2 |
| `breakdown_read_scene` | MEDIUM | LOW | P2 |
| `shot_update` | MEDIUM | LOW | P2 |
| `show_*` / `episode_*` (create/list/bible) | MEDIUM | LOW–MEDIUM | P2 |
| any `*_delete` | (negative) | LOW | P3 / anti-feature |
| MCP Resources / Prompts / native tasks | LOW (now) | MEDIUM | P3 |

**Priority key:** P1 = launch (v8.0) · P2 = add after validation · P3 = future/anti-feature

---

## Cross-Cutting Notes For The Roadmapper

- **One genuinely new component:** the **job registry + `job_status` poll tool** is the only substantial new build; everything else is a thin wrap of existing services. Treat it as its own roadmap phase (it gates all three long-running tools).
- **Target-id normalization:** standalone `project_id` and `episode_id` both behave as "a project with a pipeline." Decide on a single `target` identifier convention early so screenplay/breakdown/shotlist tools work uniformly against both (avoids doubling the toolset).
- **Result shape standard:** define one envelope — `{ summary: string, data: {...}, stale?: {...}, job_id?: string }` — so the model always gets a narratable summary plus structured data and any staleness signal. Apply across all tools.
- **Auth carries through:** all tools route through the v5.0 API-key identity/rate-limit gateway (per PROJECT.md transport decision); no per-tool auth logic needed, but per-key rate limiting interacts with the agent's poll loop — set a sane `pollInterval` hint so polling doesn't burn the rate budget.
- **Descriptions must state preconditions** (e.g. "extract requires saved screenplay text") and **long-running behavior** (e.g. "returns a job_id; poll job_status until done") so a generic client needs no app-specific glue — that's the v8.0 quality bar.

---

## Sources

MCP tool-design best practices (granularity, naming, structured results):
- [MCP tool design strategy — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy.html)
- [Design MCP tools — Speakeasy](https://www.speakeasy.com/mcp/tool-design)
- [MCP server design best practices — Workato Docs](https://docs.workato.com/mcp/mcp-server-design.html)
- [MCP is Not the Problem, It's your Server — philschmid](https://www.philschmid.de/mcp-best-practices)
- [15 Best Practices for Building MCP Servers in Production — The New Stack](https://thenewstack.io/15-best-practices-for-building-mcp-servers-in-production/)
- [General Best Practices — Salesforce Hosted MCP Servers](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/general-best-practices.html)

Resources vs Tools vs Prompts + client support reality:
- [MCP Demystified: Tools vs Resources vs Prompts — Microsoft Community Hub](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/mcp-demystified-tools-vs-resources-vs-prompts-explained-simply/4508057)
- [MCP Tools vs Resources vs Prompts: When to Use Each Primitive — Exo Technologies](https://exotechnologies.xyz/research/mcp-tools-resources-prompts)
- [MCP Resources: The Overlooked Primitive (and Why That's a Problem) — Layered System](https://layered.dev/mcp-resources-the-overlooked-primitive/)
- [Understanding MCP features — WorkOS](https://workos.com/blog/mcp-features-guide)

Long-running tool calls (timeouts, progress, async tasks):
- [MCP Async Tasks: Building long-running workflows for AI Agents — WorkOS](https://workos.com/blog/mcp-async-tasks-ai-agent-workflows)
- [Fixing MCP Error -32001: Request Timeout — MCPcat](https://mcpcat.io/guides/fixing-mcp-error-32001-request-timeout/)
- [Cowork MCP client times out long-running tool calls despite progress notifications — anthropics/claude-code#58687](https://github.com/anthropics/claude-code/issues/58687)
- [Long running / async tools / resumability — modelcontextprotocol#982](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/982)

Repo grounding: `backend/app/services/` (`template_ai_service.py`, `breakdown_service.py`, `shotlist_generation_service.py`) and `backend/app/api/endpoints/` (`projects.py`, `sections.py`, `shots.py`, `shows.py`, `breakdown.py`); `.planning/PROJECT.md` (v8.0 milestone + transport decision); `.planning/REQUIREMENTS.md` (v6.0/v7.0/Phase 54 capabilities).

---
*Feature research for: MCP server tool surface (v8.0)*
*Researched: 2026-06-11*
