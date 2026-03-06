# Phase 2: Frontend Snippets Page - Research

**Researched:** 2026-03-05
**Domain:** React/TypeScript frontend + FastAPI backend — Snippet entity, AI extraction pipeline, and SnippetManager UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Snippets are a SEPARATE entity from BookChunks — new `Snippet` DB table required
- Snippet creation is AUTOMATED — AI creates them during knowledge extraction; NO manual UI creation form
- Frontend SnippetManager shows `Snippet` records (not BookChunks); users can browse, edit, delete
- New backend extraction stage: after concept analysis, AI identifies key passages per chapter → stored as Snippets linked to concepts
- New `/api/snippets` endpoints backed by Snippet table (existing BookChunk endpoints unchanged)
- Frontend SnippetManager: book selector dropdown, list view, inline edit, delete with confirmation, client-side search, total token count, processing banner, no create form

### Claude's Discretion
- Number of snippets to extract per chapter (implementation detail for AI prompt)
- Snippet DB schema field names (beyond obvious ones)
- Whether snippets get embeddings (reasonable to embed for future search)
- Exact AI prompt for snippet extraction

### Deferred Ideas (OUT OF SCOPE)
- User-created custom snippets (CUST-01/CUST-02/CUST-03 explicitly removed)
- Annotations on snippets (ANNO-01/02/03 — v2)
- Priority weighting (WGHT-01/02/03 — v2)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NAV-01 | User can access a top-level "Snippets" page from the main navigation | Header.tsx adds nav link; App.tsx adds route `/snippets` |
| NAV-02 | User can select a book from a dropdown on the Snippets page to view its snippets | `useQuery` fetches `/api/books/`; book selector `<select>` controls state |
| BROW-02 | User can see snippet content preview with chapter title, page number, and token count per snippet | Snippet record carries these fields; rendered per-card in SnippetManager |
| BROW-03 | User can see which concept(s) each snippet illustrates (via concept name label) | Snippet stores `concept_ids` as JSON; concepts looked up from Concept table in list endpoint |
| BROW-04 | User can search/filter snippets by text within current book (frontend filter, no API call) | `useMemo` filter on fetched list, search input with no debounce-to-server |
| BROW-05 | User sees a clear message when a book is still processing (editing disabled until complete) | Book.status !== 'completed' → banner + disabled edit/delete buttons |
| BROW-06 | User can see total token count across all snippets for selected book | Sum from unfiltered list (not filtered), displayed persistently |
| EDIT-03 | User sees loading indicator during re-embedding and error message if it fails (no data corruption) | Per-snippet `isPending` state + optimistic rollback via React Query mutation |
| EXTR-01 | During book processing, AI identifies and stores N key passages per chapter as `Snippet` records | New `extract_snippets()` method in `KnowledgeExtractionService`; called in `BookProcessingService.process_book()` after concept analysis |
| EXTR-02 | Each Snippet is linked to concept(s) it best illustrates and gets an embedding | `concept_ids` JSON array on Snippet model; `embedding_service.embed_text()` called per snippet |
| EXTR-03 | Snippets are created automatically; no user-facing creation form | No POST /api/snippets endpoint in the new router; list/PATCH/DELETE only |
</phase_requirements>

---

## Summary

Phase 1 delivered a fully tested snippets router that operates on `BookChunk` records and a working test infrastructure (SQLite + VectorAsText + mock_embed). Phase 2 must build on this by: (1) creating a new `Snippet` table and ORM model distinct from `BookChunk`, (2) adding a 4th extraction stage to the book processing pipeline that uses the existing `KnowledgeExtractionService._call_ai()` infrastructure to identify key passages, and (3) building a SnippetManager React page that is wired into the top-level navigation.

The critical architectural finding is that Phase 1 shipped endpoints under `/api/books/{book_id}/snippets` that operate on `BookChunk` records. Phase 2 introduces a completely separate `Snippet` entity with its own DB table and endpoints at `/api/snippets`. The two systems coexist — `BookChunk` remains unchanged for RAG, while `Snippet` is user-facing. A new DB migration is required.

The frontend gap discovered during research: `api.pauseBook()`, `api.resumeBook()`, and `api.retryBook()` are called in `BookManager.tsx` but are not defined in the current `api.tsx`. These must be added when wiring the Snippets page (since `api.tsx` will be modified anyway), but they are pre-existing bugs not introduced by Phase 2.

