# Codebase Structure

**Analysis Date:** 2026-03-01

## Directory Layout

```
screenwriting-assistant/
├── backend/                          # FastAPI Python backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app initialization
│   │   ├── db.py                     # Database engine, session factory, initialization
│   │   ├── config.py                 # Pydantic Settings with environment variables
│   │   ├── exceptions.py             # Custom exception hierarchy
│   │   ├── middleware.py             # Logging, Security, Rate Limit, Request Size middlewares
│   │   ├── api_docs.py               # Custom OpenAPI documentation
│   │   ├── api/
│   │   │   ├── dependencies.py       # Dependency injection (get_db, get_current_user)
│   │   │   └── endpoints/            # Route handlers
│   │   │       ├── projects.py       # Project CRUD and v2 template-based creation
│   │   │       ├── sections.py       # Section CRUD
│   │   │       ├── review.py         # AI review endpoint (legacy)
│   │   │       ├── phase_data.py     # Phase data CRUD and readiness checks
│   │   │       ├── list_items.py     # List item CRUD and reordering
│   │   │       ├── ai_chat.py        # AI chat sessions and message streaming
│   │   │       ├── wizards.py        # Wizard execution and result application
│   │   │       ├── chat.py           # Agent chat sessions
│   │   │       ├── agents.py         # Agent CRUD and book linking
│   │   │       ├── books.py          # Book upload, processing, concept retrieval
│   │   │       ├── templates.py      # Template listing and retrieval
│   │   │       └── auth.py           # Authentication (token, magic link)
│   │   ├── models/
│   │   │   ├── database.py           # SQLAlchemy ORM models
│   │   │   └── schemas.py            # Pydantic v2 request/response schemas with validators
│   │   ├── services/                 # Business logic
│   │   │   ├── openai_service.py     # Framework-aware prompts, in-memory response caching
│   │   │   ├── ai_provider.py        # OpenAI/Anthropic chat completion abstraction
│   │   │   ├── auth_service.py       # JWT verification, mock auth for dev
│   │   │   ├── rag_service.py        # Retrieval-augmented generation
│   │   │   ├── agent_service.py      # Agent prompt generation and execution
│   │   │   ├── document_service.py   # Document parsing and processing
│   │   │   ├── book_processing_service.py  # PDF extraction, chunking, embedding
│   │   │   ├── embedding_service.py  # Text embedding via OpenAI
│   │   │   ├── knowledge_extraction_service.py  # Concept extraction from chunks
│   │   │   ├── template_ai_service.py  # Template-aware AI generation
│   │   │   └── agent_templates.py    # Agent system prompt templates
│   │   ├── utils/
│   │   │   ├── validators.py         # Input validation, HTML sanitization
│   │   │   └── __init__.py
│   │   ├── templates/                # Template configuration system
│   │   │   ├── registry.py           # Template registry and loader
│   │   │   ├── __init__.py
│   │   │   └── shared/
│   │   │       ├── prompts/          # AI prompt templates
│   │   │       └── __init__.py
│   │   └── tests/                    # Unit and integration tests
│   │       ├── conftest.py           # pytest fixtures
│   │       ├── test_api.py           # API endpoint tests
│   │       └── test_validators.py    # Validator tests
│   ├── migrations/                   # Database migration files (SQL)
│   ├── uploads/                      # Generated directory for uploaded files
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Container image definition
│
├── frontend/                         # React + TypeScript frontend
│   ├── src/
│   │   ├── main.tsx                  # React entry point
│   │   ├── App.tsx                   # Main router and QueryClient setup
│   │   ├── index.css                 # Global styles
│   │   ├── components/
│   │   │   ├── Layout/
│   │   │   │   ├── Layout.tsx        # Main layout wrapper
│   │   │   │   └── Header.tsx        # Top navigation bar
│   │   │   ├── Projects/
│   │   │   │   ├── ProjectList.tsx   # Project listing with create modal
│   │   │   │   ├── ProjectCard.tsx   # Individual project card
│   │   │   │   └── CreateProjectModal.tsx  # Project creation form
│   │   │   ├── Editor/               # Legacy editor components
│   │   │   │   ├── Editor.tsx        # Main editor for legacy projects
│   │   │   │   ├── SectionEditor.tsx # Individual section editor
│   │   │   │   ├── Checklist.tsx     # Checklist item manager
│   │   │   │   ├── ReviewPanel.tsx   # AI review display
│   │   │   │   └── ChatSidebar.tsx   # Chat sidebar for editor
│   │   │   ├── Workspace/            # Template-based workspace (new system)
│   │   │   │   ├── ProjectWorkspace.tsx  # Main workspace router
│   │   │   │   ├── PhaseNavigation.tsx   # Phase switcher
│   │   │   │   ├── SubsectionSidebar.tsx # Subsection navigation
│   │   │   │   ├── ContentArea.tsx       # Main content renderer
│   │   │   │   └── WizardPanel.tsx       # Wizard execution and results
│   │   │   ├── Patterns/             # Dynamic view components (pluggable)
│   │   │   │   ├── CardGridView.tsx      # Grid layout for card items
│   │   │   │   ├── IndividualEditorView.tsx  # Single editor per item
│   │   │   │   ├── OrderedListView.tsx   # Numbered list view
│   │   │   │   ├── PlaceholderView.tsx   # Empty state view
│   │   │   │   ├── RepeatableCardsView.tsx  # Repeatable card set
│   │   │   │   ├── StructuredFormView.tsx   # Form with field definitions
│   │   │   │   └── WizardView.tsx        # Step-by-step wizard
│   │   │   ├── Books/
│   │   │   │   └── BookManager.tsx   # Book upload and management
│   │   │   ├── Shared/
│   │   │   │   ├── AIActionBar.tsx   # AI action buttons (fill blanks, notes)
│   │   │   │   ├── FieldRenderer.tsx # Dynamic form field renderer
│   │   │   │   ├── SidebarChat.tsx   # Agent/AI chat sidebar
│   │   │   │   └── FieldError.tsx    # Field-level error display
│   │   │   └── UI/                   # Primitive UI components
│   │   │       ├── Button.tsx        # Styled button
│   │   │       ├── Input.tsx         # Styled input
│   │   │       ├── Card.tsx          # Card container
│   │   │       ├── Modal.tsx         # Modal dialog
│   │   │       ├── ResizablePanel.tsx # Resizable split panel
│   │   │       └── [other primitives]
│   │   ├── hooks/
│   │   │   └── useKeyboardShortcuts.tsx # Keyboard shortcut handler (Cmd/Ctrl+S, etc.)
│   │   ├── lib/
│   │   │   ├── api.tsx               # API client with fetch wrapper, auth tokens
│   │   │   ├── constants.ts          # Magic numbers, framework configs, feature flags
│   │   │   ├── section-config.ts     # Section type definitions
│   │   │   ├── utils.ts              # Utility helpers (formatting, validation)
│   │   │   └── [domain-specific configs]
│   │   ├── types/
│   │   │   ├── index.ts              # Core type definitions (Project, Section, etc.)
│   │   │   └── template.ts           # Template type definitions
│   │   └── vite-env.d.ts             # Vite environment type declarations
│   ├── public/                       # Static assets
│   ├── package.json                  # npm dependencies
│   ├── tsconfig.json                 # TypeScript configuration
│   ├── vite.config.ts                # Vite build configuration
│   ├── tailwind.config.js            # Tailwind CSS theming
│   └── Dockerfile                    # Container image definition
│
├── migrations/                       # Database migration SQL files
│   └── init_db.sql                   # Schema initialization (single source of truth)
│
├── docker-compose.yml                # Multi-container orchestration (backend, frontend, postgres)
├── CLAUDE.md                         # Project instructions for Claude
├── package.json                      # Root-level npm workspace config
└── [config files]
```

