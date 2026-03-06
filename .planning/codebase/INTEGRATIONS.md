# External Integrations

**Analysis Date:** 2026-03-06

## APIs & External Services

**Large Language Models:**

- **Anthropic Claude** - Primary AI provider for chat completions (default)
  - SDK/Client: `anthropic` (>=0.39.0)
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Model: `ANTHROPIC_MODEL` env var (default: `claude-sonnet-4-6`)
  - Capabilities used: non-streaming chat, streaming chat
  - Implementation: `backend/app/services/ai_provider.py` → `_anthropic_completion()`, `_anthropic_stream()`
  - System prompt handling: Extracted from messages list and passed as top-level `system` param

- **OpenAI GPT-4** - Secondary AI provider and embeddings (always used for embeddings)
  - SDK/Client: `openai` 1.12.0
  - Auth: `OPENAI_API_KEY` environment variable
  - Chat model: `OPENAI_MODEL` env var (default: `gpt-4o`)
  - Embedding model: `EMBEDDING_MODEL` env var (default: `text-embedding-3-small`, dimension: 1536)
  - Capabilities used: chat completions, JSON mode, streaming, batch embeddings
  - Implementation: `backend/app/services/ai_provider.py`, `backend/app/services/embedding_service.py`
  - Knowledge extraction always uses `gpt-4` (via `KG_EXTRACTION_MODEL` config in `backend/app/config.py`)

**Provider Switching:**
- Controlled by `AI_PROVIDER` env var ("openai" or "anthropic")
- All chat routes through unified `chat_completion()` in `backend/app/services/ai_provider.py`
- Embeddings are always OpenAI regardless of `AI_PROVIDER` setting
- Clients are lazy-initialized to avoid startup errors when a key is missing

## Data Storage

**Databases:**
- **PostgreSQL 15 with pgvector extension**
  - Connection: `DATABASE_URL` environment variable
  - Format: `postgresql://user:password@host:5432/dbname`
  - Client: psycopg2-binary 2.9.9
  - ORM: SQLAlchemy 2.0.27 (synchronous sessions via `SessionLocal`)
  - Session management: `backend/app/db.py` → `get_db()` dependency
  - Vector columns: Custom `SafeVector` type in `backend/app/models/database.py` (handles psycopg2 list/string format differences)
  - Embedding dimension: 1536 (matches `text-embedding-3-small`)

**Database Schema (Migration Files):**
- `backend/migrations/init_db.sql` - Core tables: projects, sections, checklist_items
- `backend/migrations/002_knowledge_graph.sql` - Books, chunks, concepts, relationships, agents
- `backend/migrations/003_template_system.sql` - Template system: phase_data, list_items, ai_sessions, ai_messages, wizard_runs, screenplay_content
- `backend/migrations/004_agent_type_and_quality.sql` - Agent type enum, quality score columns
- `backend/migrations/005_book_progress.sql` - Book processing progress tracking
- `backend/migrations/006_snippet_management.sql` - Snippet soft-delete and user-created flags
- `backend/migrations/007_snippets_table.sql` - Dedicated snippets table

**File Storage:**
- **Local filesystem** only — no cloud object storage
  - Upload directory: `backend/uploads/` (configured via `UPLOAD_DIR` in `backend/app/config.py`)
  - Docker volume: `book_uploads` (persisted across container restarts)
  - Max file size: `MAX_BOOK_SIZE_MB` (default: 50MB)
  - Supported formats: PDF (PyPDF2), EPUB (ebooklib)
  - Processing: `backend/app/services/document_service.py`, `backend/app/services/book_processing_service.py`

**Caching:**
- **In-memory only** — no Redis, Memcached, or external cache
  - AI response cache (LRU, 100 items): `backend/app/services/openai_service.py` — `OpenAIService.cache`
  - Embedding cache (LRU, 500 items): `backend/app/services/embedding_service.py` — `EmbeddingService._cache`
  - Cache keys: MD5 hash of content
  - Cache TTL: configured by `CACHE_TTL` (default: 900 seconds / 15 min)
  - Note: Cache is process-local and does not persist across restarts

## Authentication & Identity

**Auth Provider:**
- **Custom JWT (Mock implementation for MVP)**
  - Implementation: `backend/app/services/auth_service.py`
  - JWT library: python-jose 3.3.0, algorithm: HS256
  - Token expiry: 7 days for access tokens, 15 minutes for magic link tokens
  - Password hashing: passlib 1.7.4 with bcrypt
  - Development mock: `MockAuthService` returns fixed user `12345678-1234-5678-1234-567812345678`
  - Mock token string: `"mock-token"` accepted in all API tests
  - Frontend storage: `localStorage` key `AUTH_TOKEN_KEY`
  - Request header format: `Authorization: Bearer <token>`
  - Auth endpoints: `backend/app/api/endpoints/auth.py` → `/api/auth`
  - Dependencies: `backend/app/api/dependencies.py` → `get_current_user()`

## Monitoring & Observability

**Error Tracking:**
- Not integrated — no Sentry, Datadog, or similar service

