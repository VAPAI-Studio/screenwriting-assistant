# Architecture

**Analysis Date:** 2026-03-01

## Pattern Overview

**Overall:** Layered N-tier architecture with clear separation between frontend (React/TypeScript) and backend (FastAPI/Python). Backend uses service-oriented pattern with dependency injection for middleware and database concerns. Frontend implements React Query for state management and component-driven UI.

**Key Characteristics:**
- API-driven separation of frontend and backend
- Middleware stack for cross-cutting concerns (logging, security, rate limiting)
- SQLAlchemy ORM with relationship-based data modeling
- React Query for server state caching and synchronization
- Template-based project scaffolding system for flexible project creation

## Layers

**API Layer (Backend):**
- Purpose: HTTP request handling and routing via FastAPI
- Location: `backend/app/api/endpoints/`, `backend/app/main.py`
- Contains: Router handlers for projects, sections, templates, AI features, books, agents, chat
- Depends on: Services layer, database models, dependency injection
- Used by: Frontend application via HTTP requests

**Service Layer (Backend):**
- Purpose: Business logic, AI provider integration, document processing, knowledge extraction
- Location: `backend/app/services/`
- Contains: `openai_service.py`, `ai_provider.py`, `auth_service.py`, `rag_service.py`, `agent_service.py`, `book_processing_service.py`, `embedding_service.py`
- Depends on: Database models, external APIs (OpenAI/Anthropic)
- Used by: API endpoints

**Middleware Layer (Backend):**
- Purpose: Cross-cutting concerns (logging, security, rate limiting, request validation)
- Location: `backend/app/middleware.py`
- Contains: LoggingMiddleware, SecurityMiddleware, RequestSizeLimitMiddleware, RateLimitMiddleware
- Depends on: Starlette base middleware
- Used by: FastAPI app initialization

**Data Access Layer (Backend):**
- Purpose: Database abstraction via ORM, session management, database initialization
- Location: `backend/app/db.py`, `backend/app/models/database.py`
- Contains: SQLAlchemy engine, session factory, database models
- Depends on: SQLAlchemy, PostgreSQL
- Used by: Services and API endpoints via dependency injection

**Validation Layer (Backend):**
- Purpose: Input validation, schema validation, field sanitization
- Location: `backend/app/models/schemas.py`, `backend/app/utils/validators.py`
- Contains: Pydantic v2 models with field validators, HTML sanitization functions
- Depends on: Pydantic
- Used by: API endpoints for request/response validation

**UI Layer (Frontend):**
- Purpose: User interface rendering and interaction
- Location: `frontend/src/components/`
- Contains: Layout, Projects, Editor, Workspace, Books, Patterns (view variants)
- Depends on: React, React Router, Radix UI, Tailwind CSS
- Used by: User browsers

**State Management (Frontend):**
- Purpose: Server state caching, query management, request deduplication
- Location: `frontend/src/` (app-level via QueryClient)
- Contains: React Query with 5-minute stale time
- Depends on: @tanstack/react-query
- Used by: All components via hooks

**API Client Layer (Frontend):**
- Purpose: HTTP communication with backend, request timeout, auth token management
- Location: `frontend/src/lib/api.tsx`
- Contains: Fetch wrapper with timeout, header management, bearer token auth
- Depends on: Backend API routes
- Used by: Components and React Query

## Data Flow

**Project Creation Flow:**

1. User submits project form in `ProjectList.tsx`
2. Frontend calls `api.createProjectV2()` with title and template
3. API endpoint `POST /api/projects/v2` in `projects.py` receives request
4. Middleware stack processes request (logging → security headers → size limit → rate limit)
5. `get_current_user` dependency injects authenticated user
6. `create_project_v2` handler validates title via `validate_project_title()`
7. Handler retrieves template config via `get_template()` from `backend/app/templates/registry.py`
8. Creates `Project` database record with `template` and `current_phase`
9. Auto-scaffolds `PhaseData` and `ListItem` records based on template structure
10. Database transaction commits, project ID assigned
11. Response schema `ProjectResponseV2` serialized to JSON
12. Frontend receives project, React Query caches response, component renders

