# Coding Conventions

**Analysis Date:** 2026-07-24

This is a full-stack app: a Python/FastAPI backend (`backend/app/`) and a React/TypeScript/Vite frontend (`frontend/src/`). Conventions differ per side; follow the relevant section.

## Naming Patterns

**Files (backend):**
- snake_case modules: `openai_service.py`, `auth_service.py`, `db_migrator.py`
- Route handlers grouped by resource under `backend/app/api/endpoints/`: `projects.py`, `sections.py`, `review.py`, `breakdown.py`, `seasons.py`, etc.
- Test files mirror the unit under test: `test_<subject>.py` in `backend/app/tests/` (e.g. `test_validators.py`, `test_breakdown_service.py`)

**Files (frontend):**
- PascalCase for React components and their files: `CardGridView.tsx`, `SectionEditor.tsx`, `ProjectCard.tsx`
- camelCase for hooks and libs: `useKeyboardShortcuts.tsx`, `api.tsx`, `constants.ts`, `utils.ts`
- Components live in feature-named PascalCase directories under `frontend/src/components/`: `Editor/`, `Projects/`, `Breakdown/`, `Patterns/`, `UI/`, `Workspace/`, `Shows/`, `Seasons` (via `Books`/`Shows`), `Storyboard/`, `Snippets/`, `Settings/`, `Auth/`, `Shared/`, `Layout/`

**Functions:**
- Backend: snake_case (`validate_title`, `generate_mock_token`, `send_episode_within_series`)
- Frontend: camelCase (`getAuthToken`, `fetchWithTimeout`, `handleChange`); React components are PascalCase named exports (`export function CardGridView(...)`)

**Variables:**
- Backend: snake_case
- Frontend: camelCase; React state pairs follow `const [thing, setThing] = useState(...)`; refs suffixed `Ref` (`timerRef`, `formDataRef`)

**Types:**
- Backend: Pydantic classes PascalCase with intent suffix — `ProjectBase`, `ProjectCreate`, `ProjectUpdate`, `Project` (response). SQLAlchemy models PascalCase in `backend/app/models/database.py`. Enums PascalCase with UPPER_SNAKE members (`Framework.THREE_ACT`, `SectionType.INCITING_INCIDENT`)
- Frontend: PascalCase TypeScript interfaces in `frontend/src/types/index.ts` and `frontend/src/types/template.ts`, mirroring backend schema names (`Project`, `Section`, `PhaseDataResponse`)

**Constants:**
- Frontend: UPPER_SNAKE exported from `frontend/src/lib/constants.ts` (`API_TIMEOUT`, `DEBOUNCE_DELAY`, `MAX_SECTION_LENGTH`, `QUERY_KEYS`, `FRAMEWORK_CONFIG`)

## Code Style

**Backend formatting:**
- No enforced formatter config detected (no `black`/`ruff`/`.flake8`/`pyproject.toml` in `backend/`). Match surrounding style: 4-space indent, module-level comment header (`# backend/app/exceptions.py`), docstrings on classes and non-trivial functions.
- PYTHONPATH must be `/app` for imports to resolve (`from app.main import app`). Handled by the Dockerfile in prod; `pytest.ini` sets `pythonpath = .` for tests run from `backend/`.

**Frontend formatting:**
- No `.prettierrc` / `.eslintrc` / `eslint.config.*` file is checked in, but `package.json` defines `lint`: `eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0`. Treat zero warnings as the bar.
- 2-space indent, single quotes, semicolons, trailing-comma multiline imports (see `frontend/src/lib/api.tsx` import block).
- TypeScript is strict: `tsconfig.json` sets `strict`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`. Unused locals/params will fail the build (`tsc && vite build`). Prefix intentionally-unused params with `_`.

**Linting stack (frontend):** ESLint 8 + `@typescript-eslint` 6 + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh` (from `devDependencies`).

## Import Organization

**Backend:**
1. stdlib (`import json`, `import os`, `import uuid`)
2. third-party (`import pytest`, `from fastapi import ...`, `from sqlalchemy import ...`)
3. app-local (`from app.models.database import Base`, `from app.main import app`)

Always import app code via the `app.` package root, never relative-deep paths.

**Frontend:**
1. React / third-party (`react`, `@tanstack/react-query`, `lucide-react`)
2. lib/api (`../../lib/api`, `../../lib/constants`)
3. types via `import type { ... } from '../types'` (type-only imports are used deliberately)

**Path aliases:** None configured — imports are relative (`../../lib/...`). `moduleResolution: bundler` with `allowImportingTsExtensions` is set, so `.tsx`-less relative imports resolve through Vite.

## Error Handling

