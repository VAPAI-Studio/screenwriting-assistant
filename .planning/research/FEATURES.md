# Feature Landscape: Snippet Manager

**Domain:** RAG knowledge base management UI — chunk-level visibility and curation for a screenwriting assistant
**Researched:** 2026-03-05
**Confidence:** MEDIUM (based on Dify, Coze, Pinecone Console, Weaviate, Flowise, LangFlow patterns)

## Table Stakes

Features users expect. Missing = the Snippets page feels like a debug view, not a real feature.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **List all chunks per book** | Fundamental promise — "see what your agents know." Every RAG UI (Dify, Coze, Pinecone) shows chunk listings by source document. | Low | `BookChunk` model has `book_id`, `chunk_index`, `content`. Query: `GET /books/:id/chunks`. |
| **Book selector / navigation** | Users have multiple books. Need to pick which book's snippets to view. | Low | Existing `getBooks()` API already returns book list. Dropdown or sidebar selector. |
| **Chunk content preview** | Each chunk shows a meaningful text preview (~200 chars) expandable on click. | Low | `BookChunk.content` already stored. Truncate in card, expand on click. |
| **Chunk metadata display** | Show chapter title, page number, token count, chunk index per chunk. | Low | All fields exist on `BookChunk`: `chapter_title`, `page_number`, `token_count`, `chunk_index`. |
| **Edit chunk text inline** | Core "control" promise. See-only without edit feels pointless. | Medium | Requires: PATCH endpoint, re-embed edited content, optimistic UI with loading during re-embedding (~500ms–2s). |
| **Delete a chunk** | Remove irrelevant or noisy chunks. | Low | `DELETE /chunks/:id`. Hard delete for MVP. |
| **Add custom snippet** | Inject user-authored knowledge fragments. Must survive book reprocessing. | Medium | POST endpoint, `user_created=True` flag, generate embedding. |
| **Empty / zero-data states** | When book is processing or all chunks deleted, show clear message. | Low | Show processing status or "No snippets yet." |
| **Loading and error states** | Embedding ops are async and take noticeable time. Visual feedback required. | Low | React Query `isPending`, `isError` states. Follow `BookManager.tsx` patterns. |

## Differentiators

Features that set the Snippets page apart from a basic CRUD view.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Search within snippets** | Books produce 50–200+ chunks. Frontend-only substring filter is nearly free. | Low | `Array.filter()` on loaded chunks — no backend change needed. |
| **Chunk annotations / notes** | Attach a note explaining context or usage to any chunk. Passed to agents alongside content. | Medium | New `annotation` column on `BookChunk`. Accept in PATCH endpoint. |
| **Reorder / priority weighting** | Assign numeric weight to influence RAG retrieval ranking. | High | New `weight` column + modify `semantic_search` to factor weight. Touches RAG pipeline. |
| **Chunk source highlighting** | Visual breadcrumb showing chapter/page — links chunk back to source book structure. | Low | Data exists. Just visual treatment (badge) on each chunk card. |
| **Token count + budget display** | Show token count per chunk AND total for the book. Helps users understand agent context budget. | Low | Sum `token_count` across all chunks. Display as summary stat. |
| **Distinguish auto vs. custom snippets** | Visual badge (Auto / Custom) differentiating machine chunks from user-created ones. | Low | Requires `user_created` flag from DB migration. Then a visual badge. |
| **Bulk selection and delete** | Select multiple noisy chunks and delete at once. | Medium | Checkbox selection state + `DELETE /books/:id/chunks/bulk` endpoint + confirmation dialog. |
| **Semantic similarity preview** | Test search box: "what would the agent retrieve for this query?" | High | Scope existing `semantic_search` to a single book. High value but not v1. |
| **Concept linkage display** | Show which `Concept`s are linked to each chunk via `concept_ids`. | Medium | Resolve concept IDs to names. JOIN or lookup needed. |

## Anti-Features

Explicitly NOT building in v1.

| Anti-Feature | Why Avoid |
|--------------|-----------|
| **Chunk versioning / edit history** | Out of scope per PROJECT.md. Users can reprocess book to revert. |
| **Bulk import of custom snippets** | Out of scope. CSV/JSON parsing + batch embedding adds complexity for low MVP demand. |
| **Cross-book snippet merging** | Out of scope. Complicates data model, provenance confusion. |
| **Real-time collaboration** | Out of scope. Single-user MVP. |
| **Automatic re-chunking** | Power-user feature. Use existing retry-from-scratch on Book. |
| **Drag-and-drop chunk reordering** | Complex for 100+ items. Use numeric weight input instead — same RAG outcome. |
| **Embedding visualization** | t-SNE/UMAP looks impressive in demos but low practical value for screenwriters. |
| **Snippet commenting / discussion** | Social features in a single-user tool. Use annotation field for personal notes. |

## Feature Dependencies

```
Book Selector → List Chunks (must select book first)
List Chunks → Edit/Delete/Add (must see chunks to act on them)
user_created flag (DB migration) → Add Custom Snippet
Edit Chunk → Re-embed on Save (stale embeddings break RAG)
Add Custom Snippet → Generate Embedding
Annotations → DB migration (new column)
Priority/Weight → DB migration + RAG service update
Search → List Chunks (filters the list)
Bulk Delete → List Chunks + selection state
```

## MVP Recommendation

**Phase 1 — Core CRUD loop:**
1. Book selector + list all chunks
2. Chunk content preview with metadata (chapter, page, token count)
3. Edit chunk text inline with re-embed on save
4. Delete a chunk
5. Add custom snippet (with `user_created` flag)
6. Search within snippets (frontend-only filter — nearly free)
7. Loading / error / empty states

**Phase 2 — Annotations + retrieval tuning:**
- Chunk annotations/notes
- Priority/weight for RAG retrieval (requires RAG pipeline change)
- Auto vs. custom visual badges
- Token budget display

**Phase 3 or later:**
- Bulk delete
- Concept linkage display
- Semantic similarity preview

## Key Insight: Re-embedding Is the Complexity Pivot

Every edit and custom snippet creation requires an async embedding call. This is the single operation that makes "edit a text field" meaningfully harder than standard CRUD. Plan for loading states, error handling on embed failure, and token count recalculation on save.

## Existing Codebase Leverage

| Asset | Reuse For |
|-------|-----------|
| `BookChunk` model | Backend data layer (needs 3 new columns) |
| `embedding_service.embed_text()` | Re-embedding edited/new snippets |
| `rag_service.semantic_search()` | Semantic search preview (later) |
| `BookManager.tsx` patterns | Card layout, status badges, React Query mutations |
| `api.tsx` fetch wrapper | New API call patterns |
| `getBooks()` | Book selector data source |

---
*Research completed: 2026-03-05*
