<!-- refreshed: 2026-07-24 -->
# Architecture

**Analysis Date:** 2026-07-24

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     React 18 SPA (Vite, port 4321)                        │
│  `frontend/src/App.tsx` — React Router + React Query                      │
├──────────────────┬──────────────────┬───────────────────┬────────────────┤
│  ProjectWorkspace│    Breakdown /    │      Shows /       │  Books /       │
│  (phase-driven,  │    Storyboard     │      Seasons       │  Snippets /    │
│  pattern views)  │  `Breakdown/*`    │   `Shows/*`        │  Chat          │
│  `Workspace/*`   │  `Storyboard/*`   │                    │                │
│  `Patterns/*`    │                   │                    │                │
└────────┬─────────┴────────┬──────────┴─────────┬──────────┴──────┬─────────┘
         │  fetch (/api, Bearer token from localStorage)            │
         │  `frontend/src/lib/api.tsx`                              │
         ▼                  ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              FastAPI app (Uvicorn, port 8000)                             │
│  `backend/app/main.py` — middleware stack + routers + mounted MCP        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Middleware (top→bottom): CORS → Logging → Security →             │   │
│  │  RequestSizeLimit → RateLimit → ApiKeyRateLimit                   │   │
│  │  `backend/app/middleware.py`                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  Endpoints (`api/endpoints/*`) → Services (`services/*`) → Models        │
│  DI + auth: `api/dependencies.py`  •  MCP sub-app mounted at `/mcp`       │
└──────────────────────────┬───────────────────────────┬──────────────────┘
                           │ SQLAlchemy ORM             │ OpenAI / providers
                           ▼                            ▼
┌────────────────────────────────────────┐   ┌──────────────────────────────┐
│  PostgreSQL 15 (+ pgvector for RAG)     │   │  OpenAI GPT-4, embeddings,    │
│  `backend/app/models/database.py`       │   │  image gen; vapai-studio MCP; │
│  Local media dir mounted at `/media`    │   │  `services/ai_provider.py`    │
└────────────────────────────────────────┘   └──────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app + lifespan | Router registration, middleware, MCP mount, `init_db()`/migrations on startup | `backend/app/main.py` |
| Endpoints layer | HTTP route handlers, request/response validation, DI wiring | `backend/app/api/endpoints/` |
| Dependencies | DB session + auth resolution (mock, `sa_` API keys, JWT), admin gate | `backend/app/api/dependencies.py` |
| Services layer | Business logic: AI generation, RAG, breakdown, shotlist, agents, vapai push | `backend/app/services/` |
| ORM models | SQLAlchemy declarative models + enums; single source of the data model | `backend/app/models/database.py` |
| Pydantic schemas | v2 request/response schemas + field validators | `backend/app/models/schemas.py` |
| Template registry | Loads `templates/*.json`, resolves `$ref` shared phases, flattens subsections | `backend/app/templates/registry.py` |
| MCP server | In-process Streamable-HTTP MCP exposing the production pipeline as tools | `backend/app/mcp_server/server.py` |
| React SPA shell | Routing, React Query provider, layout | `frontend/src/App.tsx`, `main.tsx` |
| ProjectWorkspace | Phase/subsection navigation, dispatches to a UI pattern view | `frontend/src/components/Workspace/ProjectWorkspace.tsx`, `ContentArea.tsx` |
| Pattern views | Render a subsection according to its `ui_pattern` | `frontend/src/components/Patterns/` |
| API client | Fetch wrapper (30s timeout, Bearer auth), typed per-domain methods | `frontend/src/lib/api.tsx` |

## Pattern Overview

**Overall:** Layered client-server. FastAPI layered backend (endpoints → services → SQLAlchemy models) paired with a React Query SPA whose editor is **pattern-driven**: JSON templates describe phases/subsections, each subsection names a `ui_pattern`, and the frontend renders it by dispatching to a matching pattern component.

