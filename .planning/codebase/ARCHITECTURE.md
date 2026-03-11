# Architecture

**Analysis Date:** 2026-03-11

## Pattern Overview

**Overall:** Two-tier client-server architecture with feature-driven backend services and component-based frontend.

**Key Characteristics:**
- Layered backend with HTTP API (FastAPI) and database persistence (PostgreSQL)
- React SPA frontend with client-side routing and React Query data management
- Middleware-based request processing (logging, security, rate limiting)
- Template-driven data model for project scaffolding and phase-based workflows
- Multi-agent system for AI-powered analysis and knowledge extraction
- Vector embeddings for semantic search across book content

## Layers

**API Layer (Frontend facing):**
- Purpose: HTTP endpoints exposing business logic via REST
- Location: `backend/app/api/endpoints/`
- Contains: Route handlers for projects, sections, books, agents, chat, templates, wizards
- Depends on: Database models, schemas, services
- Used by: React frontend via `frontend/src/lib/api.tsx`

**Service Layer (Business logic):**
- Purpose: Encapsulate complex operations, AI integrations, data transformations
- Location: `backend/app/services/`
- Contains:
  - `openai_service.py` - Section review with cached responses
  - `template_ai_service.py` - AI-powered content generation for template phases
  - `agent_service.py` - Multi-agent orchestration, knowledge graph extraction
  - `book_processing_service.py` - Document chunking, embedding, concept extraction
  - `rag_service.py` - Retrieval-augmented generation for context-aware responses
  - `embedding_service.py` - Vector embedding generation
  - `knowledge_extraction_service.py` - Graph-based concept relationship extraction
  - `ai_provider.py` - Provider abstraction (OpenAI or Anthropic)
- Depends on: Database, external AI APIs, utilities
- Used by: API endpoints

**Data Access Layer (Database):**
- Purpose: SQLAlchemy ORM models and database interactions
- Location: `backend/app/models/database.py`
- Contains: SQLAlchemy model definitions, enums, relationships
- Depends on: PostgreSQL (via SQLAlchemy engine in `backend/app/db.py`)
- Used by: Services and endpoints

**Schema Layer (Data validation):**
- Purpose: Pydantic v2 request/response validation and serialization
- Location: `backend/app/models/schemas.py`
- Contains: Request/response DTOs with field validators
- Depends on: Database models (via `ConfigDict(from_attributes=True)`)
- Used by: API endpoints for validation and serialization

**Middleware Layer:**
- Purpose: Cross-cutting concerns (logging, security, rate limiting)
- Location: `backend/app/middleware.py`
- Contains: LoggingMiddleware, SecurityMiddleware, RequestSizeLimitMiddleware, RateLimitMiddleware
- Execution order (innermost to outermost):
  1. LoggingMiddleware - Request ID tracking and timing
  2. SecurityMiddleware - CSRF, XSS, CSP headers
  3. RequestSizeLimitMiddleware - 10MB max body size
  4. RateLimitMiddleware - 600 req/min per IP
  5. CORSMiddleware - Cross-origin resource sharing

**Frontend Component Layer:**
- Purpose: User interface composition and interaction
- Location: `frontend/src/components/`
- Contains:
  - `Layout/` - Page structure (Header, navigation)
  - `Projects/` - Project list, creation, management
  - `Editor/` - Legacy editor (section-based)
  - `Workspace/` - Template-based workspace with phase navigation
  - `Patterns/` - Reusable form/content patterns (CardGrid, StructuredForm, Wizard, etc.)
  - `Books/` - Book management and knowledge graph UI
  - `Shared/` - Reusable components (SidebarChat, AIActionBar, MarkdownContent)
  - `Snippets/` - Snippet manager and search
  - `UI/` - Primitives (Button, Input, Modal, Card, etc.)
- Depends on: React Query, React Router, types
- Used by: App routing

**Frontend State Management:**
- Purpose: Client-side caching and synchronization with backend
- Location: `frontend/src/` (throughout)
- Mechanism: React Query with 5-minute stale time
- Key QueryClient configuration: `staleTime: 1000 * 60 * 5`
- Used by: All data-fetching components

**Frontend Utilities:**
- Purpose: API interaction, constants, type definitions
- Location: `frontend/src/lib/` and `frontend/src/types/`
- Contains:
  - `api.tsx` - Fetch wrapper with Bearer token, 30s timeout
  - `constants.ts` - Framework configs, magic numbers, QUERY_KEYS
  - `utils.ts` - Helper functions

## Data Flow

**Project Creation Flow:**

1. User inputs project details in `CreateProjectModal` → calls `api.createProject()`
2. Frontend fetch wrapper adds `Authorization: Bearer mock-token` header
3. FastAPI endpoint `/api/projects/` (v1) or `/api/projects/v2` (template-based)
4. `projects.py` endpoint validates via `ProjectCreate` schema
5. Creates `Project` DB row with `owner_id` from JWT
6. Cascades to create `Section` rows (v1) or `PhaseData` rows (v2)
7. Commits to PostgreSQL
8. Returns `Project` schema serialized with nested `sections` or `phase_data`
9. React Query invalidates `QUERY_KEYS.PROJECTS`, refetch triggers
10. Frontend renders updated project list

