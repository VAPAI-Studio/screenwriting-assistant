# Architecture

**Analysis Date:** 2026-03-06

## Pattern Overview

**Overall:** Full-stack layered REST API with a React SPA frontend. Two distinct subsystems coexist:
1. **Legacy framework system** — Project → Section → ChecklistItem hierarchy managed through `/api/projects` and `/api/sections`
2. **Template system** — Project → PhaseData → ListItem hierarchy managed through `/api/phase-data`, `/api/list-items`, `/api/ai`, and `/api/wizards`

**Key Characteristics:**
- Backend is FastAPI with synchronous SQLAlchemy sessions (sync ORM, async route handlers via thread-pool)
- AI calls are fully async using a unified `ai_provider` abstraction supporting OpenAI and Anthropic
- Frontend is purely client-side — no SSR. All data fetching via React Query hitting `/api/*`
- The template system is data-driven: JSON files in `backend/app/templates/` define phase structure, subsection layout, and UI patterns which the frontend renders dynamically
- Knowledge Graph (KG) + RAG pipeline is a separate subsystem for book ingestion and agent-powered chat

## Layers

**HTTP Middleware Stack (backend):**
- Purpose: Cross-cutting request/response concerns, applied in reverse registration order
- Location: `backend/app/middleware.py`
- Execution order (outermost first): CORSMiddleware → RateLimitMiddleware (600 req/min) → RequestSizeLimitMiddleware (10MB) → SecurityMiddleware → LoggingMiddleware
- Depends on: Nothing — pure middleware
- Used by: All incoming HTTP requests

**Route Layer (backend):**
- Purpose: HTTP request parsing, auth enforcement, response shaping
- Location: `backend/app/api/endpoints/` — one file per domain: `projects.py`, `sections.py`, `review.py`, `auth.py`, `books.py`, `agents.py`, `chat.py`, `snippets.py`, `snippet_manager.py`, `templates.py`, `phase_data.py`, `list_items.py`, `wizards.py`, `ai_chat.py`
- Contains: FastAPI `APIRouter` instances with path operation functions
- Depends on: `backend/app/api/dependencies.py` (auth + DB session DI), service layer, schemas
- Used by: `backend/app/main.py` router registration

**Dependency Injection (backend):**
- Purpose: Provide `db: Session` and `current_user: schemas.User` to every route handler
- Location: `backend/app/api/dependencies.py`
- Pattern: `get_db()` is a generator yielding a SQLAlchemy session; `get_current_user()` validates Bearer token against `mock-token` in dev or JWT in production
- Mock auth: `settings.ENVIRONMENT == "development"` bypasses JWT and returns a fixed mock user

**Service Layer (backend):**
- Purpose: Business logic, AI orchestration, RAG retrieval — independent of HTTP concerns
- Location: `backend/app/services/`
- Key services:
  - `agent_service.py` — `AgentService` singleton; handles multi-agent review and streaming chat; routes by `AgentType` (BOOK_BASED, TAG_BASED, ORCHESTRATOR)
  - `rag_service.py` — `RAGService`; two retrieval modes: concept-first (structured review) and semantic (chat follow-up)
  - `ai_provider.py` — Unified `chat_completion()` / `chat_completion_stream()` supporting OpenAI and Anthropic; selected by `settings.AI_PROVIDER`
  - `template_ai_service.py` — Wizard generation (idea, episode, scene, beat, script)
  - `book_processing_service.py` — Async book ingestion pipeline (extract → chunk → embed → KG)
  - `embedding_service.py` — OpenAI embedding generation via `text-embedding-3-small`
  - `knowledge_extraction_service.py` — GPT-4 concept + relationship extraction from book chunks
  - `openai_service.py` — Legacy section review via framework-aware prompts (used by `/api/review`)
  - `auth_service.py` — JWT creation/verification + mock auth
  - `document_service.py` — Book document text extraction (PDF, EPUB, TXT)
  - `agent_templates.py` — Default agent seed data

**Data Layer (backend):**
- Purpose: SQLAlchemy ORM models and raw SQL migrations
- Location: `backend/app/models/database.py`, `backend/app/db.py`, `backend/migrations/`
- Contains: All ORM models (`Project`, `Section`, `ChecklistItem`, `PhaseData`, `ListItem`, `AISession`, `AIMessage`, `Book`, `BookChunk`, `Snippet`, `Concept`, `ConceptRelationship`, `Agent`, `AgentBook`, `ChatSession`, `ChatMessage`, `WizardRun`, `ScreenplayContent`)
- DB sessions: `backend/app/db.py` creates `SessionLocal` factory; `get_db()` yields sessions as a FastAPI dependency
- Schema migrations: Plain SQL files in `backend/migrations/` (`init_db.sql`, `002_knowledge_graph.sql`, `003_template_system.sql`, `003_templates_overhaul.sql`, `004_agent_type_and_quality.sql`, `005_book_progress.sql`, `006_snippet_management.sql`, `007_snippets_table.sql`); no Alembic — applied manually

