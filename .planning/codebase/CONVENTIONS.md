# Coding Conventions

**Analysis Date:** 2026-03-06

## Naming Patterns

**Files:**
- React components: PascalCase matching the exported component name — `SnippetCard.tsx`, `ProjectWorkspace.tsx`, `SidebarChat.tsx`
- Backend endpoint modules: snake_case — `projects.py`, `ai_chat.py`, `snippet_manager.py`
- Backend utility/service modules: snake_case — `validators.py`, `auth_service.py`, `embedding_service.py`
- Frontend library/utility modules: camelCase — `api.tsx`, `constants.ts`, `utils.ts`

**Functions and Methods:**
- Python: snake_case — `validate_project_title`, `get_current_user`, `create_project`
- TypeScript: camelCase — `getAuthToken`, `fetchWithTimeout`, `handlePhaseChange`
- React components: PascalCase named exports (not default) — `export function SnippetCard(...)`, `export function Editor()`
- Sub-components within a file: PascalCase local functions — `BookFootnotes`, `ProposedChangesCard` (defined in `frontend/src/components/Shared/SidebarChat.tsx`)

**Variables:**
- Python: snake_case — `db_project`, `valid_timestamps`, `current_user`
- TypeScript: camelCase — `selectedPhase`, `queryClient`, `editContent`

**Constants:**
- TypeScript: SCREAMING_SNAKE_CASE objects — `QUERY_KEYS`, `ROUTES`, `ERROR_MESSAGES`, `STORAGE_KEYS` in `frontend/src/lib/constants.ts`
- Python enum values: SCREAMING_SNAKE_CASE — `BookStatus.COMPLETED`, `PhaseType.IDEA`
- Python enum string values: snake_case — `"three_act"`, `"book_based"`, `"inciting_incident"`

**Types and Interfaces:**
- Python Pydantic schemas: PascalCase with suffix patterns — `ProjectCreate`, `ProjectUpdate`, `ProjectResponse`, `ProjectBase` in `backend/app/models/schemas.py`
- TypeScript: bare interfaces — `interface Project`, `interface Snippet`; type aliases for unions — `type ChatMode = 'brainstorm' | 'action'`
- TypeScript enums: PascalCase — `enum Framework`, `enum SectionType` in `frontend/src/types/index.ts`

**React Props Interfaces:**
- Named `{ComponentName}Props` convention — `SnippetCardProps`, `SidebarChatProps`

## Code Style

**Formatting:**
- No Prettier or ESLint config files detected — style is enforced by convention and the TypeScript compiler
- Python: PEP 8, 4-space indentation
- TypeScript/TSX: 2-space indentation, single quotes for strings

**Linting:**
- Frontend: TypeScript compiler via `npm run build` (`tsc && vite build`)
- Frontend lint command exists: `npm run lint` (ESLint)
- No `.eslintrc`, `.prettierrc`, or `biome.json` config files detected in the repo

## Import Organization

**TypeScript/React — Order:**
1. React and third-party hooks — `import { useState, useRef, useEffect } from 'react'`
2. React Router / React Query — `import { useParams } from 'react-router-dom'`, `import { useQuery } from '@tanstack/react-query'`
3. Third-party UI/icon libraries — `import { Loader2, Send, Zap } from 'lucide-react'`
4. Internal lib modules — `import { api } from '../../lib/api'`
5. Internal sibling components — `import { SectionEditor } from './SectionEditor'`
6. Internal hooks — `import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'`
7. Constants — `import { QUERY_KEYS, ERROR_MESSAGES } from '../../lib/constants'`
8. Type-only imports using `type` keyword last — `import type { PhaseConfig } from '../../types/template'`

**Python — Order:**
1. Standard library — `import re`, `from typing import Optional`, `from uuid import UUID`
2. Third-party — `from fastapi import APIRouter`, `from sqlalchemy.orm import Session`
3. Internal relative — `from ...models import schemas, database`, `from ..dependencies import get_db`

**Path Aliases:**
- No TypeScript path aliases configured — all imports use relative paths (`../../lib/api`)

## Error Handling

**Backend Pattern — Custom Exception Hierarchy (`backend/app/exceptions.py`):**
- `AppException` (base, extends `HTTPException`)
  - `ValidationException` — 400
  - `AuthenticationException` — 401 (includes `WWW-Authenticate: Bearer` header)
  - `AuthorizationException` — 403
  - `NotFoundException` — 404
  - `ConflictException` — 409
  - `RateLimitException` — 429 (includes `Retry-After` header)
  - `ExternalServiceException` — 503 → `OpenAIException`
  - `DatabaseException` — 500
  - `ConfigurationException` — 500
- Preferred usage: `raise NotFoundException(resource="Project", identifier=str(project_id))`
- Standardized error response via `ErrorResponse.to_dict()`: `{"detail": "...", "errors": [{"field": "...", "message": "..."}]}`
- Global `RequestValidationError` handler in `backend/app/main.py` returns `{"detail": "Validation error", "errors": [{field, message}]}` with 422

**Backend — Mixed Pattern (legacy):**
- Some endpoints still use raw `HTTPException` instead of custom exceptions — prefer custom exception classes for new code
- Example in `backend/app/api/endpoints/projects.py`: `update_project` uses `HTTPException(status_code=404)` while `get_project` uses `NotFoundException`

**Frontend Pattern:**
- API methods throw on non-OK: `if (!response.ok) throw new Error('Failed to fetch projects')`
- Components use `isError` from `useQuery` and render inline error states with fallback UI
- Error message extraction: `error instanceof Error ? error.message : ERROR_MESSAGES.NETWORK`
- AbortError caught for timeouts: `if (error.name === 'AbortError') throw new Error('Request timeout')`
- SSE stream parse failures silently skipped: `catch { // skip malformed events }`

