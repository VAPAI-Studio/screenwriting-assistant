# Stack Research: Snippet Manager

**Project:** Screenwriting Assistant — Snippet Manager
**Dimension:** Stack
**Date:** 2026-03-05
**Confidence:** HIGH

## Summary

Zero new dependencies needed. The existing stack covers every requirement. Re-embedding should be synchronous (single call ~200ms). Plain `<textarea>` is the correct editor — no rich text editor needed.

## Recommendations

### Re-embedding Strategy

**Synchronous on save** — not background task.

- A single `embed_text()` call via `embedding_service.py` is ~200ms
- Background processing introduces stale-embedding windows and silent failure risk
- Only switch to async background if batch-editing many snippets is added later
- On save: update `content` → call `embedding_service.embed_text(content)` → update `embedding` column in same transaction

### Editor Component

**Plain `<textarea>` with controlled state** — not a rich text editor (no TipTap, Slate, ProseMirror).

- Chunks are plain text fed to embedding models — formatting is irrelevant
- Rich text editors add bundle size and complexity with zero value
- Pattern: click to expand inline edit → textarea → Save/Cancel buttons
- Follow existing `SidebarChat.tsx` / `CardGridView.tsx` patterns for inline editing

### Database Schema Changes

Three new columns on `book_chunks` table:

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `is_user_created` | Boolean | False | Preserve on book reprocessing |
| `annotation` | Text | NULL | Note passed alongside chunk to agent context |
| `weight` | Float | 1.0 | RAG retrieval priority multiplier |

No new tables needed. All fit on `book_chunks`.

### API Design

Nest under existing books resource:

```
GET    /api/books/{book_id}/snippets          # List (paginated)
POST   /api/books/{book_id}/snippets          # Create custom snippet
GET    /api/books/{book_id}/snippets/{id}     # Get single
PATCH  /api/books/{book_id}/snippets/{id}     # Update (triggers re-embed)
DELETE /api/books/{book_id}/snippets/{id}     # Delete
PATCH  /api/books/{book_id}/snippets/reorder  # Bulk weight update
```

Follows the same pattern as `/api/books/{book_id}/concepts` in the existing codebase.

**Pagination required** — books produce 400+ chunks. Use `?page=1&per_page=50`.

### Frontend Patterns

- React Query `useQuery` for list, `useMutation` for CRUD (same pattern as BookManager.tsx)
- Optimistic updates on delete/reorder for responsiveness
- Tailwind + Radix UI primitives — no new component libraries
- Top-level route: `/snippets` → book selector → snippet list

## Existing Dependencies That Cover Requirements

| Requirement | Covered By |
|-------------|-----------|
| Embedding on save | `embedding_service.embed_text()` (already exists) |
| Text editing | `<textarea>` (HTML standard) |
| List + pagination | React Query + FastAPI pagination pattern |
| Drag-to-reorder | `@dnd-kit/core` (if weight-by-order) OR numeric weight input (simpler) |
| Token count update | `tiktoken` (already in requirements.txt) |

**Recommendation:** Use numeric weight input (1.0 default, user types 0.5 or 2.0) rather than drag-to-reorder. Simpler, already has all dependencies.

## What NOT to Use

| Option | Reason to Avoid |
|--------|----------------|
| TipTap / Slate / ProseMirror | Rich text adds no value for plain-text embedding chunks |
| Background re-embedding | Silent failure risk, stale embeddings break RAG invisibly |
| Separate `snippets` table | Adds JOIN complexity; the existing `book_chunks` table is the right home |
| Streaming embeds | Single embed call is fast enough; streaming overkill |

## Roadmap Implications

1. **Phase 1 (Backend):** Migration + CRUD endpoints. Straightforward — follows existing `books.py` patterns exactly.
2. **Phase 2 (Frontend):** SnippetsPage with BookSelector + SnippetList + inline edit cards. Follows `BookManager.tsx` patterns.
3. **Phase 3 (RAG Integration):** Wire `weight` and `annotation` into `rag_service.semantic_search()`. Modify `retry_book()` to preserve user-created chunks.

Phase ordering: Backend first (frontend needs endpoints). RAG integration last (touches existing working code, needs weight/annotation data first).

---
*Research completed: 2026-03-05*
