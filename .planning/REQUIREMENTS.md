# Requirements: Screenwriting Assistant — Snippet Manager

**Defined:** 2026-03-05
**Core Value:** Writers have full visibility and control over what book knowledge their AI agents use, so they can trust and tune the context instead of treating it as a black box.

## v1 Requirements

### Navigation

- [x] **NAV-01**: User can access a top-level "Snippets" page from the main navigation
- [x] **NAV-02**: User can select a book from a dropdown on the Snippets page to view its chunks

### Snippet Browsing

- [ ] **BROW-01**: User can view all snippets for a selected book, paginated (50 per page)
- [x] **BROW-02**: User can see snippet content preview with chapter title, page number, and token count per snippet
- [x] **BROW-03**: User can see which concept(s) each snippet illustrates (via concept name label)
- [x] **BROW-04**: User can search/filter snippets by text within the current book (frontend filter, no API call)
- [x] **BROW-05**: User sees a clear message when a book is still processing (editing disabled until complete)
- [x] **BROW-06**: User can see the total token count across all snippets for the selected book

### Snippet Editing

- [ ] **EDIT-01**: User can edit the text content of any chunk inline; changes persist permanently
- [x] **EDIT-02**: Editing a chunk's content triggers re-embedding automatically (atomic: content + embedding + token count updated together)
- [x] **EDIT-03**: User sees a loading indicator while re-embedding is in progress, and an error message if it fails (with no data corruption — rollback if embed fails)
- [x] **EDIT-04**: User can delete a chunk; deleted chunks are excluded from all future agent context retrieval

### Snippet Extraction (Backend)

- [x] **EXTR-01**: During book processing (knowledge extraction phase), the AI identifies and stores N key passages per chapter as `Snippet` records — distinct from raw `BookChunk` records
- [x] **EXTR-02**: Each `Snippet` is linked to the concept(s) it best illustrates (via concept_ids) and gets an embedding for future semantic search
- [x] **EXTR-03**: Snippets are created automatically; there is no user-facing snippet creation form

### Annotations

- [ ] **ANNO-01**: User can add a note/annotation to any chunk
- [ ] **ANNO-02**: User can edit or delete an annotation
- [ ] **ANNO-03**: Annotations marked "include in context" are passed alongside chunk content to agent context in the format: chunk text + [NOTE: annotation text]

### Priority Weighting

- [ ] **WGHT-01**: User can assign a numeric weight (0.1–10.0, default 1.0) to any chunk
- [ ] **WGHT-02**: Weight influences RAG retrieval ranking: effective_score = cosine_similarity * weight
- [ ] **WGHT-03**: Chunks with weight below 0.5 display a visual warning ("rarely retrieved")

## v2 Requirements

### Bulk Operations

- **BULK-01**: User can select multiple chunks and delete them at once
- **BULK-02**: User can bulk-update weights via a range selector

### Advanced Discovery

- **DISC-01**: User can test "what would the agent retrieve for this query?" — semantic similarity preview scoped to one book
- **DISC-02**: User can view which extracted concepts are linked to each chunk

## Out of Scope

| Feature | Reason |
|---------|--------|
| Chunk versioning / edit history | Adds DB complexity for low MVP value; retry-from-scratch is sufficient revert |
| Bulk import of custom snippets | One-at-a-time sufficient for initial use; CSV/JSON parsing adds scope |
| Cross-book snippet merging | Complicates data model and provenance tracking |
| Real-time collaboration | Single-user MVP |
| Drag-and-drop chunk reordering | Replaced by numeric weight input — same RAG outcome, simpler UI |
| Embedding visualization | Low actionable value for screenwriters |
| Automatic re-chunking settings | Power-user feature; use existing retry-from-scratch on Book |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NAV-01 | Phase 2 | Complete |
| NAV-02 | Phase 2 | Complete |
| BROW-01 | Phase 1 | Pending |
| BROW-02 | Phase 2 | Complete |
| BROW-03 | Phase 2 | Complete |
| BROW-04 | Phase 2 | Complete |
| BROW-05 | Phase 2 | Complete |
| BROW-06 | Phase 2 | Complete |
| EDIT-01 | Phase 1 | Pending |
| EDIT-02 | Phase 1 | Complete |
| EDIT-03 | Phase 2 | Complete |
| EDIT-04 | Phase 1 | Complete |
| EXTR-01 | Phase 2 | Complete |
| EXTR-02 | Phase 2 | Complete |
| EXTR-03 | Phase 2 | Complete |
| ANNO-01 | Phase 3 | Pending |
| ANNO-02 | Phase 3 | Pending |
| ANNO-03 | Phase 3 | Pending |
| WGHT-01 | Phase 3 | Pending |
| WGHT-02 | Phase 3 | Pending |
| WGHT-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after roadmap creation*