## Logging

**Backend:**
- Standard `logging` module: `import logging; logger = logging.getLogger(__name__)`
- Configured in `backend/app/main.py`: `format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'`, level `INFO`
- `LoggingMiddleware` in `backend/app/middleware.py` logs each request/response at INFO with UUID request ID, method, path, client IP, status, and duration
- Request ID propagated via `request.state.request_id` and returned in `X-Request-ID` response header

**Frontend:**
- No dedicated logging framework — browser console only
- Silent failure for non-critical stream parsing errors

## Comments

**Python:**
- Docstrings on all public endpoint functions: `"""Create a new project"""`
- Module-level docstrings on test files with phase label and run command: `"""Snippet API tests — Phase 1 ... Run: pytest app/tests/test_snippets_api.py -v"""`
- Inline comments for non-obvious logic: `# Assigns db_project.id without committing`
- Section dividers in long schema/api files: `# ============================================================`

**TypeScript/TSX:**
- JSX section comments: `{/* Phase Navigation */}`, `{/* Chat sidebar */}`
- Section dividers for sub-components: `// ── Book footnotes ────────────────────────────────────────────`
- No JSDoc on functions — TypeScript signatures serve as self-documentation

## Function Design

**Size:** Small, focused. Python endpoint handlers delegate to validators and services. React event handlers are simple state updates or navigation calls.

**Parameters:**
- Python endpoints use FastAPI `Depends` for DI: `current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)`
- React component props are flat, explicit interfaces — no nested config objects; each prop individually named and typed

**Return Values:**
- Python: endpoints return SQLAlchemy ORM objects directly (Pydantic serializes via `from_attributes=True`)
- TypeScript API: typed promises — `Promise<Project>`, `Promise<Snippet[]>`, `Promise<void>`
- Streaming methods use dual-callback pattern: `onChunk: (chunk: string) => void, onDone: (data: {...}) => void`

## Module Design

**Python Exports:**
- Public validators re-exported from `backend/app/utils/__init__.py`
- Routers: `router = APIRouter()` at top of each endpoint module, registered in `backend/app/main.py`

**TypeScript Exports:**
- Named exports for all components: `export function Editor()`
- Single exception: `export default App` in `frontend/src/App.tsx`
- Type barrel: `frontend/src/types/index.ts` re-exports via `export * from './template'`

**Centralization Rules:**
- All magic values in `frontend/src/lib/constants.ts` (timeouts, QUERY_KEYS, ROUTES, ERROR_MESSAGES, FEATURE_FLAGS, STORAGE_KEYS)
- All HTTP calls in single `api` object in `frontend/src/lib/api.tsx`
- All TypeScript interfaces in `frontend/src/types/index.ts` and `frontend/src/types/template.ts`

## Pydantic Schema Patterns

**Base/Create/Update/Response quartet** (`backend/app/models/schemas.py`):
- `{Entity}Base` — shared fields with `@field_validator` decorators
- `{Entity}Create` — extends Base, used for POST body
- `{Entity}Update` — all fields Optional, used for PATCH body
- `{Entity}` or `{Entity}Response` — includes `id: UUID`, timestamps, `model_config = ConfigDict(from_attributes=True)`

**Field Validation:**
- `@field_validator` strips and normalizes whitespace: `return v.strip()`
- Field constraints via `Field(...)`: `min_length`, `max_length`, `ge`, `pattern`
- Regex constraint example: `color: str = Field(default="#6366f1", pattern=r'^#[0-9a-fA-F]{6}$')`
- Mode constraint example: `mode: str = Field(default="brainstorm", pattern="^(brainstorm|action)$")`

**Separate validator functions** (`backend/app/utils/validators.py`):
- Standalone functions that raise `HTTPException` directly: `validate_project_title()`, `validate_review_text()`, `validate_password()`
- Return-value validators that sanitize: `validate_section_content()` truncates, `sanitize_html()` strips tags
- Boolean validators: `validate_email()`, `validate_framework()`, `validate_section_type()`

## Tailwind CSS Patterns

- Dark-first design using CSS variable tokens: `text-muted-foreground`, `bg-card/30`, `border-border/40`, `bg-background`
- Amber accent color throughout: `text-amber-500/60`, `bg-amber-500/10`, `text-amber-300`, `border-amber-500/20`
- Red for destructive actions: `text-red-400`, `hover:text-red-300`, `hover:bg-red-500/10`
- Emerald for success indicators: `bg-emerald-400`
- Conditional classes via template literals:
  ```tsx
  className={`w-full px-3 py-2 rounded-lg ${
    selected ? 'bg-amber-500/10 text-amber-300 font-medium' : 'text-muted-foreground hover:bg-muted/50'
  }`}
  ```
- Loading states: `animate-spin` on `<Loader2>`, `animate-fade-up`/`animate-fade-in` for containers
- Full-bleed panel height: `h-[calc(100vh-56px)]` (56px = header height)
- Content truncation: `line-clamp-5`, `truncate`

## API Client Pattern

**All methods follow this pattern in `frontend/src/lib/api.tsx`:**
```typescript
async methodName(params): Promise<ReturnType> {
  const response = await fetch(`${API_BASE_URL}/path`, {
    method: 'POST',        // or GET/PATCH/DELETE
    headers: getHeaders(),  // Content-Type + Bearer auth from localStorage
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to {action}');
  return response.json();
}
```

**Timeout-sensitive calls** use `fetchWithTimeout` or manual `AbortController`:
```typescript
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT);
```

---

*Convention analysis: 2026-03-06*
