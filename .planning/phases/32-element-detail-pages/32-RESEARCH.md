# Phase 32: Element Detail Pages - Research

**Researched:** 2026-03-22
**Domain:** Full-stack feature: per-element detail page with extended fields, scene cross-references, and reference image gallery
**Confidence:** HIGH

## Summary

Phase 32 adds dedicated detail pages for breakdown elements (characters, props, locations, wardrobe, vehicles). The existing codebase already has the BreakdownElement model with a JSONB `metadata` column that can store arbitrary key-value data, making extended fields (bio, age, role for characters; address, type, notes for locations; specs, owner, status for props) achievable without schema migration. The AssetMedia model already supports element-linked media via `element_id` FK, and upload/delete/list endpoints already exist. The primary work is (1) a new GET single-element backend endpoint, (2) an update to the existing PUT endpoint to accept extended fields via the `metadata` column, (3) a new React page component with routing, and (4) a full-width image gallery that reuses the existing MediaThumbnail/MediaUploadZone components at a larger scale.

There are no new database tables or migrations required. The JSONB `metadata` column on `breakdown_elements` is the correct place for category-specific extended fields. The existing `PUT /api/breakdown/element/{element_id}` endpoint already accepts a `metadata` dict in the request body (`BreakdownElementUpdate` schema supports `metadata: Optional[Dict]`). The frontend `BreakdownElement` TypeScript type already has `metadata: Record<string, unknown>`. This means the backend is nearly ready -- we just need a single-element GET endpoint and a frontend page with proper routing.

**Primary recommendation:** Store all extended fields in the existing `metadata` JSONB column with a category-specific schema convention. Build a new `/projects/:projectId/breakdown/elements/:elementId` route. Reuse existing media APIs and components, scaling them up for the full gallery view.

## Standard Stack

### Core (already in project -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | UI framework | Already in project |
| React Router DOM | 6.x | Routing for element detail page | Already in project |
| React Query (@tanstack/react-query) | 5.x | Data fetching/caching | Already in project |
| Tailwind CSS | 3.x | Styling | Already in project |
| Radix UI | latest | Accessible primitives (Tabs) | Already in project |
| Lucide React | latest | Icons | Already in project |
| FastAPI | 0.100+ | Backend API | Already in project |
| SQLAlchemy | 2.x | ORM | Already in project |
| Pydantic v2 | 2.x | Schemas | Already in project |

### Supporting (no new installs needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-dialog | existing | Lightbox/expand modal for images | Full-size image viewing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONB metadata for extended fields | New DB columns per category | JSONB is more flexible, avoids migration, already in use |
| Separate gallery page | Modal gallery | Full page is specified in requirements; modal would be insufficient |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
  components/
    Breakdown/
      ElementDetailPage.tsx       # NEW: full detail page component
      ElementExtendedFields.tsx   # NEW: category-specific extended fields form
      ElementSceneList.tsx        # NEW: list of scenes where element appears
      ReferenceImageGallery.tsx   # NEW: full-width image gallery with expand
      ImageLightbox.tsx           # NEW: fullscreen image viewer (expand action)
      (existing files unchanged)
  lib/
    api.tsx                       # ADD: getBreakdownElement(elementId), method
    constants.ts                  # ADD: ROUTES.ELEMENT_DETAIL, QUERY_KEYS.BREAKDOWN_ELEMENT
  types/
    index.ts                      # ADD: ElementExtendedFields type union

backend/app/
  api/endpoints/
    breakdown.py                  # ADD: GET /element/{element_id} endpoint
  models/
    schemas.py                    # ADD: BreakdownElementDetailResponse (optional, or reuse existing)
```

### Pattern 1: Category-Specific Extended Fields via JSONB Metadata

**What:** Store extended fields in the existing `metadata` JSONB column on `breakdown_elements`, keyed by a conventional schema per category.
**When to use:** Always -- this is how extended fields are persisted.
**Example:**

```python
# Character element metadata:
{
    "bio": "A former detective haunted by a cold case...",
    "age": "45",
    "role": "Protagonist"
}

