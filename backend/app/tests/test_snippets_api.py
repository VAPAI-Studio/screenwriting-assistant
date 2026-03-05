"""
Snippet API tests — Phase 1 (BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03)

Run: pytest app/tests/test_snippets_api.py -v
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.models.database import Book, BookChunk, BookStatus

# The mock auth user ID — matches MockAuthService.get_current_user()
MOCK_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestSnippetsAPI:
    """Tests for GET/PATCH/DELETE/POST /api/books/{book_id}/snippets"""

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
        book = self._make_book(db_session)
        self._make_chunk(db_session, book, index=0)
        self._make_chunk(db_session, book, index=1)

        resp = client.get(
            f"/api/books/{book.id}/snippets?page=1&per_page=50",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert "pages" in data
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["per_page"] == 50
        assert len(data["items"]) == 2

    def test_edit_snippet_persists(self, client, db_session, mock_auth_headers, mock_embed):
        """EDIT-01: PATCH updates content in DB."""
        book = self._make_book(db_session)
        chunk = self._make_chunk(db_session, book, index=0)

        resp = client.patch(
            f"/api/books/{book.id}/snippets/{chunk.id}",
            json={"content": "Updated content for the snippet"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Updated content for the snippet"

        # Verify DB was actually updated
        db_session.refresh(chunk)
        assert chunk.content == "Updated content for the snippet"

    def test_edit_snippet_atomic_rollback(self, client, db_session, mock_auth_headers):
        """EDIT-02: If embed fails, DB content must be unchanged."""
        book = self._make_book(db_session)
        chunk = self._make_chunk(db_session, book, index=0)
        original_content = chunk.content

        with patch(
            "app.services.embedding_service.embedding_service.embed_text",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Embedding service unavailable"),
        ):
            resp = client.patch(
                f"/api/books/{book.id}/snippets/{chunk.id}",
                json={"content": "New content that should not persist"},
                headers=mock_auth_headers,
            )

        # Should return 5xx because embed raised
        assert resp.status_code >= 500

        # DB content must be unchanged — re-query from DB
        db_session.expire(chunk)
        db_session.refresh(chunk)
        assert chunk.content == original_content

    def test_delete_snippet_soft(self, client, db_session, mock_auth_headers):
        """EDIT-04: DELETE soft-deletes; chunk absent from list."""
        book = self._make_book(db_session)
        chunk = self._make_chunk(db_session, book, index=0)

        # Delete the snippet
        resp = client.delete(
            f"/api/books/{book.id}/snippets/{chunk.id}",
            headers=mock_auth_headers,
        )
        assert resp.status_code == 200

        # Verify is_deleted flag set in DB
        db_session.refresh(chunk)
        assert chunk.is_deleted is True

        # Verify absent from list
        list_resp = client.get(
            f"/api/books/{book.id}/snippets",
            headers=mock_auth_headers,
        )
        assert list_resp.status_code == 200
        ids_in_list = [item["id"] for item in list_resp.json()["items"]]
        assert str(chunk.id) not in ids_in_list

    def test_create_custom_snippet(self, client, db_session, mock_auth_headers, mock_embed):
        """CUST-01: POST creates snippet with is_user_created=True."""
        book = self._make_book(db_session)

        resp = client.post(
            f"/api/books/{book.id}/snippets",
            json={
                "content": "A brand new user-created snippet",
                "chapter_title": "Chapter One",
                "page_number": 1,
            },
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_user_created"] is True
        assert data["content"] == "A brand new user-created snippet"
        assert data["chapter_title"] == "Chapter One"
        assert data["page_number"] == 1

    def test_create_snippet_has_embedding(self, client, db_session, mock_auth_headers, mock_embed):
        """CUST-03: POST stores embedding."""
        book = self._make_book(db_session)

        resp = client.post(
            f"/api/books/{book.id}/snippets",
            json={"content": "Snippet with embedding"},
            headers=mock_auth_headers,
        )
        assert resp.status_code == 201

        # Verify embedding was called (mock_embed is an AsyncMock)
        mock_embed.assert_called_once()

        # Verify chunk in DB has an embedding (non-None)
        chunk_id = resp.json()["id"]
        from app.models.database import BookChunk
        chunk = db_session.query(BookChunk).filter(BookChunk.id == chunk_id).first()
        assert chunk is not None
        assert chunk.embedding is not None


class TestRetryBook:
    """Tests for retry_book() safety (CUST-02)."""

    def test_retry_preserves_user_chunks(self, db_session):
        """CUST-02: retry_book() must not delete is_user_created=True chunks."""
        from app.models.database import Book, BookChunk, BookStatus
        from app.services.book_processing_service import retry_book

        # Create a book with both system and user chunks
        book = Book(
            id=uuid.uuid4(),
            owner_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            title="Test Book",
            filename="test.pdf",
            file_type="pdf",
            status=BookStatus.COMPLETED,
        )
        db_session.add(book)
        db_session.commit()

        system_chunk = BookChunk(
            id=uuid.uuid4(),
            book_id=book.id,
            chunk_index=0,
            content="System chunk",
            token_count=5,
            is_user_created=False,
            is_deleted=False,
        )
        user_chunk = BookChunk(
            id=uuid.uuid4(),
            book_id=book.id,
            chunk_index=1,
            content="User chunk",
            token_count=5,
            is_user_created=True,
            is_deleted=False,
        )
        db_session.add(system_chunk)
        db_session.add(user_chunk)
        db_session.commit()

        user_chunk_id = user_chunk.id

        # retry_book() is expected to reset book for reprocessing
        # but must NOT delete user-created chunks
        retry_book(book.id, db_session)

        # User chunk must still exist and not be deleted
        surviving = db_session.query(BookChunk).filter(
            BookChunk.id == user_chunk_id
        ).first()
        assert surviving is not None
        assert surviving.is_deleted is False
