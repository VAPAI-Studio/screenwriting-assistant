# Codebase Structure

**Analysis Date:** 2026-03-11

## Directory Layout

```
screenwriting-assistant/
├── backend/                           # FastAPI Python backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app instantiation, router registration
│   │   ├── config.py                 # Pydantic Settings, env var loading
│   │   ├── db.py                     # SQLAlchemy engine, session factory
│   │   ├── middleware.py             # Custom middleware stack
│   │   ├── exceptions.py             # Custom exception hierarchy
│   │   ├── api_docs.py               # OpenAPI customization
│   │   ├── api/
│   │   │   ├── dependencies.py       # DI: get_db, get_current_user
│   │   │   └── endpoints/            # Route handlers by domain
│   │   │       ├── projects.py       # Project CRUD (v1 + v2)
│   │   │       ├── sections.py       # Section CRUD (legacy)
│   │   │       ├── review.py         # AI review endpoint
│   │   │       ├── phase_data.py     # Phase data CRUD, readiness
│   │   │       ├── list_items.py     # List item CRUD
│   │   │       ├── books.py          # Book upload, processing
│   │   │       ├── snippets.py       # Snippet extraction endpoints
│   │   │       ├── snippet_manager.py # Snippet CRUD
│   │   │       ├── agents.py         # Agent CRUD
│   │   │       ├── chat.py           # Chat session CRUD (legacy)
│   │   │       ├── ai_chat.py        # Multi-agent chat with RAG
│   │   │       ├── templates.py      # Template config endpoints
│   │   │       ├── wizards.py        # Wizard-driven generation
│   │   │       ├── auth.py           # Auth endpoints
│   │   │       └── endpoint.py       # Base endpoint utilities
│   │   ├── models/
│   │   │   ├── database.py           # SQLAlchemy ORM models
│   │   │   └── schemas.py            # Pydantic v2 request/response DTOs
│   │   ├── services/                 # Business logic layer
│   │   │   ├── openai_service.py     # Section review with caching
│   │   │   ├── template_ai_service.py # AI content generation for phases
│   │   │   ├── agent_service.py      # Multi-agent orchestration
│   │   │   ├── book_processing_service.py # PDF extraction, chunking
│   │   │   ├── knowledge_extraction_service.py # Concept + relationship extraction
│   │   │   ├── embedding_service.py  # Vector embedding wrapper
│   │   │   ├── rag_service.py        # RAG context retrieval
│   │   │   ├── document_service.py   # Document utilities
│   │   │   ├── ai_provider.py        # OpenAI/Anthropic abstraction
│   │   │   ├── auth_service.py       # JWT + mock auth
│   │   │   ├── agent_templates.py    # Agent prompt templates
│   │   │   └── __init__.py
│   │   ├── templates/                # Template definitions (JSON)
│   │   │   ├── registry.py           # Template loader
│   │   │   ├── short_movie.json      # Phase workflow template
│   │   │   ├── shared/
│   │   │   │   ├── write_phase.json  # Shared write phase definition
│   │   │   │   └── prompts/          # AI prompts for phases
│   │   │   └── __init__.py
│   │   ├── utils/
│   │   │   ├── validators.py         # Input validation, sanitization
│   │   │   └── __init__.py
│   │   ├── tests/                    # Pytest test suite
│   │   │   ├── conftest.py           # Fixtures, test config
│   │   │   ├── test_api.py           # API endpoint tests
│   │   │   ├── test_validators.py    # Validator tests
│   │   │   ├── test_snippets_api.py  # Snippet API tests
│   │   │   ├── test_snippet_extraction.py # Extraction tests
│   │   │   ├── test_snippet_manager.py # Manager tests
│   │   │   └── __init__.py
│   │   └── __init__.py
│   ├── migrations/                   # SQL migration files
│   │   ├── init_db.sql               # Initial schema
│   │   ├── 003_template_system.sql   # Template table schema
│   │   ├── 004_agent_type_and_quality.sql # Agent enhancements
│   │   └── 005_book_progress.sql     # Book progress tracking
│   ├── uploads/                      # User-uploaded files
│   ├── Dockerfile                    # Container image
│   ├── requirements.txt               # Python dependencies
│   ├── venv/                         # Virtual environment
│   └── main.py                       # Entry point (if standalone)
├── frontend/                          # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── main.tsx                  # React DOM mount point
│   │   ├── App.tsx                   # Router, QueryClient setup
│   │   ├── index.css                 # Global Tailwind styles
│   │   ├── components/               # React components by domain
│   │   │   ├── Layout/
│   │   │   │   ├── Layout.tsx        # Page wrapper with header
│   │   │   │   └── Header.tsx        # Navigation, user menu
│   │   │   ├── Projects/
│   │   │   │   ├── ProjectList.tsx   # Project listing page
│   │   │   │   ├── ProjectCard.tsx   # Project card component
│   │   │   │   └── CreateProjectModal.tsx # Create project form
│   │   │   ├── Editor/
│   │   │   │   ├── Editor.tsx        # Legacy section-based editor
│   │   │   │   ├── ChatSidebar.tsx   # Chat panel in editor
│   │   │   │   ├── SectionEditor.tsx # Individual section editor
│   │   │   │   ├── Checklist.tsx     # Checklist UI
│   │   │   │   └── ReviewPanel.tsx   # AI review display
│   │   │   ├── Workspace/
│   │   │   │   ├── ProjectWorkspace.tsx # Template-based workspace
│   │   │   │   ├── PhaseNavigation.tsx # Phase selector, progress
│   │   │   │   ├── SubsectionSidebar.tsx # Subsection list
│   │   │   │   ├── ContentArea.tsx   # Dynamic pattern renderer
│   │   │   │   └── AIActionBar.tsx   # AI generation controls
│   │   │   ├── Patterns/
│   │   │   │   ├── PlaceholderView.tsx # Empty state
│   │   │   │   ├── CardGridView.tsx  # Card grid layout
│   │   │   │   ├── StructuredFormView.tsx # Form with fields
│   │   │   │   ├── OrderedListView.tsx # Ordered list editor
│   │   │   │   ├── RepeatableCardsView.tsx # Add/remove cards
│   │   │   │   ├── ScreenplayEditorView.tsx # Screenplay formatting
│   │   │   │   └── WizardView.tsx    # Multi-step wizard
│   │   │   ├── Books/
│   │   │   │   ├── BookManager.tsx   # Book list and upload
│   │   │   │   ├── BookCard.tsx      # Book status card
│   │   │   │   ├── AgentManager.tsx  # Agent config UI
│   │   │   │   └── KnowledgeGraph.tsx # Concept visualization
│   │   │   ├── Snippets/
│   │   │   │   ├── SnippetManager.tsx # Snippet list, search
│   │   │   │   ├── SnippetCard.tsx   # Snippet display
│   │   │   │   └── SnippetSearchBar.tsx # Search filter
│   │   │   ├── Shared/
│   │   │   │   ├── SidebarChat.tsx   # Agent chat panel
│   │   │   │   ├── AIActionBar.tsx   # AI action buttons
│   │   │   │   ├── MarkdownContent.tsx # Markdown renderer
│   │   │   │   └── [other primitives]
│   │   │   └── UI/
│   │   │       ├── Button.tsx        # Styled button
│   │   │       ├── Input.tsx         # Styled input field
│   │   │       ├── Modal.tsx         # Modal dialog
│   │   │       ├── Card.tsx          # Card container
│   │   │       ├── ResizablePanel.tsx # Resizable panes
│   │   │       └── [other primitives]
│   │   ├── hooks/
│   │   │   └── useKeyboardShortcuts.tsx # Cmd/Ctrl+S, Cmd/Ctrl+Enter
│   │   ├── lib/
│   │   │   ├── api.tsx              # Fetch wrapper with Bearer auth
│   │   │   ├── constants.ts         # QUERY_KEYS, framework configs
│   │   │   └── utils.ts             # Helper functions
│   │   └── types/
│   │       ├── index.ts             # Enums + interfaces (v1 models)
│   │       └── template.ts          # Template config types (v2)
│   ├── public/
│   │   ├── index.html               # HTML entry point
│   │   └── favicon.ico
│   ├── Dockerfile                   # Container image
│   ├── package.json                 # NPM dependencies
│   ├── package-lock.json            # Locked versions
│   ├── tsconfig.json                # TypeScript compiler config
│   ├── tsconfig.node.json           # Node.js-specific ts config
│   ├── vite.config.ts               # Vite dev server + build config
│   ├── tailwind.config.js           # Tailwind CSS theme
│   └── postcss.config.js            # PostCSS plugins
├── .planning/
│   ├── codebase/
│   │   ├── ARCHITECTURE.md          # (this file)
│   │   ├── STRUCTURE.md             # (sibling)
│   │   └── [other analysis docs]
│   └── config.json                  # Planning orchestrator config
├── .claude/                         # Claude Code session cache
├── migrations/                      # Alembic-style SQL migrations
├── docker-compose.yml               # Full-stack container orchestration
├── CLAUDE.md                        # Project instructions
├── .env                             # Environment variables (never committed)
├── .env.docker.example              # Example Docker env vars
├── .gitignore                       # Git exclusions
├── readme.md                        # Project overview
├── setup-guide.md                   # Deployment guide
├── development-guide.md             # Dev instructions
└── [other root files]
```