**Primary recommendation:** Implement in two plans — Plan 1: backend (Snippet model, migration 007, extraction stage, API router); Plan 2: frontend (SnippetManager page, Header/App wiring, api.tsx additions, concept-name display).

---

## Standard Stack

### Core (confirmed from codebase)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React Query (`@tanstack/react-query`) | 5.x (package.json) | Server state, mutations with loading/error | Already used everywhere in the project |
| FastAPI | (existing) | Backend router for `/api/snippets` | Project standard |
| SQLAlchemy | 2.x (existing) | ORM for Snippet model | Project standard |
| tiktoken | (existing) | Token counting on edit | Already imported in `snippets.py` |
| Tailwind CSS | (existing) | Styling | Project standard |
| Radix UI | (existing) | Accessible primitives if needed | Project standard |
| lucide-react | (existing) | Icons (Search, Edit2, Trash2, Loader2) | Already used in BookManager |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `embedding_service.embed_text()` | existing | Embed snippet on extraction and edit | Called in extraction pipeline and edit endpoint |
| `KnowledgeExtractionService._call_ai()` | existing | AI calls with retry | Reuse for snippet extraction prompt |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate `Snippet` table | Reuse `BookChunk` | Context.md locks separate entity — do not reconsider |
| Client-side text filter | Server-side search API | Context.md locks client-side — no API call on keystroke |

**Installation:** No new packages required. All dependencies already installed.

---

## Architecture Patterns

### Recommended Project Structure — New Files

```
backend/
  migrations/
    007_snippets_table.sql       # New Snippet table + indexes
  app/
    models/
      database.py                # Add Snippet ORM model
    services/
      knowledge_extraction_service.py  # Add extract_snippets() stage
    api/
      endpoints/
        snippet_manager.py       # New router: GET/PATCH/DELETE /api/snippets/*

frontend/
  src/
    types/
      index.ts                   # Add Snippet, SnippetListResponse types
    lib/
      api.tsx                    # Add snippetApi section + fix pauseBook/resumeBook/retryBook
      constants.ts               # Add QUERY_KEYS.SNIPPETS, ROUTES.SNIPPETS
    components/
      Snippets/
        SnippetManager.tsx       # Main page component
        SnippetCard.tsx          # Per-snippet row with inline edit
        SnippetSearchBar.tsx     # Client-side search input
```

### Pattern 1: Snippet DB Schema

**What:** New `snippets` table, separate from `book_chunks`. Linked to book via FK, concepts via JSON array (same pattern as `book_chunks.concept_ids`).

**Fields:**
```sql
CREATE TABLE snippets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_title VARCHAR(500),
    page_number INTEGER,
    content TEXT NOT NULL,
    justification TEXT,           -- AI's reason for selecting this passage
    concept_ids JSONB DEFAULT '[]', -- concept UUIDs this illustrates
    concept_names JSONB DEFAULT '[]', -- denormalized names for display (avoids JOIN)
    token_count INTEGER DEFAULT 0,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_snippets_book ON snippets(book_id);
CREATE INDEX idx_snippets_not_deleted ON snippets(book_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_snippets_embedding ON snippets USING hnsw (embedding vector_cosine_ops);
```

**Rationale for `concept_names` denormalization:** The list endpoint needs concept names for display (BROW-03). Doing a JOIN or N+1 queries per snippet is slow. Storing names alongside IDs at extraction time is correct since concept names are stable (never edited). This mirrors the pattern already used in `BookChunk.concept_ids`.

**Confidence:** HIGH — modeled directly on existing migration patterns and `BookChunk` schema.

### Pattern 2: Snippet ORM Model (database.py)

```python
# Source: existing BookChunk model as template
class Snippet(Base):
    __tablename__ = "snippets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False, index=True)
    chapter_title = Column(String(500))
    page_number = Column(Integer)
    content = Column(Text, nullable=False)
    justification = Column(Text)
    concept_ids = Column(JSON, default=list)
    concept_names = Column(JSON, default=list)
    token_count = Column(Integer, default=0)
    embedding = deferred(Column(SafeVector(1536)))
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    book = sa_relationship("Book", back_populates="snippets")
```

