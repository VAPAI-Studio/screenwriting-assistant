# Architecture Patterns

**Domain:** AI-powered script breakdown integrated into an existing screenwriting assistant
**Researched:** 2026-03-12

---

## Existing Architecture (What We're Adding To)

The codebase has a template-driven phase system with AI generation and an agent orchestration pipeline:

**Template System:** Projects use templates (e.g., `short_movie.json`) that define phases (Idea, Story, Scenes, Write), each with subsections rendered by UI patterns (card_grid, wizard, ordered_list, etc.). Data flows through `PhaseData` (subsection-level) and `ListItem` (individual items like scenes, characters).

**Generation Pipeline:** `template_ai_service.py` generates content via `ai_provider.py` (OpenAI/Anthropic). Wizards produce structured JSON that `apply_wizard_result_to_db()` persists as PhaseData, ListItems, or ScreenplayContent records. Agent review middleware intercepts wizard output for parallel agent review before persistence.

**Screenplay Content:** The `ScreenplayContent` table stores generated screenplay text with `project_id` and optional `list_item_id` (scene reference). The `write` phase has a `screenplay_editor` subsection and a `script_writer_wizard` for generation.

**Key Insight:** The breakdown feature reads from ALL phases (characters from `story`, scene structure from `scenes`, screenplay text from `write`) but is not itself a phase. It is a cross-cutting derived view of the entire project.

---

## Recommended Architecture

The breakdown system adds a new data domain (production elements) with its own DB tables, API router, service layer, and frontend page. It does NOT use the template phase system. It reads from existing project data but stores its output independently.

```
 Existing System                       New Breakdown System
 +---------------------+
 | ScreenplayContent   |---(read)--+
 | ListItem (scenes)   |---(read)--+--> BreakdownService (AI extraction)
 | ListItem (chars)    |---(read)--+         |
 | PhaseData (all)     |---(read)--+         v
 +---------------------+           +---------------------+
                                   | breakdown_elements   |
                                   | element_scene_links  |
                                   | breakdown_runs       |
                                   +---------------------+
                                             |
        Staleness hooks                      v
 (phase_data PUT, wizard apply) --> project.breakdown_stale
                                             |
                                             v
                                   +---------------------+
                                   | /api/breakdown/*     |
                                   | BreakdownPage (FE)   |
                                   +---------------------+
```

### Why Not a Template Phase

The breakdown is **project-level**, not phase-level. Making it a template phase would force it into the sequential `PhaseData`/subsection model, which does not fit because:

1. It consumes data from ALL phases simultaneously (characters, scenes, screenplay text)
2. It has its own data model (elements with categories, scene links) that differs from the PhaseData/ListItem pattern
3. It needs its own UI page layout (category tabs + master list), not any existing UI pattern
4. It is a derived, cross-cutting view -- not a step in the creative workflow

A dedicated route, dedicated tables, and dedicated page is the correct boundary.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `BreakdownElement` (DB model) | Stores one production element per project with category, name, description, metadata | `Project`, `ElementSceneLink` |
| `ElementSceneLink` (DB model) | Junction table linking elements to scene ListItems with context notes | `BreakdownElement`, `ListItem` |
| `BreakdownRun` (DB model) | Tracks each AI extraction run for auditability (status, counts, errors) | `Project` |
| `BreakdownService` (backend service) | Orchestrates AI extraction: gathers project data, builds prompt, calls AI provider, upserts elements with user-modified protection, manages scene links | `ai_provider`, DB models, `_get_project_context()` |
| `breakdown.py` (API router) | CRUD for elements, trigger extraction, summary with staleness, scene-filtered queries | `BreakdownService`, DB models |
| `BreakdownPage` (frontend page) | Dedicated page with category tabs, master element list, inline editing, scene chips, staleness banner | API client, React Query |

---

## New Database Tables

### `breakdown_elements`

The core table. One row per production element per project. Single table with category column (not table-per-category) because all categories share core fields, the JSONB metadata column handles category-specific fields, cross-category queries are simple, and adding new categories requires zero migration.

