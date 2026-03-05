# Phase 1: Backend Foundation and Data Safety - Research

**Researched:** 2026-03-05
**Domain:** FastAPI + SQLAlchemy + PostgreSQL — snippet CRUD API with transactional re-embedding and soft deletes
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BROW-01 | User can view all chunks for a selected book, paginated (50 per page) | Paginated GET endpoint on existing `book_chunks` table; SQLAlchemy `.offset()/.limit()` with total count query |
| EDIT-01 | User can edit the text content of any chunk inline; changes persist permanently | PATCH endpoint on `/api/books/{id}/snippets/{chunk_id}`; overwrite-in-place per project decision |
| EDIT-02 | Editing a chunk's content triggers re-embedding automatically (atomic: content + embedding + token count updated together) | Single DB transaction: update content + call `embedding_service.embed_text()` + write result; rollback on embed failure |
| EDIT-04 | User can delete a chunk; deleted chunks are excluded from all future agent context retrieval | Soft delete via `is_deleted` flag; all retrieval queries in `rag_service.py` must filter `is_deleted = False` |
| CUST-01 | User can create a new custom snippet from scratch for a selected book | POST endpoint; creates `BookChunk` with `is_user_created=True`, embeds on creation |
| CUST-02 | Custom snippets marked `is_user_created` survive book reprocessing (retry_book() must not delete them) | Fix `retry_book()` in `book_processing_service.py` to use `WHERE is_user_created = FALSE` in delete query |
| CUST-03 | New custom snippets are embedded automatically on creation | Embed call inside the POST handler before committing; rollback transaction if embed fails |
</phase_requirements>

---

## Summary

Phase 1 is a pure backend data-safety and API expansion phase. No new infrastructure is required — the project already has FastAPI, SQLAlchemy ORM, PostgreSQL with pgvector, and an `EmbeddingService` wrapping the OpenAI Embeddings API. Everything needed is already wired up.

The work decomposes into three tightly related pieces: (1) extend the `BookChunk` DB model and write a SQL migration adding `is_deleted`, `is_user_created`, and `updated_at` columns; (2) build a new `snippets` router under `/api/books/{id}/snippets` with four endpoints (list paginated, patch edit, delete soft, post create); and (3) fix the `retry_book()` method in `book_processing_service.py` to preserve user-owned rows before reprocessing deletes everything.

The most dangerous aspect of this phase is the atomic edit-and-re-embed pattern. If the embedding call succeeds but the DB commit fails (or vice versa), the stored embedding will be stale or the content will revert but the embedding will be fresh — either is silent corruption. The fix is a single SQLAlchemy session that mutates both columns and only commits after both the content update and the embedding value are ready. No commit happens until the embed result is in hand; if `embed_text()` raises, the session is rolled back automatically.

**Primary recommendation:** Add the three columns in a new SQL migration (006), extend the `BookChunk` SQLAlchemy model, build a `snippets.py` router following the existing `books.py` pattern, and fix `retry_book()` before wiring the router into `main.py`.

---

## Standard Stack

### Core (already present — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.110.0 | HTTP routing, request validation, dependency injection | Already used for all endpoints |
| SQLAlchemy | 2.0.27 | ORM, session management, transactions | Already used for all DB models |
| Pydantic v2 | >=2.10 | Request/response schemas with validation | Already used project-wide |
| psycopg2-binary | 2.9.9 | PostgreSQL adapter | Already present |
| openai | 1.12.0 | Embedding API calls via `embedding_service.embed_text()` | Already wired up |
| tiktoken | 0.7.0 | Token counting after content edit | Already installed |
| pytest | 8.0.2 | Test suite runner | Already used with SQLite in-memory fixtures |
| httpx / TestClient | >=0.25.0 | FastAPI test client | Already used in `conftest.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tiktoken | 0.7.0 | Recount tokens after content edit | Call `len(tiktoken.encoding_for_model("gpt-4").encode(new_content))` on every edit |
| pytest-asyncio | 0.23.5 | Run async test functions | Needed if any test calls async service methods directly |

**Installation:** No new packages needed. All dependencies are already in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── migrations/
│   └── 006_snippet_management.sql    # NEW: adds is_deleted, is_user_created, updated_at to book_chunks
├── app/
│   ├── models/
│   │   └── database.py               # MODIFY: add 3 columns to BookChunk
│   ├── api/
│   │   └── endpoints/
│   │       └── snippets.py           # NEW: paginate / edit / delete / create snippets
│   ├── services/
│   │   └── book_processing_service.py  # MODIFY: fix retry_book() delete query
│   └── main.py                       # MODIFY: register snippets router
```