# Location element metadata:
{
    "address": "123 Oak Street, Portland",
    "type": "Interior",
    "notes": "Needs to be a single-story house with a porch"
}

# Prop element metadata:
{
    "specs": "Smith & Wesson Model 10 revolver",
    "owner": "Detective Blake",
    "status": "Hero prop - needs multiples"
}
```

**Frontend type:**
```typescript
// Category-specific field definitions
export const ELEMENT_EXTENDED_FIELDS: Record<BreakdownCategory, Array<{
  key: string;
  label: string;
  type: 'text' | 'textarea';
}>> = {
  character: [
    { key: 'bio', label: 'Biography', type: 'textarea' },
    { key: 'age', label: 'Age', type: 'text' },
    { key: 'role', label: 'Role', type: 'text' },
  ],
  location: [
    { key: 'address', label: 'Address', type: 'text' },
    { key: 'type', label: 'Type', type: 'text' },
    { key: 'notes', label: 'Notes', type: 'textarea' },
  ],
  prop: [
    { key: 'specs', label: 'Specifications', type: 'textarea' },
    { key: 'owner', label: 'Owner', type: 'text' },
    { key: 'status', label: 'Status', type: 'text' },
  ],
  wardrobe: [
    { key: 'specs', label: 'Specifications', type: 'textarea' },
    { key: 'owner', label: 'Owner / Wearer', type: 'text' },
    { key: 'status', label: 'Status', type: 'text' },
  ],
  vehicle: [
    { key: 'specs', label: 'Specifications', type: 'textarea' },
    { key: 'owner', label: 'Owner / Driver', type: 'text' },
    { key: 'status', label: 'Status', type: 'text' },
  ],
};
```

### Pattern 2: Navigating from ElementCard to Detail Page

**What:** Make each ElementCard clickable to navigate to the detail page.
**When to use:** When displaying elements in the BreakdownPage and AssetsPanel.
**Example:**

```typescript
// In ElementCard.tsx -- wrap the card in a navigate handler
// Instead of onClick opening edit mode, navigate to detail page
const handleCardClick = () => {
  navigate(`/projects/${projectId}/breakdown/elements/${element.id}`);
};
```

### Pattern 3: Back Navigation from Detail Page

**What:** Detail page includes a back button returning to the breakdown page.
**When to use:** Always on the detail page.
**Example:**

```typescript
// In ElementDetailPage.tsx
<button onClick={() => navigate(ROUTES.PROJECT_BREAKDOWN(projectId))}>
  <ArrowLeft className="h-4 w-4" /> Back to Breakdown
