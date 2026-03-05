# External Integrations

**Analysis Date:** 2026-03-05

## APIs & External Services

**Large Language Models:**
- **OpenAI** - GPT-4 chat completions and embeddings
  - SDK/Client: `openai` (1.12.0)
  - Auth: Environment variable `OPENAI_API_KEY`
  - Models: `gpt-4o` (chat), `text-embedding-3-small` (embeddings)
  - Used by: `backend/app/services/ai_provider.py`, `backend/app/services/embedding_service.py`

- **Anthropic** - Claude chat completions (alternative provider)
  - SDK/Client: `anthropic` (>=0.39.0)
  - Auth: Environment variable `ANTHROPIC_API_KEY`
  - Model: `claude-sonnet-4-6` (configurable)
  - Used by: `backend/app/services/ai_provider.py`
  - Provider Selection: Controlled by `AI_PROVIDER` config (default: "anthropic")

## Data Storage

**Databases:**
- **PostgreSQL 15**
  - Connection: Environment variable `DATABASE_URL` (via `backend/app/config.py`)
  - Client: psycopg2-binary 2.9.9
  - ORM: SQLAlchemy 2.0.27
  - Location: Container service `db` in `docker-compose.yml`
  - Schema: Defined in `backend/migrations/` (5 migration files)
  - Vector Storage: pgvector 0.3.6 extension for embeddings

**File Storage:**
- **Local filesystem** - Document uploads via `backend/uploads/` directory
  - Mounted volume: `book_uploads` in Docker Compose
  - Path configured: `backend/app/config.py` → `UPLOAD_DIR`
  - Max file size: `MAX_BOOK_SIZE_MB` (default: 50MB)
  - Supported formats: PDF (PyPDF2), EPUB (ebooklib)

**Caching:**
- **In-memory** - No external cache service
  - Query response caching: 15-minute TTL in services
  - Embedding LRU cache: 500-item max in `backend/app/services/embedding_service.py`

## Authentication & Identity

**Auth Provider:**
- **Custom JWT-based (Mock for MVP)**
  - Implementation: `backend/app/services/auth_service.py`
  - Token: Mock token `"mock-token"` used in development
  - Endpoint: `POST /api/auth/token/mock` (development only)
  - Token storage (frontend): `localStorage` with key `AUTH_TOKEN_KEY`
  - Token format: Bearer token in `Authorization` header
  - Libraries: python-jose 3.3.0 (JWT), passlib 1.7.4 (password hashing)
  - Middleware: `backend/app/middleware.py` → `SecurityMiddleware`

## Monitoring & Observability

**Error Tracking:**
- Not detected - No error tracking service integrated

**Logs:**
- **Standard logging** - Python logging module
  - Configuration: `backend/app/main.py` → `logging.basicConfig()`
  - Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Levels: DEBUG in development, INFO in production
  - Middleware logging: `backend/app/middleware.py` → `LoggingMiddleware`

## CI/CD & Deployment

**Hosting:**
- Docker Compose (local/self-hosted) - All services containerized
- No cloud platform integration detected

**CI Pipeline:**
- Not detected - No GitHub Actions, GitLab CI, or other CI service configured

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key (must not be default in production)
- `OPENAI_API_KEY` - Required if using OpenAI provider
- `ANTHROPIC_API_KEY` - Required if using Anthropic provider
- `AI_PROVIDER` - Either "openai" or "anthropic" (default: "anthropic")
- `POSTGRES_PASSWORD` - PostgreSQL password (required for Docker)

**Optional env vars:**
- `POSTGRES_USER` - PostgreSQL username (default: "screenwriter")
- `POSTGRES_DB` - PostgreSQL database name (default: "screenwriter_db")
- `ENVIRONMENT` - "development", "staging", or "production" (default: "development")
- `OPENAI_MODEL` - OpenAI model name (default: "gpt-4o")
- `ANTHROPIC_MODEL` - Anthropic model name (default: "claude-sonnet-4-6")
- `EMBEDDING_MODEL` - Embedding model (default: "text-embedding-3-small")
- `ALLOWED_ORIGINS` - CORS allowlist JSON array
- `MAX_TOKENS` - Max response tokens (default: 1500)
- `CACHE_TTL` - Cache TTL in seconds (default: 900)
- `VITE_API_URL` - Frontend API base URL (docker-compose: "http://localhost:8000/api")

**Secrets location:**
- Development: `.env` file (not committed, see `.gitignore`)
- Production: Environment variables passed to Docker containers (via docker-compose.yml)
- Docker Compose uses conditional env var injection (e.g., `${OPENAI_API_KEY:?OPENAI_API_KEY must be set}`)

## Webhooks & Callbacks

**Incoming:**
- Not detected - No webhook ingestion endpoints

**Outgoing:**
- Not detected - No outbound webhook triggers

## AI Service Integration Details

**Chat Completion Flow:**
- All AI requests route through `backend/app/services/ai_provider.py`
- Unified `chat_completion()` function supports both OpenAI and Anthropic
- Supports both standard and streaming responses
- Request: `messages` list (system/user/assistant roles), `temperature`, `max_tokens`
- Response: Text content string (auto-extracted from provider response)

**Embedding Service:**
- Dedicated `backend/app/services/embedding_service.py`
- Uses OpenAI's `text-embedding-3-small` model
- Features: LRU in-memory caching (500 items), batch processing (50 items/batch)
- Rate limit handling: Exponential backoff retry (2^attempt * 2 seconds, max 5 attempts)
- Storage: Vectors stored in PostgreSQL via pgvector extension

**Knowledge Graph & RAG:**
- Document embeddings stored in `pgvector` for semantic search
- Service: `backend/app/services/rag_service.py`
- Token counting via `tiktoken` for accurate prompt sizing
- Document processing: `backend/app/services/book_processing_service.py`

---

*Integration audit: 2026-03-05*
