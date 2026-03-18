# Phase 13: Breakdown Page - Research

**Researched:** 2026-03-14
**Domain:** React frontend — dedicated page with React Query, Radix UI, inline editing, optimistic updates
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Dedicated Breakdown page accessible from project workspace navigation (not a template phase) | New route `/projects/:projectId/breakdown` in App.tsx; new "Breakdown" tab injected into PhaseNavigation alongside phase tabs |
| UI-02 | Category tabs (Characters, Locations, Props, Wardrobe, Vehicles) with count badges | `counts_by_category` from `GET /api/breakdown/summary/:projectId`; render with Radix `@radix-ui/react-tabs` (already installed) |
| UI-03 | Master list per category: name, description, scene count, source badge (AI/User), user-modified indicator | `BreakdownElementResponse` has `source`, `user_modified`, `scene_links` (count derived from scene_links length or separate count field) |
| UI-04 | Inline editing of element names and descriptions | Local `useState` edit mode per card; `useMutation` PUT on blur/confirm; optimistic update pattern from existing `RepeatableCardsView` |
| UI-05 | Scene chips showing linked scenes; clickable to navigate to scene | `scene_links` on element includes `scene_item_id`; navigate to `/projects/:projectId/write/scenes/:itemId` |
| UI-06 | "Extract Breakdown" button for first extraction; staleness banner with "Refresh" when outdated | `is_stale` from summary endpoint; `POST /api/breakdown/extract/:projectId` triggers extraction |
| UI-07 | Add element dialog for manually creating new elements | Radix `Dialog.Root` pattern (established in `CreateProjectModal`); `POST /api/breakdown/elements/:projectId` |
| UI-08 | Empty state with clear CTA when no breakdown exists yet | `total_elements === 0 && !last_run` condition; shows "Extract Breakdown" button |
</phase_requirements>

---

## Summary

Phase 13 adds a dedicated Breakdown page to the project workspace — a frontend-only phase consuming the already-complete breakdown API (Phases 10-12). The page sits outside the template phase system: it gets its own React Router route and a new "Breakdown" tab grafted onto `PhaseNavigation`. All backend data is in place; this phase is purely a UI construction job.

The primary technical challenges are: (1) navigating from two distinct navigation entry points (phase tabs + breakdown tab) while keeping state clean, (2) implementing inline edit-on-click with optimistic updates for element name/description, (3) scene chip navigation that correctly resolves scene item IDs to workspace URLs, and (4) the extraction loading UX — extraction is synchronous (returns `BreakdownRunResponse` directly) but may take 5-15 seconds.

The project already has all required dependencies: `@radix-ui/react-tabs` and `@radix-ui/react-dialog` are installed, React Query v5 is the state layer, Tailwind + Lucide are the styling/icon systems. No new packages are needed.

**Primary recommendation:** Build BreakdownPage as a self-contained route component outside the `ProjectWorkspace` shell, sharing only `PhaseNavigation` (extended with a breakdown tab) and the global query client. Keep API client additions in `api.tsx`, types in `types/index.ts`, and query keys in `constants.ts` following established conventions.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tanstack/react-query` | ^5.20.1 | Data fetching, caching, mutations | Project standard — all data flows through React Query |
| `@radix-ui/react-tabs` | ^1.0.4 | Category tabs with accessibility | Already installed; project uses Radix primitives for UI |
| `@radix-ui/react-dialog` | ^1.0.5 | AddElementDialog modal | Established pattern in `CreateProjectModal.tsx` |
| `react-router-dom` | ^6.21.3 | Route for `/projects/:projectId/breakdown` | Project standard routing |
| `lucide-react` | ^0.314.0 | Icons (Sparkles, RefreshCw, Plus, Pencil, Trash2, etc.) | Project standard icon set |
| `tailwindcss` | ^3.4.1 | All styling | Project standard; uses HSL CSS variables |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `clsx` + `tailwind-merge` | installed | Conditional class composition | Already used project-wide for dynamic classes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Radix Tabs | Custom tab buttons | Radix gives accessible keyboard navigation for free; custom buttons are faster to build but miss ARIA patterns |
| React Query mutations | Local fetch + useState | React Query provides automatic cache invalidation and loading states; manual fetch is more code with no benefit |

**Installation:** No new packages needed. All dependencies already in `frontend/package.json`.

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── types/index.ts              # Add BreakdownElement, BreakdownSummary, BreakdownRun types
├── lib/
│   ├── api.tsx                 # Add 5 breakdown API methods
│   └── constants.ts            # Add QUERY_KEYS.BREAKDOWN_*, BREAKDOWN_CATEGORIES constant
├── components/
│   ├── Workspace/
│   │   ├── PhaseNavigation.tsx # Extend with optional breakdownTab prop
│   │   └── ProjectWorkspace.tsx # Add breakdown tab handler
│   └── Breakdown/              # New directory
│       ├── BreakdownPage.tsx       # Top-level page component
│       ├── CategoryTabs.tsx        # Radix Tabs wrapper with count badges
│       ├── ElementList.tsx         # List of ElementCards for a category
│       ├── ElementCard.tsx         # Single element with inline editing
│       ├── AddElementDialog.tsx    # Create element modal
│       └── StalenessBar.tsx        # "Breakdown is outdated" banner
└── App.tsx                     # Add route: /projects/:projectId/breakdown
```

