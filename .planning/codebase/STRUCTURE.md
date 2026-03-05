# Codebase Structure

**Analysis Date:** 2026-03-05

## Directory Layout

```
screenwriting-assistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/          # Route handlers by domain
│   │   │   └── dependencies.py     # DI for DB session and auth
│   │   ├── models/
│   │   │   ├── database.py         # SQLAlchemy ORM models
│   │   │   └── schemas.py          # Pydantic v2 request/response schemas
│   │   ├── services/               # Business logic layer
│   │   ├── templates/              # JSON-based project workflow configs
│   │   ├── utils/                  # Validators and helpers
│   │   ├── tests/                  # pytest test suite
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── middleware.py           # Custom middleware (logging, security, rate limit)
│   │   ├── config.py               # Pydantic Settings from env
│   │   ├── db.py                   # SQLAlchemy engine and session factory
│   │   ├── exceptions.py           # Custom exception classes
│   │   └── api_docs.py             # OpenAPI schema customization
│   ├── migrations/                 # SQL migration files (003-005)
│   ├── uploads/                    # User-uploaded files (books)
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Container image for backend
│   └── .env.example.txt            # Environment variable template
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Books/              # BookManager, AgentManager components
│   │   │   ├── Editor/             # Legacy section editor (SectionEditor, Checklist, ReviewPanel, ChatSidebar)
│   │   │   ├── Layout/             # Header, Layout wrapper
│   │   │   ├── Projects/           # ProjectList, ProjectCard, CreateProjectModal
│   │   │   ├── Patterns/           # Template-driven views (CardGridView, WizardView, ScreenplayEditorView, etc.)
│   │   │   ├── Shared/             # Reusable: AIActionBar, SidebarChat, MarkdownContent, FieldRenderer
│   │   │   ├── UI/                 # Primitives: Button, ResizablePanel
│   │   │   └── Workspace/          # New template-based editor (ProjectWorkspace, PhaseNavigation, SubsectionSidebar, ContentArea)
│   │   ├── hooks/                  # Custom React hooks (useKeyboardShortcuts)
│   │   ├── lib/
│   │   │   ├── api.tsx             # HTTP fetch wrapper and API client
│   │   │   ├── constants.ts        # Magic numbers, feature flags, configs
│   │   │   ├── section-config.ts   # Framework/section metadata
│   │   │   └── utils.ts            # Helper functions
│   │   ├── types/
│   │   │   ├── index.ts            # TypeScript interfaces (Project, Section, Book, Agent, etc.)
│   │   │   └── template.ts         # Template structure types (PhaseConfig, SubsectionConfig, etc.)
│   │   ├── App.tsx                 # Router setup, QueryClient init
│   │   ├── main.tsx                # React 18 root render
│   │   └── index.css               # Global tailwind styles
│   ├── public/                     # Static assets
│   ├── dist/                       # Built output (Vite)
│   ├── package.json                # npm dependencies
│   ├── package-lock.json           # Locked versions
│   ├── tsconfig.json               # TypeScript config
│   ├── vite.config.ts              # Vite build config with /api proxy
│   ├── tailwind.config.js          # Tailwind CSS with HSL variables
│   ├── Dockerfile                  # Container image for frontend
│   └── .env.example.txt            # Environment template (VITE_API_URL)
├── docker-compose.yml              # Multi-container orchestration
├── CLAUDE.md                       # Project guidelines
└── .planning/
    └── codebase/                   # GSD codebase analysis docs
```

## Directory Purposes

**backend/app/api/endpoints/:**
- Purpose: HTTP endpoint handlers, organized by feature domain
- Contains: One file per domain (projects.py, agents.py, chat.py, books.py, sections.py, templates.py, etc.)
- Key files:
  - `projects.py`: GET/POST/PATCH projects; includes both v1 (framework-based) and v2 (template-based) creation
  - `agents.py`: CRUD for Agent models (system prompts, personality, books filter)
  - `chat.py`: Deprecating in favor of `ai_chat.py` (multi-agent orchestrated conversations)
  - `books.py`: Upload, list, process, delete books
  - `phase_data.py`: GET/PATCH phase data and list items for template-based workflow
  - `ai_chat.py`: AI-powered chat with agents and RAG context
  - `wizards.py`: Guided workflows for concept extraction, screenplay generation
- Pattern: FastAPI router per file, imported and registered in main.py

**backend/app/services/:**
- Purpose: Business logic, external integrations, data orchestration
- Key services:
  - `openai_service.py`: Screenplay review with framework-aware prompts, LRU caching
  - `agent_service.py`: Multi-agent orchestration, system prompt templating, context formatting
  - `rag_service.py`: Concept retrieval via embedding similarity, top-K filtering
  - `book_processing_service.py`: Document ingestion, text extraction, chunking
  - `knowledge_extraction_service.py`: LLM-based concept extraction, relationship mapping
  - `embedding_service.py`: Vector generation and storage (OpenAI text-embedding-3-small, 1536 dim)
  - `ai_provider.py`: Abstraction over OpenAI/Anthropic chat completion
  - `auth_service.py`: JWT verification stub (mock for MVP)
  - `template_ai_service.py`: Template-specific AI review (e.g., writing phase feedback)
  - `document_service.py`: PDF/EPUB text extraction
  - `agent_templates.py`: Predefined agent configurations
