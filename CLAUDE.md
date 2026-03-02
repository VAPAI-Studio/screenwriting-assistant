# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Screenwriting assistant MVP — a full-stack app for creating and managing screenplay projects using story frameworks (Three-Act, Save the Cat, Hero's Journey) with AI-powered review via OpenAI GPT-4.

## Tech Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Radix UI, React Query
- **Backend:** FastAPI, Python 3.11, SQLAlchemy, Pydantic v2
- **Database:** PostgreSQL 15
- **AI:** OpenAI API (GPT-4)
- **Infrastructure:** Docker Compose

## Development Commands

### Full stack (Docker)
```bash
docker compose up --build          # Start all services
docker compose down                # Stop all services
```

### Backend (standalone)
```bash
cd backend
source venv/bin/activate           # Activate virtualenv
uvicorn app.main:app --reload --port 8000
```

### Frontend (standalone)
```bash
cd frontend
npm run dev                        # Vite dev server on :5173
npm run build                      # tsc && vite build
npm run lint                       # ESLint
```

### Tests
```bash
cd backend
source venv/bin/activate
pytest app/tests/test_api.py               # API tests
pytest app/tests/test_validators.py        # Validator tests
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid  # Single test
```

## Architecture

### Backend (`backend/app/`)

Entry point: `main.py` — FastAPI app with middleware stack (order matters): RateLimitMiddleware → RequestSizeLimitMiddleware → SecurityMiddleware → LoggingMiddleware.

- `api/endpoints/` — Route handlers: `projects.py`, `sections.py`, `review.py`, `auth.py`
- `api/dependencies.py` — DI for DB sessions and auth (mock auth via `MockAuthService` for MVP)
- `models/database.py` — SQLAlchemy models: Project → Section → ChecklistItem (cascade deletes)
- `models/schemas.py` — Pydantic v2 request/response schemas with field validators
- `services/openai_service.py` — Framework/section-aware prompts, in-memory response caching (15min TTL)
- `services/auth_service.py` — JWT auth + mock auth for development
- `middleware.py` — Rate limiting (60 req/min/IP), request size limits (10MB), security headers
- `exceptions.py` — Custom exception hierarchy mapped to HTTP status codes
- `utils/validators.py` — Input validation and HTML sanitization
- `config.py` — Pydantic Settings loaded from env vars

API routes are prefixed: `/api/auth`, `/api/projects`, `/api/sections`, `/api/review`. Health check at `/health`.

### Frontend (`frontend/src/`)

Entry: `main.tsx` → `App.tsx` with React Query provider and BrowserRouter.

- Routes: `/` → ProjectList, `/projects/:projectId` → Editor
- `lib/api.tsx` — Fetch wrapper with 30s timeout, Bearer token auth from localStorage
- `lib/constants.ts` — All magic numbers, framework configs, section configs, feature flags
- `lib/utils.ts` — Utility helpers
- `types/index.ts` — TypeScript interfaces mirroring backend schemas
- `components/` — Layout (Header), Projects (ProjectList, ProjectCard, CreateProjectModal), Editor (Editor, SectionEditor, Checklist, ReviewPanel), UI primitives (Button, Input, Modal, Card)
- `hooks/useKeyboardShortcuts.tsx` — Cmd/Ctrl+S (save), Cmd/Ctrl+Enter (AI review)

### Data Model

Project (title, framework, owner_id) → has many Sections (type enum, user_notes, ai_suggestions JSON) → has many ChecklistItems (prompt, answer, status, order).

Frameworks define which section types are created (e.g., THREE_ACT creates: INCITING_INCIDENT, PLOT_POINT_1, MIDPOINT, PLOT_POINT_2, CLIMAX, RESOLUTION).

## Key Conventions

- Backend uses mock auth token `"mock-token"` for MVP development — tests use `Bearer mock-token`
- Vite proxies `/api` requests to `http://localhost:8000` in dev mode
- Tailwind uses HSL CSS variables for theming (defined in `tailwind.config.js`)
- Frontend state management is React Query with 5-minute stale time, not Redux/Context
- Backend PYTHONPATH must be set to `/app` (handled by Dockerfile)

## Environment Variables

Backend (see `backend/.env.example.txt`): `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `MAX_TOKENS`, `MAX_SECTION_LENGTH`, `CACHE_TTL`

Frontend (see `frontend/.env.example.txt`): `VITE_API_URL`
