# Technology Stack

**Analysis Date:** 2026-07-24

## Languages

**Primary:**
- Python 3.11 - Backend API, services, MCP server (`backend/app/`). Pinned via `backend/Dockerfile` (`python:3.11-slim`). Note: Python 3.14 breaks SQLAlchemy/tiktoken — use 3.11.
- TypeScript ~5.2 - Frontend SPA (`frontend/src/`). Strict-ish React app under Vite.

**Secondary:**
- SQL - Postgres init + migrations (`backend/migrations/init_db.sql`, `backend/migrations/`)
- Bash - Dev/seed scripts (`backend/dev.sh`, `backend/scripts/`, `scripts/`)

## Runtime

**Backend Environment:**
- Python 3.11 (CPython, `python:3.11-slim` base image)
- ASGI server: Uvicorn (`uvicorn>=0.31.1`) running `app.main:app`
- `PYTHONPATH=/app` required (set in `backend/Dockerfile`)

**Frontend Environment:**
- Node.js (no `.nvmrc` pin present) — build via Vite 5, dev server on port 4321
- Browser SPA (React 18), served statically after build

**Package Managers:**
- Backend: `pip` + `backend/requirements.txt` (no hash-locked lockfile; versions pinned inline with rationale comments)
- Frontend: `npm` + `frontend/package.json`; lockfile `frontend/package-lock.json` **present**

## Frameworks

**Backend Core:**
- FastAPI `0.110.0` - HTTP API framework (`backend/app/main.py`). Middleware stack order matters: RateLimit → RequestSizeLimit → Security → Logging.
- Starlette `>=0.36.3,<0.37` - ASGI foundation. **Pinned** to FastAPI 0.110's range to stop `sse-starlette` pulling Starlette 1.x (MCP constraint).
- Pydantic v2 (`pydantic[email]>=2.10`) + `pydantic-settings>=2.6` - Schemas (`backend/app/models/schemas.py`) and env-driven config (`backend/app/config.py`)
- SQLAlchemy `2.0.27` - ORM (`backend/app/models/database.py`)

**Frontend Core:**
- React `^18.2.0` + React DOM - UI (`frontend/src/`)
- Vite `^5.1.0` (`@vitejs/plugin-react`) - Build/dev tooling (`frontend/vite.config.ts`)
- React Router DOM `^6.21.3` - Routing (`/`, `/projects/:projectId`, `/login`, plus show/season/breakdown/storyboard routes)
- TanStack React Query `^5.20.1` - Server-state management (5-min stale time; not Redux/Context)
- Tailwind CSS `^3.4.1` + PostCSS + autoprefixer - Styling (`frontend/tailwind.config.js`, HSL CSS-variable theming)
- Radix UI primitives - dialog, dropdown-menu, select, slot, tabs, toast
- Supporting UI: `lucide-react` (icons), `@hello-pangea/dnd` (drag-and-drop), `react-markdown` + `remark-gfm` (markdown), `class-variance-authority`, `clsx`, `tailwind-merge`

**MCP (Model Context Protocol) Server:**
- `mcp>=1.27.2,<2.0` - Official modelcontextprotocol/python-sdk. FastMCP server mounted in-process at `/mcp` over Streamable HTTP (`backend/app/mcp_server/server.py`)
- `sse-starlette<2.2` - SSE transport support (kept within Starlette <0.37 line)

**Testing:**
- pytest `8.0.2` + `pytest-asyncio 0.23.5` + `pytest-cov 4.1.0` - Backend tests (`backend/app/tests/`, config `backend/pytest.ini`)
- `pytest-rerunfailures 14.0` - Absorbs documented suite-isolation flakes in CI
- `httpx>=0.25.0,<0.28.0` - Test client / async HTTP (also used by `vapai_service`)
- Frontend: **no test runner configured** (only ESLint)

**Build/Dev (Frontend):**
- ESLint `^8.56.0` + `@typescript-eslint/*` `^6.21.0` + react-hooks / react-refresh plugins
- TypeScript compiler (`tsc && vite build`)

## Key Dependencies

**AI / LLM:**
- `openai>=1.40.0` - GPT-4o chat, `text-embedding-3-small` embeddings, knowledge-graph extraction
- `anthropic>=0.77.0` - Claude models (default provider). Supports modern Opus 4.7/4.8, Sonnet 5, Fable 5, Mythos 5 request surface (no temperature, adaptive thinking, `output_config.effort`) plus prompt caching (`cache_control` ephemeral blocks)
- `tiktoken 0.7.0` - Token counting / chunking