### Pattern 1: New Route Outside ProjectWorkspace
**What:** BreakdownPage gets its own route entry in App.tsx, not nested inside ProjectWorkspace. It reads `projectId` from `useParams`, fetches the project for the title, and renders PhaseNavigation (extended) + its own content.
**When to use:** Breakdown is NOT a template phase — it has no `subsection`, no `PhaseData`, no sidebar chat. Reusing ProjectWorkspace would require hacking around all those assumptions.
**Example:**
```typescript
// App.tsx addition
<Route path="/projects/:projectId/breakdown" element={<BreakdownPage />} />

// BreakdownPage.tsx skeleton
export function BreakdownPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { data: project } = useQuery({
    queryKey: QUERY_KEYS.PROJECT_V2(projectId!),
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });

  const { data: summary } = useQuery({
    queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId!),
    queryFn: () => api.getBreakdownSummary(projectId!),
    enabled: !!projectId,
  });

  // ... render PhaseNavigation + CategoryTabs + ElementList
}
```

### Pattern 2: Extending PhaseNavigation with Breakdown Tab
**What:** Add an optional `onBreakdownClick` + `isBreakdownActive` prop pair to `PhaseNavigation`. The breakdown tab is rendered after all phase tabs, separated by a vertical divider. ProjectWorkspace passes these props; BreakdownPage passes `isBreakdownActive={true}`.
**When to use:** Breakdown must appear in the same navigation bar as phase tabs but must navigate to a completely different route.
**Example:**
```typescript
// PhaseNavigation.tsx — prop additions
interface PhaseNavigationProps {
  // ... existing props
  onBreakdownClick?: () => void;
  isBreakdownActive?: boolean;
}

// In the nav, after phase tabs:
{onBreakdownClick && (
  <>
    <div className="w-px h-4 bg-border mx-2" />   {/* divider */}
    <button
      onClick={onBreakdownClick}
      className={`
        flex items-center gap-2 px-4 py-3 text-xs font-semibold uppercase tracking-wider
        transition-all duration-200 border-b-2 -mb-px
        ${isBreakdownActive
          ? 'text-amber-400 border-amber-400'
          : 'border-transparent text-muted-foreground/40 hover:text-muted-foreground/70'
        }
      `}
    >
      <ListChecks className="h-3.5 w-3.5" />
      <span>Breakdown</span>
    </button>
  </>
)}
```

### Pattern 3: React Query for Breakdown Data
**What:** Two primary queries per page load — `breakdown/summary` (counts + staleness) and `breakdown/elements` (filtered by active category). Elements query is per-category using `category` as query key dimension.
**When to use:** Summary is cheap and drives the tab badges; element list is filtered server-side to avoid loading all categories at once.
**Example:**
```typescript
// Hooks
const { data: summary } = useQuery({
  queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId),
  queryFn: () => api.getBreakdownSummary(projectId),
  staleTime: 30_000,  // 30s — breakdown changes only on extract/edit
});

const { data: elements = [], isLoading } = useQuery({
  queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, activeCategory),
  queryFn: () => api.getBreakdownElements(projectId, activeCategory),
  enabled: !!projectId,
});
```

