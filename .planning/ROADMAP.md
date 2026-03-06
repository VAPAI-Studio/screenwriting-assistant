# Roadmap: Screenwriting Assistant — Snippet Manager

## Overview

This milestone gives writers full visibility and control over the book knowledge chunks that feed their AI agents. The build progresses from a safe, transactional backend API (Phase 1), through a complete frontend Snippets page for browsing, editing, and creating snippets (Phase 2), to RAG pipeline integration where annotations and priority weights actually influence agent retrieval behavior (Phase 3). Each phase delivers a coherent, verifiable capability that unblocks the next.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Backend Foundation and Data Safety** - Database migration, BookChunk model extensions, snippet CRUD API with transactional re-embedding, and retry_book() safety fix (completed 2026-03-05)
- [ ] **Phase 2: Frontend Snippets Page** - Top-level Snippets page with book selector, AI-curated snippet browsing, inline editing, search, and processing-state handling
- [ ] **Phase 3: RAG Integration and Enrichment** - Annotations, priority weights, RAG query modifications, and agent context injection

## Phase Details

### Phase 1: Backend Foundation and Data Safety
**Goal**: A safe, tested API exists for all snippet operations — editing re-embeds atomically, custom snippets survive book reprocessing, and no data corruption is possible
**Depends on**: Nothing (first phase)
**Requirements**: BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03
**Success Criteria** (what must be TRUE):
  1. API returns paginated chunks for a book (GET /api/books/{id}/snippets?page=1&per_page=50 returns correct data with pagination metadata)
  2. Editing a chunk via API updates content, regenerates embedding, and recalculates token count in a single transaction — if embedding fails, content is rolled back and an error is returned
  3. Deleting a chunk via API excludes it from all subsequent retrieval (soft delete with is_deleted flag)
  4. Creating a custom snippet via API embeds it automatically and marks it with is_user_created=True
  5. Reprocessing a book (retry_book) preserves all user-created and user-edited chunks
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Test scaffold: conftest SafeVector patch + embed mock fixture + 7 failing test stubs
- [x] 01-02-PLAN.md — DB foundation: migration 006, BookChunk model extension, RAG soft-delete filters, retry_book safety fix
- [x] 01-03-PLAN.md — Snippets router: 4 endpoints (list/edit/delete/create), Pydantic schemas, main.py wiring

### Phase 2: Frontend Snippets Page
**Goal**: Writers can browse, search, edit, and delete AI-curated snippets for any book through a dedicated Snippets page
**Depends on**: Phase 1
**Requirements**: NAV-01, NAV-02, BROW-02, BROW-03, BROW-04, BROW-05, BROW-06, EDIT-03, EXTR-01, EXTR-02, EXTR-03
**Success Criteria** (what must be TRUE):
  1. User can navigate to a top-level "Snippets" page from the main navigation and select any uploaded book to view its AI-curated snippets
  2. User sees snippet content with metadata (chapter title, page number, token count) and concept name badges per snippet
  3. User can search/filter snippets by text within the current book (client-side, no API call), and sees total token count for the selected book
  4. User sees a loading indicator during re-embedding operations and a clear error message if re-embedding fails (no silent data corruption)
  5. User sees a clear banner when a book is still processing, with editing disabled until processing completes
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Wave 0 test stubs: RED stubs for test_snippet_manager.py (BROW-02, BROW-03, EDIT-03, EXTR-03) and test_snippet_extraction.py (EXTR-01, EXTR-02)
- [ ] 02-02-PLAN.md — Backend foundation: migration 007, Snippet ORM model, extract_snippets() Stage 4, BookProcessingService persistence, retry_book() fix
- [ ] 02-03-PLAN.md — Snippet Manager API: GET/PATCH/DELETE /api/snippets router, Pydantic schemas, main.py wiring, GREEN tests
- [ ] 02-04-PLAN.md — Frontend SnippetManager: TypeScript types, api.tsx, constants, SnippetManager/SnippetCard/SnippetSearchBar components, Header/App wiring

### Phase 3: RAG Integration and Enrichment
**Goal**: Annotations and priority weights are fully wired into the RAG pipeline so they actually influence what agents retrieve and how they use it
**Depends on**: Phase 2
**Requirements**: ANNO-01, ANNO-02, ANNO-03, WGHT-01, WGHT-02, WGHT-03
**Success Criteria** (what must be TRUE):
  1. User can add, edit, and delete annotations on any chunk, and annotations marked "include in context" appear alongside chunk content in agent responses
  2. User can assign a numeric weight (0.1-10.0) to any chunk, and the weight visibly influences RAG retrieval ranking (effective_score = cosine_similarity * weight)
  3. Chunks with weight below 0.5 display a visual "rarely retrieved" warning in the Snippets UI
  4. Soft-deleted chunks (is_deleted=True) are excluded from all RAG retrieval queries across every retrieval path in the codebase

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Foundation and Data Safety | 3/3 | Complete   | 2026-03-05 |
| 2. Frontend Snippets Page | 2/4 | In Progress|  |
| 3. RAG Integration and Enrichment | 0/TBD | Not started | - |