## Directory Purposes

**`backend/app/`:**
- Purpose: Main Python application code
- Contains: All backend logic organized by functional domain (API, services, models)
- Key files: `main.py` (entry), `config.py` (settings), `db.py` (database)

**`backend/app/api/`:**
- Purpose: HTTP API layer
- Contains: Route handlers grouped by domain (projects, sections, templates, etc.)
- Key files: `dependencies.py` (DI configuration), `endpoints/` (routers)

**`backend/app/models/`:**
- Purpose: Data representation and validation
- Contains: SQLAlchemy ORM models (`database.py`), Pydantic schemas (`schemas.py`)
- Key pattern: Models define structure, schemas validate input

**`backend/app/services/`:**
- Purpose: Business logic and external integrations
- Contains: AI provider abstraction, book processing, knowledge extraction, RAG
- Key pattern: Service classes encapsulate domain logic, called by endpoints

**`backend/app/templates/`:**
- Purpose: Template configuration system for flexible project structures
- Contains: JSON template definitions, registry loader, prompt templates
- Key pattern: Declarative configuration driving UI and scaffolding

**`frontend/src/components/`:**
- Purpose: React component tree
- Contains: Layout, pages, features, UI primitives
- Key pattern: Components organized by feature domain, UI primitives in separate folder