### Pattern 4: Inline Editing with Optimistic Updates
**What:** ElementCard tracks local `isEditing` boolean + `editName`/`editDesc` state. On blur or Enter key, fires `useMutation` PUT. On `onMutate`, push optimistic update to query cache. On `onError`, rollback.
**When to use:** Matches the existing `SnippetCard` inline edit pattern; gives instant feedback.
**Example:**
```typescript
const updateMutation = useMutation({
  mutationFn: ({ id, name, description }: { id: string; name: string; description: string }) =>
    api.updateBreakdownElement(id, { name, description }),
  onMutate: async ({ id, name, description }) => {
    await queryClient.cancelQueries({ queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category) });
    const previous = queryClient.getQueryData(QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category));
    queryClient.setQueryData(QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category), (old: BreakdownElement[]) =>
      old.map(el => el.id === id ? { ...el, name, description, user_modified: true } : el)
    );
    return { previous };
  },
  onError: (_err, _vars, context) => {
    queryClient.setQueryData(QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category), context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId) });
  },
});
```

### Pattern 5: Soft-Delete with Optimistic Update
**What:** DELETE is soft-delete on the backend. On client, optimistically remove element from list immediately.
**Example:**
```typescript
const deleteMutation = useMutation({
  mutationFn: (elementId: string) => api.deleteBreakdownElement(elementId),
  onMutate: async (elementId) => {
    await queryClient.cancelQueries({ queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category) });
    const previous = queryClient.getQueryData(QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category));
    queryClient.setQueryData(QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category),
      (old: BreakdownElement[]) => old.filter(el => el.id !== elementId)
    );
    return { previous };
  },
  onError: (_err, _vars, context) => {
    queryClient.setQueryData(QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category), context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, category) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId) });
  },
});
```

### Pattern 6: Extraction Loading UX
**What:** Extraction (`POST /api/breakdown/extract/:projectId`) is synchronous and may take 5-15 seconds. Use `isPending` from mutation to show a spinner with informative copy. Invalidate both summary and elements on success.
**Example:**
```typescript
const extractMutation = useMutation({
  mutationFn: () => api.triggerBreakdownExtraction(projectId),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_SUMMARY(projectId) });
    // Invalidate all category element queries
    BREAKDOWN_CATEGORIES.forEach(cat => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, cat.value) });
    });
  },
});
```

### Pattern 7: Scene Chip Navigation
**What:** Each element has `scene_links` — an array from the backend with `scene_item_id`. Scene chips navigate to the scene editor. The URL pattern is `/projects/:projectId/write/scenes/:itemId`.
**Note:** The backend API (`GET /api/breakdown/elements`) returns `BreakdownElementResponse` but the current schema does NOT include `scene_links` directly in the response — only element fields. Scene links are accessible via the element's related data. Check whether the elements endpoint needs to embed scene link counts or if a separate summary is sufficient (the `summary` endpoint gives total counts, not per-element scene counts).

**IMPORTANT gap to confirm:** `BreakdownElementResponse` in `schemas.py` does NOT include a `scene_links` field or `scene_count` — only the ORM model has the relationship. The plan will need to either:
1. Add `scene_links` (array of `{scene_item_id, context}`) to `BreakdownElementResponse`, OR
2. Derive scene count from a separate call per element (N+1, bad), OR
3. Add a `scene_count: int` computed field to `BreakdownElementResponse`

**Recommendation:** Extend `BreakdownElementResponse` to include `scene_links: List[SceneLinkResponse]` with a `SceneLinkResponse` schema (id, scene_item_id, context, source). This is a small backend addition in Plan 13-01.