### Pattern 1: Single-Transaction Atomic Edit

**What:** Both the content+token_count write and the embedding assignment happen inside one SQLAlchemy session, committed only after the embedding value is ready. If `embed_text()` raises an exception, the session is never committed and SQLAlchemy's rollback-on-close discards the content change.

**When to use:** Any time a DB write depends on an external API call succeeding.

```python
# Source: project pattern — see existing book_processing_service.py step 2
async def edit_snippet(
    book_id: UUID,
    chunk_id: UUID,
    new_content: str,
    db: Session,
) -> BookChunk:
    chunk = (
        db.query(BookChunk)
        .filter(BookChunk.id == chunk_id, BookChunk.book_id == book_id, BookChunk.is_deleted == False)
        .first()
    )
    if not chunk:
        raise HTTPException(status_code=404, detail="Snippet not found")

    # Compute new embedding BEFORE touching the DB
    # If this raises, nothing is committed
    new_embedding = await embedding_service.embed_text(new_content)

    # Recount tokens
    import tiktoken
    enc = tiktoken.encoding_for_model("gpt-4")
    new_token_count = len(enc.encode(new_content))

    # Now update all fields atomically
    chunk.content = new_content
    chunk.embedding = new_embedding
    chunk.token_count = new_token_count
    chunk.updated_at = func.now()

    db.commit()
    db.refresh(chunk)
    return chunk
```

**Why this works:** `embed_text()` is awaited before any DB mutation. If it throws (network error, rate limit, etc.), the function exits before `db.commit()` is ever called. SQLAlchemy's session is left clean.

### Pattern 2: Soft Delete

**What:** Set `is_deleted = True` rather than `DELETE FROM`. Retrieval queries filter `is_deleted = False`.

**When to use:** Any deletion that must be invisible to downstream consumers without physically destroying data.

```python
# Source: project pattern — safe, reversible
@router.delete("/{book_id}/snippets/{chunk_id}")
async def delete_snippet(book_id: UUID, chunk_id: UUID, db: Session = Depends(get_db), ...):
    chunk = db.query(BookChunk).filter(
        BookChunk.id == chunk_id,
        BookChunk.book_id == book_id,
        BookChunk.is_deleted == False,
    ).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Snippet not found")
    chunk.is_deleted = True
    db.commit()
    return {"message": "Snippet deleted"}
```

### Pattern 3: Paginated List Response

**What:** Accept `page` and `per_page` query params, return items + pagination metadata.

```python
@router.get("/{book_id}/snippets")
async def list_snippets(
    book_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    base_query = db.query(BookChunk).filter(
        BookChunk.book_id == book_id,
        BookChunk.is_deleted == False,
    ).order_by(BookChunk.chunk_index)

    total = base_query.count()
    chunks = base_query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "items": [...],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }
```

### Pattern 4: Custom Snippet Creation

**What:** POST creates a new `BookChunk` with `is_user_created=True`, embeds it atomically before commit.

```python
@router.post("/{book_id}/snippets")
async def create_snippet(book_id: UUID, body: SnippetCreate, db: Session = Depends(get_db), ...):
    # Embed before any DB write
    embedding = await embedding_service.embed_text(body.content)
    enc = tiktoken.encoding_for_model("gpt-4")
    token_count = len(enc.encode(body.content))

    # Compute next chunk_index
    max_index = db.query(func.max(BookChunk.chunk_index)).filter(BookChunk.book_id == book_id).scalar() or 0

    chunk = BookChunk(
        book_id=book_id,
        chunk_index=max_index + 1,
        content=body.content,
        embedding=embedding,
        token_count=token_count,
        chapter_title=body.chapter_title,
        page_number=body.page_number,
        is_user_created=True,
        is_deleted=False,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk
```

### Pattern 5: retry_book() Safety Fix

**What:** Change the bulk delete in `retry_book()` to exclude user-owned chunks.

**Current (BROKEN):**
```python
# backend/app/services/book_processing_service.py — current behavior
db.query(BookChunk).filter(BookChunk.book_id == book.id).delete()
```

**Fixed:**
```python
# Preserve user-created and user-edited chunks
db.query(BookChunk).filter(
    BookChunk.book_id == book.id,
    BookChunk.is_user_created == False,
).delete(synchronize_session=False)
```

Note: `synchronize_session=False` is required when using bulk delete with SQLAlchemy 2.x ORM to avoid session sync issues on large datasets.

### Anti-Patterns to Avoid

