# Architecture Patterns: Snippet Manager

**Domain:** Snippet/chunk management layer for RAG-based screenwriting assistant
**Researched:** 2026-03-05
**Confidence:** HIGH (grounded in direct codebase analysis)

## Design Philosophy: Extend BookChunk, Don't Replace It

The existing `BookChunk` model is the foundation of the RAG pipeline. Rather than creating a parallel "Snippet" table, extend `BookChunk` in-place with new columns. This preserves every existing relationship (Book → BookChunk, RAG queries, concept_ids linkage) without migration risk.

**Exception:** Annotations belong in their own table because a snippet can have zero or many annotations, and they have independent lifecycle.

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `BookChunk` (extended) | Stores chunk text, embedding, weight, custom flag, soft-delete, display order | RAG service, Snippet API, Book processing pipeline |
| `SnippetAnnotation` (new) | User notes attached to a specific chunk | Snippet API, RAG service (injected into context) |
| `SnippetService` (new) | CRUD ops, re-embedding orchestration, reorder logic | Embedding service, BookChunk, SnippetAnnotation |
| `RAGService` (modified) | Respects weight multiplier, injects annotations into retrieved context | BookChunk, SnippetAnnotation, Embedding service |
| Snippet API endpoints (new) | REST interface for frontend snippet management | SnippetService, auth dependencies |
| Frontend Snippets page (new) | UI for browsing, editing, annotating, reordering snippets | Snippet API endpoints |

## Data Flow

**Viewing snippets for a book:**
```
GET /api/books/{book_id}/snippets
  → BookChunk WHERE book_id=X AND is_deleted=false ORDER BY display_order
  → JOIN SnippetAnnotation for each chunk
  → Return SnippetResponse[] with annotations (paginated)
```

**Editing a snippet:**
```
PATCH /api/snippets/{chunk_id}
  → Validate content length, trim whitespace
  → Update content, token_count (via tiktoken), updated_at
  → embed_text(new_content) → update embedding
  → All in one DB transaction (rollback if embed fails)
  → Return updated SnippetResponse
```

**Creating a custom snippet:**
```
POST /api/books/{book_id}/snippets
  → Validate content
  → Create BookChunk(is_user_created=True, chunk_index=NULL)
  → embed_text(content) → set embedding
  → display_order = MAX(display_order) + 1
  → Return SnippetResponse
```

**RAG retrieval with weights:**
```
rag_service.semantic_search()
  → Cosine similarity search (existing)
  → Filter: is_deleted=false
  → Score: adjusted_score = similarity * weight
  → Re-sort by adjusted_score
  → For chunks with annotations (include_in_context=True): append to context string
  → Return weighted, annotated results
```

## Database Schema Changes

### Strategy: Additive ALTER TABLE (no data loss)

All changes are additive. Existing rows get safe defaults. Book processing pipeline continues unchanged.

### BookChunk Extensions (Migration 006)

```sql
-- backend/migrations/006_snippet_management.sql

ALTER TABLE book_chunks
    ADD COLUMN IF NOT EXISTS is_user_created BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS weight FLOAT DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS display_order INTEGER,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- Backfill display_order from chunk_index
UPDATE book_chunks SET display_order = chunk_index WHERE display_order IS NULL;
ALTER TABLE book_chunks ALTER COLUMN display_order SET NOT NULL;
ALTER TABLE book_chunks ALTER COLUMN display_order SET DEFAULT 0;

-- Indexes for snippet listing and weighted RAG queries
CREATE INDEX IF NOT EXISTS idx_book_chunks_snippet_list
    ON book_chunks (book_id, is_deleted, display_order);
CREATE INDEX IF NOT EXISTS idx_book_chunks_weight
    ON book_chunks (book_id, is_deleted, weight);
```

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `is_user_created` | BOOLEAN | false | Protected from deletion during book reprocessing |
| `is_deleted` | BOOLEAN | false | Soft delete — excluded from RAG and UI |
| `weight` | FLOAT | 1.0 | RAG priority multiplier (range 0.1–5.0) |
| `display_order` | INTEGER | 0 | User-controlled UI ordering, independent of chunk_index |
| `updated_at` | TIMESTAMPTZ | NULL | NULL = never edited (original chunk) |

### SnippetAnnotation Table (New)

```sql
CREATE TABLE IF NOT EXISTS snippet_annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID NOT NULL REFERENCES book_chunks(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    include_in_context BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_snippet_annotations_chunk ON snippet_annotations(chunk_id);
```

Why separate table (not JSON column):
- One chunk can have multiple annotations
- `include_in_context` flag needs to be SQL-queryable for efficient RAG filtering
- Independent lifecycle (edit annotation without touching chunk content/embedding)

## API Endpoints