### Anti-Patterns to Avoid
- **Nesting BreakdownPage inside ProjectWorkspace:** Workspace assumes template phases with subsections. Breakdown has neither. Build a separate route.
- **Fetching all elements then filtering client-side:** The elements endpoint accepts a `category` query param — use it. Avoids loading 200+ elements when user views Characters tab.
- **Polling for extraction completion:** Extraction is synchronous (returns 200 with result). Do NOT poll. Just wait for `isPending` to clear.
- **Using React state for active category:** Use URL params (`/projects/:projectId/breakdown?category=character`) OR React state. URL is preferred for shareability and back-button support.
- **One query key for all element categories:** Use `['breakdown-elements', projectId, category]` so tab switches don't re-use stale data from other categories.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal/dialog | Custom overlay + portal | `@radix-ui/react-dialog` (installed) | Focus trap, escape key, aria-dialog, overlay click dismiss — all handled |
| Tab panels | Custom div-based tabs | `@radix-ui/react-tabs` (installed) | Keyboard nav (arrow keys), aria-tabpanel, roving tabindex |
| Confirmation on delete | Custom confirm state machine | Simple two-click pattern from `SnippetCard.tsx` | Already proven pattern in codebase |
| Loading spinners | Custom CSS animation | `lucide-react` `Loader2` + `animate-spin` | Consistent with rest of app |

---

## Common Pitfalls

### Pitfall 1: scene_links Missing From API Response
**What goes wrong:** ElementCard tries to render scene chips but `element.scene_links` is undefined. The `BreakdownElementResponse` Pydantic schema does NOT include scene links.
**Why it happens:** SQLAlchemy relationship exists on ORM model but was not added to the Pydantic response schema.
**How to avoid:** Plan 13-01 MUST add a `SceneLinkResponse` schema and embed `scene_links: List[SceneLinkResponse]` in `BreakdownElementResponse`. This is a backend schema change, not a frontend workaround.
**Warning signs:** TypeScript error on `element.scene_links` — catches this at compile time.

### Pitfall 2: Route Collision with ProjectWorkspace
**What goes wrong:** The route `/projects/:projectId/breakdown` conflicts with the existing wildcard route `/projects/:projectId/:phase` because `breakdown` matches `:phase`.
**Why it happens:** React Router matches routes in order; `/:phase` will match "breakdown" before the dedicated route if the dedicated route is listed after.
**How to avoid:** In App.tsx, place the `/projects/:projectId/breakdown` route BEFORE the `/:phase` routes.
**Warning signs:** Breakdown page renders the ProjectWorkspace component instead; phase navigation breaks.

### Pitfall 3: Stale Count Badges After Edit/Delete
**What goes wrong:** User deletes an element; the count badge on the tab still shows the old count.
**Why it happens:** Summary and element queries are separate; invalidating only elements doesn't update the summary.
**How to avoid:** Always invalidate BOTH `BREAKDOWN_SUMMARY` and `BREAKDOWN_ELEMENTS` in mutation `onSettled`.

### Pitfall 4: Extraction Appearing Hung
**What goes wrong:** User clicks "Extract Breakdown" and nothing visible happens for 10 seconds; they click again, triggering double extraction.
**Why it happens:** No loading indicator or disabled state during extraction.
**How to avoid:** Disable the button immediately using `extractMutation.isPending`; show `Loader2` spinner with "Extracting..." copy.

### Pitfall 5: Navigate to Scene Requires scene_item_id, Not Element ID
**What goes wrong:** Scene chip navigates to `/projects/:projectId/write/scenes/[element-id]` instead of the actual scene list item ID.
**Why it happens:** Confusing element ID with scene link's `scene_item_id`.
**How to avoid:** In ElementCard, use `link.scene_item_id` (not `element.id`) when constructing the navigate URL.

### Pitfall 6: Radix Tabs Default Value Mismatch
**What goes wrong:** `Tabs.Root` uses `defaultValue` but the first category with results is not "character"; empty category tab shows first.
**Why it happens:** Static `defaultValue="character"` even when no characters extracted.
**How to avoid:** Compute `defaultCategory` as the first category with `counts_by_category[cat] > 0`, or default to "character" regardless and show empty state within the tab.

---

## Code Examples

