# Phase 14: Reverse Sync - Research

**Researched:** 2026-03-17
**Domain:** Cross-system advisory sync — breakdown element to project ListItem
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Synced characters always land in the `supporting` card group (`item_type: "supporting"`)
- No dialog or picker — default to Supporting is safe since AI extraction doesn't know protagonist/antagonist intent; user reassigns in the Characters phase if needed
- Button appears on all character elements regardless of source (AI-extracted or user-created) — behavior is identical
- "Add to Characters" button only renders on the Characters category tab, not in any future combined view
- `element.name` → `content.name` (character name field)
- `element.description` → `content.role` (Role & Purpose field)
- `content.dialogue_style` is left blank — user fills in manually
- `item_type` = `"supporting"`
- `status` = `"draft"` (consistent with manually created items, no custom status needed)
- Endpoint lives under the breakdown router: `POST /api/breakdown/element/{element_id}/sync-to-project`
- Response is a lightweight status object: `{status: "created" | "already_exists", list_item_id: UUID}` — no full ListItem body needed
- After sync, the "Add to Characters" button changes to a disabled "Synced" state on the ElementCard
- The frontend reads a `synced_to_characters: bool` on each `BreakdownElementResponse` — backend computes this at query time by checking whether a ListItem with a matching name exists in `story.characters` PhaseData
- Duplicate detection: case-insensitive name match (`LOWER()` comparison) against existing ListItems in `story.characters`
- When duplicate detected: endpoint returns `{status: "already_exists", list_item_id: <existing_id>}` with HTTP 200 — no new item created, no error
- Frontend response to `already_exists`: put button into "Synced" state (same as created), no error toast needed
- Characters-only for this phase — no generic `target_phase`/`subsection_key` parameter
- No architectural prep for other categories (YAGNI)

### Claude's Discretion

None explicitly stated — all key decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Reverse sync for other categories (locations, props, vehicles, wardrobe)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNC-05 | Reverse sync is user-initiated — "Add to Characters" action from breakdown creates a ListItem in the characters phase, not automatic script modification | Covered by: backend endpoint pattern, frontend mutation pattern, `synced_to_characters` computed field, case-insensitive duplicate detection, idempotent 200 response |
</phase_requirements>

---

## Summary

Phase 14 implements a one-way, user-initiated push from a breakdown character element to the project's `story.characters` PhaseData. When a user clicks "Add to Characters" on an ElementCard in the Characters tab, the backend creates a Supporting ListItem in `story.characters` with the element's name and description mapped to the `name` and `role` fields. Duplicate detection uses a case-insensitive name comparison against existing items, and the endpoint is idempotent — returning `{status: "already_exists", ...}` with HTTP 200 instead of an error.

The frontend adds a `synced_to_characters: bool` to `BreakdownElementResponse`. The backend computes this at query time. After a successful sync (or discovery that the element is already synced), the "Add to Characters" button transitions to a disabled "Synced" state. No toast is shown for the `already_exists` path.

This phase requires three changes: (1) a new endpoint in `breakdown.py`, (2) a `synced_to_characters` computed field on `BreakdownElementResponse` schema + the `list_elements` query, and (3) a `syncMutation` + button UI in `ElementCard.tsx` conditional on `category === 'character'`.

**Primary recommendation:** Follow the scene-link idempotency pattern precisely — `JSONResponse(status_code=200, ...)` for already-synced, standard 200 for fresh creates. Compute `synced_to_characters` in the existing `list_elements` query to keep it in one DB round-trip.

---

## Standard Stack

### Core (already in place — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | Endpoint routing | Project standard |
| SQLAlchemy | current | ORM / query layer | Project standard |
| React Query (TanStack) | current | Mutation + cache invalidation | Project standard |
| Lucide React | current | Icons (UserCheck for Synced state) | Project standard |

### No new installation required

This phase adds no new libraries. All patterns are already established in `breakdown.py`, `list_items.py`, and `ElementCard.tsx`.

---

## Architecture Patterns

### Recommended File Touches

