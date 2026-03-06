"""
Snippet extraction pipeline tests — Phase 2 (EXTR-01, EXTR-02)
Tests that process_chapter() creates Snippet records with embeddings and concept_ids.
Run: pytest app/tests/test_snippet_extraction.py -v
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.models.database import Book, BookStatus

# The mock auth user ID — matches MockAuthService.get_current_user()
MOCK_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


class TestSnippetExtraction:
    """Tests for the AI snippet extraction pipeline (Phase 2)."""

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

    def test_extract_snippets_creates_records(self, db_session, mock_embed):
        """EXTR-01: process_chapter() triggers snippet extraction and stores Snippet records in DB"""
        pytest.fail("stub — implement in Plan 02")

    def test_snippets_have_embeddings_and_concept_ids(self, db_session, mock_embed):
        """EXTR-02: Snippet records created during extraction have non-null embedding and non-empty concept_ids"""
        pytest.fail("stub — implement in Plan 02")
