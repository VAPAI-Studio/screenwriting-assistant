# Technology Stack

**Analysis Date:** 2026-03-11

## Languages

**Primary:**
- **Python 3.11** - Backend API, AI service integration, document processing
- **TypeScript 5.2** - Frontend application with strict type checking
- **SQL** - PostgreSQL schemas and migrations

**Secondary:**
- **JavaScript (ES2020)** - Node.js scripts, build tooling
- **Bash** - Container initialization, development automation

## Runtime

**Backend:**
- Python 3.11 (slim base image in Docker)
- Uvicorn ASGI server
- PYTHONPATH configured to `/app`

**Frontend:**
- Node.js 18 (Alpine base in Docker)
- Vite 5.1 (dev server and build tool)
- Browser runtime (ES2020+)

**Package Managers:**
- **Backend:** pip (Python) with virtual environment isolation (`venv/`)
- **Frontend:** npm with lockfile (`package-lock.json`)

## Frameworks

**Backend:**
- **FastAPI 0.110.0** - REST API framework with automatic OpenAPI documentation
- **SQLAlchemy 2.0.27** - ORM with support for PostgreSQL extensions (pgvector)
- **Pydantic v2** (>=2.10) - Request/response validation with field validators
- **Pydantic Settings** (>=2.6) - Environment-based configuration management

**Frontend:**
- **React 18.2** - UI framework with hooks
- **React Router v6.21** - Client-side routing with `BrowserRouter`
- **React Query (TanStack) v5.20** - Server state management with 5-minute stale time default
- **React Markdown 10.1** - Markdown rendering with GitHub flavored markdown support (`remark-gfm`)

**UI & Styling:**
- **Tailwind CSS 3.4** - Utility-first CSS framework with HSL CSS variables for theming
- **Radix UI** - Headless component library:
  - `@radix-ui/react-dialog` v1.0.5 - Modal dialogs
  - `@radix-ui/react-dropdown-menu` v2.0.6 - Dropdown menus
  - `@radix-ui/react-select` v2.0.0 - Accessible select components
  - `@radix-ui/react-tabs` v1.0.4 - Tabbed interfaces
  - `@radix-ui/react-toast` v1.1.5 - Toast notifications
  - `@radix-ui/react-slot` v1.0.2 - Slot rendering
- **Lucide React 0.314** - Icon library (314+ icons)
- **Class Variance Authority 0.7** - Type-safe CSS class composition
- **Tailwind Merge 2.2** - Merge Tailwind CSS classes without conflicts

**Testing:**
- **pytest 8.0.2** - Python test runner
- **pytest-asyncio 0.23.5** - Async test support for FastAPI
- **pytest-cov 4.1.0** - Code coverage reporting
- **httpx >=0.25.0,<0.28.0** - Async HTTP client for testing

**Development Tools:**
- **TypeScript 5.2** - Static type checking
- **Vite 5.1** - Fast dev server and build bundler
- **ESLint 8.56** - TypeScript/JavaScript linting with React plugin
- **@typescript-eslint** - TypeScript AST linting support
- **PostCSS 8.4** - CSS processor for Tailwind
- **Autoprefixer 10.4** - Browser vendor prefixes

## Key Dependencies

**Critical (Backend):**
- **openai 1.12.0** - OpenAI API client for GPT models and embeddings
- **anthropic >=0.39.0** - Anthropic API client for Claude models
- **psycopg2-binary 2.9.9** - PostgreSQL adapter for Python
- **python-jose[cryptography] 3.3.0** - JWT authentication
- **pgvector 0.3.6** - PostgreSQL vector extension support for embeddings
- **tiktoken 0.7.0** - Token counting for OpenAI models

**Infrastructure (Backend):**
- **uvicorn 0.27.1** - ASGI application server
- **python-multipart 0.0.9** - Form data and file upload parsing
- **passlib[bcrypt] 1.7.4** - Password hashing (bcrypt)