## Directory Purposes

**backend/app/ - Core Python application:**
- Purpose: FastAPI web server with database models, business logic, and API routes
- Contains: Entry point (main.py), configuration, middleware, models, services, endpoints
- Key files: `main.py` (FastAPI app), `config.py` (settings), `db.py` (database)

**backend/app/api/endpoints/ - HTTP route handlers:**
- Purpose: Define REST endpoints grouped by domain
- Contains: One Python file per domain (projects, sections, books, agents, etc.)
- Pattern: Each file has a `router: APIRouter` exported, registered in `main.py`

**backend/app/models/ - Data definitions:**
- Purpose: Separate concerns of database schema and validation
- Contains:
  - `database.py` - SQLAlchemy ORM models with relationships
  - `schemas.py` - Pydantic request/response validation
- Key pattern: Schemas use `ConfigDict(from_attributes=True)` for ORM-to-DTO conversion

**backend/app/services/ - Business logic:**
- Purpose: Encapsulate complex operations, external API calls, transformations
- Contains: AI integrations, document processing, knowledge extraction
- Key files:
  - `openai_service.py` - Legacy section review with LRU cache
  - `template_ai_service.py` - Phase-aware AI generation
  - `agent_service.py` - Multi-agent orchestration and RAG
  - `rag_service.py` - Context retrieval from books

