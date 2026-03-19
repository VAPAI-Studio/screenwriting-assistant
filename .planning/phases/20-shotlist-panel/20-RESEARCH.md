# Phase 20: Shotlist Panel - Research

**Researched:** 2026-03-19
**Domain:** React frontend -- editable data table with scene grouping, inline editing, optimistic mutations
**Confidence:** HIGH

## Summary

Phase 20 is a pure frontend phase that builds the interactive shotlist table in the center panel of the BreakdownLayout. The backend API (Phase 19) is complete and provides all required endpoints: list, create, update, delete, and reorder shots. The BreakdownLayout (Phase 18) already renders the center panel with a placeholder that must be replaced with the ShotlistPanel component. A detailed UI-SPEC (20-UI-SPEC.md) prescribes every visual detail -- typography, colors, column layout, interaction states, and copy.

The core implementation pattern follows the existing ElementCard/ElementList approach from Phase 13: React Query for data fetching, optimistic mutations with snapshot/rollback via `onMutate`/`onError`/`onSettled`, and inline editing with blur-save (150ms debounce). The key new challenges are: (1) CSS grid table layout with fixed + flexible columns, (2) scene-based grouping of a flat shot array, (3) button-based reorder (up/down arrows) calling the existing `/reorder` endpoint, and (4) per-cell inline editing rather than per-card editing. No new dependencies are required.

**Primary recommendation:** Build all components using existing patterns from ElementCard (optimistic mutations, delete confirmation, inline edit) and ElementList (query + loading skeleton), adapting them from card-based to row/cell-based layout. No new libraries needed -- CSS Grid and existing React Query patterns cover all requirements.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHOT-03 | Shots grouped by scene with scene headers in shotlist panel | Frontend groups flat array by `scene_item_id`; API returns sorted by `scene_item_id, sort_order` |
| SHOT-04 | User can edit shot fields inline in the shotlist table | InlineEditCell component using ElementCard blur-save pattern (150ms debounce) |
| SHOT-05 | User can delete shots | DeleteShotButton using ElementCard 3-second confirmation pattern |
| SHOT-06 | Shots have sort_order and can be reordered within a scene | Button-based up/down arrows calling POST `/api/shots/{project_id}/reorder` |
| SHOT-07 | Shotlist panel displays as table/grid in center area of breakdown mode | ShotlistPanel replaces center placeholder in BreakdownLayout |
| SHOT-08 | Empty state shows clear CTA when no shots exist | EmptyState component with "Add First Shot" button creating a shot via POST |
</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | 5.75.1 | Data fetching, caching, optimistic updates | Already in use; all mutations follow established pattern |
| react | 18.2.x | UI rendering | Existing |
| react-router-dom | 6.21.x | `useParams` for projectId | Existing |
| lucide-react | 0.314.x | Icons (GripVertical, ChevronUp, ChevronDown, Trash2, List, AlertCircle, Plus) | Existing |
| tailwindcss | 3.4.x | Styling with CSS variables | Existing |
| class-variance-authority | 0.7.x | Button variants | Existing |
| clsx + tailwind-merge | via `cn()` | Class merging utility | Existing |

### Supporting (already available)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-slot | 1.0.2 | Button asChild pattern | Button component already uses this |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS Grid table | @tanstack/react-table | Overkill for 7 columns, adds 20KB+ bundle, project doesn't use it |
| Button-based reorder | @dnd-kit or react-beautiful-dnd | Explicitly deferred to v3.1 (SMGT-01) |
| Custom inline edit | react-contenteditable | Adds dependency; `<input>` with blur-save is simpler and matches ElementCard |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/components/Breakdown/
  BreakdownLayout.tsx       # MODIFY: replace center placeholder with <ShotlistPanel>
  ShotlistPanel.tsx          # NEW: main panel component
  SceneGroup.tsx             # NEW: scene header + shot rows
  ShotRow.tsx                # NEW: single shot row with cells
  InlineEditCell.tsx         # NEW: click-to-edit cell
  AddShotButton.tsx          # NEW: ghost button at bottom of each scene group
  ReorderControls.tsx        # NEW: up/down arrow buttons
  DeleteShotButton.tsx       # NEW: trash icon with confirmation
  ShotlistEmptyState.tsx     # NEW: empty state CTA
