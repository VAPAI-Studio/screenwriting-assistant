# Testing Patterns

**Analysis Date:** 2025-03-05

## Test Framework

**Runner:**
- Backend: pytest 8.0.2
- Config: `backend/pytest.ini`
  - testpaths: `app/tests`
  - pythonpath: `.`
  - asyncio_mode: `auto` (for async test support)
- Frontend: No test framework currently configured (ESLint only)

**Assertion Library:**
- Backend: pytest's built-in assertions (no additional library needed)
- Frontend: Not applicable (no tests present)

**Run Commands:**
```bash
# Backend: Run all tests
cd backend && pytest

# Backend: Run specific test class
pytest app/tests/test_api.py::TestProjectsAPI

# Backend: Run single test
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid

# Backend: Run with coverage
pytest --cov=app app/tests/

# Frontend: Only linting available
npm run lint

# Frontend: Type checking
tsc --noEmit
```

## Test File Organization

**Location:**
- Backend: Tests co-located in `backend/app/tests/` directory (separate from source)
- Pattern: `test_*.py` files in `app/tests/` alongside `app/` source

**Naming:**
- Backend test files: `test_api.py`, `test_validators.py`
- Backend test classes: `TestProjectsAPI`, `TestSectionsAPI`, `TestValidators` (CamelCase with Test prefix)
- Backend test methods: `test_create_project_valid()`, `test_validate_email()` (snake_case with test_ prefix)
- Frontend: No test files present

**Structure:**
```
backend/
├── app/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py           # Fixtures and setup
│   │   ├── test_api.py           # API endpoint tests
│   │   └── test_validators.py    # Validator function tests
│   ├── models/
│   ├── services/
│   └── ...
```

## Test Structure

**Suite Organization:**

From `backend/app/tests/test_api.py`:
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
```

From `backend/app/tests/test_validators.py`:
```python
class TestValidators:
    """Test validation functions"""

    def test_validate_email(self):
        """Test email validation"""
        # Valid emails
        assert validate_email("user@example.com") is True
        assert validate_email("user.name+tag@example.co.uk") is True

        # Invalid emails
        assert validate_email("invalid.email") is False
