# Screenwriting Assistant — Snippet Manager

## What This Is

A screenwriting assistant that uses uploaded books as knowledge sources for AI agents. Books are chunked and embedded at upload time; agents retrieve relevant chunks via RAG to inform their feedback. This milestone adds a dedicated **Snippets** page where writers can see, edit, annotate, reorder, and curate the exact text fragments being fed to their agents — making the knowledge context transparent and controllable.

## Core Value

Writers have full visibility and control over what book knowledge their AI agents use, so they can trust and tune the context instead of treating it as a black box.

## Requirements

### Validated

- ✓ Book upload and processing pipeline (chunking at 750 tokens/150 overlap, embedding via text-embedding-3-small) — existing
- ✓ RAG retrieval: agents pull relevant BookChunks + Concepts via embedding similarity — existing
- ✓ Agent-book association (AgentBook many-to-many) — existing
- ✓ BookManager UI for uploading and managing books — existing
- ✓ Book processing status tracking (PENDING → EXTRACTING → ANALYZING → EMBEDDING → COMPLETED) — existing

### Active

- [ ] Top-level "Snippets" navigation entry in the frontend
- [ ] Per-book snippet list: view all BookChunks for a selected book
- [ ] Edit snippet text inline and persist changes permanently (re-embed on save)
- [ ] Add custom snippets to a book (not derived from chunking — user-authored)
- [ ] Remove snippets from a book (soft or hard delete)
- [ ] Reorder snippets and assign weight/priority for RAG retrieval
- [ ] Annotate snippets with a note (displayed alongside the chunk in agent context)

### Out of Scope

- Real-time collaboration on snippets — single-user MVP
- Snippet versioning/history — edits overwrite in place
- Bulk import of custom snippets — one at a time for now
- Cross-book snippet merging — per-book management only

## Context

**Existing data model:** `BookChunk` (id, book_id, content, chunk_index, token_count, embedding vector) stored in PostgreSQL with pgvector. Chunks created by `book_processing_service.py`.

**RAG flow:** `rag_service.retrieve_relevant_concepts()` does cosine similarity search against chunk embeddings, returning top-k chunks as agent context. Any edits to chunk content must re-generate the embedding to maintain retrieval accuracy.

**Current gap:** There is no UI surface for the `BookChunk` table — chunks are created automatically and consumed silently. Writers cannot see, verify, or improve what context their agents receive.

**Custom snippets:** Need a way to mark chunks as `user_created=True` so they're preserved if the book is ever reprocessed.

## Constraints

- **Tech Stack:** React 18 + TypeScript frontend, FastAPI + SQLAlchemy backend, PostgreSQL 15 + pgvector — no new infrastructure
- **Embedding:** Edited or new snippet content must be re-embedded via OpenAI `text-embedding-3-small` to keep RAG retrieval accurate
- **Auth:** Mock auth for MVP (`mock-token`) — no multi-user ownership concerns yet

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Permanent edits (overwrite in place) | Simplicity — no version history needed for MVP | — Pending |
| Re-embed on save | Edited text with stale embedding breaks RAG — must stay in sync | — Pending |
| Top-level nav (not nested under Books) | Snippets are a primary workflow surface, not a sub-feature of book management | — Pending |

---
*Last updated: 2026-03-05 after initialization*