**Vector Search / RAG:**
- `pgvector 0.3.6` - Postgres vector extension bindings. Custom `SafeVector` SQLAlchemy type handles list/string adapter mismatch (`backend/app/models/database.py`). 1536-dim embeddings on Concept/BookChunk tables (`deferred` columns).
- `numpy>=1.24.0` - Vector math

**Document Processing (book ingestion):**
- `PyPDF2 3.0.1` - PDF text extraction
- `ebooklib 0.18` + `beautifulsoup4 4.12.3` - EPUB extraction (`backend/app/services/document_service.py`)

**Image / Media:**
- `Pillow>=12.0` - WebP thumbnail generation (`backend/app/services/media_service.py`)
- `google-cloud-aiplatform>=1.60.0` - Google Vertex AI Imagen storyboard frame generation (`backend/app/services/imagen_service.py`)

**Database Driver:**
- `psycopg2-binary 2.9.9` - PostgreSQL driver

**Auth / Security:**
- `python-jose[cryptography] 3.3.0` - JWT encode/decode (`backend/app/services/auth_service.py`, HS256, 7-day tokens)
- `passlib[bcrypt] 1.7.4` + `bcrypt<4.1` - Password hashing. **bcrypt pinned <4.1** (passlib 1.7.4 incompatible with 4.1+ 72-byte check)
- `python-multipart 0.0.9` - File upload form parsing

## Configuration

**Environment (backend):**
- Loaded via Pydantic Settings from `.env` (`backend/app/config.py`, `case_sensitive=True`)
- `AI_PROVIDER` selects `openai` | `anthropic` (default `anthropic`)
- Critical keys: `DATABASE_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SECRET_KEY`, `ALLOWED_ORIGINS`
- Feature/tuning knobs: screenplay critique loop (`SCREENPLAY_CRITIQUE_ENABLED`, `_THRESHOLD`, `_POLISH_ENABLED`), craft doctrine injection (`DOCTRINE_*`), embedding (`EMBEDDING_MODEL`, `EMBEDDING_DIMENSION=1536`), book processing (`CHUNK_SIZE_TOKENS`, `MAX_BOOK_SIZE_MB`), agents/pipeline budgets
- Production guards: refuses default `SECRET_KEY`, warns on localhost in `ALLOWED_ORIGINS`
- Example files: `backend/.env.example.txt`, `.env.docker.example`
- App will NOT import in prod without `OPENAI_API_KEY` (SDK validates at construction; services lazy-init clients to keep CI import safe)

**Environment (frontend):**
- `VITE_API_URL` (defaults to `/api`), `VITE_PROXY_TARGET` (dev proxy target)
- Example: `frontend/.env.example.txt`

**Build:**
- Backend: `backend/Dockerfile` (multi-step pip install, non-root `appuser`, `EXPOSE 8000`, shell-form CMD expanding `${PORT}`)
- Frontend: `frontend/vite.config.ts` (port 4321, `/api` and `/media` dev proxy to `:8000`), `frontend/tsconfig.json`
- MCP config lives inline in `Settings`: `MCP_BASE_URL`, `MCP_DNS_REBINDING_PROTECTION`

## Platform Requirements

**Development:**
- Docker Compose (`docker-compose.yml` + `docker-compose.override.yml`) brings up: `db` (pgvector/pgvector:pg15), `backend`, `frontend`
- Standalone: Python 3.11 venv + `uvicorn app.main:app --reload`; `npm run dev`
- Local backend sometimes runs on port 8001 (per project notes); MCP metadata defaults to `http://localhost:8001`
- Backend test suite requires `mcp` dep installed in venv or the WHOLE pytest collection fails; re-pin `starlette<0.37` after installing

**Production:**
- **Backend:** Railway (`backend/railway.json`, DOCKERFILE builder, healthcheck `/health`, `targetPort=8000`, restart ON_FAILURE). Service host `web-production-73857` (Railway "web").
- **Frontend:** Vercel (`frontend/vercel.json`, Vite framework, SPA rewrites to `/index.html`). Domain `guion.vapai.studio`. `.vercel/` present at repo root.
- **Database:** PostgreSQL 15 with pgvector extension
- CORS is domain-gated via `ALLOWED_ORIGINS` — unlisted domain => "Failed to fetch"
- PWA: installable web app manifest (`frontend/public/manifest.json`)

---

*Stack analysis: 2026-07-24*