**Template Registry (backend):**
- Purpose: Load and serve JSON template definitions that drive both the frontend UI and AI context
- Location: `backend/app/templates/registry.py`, `backend/app/templates/micro_drama.json`, `backend/app/templates/short_movie.json`, `backend/app/templates/shared/write_phase.json`
- Pattern: `get_template(template_id)` loads and returns the full JSON dict; `list_templates()` returns metadata for all templates
- Used by: `template_ai_service.py`, `agent_service.py`, `phase_data.py` endpoint, `wizards.py` endpoint

**Configuration (backend):**
- Purpose: Typed settings loaded from environment variables
- Location: `backend/app/config.py`
- Pattern: `pydantic_settings.BaseSettings` subclass; instantiated once as module-level `settings` singleton; all services import `settings` directly
- Default AI provider is `"anthropic"` with model `claude-sonnet-4-6`; OpenAI fallback with `gpt-4o`

**Frontend App Shell:**
- Purpose: SPA routing, React Query provider, global layout
- Location: `frontend/src/main.tsx` → `frontend/src/App.tsx`
- `QueryClient` configured with 5-minute stale time and 1 retry
- Routes: `/` and `/projects` → `ProjectList`; `/projects/:projectId` → `Editor` (legacy); `/projects/:projectId/:phase[/:subsectionKey[/:itemId]]` → `ProjectWorkspace` (template system); `/books` → `BookManager`; `/snippets` → `SnippetManager`

**Workspace Layer (frontend):**
- Purpose: Template-driven project editing; renders the correct UI pattern per subsection
- Location: `frontend/src/components/Workspace/`
- Key components:
  - `ProjectWorkspace.tsx` — Orchestrates phase navigation + subsection routing + content area + sidebar chat
  - `ContentArea.tsx` — Switch on `subsection.ui_pattern` to render the correct Pattern view
  - `PhaseNavigation.tsx` — Top bar with phase tabs
  - `SubsectionSidebar.tsx` — Left sidebar listing subsections for the current phase

**UI Pattern Views (frontend):**
- Purpose: Pluggable content views selected by `subsection.ui_pattern`
- Location: `frontend/src/components/Patterns/`
- Pattern types: `structured_form` → `StructuredFormView`; `card_grid` → `CardGridView`; `repeatable_cards` → `RepeatableCardsView`; `wizard` / `wizard_with_chat` / `import_wizard` → `WizardView`; `ordered_list` → `OrderedListView`; `individual_editor` → `IndividualEditorView`; `screenplay_editor` → `ScreenplayEditorView`; `analyzer` → `PlaceholderView`

**API Client (frontend):**
- Purpose: Typed fetch wrapper for all backend endpoints
- Location: `frontend/src/lib/api.tsx`
- Pattern: Single `api` object with async methods; uses `fetchWithTimeout` (30s default, 120s for chat/AI); reads Bearer token from `localStorage` with fallback to `"mock-token"`

## Data Flow

**Template-driven project editing:**

1. User navigates to `/projects/:projectId/idea/premise`
2. `ProjectWorkspace` fetches project record (`GET /api/projects/:id`) and template config (`GET /api/templates/:templateId`)
3. `ContentArea` reads `subsection.ui_pattern` and renders the matching Pattern view
4. Pattern view fetches subsection content (`GET /api/phase-data/:projectId/:phase/:key`) via React Query
5. User edits fields; Pattern view calls `PATCH /api/phase-data/:projectId/:phase/:key` on change
6. React Query cache is invalidated; UI reflects saved state

**Agent-powered streaming chat:**

1. User sends message in `SidebarChat` (`frontend/src/components/Shared/SidebarChat.tsx`)
2. Frontend calls `POST /api/chat/sessions/:sessionId/messages/stream` with `field_context` payload
3. `AgentService.chat_stream_prepare()` runs semantic RAG search (via `rag_service.semantic_search()`) and builds system prompt with concept cards + book excerpts + project context
4. User message saved to `ChatMessage` table; streaming params returned
5. `chat.py` endpoint calls `ai_provider.chat_completion_stream()` and emits SSE `data:` lines
6. Frontend `SidebarChat` reads the SSE stream, accumulates chunks, renders markdown via `MarkdownContent`
7. On stream completion, `AgentService.chat_stream_finalize()` post-processes: extracts JSON blocks (`book_references`, `field_updates`, `list_item_creates`), saves `ChatMessage`, optionally creates `ListItem` records
8. Frontend receives `field_updates` in the `done` SSE event and shows a confirmation card for the user to apply