**Key Characteristics:**
- **Template-driven content model.** A `Project` is scaffolded from a `TemplateType` JSON (`short_movie`, `sketch`, `episode`, `vertical_drama`). Templates define phases (`idea`, `story`, `scenes`, `write`) and subsections; user content lands in generic `PhaseData` / `ListItem` rows keyed by `(phase, subsection_key)`, not per-feature tables.
- **Pattern dispatch on the frontend.** `ContentArea` switches on `subsection.ui_pattern` (`structured_form`, `card_grid`, `repeatable_cards`, `wizard`, `wizard_with_chat`, `ordered_list`, `individual_editor`, `scene_workspace`, `screenplay_editor`) to a component in `Patterns/`.
- **Dual API surface.** The same services back both REST (`/api/*`) and an MCP server (`/mcp`), sharing auth via framework-neutral `authenticate_token`.
- **Owner-scoped multi-tenancy.** Every row carries `owner_id`; auth resolves a `User` and queries filter by owner.
- **AI as a service concern.** Provider abstraction (`ai_provider.py`) + specialized services (template/breakdown/shotlist/socratic/rag); endpoints stay thin.
- **Continuity domain layered above projects.** `Show` (bible) → `Season` → `EpisodeSlot` (plan) → `Project` (episode, `show_id`/`season_id`), with staleness flags reconciling plan vs. written episode.

## Layers

**Presentation (React SPA):**
- Purpose: All UI. Phase-based editing, breakdown/shotlist/storyboard boards, shows/seasons, books/chat.
- Location: `frontend/src/`
- Contains: Routed pages (`App.tsx`), domain components under `components/*`, reusable `Patterns/*`, API client `lib/api.tsx`, `lib/constants.ts`, hooks.
- Depends on: REST `/api/*`, static `/media/*`.
- Used by: End users (browser).

**API / Endpoints:**
- Purpose: HTTP interface, validation, orchestration of services.
- Location: `backend/app/api/endpoints/`
- Contains: Route handlers grouped by domain. Registered in `main.py`.
- Depends on: `api/dependencies.py` (DB + auth), services, schemas.
- Used by: Frontend, external API-key clients.

**Services (business logic):**
- Purpose: Domain logic and AI orchestration.
- Location: `backend/app/services/`
- Contains: `template_ai_service.py` (largest — AI generation per template/phase), `breakdown_service.py`, `shotlist_generation_service.py`, `agent_service.py`, `rag_service.py`, `knowledge_extraction_service.py`, `book_processing_service.py`, `socratic_service.py`, `vapai_service.py`, `ai_provider.py`, `pipeline_composer.py`.
- Depends on: ORM models, external providers (OpenAI, embeddings, image gen, vapai MCP).
- Used by: Endpoints and MCP tools.

**Persistence:**
- Purpose: Durable state.
- Location: `backend/app/models/database.py`, `backend/app/db.py`
- Contains: SQLAlchemy models + `SafeVector` pgvector type; engine/session; `init_db()` runs migrations (`services/db_migrator.py`).
- Depends on: PostgreSQL 15 + pgvector.
- Used by: Services, endpoints, MCP tools.

**MCP integration:**
- Purpose: Expose the production pipeline as agent tools over Streamable HTTP.
- Location: `backend/app/mcp_server/`
- Contains: `server.py` (FastMCP + instructions), `auth.py` (`ApiKeyTokenVerifier`, `require_user`), `session.py`, `jobs.py`, `context.py`, `tools/` (core, screenwriting, management, breakdown, shotlist).
- Depends on: Same services + `authenticate_token`.
- Used by: External MCP clients (agents) authenticated with `sa_` API keys.

## Data Flow

### Primary Request Path (edit a subsection)

1. User edits a subsection in the workspace; `ProjectWorkspace` routes `/projects/:projectId/:phase/:subsectionKey` (`frontend/src/App.tsx:67-69`).
2. `ContentArea` fetches subsection data via React Query and dispatches on `ui_pattern` to a `Patterns/*` view (`frontend/src/components/Workspace/ContentArea.tsx:48`).
3. Pattern view calls `api.*` (`frontend/src/lib/api.tsx`) → `PUT/POST /api/phase-data` or `/api/list-items` with Bearer token.
4. Middleware stack processes the request (`backend/app/main.py:104-117`), then the router (`phase_data_ep` / `list_items_ep`) resolves `get_current_user` (`api/dependencies.py:153`).
5. Handler validates against `models/schemas.py`, mutates `PhaseData`/`ListItem` (`models/database.py`), commits, returns.
6. React Query invalidates and re-renders.

