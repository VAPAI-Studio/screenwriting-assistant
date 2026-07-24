# Codebase Structure

**Analysis Date:** 2026-07-24

## Directory Layout

```
screenwriting-assistant/
├── backend/
│   └── app/
│       ├── main.py                 # FastAPI entry: middleware, routers, /mcp + /media mounts, lifespan
│       ├── config.py               # Pydantic Settings from env vars
│       ├── db.py                   # Engine, SessionLocal, get_db(), init_db()→migrations
│       ├── middleware.py           # Logging/Security/RequestSize/RateLimit/ApiKeyRateLimit
│       ├── exceptions.py           # Custom exception hierarchy → HTTP codes
│       ├── api_docs.py             # Custom OpenAPI schema
│       ├── api/
│       │   ├── dependencies.py     # DB session + auth (mock / sa_ keys / JWT), require_admin
│       │   └── endpoints/          # Route handlers (one file per domain)
│       ├── services/               # Business logic + AI orchestration
│       ├── models/
│       │   ├── database.py         # SQLAlchemy models + enums (the data model)
│       │   └── schemas.py          # Pydantic v2 request/response schemas
│       ├── templates/              # Template JSONs + registry (short_movie/sketch/episode/vertical_drama)
│       ├── mcp_server/             # In-process MCP server (Streamable HTTP) + tools/
│       ├── utils/                  # validators, bible_context, episode_summary, screenplay_split
│       └── tests/                  # pytest suite (test_api.py, test_validators.py, ...)
├── frontend/
│   └── src/
│       ├── main.tsx                # React entry → App
│       ├── App.tsx                 # Router + React Query provider; route table
│       ├── components/             # Domain + pattern + UI components
│       ├── lib/                    # api.tsx (fetch client), constants.ts, auth.ts, utils
│       ├── hooks/                  # useKeyboardShortcuts
│       ├── types/                  # index.ts, template.ts (TS mirrors of backend)
│       └── index.css               # Tailwind entry + HSL theme vars
├── docker-compose.yml              # Postgres + backend + frontend
├── CLAUDE.md                       # Project guidance
├── mcp-guide.md / setup-guide.md / development-guide.md
└── requirements.txt / runtime.txt  # Railway deploy hints (backend)
```

## Directory Purposes

**`backend/app/api/endpoints/`:**
- Purpose: HTTP route handlers, one module per domain, registered in `main.py`.
- Contains: `projects.py`, `sections.py`, `review.py`, `auth.py`, `books.py`, `snippets.py`, `snippet_manager.py`, `agents.py`, `chat.py`, `templates.py`, `phase_data.py`, `list_items.py`, `wizards.py`, `ai_chat.py`, `breakdown.py`, `breakdown_chat.py`, `shots.py`, `media.py`, `storyboard.py`, `shows.py`, `seasons.py`, `socratic.py`.
- Key files: `projects.py` (project CRUD + phase), `wizards.py` (AI wizards, largest), `ai_chat.py` (AI generation surface), `shows.py`/`seasons.py` (continuity).

**`backend/app/services/`:**
- Purpose: Business logic + AI. Endpoints stay thin.
- Contains: `template_ai_service.py` (largest, per-template AI generation), `breakdown_service.py`, `shotlist_generation_service.py`, `agent_service.py`, `agent_review_middleware.py`, `rag_service.py`, `knowledge_extraction_service.py`, `book_processing_service.py`, `embedding_service.py`, `socratic_service.py`, `doctrine_service.py`, `pipeline_composer.py`, `vapai_service.py` (vapai-studio push), `ai_provider.py`/`openai_service.py`/`imagen_service.py`, `media_service.py`, `document_service.py`, `auth_service.py`, `db_migrator.py`, `agent_templates.py`.

**`backend/app/models/`:**
- Purpose: Data model + schemas.
- Key files: `database.py` (ORM models + `SafeVector` pgvector type + all enums), `schemas.py` (Pydantic v2).

**`backend/app/templates/`:**
- Purpose: Template definitions driving project scaffolding + the pattern editor.
- Key files: `registry.py` (loader + `$ref` resolution), `episode.json`, `short_movie.json`, `sketch.json`, `vertical_drama.json`, `shared/` (referenced phase fragments).

**`backend/app/mcp_server/`:**
- Purpose: MCP server exposing the production pipeline as agent tools.
- Key files: `server.py` (FastMCP + instructions + `mcp_app`), `auth.py` (`ApiKeyTokenVerifier`, `require_user`), `session.py`, `jobs.py`, `context.py`, `tools/{core,screenwriting,management,breakdown,shotlist}.py`.

