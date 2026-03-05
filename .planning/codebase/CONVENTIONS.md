# Coding Conventions

**Analysis Date:** 2025-03-05

## Naming Patterns

**Files:**
- Backend: snake_case for all Python files (e.g., `openai_service.py`, `auth_service.py`)
- Frontend: PascalCase for React components (e.g., `Editor.tsx`, `SectionEditor.tsx`), lowercase for utilities (e.g., `api.tsx`, `constants.ts`, `utils.ts`)
- Models: PascalCase for classes and enums (e.g., `Framework`, `SectionType`)
- Packages: kebab-case for directories (e.g., `api/endpoints/`, `components/UI/`)

**Functions:**
- Backend: snake_case for all function and method names (e.g., `validate_project_title()`, `verify_password()`)
- Frontend: camelCase for functions and hooks (e.g., `getAuthToken()`, `useKeyboardShortcuts()`)
- Async functions in backend prefixed with `async def` (e.g., `async def review_section()`)
- Hook functions prefixed with `use` (e.g., `useKeyboardShortcuts`, `useQuery`)

**Variables:**
- Backend: snake_case (e.g., `db_project`, `request_id`, `cache_key`)
- Frontend: camelCase (e.g., `selectedSectionId`, `isLoading`, `authToken`)
- Constants: UPPERCASE_SNAKE_CASE in both (e.g., `API_TIMEOUT`, `MAX_SECTION_LENGTH`)

**Types:**
- Frontend TypeScript enums: PascalCase values (e.g., `Framework.THREE_ACT`)
- Backend SQLAlchemy enums: UPPERCASE values (e.g., `SectionType.INCITING_INCIDENT`)
- Pydantic models: PascalCase with `BaseModel` suffix (e.g., `ProjectCreate`, `ChecklistItem`)
- Type interfaces in frontend: PascalCase (e.g., `ButtonProps`, `UseKeyboardShortcutsProps`)

## Code Style

**Formatting:**
- Frontend: No explicit formatter configured (ESLint used for linting)
- Backend: No explicit formatter configured (follows Python conventions)
- Tailwind CSS for all styling in frontend—uses utility-first approach
- CSS variables for theming: defined as HSL values (e.g., `--ring`, `--primary`, `--foreground`)

**Linting:**
- Frontend: ESLint with TypeScript support enabled
  - Config: `frontend/package.json` scripts (`npm run lint`)
  - Rules: `eslint` + `@typescript-eslint/eslint-plugin` + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh`
  - Reports unused disable directives and enforces zero warnings: `--max-warnings 0`
- Backend: No linter enforced (pytest used for testing)

**Line Length:**
- No explicit line length limit observed
- React components average 100-150 lines
- Python functions average 30-80 lines

## Import Organization

**Order (Frontend):**
1. React/Library imports (`import React from 'react'`)
2. External packages (`import { useQuery } from '@tanstack/react-query'`)
3. Icons (`import { Loader2 } from 'lucide-react'`)
4. Internal lib imports (`import { api } from '../../lib/api'`)
5. Component imports (`import { Button } from '../UI/Button'`)
6. Type imports (`import { Project, Section } from '../types'`)
7. Config/constants (`import { QUERY_KEYS } from '../../lib/constants'`)

**Order (Backend):**
1. Standard library imports (`import json`, `import logging`)
2. Third-party imports (`from fastapi import`, `from sqlalchemy import`)
3. Internal app imports (`from ..models import`, `from ..services import`)
4. Relative service imports (`from ..config import settings`)

**Path Aliases:**
- Frontend: No path aliases configured (relative imports only)
- Backend: Relative imports with dots (e.g., `from ..models import schemas`)

## Error Handling

**Patterns:**

**Backend:**
- Custom exception hierarchy in `app/exceptions.py`:
  - `AppException` (base, extends HTTPException)
  - `ValidationException` (400 Bad Request)
  - `AuthenticationException` (401 Unauthorized)
  - `AuthorizationException` (403 Forbidden)
  - `NotFoundException` (404 Not Found)
  - `ConflictException` (409 Conflict)
  - `RateLimitException` (429 Too Many Requests)
  - `ExternalServiceException` (503 Service Unavailable)
  - `OpenAIException` (extends ExternalServiceException)
  - `DatabaseException` (500 Internal Server Error)
  - `ConfigurationException` (500 Internal Server Error)

Example usage in `app/api/endpoints/projects.py`:
```python
if not validate_framework(project.framework.value):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid framework selected"
    )
```

- Validation errors in `app/main.py` caught at global level:
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        errors.append({"field": field, "message": message})
    return JSONResponse(status_code=422, content={"detail": "Validation error", "errors": errors})
```

- Try/catch in dependencies:
```python
try:
    user_id = auth_service.verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(...)
except Exception as e:
    raise HTTPException(status_code=401, ...)
```

