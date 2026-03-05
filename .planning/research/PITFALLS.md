# Pitfalls: Snippet Manager

**Domain:** RAG chunk editing on an existing screenwriting assistant
**Researched:** 2026-03-05
**Confidence:** HIGH (grounded in actual codebase analysis)

## Critical Pitfalls

### 1. Stale Embeddings After Edit

**What happens:** A PATCH endpoint updates `BookChunk.content` without regenerating `BookChunk.embedding`. The text has changed but the embedding still represents the old text. RAG retrieval now returns this chunk for semantically incorrect queries and misses it for correct ones. The bug is completely silent — no errors, just degraded retrieval quality.

**Warning signs:**
- PATCH endpoint returns 200 but doesn't call `embedding_service.embed_text()`
- Agent responses seem "confused" after user edits a chunk

**Prevention:** Make re-embedding atomic with content save. In the same DB transaction: update `content` → call `embed_text(new_content)` → update `embedding`. Never let the two columns diverge. Also recalculate `token_count` via `tiktoken` on every save.

**Phase:** Phase 1 (CRUD endpoints) — must be solved before any editing UI ships.

---

### 2. Book Reprocessing Destroys User Work

**What happens:** `retry_book()` in `book_processing_service.py` does a DELETE of all `BookChunk` records for the book before re-chunking. Any custom snippets the user added, or any edits they made to existing chunks, are permanently lost. The user retries a failed book and silently loses all their curation work.

**Warning signs:**
- `retry_book()` has no check for `is_user_created` or `is_user_edited` flags
- User-created chunks have `book_id` as their only identifier

**Prevention:**
- Add `is_user_created` (Boolean, default False) and `is_user_edited` (Boolean, default False) columns to `BookChunk` in Phase 1 migration
- Modify `retry_book()` to: (1) back up chunks where `is_user_created=True` OR `is_user_edited=True`, (2) delete auto-generated chunks, (3) re-chunk the book, (4) restore backed-up chunks with new sequential `chunk_index` values

**Phase:** Phase 1 (DB migration) — must happen before editing UI ships.

---

### 3. Concept-Chunk Linking Becomes Stale on Edit

**What happens:** `BookChunk.concept_ids` stores a JSON array of concept IDs linked to the chunk via string-matching heuristics run during `book_processing_service.process_book()`. When a user edits the chunk content, the `concept_ids` still references concepts matched against the old text. The knowledge graph connection is now wrong — concepts are linked to text that no longer contains the relevant terms.

**Warning signs:**
- Editing chunk content doesn't trigger re-linking
- `concept_ids` column not updated in PATCH endpoint

**Prevention:** On content edit, re-run concept linking for that chunk. Either: (1) call `knowledge_extraction_service` to re-extract and re-link concepts for the edited chunk, or (2) clear `concept_ids` on edit and rely on embedding similarity alone for retrieval. Option 2 is simpler for MVP.

**Phase:** Phase 1 (PATCH endpoint) — clear `concept_ids` on save at minimum.

---

### 4. Weight/Priority Has No Retrieval Effect Without RAG Query Changes

**What happens:** A `weight` column is added to `BookChunk` and the UI lets users set priority. But all four retrieval paths in `rag_service.py` use pure cosine-similarity ordering — the `weight` field is never read. Users think they're influencing what the agent knows. They're not. The weight control is purely decorative.

**Warning signs:**
- `rag_service.semantic_search()` (or equivalent) orders results by `similarity` only
- No `ORDER BY weight * similarity DESC` or equivalent weighted scoring
- Weight column added in migration but not referenced in any query

**Prevention:** When implementing weight, immediately update the RAG retrieval query to incorporate it: `effective_score = similarity * weight`. Add this to Phase 2 scope explicitly — do not ship the weight UI without the retrieval change.

**Phase:** Phase 2 (RAG integration) — weight UI and RAG query change must ship together.

---

## Moderate Pitfalls

### 5. No Pagination = UI Freeze on Large Books

**What happens:** A large book (300-page novel) produces 400–600 `BookChunk` records. Loading all of them at once returns a massive JSON payload, freezes the browser during rendering, and makes the page unusable. This is not a theoretical risk — 750-token chunks from a 100k-token book = ~130 chunks minimum. Longer books hit 500+.

**Warning signs:**
- `GET /books/:id/snippets` returns all rows without `LIMIT`/`OFFSET`
- No `page`/`per_page` query params on the endpoint

**Prevention:** Server-side pagination from day one. Use `?page=1&per_page=50` on the list endpoint. Never return all chunks in a single response. Add virtual scrolling or "Load more" on the frontend if needed.

**Phase:** Phase 1 (list endpoint design) — build pagination in from the start.

---

### 6. chunk_index Collision for Custom Snippets

**What happens:** Auto-generated chunks are assigned sequential `chunk_index` values (0, 1, 2, ...). A user-created snippet is inserted with `chunk_index = max + 1`. When the book is reprocessed, the new auto-generated chunks are re-indexed from 0, potentially colliding with the appended user chunk or invalidating ordering assumptions.

