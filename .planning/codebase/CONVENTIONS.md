# Coding Conventions

**Analysis Date:** 2026-03-01

## Naming Patterns

**Files:**
- Python backend: snake_case (e.g., `openai_service.py`, `test_validators.py`)
- TypeScript/React frontend: kebab-case (e.g., `useKeyboardShortcuts.tsx`, `useKeyboardShortcuts.tsx`)
- Components: PascalCase (e.g., `ProjectCard.tsx`, `Editor.tsx`)
- Hooks: camelCase with `use` prefix (e.g., `useKeyboardShortcuts`)

**Functions:**
- Backend: snake_case functions (e.g., `validate_project_title()`, `create_project()`)
- Frontend: camelCase functions and methods (e.g., `getAuthToken()`, `getHeaders()`)
- React components: PascalCase (e.g., `function Editor()`, `export function ProjectList()`)

**Variables:**
- Backend: snake_case (e.g., `cache_key`, `section_type`, `db_project`)
- Frontend: camelCase (e.g., `selectedSectionId`, `isLoading`, `projectId`)
- Constants: UPPER_SNAKE_CASE (e.g., `API_TIMEOUT`, `SECTION_LABELS`, `QUERY_KEYS`)

**Types:**
- TypeScript interfaces: PascalCase (e.g., `interface Project {}`, `interface ChecklistItem {}`)
- TypeScript enums: PascalCase with UPPER_SNAKE_CASE values (e.g., `enum Framework { THREE_ACT = "three_act" }`)
- Pydantic models: PascalCase (e.g., `class ProjectCreate(BaseModel):`, `class Section(SectionBase):`)

## Code Style

**Formatting:**
- Backend: No configured formatter mentioned; follows Python conventions with 80-100 char lines
- Frontend: TypeScript + Tailwind CSS; uses Vite for bundling
- Indentation: 2 spaces (frontend), 4 spaces (backend/Python standard)

**Linting:**
- Frontend: ESLint with TypeScript support via `@typescript-eslint/eslint-plugin`
  - Runs on: `.ts`, `.tsx` files
  - Command: `npm run lint` with `--max-warnings 0`
  - Plugins: `react-hooks`, `react-refresh`
  - Rules enforced: Unused locals/parameters checked, no fallthroughs in switch statements
- Backend: No explicit linting tool configured; follows Python PEP 8 conventions
  - Pydantic v2 models with field validators
  - FastAPI best practices (dependency injection, exception handling)

**TypeScript Configuration:**
- Target: `ES2020`
- Strict mode: Enabled
- Module resolution: `bundler`
- Options enforced:
  - `noUnusedLocals`: true
  - `noUnusedParameters`: true
  - `noFallthroughCasesInSwitch`: true
  - `strict`: true

## Import Organization

**Order:**
1. External dependencies (React, React Router, React Query)
2. Internal utilities and constants (lib/api, lib/constants, utils)
3. Components (local to the module)
4. Type definitions (types/index)

**Examples from codebase:**
```typescript
// App.tsx - frontend component imports
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout/Layout';
import { ProjectList } from './components/Projects/ProjectList';
```

```python
# projects.py - backend endpoint imports
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...utils import validate_project_title, validate_framework
from ...exceptions import NotFoundException, ValidationException
```

**Path Aliases:**
- Frontend: No aliases configured in tsconfig
- Backend: Uses relative imports with `from app.models import schemas`

## Error Handling

**Backend Patterns:**
Custom exception hierarchy in `backend/app/exceptions.py`:
- `AppException` - base exception with status_code and detail
- `ValidationException` - 400 Bad Request, field-specific errors
- `AuthenticationException` - 401 Unauthorized with WWW-Authenticate header
- `AuthorizationException` - 403 Forbidden
- `NotFoundException` - 404 with resource name
- `ConflictException` - 409 Conflict
- `RateLimitException` - 429 with Retry-After header
- `ExternalServiceException` - 503 Service Unavailable
- `DatabaseException` - 500 for DB errors
- `ConfigurationException` - 500 for config errors

**Validation Pattern:**
Validator functions in `backend/app/utils/validators.py` raise `HTTPException`:
```python
def validate_project_title(title: str) -> None:
    if not title or not title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project title cannot be empty"
        )
```

