# Testing Patterns

**Analysis Date:** 2026-07-24

## Test Framework

**Runner:**
- pytest 8.0.2 (backend only)
- Config: `backend/pytest.ini`
- Plugins: `pytest-asyncio` 0.23.5 (`asyncio_mode = auto` — async tests need no decorator), `pytest-cov` 4.1.0, `pytest-rerunfailures` 14.0 (absorbs documented suite-isolation flakes; real failures still fail all reruns)

**Assertion Library:**
- Plain `assert` (pytest rewriting). No separate assertion lib.

**Scope & scale:**
- ~52 test modules in `backend/app/tests/` (~594 `test_` functions). Covers API endpoints, services, MCP tools, models, validators, breakdown, seasons, shots, storyboard, snippets, staleness, bible/wizard injection, and vapai integration scope.

**Run Commands:**
```bash
cd backend
source venv/bin/activate

pytest                                         # Run whole suite (from backend/, pythonpath=. via pytest.ini)
pytest app/tests/test_api.py                   # One module
pytest app/tests/test_validators.py            # Validator tests
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid  # Single test
pytest --cov=app                               # Coverage (pytest-cov)
```

## Environment / Venv Gotchas (read before running)

- **Use Python 3.11 for the venv.** Python 3.14 breaks SQLAlchemy/tiktoken; 3.11 is the supported line.
- **The `mcp` dependency must be installed** or the WHOLE suite fails to collect (import-time failure in `app.main`). If the venv is missing `mcp`, install it, then re-pin `starlette<0.37` (per `requirements.txt`, `mcp>=1.27.2` otherwise pulls a starlette 1.x that breaks FastAPI 0.110).
- Tests never touch real Postgres or OpenAI: `conftest.py` sets `SKIP_DB_INIT=1` and `SKIP_MCP_LIFESPAN=1` at import time (before `from app.main import app`), and rebinds the DB to in-memory SQLite. Live OpenAI calls are avoided via the `mock_embed` fixture and per-test `patch`.

## Test File Organization

**Location:**
- Separate `backend/app/tests/` directory (not co-located with source).

**Naming:**
- `test_<subject>.py`; subject mirrors the module/feature under test.

**Structure:**
```
backend/app/tests/
├── conftest.py              # shared fixtures + SQLite adaptation
├── test_api.py              # REST endpoint tests (class-grouped)
├── test_validators.py
├── test_breakdown_service.py
├── test_mcp_*.py            # MCP tool suites
├── test_seasons_api.py, test_shots_api.py, ...
└── ...
```

## Test Structure

**Suite Organization** — tests are grouped in classes by resource, methods receive fixtures as params:
```python
class TestProjectsAPI:
    """Test projects API endpoints"""

    def test_create_project_valid(self, client, mock_auth_headers):
        response = client.post(
            "/api/projects/",
            json={"title": "Test Project", "framework": "three_act"},
            headers=mock_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Test Project"
```

**Patterns:**
- Validation errors assert 422 and inspect the `errors` array: `assert any("title" in e["field"] for e in response.json()["errors"])`.
- Create-then-act: POST to create a resource, read its `id` from the response, then PATCH/GET against it (see `test_update_project_validation`).

## Key Fixtures (`backend/app/tests/conftest.py`)

- `test_engine` (session, autouse via `_bind_app_db_to_test_engine`) — in-memory SQLite (`sqlite://`, StaticPool). `_patch_uuid_columns_for_sqlite()` swaps PG `UUID`→`String(36)`, native `Enum`→`String(50)`, and `SafeVector`→`VectorAsText` (JSON round-trip) so the Postgres schema runs on SQLite.
- `_bind_app_db_to_test_engine` — rebinds `app.db.engine`/`app.db.SessionLocal` to the test engine for the whole session (needed because some paths call `SessionLocal()` directly instead of the overridden dependency).
- `db_session` (function) — fresh session per test, rolled back and closed on teardown.
- `client` (function) — `TestClient(app)` with `get_db` overridden to the test session; clears `dependency_overrides` after.
- `mock_auth_headers` — `{"Authorization": "Bearer mock-token"}`.
- `mock_embed` — patches `embedding_service.embed_text` (AsyncMock) to a fixed 1536-float vector; use in any test that creates/edits snippets so no live OpenAI embedding call fires.

## Rate-Limiter Reset (REQUIRED in new API test files)

`RateLimitMiddleware` keeps an in-memory per-IP request log shared across the whole session. In the full suite the shared `testclient` IP accumulates enough requests to trip the 60/min limit, so later tests get 429 instead of hitting the route. Any new test file that makes several client requests MUST add an autouse fixture that clears the live middleware instance's log before each test:

```python
from app.main import app
from app.middleware import RateLimitMiddleware

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    node = getattr(app, "middleware_stack", None)
    while node is not None:
        if isinstance(node, RateLimitMiddleware):
            node.requests = {}
            break
        node = getattr(node, "app", None)
    yield
```

Present in `test_vapai_scope.py` and `test_bible_wizard.py`. Omitting it produces spurious 429s in unrelated later tests.

## Mocking

**Framework:** `unittest.mock` (`patch`, `AsyncMock`).

**Patterns:**
```python
from unittest.mock import patch, AsyncMock

with patch(
    "app.services.embedding_service.embedding_service.embed_text",
    new_callable=AsyncMock,
    return_value=[0.1] * 1536,
):
    ...
```
- External services (OpenAI, vapai) are patched at the service-instance attribute so the endpoint's routing/validation is asserted without network calls (see `test_vapai_scope.py`: `vapai_service` patched, assert which method the route calls).

**What to Mock:** OpenAI/embeddings, the vapai bridge, any outbound network call.
**What NOT to Mock:** the DB (use the real in-memory SQLite engine), FastAPI routing/middleware (exercised through `TestClient`).

## Fixtures and Factories

- No factory library; tests build data inline (dicts POSTed to endpoints, or ORM rows constructed directly, e.g. `Project`, `Show`, `ScreenplayContent` in `test_vapai_scope.py`).
- Owner-scoped rows must use the mock user id `12345678-1234-5678-1234-567812345678` to be visible under mock auth.

## Coverage

**Requirements:** None enforced (no threshold configured).
```bash
cd backend && pytest --cov=app
```

## Test Types

**Unit tests:** validators, services, models, staleness/pipeline logic (`test_validators.py`, `test_breakdown_service.py`, `test_pipeline_composer.py`, etc.).
**Integration tests:** endpoint tests through `TestClient` against the real in-memory DB (`test_api.py`, `test_*_api.py`); MCP tool suites (`test_mcp_*.py`). `test_mcp_foundation.py` runs the real app lifespan itself and does NOT use the shared fixtures.
**E2E tests:** None.

## Frontend Tests

**None present.** No `*.test.*` / `*.spec.*` files under `frontend/src/`, no test runner (Vitest/Jest) in `frontend/package.json`. Frontend quality gates are TypeScript strict compilation (`tsc && vite build`) and ESLint (`npm run lint`, `--max-warnings 0`). Adding frontend tests would mean introducing a runner (e.g. Vitest) from scratch.

## Common Patterns

**Async testing** (`asyncio_mode = auto` — no decorator needed):
```python
async def test_something():
    result = await some_async_service()
    assert result == expected
```

**Error testing:**
```python
response = client.post("/api/projects/", json={"title": ""}, headers=mock_auth_headers)
assert response.status_code == 422
assert any("title" in e["field"] for e in response.json()["errors"])
```

---

*Testing analysis: 2026-07-24*
