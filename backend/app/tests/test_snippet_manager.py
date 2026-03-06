"""
Snippet Manager API tests — Phase 2 (BROW-02, BROW-03, EDIT-03, EXTR-03)
Tests the /api/snippets router which operates on the Snippet table (NOT BookChunks).
Run: pytest app/tests/test_snippet_manager.py -v
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.models.database import Book, BookStatus

# The mock auth user ID — matches MockAuthService.get_current_user()
MOCK_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestSnippetAPI:
    """Tests for /api/snippets router (Snippet entity, Phase 2)."""

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

    def test_list_snippets_includes_metadata(self, client, db_session, mock_auth_headers):
        """BROW-02: GET /api/snippets?book_id={id} returns items with chapter_title, page_number, token_count"""
        pytest.fail("stub — implement in Plan 03")

    def test_list_snippets_includes_concept_names(self, client, db_session, mock_auth_headers):
        """BROW-03: GET /api/snippets?book_id={id} returns items with concept_names list"""
        pytest.fail("stub — implement in Plan 03")

    def test_edit_snippet_atomic_rollback(self, client, db_session, mock_auth_headers, mock_embed):
        """EDIT-03: PATCH /api/snippets/{id} with failing embed returns 5xx and does not mutate DB"""
        pytest.fail("stub — implement in Plan 03")

    def test_no_create_endpoint(self, client, db_session, mock_auth_headers):
        """EXTR-03: POST /api/snippets returns 404 or 405 — no user-facing creation allowed"""
        pytest.fail("stub — implement in Plan 03")