```
backend/app/api/endpoints/breakdown.py   # Add sync endpoint + synced_to_characters logic
backend/app/models/schemas.py            # Add synced_to_characters: bool to BreakdownElementResponse
frontend/src/types/index.ts              # Add synced_to_characters: bool to BreakdownElement
frontend/src/lib/api.tsx                 # Add syncBreakdownElementToCharacters()
frontend/src/components/Breakdown/ElementCard.tsx  # Add syncMutation + conditional button
backend/app/tests/test_breakdown_api.py  # Tests for sync endpoint
```

### Pattern 1: Idempotent POST with status field (established by scene links)

The scene link `add_scene_link` endpoint already implements the idempotency pattern this phase reuses:

```python
# Source: backend/app/api/endpoints/breakdown.py — add_scene_link handler
if existing:
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Scene link already exists", "id": str(existing.id)},
    )
```

The sync endpoint mirrors this:
- Fresh create → `201` with `{status: "created", list_item_id: <new_uuid>}`
- Duplicate detected → `200` with `{status: "already_exists", list_item_id: <existing_uuid>}`

Wait — the CONTEXT.md specifies HTTP 200 for both. Use `JSONResponse(status_code=200, ...)` for created too, since no full body is needed. Verify: CONTEXT.md says "Response is a lightweight status object: `{status: 'created' | 'already_exists', list_item_id: UUID}`" with no status code differentiation. Use 200 for both paths to keep it simple and consistent.

### Pattern 2: `synced_to_characters` computed field

The field does not need a DB column. It is computed per-element by checking whether a ListItem with a matching name (case-insensitive) exists in the project's `story.characters` PhaseData.

**Two-step lookup:**

```python
# Step 1: find the story.characters PhaseData for this project
chars_pd = db.query(database.PhaseData).filter(
    database.PhaseData.project_id == str(project_id),
    database.PhaseData.phase == "story",
    database.PhaseData.subsection_key == "characters",
).first()

# Step 2: for each character element, check if a ListItem with matching name exists
# Use func.lower() for case-insensitive match
if chars_pd:
    synced_names = {
        row[0].lower()
        for row in db.query(func.json_extract(database.ListItem.content, '$.name'))
        .filter(database.ListItem.phase_data_id == str(chars_pd.id))
        .all()
        if row[0]
    }
else:
    synced_names = set()
```

**Important:** `json_extract` is SQLite syntax. For PostgreSQL use `database.ListItem.content['name'].astext`. Since tests use SQLite (conftest.py) and production uses PostgreSQL, the safest approach that works for both is to load the content dicts in Python:

```python
# Portable approach — load all item content dicts for the characters phase_data
if chars_pd:
    items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == str(chars_pd.id)
    ).all()
    synced_names = {
        (item.content.get("name") or "").lower()
        for item in items
        if item.content.get("name")
    }
else:
    synced_names = set()
```

This avoids JSON path syntax differences between SQLite and PostgreSQL.

### Pattern 3: `story.characters` PhaseData lookup or creation

The sync endpoint must locate (or create) the `story.characters` PhaseData. The CONTEXT.md notes "query must look up or create this PhaseData record." Looking at existing patterns:

- `list_items.py` `create_list_item` does NOT create PhaseData — it requires an existing `phase_data_id`.
- `phase_data.py` only creates PhaseData via template initialization (project creation).

The sync endpoint should look up the PhaseData and raise HTTP 422 if it doesn't exist (i.e., if the project hasn't gone through story phase setup). This is safer than silently creating PhaseData which might break the template rendering.

Actually, re-reading CONTEXT.md: "query must look up or create this PhaseData record." So the endpoint should upsert it. Use `get_or_create` pattern:

```python
chars_pd = db.query(database.PhaseData).filter(
    database.PhaseData.project_id == str(element.project_id),
    database.PhaseData.phase == "story",
    database.PhaseData.subsection_key == "characters",
).first()

if not chars_pd:
    chars_pd = database.PhaseData(
        project_id=element.project_id,
        phase="story",
        subsection_key="characters",
        content={},
        sort_order=0,
    )
    db.add(chars_pd)
    db.flush()  # get the id without committing yet
```

### Pattern 4: ListItem creation for supporting character

