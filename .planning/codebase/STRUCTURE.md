# Codebase Structure

**Analysis Date:** 2026-03-06

## Directory Layout

```
screenwriting-assistant/
├── backend/                    # FastAPI Python backend
│   ├── app/                    # Application package
│   │   ├── api/                # HTTP layer
│   │   │   ├── endpoints/      # Route handlers (one file per domain)
│   │   │   └── dependencies.py # DI for auth + DB sessions
│   │   ├── models/             # Data models
│   │   │   ├── database.py     # SQLAlchemy ORM models + enums
│   │   │   └── schemas.py      # Pydantic v2 request/response schemas
│   │   ├── services/           # Business logic + AI orchestration
│   │   ├── templates/          # JSON template definitions (data-driven UI)
│   │   │   ├── shared/         # Shared template fragments + prompts
│   │   │   │   └── prompts/    # Reusable AI prompt templates
│   │   │   ├── micro_drama.json
│   │   │   ├── short_movie.json
│   │   │   └── registry.py     # Template loading + lookup functions
│   │   ├── utils/              # Input validation + sanitization
│   │   ├── tests/              # Backend test suite
│   │   ├── main.py             # FastAPI app + middleware + router registration
│   │   ├── db.py               # SQLAlchemy engine + session factory
│   │   ├── config.py           # Pydantic Settings (env var loading)
│   │   ├── middleware.py       # Custom middleware stack
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   └── api_docs.py         # OpenAPI schema customization
│   ├── migrations/             # Raw SQL migration files
│   ├── uploads/                # User-uploaded book files (runtime)
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Backend container build
│   └── venv/                   # Local virtualenv (not committed)
├── frontend/                   # React + TypeScript SPA
│   ├── src/
│   │   ├── components/         # React components by domain
│   │   │   ├── Books/          # Book management UI
│   │   │   ├── Editor/         # Legacy framework editor
│   │   │   ├── Layout/         # App shell (Header, Layout)
│   │   │   ├── Patterns/       # Template UI pattern views
│   │   │   ├── Projects/       # Project list + creation
│   │   │   ├── Shared/         # Cross-cutting components
│   │   │   ├── Snippets/       # Snippet management UI
│   │   │   ├── UI/             # Primitive UI components
│   │   │   └── Workspace/      # Template workspace orchestration
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # Utilities, API client, constants
│   │   ├── types/              # TypeScript type definitions
│   │   ├── App.tsx             # Root component with routes
│   │   ├── main.tsx            # React DOM entry point
│   │   └── index.css           # Global CSS + Tailwind directives
│   ├── public/                 # Static assets
│   ├── dist/                   # Built output (not committed)
│   ├── package.json            # NPM dependencies + scripts
│   ├── vite.config.ts          # Vite build + dev proxy config
│   ├── Dockerfile              # Frontend container build
│   └── tailwind.config.js      # Tailwind CSS configuration
├── docker-compose.yml          # Multi-service orchestration
├── CLAUDE.md                   # Project instructions for Claude Code
└── .planning/                  # GSD planning documents
    ├── codebase/               # Architecture + convention docs
    ├── phases/                 # Phase plans + execution logs
    └── research/               # Research documents
```

## Directory Purposes

**`backend/app/api/endpoints/`:**
- Purpose: One FastAPI router per domain; each file exports a `router = APIRouter()`
- Contains: Route handler functions using `Depends(get_db)` and `Depends(get_current_user)`
- Key files:
  - `projects.py` — Project CRUD + v2 template-based creation
  - `phase_data.py` — PhaseData CRUD + readiness checks
  - `list_items.py` — ListItem CRUD + reordering
  - `books.py` — Book upload + processing + status
  - `chat.py` — Agent chat sessions + streaming messages
  - `ai_chat.py` — Template AI sessions + streaming + fill-blanks + give-notes
  - `wizards.py` — Wizard run + apply results
  - `agents.py` — Agent CRUD + book linking + seed defaults + tag listing
  - `snippet_manager.py` — Snippet edit + delete (at `/api/snippets`)
  - `snippets.py` — Book-scoped snippet listing (at `/api/books`)
  - `templates.py` — Template listing + detail
  - `sections.py` — Legacy section editing + checklist
  - `review.py` — Legacy AI section review
  - `auth.py` — Mock token + magic link auth

