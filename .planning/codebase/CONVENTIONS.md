# Coding Conventions

**Analysis Date:** 2026-03-11

## Naming Patterns

**Files:**
- Python backend: `snake_case` (e.g., `openai_service.py`, `validators.py`, `conftest.py`)
- TypeScript/React: `PascalCase` for components and interfaces, `camelCase` for utilities and hooks (e.g., `ProjectCard.tsx`, `useKeyboardShortcuts.tsx`, `api.tsx`)
- Test files: `test_*.py` (Python) — descriptive names indicating what is tested

**Functions:**
- Python: `snake_case` with descriptive verbs (e.g., `validate_project_title()`, `_generate_cache_key()`, `_get_system_prompt()`)
- TypeScript/React: `camelCase` for functions and methods, `PascalCase` for React components (e.g., `formatDate()`, `handleKeyDown()`, `ProjectCard()`)
- Private/internal functions: prefix with underscore in both Python and TypeScript (e.g., `_patch_uuid_columns_for_sqlite()`, `_get_openai_client()`)
- Custom hooks: prefix with `use` (e.g., `useKeyboardShortcuts()`)

**Variables:**
- Python: `snake_case` (e.g., `cache_key`, `db_session`, `sanitized_text`)
- TypeScript/React: `camelCase` for variables (e.g., `templateColor`, `isTemplateProject`, `currentUser`)
- Constants: `UPPER_SNAKE_CASE` in Python, `UPPER_SNAKE_CASE` in TypeScript when defined in constants files or globally (e.g., `API_BASE_URL`, `MAX_SECTION_LENGTH`, `DEBOUNCE_DELAY`)
- React props objects: `camelCase` (e.g., `onDelete`, `onSave`, `isLoading`)

**Types:**
- TypeScript interfaces: `PascalCase` without `I` prefix (e.g., `ChecklistItem`, `Project`, `ReviewResponse`, not `IProject`)
- TypeScript enums: `PascalCase` with `UPPER_SNAKE_CASE` enum values (e.g., `enum SectionType { INCITING_INCIDENT = "inciting_incident" }`)
- Python Pydantic models: `PascalCase` with suffixes for variants (e.g., `ProjectCreate`, `ProjectUpdate`, `ProjectBase`)
- Database models: `PascalCase` in `database.py` (e.g., `Project`, `Section`, `ChecklistItem`)

## Code Style

**Formatting:**
- No explicit Prettier or ESLint config in project root (not detected)
- Backend: Follows PEP 8 conventions implicitly
- Frontend: TypeScript strict mode enabled (`tsconfig.json`), basic ESLint setup from `package.json` with `eslint-plugin-react-hooks` and `eslint-plugin-react-refresh`
- Line length: No explicit limit, but kept reasonable (typically under 100 characters)

**Linting:**
- Frontend: `npm run lint` runs ESLint with `--max-warnings 0` (fails if any warnings), checks `.ts` and `.tsx` files
- Backend: No explicit linter configured, but tests use pytest
- TypeScript strict mode: enabled in `frontend/tsconfig.json`

## Import Organization

**Order (Frontend - `api.tsx` pattern):**
1. External packages (React, third-party libraries)
2. Internal types (from `../types`)
3. Internal utilities/constants (from `../lib`)
4. Components (relative imports)

Example from `frontend/src/lib/api.tsx`:
```typescript
import {
  Project, Section, ChecklistItem, ReviewRequest, ReviewResponse,
  Book, Concept, Agent, AgentType, ChatSession, ChatMessage,
} from '../types';
import type { YoloEvent } from '../types/template';
import { API_BASE_URL, AUTH_TOKEN_KEY, API_TIMEOUT } from './constants';
```

**Order (Backend - `endpoints/projects.py` pattern):**
1. Standard library
2. Third-party (FastAPI, SQLAlchemy, etc.)
3. Relative imports from current package (models, dependencies, utils, services)

Example from `backend/app/api/endpoints/projects.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID

from ...models import schemas, database
from ..dependencies import get_db, get_current_user
from ...utils import validate_project_title, validate_framework
```

**Path Aliases:**
- Frontend uses relative paths (no path aliases configured)
- Backend uses relative imports with `..` notation (configured via `PYTHONPATH` in Dockerfile)

## Error Handling

**Backend Patterns (`app/exceptions.py`):**
- Custom exception hierarchy: `AppException` base class extending `HTTPException`
- Specific exception types: `ValidationException`, `AuthenticationException`, `AuthorizationException`, `NotFoundException`, `ConflictException`, `RateLimitException`, `ExternalServiceException`, `OpenAIException`, `DatabaseException`, `ConfigurationException`
- All exceptions include status code and detail message
- Usage in endpoints: raise exceptions directly (e.g., `raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")`)
- Try-catch patterns in service methods (e.g., `app/services/openai_service.py`): wrap external API calls, log errors, raise `OpenAIException`

