# External Integrations

**Analysis Date:** 2026-03-11

## APIs & External Services

**AI Providers (Dual-Provider Support):**

1. **OpenAI**
   - What it's used for: LLM completions, embeddings, knowledge graph extraction, structured JSON responses
   - SDK/Client: `openai` v1.12.0
   - Auth: `OPENAI_API_KEY` environment variable
   - Models supported:
     - `gpt-4o` (default chat model)
     - `gpt-4` (knowledge graph extraction, `KG_EXTRACTION_MODEL`)
     - `text-embedding-3-small` (embeddings, default 1536 dimensions)
   - Implementation: `backend/app/services/ai_provider.py` → `_openai_completion()`, `_openai_stream()`
   - Rate limit handling: Exponential backoff in embedding service

2. **Anthropic**
   - What it's used for: LLM completions, streaming responses, agent-based reviews
   - SDK/Client: `anthropic` >=0.39.0
   - Auth: `ANTHROPIC_API_KEY` environment variable
   - Models supported:
     - `claude-sonnet-4-6` (default chat model)
   - Implementation: `backend/app/services/ai_provider.py` → `_anthropic_completion()`, `_anthropic_stream()`
   - JSON mode support: Manual instruction appending to system prompt

**Provider Selection:**
- Active provider configured via `AI_PROVIDER` env var ("openai" or "anthropic")
- Lazy client initialization (missing API keys don't crash on import)
- Unified interface: `chat_completion()` and `chat_completion_stream()` in `ai_provider.py`

## Data Storage

**Primary Database:**
- **PostgreSQL 15 with pgvector extension**
  - Docker image: `pgvector/pgvector:pg15`
  - Connection: `DATABASE_URL` environment variable
  - ORM: SQLAlchemy 2.0.27
  - Client: `psycopg2-binary` 2.9.9
  - Database name (default): "screenwriter_db"
  - Tables: 24+ (projects, sections, books, concepts, agents, chat sessions, etc.)
  - Vector support: SafeVector custom type for embeddings (1536-dimensional)

**File Storage:**
- Local filesystem only
- Upload directory: `backend/uploads/` (configurable via `UPLOAD_DIR`)
- Volumes: `book_uploads` (Docker Compose)
- File types supported: PDF (PyPDF2), EPUB (ebooklib)
- Max file size: 50MB (configurable via `MAX_BOOK_SIZE_MB`)
- Tracking: Filename and metadata stored in `Book` table

**Caching:**
- In-memory only (no Redis)
- Backend caches:
  - OpenAI embedding query results (500-item LRU cache in `EmbeddingService`)
  - AI response caching (15-minute TTL, configurable via `CACHE_TTL`)
- Frontend: React Query with 5-minute stale time default

## Authentication & Identity

**Auth Provider:**
- Custom implementation (mock auth for MVP)
- Implementation: `backend/app/services/auth_service.py`
- Auth method: Mock token ("mock-token" for development)
- JWT support: `python-jose[cryptography]` 3.3.0
- Password hashing: `passlib[bcrypt]` 1.7.4
- Token storage (frontend): `localStorage`
- Token format: Bearer token in Authorization header

**User Identity:**
- Owner ID: UUID (tracked in projects, books, agents, chat sessions)
- No password-based authentication in MVP
- Session tracking: Per-project and per-chat session

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Rollbar, etc.)

**Logs:**
- Standard Python logging (`logging` module)
- Log level: INFO (development: DEBUG)
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Log files: Console output only
- Custom middleware logging: `LoggingMiddleware` in `backend/app/middleware.py`

**Middleware Instrumentation:**
- `LoggingMiddleware` - Request/response logging
- `SecurityMiddleware` - Security header enforcement
- `RateLimitMiddleware` - 600 requests/minute (development), configurable for production
- `RequestSizeLimitMiddleware` - 10MB request limit

## CI/CD & Deployment

