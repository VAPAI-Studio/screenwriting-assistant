# Testing Patterns

**Analysis Date:** 2026-03-06

## Test Framework

**Runner:**
- pytest (Python backend only)
- Config: no `pytest.ini` or `pyproject.toml` test config detected — uses pytest defaults

**Assertion Library:**
- Built-in `assert` statements (pytest rewrites)
- `pytest.raises` for exception testing

**Run Commands:**
```bash
cd backend
source venv/bin/activate
pytest app/tests/test_api.py                    # API endpoint tests
pytest app/tests/test_validators.py             # Validator unit tests
pytest app/tests/test_snippets_api.py           # Snippet Phase 1 tests
pytest app/tests/test_snippet_manager.py        # Snippet Phase 2 tests
pytest app/tests/test_snippet_extraction.py     # Extraction pipeline tests
pytest app/tests/test_api.py -v                 # Verbose output
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid  # Single test
```

## Test File Organization

**Location:**
- All tests co-located in `backend/app/tests/`
- No frontend tests exist

**Naming:**
- Test files: `test_{module}.py` — `test_api.py`, `test_validators.py`, `test_snippets_api.py`, `test_snippet_manager.py`, `test_snippet_extraction.py`
- Test classes: `Test{Feature}` — `TestProjectsAPI`, `TestSectionsAPI`, `TestSnippetsAPI`, `TestSnippetExtraction`
- Test methods: `test_{what_is_tested}` — `test_create_project_valid`, `test_edit_snippet_persists`

**Structure:**
```
backend/app/tests/
├── __init__.py
├── conftest.py                    # Fixtures: engine, db_session, client, auth headers, mock_embed
├── test_api.py                    # Core API: projects, sections, review, auth, middleware
├── test_validators.py             # Unit tests for backend/app/utils/validators.py
├── test_snippets_api.py           # Phase 1: /api/books/{id}/snippets (BookChunk-based)
├── test_snippet_manager.py        # Phase 2: /api/snippets (Snippet entity)
└── test_snippet_extraction.py     # Phase 2: AI extraction pipeline
```

## Test Structure

**Suite Organization:**
```python
class TestProjectsAPI:
    """Test projects API endpoints"""

    def test_create_project_valid(self, client, mock_auth_headers):
        """Test creating a project with valid data"""
        response = client.post(
            "/api/projects/",
            json={"title": "Test Project", "framework": "three_act"},
            headers=mock_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Project"
        assert data["framework"] == "three_act"

    def test_create_project_invalid_title(self, client, mock_auth_headers):
        """Test creating a project with invalid title"""
        response = client.post(
            "/api/projects/",
            json={"title": "", "framework": "three_act"},
            headers=mock_auth_headers
        )
        assert response.status_code == 422
        errors = response.json()["errors"]
        assert any("title" in error["field"] for error in errors)
```

**Patterns:**
- Each test class groups tests for one feature area or API resource
- Test methods receive fixtures via pytest injection — `self, client, db_session, mock_auth_headers`
- Docstrings reference requirement IDs — `"""BROW-01: GET /api/books/{id}/snippets returns paginated list."""`
- Happy path tested first, then validation failures, then edge cases

## Fixtures (conftest.py)

**All fixtures defined in `backend/app/tests/conftest.py`:**

**`test_engine` (session-scoped):**
```python
@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine (SQLite in-memory)."""
    _patch_uuid_columns_for_sqlite()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
```

**`db_session` (function-scoped):**
```python
@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
```

**`client` (function-scoped):**
```python
@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden DB dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**`mock_auth_headers`:**
```python
@pytest.fixture
def mock_auth_headers():
    """Return headers with mock authentication token."""
    return {"Authorization": "Bearer mock-token"}
```

**`mock_embed`:**
```python
@pytest.fixture
def mock_embed():
    """Mock embedding_service.embed_text to return a fixed 1536-float vector."""
    fake_embedding = [0.1] * 1536
    with patch(
        "app.services.embedding_service.embedding_service.embed_text",
        new_callable=AsyncMock,
        return_value=fake_embedding,
    ) as mock:
        yield mock