**Template-system AI chat (SidebarChat in template mode):**

1. User sends message in `SidebarChat` with `panelMode === 'template'`
2. Frontend calls `api.sendAIMessageStream()` targeting `POST /api/ai/sessions/:sessionId/messages/stream`
3. `ai_chat.py` endpoint uses `template_ai_service` to build context from all project `PhaseData`
4. Streaming response follows same SSE pattern; `field_updates` may be returned in action mode
5. Frontend shows `ProposedChangesCard` for user to accept or dismiss field-level edits

**Book processing pipeline:**

1. User uploads file at `POST /api/books/upload`
2. `books.py` saves file to `backend/uploads/:owner_id/`, creates `Book` record with `PENDING` status
3. FastAPI `BackgroundTasks` triggers `book_processing_service.process_book()`
4. Pipeline stages update `Book.status`: `EXTRACTING` → `ANALYZING` → `EMBEDDING` → `COMPLETED`
5. `document_service` extracts text; text is chunked → `knowledge_extraction_service` extracts concepts via GPT-4 → `embedding_service` generates embeddings → stored as `BookChunk` + `Concept` + `ConceptRelationship` + `Snippet` rows with pgvector embeddings

**Wizard generation:**

1. User configures wizard in `WizardView` (`frontend/src/components/Patterns/WizardView.tsx`)
2. Frontend calls `POST /api/wizards/run` with wizard type and config
3. `wizards.py` gathers full project context from all `PhaseData` records and calls `template_ai_service.wizard_generate()`
4. AI generates structured content (beats, episodes, scenes); result stored in `WizardRun.result`
5. User previews result; on confirm, `POST /api/wizards/:runId/apply` writes content into `PhaseData` / `ListItem` records

**State Management:**
- All server state managed by React Query with query keys defined in `frontend/src/lib/constants.ts` (`QUERY_KEYS`)
- No global client-side state store (no Redux, no Context); component-local `useState` for UI-only concerns (selected phase, open panels)
- Cache invalidation is manual: each mutation calls `queryClient.invalidateQueries()` on affected query keys
- Stale time: 5 minutes globally; retry: 1

## Key Abstractions

**TemplateConfig (JSON schema):**
- Purpose: Data-driven description of a screenplay format — its phases, subsections, and how each subsection should be rendered and edited
- Examples: `backend/app/templates/micro_drama.json`, `backend/app/templates/short_movie.json`
- Pattern: Loaded server-side by `backend/app/templates/registry.py`; served to frontend via `GET /api/templates/:id`; frontend types defined in `frontend/src/types/template.ts`
- Key fields on `SubsectionConfig`: `ui_pattern` (selects the React view), `fields`, `field_groups`, `wizard_config`, `list_config`, `editor_config`, `ai_actions`, `sidebar_chat`, `chat_system_prompt`

**AgentType routing:**
- Purpose: The `Agent` model has a type enum (`BOOK_BASED`, `TAG_BASED`, `ORCHESTRATOR`) that controls how `AgentService` fetches RAG context and builds system prompts
- Location: `backend/app/services/agent_service.py`
- Pattern: `chat_stream_prepare()` switches on `agent.agent_type` before calling `rag_service`; `ORCHESTRATOR` type delegates to `_orchestrate_stream_prepare()` which fans out to specialist agents in parallel via `asyncio.gather()`

**PhaseData / ListItem as generic content store:**
- Purpose: All template-system content stored as `PhaseData` (one row per project+phase+subsection_key) with a `content` JSON column; repeatable items stored as child `ListItem` rows
- Location: `backend/app/models/database.py` — `PhaseData`, `ListItem`
- Unique constraint: `(project_id, phase, subsection_key)` on `PhaseData` ensures upsert safety

**Unified AI Provider:**
- Purpose: Abstracts over OpenAI and Anthropic so service code doesn't care which LLM is active
- Location: `backend/app/services/ai_provider.py`
- Pattern: `chat_completion(messages, ...)` and `chat_completion_stream(messages, ...)` read `settings.AI_PROVIDER` to route; provider can be overridden per-call via the `provider` argument
- Handles Anthropic-specific quirks: system message extraction, message alternation rules, code fence stripping for JSON mode

**Custom Exception Hierarchy:**
- Purpose: Map business errors to HTTP status codes with structured error payloads
- Location: `backend/app/exceptions.py`
- Base class: `AppException(HTTPException)` with subclasses: `ValidationException` (400), `AuthenticationException` (401), `AuthorizationException` (403), `NotFoundException` (404), `ConflictException` (409), `RateLimitException` (429), `ExternalServiceException` / `OpenAIException` (503), `DatabaseException` (500), `ConfigurationException` (500)

