# Technology Stack

**Analysis Date:** 2026-03-05

## Languages

**Primary:**
- Python 3.11 - Backend API and services
- TypeScript 5.2.2 - Frontend React application and types
- SQL - PostgreSQL database schemas and queries

**Secondary:**
- JavaScript (Node.js) - Frontend build tooling and dependencies

## Runtime

**Environment:**
- Node.js (managed via Vite and npm)
- Python 3.11 (via Docker/virtualenv)
- PostgreSQL 15 (with pgvector extension)

**Package Manager:**
- npm (frontend) - lockfile: `frontend/package-lock.json`
- pip (backend) - lockfile: `backend/requirements.txt`

## Frameworks

**Core:**
- FastAPI 0.110.0 - Backend REST API framework
- React 18.2.0 - Frontend UI library
- Vite 5.1.0 - Frontend build tool and dev server (port 5173)
- SQLAlchemy 2.0.27 - Python ORM for database interactions
- Pydantic 2.10+ - Data validation and serialization (backend)

**Testing:**
- pytest 8.0.2 - Backend unit and integration tests
- pytest-asyncio 0.23.5 - Async test support for FastAPI
- pytest-cov 4.1.0 - Test coverage reporting
- httpx 0.25.0-0.27.x - Async HTTP client for testing

**Build/Dev:**
- TypeScript 5.2.2 - Type checking (frontend)
- ESLint 8.56.0 - Frontend linting
- Tailwind CSS 3.4.1 - Utility-first CSS framework
- PostCSS 8.4.35 - CSS processing
- Autoprefixer 10.4.17 - CSS vendor prefix injection

**Styling:**
- Radix UI - Unstyled, accessible component primitives
- class-variance-authority 0.7.0 - Component variant composition
- clsx 2.1.0 - Conditional class merging
- tailwind-merge 2.2.1 - Tailwind conflict resolution
- lucide-react 0.314.0 - Icon library

## Key Dependencies

**Critical:**
- openai 1.12.0 - OpenAI GPT-4 API client (embeddings, chat completions)
- anthropic >=0.39.0 - Anthropic Claude API client (alternative AI provider)
- psycopg2-binary 2.9.9 - PostgreSQL adapter for Python
- pgvector 0.3.6 - PostgreSQL vector search support (embeddings storage)

**Infrastructure:**
- uvicorn 0.27.1 - ASGI server for FastAPI
- python-jose 3.3.0 - JWT authentication
- passlib 1.7.4 - Password hashing and verification
- python-multipart 0.0.9 - Multipart form data handling

**Document Processing:**
- PyPDF2 3.0.1 - PDF parsing and extraction
- ebooklib 0.18 - EPUB/eBook processing
- beautifulsoup4 4.12.3 - HTML parsing

**AI/ML:**
- tiktoken 0.7.0 - Token counting for OpenAI models
- numpy >=1.24.0 - Numerical computing (embeddings support)

**Frontend State Management:**
- @tanstack/react-query 5.20.1 - Server state management and caching
- react-router-dom 6.21.3 - Client-side routing
- react-markdown 10.1.0 - Markdown rendering
- remark-gfm 4.0.1 - GitHub Flavored Markdown support

## Configuration

**Environment:**
- Configuration managed via environment variables (loaded in `backend/app/config.py`)
- Pydantic Settings with `.env` file support
- Default values in `config.py` with validation

**Key Configs:**
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API credentials (optional)
- `ANTHROPIC_API_KEY` - Anthropic API credentials (optional)
- `AI_PROVIDER` - "openai" or "anthropic" (default: "anthropic")
- `SECRET_KEY` - JWT signing key
- `ALLOWED_ORIGINS` - CORS allowlist (defaults to localhost:5173, localhost:3000)
- `ENVIRONMENT` - "development", "staging", or "production"
- `OPENAI_MODEL` - OpenAI model name (default: "gpt-4o")
- `ANTHROPIC_MODEL` - Anthropic model name (default: "claude-sonnet-4-6")
- `EMBEDDING_MODEL` - OpenAI embedding model (default: "text-embedding-3-small")
- `MAX_TOKENS` - Response token limit (default: 1500)
- `CACHE_TTL` - Response cache time-to-live in seconds (default: 900 = 15 min)

**Build:**
- `frontend/vite.config.ts` - Vite configuration with dev server proxy to `/api`
- `frontend/tailwind.config.js` - Tailwind CSS configuration with HSL theme variables
- `frontend/tsconfig.json` - TypeScript compiler options
- `frontend/.eslintrc.*` - ESLint rules for React/TypeScript

## Platform Requirements

**Development:**
- Docker 20.10+ (for containerized stack)
- Docker Compose 2.0+ (for multi-service orchestration)
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend development)
- PostgreSQL 15 client tools (optional, for direct DB access)

**Production:**
- Docker container runtime
- PostgreSQL 15 database (external or managed)
- 2+ CPU cores, 2GB+ RAM minimum for all services

## Docker Configuration

**Services Defined:**
- `db` - pgvector/pgvector:pg15 (PostgreSQL 15 with vector extension)
- `backend` - Custom Docker image from `backend/Dockerfile`
- `frontend` - Custom Docker image from `frontend/Dockerfile`

**Volumes:**
- `postgres_data` - PostgreSQL persistent data
- `book_uploads` - Uploaded books and documents

**Port Mapping:**
- Frontend: 5173
- Backend: 8000
- PostgreSQL: 5432

---

*Stack analysis: 2026-03-05*