```

## Database Strategy

**SQLite in-memory with PostgreSQL compatibility patches:**
- Production uses PostgreSQL; tests use SQLite via `StaticPool`
- `_patch_uuid_columns_for_sqlite()` in `backend/app/tests/conftest.py` patches at session start:
  - PostgreSQL `UUID` columns → `String(36)`
  - PostgreSQL `Enum` columns → `String(50)`
  - Custom `SafeVector` columns → `VectorAsText()` (JSON serialization for vector data)
- `sqlite3.register_adapter(uuid.UUID, lambda u: str(u))` adapts Python UUIDs
- Custom `VectorAsText` TypeDecorator serializes lists as JSON strings for SQLite round-tripping

**Session lifecycle:**
- Engine created once per test session (all tables created once)
- Each test gets a fresh `db_session` that rolls back on teardown
- FastAPI `get_db` dependency overridden per test via `app.dependency_overrides`

## Mocking

**Framework:** `unittest.mock` — `patch`, `AsyncMock`

**External Service Mocking:**
```python
# Mock the embedding service to avoid real OpenAI calls
with patch(
    "app.services.embedding_service.embedding_service.embed_text",
    new_callable=AsyncMock,
    return_value=[0.1] * 1536,
) as mock:
    yield mock
```

```python
# Mock AI extraction to return fixed response
with patch.object(
    service,
    "_call_ai",
    new_callable=AsyncMock,
    return_value=FIXED_AI_RESPONSE,
):
    raw_snippets = asyncio.get_event_loop().run_until_complete(
        service.extract_snippets(...)
    )
```

**Failure Simulation for Atomic Rollback Tests:**
```python
with patch(
    "app.services.embedding_service.embedding_service.embed_text",
    new_callable=AsyncMock,
    side_effect=RuntimeError("Embedding service unavailable"),
):
    with TestClient(app, raise_server_exceptions=False) as rollback_client:
        resp = rollback_client.patch(...)
    assert resp.status_code >= 500

# Verify DB unchanged
db_session.expire(chunk)
db_session.refresh(chunk)
assert chunk.content == original_content
```

**What to Mock:**
- OpenAI embedding service (`embedding_service.embed_text`)
- AI extraction service (`_call_ai`)
- Any external API call

**What NOT to Mock:**
- Database operations — use real SQLite in-memory DB
- FastAPI routing, middleware, validation — tested through the full stack via `TestClient`
- Pydantic schema validation

## Fixtures and Factories

**Test Data Helpers (defined as methods on test classes):**
```python
class TestSnippetsAPI:
    def _make_book(self, db_session):
        """Helper: create a completed book owned by the mock user."""
        book = Book(
            id=uuid.uuid4(),
            owner_id=MOCK_USER_ID,
            title="Test Book",
            filename="test.pdf",
            file_type="pdf",
            status=BookStatus.COMPLETED,
        )
        db_session.add(book)
        db_session.commit()
        return book

    def _make_chunk(self, db_session, book, index=0, is_user_created=False):
        """Helper: create a BookChunk fixture."""
        chunk = BookChunk(
            id=uuid.uuid4(),
            book_id=book.id,
            chunk_index=index,
            content=f"Chunk content {index}",
            token_count=10,
            is_user_created=is_user_created,
            is_deleted=False,
        )
        db_session.add(chunk)
        db_session.commit()
        return chunk