Also add `snippets` relationship to the `Book` model:
```python
snippets = sa_relationship("Snippet", back_populates="book", cascade="all, delete-orphan")
```

### Pattern 3: Snippet Extraction Stage in KnowledgeExtractionService

**Where it fits:** Stage 4 in `KnowledgeExtractionService.process_chapter()` — after concept analysis is complete and enriched concepts are available. Called with chapter text + enriched concept list.

**Input:** chapter text (truncated to ~10000 chars), list of concept names + definitions from Stage 1+2.
**Output:** 3-5 passages with justification and which concept each illustrates.

**Recommended count:** 3-5 snippets per chapter. Rationale: "Save the Cat" has ~16 chapters × 4 snippets = ~64 snippets per book — manageable. More than 5 per chapter creates noise; fewer than 3 may miss key passages.

```python
# Source: pattern from existing _call_ai() infrastructure
async def extract_snippets(
    self,
    chapter_text: str,
    chapter_title: str,
    book_title: str,
    concepts: List[Dict],
) -> List[Dict]:
    """Stage 4: Identify 3-5 key passages that best illustrate the extracted concepts."""
    if not concepts:
        return []

    concept_summary = "\n".join(
        f"- {c['name']}: {c['definition'][:100]}" for c in concepts
    )

    system_prompt = """You are a knowledge curation specialist. Given a chapter from a screenwriting book and its extracted concepts, identify the 3-5 most illuminating passages that best illustrate these concepts.

For each passage, extract the EXACT text from the chapter (do not paraphrase or summarize). Choose passages that:
- Directly define, demonstrate, or exemplify a specific concept
- Are self-contained and understandable without surrounding context
- Are 50-300 words in length (long enough to be meaningful, short enough to be scannable)

Return a JSON object with:
{
  "snippets": [
    {
      "content": "The exact passage text from the chapter",
      "concept_name": "The concept this passage best illustrates (exact name from the list)",
      "justification": "1-2 sentence explanation of why this passage was chosen"
    }
  ]
}

Return 3-5 snippets. Quality over quantity."""

    user_prompt = f"""Book: "{book_title}"
Chapter: "{chapter_title}"

Extracted concepts from this chapter:
{concept_summary}

Chapter text:
{chapter_text[:10000]}"""

    try:
        result = await self._call_ai(system_prompt, user_prompt)
        return result.get("snippets", [])
    except Exception as e:
        logger.error(f"Snippet extraction failed for chapter '{chapter_title}': {e}")
        return []
```

### Pattern 4: Integration in process_chapter()

Append Stage 4 to the existing `process_chapter()` return value:

```python
async def process_chapter(self, chapter_text, chapter_title, book_title) -> Dict:
    # ... existing stages 1-3 ...

    # Stage 4: Extract key snippets
    snippets = await self.extract_snippets(
        chapter_text=chapter_text,
        chapter_title=chapter_title,
        book_title=book_title,
        concepts=enriched_concepts,
    )
    logger.info(f"  Found {len(snippets)} snippets in '{chapter_title}'")

    return {
        "concepts": enriched_concepts,
        "relationships": relationships,
        "snippets": snippets,  # NEW
    }
```

Then in `BookProcessingService.process_book()`, after the chapter loop, persist snippets:

```python
# After all_concepts and all_relationships are collected:
# Persist snippets with embeddings
all_raw_snippets = []
for chapter_result in chapter_results:
    all_raw_snippets.extend(chapter_result.get("snippets", []))

# Embed all snippet contents in one batch call
if all_raw_snippets:
    snippet_texts = [s["content"] for s in all_raw_snippets]
    snippet_embeddings = await embedding_service.embed_batch(snippet_texts)

    for raw_snippet, emb in zip(all_raw_snippets, snippet_embeddings):
        # Look up concept UUID by name
        concept_db = concept_name_to_db.get(raw_snippet.get("concept_name"))
        concept_ids = [str(concept_db.id)] if concept_db else []
        concept_names = [concept_db.name] if concept_db else []

        db_snippet = Snippet(
            book_id=book_id,
            chapter_title=raw_snippet.get("chapter_title"),  # injected by caller
            content=raw_snippet["content"],
            justification=raw_snippet.get("justification"),
            concept_ids=concept_ids,
            concept_names=concept_names,
            token_count=_count_tokens(raw_snippet["content"]),
            embedding=emb,
        )
        db.add(db_snippet)
    db.commit()
```

