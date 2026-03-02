# Testing Patterns

**Analysis Date:** 2026-03-01

## Test Framework

**Runner:**
- Backend: pytest 8.0.2
- Config: `backend/pytest.ini`
  ```ini
  [pytest]
  testpaths = app/tests
  pythonpath = .
  asyncio_mode = auto
  ```

**Assertion Library:**
- Backend: pytest's built-in assertions (via `assert` statements)
- Frontend: No test framework detected (no jest.config, vitest.config found)

**Run Commands:**

Backend:
```bash
cd backend
source venv/bin/activate

pytest app/tests/test_api.py              # Run all API tests
pytest app/tests/test_validators.py       # Run validator tests
pytest app/tests/test_api.py::TestProjectsAPI::test_create_project_valid  # Single test
```

Frontend:
- No test runner configured
- Linting only: `npm run lint` (ESLint)

## Test File Organization

**Location:**
- Backend: `backend/app/tests/` - tests live alongside source code
- Test files: `test_api.py`, `test_validators.py`

**Naming:**
- Pattern: `test_*.py` (pytest discovery)
- Class-based grouping: `class TestProjectsAPI:`, `class TestSectionsAPI:`, `class TestValidators:`

**Structure:**
```
backend/app/tests/
├── conftest.py          # Shared fixtures and pytest configuration
├── __init__.py
├── test_api.py          # API endpoint tests (organized by class)
└── test_validators.py   # Validation function tests (organized by class)
```

## Test Structure

**Suite Organization:**

Classes group related tests:
```python
class TestProjectsAPI:
    """Test projects API endpoints"""

    def test_create_project_valid(self, client, mock_auth_headers):
        """Test creating a project with valid data"""

class TestSectionsAPI:
    """Test sections API endpoints"""

    def test_update_section_content_validation(self, client, mock_auth_headers):
        """Test updating section content with validation"""
```

**Patterns:**

Setup via conftest.py fixtures:
```python
@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine (SQLite in-memory)."""
    _patch_uuid_columns_for_sqlite()  # Handle PostgreSQL types for SQLite
    engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, ...)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

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

Teardown: Fixtures handle rollback and cleanup automatically

Mock auth via fixture:
```python
@pytest.fixture
def mock_auth_headers():
    """Return headers with mock authentication token."""
    return {"Authorization": "Bearer mock-token"}
```

## Mocking

**Framework:** pytest's built-in dependency injection via `monkeypatch` or FastAPI's `app.dependency_overrides`

**Patterns:**

Database mocking:
```python
# In conftest.py: Override get_db with test session
def override_get_db():
    try:
        yield db_session
    finally:
        pass

app.dependency_overrides[get_db] = override_get_db
```

Auth mocking:
```python
# Tests use mock token header
response = client.post(
    "/api/projects/",
    json={"title": "Test Project", "framework": "three_act"},
    headers=mock_auth_headers  # {"Authorization": "Bearer mock-token"}
)
```

SQLite for PostgreSQL types:
```python
def _patch_uuid_columns_for_sqlite():
    """Patch PostgreSQL UUID columns and Enum columns to work with SQLite."""
    sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_UUID):
                column.type = String(36)
            elif isinstance(column.type, SAEnum):
                column.type = String(50)  # SQLite doesn't support native enums
```

**What to Mock:**
- Database: Override `get_db` dependency
- Authentication: Use mock token in headers
- External services: Not yet mocked (no OpenAI mocking pattern observed)

**What NOT to Mock:**
- Validators: Test actual validation logic (test_validators.py tests real validators)
- Business logic: Test actual FastAPI endpoints via TestClient
- Schema serialization: Test real Pydantic model behavior

## Fixtures and Factories

**Test Data:**

Test data is created inline in test methods:
```python
def test_create_project_valid(self, client, mock_auth_headers):
    response = client.post(
        "/api/projects/",
        json={
            "title": "Test Project",
            "framework": "three_act"
        },
        headers=mock_auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Project"
    assert data["framework"] == "three_act"
```

Boundary testing with hardcoded edge cases:
```python
def test_create_project_invalid_title(self, client, mock_auth_headers):
    # Empty title
    response = client.post(..., json={"title": "", "framework": "three_act"}, ...)
    assert response.status_code == 422

    # Title too short
    response = client.post(..., json={"title": "A", "framework": "three_act"}, ...)
    assert response.status_code == 422

    # Title too long
    response = client.post(..., json={"title": "A" * 256, "framework": "three_act"}, ...)
    assert response.status_code == 422
```

**Location:**
- All fixtures live in `backend/app/tests/conftest.py`
- Test data created per-test (no factory pattern)

## Coverage

**Requirements:** No coverage enforcement detected

**View Coverage:**
```bash
cd backend
source venv/bin/activate
pytest --cov=app app/tests/  # Run tests with coverage report
```

Coverage dependencies present (`pytest-cov==4.1.0`) but not enforced via configuration.

## Test Types

**Unit Tests:**
- Scope: Individual validator functions
- Approach: Test pure functions in isolation
- Example from `test_validators.py`:
  ```python
  def test_validate_email(self):
      """Test email validation"""
      assert validate_email("user@example.com") is True
      assert validate_email("invalid.email") is False
  ```

**Integration Tests:**
- Scope: API endpoints with database
- Approach: Full request/response cycle via TestClient
- Example from `test_api.py`:
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
      # Verifies: validation, DB write, serialization, HTTP response
  ```

**E2E Tests:**
- Framework: Not implemented
- Frontend has no automated test suite

## Common Patterns

**Testing Validation:**

Validators tested via HTTPException assertions:
```python
def test_validate_project_title(self):
    """Test project title validation"""
    # Valid
    validate_project_title("My Project")  # Should not raise

    # Invalid - empty
    with pytest.raises(HTTPException) as exc:
        validate_project_title("")
    assert exc.value.status_code == 400
    assert "empty" in exc.value.detail

    # Invalid - too short
    with pytest.raises(HTTPException) as exc:
        validate_project_title("A")
    assert exc.value.status_code == 400
    assert "at least 2 characters" in exc.value.detail

    # Invalid - too long
    with pytest.raises(HTTPException) as exc:
        validate_project_title("A" * 256)
    assert exc.value.status_code == 400
    assert "exceed 255 characters" in exc.value.detail
```

API validation tested via response status/error codes:
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

**Error Testing:**

Expected error responses verified:
```python
def test_review_validation(self, client, mock_auth_headers):
    # Test with text too short
    response = client.post(
        "/api/review/",
        json={
            "section_id": "12345678-1234-5678-1234-567812345678",
            "text": "Too short",
            "framework": "three_act"
        },
        headers=mock_auth_headers
    )
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert any("text" in error["field"] for error in errors)
```

**Testing Request Size Limits:**
```python
def test_request_size_limit(self, client, mock_auth_headers):
    large_content = "A" * (11 * 1024 * 1024)  # 11MB, exceeding 10MB limit
    response = client.post(
        "/api/projects/",
        json={
            "title": "Large Project",
            "framework": "three_act",
            "large_field": large_content
        },
        headers=mock_auth_headers
    )
    # Should fail with 413 Payload Too Large or similar
```

**Testing Data Truncation:**
```python
def test_validate_section_content(self):
    # Content exceeding max length (MAX_SECTION_LENGTH = 1500)
    long_content = "A" * 2000
    result = validate_section_content(long_content)
    assert len(result) == 1503  # 1500 + "..."
    assert result.endswith("...")
```

---

*Testing analysis: 2026-03-01*
