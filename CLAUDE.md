# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack **screenwriting + production-breakdown assistant**. It takes a project from a blank page to a production-ready breakdown: AI helps write the screenplay through a phased pipeline (Idea → Story → Scenes → Write), then extracts everything needed to produce it (element breakdown, shot list, storyboard). It also manages multi-episode **shows/seasons** with cross-episode continuity, a **book/RAG knowledge library** that injects craft doctrine into generation, reusable **snippets**, an **AI chat** assistant, and an in-process **MCP server** so external agents can drive the whole pipeline. A "Send to vapai-studio" bridge pushes finished screenplays to a separate production app.

This is an **internal tool**, not a market product — scope is script-writing and breakdown quality, not market/growth features.

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Radix UI, TanStack React Query, react-router-dom, lucide-react, react-markdown, @hello-pangea/dnd
- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2.0, Pydantic v2 / pydantic-settings
- **Database:** PostgreSQL 15 with **pgvector** (RAG embeddings, 1536-dim)
- **AI:** Provider-agnostic via `services/ai_provider.py` — **default provider is Anthropic** (`claude-opus-4-8`); OpenAI (`gpt-4o`) selectable. OpenAI is also used for embeddings (`text-embedding-3-small`). Optional Google Vertex **Imagen** for storyboard image generation.
- **MCP:** Official `mcp` Python SDK, mounted in-process over Streamable HTTP at `/mcp`
- **Infrastructure:** Docker Compose (db + backend + frontend). Prod: backend on **Railway**, frontend on **Vercel**.

## Development Commands

### Full stack (Docker)
```bash
docker compose up --build          # db (pgvector:pg15) + backend :8000 + frontend :4321
docker compose down
```

### Backend (standalone)
```bash
cd backend
source venv/bin/activate            # Python 3.11 (3.14 breaks SQLAlchemy/tiktoken)
uvicorn app.main:app --reload --port 8000
```

### Frontend (standalone)
```bash
cd frontend
npm run dev                         # Vite dev server on :4321 (proxies /api → :8000)
npm run build                       # tsc && vite build
npm run lint                        # ESLint (max-warnings 0)
```

### Tests (backend, ~52 test files)
```bash
cd backend
source venv/bin/activate
pytest app/tests/                                       # full suite
pytest app/tests/test_api.py                            # one file
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid  # single test
```
- Tests run against **in-memory SQLite** via a `TestClient` (see `app/tests/conftest.py`); `SKIP_DB_INIT=1` and `SKIP_MCP_LIFESPAN=1` keep the app lifespan from touching Postgres/the MCP manager.
- The venv **must have `mcp` installed** or the whole suite fails to collect — but re-pin `starlette<0.37` afterward (see `requirements.txt` comments).
- Adding a new test file that does several client POSTs can trip the rate limiter and **429 unrelated later tests** — include the autouse rate-limiter reset fixture.
- `pytest-rerunfailures` absorbs a few documented suite-isolation flakes; real failures still fail all reruns.

## Architecture

Layered backend: **`api/endpoints/` (routes) → `services/` (logic) → `models/database.py` (SQLAlchemy)**. Frontend is React Query for all server state (no Redux/Context store) with a **pattern-based view system** (`components/Patterns/`) that renders a project phase's data by pattern (wizard, ordered list, card grid, screenplay editor, scene workspace, …).

### Backend (`backend/app/`)

Entry point: `main.py` — FastAPI app. Middleware stack (added bottom-up, so execution order is): `LoggingMiddleware` → `SecurityMiddleware` → `RequestSizeLimitMiddleware` (25MB) → `RateLimitMiddleware` (600 req/min/IP) → `ApiKeyRateLimitMiddleware` (1000/key). CORS is added last. The app **lifespan** composes the mounted MCP sub-app's lifespan and runs `init_db()` (schema + boot-time migrations).