```sql
CREATE TABLE IF NOT EXISTS breakdown_elements (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    category        VARCHAR(50) NOT NULL,
    name            VARCHAR(500) NOT NULL,
    description     TEXT DEFAULT '',
    metadata        JSONB DEFAULT '{}',
    source          VARCHAR(20) DEFAULT 'ai',
    user_modified   BOOLEAN DEFAULT FALSE,
    is_deleted      BOOLEAN DEFAULT FALSE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_breakdown_element UNIQUE (project_id, category, name)
);

CREATE INDEX idx_breakdown_elements_project ON breakdown_elements(project_id);
CREATE INDEX idx_breakdown_elements_category ON breakdown_elements(project_id, category);
```

**Category values** (scoped to PROJECT.md requirements):

| Category | Description | Metadata Fields |
|----------|-------------|-----------------|
| `character` | Speaking or named characters | `{role: "protagonist/antagonist/supporting", dialogue_style: "..."}` |
| `location` | Distinct filming locations | `{int_ext: "INT/EXT", time_of_day: "DAY/NIGHT"}` |
| `prop` | Objects actors interact with | `{handler: "character_name", significance: "plot/atmosphere"}` |
| `wardrobe` | Costume pieces per character-day | `{character: "name", script_day: 1, outfit_number: 1}` |
| `vehicle` | Picture vehicles on screen | `{type: "car/motorcycle/boat", driver: "character_name"}` |

These five categories match the PROJECT.md spec. Additional industry-standard categories (stunts, special effects, extras, animals, set dressing, makeup/hair, sound effects, special equipment) are explicitly out of scope but could be added later by inserting new category values with no schema migration.

### `element_scene_links`

Junction table linking elements to scenes. A scene is a `ListItem` with `item_type = 'scene'` in the `scenes.scene_list` PhaseData.

```sql
CREATE TABLE IF NOT EXISTS element_scene_links (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    element_id      UUID NOT NULL REFERENCES breakdown_elements(id) ON DELETE CASCADE,
    scene_item_id   UUID NOT NULL REFERENCES list_items(id) ON DELETE CASCADE,
    context         TEXT DEFAULT '',
    source          VARCHAR(20) DEFAULT 'ai',
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_element_scene UNIQUE (element_id, scene_item_id)
);

CREATE INDEX idx_element_scene_element ON element_scene_links(element_id);
CREATE INDEX idx_element_scene_scene ON element_scene_links(scene_item_id);
```

**Why link to `list_items` (scenes) not `screenplay_content`:** Scenes are structurally stable -- they have UUIDs, structured content (summary, arena, etc.), and persist across regenerations. ScreenplayContent is full text that changes on every edit. Position-based linking (text spans) would break on every change. Scene-level linking is both more stable and more useful for production planning ("which scenes need this prop?").

### `breakdown_runs`

Audit trail for extraction runs.

```sql
CREATE TABLE IF NOT EXISTS breakdown_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'pending',
    config          JSONB DEFAULT '{}',
    result_summary  JSONB DEFAULT '{}',
    error_message   TEXT,
    elements_created INTEGER DEFAULT 0,
    elements_updated INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_breakdown_runs_project ON breakdown_runs(project_id);
```

### Staleness Column on Projects

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS breakdown_stale BOOLEAN DEFAULT FALSE;
```

### Relationship to Existing Models

```
Project (1) -----> (N) BreakdownElement
Project (1) -----> (N) BreakdownRun
BreakdownElement (N) <---> (N) ListItem[scene]  via ElementSceneLink