**Template-Based Phase Workflow:**

1. User navigates to `/projects/:projectId/:phase/:subsectionKey`
2. `ProjectWorkspace.tsx` fetches `project` and `templateConfig` via React Query
3. Routes resolve to `ContentArea` with template UI pattern
4. Pattern component (e.g., `StructuredFormView`) renders based on schema
5. User updates content → calls `api.updateSubsectionData()`
6. Backend `/api/phase-data/{project_id}/{phase}/{subsection_key}` PATCH
7. Endpoint merges JSON content into `PhaseData.content`
8. Optional: AI generation via `template_ai_service` if content triggers wizard
9. Invalidates `QUERY_KEYS.PHASE_DATA` on frontend
10. Component refetches and re-renders

**AI Review Flow (Legacy):**

1. User clicks "Review" in section editor
2. Frontend calls `api.reviewSection({ section_id, text, framework })`
3. Backend `/api/review` endpoint validates text length
4. Calls `openai_service.review_section()`
5. Service checks LRU cache (15-min TTL, 100-item capacity)
6. If miss: Calls `ai_provider.chat_completion()` with framework/section prompts
7. Parses JSON response into `{ issues, suggestions }`
8. Caches result and returns
9. Frontend displays in `ReviewPanel`

**Book Processing Flow:**

1. User uploads PDF via `BookManager`
2. Frontend calls `api.uploadBook(formData)` with file
3. Backend `/api/books/upload` saves file to `backend/uploads/`
4. Creates `Book` with status `PENDING`
5. Returns `Book` schema to frontend
6. Frontend polls `api.getBook(bookId)` to monitor `progress` and `status`
7. Background processing (not async in this MVP):
   - `book_processing_service.extract_text_from_pdf()` → chunks
   - `knowledge_extraction_service.extract_concepts()` → Concept rows
   - `embedding_service.embed_text()` → pgvector embeddings (1536-dim)
   - `rag_service.compute_relationships()` → ConceptRelationship rows
8. Updates `Book.status` to `COMPLETED`, `progress` to 100
9. Frontend displays concepts in knowledge graph UI

**Multi-Agent Chat Flow:**

1. User opens `SidebarChat` in workspace
2. Selects agent (e.g., "Book-Based Agent")
3. Types message → calls `api.createAIMessage()`
4. Backend creates `AISession` and `AIMessage` (role: user)
5. Calls `agent_service.generate_response()` with session context
6. Agent retrieves relevant book chunks via `rag_service`
7. Constructs system prompt with agent personality + retrieved context
8. Calls `ai_provider.chat_completion()` with full conversation history
9. Returns response, creates `AIMessage` (role: assistant) in DB
10. Frontend subscribes to SSE or polls for new messages
11. Renders response with markdown formatting and references

**State Management:**

- **Backend:** SQLAlchemy models with relationships maintain referential integrity
- **Frontend:** React Query caches responses with QUERY_KEYS, invalidation on mutations
- **Database:** PostgreSQL ACID transactions ensure consistency across cascading operations

## Key Abstractions

**Project Container:**
- Purpose: Represents a screenplay project with template-based structure
- Examples: `backend/app/models/database.py` (Project model), `frontend/src/types/index.ts` (Project type)
- Pattern: Project → PhaseData (template) or Project → Section (legacy)

**Template System:**
- Purpose: Define multi-phase workflows with subsections, form schemas, and wizard configs
- Examples: `backend/app/templates/short_movie.json` (template config), `frontend/src/types/template.ts` (TypeScript types)
- Pattern: Template config describes phases → subsections → UI patterns + AI prompts

**AI Service Abstraction:**
- Purpose: Unified interface for OpenAI or Anthropic
- Examples: `backend/app/services/ai_provider.py` (provider logic), `backend/app/services/openai_service.py` (specific service)
- Pattern: `chat_completion(messages, model, temperature)` accepts provider-agnostic requests

**Knowledge Graph:**
- Purpose: Semantic relationships between concepts extracted from books
- Examples: `Concept`, `ConceptRelationship`, `BookChunk` (database models)
- Pattern: Bidirectional relationships (depends_on, related_to, part_of, etc.) enable reasoning

**Multi-Agent System:**
- Purpose: Task-specific AI agents with personalized prompts and knowledge access
- Examples: `Agent` model with `system_prompt_template`, `Agent.books` relationship
- Pattern: Agent selects relevant books → RAG retrieves context → personalized response

**UI Pattern Components:**
- Purpose: Reusable form renderers for diverse data structures
- Examples: `CardGridView`, `StructuredFormView`, `OrderedListView`, `WizardView` (frontend)
- Pattern: Pattern config + phase data → component renders appropriate UI + handles persistence