</button>
```

### Pattern 4: Scene Cross-Reference with Navigation

**What:** The detail page lists all scenes where the element appears, each clickable to navigate to the scene.
**When to use:** Always -- ElementSceneLink junction table already tracks this.
**Example:**

```typescript
// element.scene_links is already loaded from the API
// Each link has scene_item_id which maps to a ListItem (scene)
// We need scene content (title) -- either:
// 1. Enrich the single-element API response to include scene names
// 2. Or fetch scenes client-side
// Option 1 is cleaner: join ListItem content in the backend response
```

### Anti-Patterns to Avoid
- **Do NOT add new database columns for extended fields:** The JSONB metadata column exists for this exact purpose. Category-specific columns would require a migration per new field.
- **Do NOT build inline editing on the detail page via the ElementCard pattern:** The detail page should have proper form fields, not the inline edit pattern from the card.
- **Do NOT create a separate media upload endpoint:** Reuse the existing `POST /api/media/{project_id}` with `element_id` parameter.
- **Do NOT use React Context for detail page state:** Use React Query for data fetching/caching consistent with the rest of the app.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image gallery grid | Custom grid layout | Tailwind CSS grid (`grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3`) | Responsive, zero JS |
| Image expand/lightbox | Custom modal | Radix Dialog + full-size img | Accessible, already in project |
| Media upload | New upload component | Existing `MediaUploadZone` component | Already handles drag-drop, validation, progress |
| Media thumbnails | New thumbnail renderer | Existing `MediaThumbnail` component (scaled up) | Already handles error states, click-to-expand |
| Form autosave | Custom debounce | `useMutation` with debounced trigger | Consistent with project patterns |

**Key insight:** Most of the hard UI work (media upload, thumbnails, delete confirmation) is already built in Phase 23/28 components. This phase primarily composes existing pieces into a new page layout.

## Common Pitfalls

### Pitfall 1: ElementCard Click Conflict
**What goes wrong:** ElementCard currently has `onClick={() => setIsEditing(true)}` on the card body. Adding navigation would conflict with the edit behavior.
**Why it happens:** The card was designed for inline editing, not navigation.
**How to avoid:** Change the card's primary click action to navigate. Remove or relocate the inline edit trigger (e.g., make a small edit icon that opens editing, or let the detail page be the editing surface).
**Warning signs:** Clicking an element opens inline edit instead of navigating.

### Pitfall 2: Missing Single-Element GET Endpoint
**What goes wrong:** There is no `GET /api/breakdown/element/{element_id}` endpoint. The detail page needs to fetch a single element by ID.
**Why it happens:** The breakdown API was built around list views, not detail views.
**How to avoid:** Add a `GET /api/breakdown/element/{element_id}` endpoint that returns a `BreakdownElementResponse` with scene_links eagerly loaded.
**Warning signs:** Frontend has to fetch all elements and filter client-side.

### Pitfall 3: Scene Names Not Available
**What goes wrong:** The `scene_links` on an element contain `scene_item_id` but no scene title/label. The detail page needs to show "Scene 1: INT. HOUSE - DAY" not just "Scene 1".
**Why it happens:** `ElementSceneLink` only stores the FK, not the scene content.
**How to avoid:** In the single-element GET endpoint, join through to ListItem to get scene content (title). Return enriched scene link data.
**Warning signs:** Scene list shows only "Scene 1", "Scene 2" with no context.

### Pitfall 4: Metadata Field Persistence
**What goes wrong:** Updating extended fields via the PUT endpoint doesn't merge -- it replaces the entire metadata object.
**Why it happens:** The existing `BreakdownElementUpdate` schema sends the full `metadata` dict, and the endpoint does `setattr(element, 'metadata_', value)`.
**How to avoid:** The frontend must send the complete metadata object (read-modify-write pattern). The backend approach (full replacement) is correct for JSONB columns.
**Warning signs:** Saving one field clears others.

### Pitfall 5: Route Order in App.tsx
**What goes wrong:** The new route `/projects/:projectId/breakdown/elements/:elementId` might be caught by existing route patterns.
**Why it happens:** React Router matches greedily. The existing `/projects/:projectId/:phase` could match if not ordered correctly.
**How to avoid:** Add the element detail route BEFORE the generic `/:phase` catch-all, and AFTER the specific `/breakdown` route.
**Warning signs:** Navigating to element detail shows the wrong page.

## Code Examples

### Backend: Single-Element GET Endpoint
```python
# Source: follows existing patterns in breakdown.py
@router.get("/element/{element_id}", response_model=schemas.BreakdownElementResponse)
async def get_element(
    element_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single breakdown element with scene links."""
    element = _verify_element_ownership(db, element_id, current_user.id)
    # Eagerly load scene_links
    db.query(database.BreakdownElement).options(
        selectinload(database.BreakdownElement.scene_links)
    ).filter(database.BreakdownElement.id == str(element.id)).first()
    return element
```

### Frontend: API Method for Single Element
```typescript
// Source: follows existing api.tsx patterns
async getBreakdownElement(elementId: string): Promise<BreakdownElement> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/breakdown/element/${elementId}`,
    { headers: getHeaders() }
  );
  if (!response.ok) throw new Error('Failed to fetch element');
  return response.json();
},
```

### Frontend: Route Registration
```typescript
// In App.tsx -- add BEFORE the /:phase catch-all
<Route path="/projects/:projectId/breakdown/elements/:elementId" element={<ElementDetailRoute />} />
<Route path="/projects/:projectId/breakdown" element={<BreakdownLayout />} />
```

### Frontend: Extended Fields Form
```typescript
// Source: follows project's form patterns
function ElementExtendedFields({ element, onSave }: Props) {
  const fieldDefs = ELEMENT_EXTENDED_FIELDS[element.category] || [];
  const [values, setValues] = useState<Record<string, string>>(
    () => element.metadata as Record<string, string> || {}
  );

  const handleChange = (key: string, value: string) => {
    setValues(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    onSave({ metadata: values });
  };

  return (
    <div className="space-y-4">
      {fieldDefs.map(field => (
        <div key={field.key}>
          <label className="text-xs font-semibold text-muted-foreground uppercase">
            {field.label}
          </label>
          {field.type === 'textarea' ? (
            <textarea
              value={values[field.key] || ''}
              onChange={e => handleChange(field.key, e.target.value)}
              onBlur={handleSave}
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm"
              rows={3}
            />
          ) : (
            <input
              value={values[field.key] || ''}
              onChange={e => handleChange(field.key, e.target.value)}
              onBlur={handleSave}
              className="w-full bg-background border border-border rounded px-3 py-2 text-sm"
            />
          )}
        </div>
      ))}
    </div>
  );
}
```

### Frontend: Image Gallery with Expand
```typescript
// Larger gallery grid compared to AssetElementCard's 3-col tiny thumbnails
<div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
  {images.map(img => (
    <div key={img.id} className="relative group aspect-square">
      <img
        src={img.thumbnail_path || img.file_path}
        alt={img.original_filename}
        className="w-full h-full object-cover rounded-lg border border-border/50
          cursor-pointer hover:opacity-80 transition-opacity"
        onClick={() => setExpandedImage(img)}
      />
      <button
        onClick={() => handleDelete(img.id, img.original_filename)}
        className="absolute top-2 right-2 h-7 w-7 flex items-center justify-center
          bg-background/80 hover:bg-destructive hover:text-destructive-foreground
          rounded-md text-muted-foreground transition-colors opacity-0 group-hover:opacity-100"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  ))}
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Inline editing only (ElementCard) | Detail page with extended fields | Phase 32 | Full per-element editing surface |
| Small 3-col thumbnail grid (80px) | Full responsive gallery (aspect-square) | Phase 32 | Better reference image UX |
| No single-element API | GET /element/{id} | Phase 32 | Direct element fetching |

**Existing infrastructure leveraged:**
- `BreakdownElement.metadata_` JSONB column: already exists, already handled by PUT endpoint
- `AssetMedia` with `element_id` FK: already exists, list/upload/delete endpoints already work
- `MediaThumbnail`, `MediaUploadZone`, `AudioPlayer`: reusable components
- `ElementSceneLink` with `scene_item_id`: already provides scene cross-reference data

## Open Questions

1. **Scene Name Enrichment**
   - What we know: `ElementSceneLink` has `scene_item_id` FK to `list_items`. ListItem `content` JSON has a `title` field.
   - What's unclear: Whether to join in backend (enriched response) or fetch scenes client-side.
   - Recommendation: Join in backend for the single-element endpoint. Return scene links with an added `scene_title` field. This avoids an extra round-trip.

2. **Wardrobe and Vehicle Extended Fields**
   - What we know: The requirements specify character/location/prop extended fields explicitly.
   - What's unclear: What fields wardrobe and vehicle categories should have.
   - Recommendation: Use the same specs/owner/status pattern as props for both wardrobe and vehicles. This can be refined later without migration.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + FastAPI TestClient (SQLite in-memory) |
| Config file | backend/app/tests/conftest.py |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_breakdown_api.py -x -q` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDP-01 | Navigate to element detail page, shows name/category/description/scenes/extended fields | integration (frontend manual) | Manual: click element -> verify page content | N/A (frontend) |
| EDP-01 | GET /element/{id} returns single element with scene_links | unit | `cd backend && python -m pytest app/tests/test_breakdown_api.py::TestGetElement -x` | Wave 0 |
| EDP-02 | Reference image gallery shows media, supports upload/delete/expand | integration (frontend manual) | Manual: upload image -> verify gallery -> expand -> delete | N/A (frontend) |
| EDP-02 | PUT /element/{id} with metadata persists extended fields | unit | `cd backend && python -m pytest app/tests/test_breakdown_api.py::TestUpdateElementMetadata -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_breakdown_api.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_breakdown_api.py::TestGetElement` -- test class for GET /element/{id} endpoint
- [ ] `app/tests/test_breakdown_api.py::TestUpdateElementMetadata` -- test for metadata persistence via PUT

*(Existing test infrastructure (conftest.py, TestClient, db_session, mock_auth_headers) covers all shared fixtures needed.)*

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EDP-01 | Clicking any element navigates to detail page showing name, category, description, all scenes, and extended fields (character: bio/age/role; location: address/type/notes; prop: specs/owner/status). Changes persist on refresh. | JSONB metadata column already exists for extended fields; existing PUT endpoint supports metadata updates; need new GET single-element endpoint; need new React route and page component; ElementCard click behavior needs to change from inline-edit to navigate |
| EDP-02 | Full reference image gallery (larger than assets panel) with upload, delete, and expand actions | Existing AssetMedia model with element_id FK; existing upload/delete/list API endpoints; existing MediaThumbnail and MediaUploadZone components to reuse at larger scale; need ImageLightbox component for expand action |
</phase_requirements>

## Sources

### Primary (HIGH confidence)
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/models/database.py` -- BreakdownElement model with metadata_ JSONB column, AssetMedia with element_id FK
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/models/schemas.py` -- BreakdownElementUpdate already accepts Optional[Dict] metadata, BreakdownElementResponse serializes metadata
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/api/endpoints/breakdown.py` -- PUT endpoint handles metadata, no GET single-element endpoint exists
- `/Users/yvesfogel/Desktop/screenwriting-assistant/backend/app/api/endpoints/media.py` -- Upload/list/delete endpoints with element_id filtering
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/components/Breakdown/ElementCard.tsx` -- Current inline-edit click behavior, needs navigation change
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/components/Breakdown/AssetElementCard.tsx` -- Media display pattern with thumbnails
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/components/Breakdown/MediaUploadZone.tsx` -- Upload component to reuse
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/components/Breakdown/MediaThumbnail.tsx` -- Thumbnail component to reuse at larger scale
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/App.tsx` -- Routing structure, where to add new route
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/types/index.ts` -- BreakdownElement type with metadata: Record<string, unknown>
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/lib/api.tsx` -- No getBreakdownElement(id) method exists
- `/Users/yvesfogel/Desktop/screenwriting-assistant/frontend/src/lib/constants.ts` -- ROUTES, QUERY_KEYS, BREAKDOWN_CATEGORIES patterns

### Secondary (MEDIUM confidence)
- `/Users/yvesfogel/Desktop/screenwriting-assistant/.planning/ROADMAP.md` -- Phase 32 requirements and success criteria

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies, all existing libraries
- Architecture: HIGH - patterns directly derived from inspecting existing code
- Pitfalls: HIGH - identified from actual code inspection (missing endpoint, click conflict, route ordering)

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable -- no external library changes)