**SafeVector (pgvector adapter):**
- Purpose: Custom SQLAlchemy type that safely handles both string and list representations of pgvector embeddings, avoiding the `list has no attribute split` error
- Location: `backend/app/models/database.py` — `SafeVector` class
- Used on: `BookChunk.embedding`, `Snippet.embedding`, `Concept.embedding` (all deferred-loaded, dimension 1536)

## Entry Points

**Backend HTTP server:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --reload --port 8000` (standalone) or Docker Compose `backend` service
- Responsibilities: Registers all middleware, mounts all routers under `/api/*`, registers startup/shutdown lifecycle events, initialises DB connection on startup via `init_db()`

**Frontend SPA:**
- Location: `frontend/src/main.tsx` → `frontend/src/App.tsx`
- Triggers: `npm run dev` (Vite dev server on :5173) or Docker container serving built assets
- Responsibilities: Provides `QueryClientProvider` + `BrowserRouter`; maps URL paths to top-level page components

**Background Book Processor:**
- Location: `backend/app/services/book_processing_service.py`
- Triggers: FastAPI `BackgroundTasks` after `POST /api/books/upload`
- Responsibilities: Orchestrates the extract → chunk → analyze → embed pipeline in-process (no separate worker queue or task broker)

## API Route Map

| Prefix | Router File | Domain |
|---|---|---|
| `/api/auth` | `backend/app/api/endpoints/auth.py` | Authentication (mock token, magic link) |
| `/api/projects` | `backend/app/api/endpoints/projects.py` | Project CRUD + v2 template-based creation |
| `/api/sections` | `backend/app/api/endpoints/sections.py` | Legacy section editing + checklist items |
| `/api/review` | `backend/app/api/endpoints/review.py` | Legacy AI section review |
| `/api/books` | `backend/app/api/endpoints/books.py` | Book upload, processing, CRUD |
| `/api/books` | `backend/app/api/endpoints/snippets.py` | Book-scoped snippet listing |
| `/api/snippets` | `backend/app/api/endpoints/snippet_manager.py` | Snippet CRUD (edit, delete) |
| `/api/agents` | `backend/app/api/endpoints/agents.py` | Agent CRUD, book linking, seed defaults |
| `/api/chat` | `backend/app/api/endpoints/chat.py` | Agent chat sessions + streaming messages |
| `/api/templates` | `backend/app/api/endpoints/templates.py` | Template listing + detail |
| `/api/phase-data` | `backend/app/api/endpoints/phase_data.py` | Phase data CRUD + readiness checks |
| `/api/list-items` | `backend/app/api/endpoints/list_items.py` | ListItem CRUD + reordering |
| `/api/wizards` | `backend/app/api/endpoints/wizards.py` | Wizard run + apply results |
| `/api/ai` | `backend/app/api/endpoints/ai_chat.py` | Template AI sessions, streaming, fill-blanks, give-notes, analyze-structure |
| `/health` | `backend/app/main.py` | Health check (inline) |

## Error Handling

**Strategy:** Custom exception hierarchy extending `HTTPException`; exceptions raised inside service/route code and automatically serialised by FastAPI's default exception handlers. Pydantic v2 validation errors caught with two explicit handlers in `backend/app/main.py` — one for `RequestValidationError` (422 with structured field errors) and one for `ValidationError`.

**Patterns:**
- `AppException` subclasses in `backend/app/exceptions.py` map directly to HTTP status codes (see Key Abstractions above)
- Frontend: all `api.*` methods throw `Error` on non-OK responses with descriptive messages; React Query surfaces these as `error` state in component hooks; no global error boundary present
- AI provider errors are caught within service methods and re-raised as `ExternalServiceException` / `OpenAIException`

## Cross-Cutting Concerns

**Logging:** Python `logging` module configured at INFO level in `backend/app/main.py`; `LoggingMiddleware` in `backend/app/middleware.py` logs every request with UUID request ID and duration; each service/endpoint module instantiates `logger = logging.getLogger(__name__)`; debug-level logging enabled automatically when `ENVIRONMENT=development`

**Validation:** Pydantic v2 schemas in `backend/app/models/schemas.py` validate all inbound request bodies; `field_validator` decorators enforce constraints (non-empty strings, length limits); HTML sanitization utilities in `backend/app/utils/validators.py`

**Authentication:** Bearer token auth via `HTTPBearer` FastAPI security dependency in `backend/app/api/dependencies.py`; dev shortcut: any request with token `"mock-token"` when `ENVIRONMENT=development` is authenticated as a hardcoded mock user (UUID fixed across all requests); frontend reads token from `localStorage` key `auth_token` with fallback to `"mock-token"`

---

*Architecture analysis: 2026-03-06*