### TypeScript Types to Add (types/index.ts)
```typescript
// Source: backend/app/models/schemas.py BreakdownElementResponse
export interface SceneLink {
  id: string;
  scene_item_id: string;
  context: string;
  source: 'ai' | 'user';
}

export type BreakdownCategory = 'character' | 'location' | 'prop' | 'wardrobe' | 'vehicle';

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
  scene_links: SceneLink[];   // requires backend schema extension
  created_at: string;
  updated_at: string | null;
}

export interface BreakdownRun {
  id: string;
  project_id: string;
  status: string;
  config: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  elements_created: number;
  elements_updated: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface BreakdownSummary {
  project_id: string;
  is_stale: boolean;
  total_elements: number;
  counts_by_category: Record<BreakdownCategory, number>;
  last_run: BreakdownRun | null;
}

export interface BreakdownElementCreate {
  category: BreakdownCategory;
  name: string;
  description: string;
}
```

### API Client Functions to Add (lib/api.tsx)
```typescript
// Source: backend/app/api/endpoints/breakdown.py

async getBreakdownSummary(projectId: string): Promise<BreakdownSummary> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/breakdown/summary/${projectId}`, {
    headers: getHeaders()
  });
  if (!response.ok) throw new Error('Failed to fetch breakdown summary');
  return response.json();
},

async getBreakdownElements(projectId: string, category?: string): Promise<BreakdownElement[]> {
  const url = category
    ? `${API_BASE_URL}/breakdown/elements/${projectId}?category=${category}`
    : `${API_BASE_URL}/breakdown/elements/${projectId}`;
  const response = await fetchWithTimeout(url, { headers: getHeaders() });
  if (!response.ok) throw new Error('Failed to fetch breakdown elements');
  return response.json();
},

async createBreakdownElement(projectId: string, data: BreakdownElementCreate): Promise<BreakdownElement> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/breakdown/elements/${projectId}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create breakdown element');
  return response.json();
},

async updateBreakdownElement(elementId: string, data: { name?: string; description?: string }): Promise<BreakdownElement> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/breakdown/element/${elementId}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update breakdown element');
  return response.json();
},

async deleteBreakdownElement(elementId: string): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/breakdown/element/${elementId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to delete breakdown element');
},

async triggerBreakdownExtraction(projectId: string): Promise<BreakdownRun> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/breakdown/extract/${projectId}`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to trigger extraction');
  return response.json();
},
```

### Query Keys to Add (lib/constants.ts)
```typescript
BREAKDOWN_SUMMARY: (projectId: string) => ['breakdown-summary', projectId],
BREAKDOWN_ELEMENTS: (projectId: string, category?: string) => ['breakdown-elements', projectId, category],
```

### BREAKDOWN_CATEGORIES Constant
```typescript
// lib/constants.ts
export const BREAKDOWN_CATEGORIES = [
  { value: 'character' as const, label: 'Characters' },
  { value: 'location' as const, label: 'Locations' },
  { value: 'prop' as const, label: 'Props' },
  { value: 'wardrobe' as const, label: 'Wardrobe' },
  { value: 'vehicle' as const, label: 'Vehicles' },
] as const;
```

### Radix Tabs Pattern (CategoryTabs.tsx)
```typescript
// Source: @radix-ui/react-tabs v1.0.4 API
import * as Tabs from '@radix-ui/react-tabs';

<Tabs.Root value={activeCategory} onValueChange={setActiveCategory}>
  <Tabs.List className="flex items-center gap-1 border-b border-border px-6">
    {BREAKDOWN_CATEGORIES.map(cat => (
      <Tabs.Trigger
        key={cat.value}
        value={cat.value}
        className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider
          border-b-2 -mb-px transition-colors
          data-[state=active]:border-amber-400 data-[state=active]:text-amber-400
          data-[state=inactive]:border-transparent data-[state=inactive]:text-muted-foreground/60
          hover:text-muted-foreground"
      >
        {cat.label}
        <span className="ml-1 text-[10px] bg-muted/60 px-1.5 py-0.5 rounded-full">
          {summary?.counts_by_category[cat.value] ?? 0}
        </span>
      </Tabs.Trigger>
    ))}
  </Tabs.List>

  {BREAKDOWN_CATEGORIES.map(cat => (
    <Tabs.Content key={cat.value} value={cat.value} className="outline-none">
      <ElementList projectId={projectId} category={cat.value} />
    </Tabs.Content>
  ))}
</Tabs.Root>
```