**Pydantic Field Validators:**
Schemas use `@field_validator` decorator for input validation:
```python
@field_validator('prompt')
def validate_prompt(cls, v):
    if not v.strip():
        raise ValueError("Prompt cannot be empty or just whitespace")
    return v.strip()
```

**API Response Handler:**
Custom exception handlers in `main.py` transform validation errors into structured JSON:
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": field, "message": message} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": errors})
```

**Frontend Error Handling:**
React components check error states from React Query:
```typescript
const { data: project, isLoading, isError, error } = useQuery({...});

if (isError) {
  return (
    <div>
      <p>{ERROR_MESSAGES.GENERIC}</p>
      <p>{error instanceof Error ? error.message : ERROR_MESSAGES.NETWORK}</p>
    </div>
  );
}
```

API wrapper throws errors that bubble to React Query:
```typescript
const fetchWithTimeout = async (url: string, options: RequestInit = {}) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    throw error;
  }
};
```

## Logging

**Framework:** Python's built-in `logging` module

**Setup Pattern:**
```python
import logging

logger = logging.getLogger(__name__)
```

**When/How to Log:**
- Backend startup/config: `logger.warning()` for non-fatal config issues (e.g., default SECRET_KEY)
- Service operations: `logger.info()` for major operations (e.g., "Action mode: phase=...", "Action mode: updated ListItem {item.id}")
- Errors: `logger.error()` with `exc_info=True` for exception context
- Example from `ai_chat.py`:
  ```python
  logger.info(f"Action mode: phase={session.phase}, subsection={session.subsection_key}")
  logger.warning(f"Session {session_id} was deleted during AI response generation")
  logger.error(f"Action streaming error: {e}", exc_info=True)
  ```

**Frontend:**
- No structured logging; uses `console.error/warn/log` implicitly through error boundaries
- React Query handles request logging internally

## Comments

**When to Comment:**
- Complex algorithms or multi-step validation logic
- Non-obvious business rules (e.g., framework-specific behavior)
- Workarounds or hacks

**DocString Style:**
- Backend: Triple-quoted docstrings on functions (Google style):
  ```python
  def validate_project_title(title: str) -> None:
      """Validate project title"""
  ```
- Frontend: JSDoc-style comments for hooks and utility functions:
  ```typescript
  // Get auth token from localStorage or use mock token for development
  const getAuthToken = () => {
  ```

**Section Dividers:**
- Backend: None observed (uses clear function/class organization)
- Frontend: Section markers for related API methods:
  ```typescript
  // ============================================================
  // Books
  // ============================================================
  ```

## Function Design

**Size:** Keep functions focused on single responsibility
- Backend validators: 10-15 lines
- API endpoints: 20-40 lines (includes validation + DB operations)
- Frontend hooks: 15-25 lines
- Frontend components: 50-150 lines (split complex logic into custom hooks)

**Parameters:**
- Backend: Use dependency injection for DB sessions and auth
  ```python
  async def create_project(
      project: schemas.ProjectCreate,
      current_user: schemas.User = Depends(get_current_user),
      db: Session = Depends(get_db)
  ):
  ```
- Frontend: Use object parameters for multiple related options
  ```typescript
  function useKeyboardShortcuts({ onSave, onReview }: UseKeyboardShortcutsProps)
  ```

**Return Values:**
- Backend: Return Pydantic response models (automatically serialized to JSON)
  ```python
  @router.post("/", response_model=schemas.Project)
  async def create_project(...) -> schemas.Project:
      return db_project
  ```
- Frontend: Return data or null for optional async results
  ```typescript
  async lookupAISession(...): Promise<AISessionResponse | null>
  ```

## Module Design

**Exports:**
- Backend: Router instances exported as `router` (included in main app):
  ```python
  router = APIRouter()
  @router.post("/", response_model=schemas.Project)
  ```
- Frontend: Named exports for components and utilities:
  ```typescript
  export function Editor() { }
  export const api = { /* methods */ }
  ```

**Barrel Files:**
- `frontend/src/types/index.ts` - exports all type definitions
- `backend/app/utils/__init__.py` - empty (functions imported directly)
- `backend/app/api/endpoints/__init__.py` - empty (routers imported directly)

---

*Convention analysis: 2026-03-01*