**Frontend:**
- Error handling in React Query hook with conditional rendering:
```typescript
if (isError) {
  return (
    <div className="flex flex-col items-center justify-center h-[80vh]">
      <p className="text-foreground font-medium">{ERROR_MESSAGES.GENERIC}</p>
      <p className="text-sm text-muted-foreground">
        {error instanceof Error ? error.message : ERROR_MESSAGES.NETWORK}
      </p>
    </div>
  );
}
```

- Promise rejection in async operations:
```typescript
if (!response.ok) throw new Error('Failed to fetch projects');
return response.json();
```

- AbortError handling for timeouts:
```typescript
if (error instanceof Error && error.name === 'AbortError') {
  throw new Error('Request timeout');
}
```

## Logging

**Framework:**
- Backend: Python's built-in `logging` module
- Frontend: Console methods (`console.log`, `console.error`)—no structured logging library

**Patterns:**

Backend (in `app/main.py`):
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

In middleware (`app/middleware.py`):
```python
logger.info(
    f"Request [{request_id}]: {request.method} {request.url.path} "
    f"Client: {request.client.host if request.client else 'Unknown'}"
)
logger.info(f"Response [{request_id}]: {response.status_code} Duration: {duration:.3f}s")
```

In services (`app/config.py`):
```python
logger.warning("Using default SECRET_KEY - please change in production!")
```

When to log:
- Request/response metadata in middleware
- Configuration warnings
- Service initialization
- Error context (auth failures, external service calls)
- Do NOT log in tests unless debugging

## Comments

**When to Comment:**
- Complex algorithm logic (cache key generation, LRU eviction)
- Non-obvious business rules (framework-specific behavior)
- Integration points with external services
- Workarounds and known limitations

**JSDoc/TSDoc:**
- Minimal use in codebase
- Docstrings on service classes and public methods: example from `app/services/openai_service.py`:
```python
async def review_section(
    self,
    section_id: str,
    text: str,
    framework: Framework,
    section_type: SectionType
) -> Dict[str, List[str]]:
    """Send section text to OpenAI for review"""
```

- No @param/@return annotations observed
- Type hints used instead of inline documentation

## Function Design

**Size:**
- Most functions stay under 50 lines
- Service methods average 20-40 lines
- React components (excluding render) average 100-150 lines total
- Validators are typically 10-15 lines

**Parameters:**
- Backend: Use Pydantic models for complex parameters (e.g., `schemas.ProjectCreate`)
- Frontend: Use typed interfaces (e.g., `ButtonProps extends React.ButtonHTMLAttributes`)
- Avoid long parameter lists—use destructuring: `const { onSave, onReview } = props`
- Optional parameters use `Optional[Type]` in Python and `?: Type` in TypeScript

**Return Values:**
- Backend services return Pydantic models or dicts
- API endpoints return response models defined in `schemas.py`
- Async functions always declared with `async def` and return awaitable
- Frontend hooks return primitive values or objects (no JSX from utility hooks)

## Module Design

**Exports:**
- Backend: Functions/classes exported implicitly, router pattern for endpoints
- Frontend: Named exports for components: `export { Button, buttonVariants }`
- Services exported as singleton instances: `auth_service = AuthService()`

Example from `app/services/auth_service.py`:
```python
# Singleton instance
auth_service = AuthService()

# Mock authentication for MVP
class MockAuthService:
    ...

# Would be instantiated separately
mock_auth_service = MockAuthService()
```

**Barrel Files:**
- Frontend: API object pattern in `lib/api.tsx` aggregates all API calls:
```typescript
export const api = {
  async getProjects(): Promise<Project[]> { ... },
  async getProject(id: string): Promise<Project> { ... },
  async createProject(data: { ... }): Promise<Project> { ... }
}
```

- Backend: Router pattern in `main.py` includes all routers:
```python
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
```

- No explicit barrel exports (`index.ts`, `__init__.py` mostly empty)

## Dependency Injection

**Backend:**
- FastAPI `Depends()` for DI: `Depends(get_db)`, `Depends(get_current_user)`
- Middleware system for cross-cutting concerns (logging, security, rate limiting)
- Singleton pattern for services: `auth_service = AuthService()`

**Frontend:**
- React Context (not used; props drilling preferred for this MVP)
- React Query for server state management with caching
- Custom hooks for shared logic: `useKeyboardShortcuts()`

## Constants and Configuration

**Location:**
- Backend: `app/config.py` using Pydantic Settings
- Frontend: `lib/constants.ts` for all magic numbers and configs

Frontend constants pattern (`lib/constants.ts`):
```typescript
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
export const API_TIMEOUT = 30000; // 30 seconds
export const FRAMEWORK_CONFIG = { ... };
```

Backend config pattern (`app/config.py`):
```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://..."
    OPENAI_API_KEY: str = ""
    @field_validator('SECRET_KEY')
    def validate_secret_key(cls, v):
        if v == "your-secret-key-replace-in-production":
            logger.warning("Using default SECRET_KEY...")
        return v
```

---

*Convention analysis: 2025-03-05*