```

### Pattern 1: Shot API Functions in `api.tsx`

**What:** Add shot CRUD functions to the existing `api` object.
**When to use:** All shot data operations.
**Example:**
```typescript
// Source: Existing api.tsx pattern + shots.py endpoints
async listShots(projectId: string): Promise<Shot[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/shots/${projectId}`, {
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to fetch shots');
  return response.json();
},

async createShot(projectId: string, data: ShotCreate): Promise<Shot> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/shots/${projectId}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create shot');
  return response.json();
},

async updateShot(projectId: string, shotId: string, data: ShotUpdate): Promise<Shot> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/shots/${projectId}/${shotId}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update shot');
  return response.json();
},

async deleteShot(projectId: string, shotId: string): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/shots/${projectId}/${shotId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to delete shot');
},

async reorderShots(
  projectId: string,
  items: Array<{ id: string; sort_order: number }>
): Promise<void> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/shots/${projectId}/reorder`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ items }),
  });
  if (!response.ok) throw new Error('Failed to reorder shots');
},
```

### Pattern 2: Scene Grouping (Frontend Transformation)

**What:** Transform flat shot array into scene-grouped structure.
**When to use:** In ShotlistPanel before rendering SceneGroups.
**Example:**
```typescript
// Source: UI-SPEC Data Flow section
interface SceneGroupData {
  sceneItemId: string | null;
  sceneTitle: string;
  shots: Shot[];
}

