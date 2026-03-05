"""
Snippet API tests — Phase 1 (BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03)

These stubs are RED until Plan 03 implements the snippets router.
Run: pytest app/tests/test_snippets_api.py -v
"""
import uuid
import pytest

from app.models.database import Book, BookChunk, BookStatus


class TestSnippetsAPI:
    """Tests for GET/PATCH/DELETE/POST /api/books/{book_id}/snippets"""

    def _make_book(self, db_session):
        """Helper: create a completed book fixture."""
        book = Book(
            id=uuid.uuid4(),
            owner_id=uuid.uuid4(),
            title="Test Book",
            filename="test.pdf",
            file_type="pdf",
            status=BookStatus.COMPLETED,
        )
        db_session.add(book)
        db_session.commit()
        return book

    def _make_chunk(self, db_session, book, index=0, is_user_created=False):
        """Helper: create a BookChunk fixture (no embedding — SQLite cannot store vectors)."""
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

    def test_list_snippets_paginated(self, client, db_session, mock_auth_headers):
        """BROW-01: GET /api/books/{id}/snippets returns paginated list."""
        pytest.fail("not implemented — waiting for Plan 03 snippets router")

    def test_edit_snippet_persists(self, client, db_session, mock_auth_headers, mock_embed):
        """EDIT-01: PATCH updates content in DB."""
        pytest.fail("not implemented — waiting for Plan 03 snippets router")

    def test_edit_snippet_atomic_rollback(self, client, db_session, mock_auth_headers):
        """EDIT-02: If embed fails, DB content must be unchanged."""
        pytest.fail("not implemented — waiting for Plan 03 snippets router")

    def test_delete_snippet_soft(self, client, db_session, mock_auth_headers):
        """EDIT-04: DELETE soft-deletes; chunk absent from list."""
        pytest.fail("not implemented — waiting for Plan 03 snippets router")

    def test_create_custom_snippet(self, client, db_session, mock_auth_headers, mock_embed):
        """CUST-01: POST creates snippet with is_user_created=True."""
        pytest.fail("not implemented — waiting for Plan 03 snippets router")

    def test_create_snippet_has_embedding(self, client, db_session, mock_auth_headers, mock_embed):
        """CUST-03: POST stores embedding."""
        pytest.fail("not implemented — waiting for Plan 03 snippets router")


class TestRetryBook:
    """Tests for retry_book() safety (CUST-02)."""

    def test_retry_preserves_user_chunks(self, db_session):
        """CUST-02: retry_book() must not delete is_user_created=True chunks."""
        pytest.fail("not implemented — waiting for Plan 02 retry_book fix")