**Document Processing:**
- **PyPDF2 3.0.1** - PDF extraction and manipulation
- **ebooklib 0.18** - eBook format handling (EPUB)
- **beautifulsoup4 4.12.3** - HTML/XML parsing
- **numpy >=1.24.0** - Numerical operations (required by pgvector)

**Frontend State & Utilities:**
- **clsx 2.1.0** - Conditional CSS class concatenation
- **react-dom 18.2** - React DOM rendering

## Configuration

**Environment:**

Backend configuration via Pydantic Settings (`backend/app/config.py`) with `.env` file support:
- `DATABASE_URL` - PostgreSQL connection string (required)
- `AI_PROVIDER` - "openai" or "anthropic" (default: "anthropic")
- `OPENAI_API_KEY` - OpenAI API key (required if provider is openai)
- `OPENAI_MODEL` - Model name (default: "gpt-4o")
- `ANTHROPIC_API_KEY` - Anthropic API key (required if provider is anthropic)
- `ANTHROPIC_MODEL` - Model name (default: "claude-sonnet-4-6")
- `SECRET_KEY` - JWT signing key (must be changed in production)
- `ALLOWED_ORIGINS` - CORS whitelist (defaults: localhost:5173, localhost:3000, localhost:5174)
- `ENVIRONMENT` - "development", "staging", or "production"
- `DEBUG` - Debug mode (auto-set based on ENVIRONMENT)
- `EMBEDDING_MODEL` - OpenAI embedding model (default: "text-embedding-3-small")
- `MAX_TOKENS` - Max response tokens (default: 4000)
- `MAX_SECTION_LENGTH` - Max section content length (default: 1500)
- `CACHE_TTL` - Caching time-to-live in seconds (default: 900 / 15 min)
- `UPLOAD_DIR` - File upload directory (default: `backend/uploads/`)
- `MAX_BOOK_SIZE_MB` - Max book file size (default: 50)
- `CHUNK_SIZE_TOKENS` - Document chunk size (default: 750)
- `AGENT_REVIEW_TIMEOUT` - Agent timeout in seconds (default: 90)

Frontend configuration via Vite environment:
- `VITE_API_URL` - API endpoint path (default: "/api", proxied to backend)
- `VITE_PROXY_TARGET` - Backend URL for dev proxy (default: "http://localhost:8000")

Docker Compose overrides via environment:
- `POSTGRES_USER` - Database user (default: "screenwriter")
- `POSTGRES_PASSWORD` - Database password (required)
- `POSTGRES_DB` - Database name (default: "screenwriter_db")

**Build:**
- Frontend: `frontend/tsconfig.json` (ES2020, JSX support, strict mode)
- Frontend: `frontend/vite.config.ts` (React plugin, API proxy on port 5173)
- Backend: Uses standard Python packaging with `requirements.txt`

**Testing:**
- `backend/pytest.ini` - pytest configuration
- Test discovery: `backend/app/tests/test_*.py`
- Run: `pytest` or specific test file `pytest app/tests/test_api.py`

## Platform Requirements

**Development:**
- **Python 3.11+** (backend)
- **Node.js 18+** (frontend, Alpine image in Docker)
- **PostgreSQL 15 with pgvector extension** (database)
- **Docker & Docker Compose** (optional, full-stack via containers)
- **OpenAI API key** or **Anthropic API key** (for AI features)

**Production:**
- Deployment target: Container orchestration (Kubernetes) or managed cloud platforms
- Minimum: Docker, PostgreSQL 15, API keys for AI providers
- Security: Production-grade `SECRET_KEY`, HTTPS CORS origins, environment-based config
- Validation: ENVIRONMENT must be set to "production" to trigger security checks

## Node and Python Versions

**Node:**
- `frontend/Dockerfile` specifies `node:18-alpine`
- No `.nvmrc` file detected

**Python:**
- `backend/Dockerfile` specifies `python:3.11-slim`
- No `.python-version` file detected

---

*Stack analysis: 2026-03-11*