From the `short_movie.json` template, supporting characters have fields: `name`, `role`, `dialogue_style`.

```python
new_item = database.ListItem(
    phase_data_id=chars_pd.id,
    item_type="supporting",
    content={
        "name": element.name,
        "role": element.description,
        "dialogue_style": "",
    },
    status="draft",
)
db.add(new_item)
db.commit()
db.refresh(new_item)
```

`sort_order` auto-assigns via count of existing items (matching `list_items.py` `create_list_item`):

```python
max_order = db.query(database.ListItem).filter(
    database.ListItem.phase_data_id == str(chars_pd.id)
).count()
new_item = database.ListItem(
    ...,
    sort_order=max_order,
)
```

### Pattern 5: Frontend `syncMutation` in ElementCard

Follows the same `useMutation` + `onSettled` invalidation pattern as `updateMutation` and `deleteMutation`:

```typescript
const syncMutation = useMutation({
  mutationFn: (elementId: string) =>
    api.syncBreakdownElementToCharacters(elementId),
  onSettled: () => {
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category),
    });
    // Optionally invalidate LIST_ITEMS for the characters phase_data if its ID is known
    // But since we don't have phase_data_id here, only BREAKDOWN_ELEMENTS is needed
    // to refresh synced_to_characters flag
  },
});
```

After mutation settles, the re-fetched element will have `synced_to_characters: true`, and the button renders as disabled "Synced".

### Pattern 6: Conditional button in ElementCard

The button is only rendered when `category === 'character'`. From CONTEXT.md: "Button appears on all character elements regardless of source."

```tsx
{category === 'character' && !isEditing && (
  <div className="mt-2" onClick={e => e.stopPropagation()}>
    {element.synced_to_characters ? (
      <span className="text-xs text-muted-foreground/60 flex items-center gap-1">
        <UserCheck className="h-3 w-3" />
        Synced
      </span>
    ) : (
      <button
        onClick={() => syncMutation.mutate(element.id)}
        disabled={syncMutation.isPending}
        className="text-xs text-emerald-400 hover:text-emerald-300 ..."
      >
        + Add to Characters
      </button>
    )}
  </div>
)}
```

### Anti-Patterns to Avoid

- **JSON path syntax in queries:** Don't use `func.json_extract` or PostgreSQL's `->>` operator to filter ListItems by content fields — use Python-side filtering for cross-dialect compatibility.
- **Optimistic update for synced_to_characters:** Do NOT optimistically update `synced_to_characters` client-side. Let `onSettled` refetch. The optimistic update would require modifying the BreakdownElement in the cache, which risks stale state if the actual DB write fails. The mutation is fast enough (no AI calls).
- **HTTP 409 for duplicate:** The CONTEXT.md explicitly says return HTTP 200 with `already_exists` status, not a 409. Do not deviate from this.
- **Committing twice:** Create PhaseData (if needed) and ListItem in a single `db.commit()` call. Use `db.flush()` to get IDs before the commit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotency guard | Custom conflict logic | `JSONResponse(status_code=200, ...)` pattern | Already established by scene link endpoint |
| Ownership verification | New ownership helper | `_verify_element_ownership()` from breakdown.py | Already verifies element AND project ownership via project_id chain |
| ListItem creation | Custom DB insert | Same pattern as `list_items.py` `create_list_item` | Handles sort_order, content, status consistently |

---

## Common Pitfalls

### Pitfall 1: `synced_to_characters` query performance — N+1 on element list

**What goes wrong:** Computing `synced_to_characters` for each element independently causes N+1 queries (one per element) when listing elements.

**Why it happens:** Naively checking per-element inside a loop.

**How to avoid:** Fetch the full synced names set ONCE before the loop. The `list_elements` endpoint currently returns all elements for a project/category in one query. Compute the synced names set once before serialization, then inject it.

**Problem:** `BreakdownElementResponse` is a Pydantic model that serializes from ORM. You cannot inject runtime data into Pydantic `from_attributes=True` easily.

**Solution:** The cleanest approach — override the `list_elements` handler to build the response manually after the ORM query:

