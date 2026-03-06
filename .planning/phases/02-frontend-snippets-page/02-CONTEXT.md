# Phase 2: Frontend Snippets Page - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning
**Source:** Design decision from conversation

<domain>
## Phase Boundary

This phase delivers a dedicated Snippets page where writers can browse, search, edit, and delete AI-curated snippets for any book. Snippets are distinct from raw BookChunk records (used internally for RAG). They are curated passages extracted by the AI during book processing.

</domain>

<decisions>
## Implementation Decisions

### Snippets are a Separate Entity from BookChunks
- `BookChunk` = mechanical text splits for RAG retrieval (internal system concern)
- `Snippet` = AI-curated key passages selected during knowledge extraction (user-facing)
- The Snippets page shows `Snippet` records, NOT `BookChunk` records
- A new `Snippet` model and DB table is required

### Snippet Creation is Automated — No Manual UI Form
- Snippets are created exclusively by the AI during the book processing pipeline
- There is NO "Add Snippet" button or `CreateSnippetForm` in the UI
- Users can browse, edit content, and delete snippets — but NOT create them
- The `is_user_created` concept is obsolete; all snippets are AI-authored

### AI Snippet Extraction During Knowledge Extraction
- A new extraction stage runs inside `knowledge_extraction_service.py` (or `book_processing_service.py`)
- After concept extraction, the AI identifies N key passages per chapter that best illustrate the concepts
- These passages are stored as `Snippet` records linked to the book
- The extraction leverages the same OpenAI call infrastructure already in place

### API Endpoints
- New `/api/snippets` endpoints backed by the `Snippet` table (not `BookChunk`)
- Existing BookChunk endpoints remain unchanged (still needed for RAG)

### Frontend SnippetManager
- Book selector dropdown → loads snippets for selected book
- List of snippets with: content, chapter title, page number, token count
- Inline edit (per-snippet loading/error feedback)
- Delete with confirmation
- Client-side text search filter (no API call on keystroke)
- Total token count (does not change when filter is active)
- Processing banner when book is not yet COMPLETED (no edit/delete)
- NO create form

### Claude's Discretion
- Number of snippets to extract per chapter (implementation detail for AI prompt)
- Snippet DB schema field names (beyond the obvious ones)
- Whether snippets get embeddings (reasonable to embed them for future search)
- Exact AI prompt for snippet extraction

</decisions>

<specifics>
## Specific Ideas

- The existing `knowledge_extraction_service.py` has a clean 3-stage pipeline (concepts → analysis → relationships). Snippet extraction should be a 4th stage or integrated into stage 2 (after concept analysis, use the concept + chapter text to pick the best illustrative passages).
- Snippets should be linked to `concept_ids` (the concepts they illustrate) — mirrors how BookChunk records link to concepts.
- The processing pipeline already has a status progression: PENDING → EXTRACTING → ANALYZING → EMBEDDING → COMPLETED. Snippet extraction fits within ANALYZING.

</specifics>

<deferred>
## Deferred Ideas

- User-created custom snippets (explicitly removed — was CUST-01/CUST-02/CUST-03)
- Annotations on snippets (ANNO-01/02/03 — v2)
- Priority weighting (WGHT-01/02/03 — v2)

</deferred>

---

*Phase: 02-frontend-snippets-page*
*Context gathered: 2026-03-05 via design decision conversation*