**Note:** `chapter_title` must be injected from the caller into each raw snippet because the extraction prompt returns snippets without chapter context. The caller (process_book loop) already has `chapter.get("title")` — inject it before appending to `all_raw_snippets`.

### Pattern 5: Snippet API Router

New file: `backend/app/api/endpoints/snippet_manager.py`
Mounted at `/api/snippets` (NOT under `/api/books` — separate resource).

```python
# Endpoints:
# GET    /api/snippets?book_id={uuid}&page=1&per_page=50
# PATCH  /api/snippets/{snippet_id}    body: {"content": "..."}
# DELETE /api/snippets/{snippet_id}
```

**No POST endpoint** — snippets are AI-created only (EXTR-03).

The list endpoint returns snippets with `concept_names` inline so the frontend never needs a second API call for concept names (BROW-03).

### Pattern 6: Frontend SnippetManager Page

```typescript
// frontend/src/components/Snippets/SnippetManager.tsx

// State:
const [selectedBookId, setSelectedBookId] = useState<string | null>(null);
const [searchQuery, setSearchQuery] = useState('');
const [editingId, setEditingId] = useState<string | null>(null);
const [editContent, setEditContent] = useState('');

// Data fetching:
const { data: books = [] } = useQuery({ queryKey: [QUERY_KEYS.BOOKS], queryFn: api.getBooks });
const selectedBook = books.find(b => b.id === selectedBookId);
const isProcessing = selectedBook && selectedBook.status !== 'completed';

const { data: snippetData } = useQuery({
  queryKey: [QUERY_KEYS.SNIPPETS, selectedBookId],
  queryFn: () => api.getSnippets(selectedBookId!, { page: 1, per_page: 200 }),
  enabled: !!selectedBookId,
});

// Client-side filter (BROW-04):
const filteredSnippets = useMemo(() => {
  if (!searchQuery.trim()) return snippetData?.items ?? [];
  const q = searchQuery.toLowerCase();
  return (snippetData?.items ?? []).filter(s =>
    s.content.toLowerCase().includes(q) ||
    s.chapter_title?.toLowerCase().includes(q)
  );
}, [snippetData?.items, searchQuery]);

// Total token count (BROW-06) — based on UNFILTERED list:
const totalTokens = useMemo(
  () => (snippetData?.items ?? []).reduce((sum, s) => sum + s.token_count, 0),
  [snippetData?.items]
);

// Edit mutation (EDIT-03):
const editMutation = useMutation({
  mutationFn: ({ id, content }: { id: string; content: string }) =>
    api.editSnippet(id, content),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SNIPPETS, selectedBookId] });
    setEditingId(null);
  },
});

// Delete mutation:
const deleteMutation = useMutation({
  mutationFn: (id: string) => api.deleteSnippet(id),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SNIPPETS, selectedBookId] });
  },
});
```

### Pattern 7: Processing Banner (BROW-05)

```tsx
{isProcessing && (
  <div className="flex items-center gap-2 px-4 py-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-sm text-amber-400 mb-4">
    <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
    <span>
      This book is still processing ({selectedBook.processing_step ?? selectedBook.status}).
      Snippets are being extracted — editing is disabled until processing completes.
    </span>
  </div>
)}
```

Edit and delete buttons receive `disabled={isProcessing || editMutation.isPending}`.

### Pattern 8: Inline Edit with Per-Snippet Loading (EDIT-03)

```tsx
// Per SnippetCard:
const isEditing = editingId === snippet.id;
const isSaving = editMutation.isPending && editingId === snippet.id;

// Show Loader2 spinner inside Save button when isSaving
// Show error message below content area if editMutation.isError && editingId === snippet.id
```

### Anti-Patterns to Avoid