**Section Update with AI Suggestions Flow:**

1. User edits section content in `SectionEditor.tsx`
2. Component calls `api.updateSubsectionData()` with updated content
3. PATCH request to `/api/phase-data/{project_id}/{phase}/{subsection_key}`
4. Handler in `phase_data.py` validates ownership via `_verify_project_ownership()`
5. Handler updates `PhaseData.content` JSON field
6. Optionally triggers AI suggestions if action mode enabled
7. Service layer calls `openai_service` or `ai_provider` depending on config
8. AI response cached in-memory (15-min TTL) if available
9. Results stored in `PhaseData.ai_suggestions`
10. Response returned to frontend with updated data
11. React Query invalidates and refetches related queries

**Template-Based Content Generation:**

1. User selects template (MICRO_DRAMA or SHORT_MOVIE) during project creation
2. Template config loaded from `backend/app/templates/` registry
3. Config defines phases (IDEA, STORY, SCENES, WRITE) with subsections
4. Each subsection has field definitions, view type (WizardView, CardGridView, etc.), optional wizard config
5. Project creation scaffolds all phase_data and list_items according to template
6. Frontend loads template via `api.getTemplate()`, displays PhaseNavigation with phases
7. User navigates phases and subsections; content rendered dynamically per subsection view type
8. Wizards (if configured) provide AI-powered content generation with readiness checks
9. All generated content stored in `PhaseData.content` (JSON) and `ListItem` records

**Book Processing & Agent Knowledge Flow:**

1. User uploads PDF via `BookManager.tsx`
2. `api.uploadBook()` POSTs to `/api/books/upload`
3. Backend `books.py` receives file, creates `Book` record with status PENDING
4. Async job (via `book_processing_service.py`) extracts text chunks, creates `BookChunk` records
5. Each chunk embedded via OpenAI embedding API, embedding stored in `BookChunk.embedding` (pgvector)
6. Knowledge extraction service processes chunks, creates `Concept` records with definitions, examples
7. Concepts linked via `ConceptRelationship` (DEPENDS_ON, RELATED_TO, EXTENDS, etc.)
8. Book status updated to COMPLETED
9. Frontend displays book in list, user can link book to agents
10. When agent chat initiated, RAG service queries most similar chunks via embedding similarity
11. Agent prompt includes retrieved chunks as context, model generates informed responses

**State Management:**

- **Query caching:** React Query caches all GET responses with 5-minute stale time
- **Mutation handling:** POST/PATCH/DELETE via `useMutation`, invalidates related queries
- **Local state:** Component state for UI interactions (forms, toggles, selections)
- **Auth state:** Bearer token stored in localStorage, injected in all API request headers
- **Middleware cache:** Backend OpenAI responses cached in-memory (15-min TTL) per request fingerprint

## Key Abstractions

**Project:**
- Purpose: Top-level container for screenplay/writing project
- Examples: `database.Project`, frontend `Project` interface
- Pattern: Aggregate root with cascade delete to sections/phase_data
- Relations: owns Sections, owns PhaseData, owns AISession records

**PhaseData:**
- Purpose: Container for content within a specific project phase and subsection
- Examples: `database.PhaseData` with JSON content field
- Pattern: Generic JSON content container mapped to template definitions
- Relations: belongs to Project, has many ListItems

**ListItem:**
- Purpose: Individual item within a phase subsection (episode, scene, character, beat)
- Examples: `database.ListItem` with item_type enum
- Pattern: Ordered list with sort_order, flexible content via JSON
- Relations: belongs to PhaseData, referenced by AISession for context

**AISession:**
- Purpose: Conversation thread between user and AI within a specific project context
- Examples: `database.AISession` with AIMessage children
- Pattern: One-to-many relationship with chronological messages
- Relations: belongs to Project, has many AIMessages, optional context_item_id reference

**Concept (Knowledge Graph):**
- Purpose: Extracted knowledge unit from uploaded books with semantic meaning
- Examples: `database.Concept` with embedding, examples, actionable questions
- Pattern: Nodes in directed graph connected by ConceptRelationship edges
- Relations: belongs to Book, has many outbound relationships, has many inbound relationships

