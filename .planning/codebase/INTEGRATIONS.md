# External Integrations

**Analysis Date:** 2026-07-24

## APIs & External Services

**LLM Providers (pluggable via `AI_PROVIDER`):**
- OpenAI - GPT-4o chat completions, structured output, embeddings, KG extraction
  - SDK/Client: `openai>=1.40.0` (`AsyncOpenAI`)
  - Wrapper: `backend/app/services/ai_provider.py` (unified `chat_completion`, `chat_completion_structured`, `chat_completion_stream`)
  - Auth: `OPENAI_API_KEY`; model via `OPENAI_MODEL` (default `gpt-4o`)
  - Structured output via `client.beta.chat.completions.parse()`
- Anthropic (Claude) - **default provider** (`AI_PROVIDER=anthropic`)
  - SDK/Client: `anthropic>=0.77.0` (`AsyncAnthropic`)
  - Auth: `ANTHROPIC_API_KEY`; model via `ANTHROPIC_MODEL` (default `claude-opus-4-8`)
  - Modern models (Opus 4.7/4.8, Sonnet 5, Fable 5, Mythos 5) reject `temperature`, use adaptive thinking + `output_config.effort`
  - Prompt caching: `cache_control` ephemeral marker on last system block (`cache_system=True`)
  - Clients lazy-initialized so a missing key does not crash import (CI-safe)

**Image Generation:**
- Google Vertex AI Imagen - Storyboard frame generation
  - SDK/Client: `google-cloud-aiplatform>=1.60.0` (`vertexai`, `ImageGenerationModel`)
  - Service: `backend/app/services/imagen_service.py`; endpoint `backend/app/api/endpoints/storyboard.py` (`generate storyboard frame`)
  - Auth: Application Default Credentials or service-account key + `GOOGLE_CLOUD_PROJECT`
  - Config: `IMAGEN_MODEL` (default `imagen-3.0-generate-001`), `IMAGEN_REGION` (`us-central1`)
  - Returns PNG bytes; downstream thumbnails via Pillow

**Note on Magnific / ElevenLabs:**
- No Magnific or ElevenLabs SDK/client is present in THIS backend's code or `requirements.txt`. Those services live in the separate **vapai-studio** production app (per project memory: Magnific + ElevenLabs keys configured on vapai's worker). This app reaches them only indirectly by pushing screenplays into vapai-studio (see vapai bridge below).

## Data Storage

**Databases:**
- PostgreSQL 15 (image `pgvector/pgvector:pg15`)
  - Connection: `DATABASE_URL` (default `postgresql://user:password@localhost:5432/screenwriter_db`)
  - Client/ORM: SQLAlchemy 2.0 (`backend/app/models/database.py`), `psycopg2-binary` driver
  - Schema bootstrap: `backend/migrations/init_db.sql` (mounted as docker-entrypoint init), plus delta migrations in `backend/migrations/` and `db_migrator.py` / `init_db()`
  - Data model: Project → Section → ChecklistItem (cascade); plus Book/BookChunk/Concept/ConceptRelationship, Agent/AgentBook, Show/Season/EpisodeSlot/Episode, Snippet, templates, shots, storyboard frames

**Vector Store (RAG):**
- pgvector extension in the same Postgres DB
  - 1536-dim embeddings (`text-embedding-3-small`) on `Concept`, `BookChunk`, and a third embedding table (`deferred` `SafeVector(1536)` columns)
  - `SafeVector` custom SQLAlchemy type handles psycopg2 list-vs-string adapter quirk
  - RAG service: `backend/app/services/rag_service.py` (concept-first + semantic modes)
  - Embeddings: `backend/app/services/embedding_service.py` (OpenAI, in-memory LRU cache 500, batch w/ exponential backoff on rate limits)

**File Storage:**
- Local filesystem only
  - Uploads: `UPLOAD_DIR` (`backend/uploads/`) — book/document ingestion
  - Media: `MEDIA_DIR` (`backend/media/`, thumbnails under `media/thumbs/`) — served at `/media` static mount
  - In Docker persisted via named volumes `book_uploads`, `media_uploads`

**Caching:**
- In-memory only (no Redis/Memcached)
  - OpenAI response cache 15-min TTL (`openai_service.py`, `CACHE_TTL=900`)
  - Embedding query LRU cache (`embedding_service.py`)

## Authentication & Identity

**App auth (REST):**
- Custom JWT (`backend/app/services/auth_service.py`) — HS256, `SECRET_KEY`, 7-day access tokens, magic-link tokens (15-min), bcrypt password hashing
- Mock auth for MVP dev: `MockAuthService` returns a fixed dev user; frontend falls back to `Bearer mock-token` when no token in localStorage (`frontend/src/lib/api.tsx`)
- 401 on any non-auth call clears token and hard-redirects to `/login`
- DI wiring: `backend/app/api/dependencies.py`

**MCP auth (agent access):**
- Static bearer API keys `sa_<key>` (the v5.0 key gateway reused)
  - Verifier: `backend/app/mcp_server/auth.py` (`ApiKeyTokenVerifier` — non-incrementing 401 gate; `require_user` reads header fresh, atomically increments `request_count`/`last_used_at`, resolves owning user)
  - Every MCP tool is owner-scoped to the key; no per-tool scopes yet (a valid key grants all tools)