- **Filtering total token count:** BROW-06 explicitly states total does NOT change when filter is active. Count from `snippetData.items` (full list), not `filteredSnippets`.
- **Putting snippets under `/api/books/{id}/snippets`:** That path is already used by the Phase 1 BookChunk router. Use `/api/snippets?book_id={id}` instead.
- **Sharing the Snippet router prefix with the BookChunk snippets router:** Both are mounted in `main.py` — they must use different prefixes. Mount new router at `/api/snippets`.
- **N+1 concept name lookups in list endpoint:** Return `concept_names` from the denormalized column on the Snippet record itself — no JOIN needed.
- **Embedding in extraction prompt loop:** Batch all snippet embeddings in one `embed_batch()` call after the chapter loop, not one-by-one inside the chapter processing.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | Custom tokenizer | `tiktoken` (already in snippets.py) | Edge cases in GPT-4 tokenization |
| Text embedding | Direct OpenAI calls | `embedding_service.embed_batch()` | Rate limit handling, caching, retry logic already built |
| AI JSON responses | Raw string parsing | `_call_ai()` with json_mode=True | Retry logic (5 attempts), exponential backoff already in KnowledgeExtractionService |
| Optimistic UI | Manual state rollback | React Query `useMutation` | `onError` callback auto-reverts; `isPending` drives loading state |
| UUID generation | `str(uuid.uuid4())` | SQLAlchemy `default=uuid.uuid4` | Column-level default handles this |

**Key insight:** The existing `_call_ai()` method in `KnowledgeExtractionService` handles all the complexity of OpenAI JSON-mode calls. The extraction prompt is the only truly new code required.

---

## Common Pitfalls

### Pitfall 1: Chapter Title Not Available in Snippet Output
**What goes wrong:** The AI extraction prompt returns snippets without chapter_title because the prompt doesn't ask for it — the AI doesn't know which chapter it's in.
**Why it happens:** Each `extract_snippets()` call processes one chapter, but the returned JSON omits chapter context.
**How to avoid:** After calling `extract_snippets()`, inject `chapter_title` into each returned snippet dict before appending to `all_raw_snippets`: `s["chapter_title"] = chapter.get("title", "Untitled")`.
**Warning signs:** Snippet records in DB have NULL chapter_title despite the chapter having a title.

### Pitfall 2: Snippet Router URL Collision with Phase 1 BookChunk Router
**What goes wrong:** If the new Snippet router is mounted at `/api/books`, its routes will collide with the existing Phase 1 snippets router mounted at the same prefix.
**Why it happens:** `main.py` already has `app.include_router(snippets.router, prefix="/api/books", tags=["snippets"])`. Adding another router under `/api/books` creates ambiguous routing.
**How to avoid:** Mount the new Snippet Manager router at `/api/snippets` (not `/api/books`). Use query param `?book_id=...` instead of path param for book scoping.
**Warning signs:** 404 on `/api/snippets` endpoints or 422 on `/api/books` endpoints after adding the new router.

### Pitfall 3: Missing `pauseBook`/`resumeBook`/`retryBook` in api.tsx
**What goes wrong:** `BookManager.tsx` calls `api.pauseBook()`, `api.resumeBook()`, `api.retryBook()` but these methods are absent from the current `api.tsx`. TypeScript compiles but the app throws runtime errors when these buttons are clicked.
**Why it happens:** These methods exist in the `.bak` version of api.tsx but were not carried forward in the rewrite.
**How to avoid:** Add the three missing methods to `api.tsx` in Plan 2 when the file is modified anyway.
**Warning signs:** TypeScript error "Property 'pauseBook' does not exist on type..." or runtime "api.pauseBook is not a function".

### Pitfall 4: Total Token Count Reflects Filtered List
**What goes wrong:** Computing total tokens from `filteredSnippets` instead of `snippetData.items` causes the count to drop as the user types in search.
**Why it happens:** Intuitive to use the same array driving the render — but BROW-06 explicitly says "does not change when filter is active."
**How to avoid:** Two separate `useMemo` computations — one for `filteredSnippets` (drives render), one for `totalTokens` (always uses `snippetData?.items`).

### Pitfall 5: SQLite Test Engine Breaks on `Snippet` Table with SafeVector
**What goes wrong:** Adding the `Snippet` model with `SafeVector(1536)` column breaks the existing `conftest.py` test engine because `_patch_uuid_columns_for_sqlite()` must also replace `SafeVector` on the new `snippets` table.
**Why it happens:** The existing `conftest.py` already patches `SafeVector` for all tables in `Base.metadata`. Since `Snippet` uses the same base, it will be patched automatically IF the model is imported before the engine is created.
**How to avoid:** Ensure `Snippet` is imported in `database.py` before test engine creation. The existing conftest loop `for table in Base.metadata.tables.values()` already handles all registered tables.
**Warning signs:** `OperationalError: no such column type: vector` in tests after adding the Snippet model.