**backend/app/templates/ - Template definitions:**
- Purpose: Store and load template configurations
- Contains: JSON files defining phases, subsections, form schemas, AI prompts
- Key files:
  - `short_movie.json` - 4-phase screenwriting template
  - `shared/write_phase.json` - Reusable write phase definition
  - `registry.py` - Loader function `get_template(template_type: str)`

**backend/app/utils/ - Utilities:**
- Purpose: Reusable validation and helper functions
- Contains: Input sanitization, field validators
- Key files: `validators.py` - HTML/script stripping, field validation

**backend/app/tests/ - Test suite:**
- Purpose: Unit and integration tests
- Contains: Pytest test files with conftest fixtures
- Key files:
  - `conftest.py` - Fixture setup (DB, app client)
  - `test_api.py` - API endpoint tests
  - `test_validators.py` - Validation tests

**backend/migrations/ - Database schema:**
- Purpose: Track schema changes
- Contains: SQL migration files
- Key files:
  - `init_db.sql` - Initial schema (projects, sections, checklists)
  - `003_template_system.sql` - Phase/subsection tables
  - `004_agent_type_and_quality.sql` - Agent enhancements
  - `005_book_progress.sql` - Book progress tracking

**frontend/src/components/ - React components:**
- Purpose: Build user interface
- Pattern: Folder per feature area, functional components with hooks
- Key directories:
  - `Layout/` - Page structure
  - `Projects/` - Project management
  - `Editor/` - Legacy section editor
  - `Workspace/` - Template-based workspace with dynamic rendering
  - `Patterns/` - Reusable form patterns
  - `Books/` - Book and agent management
  - `Shared/` - Reusable components (chat, AI actions)
  - `UI/` - Primitives (buttons, modals, etc.)

**frontend/src/lib/ - Utilities and configuration:**
- Purpose: API communication, constants, helpers
- Key files:
  - `api.tsx` - Fetch wrapper with Bearer token + timeout
  - `constants.ts` - QUERY_KEYS, framework configs, magic numbers
  - `utils.ts` - Helper functions

**frontend/src/types/ - TypeScript definitions:**
- Purpose: Type safety across frontend
- Key files:
  - `index.ts` - Enums (SectionType, Framework, etc.) + interfaces
  - `template.ts` - Template system types (PhaseConfig, SubsectionConfig, etc.)

**frontend/src/hooks/ - React hooks:**
- Purpose: Shared hook logic
- Key files: `useKeyboardShortcuts.tsx` - Cmd/Ctrl+S (save), Cmd/Ctrl+Enter (review)

## Key File Locations

**Entry Points:**
- Backend: `backend/app/main.py` - FastAPI app initialization
- Frontend: `frontend/src/main.tsx` → `frontend/src/App.tsx` - React mount point
- Docker: `docker-compose.yml` - Full-stack orchestration

**Configuration:**
- Backend: `backend/app/config.py` - Pydantic Settings from .env
- Frontend: `frontend/vite.config.ts` - Vite bundler config
- Database: `backend/migrations/*.sql` - Schema definition

**Core Logic:**
- API: `backend/app/api/endpoints/*.py` - Route handlers
- Services: `backend/app/services/*.py` - Business logic
- ORM: `backend/app/models/database.py` - Database models
- Validation: `backend/app/models/schemas.py` - Pydantic schemas