**`frontend/src/components/`:**
- Purpose: All UI, grouped by domain.
- Subdirectories:
  - `Workspace/` — phase-based project editor shell: `ProjectWorkspace.tsx`, `ContentArea.tsx` (pattern dispatch), `PhaseNavigation.tsx`, `SubsectionSidebar.tsx`, `SeriesNav.tsx`, `EpisodeContextPanel.tsx`.
  - `Patterns/` — one component per `ui_pattern`: `StructuredFormView`, `CardGridView`, `RepeatableCardsView`, `WizardView`, `OrderedListView`, `IndividualEditorView`, `SceneWorkspaceView`, `ScreenplayEditorView`, `PlaceholderView`, plus `SceneCompareModal`.
  - `Breakdown/` — elements/shots/shotlist board: `BreakdownLayout`, `BreakdownPanel`, `ElementList`/`ElementCard`/`ElementDetailPage`, `ShotlistPanel`/`ShotRow`/`ShotProposalCard`, `AssetsPanel`, `MediaUploadZone`, staleness bars, `BreakdownChat`.
  - `Storyboard/` — `StoryboardView`, `ShotCard`, `FrameGalleryModal`.
  - `Shows/` — continuity UI: `ShowDetail`, `ShowCard`, `BibleEditor`/`BibleWizardModal`, `SeasonMap`/`SeasonMapWizardModal`, `EpisodeList`/`CreateEpisodeModal`, `SlotEditModal`/`ReconcileSlotModal`.
  - `Books/`, `Snippets/` — RAG knowledge management (`BookManager`, `SnippetManager`).
  - `Editor/` — legacy/section editor + chat: `Editor`, `SectionEditor`, `Checklist`, `ReviewPanel`, `ChatSidebar`, `SocraticPanel`, `EpisodeBreadcrumb`.
  - `Projects/` — `ProjectList`, project cards/modals.
  - `Shared/` — cross-cutting: `AIActionBar`, `FieldRenderer`, `MarkdownContent`, `SidebarChat`.
  - `Auth/`, `Settings/`, `Layout/`, `UI/` — auth pages/guard, profile + API keys, layout shell, UI primitives.

**`frontend/src/lib/`:**
- Purpose: Shared frontend infrastructure.
- Key files: `api.tsx` (fetch wrapper, 30s timeout, Bearer auth, all typed API methods — large), `constants.ts` (magic numbers, framework/section/template configs, `QUERY_KEYS`, feature flags), `auth.ts`, `section-config.ts`, `shotOverlay.ts`, `textHighlight.ts`, `utils.ts`.

**`frontend/src/types/`:**
- Purpose: TS interfaces mirroring backend schemas.
- Key files: `index.ts` (domain types), `template.ts` (`TemplateConfig`, `SubsectionConfig`, `ui_pattern`).

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app, routers, mounts, lifespan.
- `frontend/src/main.tsx` → `frontend/src/App.tsx`: SPA bootstrap + routes.
- `backend/app/mcp_server/server.py`: MCP app (`mcp_app`) mounted at `/mcp`.

**Configuration:**
- `backend/app/config.py`: Pydantic Settings (env vars).
- `frontend/vite.config.ts` / `frontend/src/lib/constants.ts`: dev proxy + app constants.
- `docker-compose.yml`, `backend/railway.json`: infra.

**Core Logic:**
- `backend/app/models/database.py`: data model.
- `backend/app/services/template_ai_service.py`: primary AI generation.
- `frontend/src/components/Workspace/ContentArea.tsx`: pattern dispatch.

**Testing:**
- `backend/app/tests/`: `test_api.py`, `test_validators.py`, `test_template_formats.py`, MCP integration tests.

## Naming Conventions

**Files:**
- Backend: `snake_case.py` (endpoints/services/utils). One domain per endpoint/service module.
- Frontend components: `PascalCase.tsx` (one component per file). Non-component libs: `camelCase.ts` / `kebab` (`section-config.ts`).
- Templates: `<template_id>.json` matching a `TemplateType` value.

**Directories:**
- Backend: lowercase (`api/endpoints`, `mcp_server`).
- Frontend components: `PascalCase` domain folders (`Breakdown`, `Workspace`, `Patterns`, `Shows`).

## Where to Add New Code

**New API endpoint:**
- Handler: `backend/app/api/endpoints/<domain>.py`; register the router in `backend/app/main.py` with an `/api/<domain>` prefix.
- Schemas: `backend/app/models/schemas.py`.
- Logic: `backend/app/services/<domain>_service.py`.

**New editor subsection / content type:**
- Add the subsection to the relevant `backend/app/templates/<template>.json` with a `ui_pattern`.
- If a new pattern is needed: add `frontend/src/components/Patterns/<Pattern>View.tsx` and a `case` in `frontend/src/components/Workspace/ContentArea.tsx`.
- Store content in generic `PhaseData` / `ListItem` (no new table) via `phase_data.py` / `list_items.py`.

**New template:**
- Follow the full checklist: `templates/<x>.json` + `TemplateType` enum (Pydantic + Postgres enum) + `init_db` + delta migration + `test_template_formats` guard + frontend icon maps (×2). Not just a JSON file.

**New data model:**
- Add the model to `backend/app/models/database.py` (owner-scoped `owner_id`; enum columns use `values_callable`).
- Add a delta migration under `backend/migrations/delta/` handled by `services/db_migrator.py`.

**New MCP tool:**
- Add to a group in `backend/app/mcp_server/tools/` and register in `server.py`; reuse existing services; use the job-poll pattern for long work.

**New frontend page:**
- Component under the matching `components/<Domain>/` folder; add a `<Route>` in `frontend/src/App.tsx` (wrap in `ProtectedRoute` unless public); add API methods to `lib/api.tsx` and `QUERY_KEYS` to `lib/constants.ts`.

**Shared UI:** `frontend/src/components/Shared/` (cross-domain) or `frontend/src/components/UI/` (primitives).

## Special Directories

**`backend/app/templates/shared/`:**
- Purpose: Phase fragments referenced via `$ref` from template JSONs (resolved by `registry.py`).
- Generated: No. Committed: Yes.

**`backend/app/media/` (settings.MEDIA_DIR, mounted `/media`):**
- Purpose: Uploaded media/storyboard files served statically.
- Generated: Yes (runtime uploads). Committed: No.

**`frontend/src/lib/api.tsx.bak`:**
- Purpose: Stale backup of the API client. Not imported; ignore.
- Committed: Yes (should be removed — see CONCERNS).

---

*Structure analysis: 2026-07-24*