No FK from BreakdownElement to Section, PhaseData, or ScreenplayContent.
The extraction service reads those tables, but breakdown elements are
independent entities that survive content regeneration.
```

---

## API Endpoint Structure

New router: `backend/app/api/endpoints/breakdown.py` mounted at `/api/breakdown`.

```python
# In main.py:
from .api.endpoints import breakdown as breakdown_ep
app.include_router(breakdown_ep.router, prefix="/api/breakdown", tags=["breakdown"])
```

### Endpoints

| Method | Path | Purpose | Returns |
|--------|------|---------|---------|
| `POST` | `/extract/{project_id}` | Trigger AI extraction. Creates BreakdownRun, calls BreakdownService, returns run result. | `BreakdownRunResponse` |
| `GET` | `/elements/{project_id}` | List elements filtered by category. Query: `?category=prop&include_deleted=false` | `List[BreakdownElementResponse]` |
| `GET` | `/elements/{project_id}/by-scene/{scene_item_id}` | All elements linked to a specific scene | `List[BreakdownElementResponse]` |
| `GET` | `/element/{element_id}` | Single element with scene links | `BreakdownElementDetailResponse` |
| `PUT` | `/element/{element_id}` | Update element. Sets `user_modified=true`. | `BreakdownElementResponse` |
| `POST` | `/elements/{project_id}` | Create element manually. Sets `source='user'`. | `BreakdownElementResponse` |
| `DELETE` | `/element/{element_id}` | Soft-delete (sets `is_deleted=true`) | `204 No Content` |
| `POST` | `/element/{element_id}/scenes` | Add a scene link | `ElementSceneLinkResponse` |
| `DELETE` | `/element/{element_id}/scenes/{scene_item_id}` | Remove a scene link | `204 No Content` |
| `GET` | `/summary/{project_id}` | Breakdown summary: counts per category, staleness, last run info | `BreakdownSummaryResponse` |
| `GET` | `/runs/{project_id}` | List extraction runs for audit | `List[BreakdownRunResponse]` |

### Schema Design

```python
# New schemas in schemas.py or a dedicated breakdown_schemas.py

class BreakdownElementCreate(BaseModel):
    category: str = Field(..., pattern="^(character|location|prop|wardrobe|vehicle)$")
    name: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    metadata: Dict = Field(default_factory=dict)

class BreakdownElementUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    metadata: Optional[Dict] = None

class BreakdownElementResponse(BaseModel):
    id: UUID
    project_id: UUID
    category: str
    name: str
    description: str
    metadata: Dict
    source: str
    user_modified: bool
    is_deleted: bool
    sort_order: int
    scene_count: int  # computed from scene links
    created_at: datetime
    updated_at: Optional[datetime]

class SceneLinkResponse(BaseModel):
    scene_item_id: UUID
    scene_summary: str  # from ListItem.content["summary"]
    scene_sort_order: int
    context: str

class BreakdownElementDetailResponse(BreakdownElementResponse):
    scene_links: List[SceneLinkResponse]

class BreakdownSummaryResponse(BaseModel):
    project_id: UUID
    is_stale: bool
    total_elements: int
    counts_by_category: Dict[str, int]
    last_run: Optional[BreakdownRunResponse]

class BreakdownRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    result_summary: Dict
    elements_created: int
    elements_updated: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

class SceneLinkCreate(BaseModel):
    scene_item_id: UUID
    context: str = ""
```

---

## AI Extraction Service Design

### `BreakdownService` (new file: `backend/app/services/breakdown_service.py`)

```python
class BreakdownService:
    """Extracts production elements from project data using AI."""

    async def extract(self, project_id: UUID, db: Session) -> BreakdownRun:
        """Full extraction pipeline."""
        # 1. Create BreakdownRun record (status=running)
        # 2. Gather all project data:
        #    a. Reuse _get_project_context() from wizards.py for phase data
        #    b. Query all ScreenplayContent for this project
        #    c. Query scene ListItems for scene summaries
        # 3. Build extraction prompt with structured JSON output spec
        # 4. Call ai_provider.chat_completion(json_mode=True)
        # 5. Parse AI response into element dicts
        # 6. Load existing elements for this project
        # 7. Upsert elements (with user_modified protection)
        # 8. Reconcile scene links
        # 9. Clear project.breakdown_stale flag
        # 10. Update BreakdownRun with summary and status=completed
        # 11. Return run record

    def _build_extraction_prompt(
        self, project_context: str, screenplay_text: str,
        scenes: List[Dict]
    ) -> List[Dict[str, str]]:
        """Build messages for AI extraction call."""

    def _upsert_elements(
        self, db: Session, project_id: UUID,
        extracted: List[Dict], existing: List[BreakdownElement]
    ) -> Tuple[int, int]:
        """Merge AI-extracted elements with existing data.
        Returns (created_count, updated_count).

        Rules:
        - New elements: INSERT
        - Existing AI elements (not user_modified): UPDATE description/metadata
        - Existing user_modified elements: SKIP (preserve user edits)
        - Soft-deleted elements: stay deleted even if AI re-extracts them
        - Existing AI elements not in new extraction: keep (don't delete)
        """

    def _reconcile_scene_links(
        self, db: Session, element_id: UUID,
        new_scene_refs: List[int], scene_items: List[ListItem],
        existing_links: List[ElementSceneLink]
    ):
        """Update scene links from AI extraction.
        - Add new AI links
        - Remove stale AI links (source='ai' not in new extraction)
        - Preserve user-added links (source='user')
        """