```python
elements = query.options(selectinload(database.BreakdownElement.scene_links)).all()

# Compute synced set once
chars_pd = db.query(database.PhaseData).filter(...).first()
synced_names = _get_synced_names(db, chars_pd)

# Build responses with injected synced_to_characters
result = []
for elem in elements:
    resp = schemas.BreakdownElementResponse.model_validate(elem)
    resp.synced_to_characters = elem.name.lower() in synced_names
    result.append(resp)
return result
```

This requires `synced_to_characters` to be a non-required field with default in the schema (e.g., `synced_to_characters: bool = False`).

### Pitfall 2: PhaseData phase enum vs string

**What goes wrong:** `database.PhaseData.phase` is an Enum column (`PhaseType`). Filtering with the string `"story"` may fail depending on SQLAlchemy dialect.

**Why it happens:** The ORM column uses `Enum(PhaseType, ...)`. In tests (SQLite), enum columns are patched to `String(50)` by conftest, but in production (PostgreSQL), it's a native enum.

**How to avoid:** Filter with the enum value: `database.PhaseData.phase == "story"` works because `PhaseType` is `str, enum.Enum` — the value IS the string. Confirmed working in existing `phase_data.py` endpoint which uses string comparison. No change needed.

### Pitfall 3: `story.characters` PhaseData may not exist

**What goes wrong:** A project in progress may not have a `story.characters` PhaseData record if the user hasn't visited the Characters page yet.

**Why it happens:** PhaseData records are created lazily when users first access a phase subsection.

**How to avoid:** The sync endpoint creates the PhaseData if absent (get-or-create pattern). For `synced_to_characters` computation in `list_elements`, use `synced_names = set()` when `chars_pd is None` — meaning all elements show as unsynced (correct behavior).

### Pitfall 4: Case-insensitive match drift

**What goes wrong:** A character named "JOHN" in breakdown and "John" in Characters would not show as synced after sync.

**Why it happens:** The existing ListItem has the correctly-cased name from the sync. But if the user edits the character name in Characters phase after sync, the `synced_to_characters` flag goes stale.

**How to avoid:** Use `.lower()` on both sides for the comparison. This is the specified approach. Accept that `synced_to_characters` is best-effort advisory — it tells users what was synced, not whether the two records are still in sync.

### Pitfall 5: `db.flush()` vs `db.commit()` for PhaseData creation

**What goes wrong:** Creating PhaseData then ListItem without flushing means the ListItem's `phase_data_id` FK points to an unsaved ID.

**Why it happens:** `db.add()` doesn't persist to DB; it only stages. FKs must reference committed rows.

**How to avoid:** Call `db.flush()` after `db.add(chars_pd)` to get the assigned ID, then create the ListItem, then call `db.commit()` once at the end.

---

## Code Examples

### Full sync endpoint (backend)

```python
# Source: breakdown.py — new endpoint following scene link idempotency pattern

class SyncToCharactersResponse(BaseModel):
    status: Literal["created", "already_exists"]
    list_item_id: UUID

@router.post("/element/{element_id}/sync-to-project")
async def sync_element_to_project(
    element_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Push a character breakdown element into story.characters as a supporting ListItem.
    Idempotent: returns already_exists (200) if a ListItem with the same name exists.
    """
    element = _verify_element_ownership(db, element_id, current_user.id)

    # Locate or create story.characters PhaseData
    chars_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == str(element.project_id),
        database.PhaseData.phase == "story",
        database.PhaseData.subsection_key == "characters",
    ).first()

    if not chars_pd:
        chars_pd = database.PhaseData(
            project_id=element.project_id,
            phase="story",
            subsection_key="characters",
            content={},
            sort_order=0,
        )
        db.add(chars_pd)
        db.flush()

    # Check for existing ListItem with same name (case-insensitive)
    existing_items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == str(chars_pd.id)
    ).all()

    for item in existing_items:
        existing_name = (item.content.get("name") or "").lower()
        if existing_name == element.name.lower():
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "already_exists",
                    "list_item_id": str(item.id),
                },
            )

    # Create new supporting character ListItem
    sort_order = len(existing_items)
    new_item = database.ListItem(
        phase_data_id=chars_pd.id,
        item_type="supporting",
        content={
            "name": element.name,
            "role": element.description,
            "dialogue_style": "",
        },
        status="draft",
        sort_order=sort_order,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "created",
            "list_item_id": str(new_item.id),
        },
    )
```

