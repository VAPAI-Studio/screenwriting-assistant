# Architecture

**Analysis Date:** 2026-03-05

## Pattern Overview

**Overall:** Layered service-oriented architecture with template-driven configuration

**Key Characteristics:**
- **Separation of concerns:** Database layer (SQLAlchemy) → Service layer (business logic) → API layer (endpoint handlers)
- **Configuration-driven:** Template system loads JSON files that define project phases, subsections, and workflows
- **Authentication-aware:** Dependency injection for database sessions and user extraction
- **AI-integrated:** Service-level abstractions for OpenAI/Anthropic with in-memory caching and framework-aware prompts
- **Knowledge graph:** Graph-based concept relationships extracted from uploaded books, connected to screenplay agents

## Layers

**Frontend Presentation Layer:**
- Purpose: React components that render the UI and manage user interactions
- Location: `frontend/src/components/`
- Contains: Layout components, route containers, form editors, chat interfaces, pattern-specific views
- Depends on: React Query for server state, API client (`lib/api.tsx`) for HTTP communication
- Used by: `App.tsx` routing and layout hierarchy

**Frontend State & Data Layer:**
- Purpose: HTTP client, type definitions, query caching, utilities
- Location: `frontend/src/lib/api.tsx`, `frontend/src/types/`, `frontend/src/lib/constants.ts`, `frontend/src/lib/utils.ts`
- Contains: Fetch wrapper with timeout, auth token management, React Query client configuration
- Depends on: Fetch API, localStorage for auth tokens
- Used by: All React components via React Query hooks

**Backend API Layer (Endpoints):**
- Purpose: HTTP request routing and response formatting
- Location: `backend/app/api/endpoints/`
- Contains: Route handlers for projects, sections, chat, agents, books, templates, etc.
- Pattern: FastAPI router per feature domain (e.g., `projects.py`, `agents.py`, `chat.py`)
- Depends on: Service layer, dependency injection (DB session, authenticated user)
- Used by: FastAPI router registration in `main.py`

**Backend Service Layer:**
- Purpose: Business logic, external service integration, data orchestration
- Location: `backend/app/services/`
- Key services:
  - `openai_service.py`: Framework-aware screenplay section review with LRU caching
  - `rag_service.py`: Retrieval-augmented generation using embeddings and concepts
  - `agent_service.py`: Multi-agent orchestration for screenplay feedback
  - `book_processing_service.py`: Document ingestion, chunking, and concept extraction
  - `knowledge_extraction_service.py`: Concept relationship mapping from text
  - `embedding_service.py`: Vector generation and similarity search
  - `ai_provider.py`: Abstraction over OpenAI/Anthropic APIs
- Depends on: Data models, external AI APIs
- Used by: Endpoint handlers

**Backend Data Layer:**
- Purpose: ORM models and schema definitions
- Location: `backend/app/models/database.py` (SQLAlchemy models), `backend/app/models/schemas.py` (Pydantic schemas)
- Contains:
  - **Domain models:** Project → Section → ChecklistItem (legacy), PhaseData → ListItem (template-based)
  - **Knowledge models:** Book → BookChunk → Concept → ConceptRelationship
  - **Agent models:** Agent → ChatSession → ChatMessage (with agent system prompts)
  - **Enum types:** Framework, PhaseType, AgentType, BookStatus, RelationshipType
- Depends on: SQLAlchemy, Pydantic v2
- Used by: Service and endpoint layers

**Backend Middleware & Config Layer:**
- Purpose: Cross-cutting concerns, environment configuration, middleware chain
- Location: `backend/app/middleware.py`, `backend/app/config.py`, `backend/app/main.py`
- Contains:
  - Middleware chain (order-dependent): RateLimitMiddleware → RequestSizeLimitMiddleware → SecurityMiddleware → LoggingMiddleware
  - Settings validation (Pydantic Settings with field validators)
  - CORS configuration
- Depends on: Starlette BaseHTTPMiddleware, environment variables
- Used by: FastAPI app initialization

**Template System (Configuration):**
- Purpose: Define project phases and workflows without hardcoding
- Location: `backend/app/templates/`
- Pattern: JSON files with $ref resolution for phase composition
- Key file: `shared/write_phase.json` (reusable phase definition)
- Registry: `registry.py` loads and caches templates with deep copy to prevent mutation
- Depends on: File system (JSON templates)
- Used by: Project creation endpoints (`projects.py::create_project_v2`)

