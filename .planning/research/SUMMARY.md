# Project Research Summary

**Project:** Screenwriting Assistant — Snippet Manager
**Domain:** RAG knowledge base management UI (chunk-level visibility and curation)
**Researched:** 2026-03-05
**Confidence:** HIGH

## Executive Summary

The Snippet Manager is a chunk-level curation interface layered on top of an existing RAG pipeline. Its core promise is letting users see, edit, annotate, and prioritize the text fragments that feed agent context — a feature category well-established in RAG platforms like Dify, Coze, and Pinecone Console. The right implementation strategy here is additive extension of the existing `BookChunk` model, not a new parallel data structure. Every dependency the feature needs already exists in the codebase: embedding service, RAG service, React Query, FastAPI patterns, and the `BookManager.tsx` component patterns. No new libraries or infrastructure are required.

The central technical risk is data integrity during editing. Every chunk edit requires three coordinated writes: content update, embedding regeneration, and token count recalculation — all in a single DB transaction. If any of these diverge (content updated but embedding stale, for example), RAG retrieval silently degrades with no error signal. A second critical risk is book reprocessing: the current `retry_book()` implementation deletes all chunks for a book unconditionally, which would silently destroy any user curation work. Both risks must be addressed in Phase 1 before any editing UI ships.

The recommended build order is backend foundation first (migration, model extensions, CRUD endpoints with transactional safety), then frontend (SnippetsPage following BookManager patterns), then RAG integration (weight scoring, annotation injection into agent context). The weight UI and RAG retrieval change must ship together — a weight column that the retrieval query ignores is worse than no weight feature at all, because it creates a false sense of control.

## Key Findings

### Recommended Stack

Zero new dependencies. The existing stack covers every requirement for this feature. Re-embedding on save should be synchronous (single `embed_text()` call, ~200ms) rather than background-queued — background processing introduces a stale-embedding window and silent failure risk that is not worth the marginal latency improvement for a single-chunk operation.

**Core technologies:**
- `embedding_service.embed_text()`: Re-embedding edited/created snippets — already exists, used synchronously in same DB transaction
- `tiktoken`: Token count recalculation on save — already in `requirements.txt`, cheap (~1ms per call)
- `<textarea>` (plain HTML): Inline editing — rich text editors add bundle size with zero benefit for plain-text embedding inputs
- `@dnd-kit/core`: Already in frontend dependencies but NOT recommended — use a numeric weight input instead (simpler, same RAG outcome)
- React Query `useQuery`/`useMutation`: Frontend data layer — follow `BookManager.tsx` patterns exactly
- FastAPI + SQLAlchemy: Backend API — follow `books.py` endpoint patterns exactly

**API pattern:** Nest snippets under the existing books resource (`/api/books/{book_id}/snippets`) matching the existing `/api/books/{book_id}/concepts` pattern. Server-side pagination (`?page=1&per_page=50`) is mandatory from day one.

### Expected Features

**Must have (table stakes):**
- List all chunks per book with pagination — books produce 400+ chunks; missing pagination freezes the browser
- Book selector / navigation — users have multiple books and must pick which to browse
- Chunk content preview with expandable full text — fundamental "see what your agent knows" promise
- Chunk metadata display (chapter title, page number, token count, chunk index) — all fields already on `BookChunk`
- Edit chunk text inline with re-embed on save — the core "control" feature; without it, the page is a debug view
- Delete a chunk — remove irrelevant or noisy content
- Add custom snippet (survives book reprocessing via `is_user_created` flag) — inject user-authored knowledge
- Search within snippets (frontend `Array.filter()`, no backend change) — nearly free given 50-200+ items per book
- Loading, error, and empty states — embedding ops take noticeable time; visual feedback is required

**Should have (differentiators):**
- Chunk annotations / notes — user context note passed alongside chunk to agent context
- Priority weighting — numeric weight influencing RAG retrieval score (must ship with RAG query change)
- Auto vs. custom visual badges — `is_user_created` flag drives a low-cost differentiator badge
- Token budget display — sum `token_count` across book's chunks; helps users understand context limits
- Chunk source highlighting — visual breadcrumb showing chapter/page; data already exists

**Defer to v2+:**
- Bulk delete (medium complexity, low MVP urgency)
- Semantic similarity preview ("what would the agent retrieve for this query?")
- Concept linkage display (requires JOIN on concept_ids lookup)
- Drag-and-drop reordering (complex for 100+ items; numeric weight achieves the same outcome)
- Chunk versioning / edit history
- Cross-book snippet merging

### Architecture Approach

Extend `BookChunk` in-place with five new columns (`is_user_created`, `is_deleted`, `weight`, `display_order`, `updated_at`) rather than creating a parallel snippets table. This preserves all four existing RAG query paths and all concept linkage relationships. Annotations go in a new `snippet_annotations` table (not a JSON column on `BookChunk`) because they have independent lifecycle and `include_in_context` must be SQL-queryable for efficient RAG filtering.