- `api/endpoints/` — Route handlers. Core: `projects.py`, `sections.py`, `review.py`, `auth.py`, `socratic.py`. Template pipeline: `templates.py`, `phase_data.py`, `list_items.py`, `wizards.py`, `ai_chat.py`. Breakdown/production: `breakdown.py`, `breakdown_chat.py`, `shots.py`, `media.py`, `storyboard.py`. Series: `shows.py`, `seasons.py`. Library: `books.py`, `snippets.py`, `snippet_manager.py`, `agents.py`, `chat.py`.
- `api/dependencies.py` — DI for DB sessions and auth. `authenticate_token()` is shared by REST (`get_current_user`) and the MCP server; in development the literal `mock-token` resolves to a mock user, and `sa_<key>` API keys authenticate via the key gateway.
- `models/database.py` — SQLAlchemy models (~40 tables). See Data Model below.
- `models/schemas.py` — Pydantic v2 request/response schemas with field validators.
- `services/` — `ai_provider.py` (unified OpenAI/Anthropic wrapper, prompt caching), `openai_service.py`, `template_ai_service.py`, `socratic_service.py`, `rag_service.py` + `embedding_service.py` (pgvector retrieval), `book_processing_service.py` + `knowledge_extraction_service.py` (ingest books → chunks → concepts), `doctrine_service.py` (inject craft concepts into generation), `agent_service.py` / `agent_templates.py` / `agent_review_middleware.py` / `pipeline_composer.py` (multi-agent review), `breakdown_service.py`, `shotlist_generation_service.py`, `imagen_service.py` / `media_service.py` (storyboard images/media), `vapai_service.py` (Send-to-vapai bridge), `document_service.py`, `db_migrator.py`.
- `mcp_server/` — In-process MCP server (`server.py`, `auth.py`, `session.py`, `context.py`, `jobs.py`) with tool modules under `tools/` (`core.py`, `screenwriting.py`, `breakdown.py`, `shotlist.py`, `management.py`). Auth reuses the `sa_<key>` gateway via a `TokenVerifier`; `/mcp` is exempt from the buffering middleware stack.
- `middleware.py` — Rate limiting (in-memory), request size limits, security headers.
- `exceptions.py` — Custom exception hierarchy mapped to HTTP status codes.
- `utils/validators.py` — Input validation and HTML sanitization.
- `config.py` — Pydantic Settings from env vars.
- `templates/` — Per-format JSON definitions (`short_movie.json`, `sketch.json`, `episode.json`, `vertical_drama.json`, plus `shared/write_phase.json`) and `registry.py`.
- `migrations/` — `init_db.sql` (baseline) + numbered `.sql` files, plus `migrations/delta/NNN_*.sql` applied in order at boot by `db_migrator.py` against `schema_migrations`.

API route prefixes: `/api/auth`, `/api/projects` (also mounts socratic), `/api/sections`, `/api/review`, `/api/books` (also snippets), `/api/snippets`, `/api/agents`, `/api/chat`, `/api/templates`, `/api/phase-data`, `/api/list-items`, `/api/wizards`, `/api/ai`, `/api/breakdown`, `/api/breakdown-chat`, `/api/shots`, `/api/media`, `/api/storyboard`, `/api/shows`, `/api` (seasons/slots). Health at `/health`, MCP at `/mcp`, uploaded media served from `/media`. OpenAPI docs at `/docs`.

### Frontend (`frontend/src/`)

Entry: `main.tsx` → `App.tsx` (React Query provider + BrowserRouter, 5-min stale time). Routes are auth-gated by `ProtectedRoute`:

- `/login`, `/register` — public
- `/`, `/projects` → `ProjectList`
- `/projects/:projectId` → `Editor`
- `/projects/:projectId/:phase[/:subsectionKey[/:itemId]]` → `ProjectWorkspace` (phase-driven, pattern-based views)
- `/projects/:projectId/breakdown` → `BreakdownLayout`; `.../breakdown/elements/:elementId` → `ElementDetailPage`
- `/projects/:projectId/storyboard` → `StoryboardView`
- `/books` → `BookManager`, `/snippets` → `SnippetManager`
- `/shows/:showId` → `ShowDetail`
- `/settings/profile`, `/settings/api-keys`

Key modules:
- `lib/api.tsx` — Fetch wrapper. 30s default timeout (`API_TIMEOUT`), 2-min chat/review timeout (`CHAT_TIMEOUT`), long-running calls use up to 300s. Bearer token from `localStorage` (`auth_token`), falls back to `mock-token`.
- `lib/constants.ts` — All magic numbers, `FRAMEWORK_CONFIG`, `SECTION_CONFIG`, query keys, feature flags (e.g. `VAPAI_ENABLED`).
- `lib/section-config.ts`, `lib/textHighlight.ts`, `lib/shotOverlay.ts`, `lib/utils.ts`, `lib/auth.ts` — helpers.
- `types/index.ts`, `types/template.ts` — TS interfaces mirroring backend schemas.
- `components/` — `Patterns/` (pattern-based phase views), `Workspace/` (phase navigation, series nav, content area), `Breakdown/` (elements, shots, shotlist, media, chat), `Storyboard/`, `Shows/`, `Books/`, `Snippets/`, `Editor/`, `Projects/`, `Auth/`, `Settings/`, `Layout/`, `UI/`, `Shared/`.
- `hooks/useKeyboardShortcuts.tsx` — Cmd/Ctrl+S (save), Cmd/Ctrl+Enter (AI review).

### Data Model (`models/database.py`)

Roughly 40 tables. Key clusters:

- **Auth:** `User`, `ApiKey` (`sa_<key>` gateway with usage counts).
- **Series:** `Show` → `Season` → `EpisodeSlot` (season map), with vapai linkage columns. Shows carry a "bible."
- **Project pipeline:** `Project` (title, framework, template_type, owner_id) → `Section` → `ChecklistItem`; plus `PhaseData` and `ListItem` for template-driven phase content, `SocraticQuestion`, `WizardRun`, and `ScreenplayContent` (the generated script; **ordered by `episode_index` only — never by row order**, see Concurrency/Ordering below).
- **AI/chat:** `AISession`/`AIMessage`, `ChatSession`/`ChatMessage`, `Agent`/`AgentBook`/`AgentPipelineMap`.
- **Knowledge/RAG:** `Book` → `BookChunk` (pgvector), `Concept`/`ConceptRelationship` (knowledge graph), `Snippet`.
- **Breakdown/production:** `BreakdownElement` → `ElementSceneLink`, `BreakdownRun`, `Shot` → `ShotElement`, `AssetMedia`, `StoryboardFrame`.

Enums: `Framework` (three_act, save_the_cat, hero_journey — legacy), `TemplateType` (short_movie, sketch, episode, vertical_drama), `PhaseType` (idea, story, scenes, write), `BreakdownCategory` (character, location, prop, wardrobe, vehicle, set_dressing, animal, sfx, makeup_hair, extras), plus `SectionType`, `ChecklistStatus`, `BookStatus`, `RelationshipType`, `AgentType`.

**Templates vs. Frameworks:** New projects run on the **template + phase** system (`TemplateType` → phases Idea/Story/Scenes/Write). The older `Framework` enum is legacy. **Adding a template is more than a JSON file** — it needs: the JSON in `templates/`, a `TemplateType` enum value (Pydantic + Postgres enum), an `init_db`/delta migration for the Postgres enum value, `test_template_formats` guard updates, and frontend icon maps (×2). See the `adding-a-template-checklist` memory.

## Key Conventions

- Backend dev auth token is `mock-token` (only honored when `ENVIRONMENT=development`) — tests use `Bearer mock-token`.
- Conventional commits with scopes: `feat(scenes):`, `fix(seasons):`, `chore:`, `docs:`.
- Vite proxies `/api` → `http://localhost:8000` in dev (override with `VITE_PROXY_TARGET`).
- Tailwind theming via HSL CSS variables (`tailwind.config.js`).
- Frontend server state is React Query (5-min stale time), not Redux/Context.
- Backend `PYTHONPATH=/app` (handled by the Dockerfile).
- Boot-time DB migrations: add idempotent `backend/migrations/delta/NNN_description.sql`; it's applied once and recorded in `schema_migrations`.
- **Auto-push:** in this project, commit + push directly to `main` after tests/typecheck pass, without asking (until told otherwise).

## Concurrency / Ordering Gotchas

- **`ScreenplayContent` has no reliable row order.** Always join/assemble episodes by `episode_index`, never positionally — assuming row order has caused real bugs more than once.
- Rate limiting, response caching (`CACHE_TTL`, 15 min), and API-key counters are **in-memory** — they do not survive restarts and won't scale horizontally as-is.

## Deploy (prod)

- **Backend:** Railway — `https://web-production-73857.up.railway.app` (`/health` → 200). Start command lives in the Railway dashboard, `railway.json` in `backend/`, `targetPort=8000`. The app **won't import without an AI key**; migrations apply on boot.
- **Frontend:** Vercel — `https://guion.vapai.studio` (also `screenwriting-assistant-lake.vercel.app`).
- **CORS** is locked to the prod frontend via `ALLOWED_ORIGINS`; a domain not listed there yields "Failed to fetch" in the browser.

## Environment Variables

Backend (see `backend/.env.example.txt`): `DATABASE_URL`, `AI_PROVIDER` (anthropic|openai), `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `SECRET_KEY`, `ADMIN_EMAILS` (library write gate), `ALLOWED_ORIGINS`, `EMBEDDING_MODEL`, `ENVIRONMENT`, `PORT`, MCP (`MCP_BASE_URL`, `MCP_DNS_REBINDING_PROTECTION`), Imagen (`GOOGLE_CLOUD_PROJECT`, `IMAGEN_MODEL`, `IMAGEN_REGION`), vapai bridge (`VAPAI_MCP_URL`, `VAPAI_MCP_API_KEY`, `VAPAI_WEB_URL`, `VAPAI_TIMEOUT_SECONDS`, `VAPAI_PROJECT_TYPE`), plus tuning knobs (`MAX_TOKENS`, `CACHE_TTL`, screenplay-critique and doctrine flags).

Frontend (see `frontend/.env.example.txt`): `VITE_API_URL`, `VITE_PROXY_TARGET`, `VITE_VAPAI_ENABLED`.