**Agent:**
- Purpose: AI persona with configurable system prompt and knowledge base (books)
- Examples: `database.Agent` with system_prompt_template, personality
- Pattern: Many-to-many with books via AgentBook junction table
- Relations: belongs to User (owner_id), has many books, has many ChatSessions

**Template:**
- Purpose: Project structure definition with phases, subsections, view types, field schemas
- Examples: JSON config in `backend/app/templates/`, loaded at runtime
- Pattern: Declarative configuration tree defining UI and data scaffolding
- Relations: referenced by Project.template field (enum), used to drive UI layout

## Entry Points

**Backend Entry Point:**
- Location: `backend/app/main.py`
- Triggers: Application startup via `uvicorn app.main:app`
- Responsibilities: FastAPI app initialization, middleware stack configuration, router registration, startup event (database init), custom exception handlers

**Frontend Entry Point:**
- Location: `frontend/src/main.tsx`
- Triggers: Browser loads index.html
- Responsibilities: React DOM mount, React Query provider setup, Router initialization, App component rendering

**API Entry Point:**
- Health check: `GET /health` - returns `{"status": "healthy"}`
- Project listing: `GET /api/projects/` - returns list of user's projects
- Catch-all: All routes prefixed `/api/` delegate to respective routers (projects, sections, review, books, agents, chat, templates, phase-data, list-items, wizards, ai)

## Error Handling

**Strategy:** Custom exception hierarchy mapped to HTTP status codes via dependency injection. Validation errors from Pydantic caught and reformatted with field details.

**Patterns:**

**Backend:**
- `AppException` base class extends `HTTPException`, all custom exceptions inherit from it
- Status codes: 400 (validation), 401 (auth), 403 (authz), 404 (not found), 409 (conflict), 429 (rate limit), 503 (external service), 500 (internal)
- Validation errors: FastAPI `RequestValidationError` caught globally, reformatted to include field paths and messages
- Service errors: `ExternalServiceException` (OpenAI, etc.), `DatabaseException`, `ConfigurationException`
- Request validation: Pydantic field validators in schema classes (e.g., `validate_prompt()`, `validate_notes()`)
- HTML sanitization: Input sanitized via `sanitize_html()` in validators
- Ownership checks: Handlers verify project ownership before mutation via `_verify_project_ownership()`

**Frontend:**
- API errors caught in fetch wrapper, error object thrown from `api.tsx`
- React Query handles request failures, stores error in query state
- Components check `isError` and `error.message` to display toast notifications
- Network timeouts: Fetch with AbortController, 30s API timeout, 120s chat timeout

## Cross-Cutting Concerns

**Logging:**
- Backend: `logging` module configured at app startup with INFO level (DEBUG in development)
- LoggingMiddleware generates request ID (UUID), logs method/path/client IP on entry, logs status/duration on exit
- Headers: X-Request-ID returned in all responses
- Frontend: No structured logging; errors logged to console in dev

**Validation:**
- Backend: Pydantic v2 field validators in schemas (`backend/app/models/schemas.py`)
- Validators check length constraints (min/max), sanitize whitespace, HTML sanitization
- API handlers call utility validation functions (validate_project_title, validate_framework) before persistence
- Frontend: Client-side form validation on React components (length, required fields)
- Type safety: TypeScript interfaces in `frontend/src/types/` mirror backend schemas

**Authentication:**
- Backend: HTTPBearer dependency injects credentials, mock auth for development (token="mock-token"), production uses JWT verify
- Mock auth: `MockAuthService` returns fixed user UUID
- Frontend: Token stored in localStorage under `AUTH_TOKEN_KEY`, injected as Bearer header in all requests
- Routes: All API routes require authenticated user via `get_current_user` dependency (except auth endpoints)

**Authorization:**
- Project ownership: Handlers verify user owns project before returning/updating
- Book ownership: Books linked to owner_id, agents linked to owner_id
- User context: `current_user.id` (UUID) injected via dependency, compared against owner_id in database queries