**Testing:**
- Backend tests: `backend/app/tests/` - Pytest suite
- Frontend: No test files (not set up yet)

## Naming Conventions

**Files:**

| Pattern | Example | Purpose |
|---------|---------|---------|
| `{resource}.py` | `projects.py` | API endpoint file (plural) |
| `{action}_service.py` | `openai_service.py` | Service class (suffix: _service) |
| `test_{name}.py` | `test_api.py` | Test file (prefix: test_) |
| `{feature}.tsx` | `ProjectList.tsx` | React component (PascalCase) |
| `use{Hook}.tsx` | `useKeyboardShortcuts.tsx` | React hook (prefix: use, PascalCase) |
| `{name}.json` | `short_movie.json` | Template definition (kebab-case) |

**Directories:**

| Pattern | Example | Purpose |
|---------|---------|---------|
| `{resource}s/` | `projects/`, `endpoints/` | Collection of related items (plural) |
| `{Domain}/` | `Editor/`, `Books/` | Feature area (PascalCase) |
| `lib/`, `utils/` | Standard names for utilities |
| `models/` | Data layer (schemas + ORM) |
| `services/` | Business logic layer |

**Classes & Functions:**

- **Python:** `PascalCase` for classes, `snake_case` for functions/methods
  - Example: `class OpenAIService`, `def review_section()`
- **TypeScript:** `PascalCase` for types/components, `camelCase` for variables/functions
  - Example: `interface Project`, `const useQuery()`
- **Route handlers:** Function name describes action + resource
  - Example: `async def create_project()`, `async def get_phase_data()`

**Enums:**

- Backend: `database.py` (Framework, SectionType, PhaseType, etc.)
- Frontend: `types/index.ts` (SectionType, Framework, etc.)
- Pattern: `SCREAMING_SNAKE_CASE` for values (e.g., `Framework.THREE_ACT = "three_act"`)

## Where to Add New Code

**New API Endpoint:**
1. Create function in `backend/app/api/endpoints/{domain}.py`
2. Use router with proper path and HTTP method
3. Add Pydantic schema to `backend/app/models/schemas.py` if new request/response type
4. Add database model to `backend/app/models/database.py` if new entity
5. Register router in `backend/app/main.py` with `app.include_router()`

**New Service/Business Logic:**
1. Create `backend/app/services/{feature}_service.py`
2. Implement class with public methods
3. Call from endpoints via dependency injection
4. Cache if needed (decorator pattern or explicit LRU cache)

**New React Component:**
1. Create `frontend/src/components/{Category}/{ComponentName}.tsx`
2. Import hooks (useQuery, useMutation) from `@tanstack/react-query`
3. Fetch data via `api.{method}()` from `lib/api.tsx`
4. Export as named export (not default)
5. Import in parent component and add to render

**New UI Pattern:**
1. Create `frontend/src/components/Patterns/{PatternName}View.tsx`
2. Accept `config` and `data` as props
3. Render based on pattern type (from template config)
4. Handle mutations for updates
5. Register pattern type in `ContentArea.tsx` switch statement

**New Template:**
1. Create `backend/app/templates/{template_name}.json`
2. Define `phases` array with:
   - `id`, `label`, `description`, `subsections` array
   - Each subsection: `key`, `type` (pattern type), `schema`, `wizard_config`, `ai_prompt`
3. Update `backend/app/templates/registry.py` to load and cache it
4. Create shared prompts in `backend/app/templates/shared/prompts/` if reusable

**New Database Model:**
1. Add class to `backend/app/models/database.py`
2. Define table, columns, relationships with backref
3. Add enum to database.py if new type
4. Create migration file in `backend/migrations/`
5. Add Pydantic schema to `schemas.py` (base, create, update, response)
6. Add endpoint in appropriate route file

**New Environment Variable:**
1. Add field to `backend/app/config.py` Settings class
2. Add `@field_validator` if validation needed
3. Document in `.env.example` or project README
4. Frontend: Use `import.meta.env.VITE_*` (Vite exposes VITE_ prefixed vars)

## Special Directories

**backend/uploads/:**
- Purpose: Temporary/uploaded file storage
- Generated: Yes (created at runtime)
- Committed: No (in .gitignore)

**backend/migrations/:**
- Purpose: Track schema changes
- Generated: No (manually created)
- Committed: Yes (source of truth for schema)

**frontend/dist/:**
- Purpose: Built static assets
- Generated: Yes (vite build)
- Committed: No (in .gitignore)

**.planning/:**
- Purpose: GSD orchestrator state and codebase analysis docs
- Generated: Yes (by mapping tools)
- Committed: Yes (for continuity across sessions)

**node_modules/, venv/:**
- Purpose: Dependency installations
- Generated: Yes (npm install / pip install)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-03-11*