- Pattern: Stateless functions or singleton instances, imported by endpoints

**backend/app/models/:**
- Purpose: Data layer definitions
- `database.py`: SQLAlchemy ORM models (Project, Section, ChecklistItem, PhaseData, ListItem, Book, Concept, Agent, ChatSession, etc.) with enums for types
- `schemas.py`: Pydantic v2 request/response schemas mirroring ORM models with validators

**backend/app/templates/:**
- Purpose: JSON-based workflow configuration
- `registry.py`: Loads/caches templates, resolves $ref pointers
- `shared/`: Reusable phase definitions (e.g., write_phase.json)
- `shared/prompts/`: Template-specific AI prompts (for future expansion)
- Pattern: JSON files loaded at app startup, cached in memory

**frontend/src/components/**

Sub-directory purposes:

- **Books/:** BookManager (list/upload/delete), AgentManager (create/configure agents)
- **Editor/:** Legacy section-by-section editor (SectionEditor, Checklist, ReviewPanel, ChatSidebar) - used for v1 framework projects
- **Workspace/:** New template-driven multi-phase workspace (ProjectWorkspace container, PhaseNavigation tabs, SubsectionSidebar, ContentArea routing)
- **Patterns/:** Pattern-specific rendering (template configuration defines which pattern renders each subsection):
  - `CardGridView`: Grid of concept cards (e.g., for Story phase)
  - `WizardView`: Step-by-step guided workflow (e.g., for Idea phase)
  - `ScreenplayEditorView`: Screenplay formatting with scene/action/character elements
  - `StructuredFormView`: Form fields based on template definition
  - `OrderedListView`: Ordered list of items with drag/drop
  - `RepeatableCardsView`: Add multiple items (scenes, beats, etc.)
  - `IndividualEditorView`: Single text editor (fallback)
  - `PlaceholderView`: Not yet implemented subsection
- **Projects/:** ProjectList (all projects), ProjectCard (individual card), CreateProjectModal (new project form)
- **Shared/:** Reusable (AIActionBar for quick actions, SidebarChat for multi-turn conversations, MarkdownContent for rendering, FieldRenderer for dynamic fields)
- **UI/:** Primitives (Button, ResizablePanel, Input, Modal, Card, etc.)
- **Layout/:** Header, Layout wrapper

## Key File Locations

**Backend Entry Points:**
- `backend/app/main.py`: FastAPI app initialization, middleware stack, router registration, startup/shutdown hooks

**Backend Configuration:**
- `backend/app/config.py`: Pydantic Settings, environment validation, AI provider selection (openai/anthropic)
- `backend/app/db.py`: SQLAlchemy engine, session factory

**Backend Core Logic:**
- `backend/app/api/dependencies.py`: Dependency injection (get_db, get_current_user)
- `backend/app/services/openai_service.py`: Review logic with caching
- `backend/app/services/rag_service.py`: Concept retrieval with embeddings
- `backend/app/templates/registry.py`: Template loading and caching

**Backend Data:**
- `backend/app/models/database.py`: SQLAlchemy models (Project, Section, PhaseData, Book, Concept, Agent, etc.)
- `backend/app/models/schemas.py`: Pydantic request/response schemas

**Frontend Entry Points:**
- `frontend/src/main.tsx`: React root render
- `frontend/src/App.tsx`: Router configuration, QueryClient setup

**Frontend HTTP Client:**
- `frontend/src/lib/api.tsx`: Fetch wrapper with timeout, auth token handling, all API methods

**Frontend Type Definitions:**
- `frontend/src/types/index.ts`: Interfaces for Project, Section, Book, Agent, ChatMessage, etc.
- `frontend/src/types/template.ts`: Template structure types (PhaseConfig, SubsectionConfig, FieldConfig, etc.)

**Frontend Configuration:**
- `frontend/src/lib/constants.ts`: API_BASE_URL, API_TIMEOUT, CHAT_TIMEOUT, framework configs, section labels, feature flags
- `frontend/src/lib/section-config.ts`: Metadata for framework sections

## Naming Conventions

**Files:**

- **Backend Python files:** snake_case (e.g., `book_processing_service.py`, `knowledge_extraction_service.py`)
- **Frontend TypeScript/TSX files:** PascalCase for components (e.g., `ProjectWorkspace.tsx`, `SectionEditor.tsx`), camelCase for utilities (e.g., `api.tsx`, `constants.ts`)
- **Test files:** `test_*.py` (pytest convention)
- **Type files:** `index.ts` for main type exports, `*.ts` for feature-specific types

**Directories:**

- **Backend:** snake_case (e.g., `api`, `services`, `models`, `utils`, `tests`, `migrations`)
- **Frontend:** PascalCase for feature directories (e.g., `Books`, `Editor`, `Patterns`, `Workspace`), snake_case for config directories (e.g., `lib`, `hooks`, `types`)

**Classes/Types:**

- **Backend models (SQLAlchemy):** PascalCase singular (e.g., Project, Book, Concept, Agent)
- **Backend schemas (Pydantic):** PascalCase with suffixes (ProjectCreate, ProjectUpdate, ProjectResponse)
- **Frontend types:** PascalCase interfaces (e.g., Project, Book, Agent, ChatSession)
- **Frontend enums:** PascalCase with UPPERCASE values (e.g., Framework.THREE_ACT, PhaseType.IDEA)

**Functions/Methods:**

- **Backend:** snake_case (e.g., `get_current_user`, `review_section`, `process_book`)
- **Frontend:** camelCase (e.g., `getAuthToken`, `fetchWithTimeout`, `handlePhaseChange`)

## Where to Add New Code

**New Feature (API Endpoint + Service):**

1. **Backend service logic:**
   - Create new class/functions in `backend/app/services/{feature}_service.py` (or add to existing service)
   - Define data models in `backend/app/models/database.py` if needed
   - Define Pydantic schemas in `backend/app/models/schemas.py`

2. **Backend endpoint handler:**
   - Create `backend/app/api/endpoints/{feature}.py` with FastAPI router
   - Import service dependencies
   - Register router in `backend/app/main.py`: `app.include_router(feature.router, prefix="/api/{feature}")`

3. **Frontend types:**
   - Add TypeScript interfaces to `frontend/src/types/index.ts` mirroring backend schemas

4. **Frontend API client:**
   - Add methods to `api` object in `frontend/src/lib/api.tsx` for HTTP calls

5. **Frontend UI:**
   - Create component(s) in `frontend/src/components/{Domain}/{Feature}.tsx`
   - Use `useQuery` and `useMutation` from React Query to call API methods

**New UI Component:**

1. If component is layout/container: `frontend/src/components/Workspace/` or `Layout/`
2. If component is feature-specific: `frontend/src/components/{Domain}/{Feature}.tsx`
3. If component is reusable primitive: `frontend/src/components/UI/{Component}.tsx` or `Shared/{Component}.tsx`
4. Use Tailwind CSS with HSL variable colors defined in `frontend/tailwind.config.js`
5. Export from component's directory (or use direct path)

**New Template (Workflow Configuration):**

1. Create JSON file in `backend/app/templates/{template_id}.json`
2. Define phases array with phase config (id, name, subsections array)
3. Each subsection includes: key, name, pattern (which component renders it), fields
4. If reusing phase structure: use `"$ref": "shared/write_phase.json"` with $ref resolution in registry
5. Test by creating project via `/api/projects/v2` with template_id

**New Service Integration:**

1. Add to `backend/app/services/` (new file or extend existing)
2. If external API: add configuration to `backend/app/config.py` (API key, model name, etc.)
3. Implement abstraction function (e.g., `ai_provider.py` abstraction for OpenAI/Anthropic swap)
4. Call from service layer, not directly from endpoints

**Test Coverage:**

1. Backend: Add test to `backend/app/tests/test_api.py` or create `test_{feature}.py`
2. Run: `pytest backend/app/tests/test_api.py`
3. Frontend: No test framework configured - add if needed

## Special Directories

**backend/migrations/:**
- Purpose: SQL schema version control
- Generated: Yes (created manually before code changes)
- Committed: Yes (version control for DB schema)
- Files: `003_template_system.sql`, `004_agent_type_and_quality.sql`, `005_book_progress.sql`
- Pattern: Manual numbered migrations (not auto-generated by Alembic)

**backend/uploads/:**
- Purpose: User-uploaded book files
- Generated: Yes (created at runtime when books uploaded)
- Committed: No (gitignored, local dev only)
- Structure: `{book_id}/` subdirectories with original file + extracted text files

**frontend/dist/:**
- Purpose: Built frontend output
- Generated: Yes (`npm run build` or Docker build)
- Committed: No (gitignored)

**frontend/node_modules/:**
- Purpose: npm dependencies
- Generated: Yes (`npm install`)
- Committed: No (gitignored)

**.planning/codebase/:**
- Purpose: GSD mapping documents
- Generated: Yes (by `/gsd:map-codebase`)
- Committed: Yes (part of codebase reference)

## Module Organization Patterns

**Barrel Exports:**

- `backend/app/services/__init__.py`: Empty (services imported directly)
- `backend/app/api/endpoints/__init__.py`: Empty (endpoints imported directly in main.py)
- `frontend/src/components/{Domain}/`: No barrel - import directly from component files

**Dependency Injection:**

- Backend: FastAPI `Depends()` for DB session (`get_db`) and user extraction (`get_current_user`)
- Frontend: React Query hooks (`useQuery`, `useMutation`) with dependency arrays

**Configuration:**

- Backend: Pydantic Settings singleton in `config.py`, imported as `settings`
- Frontend: Constants object in `lib/constants.ts`, imported by name

---

*Structure analysis: 2026-03-05*