**`backend/app/services/`:**
- Purpose: All business logic, AI orchestration, and external service interaction
- Contains: Service classes and standalone functions; no HTTP concerns
- Key files:
  - `ai_provider.py` — Unified OpenAI/Anthropic abstraction (use this for all LLM calls)
  - `agent_service.py` — Multi-agent RAG chat + review orchestration
  - `rag_service.py` — Concept-first and semantic retrieval
  - `template_ai_service.py` — Wizard generation for all wizard types
  - `book_processing_service.py` — Full book ingestion pipeline
  - `knowledge_extraction_service.py` — GPT-4 concept extraction from chunks
  - `embedding_service.py` — OpenAI embedding generation
  - `document_service.py` — PDF/EPUB/TXT text extraction
  - `openai_service.py` — Legacy section review (framework-based)
  - `auth_service.py` — JWT + mock auth
  - `agent_templates.py` — Default agent seed configurations

**`backend/app/models/`:**
- Purpose: All data models — both ORM and API schemas
- `database.py` — 20+ SQLAlchemy model classes, all enums, the `SafeVector` type; this is the single source of truth for the data model
- `schemas.py` — Pydantic v2 models for request validation and response serialization

**`backend/app/templates/`:**
- Purpose: JSON template definitions that drive the entire template system UI
- `micro_drama.json` — Template for micro-drama format
- `short_movie.json` — Template for short movie format
- `shared/write_phase.json` — Shared write-phase definition used by multiple templates
- `registry.py` — `get_template()`, `list_templates()`, `get_template_subsections()` loading functions

**`backend/migrations/`:**
- Purpose: Raw SQL migration files applied manually to PostgreSQL
- Files: `init_db.sql`, `002_knowledge_graph.sql`, `003_template_system.sql`, `003_templates_overhaul.sql`, `004_agent_type_and_quality.sql`, `005_book_progress.sql`, `006_snippet_management.sql`, `007_snippets_table.sql`
- No Alembic — migrations run manually

**`frontend/src/components/Workspace/`:**
- Purpose: Template-system workspace orchestration
- `ProjectWorkspace.tsx` — Top-level workspace: fetches project + template, manages phase/subsection selection, renders `PhaseNavigation` + `SubsectionSidebar` + `ContentArea` + `SidebarChat`
- `ContentArea.tsx` — Switches on `ui_pattern` to render the correct Pattern view
- `PhaseNavigation.tsx` — Phase tab bar
- `SubsectionSidebar.tsx` — Left sidebar with subsection list

**`frontend/src/components/Patterns/`:**
- Purpose: One component per `ui_pattern` value from the template JSON
- `StructuredFormView.tsx` — Renders `fields` / `field_groups` as form inputs
- `CardGridView.tsx` — Grid of cards for `card_grid` pattern
- `RepeatableCardsView.tsx` — Add/remove/edit cards for `repeatable_cards`
- `WizardView.tsx` — Multi-step wizard with configuration + AI generation
- `OrderedListView.tsx` — Sortable list of `ListItem` records
- `IndividualEditorView.tsx` — Single-item detail editor (navigated via `itemId` URL param)
- `ScreenplayEditorView.tsx` — Screenplay-formatted text editor
- `PlaceholderView.tsx` — Fallback for unimplemented patterns (e.g., `analyzer`)

**`frontend/src/components/Shared/`:**
- Purpose: Cross-cutting components used across multiple domains
- `SidebarChat.tsx` — Dual-mode chat sidebar (template AI + agent chat) with SSE streaming, markdown rendering, field-update proposals
- `AIActionBar.tsx` — AI action buttons (fill blanks, give notes, analyze structure)
- `FieldRenderer.tsx` — Generic field rendering based on `FieldDef` from template config
- `MarkdownContent.tsx` — Markdown-to-HTML renderer for AI responses