**Hosting:**
- Not preconfigured (infrastructure-agnostic)
- Container-ready: Docker & Docker Compose provided

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, etc.)

**Containerization:**
- Docker Compose orchestration: 3 services (db, backend, frontend)
- Backend: `Dockerfile` with Python 3.11-slim, Uvicorn
- Frontend: `Dockerfile` with Node 18-alpine, Vite dev server
- Database: Pre-built pgvector/pgvector:pg15 image

## Environment Configuration

**Required Environment Variables:**
- `POSTGRES_PASSWORD` - Database password (Docker Compose requirement)
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - AI provider key (at least one required)
- `SECRET_KEY` - JWT signing key (must be changed from default in production)

**Optional Environment Variables:**
- `DATABASE_URL` - PostgreSQL URL (default: postgresql://user:password@localhost:5432/screenwriter_db)
- `AI_PROVIDER` - "openai" or "anthropic" (default: "anthropic")
- `OPENAI_MODEL` - (default: "gpt-4o")
- `ANTHROPIC_MODEL` - (default: "claude-sonnet-4-6")
- `ALLOWED_ORIGINS` - CORS whitelist JSON (default: localhost:5173, localhost:3000, localhost:5174)
- `ENVIRONMENT` - "development" | "staging" | "production"
- `DEBUG` - True/False (auto-set from ENVIRONMENT)
- `EMBEDDING_MODEL` - (default: "text-embedding-3-small")
- `MAX_TOKENS`, `MAX_SECTION_LENGTH`, `CACHE_TTL` - Performance tuning
- `POSTGRES_USER`, `POSTGRES_DB` - Database credentials

**Secrets Location:**
- Backend: `.env` file (git-ignored)
- Frontend: Environment variables at build/deploy time
- Docker Compose: `.env` file for service configuration

**Configuration Validation:**
- Pydantic v2 field validators in `backend/app/config.py`
- Production validation: Rejects default SECRET_KEY, warns on localhost in ALLOWED_ORIGINS
- Environment validation: Enforces valid values (development/staging/production)

## Webhooks & Callbacks

**Incoming:**
- Not detected (no webhook endpoints)

**Outgoing:**
- Not detected (API clients only, no outbound callbacks)

## Third-Party Integrations Used in Data Processing

**Document Processing:**
- **PyPDF2 3.0.1** - PDF text extraction
- **ebooklib 0.18** - EPUB ebook processing
- **BeautifulSoup4 4.12.3** - HTML/XML parsing from extracted documents

**Embeddings & Vector Search:**
- **pgvector** - PostgreSQL vector storage and similarity search
- **Embeddings generated via OpenAI API** (text-embedding-3-small, 1536 dimensions)
- **tiktoken 0.7.0** - OpenAI token counting for input size tracking

## Database Schema Highlights

**Core Tables:**
- `projects` - Screenplay projects with framework/template selection
- `sections` - Legacy section system (deprecated in favor of phase_data)
- `phase_data` - Template system with phases (idea, story, scenes, write)
- `list_items` - Ordered content items within phase data

**Book Processing:**
- `books` - Uploaded books with processing status tracking
- `book_chunks` - Document chunks with embeddings
- `snippets` - User-created or extracted snippets with vectors
- `concepts` - Knowledge graph nodes extracted from books
- `concept_relationships` - Graph edges (depends_on, related_to, part_of, example_of, contradicts, extends)

**AI & Chat:**
- `ai_sessions` - Scoped chat contexts (project + phase + subsection)
- `ai_messages` - Message history with metadata
- `chat_sessions` - Agent-based chat conversations
- `chat_messages` - Agent chat history with book references and agent consultation log
- `wizard_runs` - Results of automated generation wizards

**Agents & Configuration:**
- `agents` - Custom AI agents (book-based, tag-based, orchestrator)
- `agent_books` - Association table for agent-book relationships
- `screenplay_content` - Generated screenplay formatted output

---

*Integration audit: 2026-03-11*