**Major components:**
1. `BookChunk` (extended) — stores chunk text, embedding, weight, custom flag, soft-delete, display order; foundation of RAG pipeline
2. `SnippetAnnotation` (new table) — user notes attached to specific chunks, injected into agent context when `include_in_context=True`
3. `SnippetService` (new) — CRUD ops, re-embedding orchestration, reorder logic; keeps endpoint handlers thin
4. `RAGService` (modified) — must be updated at 4 touchpoints to respect `is_deleted` filter, `weight` multiplier, and annotation injection
5. Frontend Snippets page (new) — follows `BookManager.tsx` card layout and React Query patterns exactly

**Strict build order dependency chain:** Migration runs first, SQLAlchemy models updated second, Pydantic schemas third, SnippetService fourth, `retry_book()` fix fifth, API endpoints sixth, frontend seventh, RAG integration eighth.

### Critical Pitfalls

1. **Stale embeddings after edit** — PATCH endpoint updates `content` without regenerating `embedding`, causing silent RAG degradation. Prevention: atomic transaction wrapping content update + `embed_text()` call + `token_count` recalculation. Must be solved before any editing UI ships.

2. **Book reprocessing destroys user work** — `retry_book()` deletes all `BookChunk` rows unconditionally. Any custom snippets or edited chunks are silently lost. Prevention: add `is_user_created` and check `updated_at` before deletion; preserve user-modified chunks across reprocessing. Must be in Phase 1 migration.

3. **Weight column with no retrieval effect** — `weight` field in the DB does nothing unless `rag_service.semantic_search()` is updated to use `effective_score = similarity * weight`. Shipping weight UI without the RAG query change creates false user confidence. Prevention: weight UI and RAG retrieval change must ship in the same phase.

4. **Embedding API failure leaves content/embedding out of sync** — network error or OpenAI rate limit during save causes content to be updated but embedding to remain stale. Prevention: transactional rollback — if `embed_text()` fails, roll back the content change and return a clear error to the frontend. Non-negotiable for Phase 1.

5. **UI freeze on large books** — 400-600 chunks without server-side pagination returns a payload that freezes the browser. Prevention: `?page=1&per_page=50` on the list endpoint, built in from day one. Never return all chunks in a single response.

## Implications for Roadmap

Based on research, the dependency graph points to a strict three-phase ordering. Backend safety must come before frontend exposure, and RAG pipeline changes must come after the data exists to drive them.

### Phase 1: Backend Foundation and Safety

**Rationale:** Frontend cannot be built without working endpoints; the critical data-integrity pitfalls (stale embeddings, reprocessing data loss) must be solved before any editing UI is exposed to users. This phase has no external dependencies — it's all within the existing codebase.

**Delivers:** A fully safe, tested API for snippet CRUD that frontend can build against.

**Addresses features:** List chunks (paginated), create custom snippet, edit chunk text (with atomic re-embed), delete chunk, book selector API support.