**`frontend/src/components/Editor/`:**
- Purpose: Legacy framework-based project editor
- `Editor.tsx` — Main editor page (used by `/projects/:projectId` route)
- `SectionEditor.tsx` — Individual section text editor
- `Checklist.tsx` — ChecklistItem management
- `ReviewPanel.tsx` — AI review display
- `ChatSidebar.tsx` — Agent chat sidebar for legacy editor

**`frontend/src/components/Books/`:**
- Purpose: Book and agent management
- `BookManager.tsx` — Book upload, listing, processing status, agent management tabs
- `AgentManager.tsx` — Agent CRUD, book linking, tag-based agent configuration

**`frontend/src/components/Snippets/`:**
- Purpose: Snippet browsing and management
- `SnippetManager.tsx` — Book selector + snippet list page
- `SnippetCard.tsx` — Individual snippet display with edit/delete
- `SnippetSearchBar.tsx` — Search/filter bar for snippets

**`frontend/src/lib/`:**
- Purpose: Shared utilities, API client, configuration constants
- `api.tsx` — Single `api` object with typed methods for every backend endpoint
- `constants.ts` — All magic numbers, query keys, route paths, framework configs, feature flags, error messages, keyboard shortcuts
- `section-config.ts` — Legacy section configuration
- `utils.ts` — Utility helpers

**`frontend/src/types/`:**
- Purpose: TypeScript type definitions
- `index.ts` — Core types: `Project`, `Section`, `ChecklistItem`, `Book`, `Concept`, `Agent`, `ChatSession`, `ChatMessage`, `Snippet`, etc.
- `template.ts` — Template system types: `TemplateConfig`, `PhaseConfig`, `SubsectionConfig`, `FieldDef`, `UIPattern`, `PhaseDataResponse`, `ListItemResponse`, `AISessionResponse`, `WizardRunResponse`, `ProjectV2`

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI application creation + startup
- `frontend/src/main.tsx`: React DOM render
- `frontend/src/App.tsx`: Router + QueryClient setup

**Configuration:**
- `backend/app/config.py`: All backend settings (DB, AI, auth, CORS, file upload)
- `frontend/src/lib/constants.ts`: All frontend constants + query keys + routes
- `frontend/vite.config.ts`: Vite build + dev proxy to backend
- `docker-compose.yml`: Multi-service orchestration (frontend, backend, postgres)

**Core Logic:**
- `backend/app/services/ai_provider.py`: All LLM calls go through here
- `backend/app/services/agent_service.py`: Agent orchestration + RAG chat
- `backend/app/services/template_ai_service.py`: Wizard generation
- `backend/app/templates/registry.py`: Template loading
- `frontend/src/components/Workspace/ContentArea.tsx`: UI pattern routing
- `frontend/src/components/Shared/SidebarChat.tsx`: AI chat interface

**Data Model:**
- `backend/app/models/database.py`: All SQLAlchemy models (single file)
- `backend/app/models/schemas.py`: All Pydantic schemas (single file)
- `frontend/src/types/index.ts`: Core TypeScript interfaces
- `frontend/src/types/template.ts`: Template system TypeScript interfaces

**Testing:**
- `backend/app/tests/test_api.py`: API integration tests
- `backend/app/tests/test_validators.py`: Validator unit tests

## Naming Conventions

**Files:**
- Backend endpoints: `snake_case.py` matching the domain (e.g., `phase_data.py`, `list_items.py`, `snippet_manager.py`)
- Backend services: `snake_case_service.py` (e.g., `agent_service.py`, `rag_service.py`)
- Frontend components: `PascalCase.tsx` matching the export name (e.g., `ProjectWorkspace.tsx`, `SidebarChat.tsx`)
- Frontend lib: `camelCase.ts` or `kebab-case.ts` (e.g., `api.tsx`, `constants.ts`, `section-config.ts`)
- Frontend types: `camelCase.ts` (e.g., `index.ts`, `template.ts`)
- SQL migrations: `NNN_description.sql` (e.g., `002_knowledge_graph.sql`)