**Admin gate:**
- `ADMIN_EMAILS` (comma-separated) — global book/agent/snippet library is readable by all authed users but writable only by listed emails (open in dev mock auth, locked in prod)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry/Rollbar). Custom exception hierarchy mapped to HTTP status codes (`backend/app/exceptions.py`)

**Logs:**
- Python `logging` to stdout (`main.py` basicConfig), `LoggingMiddleware` for requests. No aggregation service.

**Health:**
- `GET /health` (used by Railway healthcheck)

## CI/CD & Deployment

**Hosting:**
- Backend: Railway (Dockerfile builder, `backend/railway.json`, `targetPort=8000`, host `web-production-73857`). Start command persists in Railway dashboard.
- Frontend: Vercel (`frontend/vercel.json`, SPA rewrites), domain `guion.vapai.studio`

**CI Pipeline:**
- GitHub Actions present (`.github/` at repo root) — backend pytest with rerun-failures for known flakes
- Local convention: auto commit + push to `main` after tests/typecheck pass

## Environment Configuration

**Required env vars (backend):**
- `DATABASE_URL`, `OPENAI_API_KEY` (import-time requirement in prod), `SECRET_KEY`, `ALLOWED_ORIGINS`
- `ANTHROPIC_API_KEY` (when `AI_PROVIDER=anthropic`, the default)
- Imagen: `GOOGLE_CLOUD_PROJECT` (+ GCP credentials)
- vapai bridge: `VAPAI_MCP_URL`, `VAPAI_MCP_API_KEY`, `VAPAI_WEB_URL` (see below)

**Required env vars (frontend):**
- `VITE_API_URL`, `VITE_PROXY_TARGET`

**Secrets location:**
- Backend: Railway dashboard env vars; local `.env` (git-ignored). Never commit.
- Frontend: Vercel project env vars
- vapai MCP token also referenced from `~/.claude.json` for the MCP client tooling (per project memory). Gotcha: CRLF in `.env.local` files.

## MCP Server (exposed by this backend)

- FastMCP server mounted in-process at **`/mcp`** over Streamable HTTP / JSON-RPC (`backend/app/mcp_server/server.py`), `stateless_http=True`, `json_response=True`
- Lifespan-critical: MCP session manager must run for full app lifetime or tools fail with "Task group is not initialized" (composed into app lifespan in `main.py`)
- Auth: `sa_` bearer API keys, owner-scoped (see MCP auth above)
- DNS-rebinding protection off by default (`MCP_DNS_REBINDING_PROTECTION`); auth is primary defense
- Tool docstring `_INSTRUCTIONS` describes the canonical screenplay-production pipeline injected into connecting agents

**Registered tools** (`backend/app/mcp_server/tools/`):
- Transport/auth: `ping`, `whoami`
- Core (`core.py`): `job_status` (poll LONG-RUNNING jobs → `{job_id}` async pattern)
- Screenwriting (`screenwriting.py`): `screenplay_read`, `screenplay_write`, `screenplay_generate_scene`
- Management (`management.py`): `project_list`, `project_get`, `project_create`, `show_list`, `show_create`, `show_read_bible`, `bible_write`, `bible_draft`, `season_create`, `slot_create`, `episode_list`, `episode_create`
- Breakdown (`breakdown.py`): `breakdown_extract`, `breakdown_read`
- Shotlist (`shotlist.py`): `shotlist_read`, `shotlist_generate`, `shot_create`
- Async jobs backed by `backend/app/mcp_server/jobs.py`; DB session via `session.py`; request context via `context.py`

## vapai-studio Bridge (outbound integration)

- Service: `backend/app/services/vapai_service.py` — pushes a finished screenplay INTO the separate vapai-studio production app
- Transport: vapai-studio's own FastMCP HTTP endpoint (Streamable HTTP, JSON-RPC 2.0, protocol version `2025-06-18`)
- Auth: shared bearer token `VAPAI_MCP_API_KEY` matching vapai's `MCP_API_KEY` (service-to-service; vapai resolves owner from its `DEFAULT_USER_ID` or passed `user_id`). Auth header sent only when key present.
- Config gate: empty `VAPAI_MCP_URL` disables the feature; endpoint returns HTTP 424. Other knobs: `VAPAI_WEB_URL` (deep-link base), `VAPAI_DEFAULT_USER_ID`, `VAPAI_TIMEOUT_SECONDS` (30s), `VAPAI_PROJECT_TYPE`
- Remote tools called on vapai: `create_project`, `create_episode`, `create_script` (+ bible refresh on the series project)
- Two entry points: `send_screenplay` (one episode) and `send_series` (whole show as vapai `type="series"`). Only ingestion (project → episode → script + bible); breakdown/scene-shot extraction is intentionally NOT triggered — the user runs it inside vapai-studio.
- Frontend types: `SendToVapaiResponse`, `SendSeriesToVapaiResponse` (`frontend/src/types`)

## Webhooks & Callbacks

**Incoming:**
- None (no webhook receiver endpoints)

**Outgoing:**
- vapai-studio JSON-RPC calls (above) — the only outbound service-to-service integration

---

*Integration audit: 2026-07-24*