**Backend — custom exception hierarchy (`backend/app/exceptions.py`):**
- Base `AppException(HTTPException)`; all app errors subclass it and pre-bind an HTTP status:
  - `ValidationException` → 400 (optional `field` prefix)
  - `AuthenticationException` → 401 (adds `WWW-Authenticate: Bearer`)
  - `AuthorizationException` → 403
  - `NotFoundException(resource, identifier)` → 404
  - `ConflictException` → 409
  - `RateLimitException(retry_after)` → 429 (adds `Retry-After`)
  - `ExternalServiceException(service, detail)` → 503; `OpenAIException` subclasses it
- Raise the semantic exception, not a bare `HTTPException`. Pydantic field-validation failures surface as 422 with an `errors` array shaped `[{ "field": ..., ... }]` (see `test_api.py` assertions).

**Frontend:**
- `frontend/src/lib/api.tsx` wraps `fetch` with `fetchWithTimeout` (AbortController; `API_TIMEOUT` 30s, `CHAT_TIMEOUT` 120s for AI calls).
- `authFetch` intercepts any non-auth 401, clears `AUTH_TOKEN_KEY` from localStorage, and hard-redirects to `/login` (auth endpoints excluded so login failures stay inline).
- Mutations handle failure via React Query `onError` (e.g. resetting `fillingKey` in `CardGridView`).

## Authentication Convention

- MVP/dev uses a mock auth token: send `Authorization: Bearer mock-token`. The frontend defaults to this when no real token is in localStorage (`getAuthToken` in `frontend/src/lib/api.tsx`). Backend tests use the `mock_auth_headers` fixture.
- Real auth is JWT via `backend/app/services/auth_service.py`; mock auth resolves to a fixed user id `12345678-1234-5678-1234-567812345678` (owner-scoped rows in tests must use it).
- API-key auth uses `sa_`-prefixed Bearer tokens (per-key rate limiting).

## Logging

- Backend has a `LoggingMiddleware` in the middleware stack (`backend/app/middleware.py`). Prefer structured/middleware logging over ad-hoc prints.
- Frontend: no logging framework; use sparingly.

## Validation (Pydantic v2)

- Request/response models in `backend/app/models/schemas.py` use Pydantic v2: `Field(..., min_length=, max_length=, pattern=)` for constraints and `@field_validator('name')` / `@model_validator` for custom rules (e.g. `validate_title` strips whitespace and rejects blank).
- Response models set `model_config = ConfigDict(from_attributes=True)` to serialize SQLAlchemy objects.
- Additional input sanitization/HTML-stripping lives in `backend/app/utils/validators.py` (tested by `test_validators.py`).

## Function & Component Design

- Backend: thin route handlers in `api/endpoints/`, business logic in `services/*`, DI (DB session, auth) via `backend/app/api/dependencies.py`.
- Frontend: each "view" pattern is its own component in `frontend/src/components/Patterns/` (`CardGridView`, `OrderedListView`, `StructuredFormView`, `WizardView`, `RepeatableCardsView`, `IndividualEditorView`, `ScreenplayEditorView`, `SceneWorkspaceView`, `CardGridView`, `PlaceholderView`). A template config drives which pattern renders — add a new view type here rather than branching inside an existing view.
- Autosave pattern: debounced `setTimeout` (multiples of `DEBOUNCE_DELAY`) writing through a React Query mutation, with a `formDataRef` mirror so the debounced callback reads fresh state.

## State Management (frontend)

- React Query (`@tanstack/react-query` v5) is the single source of server state — no Redux, no global Context store. 5-minute stale time.
- Query keys are centralized in `QUERY_KEYS` (`frontend/src/lib/constants.ts`); invalidate via `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.X(...) })` after mutations. Do not hand-write query-key arrays.
- All magic numbers, timeouts, framework/section configs, and feature flags live in `frontend/src/lib/constants.ts` — never inline them.

## Theming

- Tailwind CSS with HSL CSS variables (defined in `frontend/tailwind.config.js`). Reference semantic color tokens, not raw hex.

## Commit Message Style

Conventional Commits with a scope, lowercase imperative subject, and an em-dash clarifier. Observed from `git log`:

- `feat(chat): contextual question chips in the empty sidebar chat`
- `fix(workspace): unresolvable subsection keys fold into the visible surface`
- `feat(scenes): master-detail fusion — list + editor in one surface`
- `chore: favicon + remove the Screenplay Analyzer stub`
- `docs: MCP guide — connecting agents and driving the pipeline`
- `polish(templates): sharpen vertical-microdrama prompts`

Types in use: `feat`, `fix`, `chore`, `docs`, `polish`. Scopes are feature areas: `chat`, `scenes`, `seasons`, `shows`, `bible`, `mcp`, `templates`, `doctrine`, `workspace`, `vapai`, `pwa`, `agent-chat`. Per project memory, changes are committed and pushed directly to `main` after tests/typecheck pass.

---

*Convention analysis: 2026-07-24*