### Radix Dialog Pattern for AddElementDialog (reusing established pattern)
```typescript
// Source: frontend/src/components/Projects/CreateProjectModal.tsx (established pattern)
import * as Dialog from '@radix-ui/react-dialog';

<Dialog.Root open={open} onOpenChange={onOpenChange}>
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
    <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[480px]
      -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border p-0
      shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-hidden">
      <div className="flex items-center justify-between px-6 pt-6 pb-4">
        <Dialog.Title className="font-display text-xl font-semibold text-foreground">
          Add Element
        </Dialog.Title>
        <Dialog.Close asChild>
          <button className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </Dialog.Close>
      </div>
      {/* form content */}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

### Staleness Banner Pattern
```typescript
// Conditional banner shown when summary.is_stale === true
{summary?.is_stale && (
  <div className="flex items-center justify-between px-6 py-3 bg-amber-500/10 border-b border-amber-500/20">
    <div className="flex items-center gap-2 text-sm text-amber-400">
      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
      <span>Your breakdown may be outdated — script has changed since last extraction.</span>
    </div>
    <button
      onClick={() => extractMutation.mutate()}
      disabled={extractMutation.isPending}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-amber-400
        bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 rounded-md transition-colors"
    >
      {extractMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
      {extractMutation.isPending ? 'Extracting...' : 'Refresh'}
    </button>
  </div>
)}
```

### Empty State Pattern
```typescript
// Shown when total_elements === 0 and no active extraction
{summary?.total_elements === 0 && !extractMutation.isPending && (
  <div className="flex flex-col items-center justify-center py-24 text-center">
    <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-5">
      <ListChecks className="h-8 w-8 text-amber-500/60" />
    </div>
    <h3 className="text-lg font-semibold text-foreground mb-2">No breakdown yet</h3>
    <p className="text-sm text-muted-foreground max-w-xs mb-6">
      Extract production elements from your screenplay — characters, locations, props, wardrobe, and vehicles.
    </p>
    <button
      onClick={() => extractMutation.mutate()}
      className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold
        bg-amber-500 hover:bg-amber-400 text-white rounded-lg transition-colors"
    >
      <Sparkles className="h-4 w-4" />
      Extract Breakdown
    </button>
  </div>
)}
```

---

## Backend Schema Extension Required (Plan 13-01)

This is a small backend change needed before frontend work begins in Plan 13-02.

**Problem:** `BreakdownElementResponse` in `backend/app/models/schemas.py` lacks `scene_links`. The frontend needs scene links to render scene chips and navigate to scenes.

**Solution:** Add to `schemas.py`:
```python
class SceneLinkResponse(BaseModel):
    id: UUID
    scene_item_id: UUID
    context: str
    source: str

    model_config = ConfigDict(from_attributes=True)

# Extend BreakdownElementResponse:
class BreakdownElementResponse(BaseModel):
    # ... existing fields ...
    scene_links: List[SceneLinkResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
```

SQLAlchemy will eager-load `scene_links` if the relationship is accessed during the response serialization. For performance, add `joinedload` to the list query or use `selectinload`.

**Risk:** LOW — additive change to an existing schema. Existing tests for the elements endpoint will still pass (new field just defaults to `[]`).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom tab divs | `@radix-ui/react-tabs` | Already in use (installed) | Accessible tabs with zero custom code |
| Promise-based mutations with local state | `useMutation` from React Query v5 | Already in use | Automatic loading/error states, cache invalidation |
| Separate modal state management | Radix Dialog with controlled `open` | Already in use (CreateProjectModal) | Portal rendering, focus trap, keyboard dismiss |

---

## Open Questions

1. **Scene link navigation destination**
   - What we know: Scene items exist in `write` phase, `scenes` subsection as `ListItem` records
   - What's unclear: What URL pattern does `IndividualEditorView` use to navigate to a specific scene? The route `/projects/:projectId/write/scenes/:itemId` is inferred from `ProjectWorkspace` pattern but needs confirmation.
   - Recommendation: Check how `OrderedListView` or `IndividualEditorView` constructs its item deep-link URL. The route pattern in App.tsx is `/projects/:projectId/:phase/:subsectionKey/:itemId` — confirm this is the correct destination for scene navigation.

2. **Whether to lazy-load element tab content**
   - What we know: Radix Tabs renders all `Tabs.Content` panels but can lazy-mount them
   - What's unclear: With 200+ elements across 5 categories, should we only fetch the active category's elements?
   - Recommendation: Yes — use per-category queries that only run when the category is active (`enabled: activeCategory === cat.value`). This avoids 5 concurrent API calls on page load.

3. **Scene chip label — what to display?**
   - What we know: `scene_item_id` links to a `ListItem`; `ListItem.content` is a JSON object with scene fields (e.g., `scene_number`, `title`, `setting`)
   - What's unclear: Which field of `ListItem.content` to display as the chip label
   - Recommendation: Display `content.title` or `content.scene_number` — check `OrderedListView` for how scenes are labeled in the existing UI.

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`. No frontend test framework is installed (no vitest, jest, or testing-library in `package.json`). Backend uses pytest with a FastAPI test client. The validation strategy reflects this reality.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (existing infrastructure in `backend/app/tests/`) |
| Frontend framework | None installed — Wave 0 of Plan 13-01 must install if tests desired |
| Backend quick run | `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q` |
| Backend full suite | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` |
| Frontend type check | `cd frontend && npm run build` (tsc + vite build catches type errors) |
| Frontend lint | `cd frontend && npm run lint` |

### What Automated Tests Can Verify

**Plan 13-01 (types, API client, query hooks, route, nav tab):**
- Backend: `SceneLinkResponse` fields and `BreakdownElementResponse.scene_links` round-trips via existing `test_breakdown_api.py` tests (add assertion for `scene_links` field presence in element list response)
- Frontend: TypeScript compilation (`npm run build`) catches type errors in new interfaces, API client function signatures, and `QUERY_KEYS` additions
- No runtime unit tests without a test framework

**Plan 13-02 (BreakdownPage layout, CategoryTabs, ElementCard, StalenessBar):**
- No automated component rendering tests without vitest/testing-library
- TypeScript compilation validates prop types and React Query usage
- ESLint catches unused variables and hooks violations
- Manual visual testing required for all rendering

**Plan 13-03 (AddElementDialog, empty state, extraction trigger, soft-delete with optimistic updates):**
- Backend: Add `test_breakdown_api.py` tests for the `POST /breakdown/elements` create endpoint (conflict/restore logic is already tested; verify 201 response shape includes `scene_links`)
- Frontend: TypeScript confirms mutation signatures and query invalidation patterns
- Optimistic update rollback: requires human testing (break network, verify UI reverts)

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| UI-01 | Breakdown tab in navigation | Manual visual | `npm run build` (type check) | No route testing without framework |
| UI-02 | Category tabs with count badges | Manual visual | `npm run build` | Counts from summary API — verify with backend test |
| UI-03 | Element list with all fields | Manual visual + TypeScript | `npm run build` | `scene_links` field needs backend test |
| UI-04 | Inline editing saves correctly | Manual + backend API test | `pytest app/tests/test_breakdown_api.py -k update -x` | PUT endpoint already tested; frontend edit flow is manual |
| UI-05 | Scene chips navigate correctly | Manual visual | N/A | Navigation requires running app |
| UI-06 | Extract/Refresh buttons with staleness banner | Manual + backend API test | `pytest app/tests/test_staleness.py -x` | Staleness flag already tested |
| UI-07 | Add element dialog creates element | Manual + backend API test | `pytest app/tests/test_breakdown_api.py -k create -x` | POST endpoint already tested |
| UI-08 | Empty state CTA triggers extraction | Manual visual | N/A | Requires running app |

### Backend Schema Test Addition (Wave 0 for Plan 13-01)
The existing `test_breakdown_api.py` should be extended with one assertion:

```python
# Add to existing test_list_elements test
def test_element_response_includes_scene_links(client, mock_auth_headers, db_session):
    """Verify BreakdownElementResponse includes scene_links field."""
    project_id = _create_project_via_api(client, mock_auth_headers)
    resp = client.get(f"/api/breakdown/elements/{project_id}", headers=mock_auth_headers)
    assert resp.status_code == 200
    # scene_links must be present as a list (empty for new elements)
    for element in resp.json():
        assert "scene_links" in element
        assert isinstance(element["scene_links"], list)
```

### Frontend Test Framework (Wave 0 Gap — Optional)
If component-level testing is desired, install vitest + @testing-library/react:
```bash
cd frontend
npm install --save-dev vitest @testing-library/react @testing-library/user-event jsdom
```
Add to `vite.config.ts`:
```typescript
test: { environment: 'jsdom', globals: true }
```
This is OPTIONAL for Phase 13. The existing project has zero frontend tests; adding a framework is a separate decision. TypeScript + ESLint cover structural correctness; all behavior testing is visual/manual.

### Sampling Rate
- **Per task commit:** `cd backend && pytest app/tests/test_breakdown_api.py -x -q && cd frontend && npm run build`
- **Per plan merge:** `cd backend && pytest app/tests/ -x -q && cd frontend && npm run build && npm run lint`
- **Phase gate:** Full backend suite green, frontend builds without errors, all success criteria manually verified in running app

### Wave 0 Gaps
- [ ] `backend/app/tests/test_breakdown_api.py` — add `scene_links` field assertion (extend existing test)
- [ ] `frontend/src/types/index.ts` — `BreakdownElement`, `BreakdownSummary`, `BreakdownRun`, `SceneLink` types
- [ ] `frontend/src/lib/constants.ts` — `QUERY_KEYS.BREAKDOWN_*`, `BREAKDOWN_CATEGORIES`
- [ ] `frontend/src/lib/api.tsx` — 6 breakdown API methods
- [ ] `backend/app/models/schemas.py` — `SceneLinkResponse` + `scene_links` field on `BreakdownElementResponse`

---

## Sources

### Primary (HIGH confidence)
- `backend/app/api/endpoints/breakdown.py` — All API endpoints, URL patterns, request/response shapes
- `backend/app/models/schemas.py` — Pydantic schemas including `BreakdownElementResponse`, `BreakdownSummaryResponse`
- `backend/app/models/database.py` — ORM models including `BreakdownElement`, `ElementSceneLink` relationships
- `frontend/src/components/Projects/CreateProjectModal.tsx` — Established Radix Dialog pattern
- `frontend/src/components/Workspace/PhaseNavigation.tsx` — Exact navigation component to extend
- `frontend/src/components/Workspace/ProjectWorkspace.tsx` — Route/workspace architecture
- `frontend/src/App.tsx` — Current route structure, insertion point for breakdown route
- `frontend/src/lib/api.tsx` — Established API client patterns
- `frontend/src/lib/constants.ts` — QUERY_KEYS pattern to extend
- `frontend/src/components/Patterns/RepeatableCardsView.tsx` — Inline edit + mutation pattern
- `frontend/src/components/Snippets/SnippetCard.tsx` — Two-click delete confirm pattern
- `frontend/package.json` — Confirms all required dependencies installed; no test framework present

### Secondary (MEDIUM confidence)
- `@radix-ui/react-tabs` v1.0.4 API — `Tabs.Root`, `Tabs.List`, `Tabs.Trigger`, `Tabs.Content` — verified via package.json install and existing Dialog usage confirming Radix pattern knowledge
- React Query v5 `useMutation` optimistic updates — `onMutate`/`onError`/`onSettled` pattern — consistent with v5 docs; project uses `@tanstack/react-query` ^5.20.1

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies confirmed present in package.json
- Architecture: HIGH — all patterns derived directly from reading existing source files
- Pitfalls: HIGH — derived from code inspection (route collision from reading App.tsx, missing scene_links from reading schemas.py)
- Backend schema gap: HIGH — confirmed by reading `BreakdownElementResponse` which has no `scene_links` field

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack; dependencies change slowly)