**`frontend/src/components/Workspace/`:**
- Purpose: New template-based project editing interface
- Contains: ProjectWorkspace (router), phase/subsection navigation, content area
- Key pattern: Dynamically renders views based on template config, not hardcoded sections

**`frontend/src/components/Patterns/`:**
- Purpose: Pluggable view components that render template subsections
- Contains: Different layout strategies (grid, list, form, wizard)
- Key pattern: Subsection.view_type field selects which component to use

**`frontend/src/lib/`:**
- Purpose: Utilities and configuration
- Contains: API client, constants, helpers
- Key files: `api.tsx` (fetch wrapper), `constants.ts` (all magic numbers)

**`frontend/src/types/`:**
- Purpose: TypeScript type definitions
- Contains: Interfaces mirroring backend schemas
- Key pattern: Types stay in sync with Pydantic models manually (no codegen)

**`migrations/`:**
- Purpose: Database schema versioning
- Contains: SQL migration files (currently single `init_db.sql`)
- Note: Single source of truth; future migrations added here

## Key File Locations

**Entry Points:**
- Backend: `backend/app/main.py` - FastAPI app creation, middleware setup
- Frontend: `frontend/src/main.tsx` - React DOM mount
- Database: `backend/app/db.py` - Session factory, engine creation
- API routes: All in `backend/app/api/endpoints/` grouped by resource

**Configuration:**
- Backend: `backend/app/config.py` - Pydantic Settings, environment loading
- Frontend: `frontend/src/lib/constants.ts` - API URLs, timeouts, feature flags
- Build: `frontend/vite.config.ts`, `backend/requirements.txt`, `docker-compose.yml`
- Templates: `backend/app/templates/` - Template JSON configs and registry

**Core Logic:**
- Projects: `backend/app/api/endpoints/projects.py` (CRUD), `backend/app/models/database.py` (model)
- Sections: `backend/app/api/endpoints/sections.py`, legacy three-act structure
- Phase Data: `backend/app/api/endpoints/phase_data.py`, template-based subsection content
- AI: `backend/app/services/openai_service.py`, `ai_provider.py`, `rag_service.py`
- Books: `backend/app/services/book_processing_service.py`, `embedding_service.py`

**Testing:**
- Backend: `backend/app/tests/` - `conftest.py` (fixtures), `test_api.py`, `test_validators.py`
- Frontend: No test files currently in repo; components would go alongside source

**Utilities:**
- Validation: `backend/app/utils/validators.py` - Input sanitization, constraints
- Type definitions: `frontend/src/types/index.ts`, `frontend/src/types/template.ts`
- API client: `frontend/src/lib/api.tsx` - ~600 lines covering all endpoints

## Naming Conventions

**Files:**
- Python: snake_case (e.g., `openai_service.py`, `get_current_user()`)
- TypeScript: camelCase or PascalCase for components (e.g., `ProjectWorkspace.tsx`, `useKeyboardShortcuts.tsx`)
- Endpoints: RESTful lowercase with dashes (e.g., `/api/projects/`, `/api/phase-data/`)

**Directories:**
- Feature-based: `Projects/`, `Books/`, `Workspace/` (group by domain)
- Layer-based in backend: `api/`, `models/`, `services/`, `utils/`
- Plural for collections: `endpoints/`, `migrations/`, `components/`, `services/`

**Functions:**
- Backend: `verb_noun` pattern (e.g., `validate_project_title()`, `get_current_user()`)
- Frontend: React hooks start with `use` (e.g., `useKeyboardShortcuts()`)
- Async: `async def` in Python, `async function` in TS