```

### Extraction Prompt Strategy

The prompt requests structured JSON output organized by category. Uses existing `ai_provider.chat_completion()` with `json_mode=True`.

```python
EXTRACTION_SYSTEM_PROMPT = """You are a production breakdown analyst for film pre-production.
Given a screenplay and project data, extract ALL production elements organized by category.

Categories:
- character: Named or speaking characters (not extras/background)
- location: Distinct filming locations
- prop: Objects that actors physically interact with
- wardrobe: Notable costume pieces (character-specific)
- vehicle: Picture vehicles that appear on screen

For each element, identify which scenes it appears in by scene number (1-based index).

Return ONLY valid JSON matching this schema:
{
  "elements": [
    {
      "category": "prop",
      "name": "Revolver",
      "description": "Smith & Wesson .38, carried by Detective Mills",
      "scenes": [1, 3, 7],
      "metadata": {"handler": "Detective Mills", "significance": "plot"}
    }
  ]
}

Rules:
- Be thorough: extract every element mentioned or implied in the script
- Use consistent naming (same character spelled the same way throughout)
- For wardrobe, include character name and script day in metadata
- For props, distinguish from set dressing (props are touched/used by actors)
- Scene numbers reference the scene list order (1 = first scene, etc.)
"""
```

### Token Budget

For short films (current scope): screenplay is 5-15 pages (~3,000-8,000 tokens). Combined with project context (~2,000-4,000 tokens), total input is well within model limits. Single-call extraction is appropriate.

**Future scaling (feature-length):** Build the service to accept chunked input, but implement single-call for now. The `_build_extraction_prompt` method already encapsulates prompt construction, making it straightforward to add chunking later.

Set `max_tokens=4000` for the response -- breakdown JSON is structured and compact.

---

## Bidirectional Sync Mechanism

### Forward Sync: Script Changes -> Breakdown Staleness

**Mechanism:** Staleness flag, not event-driven sync. When content that feeds the breakdown changes, set `project.breakdown_stale = True`. The frontend shows a "Breakdown outdated -- refresh?" indicator.

**Detection hook points** (modifications to existing code):

| Existing File | Hook Location | Trigger Condition |
|---|---|---|
| `phase_data.py` PUT endpoint | After successful content update | `phase in ('write', 'scenes')` AND breakdown exists for project |
| `wizards.py` `apply_wizard_result_to_db()` | After DB persist | `wizard_type == 'script_writer_wizard'` |
| `list_items.py` create/update/delete | After successful mutation | ListItem's PhaseData has `phase == 'scenes'` |

**Implementation pattern:**

```python
# Utility function in breakdown_service.py or a shared utils module:
def mark_breakdown_stale(db: Session, project_id: UUID):
    """Mark project breakdown as stale if a breakdown exists."""
    has_breakdown = db.query(BreakdownElement).filter(
        BreakdownElement.project_id == project_id,
        BreakdownElement.is_deleted == False
    ).limit(1).count() > 0
    if has_breakdown:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.breakdown_stale = True
            # No separate commit -- the caller's transaction handles it
```

This check is lightweight (indexed query limited to 1 row) and only modifies a boolean column.

### Reverse Sync: Breakdown -> Script (User-Initiated Actions)

The reverse direction is **not automatic propagation**. It is specific user-initiated actions:

| Trigger | Action | Implementation |
|---------|--------|----------------|
| User adds character in breakdown not in characters list | "Add to Characters" button | POST `/api/list-items` to create character ListItem in `story.characters` PhaseData |
| User edits character name that differs from characters list | Show "Name differs from Characters list" warning | UI-only indicator in ElementCard |
| User adds location in breakdown | No auto-sync (locations not a current phase data type) | Potential future enhancement |

**Why not automatic reverse sync:**
1. The screenplay is the source of truth; the breakdown is a derived view
2. Automatically modifying screenplay text from breakdown edits creates circular dependencies
3. Conflict resolution between AI-generated breakdown and user-written screenplay is genuinely hard
4. PROJECT.md explicitly scopes sync to "on save/generate, not as user types"
5. Find-and-replace in screenplay for name changes risks corrupting dialogue formatting

### Staleness Lifecycle

```
1. Script content changes (wizard generate, manual save, scene edit)
   -> project.breakdown_stale = True