### AI Generation Flow (wizard / review)

1. Pattern view (`WizardView`) or `AIActionBar` posts to `/api/ai/*` or `/api/wizards/*`.
2. Endpoint calls a service (`template_ai_service.py`, `socratic_service.py`), which assembles context (bible via `utils/bible_context.py`, RAG snippets via `rag_service.py`) and calls `ai_provider.py`.
3. Result persists into `ai_suggestions` JSON on `PhaseData`/`ListItem`, or `SocraticQuestion`, or a `WizardRun`.

### Breakdown / Shotlist Flow

1. Screenplay text lives in `ScreenplayContent` / `ListItem`. `breakdown_service.py` extracts `BreakdownElement`s linked to scenes via `ElementSceneLink`; a `BreakdownRun` records the async run.
2. `shotlist_generation_service.py` produces `Shot`s (linked to scenes via `scene_item_id`, to elements via `ShotElement`).
3. `Project.breakdown_stale` / `shotlist_stale` flags flip when upstream text changes, prompting re-extraction. Media attaches via `AssetMedia`; storyboard frames via `StoryboardFrame`.

### MCP Tool Flow

1. Agent connects to `/mcp` with a `Bearer sa_…` key; `ApiKeyTokenVerifier` validates (`mcp_server/auth.py`) via `validate_token` (`api/dependencies.py:114`).
2. Tool call runs inside `mcp_session()` DB session; `require_user` resolves the owner (increments `request_count` once).
3. Tool delegates to the same services; LONG-RUNNING tools return `{job_id}`, polled via `job_status` (`mcp_server/jobs.py`).

**State Management:**
- Server state: React Query (5-min stale time, retry 1) — no Redux/Context store (`frontend/src/App.tsx:23-30`).
- Auth token: `localStorage`, injected as Bearer by `lib/api.tsx`.
- Backend rate-limit + AI response caches: in-memory (per-process).

## Key Abstractions

**Template + Pattern:**
- Purpose: Data-drive the editor. A template JSON declares phases/subsections and each subsection's `ui_pattern`; the frontend maps pattern → component.
- Examples: `backend/app/templates/episode.json`, `frontend/src/components/Patterns/`, `frontend/src/components/Workspace/ContentArea.tsx`.
- Pattern: Config-driven UI / strategy dispatch.

**PhaseData / ListItem generic content store:**
- Purpose: Hold arbitrary structured content without per-feature tables. Unique on `(project_id, phase, subsection_key)`.
- Examples: `models/database.py` (`PhaseData`, `ListItem`), `api/endpoints/phase_data.py`, `list_items.py`.

**Continuity hierarchy (Show → Season → Slot → Episode):**
- Purpose: TV-series bible + season planning above standalone projects.
- Examples: `models/database.py` (`Show`, `Season`, `EpisodeSlot`, `Project.show_id`), `api/endpoints/shows.py`, `seasons.py`, `utils/bible_context.py`, `utils/episode_summary.py`.

**Knowledge/RAG (Book → Chunk/Snippet/Concept → Agent):**
- Purpose: Ground AI in uploaded craft books; agents built from books/tags.
- Examples: `models/database.py` (`Book`, `BookChunk`, `Snippet`, `Concept`, `Agent`), `services/rag_service.py`, `knowledge_extraction_service.py`, `embedding_service.py`.

**AI provider abstraction:**
- Purpose: Single seam for model calls; specialized services build prompts.
- Examples: `services/ai_provider.py`, `openai_service.py`, `template_ai_service.py`.

## Entry Points

**Backend HTTP:**
- Location: `backend/app/main.py` (`app` FastAPI instance).
- Triggers: Uvicorn (`uvicorn app.main:app`), Docker Compose, Railway.
- Responsibilities: Middleware, router registration (`/api/*`), `/health`, `/media` static mount, `/mcp` MCP mount, lifespan `init_db()` + MCP session manager.

**MCP:**
- Location: `backend/app/mcp_server/server.py` (`mcp_app`), mounted at `/mcp` (`main.py:179`).
- Triggers: External MCP clients over Streamable HTTP.
- Responsibilities: Tool registration + owner-scoped execution.

