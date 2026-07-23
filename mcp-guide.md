# MCP Guide — Connecting Agents to the Screenwriting Pipeline

The backend exposes the studio's screenplay-production pipeline as an **MCP server**
(Model Context Protocol, Streamable HTTP). Any MCP-capable agent — Claude Code,
Claude Desktop, a custom client — can connect and drive the full flow: create
shows and projects, write bibles, plan seasons, write screenplays, extract
breakdowns, and generate shotlists. Everything an agent creates is visible and
editable in the web app, and vice versa.

---

## 1. Endpoint & transport

| Environment | URL |
|---|---|
| Production | `https://web-production-73857.up.railway.app/mcp/` |
| Local dev | `http://localhost:8000/mcp/` |

- Transport: **Streamable HTTP** (the modern MCP HTTP transport; no SSE-only mode).
- The server is mounted inside the main FastAPI app — same deploy, same DB as the web app.

## 2. Authentication

All tools require a **Bearer API key**:

```
Authorization: Bearer sa_<prefix>_<secret>
```

- Create keys in the web app: **Settings → API Keys**. The full key is shown
  **exactly once** at creation — store it then.
- Every tool is **owner-scoped to the key**: the agent only sees and touches the
  key owner's data. There is no cross-user access.
- No key / bad key → `401 {"error": "invalid_token"}`.

**There are no delete tools by design.** Agents can create and write, never
destroy. Deletion happens only in the web app.

## 3. Connecting a client

**Claude Code (CLI):**

```bash
claude mcp add --transport http screenwriting \
  https://web-production-73857.up.railway.app/mcp/ \
  --header "Authorization: Bearer sa_YOUR_KEY"
```

**Claude Desktop / JSON config style:**

```json
{
  "mcpServers": {
    "screenwriting": {
      "type": "http",
      "url": "https://web-production-73857.up.railway.app/mcp/",
      "headers": { "Authorization": "Bearer sa_YOUR_KEY" }
    }
  }
}
```

**Verify the connection** with the two probe tools:
- `ping()` → `{"status": "ok", "transport": "streamable-http"}`
- `whoami()` → the user resolved from your key (proves auth + owner scoping).

## 4. The canonical pipeline

The server ships instructions telling agents to drive every step through tools
instead of improvising. The flow:

```
1. ORIENT     project_list / show_list / episode_list / show_read_bible
2. CREATE     project_create (standalone)  |  show_create → bible → season → episode (series)
3. WRITE      screenplay_write (+ screenplay_generate_scene previews)
4. BREAKDOWN  breakdown_extract → breakdown_read
5. SHOTLIST   shotlist_generate → shotlist_read (+ shot_create)
```

Before writing anything for a show, the agent must call `show_read_bible` and
honor the **full** bible: central premise, story engine, series questions
(advance, never close), regular cast, characters, world/setting, season arc,
tone & style.

## 5. Tool reference

`?` marks optional parameters.

### Core
| Tool | What it does |
|---|---|
| `ping()` | Transport liveness check. |
| `whoami()` | Authenticated user for the key. |
| `job_status(job_id)` | Poll a long-running job until `done` / `error`. |

### Standalone projects (films, shorts, sketches)
| Tool | What it does |
|---|---|
| `project_list()` | List standalone projects (episodes are listed per-show instead). |
| `project_get(project_id)` | One project's metadata + staleness flags. |
| `project_create(title, framework?, template?)` | Create a standalone project. `template`: `short_movie` (default) \| `sketch` \| `vertical_drama`. Scaffolds the template's phases (idea/story/scenes/write). `framework` (`three_act` \| `save_the_cat` \| `hero_journey`) is recorded for the short-film flow. |

### Shows & series
| Tool | What it does |
|---|---|
| `show_list()` | List the user's shows with episode counts. |
| `show_create(title, description?, continuity_mode?)` | Create a show. `continuity_mode`: `anthology` (default) \| `connected` \| `standalone`. |
| `show_read_bible(show_id)` | Read the full bible. **Required before writing any episode.** |
| `bible_write(show_id, ...fields?)` | Partial-update the bible. Only passed fields change. `regular_cast` is a list of `{name, role, arc}` objects. |
| `bible_draft(show_id, logline?, genre?, tone?, guidance?)` | AI-propose a full bible from a seed, grounded on the current bible. **Returns a proposal without saving** — review, then persist with `bible_write`. |
| `season_create(show_id, title?, arc_summary?, number?)` | Create a season (number auto-increments). A season's `arc_summary` supersedes the show's bible season arc for its episodes. |
| `slot_create(season_id, title?, logline?, arc_function?, cliffhanger?, slot_number?)` | Add a planned-episode slot to the season map (slot_number auto-increments). The slot is the plan; the written episode is the truth. |
| `episode_create(show_id, title, template?, episode_number?)` | Create an episode (a project under the show), scaffolded with a template: `episode` (default) \| `vertical_drama` \| `short_movie` \| `sketch`. Episode number auto-increments. |
| `episode_list(show_id)` | List a show's episodes ordered by episode number. |