2. User navigates to Breakdown page
   -> GET /api/breakdown/summary/{project_id}
   -> Response: {is_stale: true, last_run: {...}, counts_by_category: {...}}
   -> UI shows amber banner: "Script has changed since last breakdown. Refresh?"

3. User clicks "Refresh Breakdown"
   -> POST /api/breakdown/extract/{project_id}
   -> BreakdownService.extract() runs
   -> Upserts elements (respecting user_modified flags)
   -> project.breakdown_stale = False

4. User manually edits an element
   -> PUT /api/breakdown/element/{id}
   -> element.user_modified = True
   -> Next re-extraction preserves this element unchanged

5. User soft-deletes an element
   -> DELETE /api/breakdown/element/{id}
   -> element.is_deleted = True
   -> Next re-extraction does NOT resurrect it
```

---

## Frontend Page/Component Structure

### Routing

Add a new route at the project level (not inside the phase navigation):

```tsx
// In App.tsx, add:
<Route path="/projects/:projectId/breakdown" element={<BreakdownPage />} />
```

### Navigation Integration

The breakdown is NOT a phase. Add it as a separate navigation element after the phase tabs in `PhaseNavigation.tsx`:

```tsx
// After phase tabs, add a divider and breakdown button:
<div className="border-l border-border pl-4 ml-2 flex items-center">
  <button
    onClick={() => navigate(`/projects/${projectId}/breakdown`)}
    className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold
      uppercase tracking-wider border-b-2 -mb-px transition-all
      ${isBreakdownActive ? 'text-rose-400 border-rose-400' : 'text-muted-foreground border-transparent'}`}
  >
    <ClipboardList className="h-4 w-4" />
    Breakdown
    {isStale && <span className="w-2 h-2 rounded-full bg-amber-400 ml-1 animate-pulse" />}
  </button>
</div>
```

The `isStale` indicator uses React Query to poll `/api/breakdown/summary/{projectId}` (stale time: 30s).

### Component Hierarchy

```
BreakdownPage
  +-- BreakdownHeader
  |     +-- Project title
  |     +-- Staleness banner (amber, with "Refresh" button)
  |     +-- "Extract Breakdown" button (if no breakdown exists yet)
  |     +-- Last extraction timestamp
  +-- CategoryTabs
  |     +-- Characters | Locations | Props | Wardrobe | Vehicles
  |     +-- Count badge per tab
  +-- ElementList (filtered by selected category)
  |     +-- ElementCard (per element)
  |           +-- ElementName (inline editable text)
  |           +-- ElementDescription (expandable textarea)
  |           +-- SceneChips (row of clickable pills showing linked scenes)
  |           +-- SourceBadge (AI or User indicator)
  |           +-- UserModifiedIndicator (pencil icon if user-edited)
  |           +-- ElementActions (edit, delete, add scene link)
  +-- AddElementDialog (modal for manually adding an element)
  +-- EmptyState (shown when no elements exist yet, with "Extract" CTA)
```

### New Frontend Files

| File | Purpose |
|------|---------|
| `frontend/src/components/Breakdown/BreakdownPage.tsx` | Main page: category tabs, element list, staleness banner |
| `frontend/src/components/Breakdown/ElementCard.tsx` | Single element with inline editing, scene chips, actions |
| `frontend/src/components/Breakdown/CategoryTabs.tsx` | Horizontal tab bar with count badges |
| `frontend/src/components/Breakdown/AddElementDialog.tsx` | Modal for creating elements manually |
| `frontend/src/components/Breakdown/SceneChips.tsx` | Pill/chip display of linked scenes |
| `frontend/src/components/Breakdown/BreakdownHeader.tsx` | Title, staleness banner, extract/refresh button |
| `frontend/src/types/breakdown.ts` | TypeScript interfaces for breakdown API responses |

### React Query Integration

