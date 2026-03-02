# Technology Stack

**Analysis Date:** 2026-03-01

## Languages

**Primary:**
- Python 3.11 - Backend API, AI services, data processing
- TypeScript 5.2.2 - Frontend application and build tooling
- JavaScript - Frontend runtime and configuration
- SQL - PostgreSQL database queries and migrations

**Secondary:**
- HTML/CSS - Frontend templates and styling

## Runtime

**Environment:**
- Python 3.11-slim (Docker image for backend)
- Node.js 18-alpine (Docker image for frontend)
- Node.js 18+ (local development for frontend)

**Package Manager:**
- pip (Python) - Backend dependencies via `requirements.txt`
- npm (Node.js) - Frontend dependencies via `package.json`
- Lockfile: `package-lock.json` (frontend present), Python has `requirements.txt` with pinned versions

## Frameworks

**Backend Core:**
- FastAPI 0.110.0 - REST API framework with automatic OpenAPI documentation
- Uvicorn 0.27.1 - ASGI server for running FastAPI
- SQLAlchemy 2.0.27 - ORM for database model definitions and queries

**Frontend Core:**
- React 18.2.0 - UI component framework
- React Router DOM 6.21.3 - Client-side routing

**Testing:**
- pytest 8.0.2 - Python test framework for backend tests
- pytest-asyncio 0.23.5 - Async test support for FastAPI
- pytest-cov 4.1.0 - Code coverage reporting
- httpx 0.25.0-0.27.0 - HTTP client for API testing

**Build/Dev:**
- Vite 5.1.0 - Frontend bundler and dev server
- TypeScript 5.2.2 - Type checking and compilation
- ESLint 8.56.0 - Frontend code linting
- Tailwind CSS 3.4.1 - Utility-first CSS framework
- PostCSS 8.4.35 - CSS transformation pipeline
- Autoprefixer 10.4.17 - CSS vendor prefix plugin

## Key Dependencies

**Critical:**
- pydantic 2.10+ - Data validation and settings management (Pydantic v2)
- pydantic-settings 2.6+ - Environment-based configuration for FastAPI
- openai 1.12.0 - OpenAI API client for GPT integrations
- anthropic 0.39.0+ - Anthropic API client for Claude models
- tiktoken 0.7.0 - Token counting for OpenAI models

**Database & ORM:**
- psycopg2-binary 2.9.9 - PostgreSQL adapter for Python
- pgvector 0.3.6 - Vector search extension for PostgreSQL (AI embeddings)
- sqlalchemy 2.0.27 - Database abstraction and ORM

**Authentication & Security:**
- python-jose 3.3.0 with cryptography - JWT token handling
- passlib 1.7.4 with bcrypt - Password hashing (development use)

**Document Processing:**
- PyPDF2 3.0.1 - PDF file parsing and extraction
- ebooklib 0.18 - EPUB ebook file parsing
- beautifulsoup4 4.12.3 - HTML parsing for document content
- numpy 1.24.0+ - Numerical computing for embeddings

**Utilities:**
- python-multipart 0.0.9 - Multipart form data parsing (file uploads)
- requests (via httpx for async) - HTTP client library

**Frontend UI Components:**
- @radix-ui/react-dialog 1.0.5 - Modal/dialog components
- @radix-ui/react-dropdown-menu 2.0.6 - Dropdown menu components
- @radix-ui/react-select 2.0.0 - Select input components
- @radix-ui/react-tabs 1.0.4 - Tab components
- @radix-ui/react-toast 1.1.5 - Toast notification components
- lucide-react 0.314.0 - Icon library
- clsx 2.1.0 - Conditional CSS class utilities
- class-variance-authority 0.7.0 - Variant composition for components
- tailwind-merge 2.2.1 - Merge Tailwind class names intelligently

**Frontend State Management:**
- @tanstack/react-query 5.20.1 - Server state management with caching and synchronization

**Development Dependencies (Frontend):**
- @vitejs/plugin-react 4.2.1 - React Fast Refresh plugin for Vite
- @typescript-eslint/eslint-plugin 6.21.0 - TypeScript linting rules
- @typescript-eslint/parser 6.21.0 - TypeScript parser for ESLint
- eslint-plugin-react-hooks 4.6.0 - ESLint rules for React Hooks
- eslint-plugin-react-refresh 0.4.5 - React Refresh validation

## Configuration

**Environment:**
- Configuration managed via Pydantic Settings in `backend/app/config.py`
- Environment variables required:
  - `DATABASE_URL` - PostgreSQL connection string
  - `OPENAI_API_KEY` - OpenAI API key for GPT models
  - `ANTHROPIC_API_KEY` - Anthropic API key for Claude models
  - `AI_PROVIDER` - Switch between "openai" and "anthropic"
  - `SECRET_KEY` - JWT signing key
  - `ALLOWED_ORIGINS` - CORS origins (comma-separated)
  - `ENVIRONMENT` - "development", "staging", or "production"
- Frontend env vars in `.env` file:
  - `VITE_API_URL` - Backend API base URL (defaults to `http://localhost:8000/api`)

**Build:**
- Frontend: `vite.config.ts` with React plugin and API proxy configuration
- Frontend: `tsconfig.json` with strict mode enabled, ES2020 target
- Frontend: `postcss.config.js` for Tailwind CSS processing
- Frontend: `tailwind.config.js` for CSS configuration
- Backend: Dockerfile-based builds in `backend/Dockerfile.txt`
- Frontend: Dockerfile-based builds in `frontend-dockerfile.txt`

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js 18+
- PostgreSQL 15 (with pgvector extension)
- Docker and Docker Compose (for containerized development)

**Production:**
- Docker container orchestration (Docker Compose or Kubernetes)
- PostgreSQL 15 database
- Reverse proxy (nginx or similar) for HTTPS termination
- API key management system for OpenAI and Anthropic keys

## Deployment

**Docker Compose Services:**
- `db` - PostgreSQL 15 with pgvector (pgvector/pgvector:pg15)
- `backend` - FastAPI application on port 8000
- `frontend` - React dev server on port 5173
- Volume management: `postgres_data` (database persistence), `book_uploads` (file storage)

---

*Stack analysis: 2026-03-01*