**Prevention:** Use a separate `sort_order` float column (not `chunk_index`) for display ordering. `chunk_index` stays as the original chunking index (immutable after creation). `sort_order` is user-controllable. User-created snippets get `chunk_index = NULL` and a `sort_order` that places them at the end by default.

**Phase:** Phase 1 (DB schema design) — decide this before the migration runs.

---

### 7. Embedding API Failure Leaves Content/Embedding Out of Sync

**What happens:** User edits chunk content. PATCH endpoint updates `content` in the DB but the embedding API call to OpenAI fails (network error, rate limit, timeout). Content is now saved with the old embedding. The error may or may not be surfaced to the user.

**Prevention:**
- Use a DB transaction: wrap content update + embedding update together
- If embedding fails, roll back the content change and return a clear error to the frontend
- Alternatively: add `embedding_stale` (Boolean) flag — set to True when content changes, False when embedding updates successfully. Use this flag in RAG retrieval to warn or skip stale chunks.

**Phase:** Phase 1 (PATCH endpoint) — transactional safety is non-negotiable.

---

### 8. Token Count Mismatch After Edit

**What happens:** User edits a chunk to be significantly longer or shorter. `BookChunk.token_count` still reflects the original content's token count. RAG context assembly uses `token_count` to estimate context window usage. With stale token counts, the agent may receive more context than the model's window allows, causing truncation or API errors.

**Prevention:** Recalculate `token_count` using `tiktoken` on every content save. This is a cheap operation (~1ms).

**Phase:** Phase 1 (PATCH endpoint).

---

### 9. Delete Cascade Removes RAG Context Without Warning

**What happens:** User deletes a chunk that is actively referenced in recent `ChatMessage.book_references`. The chunk is gone but chat history still references its ID. Future attempts to display "what context was used" for past messages will fail or show missing references.

**Prevention:** Hard delete is fine for MVP (per PROJECT.md). But add a confirmation dialog: "This snippet is used in agent context. Deleting it will remove it from all future conversations." No need to preserve the data — just warn the user.

**Phase:** Phase 1 (delete endpoint + UI).

---

## Minor Pitfalls

### 10. Annotation Text Not Passed to Agent Context

**What happens:** User adds an annotation to a chunk explaining its significance ("This is the author's core thesis on structure"). The annotation is stored in the DB but `agent_service.format_agent_context()` only passes `chunk.content` to the system prompt — the annotation is ignored. Users think the agent knows their note. It doesn't.

**Prevention:** When building agent context, concatenate annotation into the context string: `f"[SNIPPET]\n{chunk.content}\n[NOTE: {chunk.annotation}]"` if annotation is not null.

**Phase:** Phase 2 (RAG integration) — when annotations are added.

---

### 11. Weight = 0 Makes Chunk Permanently Unretrievable

**What happens:** User accidentally sets a chunk's weight to 0. In weighted scoring (`similarity * weight`), the score becomes 0 regardless of semantic similarity. The chunk never surfaces in RAG results, even for highly relevant queries. No error, no warning.

**Prevention:** Validate weight on input: minimum 0.1, maximum 10.0 (or similar). Warn users if they set weight below 0.5. Display "This snippet will rarely be retrieved" for low-weight chunks.

**Phase:** Phase 2 (weight UI).

---

### 12. Race Condition on Rapid Successive Edits

**What happens:** User types, pauses, types more, and the PATCH endpoint is called twice in quick succession. Two concurrent embedding requests fire. The second response arrives first (race condition), and the first (stale) response overwrites the correct embedding.

**Prevention:** Debounce the save action on the frontend (300ms minimum after last keystroke). Use optimistic locking on the backend: check `updated_at` timestamp before writing. For MVP, debounce alone is sufficient.

**Phase:** Phase 1 (frontend editor component).

---

### 13. Snippets Page Shows Chunks for Books Still Processing

**What happens:** A book with `status != COMPLETED` has partial chunks (some processed, some not). The Snippets page shows these partial results without indicating the book is still being processed. Users edit chunks not knowing the set is incomplete — their edits may be on chunks that will be deleted and re-created when processing completes.

**Prevention:** Show a "still processing" banner on the Snippets page when `book.status != COMPLETED`. Disable edit/delete/create controls until processing is complete, or at least warn the user.

**Phase:** Phase 1 (SnippetsPage component).

---

## Summary: What Must Be in Phase 1

These pitfalls are prerequisites — ship any of them unresolved and the feature corrupts data silently:

| # | Pitfall | Phase 1 Solution |
|---|---------|-----------------|
| 1 | Stale embeddings | Atomic re-embed on save |
| 2 | Reprocessing destroys user work | `is_user_created` + `is_user_edited` flags in migration |
| 3 | Concept linking staleness | Clear `concept_ids` on edit |
| 5 | UI freeze | Server-side pagination from day 1 |
| 6 | chunk_index collision | Use separate `sort_order` column |
| 7 | Embedding API failure | Transactional rollback on embed failure |
| 8 | Token count mismatch | Recalculate `token_count` on save |
| 12 | Race conditions | Debounce save action |
| 13 | Processing state shown | Disable editing during processing |

---
*Research completed: 2026-03-05*