```typescript
// In constants.ts:
BREAKDOWN_SUMMARY: (projectId: string) => ['breakdown-summary', projectId],
BREAKDOWN_ELEMENTS: (projectId: string, category?: string) =>
  ['breakdown-elements', projectId, category].filter(Boolean),
BREAKDOWN_ELEMENT: (elementId: string) => ['breakdown-element', elementId],

// In api.tsx:
async getBreakdownSummary(projectId: string): Promise<BreakdownSummary> { ... }
async getBreakdownElements(projectId: string, category?: string): Promise<BreakdownElement[]> { ... }
async extractBreakdown(projectId: string): Promise<BreakdownRun> { ... }
async updateBreakdownElement(elementId: string, data: BreakdownElementUpdate): Promise<BreakdownElement> { ... }
async createBreakdownElement(projectId: string, data: BreakdownElementCreate): Promise<BreakdownElement> { ... }
async deleteBreakdownElement(elementId: string): Promise<void> { ... }
async addSceneLink(elementId: string, sceneItemId: string, context?: string): Promise<void> { ... }
async removeSceneLink(elementId: string, sceneItemId: string): Promise<void> { ... }
```

---

## Patterns to Follow

### Pattern 1: Upsert with User-Modified Protection

**What:** When AI re-extracts elements, protect user modifications from being overwritten.
**When:** Every time `BreakdownService.extract()` runs.
**Example:**

```python
def _upsert_elements(self, db, project_id, extracted, existing):
    existing_map = {(e.category, e.name): e for e in existing}
    created, updated = 0, 0

    for elem in extracted:
        key = (elem["category"], elem["name"])
        existing_elem = existing_map.get(key)

        if existing_elem is None:
            db.add(BreakdownElement(project_id=project_id, **elem))
            created += 1
        elif existing_elem.is_deleted:
            continue  # respect user deletion
        elif existing_elem.user_modified:
            # preserve user edits but still update scene links
            self._reconcile_scene_links(db, existing_elem.id, elem.get("scenes", []))
        else:
            existing_elem.description = elem.get("description", existing_elem.description)
            existing_elem.metadata = elem.get("metadata", existing_elem.metadata)
            self._reconcile_scene_links(db, existing_elem.id, elem.get("scenes", []))
            updated += 1

    return created, updated
```

### Pattern 2: Staleness Flag Instead of Event-Driven Sync

**What:** Set a boolean on the project when content changes, rather than pushing real-time events.
**When:** Any save/generate operation that modifies screenplay or scene data.
**Why:** Matches project constraint ("on save/generate, not as user types"). Avoids websocket infrastructure, conflict resolution, and partial update reconciliation. The breakdown is a pre-production planning tool, not a live dashboard.

### Pattern 3: Reuse Existing Project Context Builder

**What:** Use `_get_project_context()` (already in `wizards.py` and `ai_chat.py`) to gather all project data for the extraction prompt.
**When:** Building the AI extraction prompt in BreakdownService.
**Why:** This function already traverses all PhaseData and ListItems. No need to duplicate that traversal. BreakdownService adds screenplay content on top.

**Note:** The `_get_project_context` function is currently duplicated between `wizards.py` and `ai_chat.py`. Consider extracting it to a shared utility as part of this work.

### Pattern 4: Single Table with Category Column

**What:** Store all breakdown element types in one table with a `category` VARCHAR column and a JSONB `metadata` column for category-specific fields.
**When:** Designing the breakdown data model.
**Why:** Uniform querying (no UNIONs), simple API (one CRUD set), easy to add categories (no migration), consistent UI (one list component with category filter).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Making Breakdown a Template Phase

**What:** Adding `"breakdown"` as a phase in `short_movie.json` and using PhaseData/ListItem.
**Why bad:** Breakdown reads from ALL phases -- it is cross-cutting, not sequential. PhaseData is scoped to one phase/subsection. Cramming breakdown into this model requires awkward cross-phase queries, pollutes phase navigation, and creates confusing ownership ("is the character in breakdown the same entity as the character in story.characters?").
**Instead:** Dedicated tables, route, and page.

### Anti-Pattern 2: Real-Time Sync via WebSockets