```
GET    /api/books/{book_id}/snippets           List (paginated, ?page=1&per_page=50)
POST   /api/books/{book_id}/snippets           Create custom snippet
PATCH  /api/snippets/{chunk_id}                Update content, weight, display_order
DELETE /api/snippets/{chunk_id}                Soft delete (sets is_deleted=True)
POST   /api/snippets/{chunk_id}/annotations    Add annotation
PATCH  /api/snippets/{chunk_id}/annotations/{annotation_id}   Update annotation
DELETE /api/snippets/{chunk_id}/annotations/{annotation_id}   Delete annotation
PATCH  /api/books/{book_id}/snippets/reorder   Bulk update display_order
```

Follows the same pattern as existing `/api/books/{book_id}` endpoints in `books.py`.

## RAG Service Modifications

There are **4 query touchpoints** in `rag_service.py` that need updating:

1. **`semantic_search()`** — primary retrieval method:
   - Add `AND is_deleted = false` to WHERE clause
   - Multiply similarity score by `weight`: `adjusted_score = 1 - (embedding <=> query_embedding) * weight`
   - Re-sort results by `adjusted_score DESC`

2. **`retrieve_relevant_concepts()`** — concept retrieval path:
   - Add `AND is_deleted = false` filter

3. **`get_chunks_for_book()`** (if exists) — full-book context path:
   - Add `AND is_deleted = false` filter

4. **`agent_service.format_agent_context()`** — context formatting:
   - After retrieving chunks, load annotations where `include_in_context = True`
   - Format: `f"[SNIPPET]\n{chunk.content}\n[NOTE: {annotation.content}]"` if annotation exists

## Book Reprocessing Safety Fix

**Critical:** `book_processing_service.retry_book()` currently does:
```python
db.query(BookChunk).filter(BookChunk.book_id == book_id).delete()
```

Must be changed to:
```python
# Preserve user-created and user-edited chunks
db.query(BookChunk).filter(
    BookChunk.book_id == book_id,
    BookChunk.is_user_created == False,
    BookChunk.updated_at == None  # Never user-edited
).delete()
```

## SQLAlchemy Model Changes

```python
class BookChunk(Base):
    __tablename__ = "book_chunks"
    # ... existing columns ...
    is_user_created = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    # Relationship
    annotations = relationship("SnippetAnnotation", back_populates="chunk", cascade="all, delete-orphan")

class SnippetAnnotation(Base):
    __tablename__ = "snippet_annotations"
    id = Column(UUID, primary_key=True, default=uuid4)
    chunk_id = Column(UUID, ForeignKey("book_chunks.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    include_in_context = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    chunk = relationship("BookChunk", back_populates="annotations")
```

## Build Order (Strict Dependency Chain)

```
Phase 1 — Backend Foundation:
  1. Write migration 006_snippet_management.sql
  2. Update BookChunk SQLAlchemy model (new columns + annotations relationship)
  3. Create SnippetAnnotation SQLAlchemy model
  4. Update Pydantic schemas (SnippetResponse, CreateSnippetRequest, UpdateSnippetRequest)
  5. Create SnippetService (CRUD + re-embedding logic)
  6. Fix retry_book() to preserve user-created/edited chunks
  7. Create snippet API endpoints (books.py extension or new snippets.py)
  8. Register routes in main.py
  9. Write backend tests

Phase 2 — Frontend:
  10. Add Snippets route to App.tsx
  11. Add Snippets nav item to sidebar/header
  12. Create SnippetsPage component (book selector)
  13. Create SnippetList component (paginated)
  14. Create SnippetCard component (preview + expand)
  15. Create SnippetEditor component (inline textarea + save/cancel)
  16. Add React Query hooks for snippet CRUD
  17. Add annotation UI within SnippetCard

Phase 3 — RAG Integration (can overlap with Phase 2):
  18. Modify rag_service.py (4 touchpoints: is_deleted filter, weight scoring, annotation injection)
  19. Modify agent_service.format_agent_context() (annotation injection)
  20. End-to-end test: edit snippet → verify agent uses new content
```

## Patterns to Follow

| Existing Pattern | Where | Apply To |
|-----------------|-------|---------|
| `books.py` endpoint structure | `backend/app/api/endpoints/` | New snippet endpoints |
| `BookResponse` schema shape | `schemas.py` | `SnippetResponse` schema |
| `BookManager.tsx` card layout | `frontend/src/components/Books/` | `SnippetCard` component |
| `useQuery` + `useMutation` | `BookManager.tsx` | Snippet React Query hooks |
| React Query invalidation | Any mutation hook | Invalidate `['snippets', book_id]` on CRUD |

## Anti-Patterns to Avoid

| Anti-Pattern | Reason |
|-------------|--------|
| Separate `snippets` table | Forces rewriting all 4 RAG query paths; no benefit |
| Async background re-embedding | Silent failure window; single embed call is ~200ms, sync is fine |
| Background re-embedding | `updated_at` check not threadsafe; transactional sync embed is safer |
| Embedding annotation text | Embeddings capture semantic meaning of content, not metadata notes |
| Returning all chunks without pagination | 400+ chunks will freeze browser and timeout the API |

---
*Research completed: 2026-03-05*