Example from `backend/app/api/endpoints/review.py` (lines 55-75):
```python
try:
    review_result = await openai_service.review_section(...)
    section.ai_suggestions = review_result
    db.commit()
    return review_result
except Exception as e:
    print(f"Review error: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error processing review request"
    )
```

**Frontend Patterns:**
- API errors caught in `lib/api.tsx` fetch wrapper with timeout handling (AbortError)
- Component-level error handling via React Query error states
- No explicit error boundary detected; errors logged to console or handled in mutation/query error callbacks

## Logging

**Framework:** Python `logging` module

**Backend Implementation:**
- Logger initialized per module: `logger = logging.getLogger(__name__)`
- Log levels used: `logger.error()`, `logger.info()` (implicit from review of files)
- Error logging: `logger.error(f"OpenAI API error: {str(e)}")` (from `openai_service.py`)
- Print statements also used for quick debugging (e.g., `print(f"Review error: {str(e)}")`) — not ideal but present

**Frontend:**
- No explicit logging framework; relies on console methods
- Could benefit from structured logging setup

## Comments

**When to Comment:**
- Use comments sparingly; code should be self-documenting
- Comment complex algorithms and non-obvious decisions
- Docstrings used in test functions for clarity (e.g., `"""Test email validation"""`)
- Module-level docstrings in service files explain purpose (e.g., `app/services/ai_provider.py`)

**JSDoc/TSDoc:**
- Minimal usage observed
- Test functions include docstrings describing what they test
- Not systematically enforced

Example from `app/tests/test_snippets_api.py`:
```python
def test_edit_snippet_persists(self, client, db_session, mock_auth_headers, mock_embed):
    """EDIT-01: PATCH updates content in DB."""
```

## Function Design

**Size:** Functions kept reasonably small; endpoints in `endpoints/*.py` are 10-30 lines typically

**Parameters:**
- FastAPI dependency injection used for common parameters (`get_db`, `get_current_user`)
- Pydantic models for request bodies
- Type hints everywhere in Python and TypeScript

Example from `backend/app/api/endpoints/projects.py`:
```python
async def create_project(
    project: schemas.ProjectCreate,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```

**Return Values:**
- Backend endpoints return Pydantic models or lists (with `response_model` annotation)
- Services return typed objects (dicts, lists, objects)
- Frontend API methods return typed promises (`Promise<Project>`, `Promise<Project[]>`)
- Async functions used extensively in backend (FastAPI async)

## Module Design

**Exports:**
- Python: explicit imports in `__init__.py` where needed; modules import directly from files
- TypeScript: index files or direct imports from component files

**Barrel Files:**
- Frontend: no explicit barrel files in observed structure; components imported individually
- Backend: services, endpoints imported directly from module files

**Organization by Feature/Layer:**
- Backend: organized by layer (`api/endpoints/`, `services/`, `models/`, `utils/`)
- Frontend: organized by component type (`components/`, `lib/`, `hooks/`, `types/`)

## Async/Await Patterns

**Backend (Python):**
- Service methods marked `async` for external API calls
- Endpoints marked `async` and use `await` for service calls
- Example from `openai_service.py`:
```python
async def review_section(
    self,
    section_id: str,
    text: str,
    framework: Framework,
    section_type: SectionType
) -> Dict[str, List[str]]:
    # ...
    ai_text = await chat_completion(...)
```

**Frontend (TypeScript):**
- React Query `useQuery` and `useMutation` hooks handle async data fetching
- Direct `await` calls in event handlers rare; prefer callback-based mutations
- Example from `components/Books/BookManager.tsx`:
```typescript
const { data: books } = useQuery({
  queryKey: [QUERY_KEYS.BOOKS],
  queryFn: api.getBooks,
});
```

## Data Validation

**Backend:**
- Pydantic v2 field validators in schema models (`models/schemas.py`)
- Validator functions in `utils/validators.py` for complex validation
- Validators strip whitespace, enforce length constraints, validate formats
- HTML sanitization in review endpoints (`sanitize_html()`)

Example from `models/schemas.py`:
```python
class ProjectBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)

    @field_validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty or just whitespace")
        return v.strip()
```

**Frontend:**
- Type safety via TypeScript
- Minimal runtime validation (relies on backend validation)
- No explicit validation schema library (zod, yup, etc.)

---

*Convention analysis: 2026-03-11*