**Logs:**
- Python `logging` module (standard library only)
- Configuration: `backend/app/main.py` → `logging.basicConfig()`
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Levels: DEBUG in development, INFO in production (controlled by `ENVIRONMENT` config)
- Request/response logging: `backend/app/middleware.py` → `LoggingMiddleware` (logs method, path, client IP, status, duration, request ID)

**Performance Metrics:**
- Not integrated — no APM service

## CI/CD & Deployment

**Hosting:**
- Docker Compose (local/self-hosted) — all services defined in `docker-compose.yml`
- No cloud platform (AWS, GCP, Azure, Vercel, Railway, etc.) configured

**CI Pipeline:**
- Not configured — no GitHub Actions, GitLab CI, CircleCI, or other CI service

## Environment Configuration

**Required env vars (will fail or warn if missing):**
- `DATABASE_URL` - Full PostgreSQL connection string
- `SECRET_KEY` - JWT signing secret (startup warning if default value used)
- `POSTGRES_PASSWORD` - Required by `docker-compose.yml` (no default allowed)
- `OPENAI_API_KEY` - Required if `AI_PROVIDER=openai` or for embeddings
- `ANTHROPIC_API_KEY` - Required if `AI_PROVIDER=anthropic` (default provider)

**Optional env vars with defaults:**
- `AI_PROVIDER` - "openai" or "anthropic" (default: "anthropic")
- `OPENAI_MODEL` - (default: "gpt-4o")
- `ANTHROPIC_MODEL` - (default: "claude-sonnet-4-6")
- `EMBEDDING_MODEL` - (default: "text-embedding-3-small")
- `EMBEDDING_DIMENSION` - (default: 1536)
- `ENVIRONMENT` - "development", "staging", "production" (default: "development")
- `ALLOWED_ORIGINS` - JSON array of allowed CORS origins (default: localhost:5173, localhost:3000)
- `MAX_TOKENS` - AI response token limit (default: 4000)
- `MAX_SECTION_LENGTH` - Max section text length (default: 1500 chars)
- `CACHE_TTL` - Cache TTL seconds (default: 900)
- `MAX_BOOK_SIZE_MB` - Max upload size (default: 50)
- `CHUNK_SIZE_TOKENS` - Book chunking size (default: 750)
- `CHUNK_OVERLAP_TOKENS` - Chunk overlap (default: 150)
- `MAX_CHUNKS_PER_RETRIEVAL` - RAG retrieval limit (default: 6)
- `MAX_CONCEPTS_PER_REVIEW` - Agent concept limit (default: 10)
- `KG_EXTRACTION_MODEL` - Model for knowledge graph extraction (default: "gpt-4")
- `MAX_AGENTS_PER_REVIEW` - Max agents per review (default: 5)
- `AGENT_REVIEW_TIMEOUT` - Agent timeout seconds (default: 90)
- `VITE_API_URL` - Frontend API base URL (frontend, default: "/api" in Docker)

**Secrets location:**
- Development: `.env` file at project root or `backend/.env` (not committed)
- Production: Environment variables injected into Docker containers via `docker-compose.yml`
- `docker-compose.yml` uses `${VAR:?error}` syntax to enforce required vars at startup

## Webhooks & Callbacks

**Incoming:**
- Not implemented — no webhook endpoints

**Outgoing:**
- Not implemented — no outbound webhooks

## AI Service Integration Details

**Unified Chat Completion Pattern:**
```python
# All AI calls go through this interface in backend/app/services/ai_provider.py
await chat_completion(messages=[...], temperature=0.7, max_tokens=2000, json_mode=True)
await chat_completion_stream(messages=[...], temperature=0.7, max_tokens=2000)
```

**Streaming Response Pattern:**
- Used in: `backend/app/api/endpoints/ai_chat.py`, `backend/app/api/endpoints/chat.py`
- Returns: `StreamingResponse` with `text/event-stream` content type
- Yields text chunks from `chat_completion_stream()` async generator

**Embedding Pipeline:**
```python
# In backend/app/services/embedding_service.py
await embedding_service.embed_text(text)          # Single embedding, cached
await embedding_service.embed_batch(texts, batch_size=50)  # Batched with rate limit retry
```

**Knowledge Graph Extraction:**
- Service: `backend/app/services/knowledge_extraction_service.py`
- Uses `KG_EXTRACTION_MODEL` (default: "gpt-4") via OpenAI directly
- Extracts: concepts, relationships, definitions, examples, actionable questions
- Stores: `backend/app/models/database.py` → `Concept`, `ConceptRelationship` tables

**RAG Retrieval:**
- Service: `backend/app/services/rag_service.py`
- Mode 1 (concept-first): Queries concepts by `section_relevance` score, traverses relationships
- Mode 2 (semantic): Embeds user message, searches concept + chunk embeddings via pgvector
- Max retrieval: `MAX_CHUNKS_PER_RETRIEVAL` (default: 6 chunks)

---

*Integration audit: 2026-03-06*
