import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String, Enum as SAEnum
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base
from app.main import app
from app.db import get_db

SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"


def _patch_uuid_columns_for_sqlite():
    """Patch PostgreSQL UUID columns and Enum columns to work with SQLite."""
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    # Tell sqlite3 how to adapt Python UUID objects to strings
    sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, PG_UUID):
                column.type = String(36)
                if column.default is not None and column.default.arg is uuid.uuid4:
                    column.default.arg = lambda: str(uuid.uuid4())
            elif isinstance(column.type, SAEnum):
                # SQLite doesn't support native enums; use String instead
                column.type = String(50)


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine (SQLite in-memory)."""
    _patch_uuid_columns_for_sqlite()
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

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

@pytest.fixture
def mock_auth_headers():
    """Return headers with mock authentication token."""
    return {"Authorization": "Bearer mock-token"}