```

**Mock User ID constant:**
```python
MOCK_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
```

**Location:**
- Shared fixtures: `backend/app/tests/conftest.py`
- Class-specific helpers: `_make_book()`, `_make_chunk()`, `_make_snippet()` defined as private methods on test classes

## Coverage

**Requirements:** None enforced — no coverage config or thresholds detected

**View Coverage:**
```bash
cd backend && source venv/bin/activate
pytest --cov=app app/tests/     # If pytest-cov installed
```

## Test Types

**Unit Tests:**
- `backend/app/tests/test_validators.py` — tests standalone validation functions in isolation
- Pure function tests: input/output assertions, `pytest.raises` for expected exceptions
- No DB or HTTP client needed

**Integration Tests (API):**
- `backend/app/tests/test_api.py` — tests endpoint handlers through FastAPI TestClient
- `backend/app/tests/test_snippets_api.py` — Phase 1 snippet CRUD
- `backend/app/tests/test_snippet_manager.py` — Phase 2 snippet manager CRUD
- Full request/response cycle: HTTP method, headers, JSON body, status code, response body
- Database state verified after mutations: `db_session.refresh(obj); assert obj.field == expected`

**Pipeline Tests:**
- `backend/app/tests/test_snippet_extraction.py` — tests AI extraction pipeline with mocked AI
- Uses `asyncio.get_event_loop().run_until_complete()` for async service methods
- Verifies DB records created correctly after pipeline execution

**E2E Tests:**
- Not present — no Playwright, Cypress, or similar framework

**Frontend Tests:**
- Not present — no test files, no vitest/jest config detected

## Common Patterns

**API Endpoint Testing:**
```python
def test_create_project_valid(self, client, mock_auth_headers):
    response = client.post(
        "/api/projects/",
        json={"title": "Test Project", "framework": "three_act"},
        headers=mock_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Project"
```

**Validation Error Testing:**
```python
def test_create_project_invalid_title(self, client, mock_auth_headers):
    response = client.post(
        "/api/projects/",
        json={"title": "", "framework": "three_act"},
        headers=mock_auth_headers
    )
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert any("title" in error["field"] for error in errors)
```

**Exception Testing (unit):**
```python
def test_validate_project_title(self):
    with pytest.raises(HTTPException) as exc:
        validate_project_title("")
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail
```

**Soft Delete Testing:**
```python
def test_delete_snippet_soft(self, client, db_session, mock_auth_headers):
    # Delete via API
    resp = client.delete(f"/api/books/{book.id}/snippets/{chunk.id}", headers=mock_auth_headers)
    assert resp.status_code == 200

    # Verify is_deleted flag in DB
    db_session.refresh(chunk)
    assert chunk.is_deleted is True

    # Verify absent from list endpoint
    list_resp = client.get(f"/api/books/{book.id}/snippets", headers=mock_auth_headers)
    ids_in_list = [item["id"] for item in list_resp.json()["items"]]
    assert str(chunk.id) not in ids_in_list
```

**Atomic Rollback Testing:**
```python
def test_edit_snippet_atomic_rollback(self, db_session, mock_auth_headers):
    """If embed fails, DB content must be unchanged."""
    # ... setup ...
    with patch("...embed_text", side_effect=RuntimeError("fail")):
        with TestClient(app, raise_server_exceptions=False) as rollback_client:
            resp = rollback_client.patch(...)
    assert resp.status_code >= 500
    db_session.expire(chunk)
    db_session.refresh(chunk)
    assert chunk.content == original_content
```

**Async Service Testing:**
```python
raw_snippets = asyncio.get_event_loop().run_until_complete(
    service.extract_snippets(
        chapter_text="...",
        chapter_title="Chapter 1",
        book_title="Test Book",
        concepts=fake_concepts,
    )
)
assert len(raw_snippets) >= 1
```

## Test Inventory

| File | Classes | Test Count | Focus |
|------|---------|------------|-------|
| `backend/app/tests/test_api.py` | `TestProjectsAPI`, `TestSectionsAPI`, `TestReviewAPI`, `TestAuthAPI`, `TestMiddleware` | ~11 | Core API endpoints, validation, middleware |
| `backend/app/tests/test_validators.py` | `TestValidators` | ~7 | Standalone validator functions |
| `backend/app/tests/test_snippets_api.py` | `TestSnippetsAPI`, `TestRetryBook` | ~7 | Phase 1 snippet CRUD on BookChunks |
| `backend/app/tests/test_snippet_manager.py` | `TestSnippetAPI` | ~4 | Phase 2 snippet CRUD on Snippet entity |
| `backend/app/tests/test_snippet_extraction.py` | `TestSnippetExtraction` | ~2 | AI extraction pipeline |

## Key Test Conventions

1. **Always pass `mock_auth_headers`** for authenticated endpoints — value is `{"Authorization": "Bearer mock-token"}`
2. **Use `mock_embed` fixture** for any test that triggers embedding (snippet create/edit)
3. **Verify DB state after mutations** — call `db_session.refresh(obj)` then assert field values
4. **Use `raise_server_exceptions=False`** on TestClient when testing that 5xx errors are returned gracefully
5. **Requirement traceability** — docstrings reference ticket IDs like `BROW-01`, `EDIT-02`, `CUST-03`, `EXTR-01`
6. **Helper methods prefixed with `_`** on test classes for creating test data — `_make_book()`, `_make_chunk()`, `_make_snippet()`
7. **Mock user ID is stable** — `uuid.UUID("12345678-1234-5678-1234-567812345678")` matches `MockAuthService`

---

*Testing analysis: 2026-03-06*