```

**Patterns:**
- Setup: Fixture-based with pytest decorators (@pytest.fixture)
- One logical test per method (single assertion concept, though may have multiple asserts)
- Docstrings describe test purpose clearly
- Error path testing (e.g., test invalid input alongside valid input)
- HTTP status codes tested for all paths (200, 400, 404, 422, etc.)

## Mocking

**Framework:**
- Backend: No explicit mocking library used (pytest-mock not in requirements)
- Instead: Dependency injection override for database sessions and auth
- Manual mocking for auth tokens via `mock_auth_headers` fixture

**Patterns:**

Database mocking via `conftest.py`:
```python
@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a fresh database session for each test."""
    TestSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

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

Auth mocking:
```python
@pytest.fixture
def mock_auth_headers():
    """Return headers with mock authentication token."""
    return {"Authorization": "Bearer mock-token"}
```

Usage in tests:
```python
def test_create_project_valid(self, client, mock_auth_headers):
    response = client.post(
        "/api/projects/",
        json={"title": "Test Project", "framework": "three_act"},
        headers=mock_auth_headers
    )
    assert response.status_code == 200
```

**What to Mock:**
- Database: Yes (use in-memory SQLite via test engine)
- External APIs (OpenAI, Anthropic): Not tested (no mocking in current test suite)
- Authentication: Yes (use `mock-token` in development/tests)
- File I/O: Not tested (no test coverage)

**What NOT to Mock:**
- Request/response parsing (test actual Pydantic validation)
- Middleware behavior (test actual SecurityMiddleware, RateLimitMiddleware)
- Business logic in validators (test actual validation functions)

## Fixtures and Factories

**Test Data:**

From `conftest.py`:
```python
def _patch_uuid_columns_for_sqlite():
    """Patch PostgreSQL UUID columns and Enum columns to work with SQLite."""
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_UUID):
                column.type = String(36)
```

Test data passed inline in test methods:
```python
def test_create_project_valid(self, client, mock_auth_headers):
    response = client.post(
        "/api/projects/",
        json={"title": "Test Project", "framework": "three_act"},
        headers=mock_auth_headers
    )
```

No separate fixture factories or builders observed. All test data created directly in test methods.

**Location:**
- `backend/app/tests/conftest.py` for shared fixtures and setup
- Inline JSON test data within test methods
- SQLite in-memory database as fixture (`test_engine`)

## Coverage

**Requirements:** Not explicitly enforced

**View Coverage:**
```bash
cd backend
pytest --cov=app --cov-report=html app/tests/
# Opens coverage report in htmlcov/index.html
```

**Coverage Gaps:**
- Frontend: No test framework—0% coverage
- Backend: Partial coverage
  - API endpoint tests present: `test_api.py`
  - Validation tests present: `test_validators.py`
  - Service tests: None observed
  - Middleware tests: Stubs only (`test_rate_limiting`, `test_request_size_limit`)
  - Database model tests: None
  - Auth service tests: None (no .verify_token() tests)

## Test Types

**Unit Tests:**
- Scope: Individual validator functions, model validation
- Approach: Direct function calls with different inputs
- Examples: `test_validate_email()`, `test_validate_project_title()`

From `test_validators.py`:
```python
def test_validate_password(self):
    """Test password validation"""
    # Valid password
    validate_password("StrongPass123")  # Should not raise

    # Too short
    with pytest.raises(HTTPException) as exc:
        validate_password("Short1")
    assert exc.value.status_code == 400
    assert "at least 8 characters" in exc.value.detail
```

**Integration Tests:**
- Scope: Full API request/response cycle with test database
- Approach: Use TestClient to make HTTP requests, check status codes and response data
- Examples: `test_create_project_valid()`, `test_update_project_validation()`

From `test_api.py`:
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
    assert data["framework"] == "three_act"
```

**E2E Tests:**
- Framework: Not used
- Status: No end-to-end tests present

## Common Patterns

**Async Testing:**

Pytest async support configured via `asyncio_mode = auto` in `pytest.ini`.

No explicit async test examples in current test suite, but the configuration allows:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

**Error Testing:**

Exception testing with pytest.raises():
```python
def test_validate_project_title(self):
    """Test project title validation"""
    # Empty title
    with pytest.raises(HTTPException) as exc:
        validate_project_title("")
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail
```

HTTP response error testing:
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

**Validation Testing:**

Comprehensive validation of field constraints:
```python
def test_validate_section_content(self):
    """Test section content validation"""
    # Normal content
    assert validate_section_content("Some content") == "Some content"

    # Empty content
    assert validate_section_content("") == ""

    # Content exceeding max length
    long_content = "A" * 2000
    result = validate_section_content(long_content)
    assert len(result) == 1503  # 1500 + "..."
    assert result.endswith("...")
```

**Middleware Testing:**

Test structure exists but implementations are stubs:
```python
class TestMiddleware:
    """Test custom middleware"""

    def test_rate_limiting(self, client):
        """Test rate limiting middleware"""
        # Note: This test would need to be configured based on the rate limit settings
        pass

    def test_security_headers(self, client):
        """Test security headers middleware"""
        response = client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
```

## Test Database Setup

**SQLite In-Memory:**

From `conftest.py`:
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

PostgreSQL UUID/Enum translation:
- UUID columns converted to String(36) for SQLite
- Enum columns converted to String(50) for SQLite
- Type conversions happen automatically via SQLAlchemy type processors

**Test Isolation:**
- Session-scoped engine (created once per test session)
- Function-scoped sessions (fresh per test)
- Session rollback after each test (no commit)
- Dependencies overridden per test (`app.dependency_overrides`)

---

*Testing analysis: 2025-03-05*