### Screenplay
| Tool | What it does |
|---|---|
| `screenplay_write(project_id, text, phase?)` | Persist the full screenplay. Every scene needs an `INT.`/`EXT.` slugline (each slugline becomes one scene). **Writes REPLACE all scenes** — to revise one scene, read everything, edit, write the full text back. This is also the import path for existing scripts. |
| `screenplay_read(project_id, scene_index?, phase?)` | Read the screenplay (whole or one scene). |
| `screenplay_generate_scene(project_id, episode_index, phase?)` | AI-craft a **preview** of a single scene (continuity + character voice). Does not persist — merge via `screenplay_write`. LONG-RUNNING. |

### Breakdown & shotlist
| Tool | What it does |
|---|---|
| `breakdown_extract(project_id)` | Extract production elements (characters, locations, props, …). LONG-RUNNING. Re-run when `breakdown_stale` is true. |
| `breakdown_read(project_id, category?)` | Read extracted elements, filterable by category. |
| `shotlist_generate(project_id)` | Build shots from the screenplay (run after breakdown). LONG-RUNNING. |
| `shotlist_read(project_id)` | Shots grouped by scene. |
| `shot_create(project_id, fields?, scene_item_id?, shot_number?)` | Add a manual shot. |

## 6. Long-running jobs

`breakdown_extract`, `shotlist_generate`, and `screenplay_generate_scene`
return `{job_id}` immediately. Poll:

```
job_status(job_id) → {"status": "pending" | "running" | "done" | "error", "result": ...}
```

**Never assume a long-running tool finished without polling.**

## 7. End-to-end recipes

### A series (e.g. a vertical microdrama)

```
show_create(title, continuity_mode="connected")
bible_draft(show_id, logline, genre, tone)      # proposal only
bible_write(show_id, ...accepted fields...)     # persist what you keep
season_create(show_id)
slot_create(season_id, title, logline, arc_function, cliffhanger)   # × N episodes
episode_create(show_id, title, template="vertical_drama")
show_read_bible(show_id)                        # honor it in the script
screenplay_write(episode_project_id, full_text)
```

Vertical-drama grammar the script must respect: hook in the first 3 seconds,
ONE plotline, one reversal, **mandatory cliffhanger** ending every episode.

### A standalone short

```
project_create(title, template="short_movie")   # or "sketch" / "vertical_drama"
screenplay_write(project_id, full_text)
breakdown_extract(project_id) → poll job_status
shotlist_generate(project_id) → poll job_status
```

## 8. Rules & gotchas

- **Match scenes by `episode_index`, never by list position.** Screenplay
  content has no reliable positional order.
- **`screenplay_write` replaces everything.** Read → edit → write back the
  full text for single-scene revisions.
- **Staleness flags:** `breakdown_stale` / `shotlist_stale` on a project mean
  the screenplay changed since the last extraction — re-run those steps.
- **Bible before writing:** for any episode, `show_read_bible` first; episodes
  must run on the story engine and advance series questions without closing them.
- **`bible_draft` saves nothing.** Persisting requires an explicit `bible_write`.
- **No deletes over MCP.** Clean up test shows/projects in the web app.

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `401 invalid_token` | Missing/wrong `Authorization` header, or a revoked key. Create a new key in Settings → API Keys. |
| `404` on an id the agent just used | Owner scoping: the resource belongs to another user's key, or the id is stale. Re-orient with `project_list` / `show_list`. |
| `400 template must be one of [...]` | Invalid `template` value — see the lists in `project_create` / `episode_create` above. |
| Long-running tool "never finishes" | You must poll `job_status(job_id)`; the tool call itself returns immediately. |
| Agent claims success but nothing appears in the web app | The agent likely hallucinated a call. Demand raw tool outputs; every create tool returns the new entity's id. |
