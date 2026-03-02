# External Integrations

**Analysis Date:** 2026-03-01

## APIs & External Services

**AI Models (Dual Provider Support):**
- OpenAI GPT Models
  - SDK/Client: `openai==1.12.0` (AsyncOpenAI for async operations)
  - Auth: `OPENAI_API_KEY` environment variable
  - Usage: Section reviews, content generation, embeddings
  - Models configured in `backend/app/config.py`: `OPENAI_MODEL` (default: "gpt-4o"), `EMBEDDING_MODEL` (default: "text-embedding-3-small")
  - Implementation: `backend/app/services/ai_provider.py` (unified wrapper)

- Anthropic Claude Models
  - SDK/Client: `anthropic>=0.39.0` (AsyncAnthropic for async operations)
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Usage: Alternative AI provider for chat completion and content generation
  - Models configured in `backend/app/config.py`: `ANTHROPIC_MODEL` (default: "claude-sonnet-4-6")
  - Implementation: `backend/app/services/ai_provider.py` (unified wrapper with provider switching via `AI_PROVIDER` setting)

**Vector Embeddings:**
- OpenAI Embeddings API
  - Model: `text-embedding-3-small` (configurable via `EMBEDDING_MODEL`)
  - Dimension: 1536 (configurable via `EMBEDDING_DIMENSION`)
  - Service: `backend/app/services/embedding_service.py`
  - In-memory LRU caching with 500-item max size
  - Batch processing with rate limit handling (exponential backoff: 2, 4, 8, 16, 32 seconds)

## Data Storage

**Databases:**
- PostgreSQL 15 with pgvector extension
  - Connection: `DATABASE_URL` environment variable (format: `postgresql://user:password@host:port/database`)
  - Client: SQLAlchemy 2.0.27 ORM
  - Vector Search: pgvector 0.3.6 for semantic search on embeddings
  - Initialization: SQL migrations in `backend/migrations/init_db.sql` and `backend/migrations/002_knowledge_graph.sql`
  - Tables managed directly via SQL migrations (not Alembic)

**File Storage:**
- Local filesystem only (development and Docker volumes)
  - Upload directory: `backend/uploads/` (configurable via `UPLOAD_DIR` setting)
  - Max file size: 50MB (configurable via `MAX_BOOK_SIZE_MB`)
  - Supported formats: PDF, EPUB (processed by PyPDF2 and ebooklib)
  - Storage mechanism: Docker volume `book_uploads` for persistence

**Caching:**
- In-Memory LRU Caching
  - OpenAI reviews: 100-item max (OrderedDict in `OpenAIService`)
  - Embeddings: 500-item max (OrderedDict in `EmbeddingService`)
  - TTL: 15 minutes (900 seconds, configurable via `CACHE_TTL`)
  - No external cache service (Redis, Memcached) - all in-process

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based (development MVP mode)
  - Implementation: `backend/app/services/auth_service.py`
  - Token type: Bearer tokens via Authorization header
  - Mock auth for development: `Bearer mock-token` for API testing
  - JWT signing: `python-jose[cryptography]` 3.3.0
  - Secret key: `SECRET_KEY` environment variable (must be changed in production)

**Auth Endpoints:**
- `POST /api/auth/token/mock` - Get mock token for development
- `POST /api/auth/magic-link` - Request magic link authentication
- `POST /api/auth/verify-magic-link` - Verify magic link token

## Monitoring & Observability

**Error Tracking:**
- Not detected (no Sentry, Rollbar, or similar integration)
- Standard logging via Python `logging` module to stdout

**Logs:**
- Backend: Python `logging` module with configurable levels
  - Development: DEBUG level
  - Production: INFO level
  - Log format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  - Logged to console/stdout (no file persistence configured)
- Frontend: Browser console logging only

**Monitoring Metrics:**
- Health check endpoint: `GET /health` returns `{"status": "healthy"}`
- No metrics collection (Prometheus, DataDog, etc.)

## CI/CD & Deployment

**Hosting:**
- Docker Compose for local/development deployment
- Services: PostgreSQL (db), FastAPI backend, React frontend
- Environment: Configurable via `.env` file or `docker-compose.yml` environment variables

**CI Pipeline:**
- Not detected (no GitHub Actions, GitLab CI, or other automated testing)
- Manual testing via pytest and npm scripts

**Deployment Configuration:**
- Docker Compose orchestration in `docker-compose.yml`
- Backend runs on port 8000 (Uvicorn)
- Frontend runs on port 5173 (Vite dev server in Docker)
- Database runs on port 5432 (PostgreSQL)
- Frontend proxy: Vite proxies `/api` requests to `http://localhost:8000`

## Environment Configuration

**Required env vars (Backend):**
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key (if using OpenAI)
- `ANTHROPIC_API_KEY` - Anthropic API key (if using Anthropic)
- `SECRET_KEY` - JWT signing secret
- `AI_PROVIDER` - "openai" or "anthropic" (default: "anthropic")
- `ALLOWED_ORIGINS` - CORS-allowed origins (comma-separated list)
- `ENVIRONMENT` - "development", "staging", "production"

**Optional env vars (Backend):**
- `OPENAI_MODEL` - OpenAI model name (default: "gpt-4o")
- `ANTHROPIC_MODEL` - Anthropic model name (default: "claude-sonnet-4-6")
- `EMBEDDING_MODEL` - Embedding model (default: "text-embedding-3-small")
- `EMBEDDING_DIMENSION` - Embedding vector dimension (default: 1536)
- `MAX_TOKENS` - Max tokens per API response (default: 1500)
- `MAX_SECTION_LENGTH` - Max input text length (default: 1500)
- `CACHE_TTL` - Cache time-to-live in seconds (default: 900)
- `MAX_BOOK_SIZE_MB` - Max file upload size (default: 50)
- `PORT` - Server port (default: 8000)

**Required env vars (Frontend):**
- `VITE_API_URL` - Backend API base URL (default: `http://localhost:8000/api`)

**Secrets location:**
- Development: `.env` file in project root (not committed)
- Docker Compose: `.env` file (loaded by docker-compose)
- Production: Environment variables from deployment platform (Heroku, AWS, etc.)

## Webhooks & Callbacks

**Incoming:**
- Not detected - no webhook endpoints configured

**Outgoing:**
- Not detected - no outbound webhook triggers
- Possible future: Magic link email delivery (not yet implemented)

## Rate Limiting

**API Rate Limiting:**
- RateLimitMiddleware in `backend/app/middleware.py`
- Limit: 60 requests per minute per IP
- Middleware order: Applied at request processing level

**AI API Rate Limiting:**
- OpenAI: Handled via EmbeddingService with exponential backoff (up to 32 seconds)
- Anthropic: Handled via native client rate limiting
- Retry logic: 5 attempts with exponential backoff for embedding batches

## Request Size Limits

**Backend:**
- RequestSizeLimitMiddleware in `backend/app/middleware.py`
- Max payload size: 10MB
- Applies to all POST/PATCH requests

---

*Integration audit: 2026-03-01*