**Avoids pitfalls:** Stale embeddings (#1), reprocessing destroys user work (#2), concept_ids staleness (#3), embedding API failure leaving data inconsistent (#7), token count mismatch (#8), chunk_index collision (#6), pagination freeze (#5).

**Key tasks:**
- Write migration `006_snippet_management.sql` (5 new columns on `book_chunks`, `snippet_annotations` table, indexes)
- Update `BookChunk` SQLAlchemy model + add `SnippetAnnotation` model
- Update Pydantic schemas (`SnippetResponse`, `CreateSnippetRequest`, `UpdateSnippetRequest`)
- Create `SnippetService` (CRUD + transactional re-embedding)
- Fix `retry_book()` to preserve `is_user_created` and user-edited chunks
- Create snippet API endpoints (extend `books.py` or new `snippets.py`)
- Register routes in `main.py`
- Write backend tests
- Research flag: STANDARD — follows established FastAPI + SQLAlchemy patterns, no research phase needed

### Phase 2: Frontend Snippets Page

**Rationale:** Once the API is stable and tested, the frontend can be built against it. Frontend patterns are fully established in `BookManager.tsx` and `CardGridView.tsx` — this is assembly work, not design work.

**Delivers:** A usable Snippets page where users can browse, search, edit, delete, and add custom snippets for any book.

**Addresses features:** All table-stakes features listed above plus frontend-only search filter, loading/error/empty states, book processing status banner, debounced save to prevent race conditions.

**Avoids pitfalls:** Race conditions on rapid edits (#12), showing editable UI during book processing (#13).

**Key tasks:**
- Add `/snippets` route to `App.tsx` and navigation
- Create `SnippetsPage` component (book selector)
- Create `SnippetList` component (paginated, with search filter)
- Create `SnippetCard` component (preview + expand + metadata badges)
- Create `SnippetEditor` component (inline textarea with debounced save/cancel)
- React Query hooks for all snippet CRUD mutations
- Empty state, loading state, processing-state banner
- Research flag: STANDARD — `BookManager.tsx` is the established pattern, no research phase needed

### Phase 3: RAG Integration and Enrichment

**Rationale:** RAG modifications touch existing, working code paths and must come after the data (weight, annotations) exists to drive them. Weight UI and RAG query change must ship together — they are atomic from a user-trust perspective.

**Delivers:** Snippet weight actually influences agent retrieval; annotations appear in agent context; auto vs. custom badges visible; token budget display.

**Addresses features:** Priority weighting (with effective retrieval), chunk annotations injected into agent context, auto vs. custom badges, token budget display.

**Avoids pitfalls:** Weight with no retrieval effect (#4), annotation text not passed to agent context (#10), weight = 0 making chunks permanently unretrievable (#11).

**Key tasks:**
- Modify `rag_service.semantic_search()` — add `is_deleted=false` filter, weight-adjusted score
- Modify `retrieve_relevant_concepts()` — add `is_deleted=false` filter
- Modify `agent_service.format_agent_context()` — inject annotations where `include_in_context=True`
- Add annotation UI within `SnippetCard`
- Add numeric weight input with validation (min 0.1, max 10.0)
- Add auto vs. custom visual badges
- Add token budget summary stat
- End-to-end test: edit snippet → verify agent uses updated content
- Research flag: NEEDS REVIEW — modifies the live RAG pipeline; recommend careful integration testing before shipping

### Phase Ordering Rationale

- Backend must precede frontend because the frontend has no endpoints to call before Phase 1 completes
- `retry_book()` safety fix must happen before any user-created snippet data exists — if it ships after Phase 2, users can lose work
- Weight and annotation features cannot precede the DB migration that adds those columns
- RAG pipeline modifications should be last because they touch the most critical existing code (agent retrieval quality) and require the Phase 1 + Phase 2 data model to be stable
- The `is_deleted` filter in Phase 3 is also needed in Phase 1 to be correct from day one — add it to the migration but wire it into RAG queries in Phase 3 as a batch change

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (RAG Integration):** Modifying `rag_service.semantic_search()` with weight scoring changes retrieval behavior for all books, not just snippets-enabled books. Recommend reviewing all 4 touchpoints in `rag_service.py` before writing the implementation plan to confirm no edge cases (e.g., books with no weight column data before migration backfill).

Phases with standard patterns (skip research phase):
- **Phase 1 (Backend):** Direct extension of existing `books.py` and `embedding_service.py` patterns. Well-understood FastAPI + SQLAlchemy + PostgreSQL work.
- **Phase 2 (Frontend):** Direct extension of `BookManager.tsx` and `CardGridView.tsx` patterns. React Query mutations and Tailwind styling are established throughout the codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Grounded in direct codebase analysis; all dependencies confirmed present in `requirements.txt` and `package.json` |
| Features | MEDIUM | Based on Dify, Coze, Pinecone Console, Flowise, LangFlow pattern analysis — no user research data |
| Architecture | HIGH | Grounded in direct codebase analysis of `rag_service.py`, `book_processing_service.py`, `BookChunk` model, and existing endpoint patterns |
| Pitfalls | HIGH | Grounded in direct codebase analysis of `retry_book()`, RAG query paths, and existing embedding service usage |

**Overall confidence:** HIGH

### Gaps to Address

- **Feature prioritization within Phase 2:** The MEDIUM confidence on features means the ordering of Phase 2 sub-features (e.g., annotations vs. weight vs. badges) should be validated against user priorities during requirements definition. The research gives a technically-grounded order but not a user-validated one.
- **Weight scoring formula:** `effective_score = similarity * weight` is the recommended formula, but this is an inference from the pattern. The exact formula (multiplicative vs. additive) should be validated against the existing cosine similarity score range in `rag_service.py` before implementation.
- **Annotation context format:** The format `[SNIPPET]\n{content}\n[NOTE: {annotation}]` is a recommendation based on common RAG context patterns. The actual format should be tested with GPT-4 prompting to confirm annotation text is correctly interpreted by the agent.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — `backend/app/services/rag_service.py`, `book_processing_service.py`, `embedding_service.py`, `models/database.py`
- Direct codebase analysis — `frontend/src/components/Books/BookManager.tsx`, `CardGridView.tsx`, `api.tsx`
- Existing migration files — `migrations/003_template_system.sql`, `004_agent_type_and_quality.sql`, `005_book_progress.sql` (established migration patterns)

### Secondary (MEDIUM confidence)
- Dify RAG management UI patterns — chunk listing, annotation, weight controls
- Pinecone Console — chunk-level visibility and metadata display conventions
- Coze knowledge base UI — book selector and chunk management patterns
- Flowise / LangFlow — RAG pipeline management reference patterns

### Tertiary (LOW confidence)
- Weight scoring formula (`similarity * weight`) — inferred from common RAG literature; needs validation against actual cosine similarity score range in production data

---
*Research completed: 2026-03-05*
*Ready for roadmap: yes*
