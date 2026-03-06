# Technology Stack

**Analysis Date:** 2026-03-06

## Languages

**Primary:**
- Python 3.11 - Backend API and all services
- TypeScript 5.2.2 - Frontend React application, types, all `.ts`/`.tsx` files
- SQL - PostgreSQL database schemas and migration scripts

**Secondary:**
- JavaScript - Frontend build tooling config files (e.g., `frontend/tailwind.config.js`, `frontend/postcss.config.js`)

## Runtime

**Environment:**
- Python 3.11 (via Docker/virtualenv at `backend/venv/`)
- Node.js 18+ (managed via Vite and npm)
- PostgreSQL 15 with pgvector extension

**Package Manager:**
- npm (frontend) - lockfile: `frontend/package-lock.json` (present)
- pip (backend) - pinned in `backend/requirements.txt` (present)

## Frameworks

**Core:**
- FastAPI 0.110.0 - Backend REST API framework, entry point `backend/app/main.py`
- Uvicorn 0.27.1 - ASGI server for FastAPI
- React 18.2.0 - Frontend UI library, entry point `frontend/src/main.tsx`
- Vite 5.1.0 - Frontend build tool and dev server (port 5173)
- SQLAlchemy 2.0.27 - ORM for all database interactions
- Pydantic 2.10+ with pydantic-settings 2.6+ - Data validation and config management

**Testing:**
- pytest 8.0.2 - Backend unit and integration tests
- pytest-asyncio 0.23.5 - Async test support for FastAPI endpoints
- pytest-cov 4.1.0 - Coverage reporting
- httpx 0.25.0-0.27.x - Async HTTP client used in test fixtures

**Build/Dev:**
- TypeScript 5.2.2 - Strict mode enabled (`frontend/tsconfig.json`)
- ESLint 8.56.0 - Frontend linting with `@typescript-eslint` rules
- Tailwind CSS 3.4.1 - Utility-first CSS with HSL CSS variable theming
- PostCSS 8.4.35 + Autoprefixer 10.4.17 - CSS processing pipeline

**UI Component Layer:**
- Radix UI (dialog, dropdown-menu, select, slot, tabs, toast) - Accessible, unstyled component primitives
- class-variance-authority 0.7.0 - Variant-based component composition
- clsx 2.1.0 + tailwind-merge 2.2.1 - Conditional class utilities
- lucide-react 0.314.0 - Icon library

## Key Dependencies

**Critical:**
- `openai` 1.12.0 - OpenAI GPT-4 and embedding API client; used by `backend/app/services/ai_provider.py` and `backend/app/services/embedding_service.py`
- `anthropic` >=0.39.0 - Anthropic Claude API client (default AI provider); used by `backend/app/services/ai_provider.py`
- `psycopg2-binary` 2.9.9 - PostgreSQL adapter for SQLAlchemy
- `pgvector` 0.3.6 - Vector column support in PostgreSQL for storing embeddings

**Auth & Security:**
- `python-jose` 3.3.0 - JWT encoding/decoding in `backend/app/services/auth_service.py`
- `passlib` 1.7.4 with bcrypt - Password hashing
- `python-multipart` 0.0.9 - Multipart form uploads (book file ingestion)

**Document Processing:**
- `PyPDF2` 3.0.1 - PDF text extraction in `backend/app/services/document_service.py`
- `ebooklib` 0.18 - EPUB parsing in `backend/app/services/document_service.py`
- `beautifulsoup4` 4.12.3 - HTML/XML parsing for EPUB content

**AI/ML Utilities:**
- `tiktoken` 0.7.0 - Token counting for GPT-4 based on `gpt-4` tokenizer
- `numpy` >=1.24.0 - Numerical support for embedding operations

**Frontend State/Routing:**
- `@tanstack/react-query` 5.20.1 - Server state management (5-minute stale time by convention)
- `react-router-dom` 6.21.3 - Client-side routing
- `react-markdown` 10.1.0 + `remark-gfm` 4.0.1 - Markdown rendering in AI responses

## Configuration

**Environment (Backend):**
- Managed via Pydantic Settings class in `backend/app/config.py`
- Loads from `.env` file and environment variables
- Required at startup: `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`)
- AI provider selected by `AI_PROVIDER` env var ("openai" or "anthropic", default: "anthropic")
- Default Anthropic model: `claude-sonnet-4-6`
- Default OpenAI model: `gpt-4o`
- Embedding model: `text-embedding-3-small` (always OpenAI, even if Anthropic is primary provider)

**Environment (Frontend):**
- Vite env vars prefixed with `VITE_`
- `VITE_API_URL` - API base URL (defaults to `/api` in Docker)
- `VITE_PROXY_TARGET` - Backend URL for Vite proxy (defaults to `http://localhost:8000`)

**Build:**
- `frontend/vite.config.ts` - Dev server at `:5173`, proxies `/api` to backend
- `frontend/tailwind.config.js` - Tailwind with HSL CSS variable theming
- `frontend/tsconfig.json` - Strict TS, ES2020 target, bundler module resolution

## Platform Requirements

**Development:**
- Docker 20.10+ and Docker Compose 2.0+ (full stack via `docker compose up --build`)
- OR: Node.js 18+ for frontend standalone, Python 3.11+ with virtualenv for backend standalone
- PostgreSQL 15 with pgvector extension required for database

**Production:**
- Docker container runtime
- PostgreSQL 15 with pgvector extension (or managed service with extension support)
- File storage volume for uploaded books (`book_uploads`)
- `SECRET_KEY` must be overridden from default; `POSTGRES_PASSWORD` is required

## Docker Configuration

**Services Defined in `docker-compose.yml`:**
- `db` - `pgvector/pgvector:pg15` image; runs migrations from `backend/migrations/` on init
- `backend` - Custom image from `backend/Dockerfile`; mounts `backend/app/` for live reload
- `frontend` - Custom image from `frontend/Dockerfile`; mounts `frontend/src/` for live reload

**Volumes:**
- `postgres_data` - PostgreSQL persistent data
- `book_uploads` - Uploaded books and documents (shared between host and backend container)

**Port Mapping:**
- Frontend: 5173
- Backend API: 8000
- PostgreSQL: 5432

**Migration Strategy:**
- SQL files in `backend/migrations/` auto-applied at DB container init
- Files: `init_db.sql`, `002_knowledge_graph.sql`, `003_template_system.sql`, `004_agent_type_and_quality.sql`, `005_book_progress.sql`, `006_snippet_management.sql`, `007_snippets_table.sql`
- No Alembic — all schema changes require new numbered SQL files

---

*Stack analysis: 2026-03-06*