**Database Layer:**
- Purpose: Persistent data storage with cascade semantics
- Location: PostgreSQL 15 (configured via DATABASE_URL in config)
- Key relationships:
  - Project has cascade-delete to Sections and PhaseData
  - Section has cascade-delete to ChecklistItems
  - Book has cascade-delete to BookChunks and Concepts
  - PhaseData has cascade-delete to ListItems
  - Agent has many-to-many with Books via AgentBook
  - ChatSession has cascade-delete to ChatMessages
- Used by: All service layers via SQLAlchemy ORM

## Data Flow

**Project Creation Flow (Template-Based):**

1. User creates project via `POST /api/projects/v2` (endpoint: `projects.py::create_project_v2`)
2. Endpoint validates title, loads template config via `registry.get_template()`
3. Service creates Project record with `template`, `current_phase=IDEA`, and `template_config` JSON
4. Service creates PhaseData records for each phase/subsection combo from template
5. Response returns ProjectV2 schema with all nested phase_data and list_items

**Screenplay Review Flow:**

1. User requests review on a section text via `POST /api/review` (endpoint: `review.py`)
2. Endpoint injects Framework, SectionType, and content
3. `OpenAIService.review_section()` called with cache check (MD5 of section_id + text + framework)
4. If cache miss: calls `ai_provider.chat_completion()` with framework+section-specific system prompt
5. AI response parsed as JSON with "issues" and "suggestions" arrays
6. Response cached with 15-min TTL, returned to frontend
7. Cached response moved to end of LRU OrderedDict on hit

**Agent-Based Knowledge Review Flow:**

1. User sends message in chat with agent context via `POST /api/ai/chat`
2. Endpoint creates/retrieves AISession (project_id, phase, subsection, agent_id, context_item_id)
3. System prompt from Agent.system_prompt_template (template with {variables})
4. If agent type is BOOK_BASED: calls `rag_service.retrieve_relevant_concepts()` to fetch book chunks + concepts via embedding similarity
5. Concepts used as context in system prompt via `agent_service.format_agent_context()`
6. Chat completion called with multi-turn message history from AIMessage
7. Response saved as AIMessage with message_type, consulted_agents list, book_references
8. Chat history persisted to enable context awareness across turns

**Book Processing Pipeline:**

1. User uploads book via `POST /api/books/upload` (endpoint: `books.py`)
2. Book record created with status=PENDING, file saved to disk
3. Background task (triggered by status change): `book_processing_service.process_book()`
4. Steps:
   - Extract text from PDF/EPUB (status: EXTRACTING)
   - Chunk text into overlapping segments (750 tokens, 150 overlap) via `document_service`
   - Generate embeddings for chunks via `embedding_service.embed_text()` (OpenAI text-embedding-3-small)
   - Extract key concepts via LLM via `knowledge_extraction_service.extract_concepts()` (status: ANALYZING)
   - Generate concept embeddings (status: EMBEDDING)
   - Create ConceptRelationship records based on semantic relatedness
   - Update Book.status to COMPLETED
5. Concepts now queryable for RAG via semantic search

**Template-Driven UI Navigation:**

1. Frontend loads project via `GET /api/projects/{id}` - includes template config
2. ProjectWorkspace component fetches template structure via `GET /api/templates/{template_id}`
3. PhaseNavigation renders phase tabs from template.phases
4. SubsectionSidebar renders subsection list from currentPhase.subsections
5. ContentArea renders pattern-specific view based on currentSubsection.pattern (e.g., "card_grid", "screenplay_editor", "wizard")
6. Pattern component fetches ListItems via `GET /api/phase-data/{project_id}/{phase}/{subsection_key}`
7. User edits ListItem, saves via `PATCH /api/list-items/{item_id}`

## State Management

**Frontend:**
- **Query Cache:** React Query with 5-minute stale time for projects, templates, phase data
- **UI State:** Local useState for selected phase, subsection, sidebar visibility
- **Auth State:** localStorage token read on each request via `getAuthToken()`
- **No Redux/Context:** All server state via React Query, all UI state local to components

**Backend:**
- **In-Memory Cache:** OpenAIService uses OrderedDict LRU (100 size limit, 15-min TTL manual expiry not implemented)
- **Database Session:** SQLAlchemy Session per request via FastAPI Depends
- **No Session Affinity:** Stateless - each request gets fresh session

## Key Abstractions