- **Embedding then failing the commit:** Never call `embed_text()` and commit content separately. Always embed first, then commit both together.
- **Hard-deleting user-edited chunks in retry_book:** The current code deletes ALL chunks. After the fix, only auto-generated (`is_user_created=False`) chunks are deleted.
- **Filtering soft deletes only at the API layer:** The `rag_service.py` semantic search queries use raw SQL. They must also add `AND bc.is_deleted = FALSE` to every `book_chunks` query — otherwise deleted chunks still pollute RAG results.
- **Missing `synchronize_session` on bulk deletes:** SQLAlchemy ORM bulk `.delete()` without `synchronize_session=False` can raise errors or silently corrupt the session cache when deleting many rows.
- **Counting tokens with `len(content.split())` word count:** Use `tiktoken` to match the token counting used at chunk creation time.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embedding generation | Custom HTTP calls to OpenAI | `embedding_service.embed_text()` | Already handles retries, batching, LRU cache, RateLimitError backoff |
| Token counting | Character count or word split | `tiktoken.encoding_for_model("gpt-4").encode()` | Matches actual GPT token boundaries used during chunking |
| Request validation | Manual field checks | Pydantic v2 schemas with `Field()` validators | Already the project pattern; ValidationError auto-mapped to 422 |
| Pagination math | Custom offset logic | `.offset((page-1)*per_page).limit(per_page)` + `.count()` | SQLAlchemy handles it cleanly; don't invent a cursor |
| DB transactions | Manual `BEGIN/COMMIT` SQL | SQLAlchemy session commit/rollback | Session-level atomicity is already the project pattern |

**Key insight:** This project already has every primitive needed. The task is assembly and integration, not building new infrastructure.

---

## Common Pitfalls

### Pitfall 1: RAG Queries Not Filtering Soft-Deleted Chunks
**What goes wrong:** `rag_service.semantic_search()` and `get_supporting_chunks()` use raw SQL strings against `book_chunks`. Adding `is_deleted` to the ORM model does NOT automatically filter it in raw queries.
**Why it happens:** Raw `sql_text()` queries bypass ORM model-level filtering.
**How to avoid:** After adding the column, grep every raw SQL query touching `book_chunks` and add `AND bc.is_deleted = FALSE` (or `AND bc.is_deleted IS NOT TRUE` for nullable boolean). There are currently 2 such queries in `rag_service.py` (lines 134-149 and 203-219 and 251-267).
**Warning signs:** A deleted snippet still appears in agent context or semantic search results.

### Pitfall 2: Stale Embedding After Embed Failure
**What goes wrong:** Content is committed to DB. The embed call fails. Now `content` is new but `embedding` is old — stale embedding silently persists forever.
**Why it happens:** Committing content and embedding in separate DB calls, or catching the embed exception and returning an error without rolling back.
**How to avoid:** Always compute the embedding value before calling `db.commit()`. If `embed_text()` raises, let the exception propagate. The session closes without committing.
**Warning signs:** RAG results return a snippet whose content doesn't match what the embedding was trained on.

### Pitfall 3: retry_book() Deletes User Chunks
**What goes wrong:** User creates a custom snippet, triggers retry (book was failed/paused), and their chunk disappears.
**Why it happens:** Current `retry_book()` does `db.query(BookChunk).filter(BookChunk.book_id == book.id).delete()` — no exclusion for user-owned rows.
**How to avoid:** Add `BookChunk.is_user_created == False` to the filter. Preserve user-created chunks across reprocessing by keeping them out of the delete query.
**Warning signs:** User-created snippets vanish after a retry operation.

### Pitfall 4: chunk_index Collision on Custom Snippet Creation
**What goes wrong:** Two custom snippets created in quick succession get the same `chunk_index` if the max query is computed before either commits.
**Why it happens:** Non-atomic read-then-write of `max(chunk_index)`.
**How to avoid:** For MVP, use a sufficiently large starting offset (e.g., `max_index + 1` inside a transaction, or use `uuid` as the natural key and treat `chunk_index` as ordering-only). If collisions become an issue, use a DB sequence. For this phase, treating `chunk_index` as advisory ordering is sufficient since retrieval uses `chunk_index` for display ordering, not as a unique key.
**Warning signs:** Two user snippets appear at the same position in paginated list.