**Directories:**
- Backend: `snake_case` (e.g., `api/endpoints/`, `services/`, `templates/shared/`)
- Frontend components: `PascalCase` by domain (e.g., `Books/`, `Patterns/`, `Workspace/`, `Shared/`, `UI/`)
- Frontend non-components: `camelCase` (e.g., `lib/`, `hooks/`, `types/`)

## Where to Add New Code

**New API endpoint:**
1. Create route handler in `backend/app/api/endpoints/{domain}.py`
2. Add Pydantic schemas in `backend/app/models/schemas.py` if needed
3. Register router in `backend/app/main.py` with `app.include_router(..., prefix="/api/{domain}", tags=["{domain}"])`
4. Add corresponding API method to `frontend/src/lib/api.tsx`
5. Add query key to `QUERY_KEYS` in `frontend/src/lib/constants.ts`

**New template UI pattern:**
1. Create `frontend/src/components/Patterns/{PatternName}View.tsx`
2. Add the pattern string to `UIPattern` type in `frontend/src/types/template.ts`
3. Add a `case` to the switch in `frontend/src/components/Workspace/ContentArea.tsx`
4. Use the pattern in a template JSON file (e.g., `backend/app/templates/micro_drama.json`)

**New service (backend):**
1. Create `backend/app/services/{name}_service.py`
2. Use `from ..config import settings` for configuration
3. Use `from .ai_provider import chat_completion` for LLM calls (do not call OpenAI/Anthropic directly)
4. Import and use in endpoint files as needed

**New database model:**
1. Add SQLAlchemy model class to `backend/app/models/database.py`
2. Write SQL migration in `backend/migrations/NNN_description.sql`
3. Add Pydantic schemas to `backend/app/models/schemas.py`
4. Add TypeScript interface to `frontend/src/types/index.ts` or `frontend/src/types/template.ts`

**New frontend page/feature:**
1. Create component in the appropriate `frontend/src/components/{Domain}/` directory
2. Add route in `frontend/src/App.tsx` if it's a new page
3. Add route path to `ROUTES` in `frontend/src/lib/constants.ts`
4. Add navigation link in `frontend/src/components/Layout/Header.tsx`

**New template type:**
1. Create `backend/app/templates/{template_name}.json` following the structure of existing templates
2. Add enum value to `TemplateType` in `backend/app/models/database.py`
3. The registry auto-discovers JSON files, but verify it loads via `get_template()`
4. Add type to `TemplateType` in `frontend/src/types/template.ts`

**Shared/reusable frontend component:**
- Cross-domain: `frontend/src/components/Shared/`
- Primitive UI: `frontend/src/components/UI/`
- Hooks: `frontend/src/hooks/`
- Utilities: `frontend/src/lib/utils.ts`

## Special Directories

**`backend/uploads/`:**
- Purpose: Stores uploaded book files, organized by owner UUID subdirectories
- Generated: Yes (at runtime)
- Committed: No (`.gitignore` should exclude, but directory structure may be committed)

**`backend/migrations/`:**
- Purpose: Raw SQL schema migration files
- Generated: No (hand-written)
- Committed: Yes

**`backend/app/templates/`:**
- Purpose: JSON template definitions that drive the entire template system
- Generated: No (hand-authored)
- Committed: Yes
- Critical: Changes here affect both backend AI context and frontend UI rendering

**`frontend/dist/`:**
- Purpose: Vite production build output
- Generated: Yes (by `npm run build`)
- Committed: No

**`.planning/`:**
- Purpose: GSD planning and analysis documents
- Generated: Yes (by Claude Code mapping commands)
- Committed: Yes

---

*Structure analysis: 2026-03-06*