**AI Provider Abstraction:**
- Purpose: Swap between OpenAI and Anthropic without changing service logic
- Location: `backend/app/services/ai_provider.py` (async function `chat_completion()`)
- Interface: Takes `messages: List[Dict]`, `model: str`, `temperature: float` → returns text
- Implementation: Routes to OpenAI or Anthropic based on `settings.AI_PROVIDER`
- Used by: OpenAIService, AgentService, TemplateAIService, KnowledgeExtractionService

**Template Registry:**
- Purpose: Load project workflow definitions from static JSON without database
- Location: `backend/app/templates/registry.py`
- Functions:
  - `get_template(template_id)`: Returns cached deep copy of template config
  - `_resolve_refs(config)`: Resolves $ref pointers to shared JSON files (e.g., `shared/write_phase.json`)
  - `list_templates()`: Enumerate available templates
- Pattern: File-based configuration with reference composition

**Service Layer Abstractions:**
- **OpenAIService:** Encapsulates screenplay review logic with caching
- **RAGService:** Hides complexity of concept retrieval via embeddings
- **AgentService:** Orchestrates multi-agent workflows with system prompt templating
- **BookProcessingService:** Coordinates extraction → chunking → embedding → analysis steps
- Each service is instantiated once and dependency-injected or imported as singleton

**Schema Validation:**
- Backend: Pydantic v2 models (`schemas.py`) with field validators for sanitization
- Frontend: TypeScript interfaces mirroring Pydantic models (manually kept in sync)
- Validators: Min/max length, string trimming, enum validation

## Entry Points

**Frontend:**
- Location: `frontend/src/main.tsx` → `App.tsx`
- Initialization: React 18 strict mode, QueryClientProvider, BrowserRouter
- Routes: `/` (projects list), `/projects/:id` (legacy editor), `/projects/:id/:phase/:subsection/:itemId` (new workspace)
- Key hooks: `useKeyboardShortcuts` (Cmd+S save, Cmd+Enter review), `useQuery` for data fetching

**Backend:**
- Location: `backend/app/main.py`
- Initialization: FastAPI app with middleware stack, CORS config, exception handlers
- Startup hook: `init_db()` creates tables if not present
- Routes: All mounted with `/api/{domain}` prefix (auth, projects, sections, books, agents, chat, templates, etc.)
- Health endpoint: `GET /health`

## Error Handling

**Strategy:** HTTP status codes propagated with custom exception hierarchy

**Patterns:**
- **404 NotFoundException:** Raised when resource not found, maps to HTTP 404
- **400 ValidationException:** Raised on invalid input (title, framework, etc.), maps to HTTP 400
- **401 Unauthorized:** Raised on failed auth, maps to HTTP 401
- **422 ValidationError:** Pydantic v2 field validation errors, custom formatter in `validation_exception_handler`
- **500 Internal Server Error:** Unhandled exceptions logged and returned as 500

**Frontend Error Handling:**
- `api.tsx` checks response.ok and throws generic "Failed to [action]" messages
- Components display error states with retry buttons (e.g., Editor, ProjectWorkspace)
- Network errors caught and displayed in UI
- Timeouts (API_TIMEOUT = 30s, CHAT_TIMEOUT = 120s, WIZARD_TIMEOUT = 300s) abort fetch and throw

## Cross-Cutting Concerns

**Logging:**
- Backend: Python logging module, configured in `config.py` (DEBUG in dev, INFO in prod)
- Frontend: Browser console only, no persistent logs
- Middleware: LoggingMiddleware logs all requests/responses with request ID (UUID)
- Requests: Logged with method, path, client IP
- Responses: Logged with status code and duration

**Validation:**
- Backend: Pydantic v2 field validators in schemas (min/max length, whitespace trimming)
- Utility functions: `utils/validators.py` has `validate_project_title()`, `validate_framework()`, etc.
- Frontend: TypeScript interfaces provide compile-time type safety; no runtime validation
- HTML sanitization: Not implemented - XSS risk if user content rendered unsanitized

**Authentication:**
- Backend: HTTPBearer scheme with token in Authorization header
- Mock auth: Mock token "mock-token" accepted in development (checked in dependencies.py)
- Production auth: `auth_service.verify_token()` stub (not fully implemented in MVP)
- Frontend: Token stored in localStorage under AUTH_TOKEN_KEY, sent in Authorization header of all requests

**Rate Limiting:**
- Backend: RateLimitMiddleware limits to 600 req/min per IP (generous for development)
- Request size: Limited to 10MB max via RequestSizeLimitMiddleware
- No frontend rate limiting

---

*Architecture analysis: 2026-03-05*