### Pitfall 5: SafeVector Type Compatibility in Tests
**What goes wrong:** The existing test suite uses SQLite in-memory (via `conftest.py`). `SafeVector` is a custom `UserDefinedType` for pgvector. SQLite cannot store vector columns.
**Why it happens:** The `conftest.py` patches UUID and Enum columns for SQLite but does not patch `SafeVector`.
**How to avoid:** For snippet tests that involve embeddings, either (a) mock `embedding_service.embed_text()` to return a list of floats and skip vector storage verification, or (b) add a SQLite-compatible patch in `conftest.py` that converts `SafeVector` columns to `Text`. Option (a) is simpler and matches the existing test pattern of mocking external services.
**Warning signs:** Tests fail with `sqlite3.OperationalError: unknown type "vector(1536)"`.

---

## Code Examples

Verified patterns from the existing codebase:

### Existing BookChunk Model (to extend)
```python
# Source: backend/app/models/database.py lines 275-289
class BookChunk(Base):
    __tablename__ = "book_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    embedding = deferred(Column(SafeVector(1536)))
    chapter_title = Column(String(500))
    page_number = Column(Integer)
    concept_ids = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    book = sa_relationship("Book", back_populates="chunks")
```

**Add these columns:**
```python
    # Phase 1 additions
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_user_created = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### SQL Migration Template (006_snippet_management.sql)
```sql
-- backend/migrations/006_snippet_management.sql
-- Adds snippet management columns to book_chunks

ALTER TABLE book_chunks
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS is_user_created BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- Index for filtering non-deleted chunks efficiently
CREATE INDEX IF NOT EXISTS idx_book_chunks_not_deleted
    ON book_chunks(book_id, is_deleted)
    WHERE is_deleted = FALSE;

-- Index for finding user-created chunks during retry_book
CREATE INDEX IF NOT EXISTS idx_book_chunks_user_created
    ON book_chunks(book_id, is_user_created)
    WHERE is_user_created = TRUE;
```

### Existing retry_book() (lines to fix)
```python
# Source: backend/app/services/book_processing_service.py lines 292-293
# CURRENT (broken — deletes user chunks):
db.query(BookChunk).filter(BookChunk.book_id == book.id).delete()