**Variables:**
- Backend: snake_case throughout (DB, config, models)
- Frontend: camelCase (props, state, constants in lowercase)
- Constants: UPPER_CASE in both (e.g., `API_TIMEOUT`, `MAX_SECTION_LENGTH`)

**Database:**
- Tables: plural, snake_case (e.g., `projects`, `phase_data`, `list_items`)
- Columns: snake_case (e.g., `owner_id`, `created_at`, `ai_suggestions`)
- Enums: uppercase values (e.g., `PENDING`, `COMPLETED`)

**API Routes:**
- Resource-based: `/api/{resource}/` (GET all), `/api/{resource}/{id}` (GET one)
- Nested: `/api/{parent}/{parent_id}/{child}/` (GET children)
- Actions: `/api/{resource}/{id}/{action}` (e.g., `/api/wizards/{id}/apply`)
- Batch: `/api/{resource}/reorder` (POST with list of items)

## Where to Add New Code

**New Feature (e.g., character manager):**
- Backend endpoint: `backend/app/api/endpoints/characters.py` - new router
- Database model: Add class to `backend/app/models/database.py`
- Schema: Add Pydantic models to `backend/app/models/schemas.py`
- Service: `backend/app/services/character_service.py` if complex logic needed
- Register router: Add to `backend/app/main.py` app.include_router()

- Frontend component: `frontend/src/components/Characters/CharacterManager.tsx`
- Type definitions: Add to `frontend/src/types/index.ts`
- API client: Add methods to `frontend/src/lib/api.tsx`
- Routes: Add to `frontend/src/App.tsx` Routes

**New Component (UI element):**
- Reusable primitive: `frontend/src/components/UI/{ComponentName}.tsx`
- Feature-specific: `frontend/src/components/{Feature}/{ComponentName}.tsx`
- Ensure: Props typed, accessibility attributes, Tailwind styling consistent

**New Pattern (view variant):**
- File: `frontend/src/components/Patterns/{ViewTypeName}View.tsx`
- Signature: `export function {ViewType}View({ subsectionConfig, phaseData, ... })`
- Register: Update template wizard_config to reference new view_type
- Render: ContentArea component uses `subsectionConfig.view_type` to select

**New Template:**
- File: `backend/app/templates/{template_name}.json` or Python config
- Schema: Define phases, subsections, field schemas, view types
- Registry: Add to `backend/app/templates/registry.py` get_template()
- Usage: Can be selected during project creation

**Utilities (helpers):**
- Backend: `backend/app/utils/{domain}.py` (e.g., `date_utils.py`, `text_utils.py`)
- Frontend: `frontend/src/lib/{domain}.ts` (e.g., `formatting.ts`, `validation.ts`)
- Pattern: Pure functions, well-typed, documented

**Tests:**
- Unit: `backend/app/tests/test_{module}.py` (one per module)
- Integration: `backend/app/tests/test_api.py` (endpoint tests)
- Fixtures: `backend/app/tests/conftest.py` (shared test data)
- Frontend: Would be co-located with components (e.g., `Component.test.tsx`)

## Special Directories

**`backend/migrations/`:**
- Purpose: Database schema versioning
- Generated: No (manually created)
- Committed: Yes
- Usage: Run once on deployment via init_db() or migrations tool
- Note: Currently single `init_db.sql`; adopt Alembic for future migrations

**`backend/uploads/`:**
- Purpose: Temporary storage for uploaded files (PDFs, etc.)
- Generated: Yes (created at runtime)
- Committed: No (in .gitignore)
- Usage: Books uploaded here during processing, chunks extracted, file optionally retained

**`frontend/public/`:**
- Purpose: Static assets served as-is (favicon, logo, etc.)
- Generated: No
- Committed: Yes
- Usage: Referenced in index.html, bundled into dist/

**`backend/app/templates/shared/prompts/`:**
- Purpose: AI prompt templates for different operations
- Generated: No
- Committed: Yes
- Usage: Loaded by services, interpolated with project/section context

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by GSD commands)
- Committed: Yes
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md

**`migrations/`:**
- Purpose: Database migration files
- Generated: No (manually written)
- Committed: Yes
- Current: Single `init_db.sql` with full schema
- Future: Adopt Alembic for incremental migrations
