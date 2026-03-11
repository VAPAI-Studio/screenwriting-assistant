# Testing Patterns

**Analysis Date:** 2026-03-11

## Test Framework

**Runner:**
- pytest v8.0.2
- Config: `backend/pytest.ini`
- Key settings: `testpaths = app/tests`, `pythonpath = .`, `asyncio_mode = auto`

**Assertion Library:**
- pytest built-in assertions (e.g., `assert response.status_code == 200`)

**Run Commands:**
```bash
pytest app/tests/                                     # Run all tests
pytest app/tests/test_api.py -v                       # Run specific test file with verbose output
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid  # Single test
```

**Additional Testing Libraries:**
- `pytest-asyncio==0.23.5` — async/await test support
- `pytest-cov==4.1.0` — code coverage
- `httpx>=0.25.0,<0.28.0` — FastAPI TestClient backend
- `unittest.mock` — mocking (AsyncMock, patch)

## Test File Organization

**Location:**
- Backend: `backend/app/tests/` (co-located with source)
- Test files are sibling to source code, not in separate `tests/` directory
- Frontend: No test files detected in codebase

**Naming:**
- Pattern: `test_*.py` prefix (e.g., `test_api.py`, `test_validators.py`, `test_snippet_manager.py`)
- Descriptive names indicating test scope

**Structure (Backend):**
```
backend/app/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_api.py              # API endpoint tests
├── test_validators.py       # Validator function tests
├── test_snippets_api.py     # Snippet API tests (Phase 1)
├── test_snippet_manager.py  # Snippet manager tests (Phase 2)
└── test_snippet_extraction.py # Document processing tests
```

## Test Structure

**Suite Organization (from `backend/app/tests/test_api.py`):**
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

class TestSectionsAPI:
    """Test sections API endpoints"""

    def test_update_section_content_validation(self, client, mock_auth_headers):
        """Test updating section content with validation"""
        ...
```

**Patterns:**
- Test classes group related tests (one class per API resource or feature)
- Test methods start with `test_` and are descriptive: `test_{action}_{scenario}`
- Docstrings explain what is being tested
- Fixtures passed as method parameters

## Mocking

**Framework:** `unittest.mock` (from Python standard library)

**Patterns from `backend/app/tests/conftest.py`:**
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

**What to Mock:**
- External API calls (OpenAI, Anthropic) — use `AsyncMock` for async functions
- File I/O operations
- Time-dependent functions
- Database calls — overridden via dependency injection instead

**What NOT to Mock:**
- Database queries — use in-memory SQLite fixture (`test_engine`)
- Validation functions — test them directly
- Framework code (FastAPI, SQLAlchemy ORM)

**Mocking Pattern in Tests (from `test_snippets_api.py`):**
```python
def test_edit_snippet_atomic_rollback(self, db_session, mock_auth_headers):
    """If embed fails, DB content must be unchanged."""
    # Use mock_embed fixture to prevent actual API calls
    # Verify that exception is raised and DB rolled back
```

## Fixtures and Factories

**Test Data (from `backend/app/tests/conftest.py`):**

**Database fixtures:**
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

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test."""
    TestSessionLocal = sessionmaker(...)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
```

**API client fixture:**
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

**Auth fixture:**
```python
@pytest.fixture
def mock_auth_headers():
    """Return headers with mock authentication token."""
    return {"Authorization": "Bearer mock-token"}
```

**Helper Factories (from `test_snippet_manager.py`):**
```python
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

def _make_snippet(self, db_session, book, **kwargs):
    """Helper: create a Snippet record for a given book."""
    defaults = dict(
        id=uuid.uuid4(),
        book_id=str(book.id),
        content="test content",
        token_count=42,
    )
    defaults.update(kwargs)
    snippet = Snippet(**defaults)
    db_session.add(snippet)
    db_session.commit()
    return snippet
```

**Location:** Helper methods defined in test class itself (underscore-prefixed)

## Coverage

**Requirements:** No coverage threshold enforced (not configured in `pytest.ini`)

**View Coverage:**
```bash
pytest --cov=app app/tests/  # Generate coverage report
```

**Tools:**
- `pytest-cov==4.1.0` provides coverage plugin

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods (validators, service helpers)
- Approach: Direct function calls, minimal fixtures
- Example from `test_validators.py`:
```python
def test_validate_email(self):
    """Test email validation"""
    assert validate_email("user@example.com") is True
    assert validate_email("invalid.email") is False
```

**Integration Tests:**
- Scope: Full API endpoints with database interactions
- Approach: Use TestClient with overridden dependency injection, in-memory SQLite database
- Example from `test_api.py`:
```python
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
```

**E2E Tests:**
- Status: Not detected in codebase
- Frontend testing infrastructure not set up (no test files, no jest/vitest config)

## Common Patterns

**Async Testing:**
- `pytest-asyncio` automatically detects async test functions
- No special decorator needed (asyncio_mode = auto in pytest.ini)
- Example from `test_snippets_api.py`:
```python
def test_edit_snippet_persists(self, client, db_session, mock_auth_headers, mock_embed):
    """EDIT-01: PATCH updates content in DB."""
    book = self._make_book(db_session)
    chunk = self._make_chunk(db_session, book, index=0)

    # AsyncMock fixture handles embedding call
    resp = client.patch(
        f"/api/books/{book.id}/snippets/{chunk.id}",
        json={"content": "Updated content"},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 200
```

**Error Testing:**
```python
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

**Validation Testing (from `test_validators.py`):**
```python
def test_validate_project_title(self):
    """Test project title validation"""
    # Valid titles
    validate_project_title("My Project")
    validate_project_title("A" * 255)

    # Invalid titles
    with pytest.raises(HTTPException) as exc:
        validate_project_title("")
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail
```

**State Verification:**
```python
def test_edit_snippet_persists(self, client, db_session, mock_auth_headers, mock_embed):
    """Verify database state after operation."""
    # Setup
    book = self._make_book(db_session)
    chunk = self._make_chunk(db_session, book, index=0)

    # Operation
    resp = client.patch(...)
    assert resp.status_code == 200

    # Verify state
    db_session.refresh(chunk)
    assert chunk.content == "Updated content for the snippet"
```

**Special Test Setup for PostgreSQL Features:**

From `conftest.py` — Tests run on SQLite but need to handle PostgreSQL-specific features:
```python
def _patch_uuid_columns_for_sqlite():
    """Patch PostgreSQL UUID columns, Enum columns, and SafeVector columns to work with SQLite."""
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_UUID):
                column.type = String(36)
            elif isinstance(column.type, SAEnum):
                column.type = String(50)
            elif isinstance(column.type, SafeVector):
                column.type = VectorAsText()
```

## Test Coverage Gaps

**Frontend:**
- No test files present
- No test runner configured (no jest/vitest config)
- React components, hooks, API client untested

**Backend:**
- Middleware tests exist but are incomplete (e.g., `test_rate_limiting()` is a stub)
- Service layer tests minimal (only `openai_service` implicitly tested via endpoint tests)
- Edge cases in complex services (document processing, RAG, embedding) not fully covered

## Best Practices Observed

1. **Isolation:** Each test gets a fresh database session (scope="function")
2. **Clarity:** Descriptive test names and docstrings explain intent
3. **Fixtures:** Common setup (auth, DB) centralized in conftest.py
4. **Dependency Injection:** Database dependency overridden via FastAPI's `dependency_overrides`
5. **SQLite for Testing:** In-memory database for speed and isolation
6. **Mock External Services:** OpenAI calls mocked to avoid API costs and network flakiness

---

*Testing analysis: 2026-03-11*