# FIXED (preserves user-created chunks):
db.query(BookChunk).filter(
    BookChunk.book_id == book.id,
    BookChunk.is_user_created == False,
).delete(synchronize_session=False)
```

### Existing router registration pattern (for main.py)
```python
# Source: backend/app/main.py line 84
app.include_router(books.router, prefix="/api/books", tags=["books"])
# Add after:
app.include_router(snippets.router, prefix="/api/books", tags=["snippets"])
# (snippets router handles /{book_id}/snippets sub-paths)
```

### Existing embed_text usage
```python
# Source: backend/app/services/book_processing_service.py lines 67-68
chunk_embeddings = await embedding_service.embed_batch(chunk_texts)
# For single-chunk edit, use:
new_embedding = await embedding_service.embed_text(new_content)
# Both return List[float] compatible with SafeVector(1536)
```

### Existing RAG chunk query (must add is_deleted filter)
```python
# Source: backend/app/services/rag_service.py lines 251-267
# CURRENT (missing is_deleted filter):
chunk_results = db.execute(
    sql_text("""
        SELECT bc.content, bc.chapter_title, bc.page_number, ...
        FROM book_chunks bc
        JOIN books b ON bc.book_id = b.id
        WHERE bc.book_id = ANY(CAST(:book_ids AS uuid[]))
          AND bc.embedding IS NOT NULL
        ORDER BY bc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), ...
)

# REQUIRED ADDITION:
#   AND bc.is_deleted IS NOT TRUE
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|----------------------|
| Hard delete rows | Soft delete with `is_deleted` flag | Retrieval queries must explicitly filter; migration needed |
| Delete all chunks on retry | Preserve `is_user_created=True` rows | Single-line fix in `retry_book()` |
| No user-created chunks | `is_user_created` flag | Migration + model extension + POST endpoint |
| Separate embed + commit | Embed before commit (atomic) | Core pattern for EDIT-02 and CUST-03 |

**No deprecated approaches in use that need changing** — the existing codebase is modern SQLAlchemy 2.x, Pydantic v2, and FastAPI. No upgrades needed.

---

## Open Questions

1. **What token counting model should be used for user-created snippets?**
   - What we know: Book processing service chunks text using `tiktoken` (via `document_service`); `requirements.txt` has `tiktoken==0.7.0`; the config has `OPENAI_MODEL` pointing to GPT-4.
   - What's unclear: The exact encoding name used in `document_service.py` wasn't read (it isn't in the files reviewed). It's likely `"cl100k_base"` (GPT-4 encoding) or `tiktoken.encoding_for_model("gpt-4")`.
   - Recommendation: Read `document_service.py` during planning to confirm the encoding, then use the same one in the snippet edit/create handlers for consistency.

2. **Should the snippets router be in `books.py` or a new `snippets.py` file?**
   - What we know: `books.py` handles upload, list, pause, resume, retry, get, concepts. Adding 4 more endpoints would make it large.
   - Recommendation: New `snippets.py` with `router = APIRouter()` mounted at `/api/books` prefix in `main.py`. This keeps books.py clean and matches the separation pattern (e.g., `agents.py` is separate from `books.py`).

3. **Are there other places in the codebase that query `book_chunks` without an `is_deleted` filter?**
   - What we know: `rag_service.py` has 2 raw SQL queries touching `book_chunks`, and `book_processing_service.py` queries chunks for concept-linking (line 90). The concept-linking query `db.query(BookChunk).filter(BookChunk.book_id == book_id).all()` will fetch soft-deleted chunks.
   - Recommendation: The concept-linking query in `process_book()` (step 6) should also filter `BookChunk.is_deleted == False` since concept-linking soft-deleted rows wastes compute and is meaningless.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | none — uses default pytest discovery |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/test_api.py -x -q` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BROW-01 | GET /api/books/{id}/snippets returns paginated list with metadata | integration | `pytest app/tests/test_snippets_api.py::TestSnippetsAPI::test_list_snippets_paginated -x` | Wave 0 |
| EDIT-01 | PATCH /api/books/{id}/snippets/{chunk_id} persists content change | integration | `pytest app/tests/test_snippets_api.py::TestSnippetsAPI::test_edit_snippet_persists -x` | Wave 0 |
| EDIT-02 | PATCH re-embeds; if embed fails, content is NOT changed in DB | integration | `pytest app/tests/test_snippets_api.py::TestSnippetsAPI::test_edit_snippet_atomic_rollback -x` | Wave 0 |
| EDIT-04 | DELETE soft-deletes; chunk absent from subsequent list | integration | `pytest app/tests/test_snippets_api.py::TestSnippetsAPI::test_delete_snippet_soft -x` | Wave 0 |
| CUST-01 | POST creates snippet with is_user_created=True | integration | `pytest app/tests/test_snippets_api.py::TestSnippetsAPI::test_create_custom_snippet -x` | Wave 0 |
| CUST-02 | retry_book() preserves is_user_created=True chunks | unit | `pytest app/tests/test_snippets_api.py::TestRetryBook::test_retry_preserves_user_chunks -x` | Wave 0 |
| CUST-03 | POST embeds snippet on creation; embedding stored | integration | `pytest app/tests/test_snippets_api.py::TestSnippetsAPI::test_create_snippet_has_embedding -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest app/tests/test_snippets_api.py -x -q`
- **Per wave merge:** `pytest app/tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_snippets_api.py` — covers all Phase 1 requirements
- [ ] Mock strategy for `embedding_service.embed_text()` — must be mocked to return `[0.1] * 1536` to avoid live OpenAI calls in tests; use `unittest.mock.patch` or pytest fixture
- [ ] SQLite SafeVector patch in `conftest.py` — `SafeVector` column type must be patched to `Text` for SQLite compatibility, or use `monkeypatch` to skip vector storage in snippet tests

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `backend/app/models/database.py` — `BookChunk` model, existing columns
- Direct codebase inspection: `backend/app/services/book_processing_service.py` — `retry_book()` delete pattern (lines 292-293)
- Direct codebase inspection: `backend/app/services/rag_service.py` — all raw SQL queries touching `book_chunks`
- Direct codebase inspection: `backend/app/services/embedding_service.py` — `embed_text()` and `embed_batch()` signatures and behavior
- Direct codebase inspection: `backend/app/api/endpoints/books.py` — existing endpoint pattern, auth dependency
- Direct codebase inspection: `backend/app/tests/conftest.py` — SQLite test setup, mock auth headers
- Direct codebase inspection: `backend/migrations/002_knowledge_graph.sql` and `005_book_progress.sql` — migration pattern
- Direct codebase inspection: `backend/requirements.txt` — exact dependency versions

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.x docs pattern: `synchronize_session=False` on bulk `.delete()` — standard recommendation for large datasets
- FastAPI pagination pattern: `Query()` with `ge`/`le` bounds on `page`/`per_page` — standard FastAPI idiom

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries directly observed in requirements.txt and usage
- Architecture: HIGH — patterns derived directly from existing code in the repo
- Pitfalls: HIGH — all pitfalls identified from direct inspection of the code that will be modified
- Test strategy: MEDIUM — SQLite SafeVector patch approach is a recommendation; needs validation against actual SQLite behavior

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable stack, no fast-moving dependencies)