### Pitfall 6: Embedding the Same Snippet Twice (Extraction vs. Edit)
**What goes wrong:** The `edit_snippet` endpoint in the new router calls `embed_text()` on save — fine. But if extraction also embeds via `embed_batch()`, ensure there's no double-embed on the extraction path.
**Why it happens:** If `extract_snippets()` were to call `embed_text()` per snippet inside the AI loop rather than via a batch call after the loop.
**How to avoid:** Embed ALL snippets for a book in one `embed_batch()` call after the full chapter loop in `process_book()` — same pattern as chunk embeddings (lines 66-68 of `book_processing_service.py`).

### Pitfall 7: `retry_book()` Must Also Delete Snippets
**What goes wrong:** `retry_book()` currently only deletes `BookChunk` (non-user-created) and `Concept` records. If `Snippet` records are not deleted, reprocessing a book creates duplicate snippets.
**Why it happens:** `retry_book()` was written before the `Snippet` table existed.
**How to avoid:** Add `db.query(Snippet).filter(Snippet.book_id == book.id).delete()` to `retry_book()` alongside the existing concept deletion.

---

## Code Examples

### Snippet List Endpoint (Backend)
```python
# Source: patterns from snippets.py (Phase 1) adapted for Snippet model
@router.get("/")
async def list_snippets(
    book_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == str(book_id), Book.owner_id == str(current_user.id)).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    base_q = (
        db.query(Snippet)
        .filter(Snippet.book_id == str(book_id), Snippet.is_deleted.isnot(True))
        .order_by(Snippet.created_at)
    )
    total = base_q.count()
    items = base_q.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page if total > 0 else 1

    return {
        "items": [_snippet_to_dict(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "book_status": book.status.value if book.status else "pending",
    }
```

**Note:** Include `book_status` in the response so the frontend can show the processing banner without a separate API call.

### Snippet Edit Endpoint (Backend)
```python
# Source: pattern from snippets.py edit_snippet()
@router.patch("/{snippet_id}")
async def edit_snippet(
    snippet_id: UUID,
    body: schemas.SnippetEdit,  # reuse existing schema: content: str
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snippet = (
        db.query(Snippet)
        .join(Book, Book.id == Snippet.book_id)
        .filter(
            Snippet.id == str(snippet_id),
            Snippet.is_deleted.isnot(True),
            Book.owner_id == str(current_user.id),
        )
        .first()
    )
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    # Embed BEFORE DB mutation — if this raises, nothing commits
    new_embedding = await embedding_service.embed_text(body.content)
    new_token_count = _count_tokens(body.content)

    snippet.content = body.content
    snippet.embedding = new_embedding
    snippet.token_count = new_token_count
    db.commit()
    db.refresh(snippet)
    return _snippet_to_dict(snippet)
```

### Frontend TypeScript Types
```typescript
// Add to frontend/src/types/index.ts

export interface Snippet {
  id: string;
  book_id: string;
  chapter_title: string | null;
  page_number: number | null;
  content: string;
  justification: string | null;
  concept_ids: string[];
  concept_names: string[];
  token_count: number;
  is_deleted: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface SnippetListResponse {
  items: Snippet[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  book_status: string;  // Included so frontend can show processing banner
}
```

### Frontend API Methods
```typescript
// Add to frontend/src/lib/api.tsx

// ============================================================
// Snippet Manager (/api/snippets)
// ============================================================
async getSnippets(
  bookId: string,
  params: { page?: number; per_page?: number } = {}
): Promise<SnippetListResponse> {
  const p = new URLSearchParams({ book_id: bookId });
  if (params.page) p.set('page', String(params.page));
  if (params.per_page) p.set('per_page', String(params.per_page));
  const response = await fetch(`${API_BASE_URL}/snippets/?${p}`, { headers: getHeaders() });
  if (!response.ok) throw new Error('Failed to fetch snippets');
  return response.json();
},

async editSnippet(snippetId: string, content: string): Promise<Snippet> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/snippets/${snippetId}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify({ content }),
  });
  if (!response.ok) throw new Error('Failed to update snippet');
  return response.json();
},

async deleteSnippet(snippetId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/snippets/${snippetId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to delete snippet');
},

// Missing from current api.tsx — fix alongside snippets work:
async pauseBook(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/books/${id}/pause`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to pause book');
},