### `synced_to_characters` field in schema (backend)

```python
# Source: schemas.py — BreakdownElementResponse addition

class BreakdownElementResponse(BaseModel):
    id: UUID
    project_id: UUID
    category: str
    name: str
    description: str
    metadata: Dict = Field(default_factory=dict, validation_alias="metadata_")
    source: str
    user_modified: bool
    is_deleted: bool
    sort_order: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    scene_links: List[SceneLinkResponse] = Field(default_factory=list)
    synced_to_characters: bool = False  # computed at query time, not stored

    model_config = ConfigDict(from_attributes=True)
```

### `list_elements` endpoint with synced_to_characters injection (backend)

```python
# Source: breakdown.py — list_elements modification

def _get_synced_character_names(db: Session, project_id) -> set:
    """Return lowercase names of all supporting ListItems in story.characters for a project."""
    chars_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == str(project_id),
        database.PhaseData.phase == "story",
        database.PhaseData.subsection_key == "characters",
    ).first()
    if not chars_pd:
        return set()
    items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == str(chars_pd.id)
    ).all()
    return {(item.content.get("name") or "").lower() for item in items if item.content.get("name")}


@router.get("/elements/{project_id}", response_model=List[schemas.BreakdownElementResponse])
async def list_elements(
    project_id: UUID,
    category: Optional[str] = None,
    include_deleted: bool = False,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_project_ownership(db, project_id, current_user.id)

    query = db.query(database.BreakdownElement).filter(
        database.BreakdownElement.project_id == str(project_id)
    )
    if not include_deleted:
        query = query.filter(database.BreakdownElement.is_deleted == False)
    if category:
        query = query.filter(database.BreakdownElement.category == category)
    query = query.order_by(
        database.BreakdownElement.sort_order,
        database.BreakdownElement.created_at
    )
    elements = query.options(selectinload(database.BreakdownElement.scene_links)).all()

    # Compute synced set once (only meaningful for character category)
    synced_names = set()
    if not category or category == "character":
        synced_names = _get_synced_character_names(db, project_id)

    result = []
    for elem in elements:
        resp = schemas.BreakdownElementResponse.model_validate(elem)
        resp.synced_to_characters = elem.name.lower() in synced_names
        result.append(resp)
    return result
```

### Frontend type addition

```typescript
// Source: frontend/src/types/index.ts — BreakdownElement interface

export interface BreakdownElement {
  id: string;
  project_id: string;
  category: BreakdownCategory;
  name: string;
  description: string;
  metadata: Record<string, unknown>;
  source: 'ai' | 'user';
  user_modified: boolean;
  is_deleted: boolean;
  sort_order: number;
  scene_links: SceneLink[];
  synced_to_characters: boolean;  // new field
  created_at: string;
  updated_at: string | null;
}
```

### Frontend API method

```typescript
// Source: frontend/src/lib/api.tsx — new method

async syncBreakdownElementToCharacters(
  elementId: string
): Promise<{ status: 'created' | 'already_exists'; list_item_id: string }> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/breakdown/element/${elementId}/sync-to-project`,
    {
      method: 'POST',
      headers: getHeaders(),
    }
  );
  if (!response.ok) throw new Error('Failed to sync element to characters');
  return response.json();
},
```

### Frontend ElementCard sync button

```tsx
// Source: ElementCard.tsx — syncMutation addition
const syncMutation = useMutation({
  mutationFn: () => api.syncBreakdownElementToCharacters(element.id),
  onSettled: () => {
    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category),
    });
  },
});