**Frontend:**
- Location: `frontend/src/main.tsx` → `frontend/src/App.tsx`.
- Triggers: Browser page load (Vite build/dev).
- Responsibilities: Router, React Query provider, layout, route → page mapping.

## Architectural Constraints

- **Threading:** Async FastAPI event loop (Uvicorn). AI/DB work is largely synchronous inside handlers; long MCP jobs use the job-poll pattern (`mcp_server/jobs.py`), not background workers.
- **Global state:** Rate-limit and API-key-rate-limit counters are per-process in-memory dicts (`middleware.py`) — do not scale across replicas without a shared store. AI response cache in `openai_service.py`/services is also in-memory. Tests must reset the rate limiter (autouse fixture) to avoid cross-test 429s.
- **MCP lifespan:** `StreamableHTTPSessionManager.run()` may be entered only once per instance; the app composes the mounted MCP sub-app's own lifespan. Tests set `SKIP_MCP_LIFESPAN=1` / `SKIP_DB_INIT=1` (`main.py:48-53`).
- **`/mcp` bypasses the BaseHTTPMiddleware stack** (logging/security/size/rate) because those buffer responses and break streaming — each middleware early-returns on `/mcp` (`middleware.py`).
- **ScreenplayContent has no reliable ordering** — join scenes by `episode_index`, never by list position (see MCP instructions and project memory).
- **Enum values:** Postgres enum columns use `values_callable=lambda x: [e.value for e in x]` so DB stores lowercase values, not member names — replicate for any new enum column.

## Anti-Patterns

### Positional scene ordering

**What happens:** Code correlates scenes/screenplay content by array index.
**Why it's wrong:** `ScreenplayContent` has no reliable order; rows can arrive in any sequence. This bug recurred (v6.0 WR-01, v7.0 ph50).
**Do this instead:** Match by `episode_index` (scenes) / explicit `sort_order`. See MCP instructions in `mcp_server/server.py` and `utils/screenplay_split.py`.

### Per-feature tables for template content

**What happens:** Adding a bespoke table for a new subsection's data.
**Why it's wrong:** The content model is generic (`PhaseData` + `ListItem` keyed by `subsection_key`); a new table breaks the pattern-driven editor and AI plumbing.
**Do this instead:** Add a template subsection with a `ui_pattern` and store content in `PhaseData`/`ListItem` (`api/endpoints/phase_data.py`, `list_items.py`).

### Adding a template as "just a JSON file"

**What happens:** Dropping `templates/<x>.json` and expecting it to work.
**Why it's wrong:** A new template also needs a `TemplateType` enum value (Pydantic + Postgres enum), `init_db` registration, a delta migration, `test_template_formats` guards, and frontend icon maps (×2).
**Do this instead:** Follow the full checklist (see `TemplateType` in `models/database.py:192`, `templates/registry.py`, migrations, and project memory "Adding a template checklist").

## Error Handling

**Strategy:** Custom exception hierarchy (`backend/app/exceptions.py`) mapped to HTTP status codes; FastAPI validation errors reshaped to `{field, message}` lists via handlers in `main.py:120-138`.

**Patterns:**
- Validation via Pydantic v2 schemas + `utils/validators.py` (input sanitization/HTML).
- Auth failures raise `HTTPException(401)` from `authenticate_token`, reused verbatim by MCP's TokenVerifier.
- Async jobs surface `status="error"` + `error_message` (`BreakdownRun`, `WizardRun`, MCP jobs).

## Cross-Cutting Concerns

**Logging:** `LoggingMiddleware` assigns a request ID + timing per request; stdlib logging configured in `main.py`.
**Validation:** Pydantic v2 schemas (`models/schemas.py`) + `utils/validators.py`; request size cap (25MB) and rate limits in middleware.
**Authentication:** Bearer token → `authenticate_token` resolving mock (`mock-token`, dev only), `sa_` API keys, or JWT (`api/dependencies.py`); owner-scoped queries; `require_admin` gate for library writes; MCP reuses the same path.

---

*Architecture analysis: 2026-07-24*