**What:** Pushing breakdown updates to frontend whenever screenplay content changes.
**Why bad:** Massive complexity (websocket infrastructure, partial update reconciliation, conflict resolution) for marginal benefit. A breakdown is reviewed periodically for production planning, not monitored in real-time.
**Instead:** Staleness flag + manual refresh.

### Anti-Pattern 3: Storing Scene References as Text Spans

**What:** Linking elements to character positions in screenplay text (e.g., "lines 42-47").
**Why bad:** Text positions break on every edit. The screenplay is regenerated frequently. Position-based linking is fragile and requires constant reconciliation.
**Instead:** Link to scene ListItems by UUID. Scenes are structurally stable even when their text content changes.

### Anti-Pattern 4: Automatic Script Rewriting from Breakdown Edits

**What:** When user renames a character in breakdown, find-and-replace in the screenplay.
**Why bad:** Screenplay text has nuanced formatting (dialogue vs. action lines vs. parentheticals). Automated rewriting risks corrupting the screenplay. Creates circular sync loops (breakdown edit -> script change -> staleness flag -> re-extract -> different result).
**Instead:** Show warnings/suggestions. User makes screenplay changes manually.

### Anti-Pattern 5: Table-Per-Category Schema

**What:** Separate `breakdown_characters`, `breakdown_locations`, `breakdown_props` tables.
**Why bad:** N tables means N CRUD endpoint sets, N schema definitions, N frontend query hooks. Adding a new category requires a migration, new model, new endpoints, new UI. Cross-category queries (e.g., "everything in scene 3") require UNION queries.
**Instead:** Single `breakdown_elements` table with category column.

---

## Build Order (Dependency-Aware)

### Phase 1: Database Foundation + Models
**Build:** Migration SQL for `breakdown_elements`, `element_scene_links`, `breakdown_runs` tables. `breakdown_stale` column on projects. SQLAlchemy models. Pydantic schemas.
**Rationale:** Everything else depends on the data model.
**Depends on:** Nothing new. Uses existing `projects` and `list_items` FKs.
**Modifies:** `database.py` (add models), `schemas.py` (add schemas). New migration file.

### Phase 2: API Endpoints (CRUD)
**Build:** `breakdown.py` router with all CRUD endpoints. Mount in `main.py`.
**Rationale:** Frontend development can begin as soon as CRUD exists, even before AI extraction works. Manual element creation/editing tests the full data flow.
**Depends on:** Phase 1 (models and schemas).
**Modifies:** `main.py` (add router). New file: `breakdown.py`.

### Phase 3: AI Extraction Service
**Build:** `BreakdownService` with extraction prompt, structured JSON parsing, upsert logic with user-modified protection, scene link reconciliation.
**Rationale:** Needs CRUD layer to store results. Can be developed/tested with mock AI responses.
**Depends on:** Phase 1 (models), Phase 2 (storage via CRUD), existing `ai_provider.py`.
**New file:** `breakdown_service.py`.

### Phase 4: Staleness Detection + Sync Hooks
**Build:** `mark_breakdown_stale()` utility. Hook into `phase_data.py` PUT, `wizards.py` apply, `list_items.py` mutations. Summary endpoint returns staleness.
**Rationale:** Requires extraction service to exist (extract clears the flag). Modifies existing endpoints with small, targeted additions.
**Depends on:** Phase 1 (stale column), Phase 3 (extract clears flag).
**Modifies:** `phase_data.py`, `wizards.py`, `list_items.py` (add staleness hooks).

### Phase 5: Frontend -- Breakdown Page
**Build:** `BreakdownPage` and sub-components. Navigation integration in `PhaseNavigation.tsx`. Route in `App.tsx`. API client functions. TypeScript types. React Query hooks.
**Rationale:** Needs API endpoints functional. Can start with CRUD endpoints (Phase 2) and progressively add extraction trigger and staleness UI.
**Depends on:** Phase 2 (API), Phase 3 (extraction trigger), Phase 4 (staleness).
**Modifies:** `App.tsx` (route), `PhaseNavigation.tsx` (breakdown tab), `api.tsx` (new functions), `constants.ts` (query keys).

### Phase 6: Reverse Sync Actions
**Build:** "Add to Characters" button in ElementCard. Warning indicators for name mismatches. Integration with existing ListItem create API.
**Rationale:** Enhancement that builds on the complete forward pipeline. Lowest priority -- the forward direction (script -> breakdown) delivers the core value.
**Depends on:** Phase 5 (UI), existing ListItem create API.