**Form Validation:**
- Purpose: Ensure data quality at API boundary
- Examples: `backend/app/models/schemas.py` (Pydantic validators), `frontend/src/lib/constants.ts` (min/max lengths)
- Pattern: Field-level validation with custom error messages

## Entry Points

**Backend Application:**
- Location: `backend/app/main.py`
- Triggers: Server startup (FastAPI app initialization)
- Responsibilities:
  - Instantiate FastAPI app with middleware stack
  - Register route routers (projects, sections, books, agents, chat, templates, wizards, ai_chat)
  - Configure CORS, exception handlers, OpenAPI docs
  - Initialize database on startup event
  - Export app for uvicorn

**Frontend Application:**
- Location: `frontend/src/main.tsx` → `frontend/src/App.tsx`
- Triggers: Browser load
- Responsibilities:
  - Mount React DOM to `#root`
  - Set up React Query provider with default stale times
  - Initialize React Router with route definitions
  - Wrap Layout component with navigation context

**API Entry Points by Domain:**

| Route Prefix | Endpoint Files | Purpose |
|---|---|---|
| `/api/projects` | `projects.py` | Project CRUD, v1 (legacy) and v2 (template) |
| `/api/sections` | `sections.py` | Section CRUD (legacy) |
| `/api/review` | `review.py` | AI review of sections |
| `/api/phase-data` | `phase_data.py` | Template phase data CRUD, readiness scoring |
| `/api/list-items` | `list_items.py` | List item CRUD within phases |
| `/api/books` | `books.py`, `snippets.py` | Book upload, processing, snippet management |
| `/api/snippets` | `snippet_manager.py` | Snippet CRUD and search |
| `/api/agents` | `agents.py` | Agent CRUD, configuration |
| `/api/chat` | `chat.py` | Chat session and message CRUD (legacy) |
| `/api/ai` | `ai_chat.py` | Multi-agent chat with RAG context |
| `/api/templates` | `templates.py` | Template config retrieval |
| `/api/wizards` | `wizards.py` | Wizard-driven content generation |

**Health Check:**
- Endpoint: `GET /health`
- Returns: `{"status": "healthy"}`

## Error Handling

**Strategy:** Hierarchical exception mapping to HTTP status codes

**Patterns:**

1. **Application Exceptions** (`backend/app/exceptions.py`):
   - `ValidationException` → 400 Bad Request
   - `AuthenticationException` → 401 Unauthorized
   - `AuthorizationException` → 403 Forbidden
   - `NotFoundException` → 404 Not Found
   - `ConflictException` → 409 Conflict
   - `RateLimitException` → 429 Too Many Requests
   - `ExternalServiceException` / `OpenAIException` → 503 Service Unavailable
   - `DatabaseException` / `ConfigurationException` → 500 Internal Server Error

2. **Request Validation** (`backend/app/main.py` exception handlers):
   - Pydantic v2 `RequestValidationError` → 422 with detailed field-level errors
   - Custom handler extracts field paths and messages
   - Returns: `{ "detail": "Validation error", "errors": [{ "field": "...", "message": "..." }] }`

3. **Frontend Error Handling** (`frontend/src/lib/api.tsx`):
   - Fetch wrapper catches AbortError (timeout) → "Request timeout"
   - HTTP errors thrown, caught by component error boundaries
   - React Query retry logic (1 retry by default)
   - User-facing error messages from `ERROR_MESSAGES` constants

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Pattern: Configured in `backend/app/main.py`, structured in `LoggingMiddleware`
- Trace: Request ID (`X-Request-ID` header) attached to all log entries
- Levels: DEBUG (dev), INFO (prod)

**Validation:**
- Backend: Pydantic v2 field validators in schema classes
- Examples: `min_length`, `max_length`, custom `@field_validator` decorators
- Sanitization: HTML/script stripping in `backend/app/utils/validators.py`

**Authentication:**
- Mechanism: HTTP Bearer token (JWT in production, `mock-token` in dev)
- Dependency: `backend/app/api/dependencies.py` `get_current_user()`
- Scope: All endpoints require `Authorization` header
- Dev mode: Accepts hardcoded `mock-token` without verification
- Extraction: Frontend stores token in localStorage under `AUTH_TOKEN_KEY`

**Authorization:**
- Pattern: User ownership checks in endpoint handlers
- Example: `Project.owner_id == current_user.id` before returning/modifying
- Scope: Per-resource (project-level granularity)

**Caching:**
- Backend:
  - Service-level: `OpenAIService` LRU cache (15-min TTL, 100 items)
  - DB: PostgreSQL query caching (implicit via ORM)
- Frontend:
  - React Query: 5-minute stale time, automatic refetch on window focus
  - localStorage: Auth token, last viewed phase/subsection

**Rate Limiting:**
- Middleware: `RateLimitMiddleware` in 60-second window
- Threshold: 600 req/min per IP (generous for dev, tighten for production)
- Response: 429 Too Many Requests with `Retry-After` header

---

*Architecture analysis: 2026-03-11*