async resumeBook(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/books/${id}/resume`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to resume book');
},

async retryBook(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/books/${id}/retry`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to retry book');
},
```

### Navigation Wiring (Header.tsx + App.tsx)
```typescript
// Header.tsx — add Snippets link:
import { BookOpen, Scissors } from 'lucide-react';  // Scissors for snippets

<Link
  to={ROUTES.SNIPPETS}
  className={`relative flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-medium rounded-md transition-colors
    ${isActive('/snippets')
      ? 'text-foreground bg-muted/60'
      : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
    }`}
>
  <Scissors className="h-3.5 w-3.5" />
  Snippets
</Link>

// constants.ts — add to ROUTES:
SNIPPETS: '/snippets',

// constants.ts — add to QUERY_KEYS:
SNIPPETS: (bookId: string) => ['snippets', bookId],

// App.tsx — add route:
import { SnippetManager } from './components/Snippets/SnippetManager';
<Route path="/snippets" element={<SnippetManager />} />
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Snippets = BookChunks | Snippets = separate entity | Phase 2 design decision | Cleaner data model; user-facing vs. RAG-internal separation |
| No snippet extraction | AI-curated extraction in processing pipeline | Phase 2 | Users get curated passages instead of mechanical text splits |
| Manual snippet creation (CUST-01) | Fully automated extraction only | Phase 2 design decision (CUST removed from scope) | Simpler frontend — no CreateSnippetForm |

**Deprecated/outdated:**
- `is_user_created` field on `BookChunk`: Still valid on BookChunk (Phase 1 work) but the Snippet entity has no equivalent — all snippets are AI-created.
- `SnippetCreate` Pydantic schema: Was built for Phase 1 CUST-01 (user-created snippets). No equivalent needed for the new Snippet entity.

---

## Open Questions

1. **Should Snippets be re-extracted on `retry_book()`?**
   - What we know: `retry_book()` deletes all non-user-created BookChunks and Concepts, then re-runs the full pipeline. The pipeline will create new Snippets if the extraction stage runs.
   - What's unclear: Should old Snippets be preserved across retry (like user-created BookChunks are preserved), or deleted and recreated?
   - Recommendation: Delete all Snippets on `retry_book()` — they are fully AI-generated and will be recreated by the new processing run. This is simpler and avoids duplicates.

2. **Pagination vs. full load for SnippetManager?**
   - What we know: BROW-04 requires client-side text search (no API call on keystroke). Client-side search on a paginated list only searches the current page.
   - What's unclear: Expected snippet count per book — a 300-page book at 4 snippets/chapter × 20 chapters = ~80 snippets. At 200 tokens each, the full list payload is small.
   - Recommendation: Fetch all snippets for the selected book in one request (per_page=200). This enables full client-side search. BROW-01 requires pagination but only "50 per page" — resolve by fetching all and paginating client-side, OR by noting that BROW-01 is already complete (Phase 1) and the new Snippet entity uses a different fetch strategy. The requirement table maps BROW-01 to Phase 1 (BookChunk), not Phase 2 Snippets — so no pagination requirement exists for the new Snippet list.

3. **What if no concepts are extracted for a chapter?**
   - What we know: `extract_snippets()` is called with `concepts` list. If concepts is empty, the method returns `[]` early.
   - What's unclear: Should we still extract snippets for a chapter with 0 concepts? The passages might still be valuable.
   - Recommendation: Skip snippet extraction if no concepts found (early return `[]`). Consistent with the CONTEXT.md design: snippets "best illustrate the concepts." No concepts = no illustrative passages.

---

## Validation Architecture