---

## Integration Points with Existing Code

| Existing File | Change | Scope |
|---|---|---|
| `backend/app/models/database.py` | Add `BreakdownElement`, `ElementSceneLink`, `BreakdownRun` models. Add `breakdown_stale` column to Project. | Additive |
| `backend/app/models/schemas.py` | Add breakdown request/response schemas | Additive |
| `backend/app/main.py` | Mount breakdown router | 1 line |
| `backend/app/api/endpoints/phase_data.py` | Call `mark_breakdown_stale()` after write/scenes phase updates | 3-5 lines |
| `backend/app/api/endpoints/wizards.py` | Call `mark_breakdown_stale()` in `apply_wizard_result_to_db()` for script_writer_wizard | 3-5 lines |
| `backend/app/api/endpoints/list_items.py` | Call `mark_breakdown_stale()` after scene ListItem mutations | 3-5 lines |
| `frontend/src/App.tsx` | Add breakdown route | 1 line |
| `frontend/src/components/Workspace/PhaseNavigation.tsx` | Add breakdown tab with staleness indicator | ~15 lines |
| `frontend/src/lib/api.tsx` | Add breakdown API functions | ~50 lines |
| `frontend/src/lib/constants.ts` | Add breakdown query keys | ~5 lines |

**No changes required to:**
- `template_ai_service.py` -- breakdown reads from project data, does not modify generation
- `agent_review_middleware.py` -- breakdown is independent of the agent pipeline
- `ai_provider.py` -- used as-is for extraction calls
- Any existing UI Pattern components (CardGridView, WizardView, etc.)

---

## Scalability Considerations

| Concern | Short Film (current) | Feature Film (future) | Series (future) |
|---------|---------------------|-----------------------|-----------------|
| Extraction input tokens | ~5K-12K (single call) | ~20K-50K (needs chunking) | Per-episode + cross-episode dedup |
| Element count | ~20-50 | ~200-500 | ~500-2000 |
| Scene link density | ~50-100 links | ~500-2000 links | ~2000-10000 links |
| Query performance | Trivial | Index on (project_id, category) sufficient | May need pagination + materialized summaries |
| Re-extraction time | 5-10 seconds (synchronous) | 30-60 seconds (background task) | Minutes (job queue) |

For short films, all operations are synchronous request-response. Feature-length and series would need background task processing, but that infrastructure decision is deferred per PROJECT.md.

---

## Sources

- [StudioBinder - Complete Guide to Script Breakdown Elements](https://www.studiobinder.com/blog/the-complete-guide-to-mastering-script-breakdown-elements/) -- standard categories, color coding, element definitions (HIGH confidence)
- [Filmustage - Props, Costumes & Locations in Script Breakdown](https://filmustage.com/blog/how-to-identify-props-costumes-and-locations-in-a-script-breakdown/) -- category definitions, prop vs set dressing distinction (HIGH confidence)
- [First Draft Filmworks - Complete Guide to Script Breakdown](https://firstdraftfilmworks.com/blog/the-complete-guide-to-script-breakdown/) -- breakdown workflow and production planning context (MEDIUM confidence)
- [MasterClass - How to Break Down a Script](https://www.masterclass.com/articles/how-to-break-down-a-script) -- element identification methodology (MEDIUM confidence)
- [StackSync - Bi-Directional Sync Explained](https://www.stacksync.com/blog/bi-directional-sync-explained-3-real-world-examples) -- staleness vs event-driven sync tradeoffs (MEDIUM confidence)
- [MuleSoft - Bi-Directional Sync Patterns](https://blogs.mulesoft.com/api-integration/patterns/data-integration-patterns-bi-directional-sync/) -- sync architecture patterns (MEDIUM confidence)
- Existing codebase: `database.py`, `wizards.py`, `ai_chat.py`, `phase_data.py`, `list_items.py`, `template_ai_service.py`, `ai_provider.py`, `short_movie.json`, `App.tsx`, `PhaseNavigation.tsx`, `ContentArea.tsx` -- direct code inspection (HIGH confidence)

---

*Architecture analysis for v2.0 Script Breakdown milestone: 2026-03-12*