function groupShotsByScene(shots: Shot[]): SceneGroupData[] {
  const groups = new Map<string, Shot[]>();
  const groupOrder: string[] = [];

  for (const shot of shots) {
    const key = shot.scene_item_id ?? 'unassigned';
    if (!groups.has(key)) {
      groups.set(key, []);
      groupOrder.push(key);
    }
    groups.get(key)!.push(shot);
  }

  return groupOrder.map(key => ({
    sceneItemId: key === 'unassigned' ? null : key,
    sceneTitle: key === 'unassigned' ? 'Unassigned Shots' : `Scene`, // resolved with scene data
    shots: groups.get(key)!,
  }));
}
```

### Pattern 3: Optimistic Update Mutation (from ElementCard)

**What:** Immediate UI update with rollback on error.
**When to use:** All mutations (update, delete, reorder).
**Example:**
```typescript
// Source: ElementCard.tsx lines 27-53
const updateMutation = useMutation({
  mutationFn: ({ shotId, data }: { shotId: string; data: ShotUpdate }) =>
    api.updateShot(projectId, shotId, data),
  onMutate: async ({ shotId, data }) => {
    await queryClient.cancelQueries({ queryKey: QUERY_KEYS.SHOTS(projectId) });
    const previous = queryClient.getQueryData<Shot[]>(QUERY_KEYS.SHOTS(projectId));
    queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId), (old: Shot[] | undefined) =>
      (old ?? []).map(s => s.id === shotId ? { ...s, ...data } : s)
    );
    return { previous };
  },
  onError: (_err, _vars, context) => {
    if (context?.previous) {
      queryClient.setQueryData(QUERY_KEYS.SHOTS(projectId), context.previous);
    }
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId) });
  },
});
```

### Pattern 4: Inline Edit Cell

**What:** Click-to-edit cell replacing static text with an input.
**When to use:** Each editable field cell in ShotRow.
**Example:**
```typescript
// Source: Adapted from ElementCard.tsx blur-save pattern
function InlineEditCell({
  value,
  fieldKey,
  onSave,
}: {
  value: string;
  fieldKey: string;
  onSave: (fieldKey: string, newValue: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const blurTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const save = useCallback(() => {
    setEditing(false);
    if (editValue.trim() !== value) {
      onSave(fieldKey, editValue.trim());
    }
  }, [editValue, value, fieldKey, onSave]);

  const cancel = useCallback(() => {
    setEditing(false);
    setEditValue(value);
  }, [value]);

  if (!editing) {
    return (
      <div onClick={() => { setEditValue(value); setEditing(true); }}
           className="truncate cursor-text px-2 py-2 text-sm text-foreground">
        {value || <span className="text-muted-foreground/40">--</span>}
      </div>
    );
  }

  return (
    <input
      autoFocus
      value={editValue}
      onChange={e => setEditValue(e.target.value)}
      onBlur={() => { blurTimeoutRef.current = setTimeout(save, 150); }}
      onFocus={() => { if (blurTimeoutRef.current) clearTimeout(blurTimeoutRef.current); }}
      onKeyDown={e => {
        if (e.key === 'Enter') { e.preventDefault(); save(); }
        if (e.key === 'Escape') cancel();
      }}
      className="w-full bg-surface border border-border rounded px-2 py-1 text-sm
        text-foreground focus:ring-1 focus:ring-primary/50 focus:outline-none"
    />
  );
}
```

### Pattern 5: Delete Confirmation (from ElementCard)

**What:** Two-click delete with 3-second auto-dismiss.
**When to use:** Delete button in each shot row.
**Example:**
```typescript
// Source: ElementCard.tsx lines 86-96
const [deleteConfirm, setDeleteConfirm] = useState(false);
const deleteConfirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

const handleDeleteClick = () => {
  setDeleteConfirm(true);
  if (deleteConfirmTimerRef.current) clearTimeout(deleteConfirmTimerRef.current);
  deleteConfirmTimerRef.current = setTimeout(() => setDeleteConfirm(false), 3000);
};

const handleDeleteConfirm = () => {
  if (deleteConfirmTimerRef.current) clearTimeout(deleteConfirmTimerRef.current);
  setDeleteConfirm(false);
  deleteMutation.mutate(shot.id);
};
```

### Pattern 6: Button-Based Reorder

**What:** Up/down arrow buttons that swap sort_order with adjacent shot.
**When to use:** ReorderControls in each shot row action cell.
**Example:**
```typescript
// Source: shots.py reorder endpoint + UI-SPEC ReorderHandle section
function handleMoveUp(shot: Shot, groupShots: Shot[]) {
  const idx = groupShots.findIndex(s => s.id === shot.id);
  if (idx <= 0) return;
  const prev = groupShots[idx - 1];
  // Swap sort_orders
  reorderMutation.mutate([
    { id: shot.id, sort_order: prev.sort_order },
    { id: prev.id, sort_order: shot.sort_order },
  ]);
}
```

### Anti-Patterns to Avoid

- **Putting mutations in child components:** Keep all React Query mutations (update, delete, reorder, create) in ShotlistPanel and pass callbacks down. This avoids duplicating query key logic and simplifies optimistic updates.
- **Re-fetching on every inline edit:** Use optimistic updates, not `refetchOnWindowFocus` or manual refetch after each save. The 150ms debounce on blur prevents rapid-fire mutations.
- **Using `<table>` HTML elements:** CSS Grid is specified in the UI-SPEC and gives more flexibility. HTML tables don't support sticky headers with horizontal scroll well.
- **Managing editing state globally:** Each InlineEditCell manages its own `editing` boolean. No need for a "currently editing cell ID" state in the parent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Optimistic mutations | Custom state + fetch | React Query `onMutate` + `onError` + `onSettled` | Already proven in ElementCard, handles race conditions |
| Class name merging | String concatenation | `cn()` utility (clsx + tailwind-merge) | Already in use, handles conflicts correctly |
| Delete confirmation UX | Custom modal/dialog | Inline "Delete?" text + 3s auto-dismiss timer | Matches existing ElementCard pattern exactly |
| Button variants | Raw HTML buttons | `<Button variant="ghost">` from UI/Button.tsx | Consistent styling across app |
| Data grouping | Manual iteration + state | Pure function `groupShotsByScene()` called in render | Derived from React Query cache, no extra state |

**Key insight:** Every UX pattern in this phase already has a working reference implementation in ElementCard.tsx or ElementList.tsx. The novelty is layout (table vs cards) and per-cell editing, not the data/mutation patterns.

## Common Pitfalls

### Pitfall 1: PUT Replaces Entire `fields` JSONB
**What goes wrong:** Sending `{ fields: { shot_size: "CU" } }` to PUT wipes all other fields because Phase 19 uses full replacement for JSONB (see STATE.md decision).
**Why it happens:** The shot update endpoint sets `fields` to whatever is sent -- it does not merge.
**How to avoid:** Always spread existing `shot.fields` and override only the changed key: `{ fields: { ...shot.fields, [fieldKey]: newValue } }`.
**Warning signs:** Fields disappearing after editing a single cell.

### Pitfall 2: Reorder Endpoint Expects `items` Array, Not `shot_ids`
**What goes wrong:** Sending wrong shape to `/reorder` causes 422 validation error.
**Why it happens:** The ReorderRequest schema expects `{ items: [{ id: UUID, sort_order: int }] }`.
**How to avoid:** Match exact schema: `api.reorderShots(projectId, [{ id: "...", sort_order: 0 }, { id: "...", sort_order: 1 }])`.
**Warning signs:** 422 errors on reorder.

### Pitfall 3: Optimistic Sort Order After Reorder
**What goes wrong:** After reorder mutation, optimistic update in cache doesn't reflect new sort_order values, causing UI to flicker back to old order on re-render.
**Why it happens:** `onMutate` must update sort_order values in the cached shot array, not just swap positions.
**How to avoid:** In `onMutate`, create a new array with updated `sort_order` fields for the swapped shots, then sort the array.
**Warning signs:** Shots briefly snapping back to old position after reorder.

### Pitfall 4: Scene Title Resolution
**What goes wrong:** The API returns `scene_item_id` (UUID) but no scene title. Displaying just a UUID is useless.
**Why it happens:** The shots endpoint doesn't join with list_items to get scene names.
**How to avoid:** Either (a) fetch list_items for the scenes phase to get titles, or (b) use "Scene {N}" fallback format as specified in UI-SPEC. Option (b) is recommended for MVP since scene data may not always be available.
**Warning signs:** UUIDs showing as scene headers.

### Pitfall 5: BreakdownLayout Center Panel Replacement
**What goes wrong:** Incorrectly nesting ShotlistPanel inside BreakdownLayout breaks flex layout.
**Why it happens:** The center panel is currently a raw `<div className="flex-1 flex flex-col">`. ShotlistPanel must replace the inner content but preserve the outer flex container.
**How to avoid:** ShotlistPanel should be rendered as the child content of the existing center panel div, not replace the outer structure. Keep the panel header ("SHOTLIST") and wrap ShotlistPanel in the content area below.
**Warning signs:** Layout overflow, horizontal scroll breaking, panels not resizing.

### Pitfall 6: Missing `projectId` from `useParams`
**What goes wrong:** `useParams` returns `undefined` for projectId when component renders outside route context.
**Why it happens:** BreakdownLayout doesn't extract projectId -- it needs to be read from route params.
**How to avoid:** Use `useParams<{ projectId: string }>()` in ShotlistPanel (or BreakdownLayout) and guard with `if (!projectId) return null`.
**Warning signs:** API calls with `undefined` in URL.

## Code Examples

### Complete ShotlistPanel Data Flow
```typescript
// Source: Adapted from BreakdownPage.tsx + ElementList.tsx patterns
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { QUERY_KEYS } from '../../lib/constants';
import type { Shot, ShotCreate, ShotUpdate } from '../../types';

export function ShotlistPanel() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();

  const { data: shots, isLoading, isError } = useQuery<Shot[]>({
    queryKey: QUERY_KEYS.SHOTS(projectId!),
    queryFn: () => api.listShots(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  // Create, update, delete, reorder mutations with optimistic updates
  // (see Architecture Patterns above for each mutation shape)

  if (isLoading) return <ShotlistSkeleton />;
  if (isError) return <ShotlistError onRetry={() => /* refetch */ } />;
  if (!shots || shots.length === 0) return <ShotlistEmptyState onAddShot={handleCreateShot} />;

  const groups = groupShotsByScene(shots);

  return (
    <div className="flex-1 overflow-auto">
      {/* Column headers - sticky */}
      <div className="sticky top-0 z-10 bg-background border-b border-border">
        <div className="grid" style={{
          gridTemplateColumns: '48px repeat(2, minmax(80px, 1fr)) minmax(80px, 1fr) repeat(2, minmax(120px, 2fr)) 80px'
        }}>
          {/* Column header cells */}
        </div>
      </div>

      {/* Scene groups */}
      {groups.map(group => (
        <SceneGroup
          key={group.sceneItemId ?? 'unassigned'}
          group={group}
          onUpdateShot={handleUpdateShot}
          onDeleteShot={handleDeleteShot}
          onMoveShot={handleMoveShot}
          onCreateShot={handleCreateShot}
        />
      ))}
    </div>
  );
}
```

### QUERY_KEYS Addition
```typescript
// Source: constants.ts -- add to QUERY_KEYS object
SHOTS: (projectId: string) => ['shots', projectId] as const,
```

### TypeScript Types (from UI-SPEC)
```typescript
// Source: 20-UI-SPEC.md TypeScript Types section
// Add to types/index.ts

export interface Shot {
  id: string;
  project_id: string;
  scene_item_id: string | null;
  shot_number: number;
  script_text: string;
  script_range: Record<string, unknown>;
  fields: ShotFields;
  sort_order: number;
  source: 'user' | 'ai';
  created_at: string;
  updated_at: string | null;
}

export interface ShotFields {
  shot_size?: string;
  camera_angle?: string;
  camera_movement?: string;
  lens?: string;
  description?: string;
  action?: string;
  dialogue?: string;
  sound?: string;
  characters?: string;
  environment?: string;
  props?: string;
  equipment?: string;
  notes?: string;
}

export interface ShotCreate {
  scene_item_id?: string | null;
  shot_number?: number;
  script_text?: string;
  fields?: Partial<ShotFields>;
  sort_order?: number;
  source?: 'user' | 'ai';
}

export interface ShotUpdate {
  scene_item_id?: string | null;
  shot_number?: number;
  script_text?: string;
  fields?: Partial<ShotFields>;
  sort_order?: number;
}
```

### CSS Grid Column Layout
```typescript
// Source: 20-UI-SPEC.md Column Layout section
const SHOTLIST_GRID_TEMPLATE =
  '48px repeat(2, minmax(80px, 1fr)) minmax(80px, 1fr) repeat(2, minmax(120px, 2fr)) 80px';

const SHOTLIST_COLUMNS = [
  { key: 'shot_number', label: '#', width: '48px', align: 'center' as const, editable: false },
  { key: 'shot_size', label: 'Size', fieldPath: 'fields.shot_size', editable: true },
  { key: 'camera_angle', label: 'Angle', fieldPath: 'fields.camera_angle', editable: true },
  { key: 'camera_movement', label: 'Movement', fieldPath: 'fields.camera_movement', editable: true },
  { key: 'description', label: 'Description', fieldPath: 'fields.description', editable: true },
  { key: 'action', label: 'Action', fieldPath: 'fields.action', editable: true },
  { key: '_actions', label: '', width: '80px', editable: false },
] as const;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTML `<table>` for data | CSS Grid with `grid-template-columns` | Tailwind 3.x era | Better sticky header support, responsive behavior |
| Redux for mutations | React Query optimistic mutations | 2022+ | Less boilerplate, built-in cache invalidation |
| Modal delete confirmation | Inline "Delete?" with auto-dismiss | Project convention (ElementCard) | Faster UX, fewer interruptions |
| Drag-and-drop reorder | Button-based up/down (v3.0) | Project decision | Simpler implementation; DnD deferred to v3.1 |

**Deprecated/outdated:**
- Drag-and-drop reorder (SMGT-01): Explicitly deferred to v3.1. Do NOT implement in this phase.
- Collapsible scene groups: Deferred per UI-SPEC. All scenes expanded by default.

## Open Questions

1. **Scene Title Resolution**
   - What we know: Shots have `scene_item_id` (UUID FK to list_items). List items have a `content` JSON field with scene title.
   - What's unclear: Whether to fetch scene list items separately or use "Scene {N}" fallback.
   - Recommendation: Use "Scene {N}" fallback for the scene header (numbered by display order). If scene data is available in a parent query, use it. Do NOT add a separate API call just for scene titles -- it can be enhanced later.

2. **"Add First Shot" in Empty State -- Which Scene?**
   - What we know: When no shots exist, the CTA button creates a shot. But which `scene_item_id`?
   - What's unclear: Should it be `null` (unassigned) or linked to the first scene?
   - Recommendation: Create with `scene_item_id: null` (unassigned). User can reassign later. This is simplest and matches the freeform nature of the tool.

3. **Shot Number Auto-Increment**
   - What we know: `shot_number` has `default=1` in the DB. UI-SPEC shows it as a field.
   - What's unclear: Should "Add Shot" auto-calculate the next shot_number within a scene group?
   - Recommendation: Yes, calculate as `max(shot_number in group) + 1`. For unassigned group, calculate across all shots.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend); no frontend test runner configured |
| Config file | backend: existing conftest.py |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHOT-03 | Shots grouped by scene in panel | manual-only | Visual inspection of scene grouping | N/A |
| SHOT-04 | Inline edit shot fields | manual-only | Click cell, edit, verify save | N/A |
| SHOT-05 | Delete a shot | manual-only | Click delete, confirm, verify removal | N/A |
| SHOT-06 | Reorder shots within scene | manual-only | Click up/down, verify order persists | N/A |
| SHOT-07 | Table/grid display in center panel | manual-only | Visual inspection of layout | N/A |
| SHOT-08 | Empty state CTA | manual-only | Load project with no shots, verify CTA | N/A |

Note: All Phase 20 requirements are frontend-only (React components). The project has no frontend test framework (no Jest, Vitest, or Playwright). Backend API tests from Phase 19 already verify CRUD correctness. Frontend validation is manual-only for this phase.

### Sampling Rate
- **Per task commit:** Visual inspection in browser (`npm run dev`)
- **Per wave merge:** Full backend test suite: `cd backend && pytest app/tests/ -x`
- **Phase gate:** All 6 requirements verified manually in browser + backend tests still pass

### Wave 0 Gaps
None -- this is a frontend-only phase. Backend API and tests already exist from Phase 19. No frontend test infrastructure exists in this project, and adding it is out of scope for this phase.

## Sources

### Primary (HIGH confidence)
- `/backend/app/api/endpoints/shots.py` -- All 5 API endpoints verified (list, create, get, update, delete, reorder)
- `/backend/app/models/schemas.py` -- ShotCreate, ShotUpdate, ShotResponse, ReorderRequest schemas verified
- `/frontend/src/components/Breakdown/ElementCard.tsx` -- Optimistic mutation pattern, inline editing, delete confirmation
- `/frontend/src/components/Breakdown/BreakdownLayout.tsx` -- Center panel structure (lines 158-171), placeholder to replace
- `/frontend/src/components/Breakdown/ElementList.tsx` -- Query pattern, loading skeleton
- `/frontend/src/lib/api.tsx` -- API function patterns, auth headers, fetchWithTimeout
- `/frontend/src/lib/constants.ts` -- QUERY_KEYS structure
- `/frontend/src/types/index.ts` -- Existing type patterns
- `.planning/phases/20-shotlist-panel/20-UI-SPEC.md` -- Complete visual/interaction contract
- `/frontend/tailwind.config.js` -- Animation classes (fade-in exists), color system
- `/frontend/src/index.css` -- `.breakdown-mode` CSS variables (lines 50-88)
- `.planning/STATE.md` -- v3.0 decisions: PUT fields replacement (not merge), button-based reorder

### Secondary (MEDIUM confidence)
- React Query v5 optimistic update patterns -- verified against existing codebase usage in ElementCard

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already installed and in use; zero new dependencies
- Architecture: HIGH - Every pattern has a working reference in existing Breakdown components
- Pitfalls: HIGH - Identified from direct code reading of shots.py (PUT replaces fields) and schemas.py (ReorderRequest shape)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- no external dependencies, all patterns internal)