nyquist_validation is enabled in config.json.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — run from `backend/` directory |
| Quick run command | `pytest app/tests/test_snippets_api.py app/tests/test_snippet_manager.py -v` |
| Full suite command | `pytest app/tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NAV-01 | Snippets route renders (App.tsx route + Header link) | manual | visual inspection | ❌ Wave 0 (frontend — no test runner configured) |
| NAV-02 | Book selector populates from API, selecting book triggers snippet fetch | manual | visual inspection | ❌ Wave 0 |
| BROW-02 | Snippet list response includes chapter_title, page_number, token_count | unit | `pytest app/tests/test_snippet_manager.py::TestSnippetAPI::test_list_snippets_includes_metadata -x` | ❌ Wave 0 |
| BROW-03 | Snippet list response includes concept_names | unit | `pytest app/tests/test_snippet_manager.py::TestSnippetAPI::test_list_snippets_includes_concept_names -x` | ❌ Wave 0 |
| BROW-04 | Client-side filter (frontend only) | manual | visual inspection | ❌ Wave 0 |
| BROW-05 | Processing banner shown when book.status != completed (frontend) | manual | visual inspection | ❌ Wave 0 |
| BROW-06 | Total token count = sum of all (unfiltered) snippets (frontend) | manual | visual inspection | ❌ Wave 0 |
| EDIT-03 | Loading indicator during re-embedding; error on failure; no DB corruption | unit | `pytest app/tests/test_snippet_manager.py::TestSnippetAPI::test_edit_snippet_atomic_rollback -x` | ❌ Wave 0 |
| EXTR-01 | Snippets created during process_chapter() | unit | `pytest app/tests/test_snippet_extraction.py::TestSnippetExtraction::test_extract_snippets_creates_records -x` | ❌ Wave 0 |
| EXTR-02 | Each snippet has embedding and concept_ids | unit | `pytest app/tests/test_snippet_extraction.py::TestSnippetExtraction::test_snippets_have_embeddings_and_concept_ids -x` | ❌ Wave 0 |
| EXTR-03 | No POST /api/snippets endpoint (no creation form) | unit | `pytest app/tests/test_snippet_manager.py::TestSnippetAPI::test_no_create_endpoint -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest app/tests/test_snippet_manager.py -v -x`
- **Per wave merge:** `pytest app/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_snippet_manager.py` — covers BROW-02, BROW-03, EDIT-03, EXTR-03 (backend API tests for new Snippet router)
- [ ] `backend/app/tests/test_snippet_extraction.py` — covers EXTR-01, EXTR-02 (extraction pipeline tests)
- [ ] Frontend tests: NAV-01, NAV-02, BROW-04, BROW-05, BROW-06 are manual-only (no frontend test framework configured in this project)

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `backend/app/api/endpoints/snippets.py` — Phase 1 snippet router implementation
- Direct code inspection: `backend/app/services/knowledge_extraction_service.py` — existing 3-stage pipeline
- Direct code inspection: `backend/app/services/book_processing_service.py` — processing orchestration
- Direct code inspection: `backend/app/models/database.py` — BookChunk, Concept, SafeVector patterns
- Direct code inspection: `backend/migrations/006_snippet_management.sql` — Phase 1 migration pattern
- Direct code inspection: `frontend/src/components/Books/BookManager.tsx` — existing React Query patterns
- Direct code inspection: `frontend/src/lib/api.tsx` — API client patterns and missing methods
- Direct code inspection: `frontend/src/App.tsx` — routing structure
- Direct code inspection: `frontend/src/components/Layout/Header.tsx` — navigation pattern
- Direct code inspection: `.planning/phases/02-frontend-snippets-page/02-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md traceability table — maps requirements to phases; BROW-01 is Phase 1 scope, confirming no pagination requirement for Phase 2 Snippet entity
- STATE.md decisions log — VectorAsText conftest pattern, IS NOT TRUE filter pattern

### Tertiary (LOW confidence)
- Snippet count recommendation (3-5 per chapter): Based on reasoning about book chapter counts and signal-to-noise ratio, not empirically validated

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed from existing codebase
- Architecture patterns: HIGH — modeled directly on Phase 1 patterns present in codebase
- Snippet schema design: HIGH — mirrors BookChunk schema with confirmed patterns
- AI extraction prompt: MEDIUM — structure validated against existing prompts; exact output quality untested
- Pitfalls: HIGH — several are confirmed existing bugs (api.tsx missing methods, retry_book missing Snippet deletion)

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable stack, 30 days)