// In JSX — inside the non-editing view, below scene chips, conditional on category
{category === 'character' && !isEditing && (
  <div className="mt-2 flex items-center" onClick={e => e.stopPropagation()}>
    {element.synced_to_characters ? (
      <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground/60">
        <UserCheck className="h-3 w-3" />
        Synced
      </span>
    ) : (
      <button
        onClick={() => syncMutation.mutate()}
        disabled={syncMutation.isPending}
        className="text-[10px] text-emerald-400/80 hover:text-emerald-400
          disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {syncMutation.isPending ? 'Adding…' : '+ Add to Characters'}
      </button>
    )}
  </div>
)}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A — new feature | Computed `synced_to_characters` (not stored) | Phase 14 | Keeps schema clean; recomputes on each list fetch |

**No deprecated patterns** — all patterns are current project conventions.

---

## Open Questions

1. **`list_items.py` query key invalidation after sync**
   - What we know: After sync, a new ListItem is created in `story.characters`. If the user is concurrently viewing the Characters phase, their list will be stale.
   - What's unclear: The `LIST_ITEMS` query key requires a `phaseDataId` (UUID), which `ElementCard` doesn't have access to. We don't want to expose the characters `PhaseData.id` to the breakdown page.
   - Recommendation: Accept this as a known limitation for this phase. The user visiting the Characters phase after sync will get fresh data. The `LIST_ITEMS` invalidation would require passing the characters `phase_data_id` down through props, which is overengineering for this scope.

2. **Success toast for created vs already_exists**
   - What we know: CONTEXT.md says no error toast for `already_exists`, and the button goes to Synced state.
   - What's unclear: Whether a success toast is wanted for the `created` path.
   - Recommendation: Show a brief success toast ("Added to Characters") only for `created`. For `already_exists`, silently transition to Synced state. This can be a low-priority UX decision for the planner.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed via conftest.py) |
| Config file | none — runs via `pytest app/tests/test_breakdown_api.py` |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-05 | POST sync-to-project creates supporting ListItem | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject -x` | ❌ Wave 0 |
| SYNC-05 | Duplicate name returns already_exists 200 | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_sync_already_exists -x` | ❌ Wave 0 |
| SYNC-05 | synced_to_characters=true after sync | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_synced_flag_after_sync -x` | ❌ Wave 0 |
| SYNC-05 | synced_to_characters=false before sync | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_synced_flag_before_sync -x` | ❌ Wave 0 |
| SYNC-05 | Non-character element ownership enforcement | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_sync_creates_phase_data_if_missing -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/app/tests/test_breakdown_api.py::TestSyncToProject` — class does not exist yet; add to existing file covering SYNC-05 behaviors

*(conftest.py, db fixtures, and client fixture all exist — no framework setup needed)*

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection — `backend/app/api/endpoints/breakdown.py` (scene link idempotency pattern, ownership helpers, `_verify_element_ownership`)
- Direct codebase inspection — `backend/app/api/endpoints/list_items.py` (ListItem creation pattern, sort_order auto-assign)
- Direct codebase inspection — `backend/app/models/database.py` (PhaseData, ListItem, BreakdownElement ORM models)
- Direct codebase inspection — `backend/app/models/schemas.py` (BreakdownElementResponse, existing fields)
- Direct codebase inspection — `backend/app/templates/short_movie.json` (supporting character fields: `name`, `role`, `dialogue_style`)
- Direct codebase inspection — `frontend/src/components/Breakdown/ElementCard.tsx` (useMutation, optimistic update, onSettled pattern)
- Direct codebase inspection — `frontend/src/lib/constants.ts` (QUERY_KEYS.BREAKDOWN_ELEMENTS, QUERY_KEYS.BREAKDOWN_SUMMARY)
- Direct codebase inspection — `backend/app/tests/conftest.py` (SQLite in-memory engine, fixture patterns)
- Direct codebase inspection — `backend/app/tests/test_breakdown_api.py` (existing test class patterns, helper functions)
- Direct codebase inspection — `.planning/phases/14-reverse-sync/14-CONTEXT.md` (locked decisions)

### Secondary (MEDIUM confidence)

- None needed — all research derived directly from codebase.

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all patterns confirmed in existing code
- Architecture: HIGH — direct inspection of all touched files; patterns are identical to existing implementations
- Pitfalls: HIGH — identified from actual SQLite/PostgreSQL compat pattern in conftest.py and existing Pydantic field injection patterns

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable codebase; no fast-moving dependencies)
