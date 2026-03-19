# Phase 21: Script Read View & Text Selection - Research

**Researched:** 2026-03-19
**Domain:** Browser Selection API, React text selection UX, frontend component architecture
**Confidence:** HIGH

## Summary

Phase 21 adds the script read view to the left panel of the breakdown layout and implements text selection with a floating bar for creating shots from selected script text. This is a purely frontend phase -- no backend changes required. The existing Shot CRUD API already supports `script_text` and `script_range` fields on shots, and the `createShot` mutation in `ShotlistPanel` already handles optimistic creation. The screenplay data is already stored in the `phase_data` table under `subsection_key="screenplay_editor"` in the `write` phase as `{ screenplays: [{ episode_index, title, content }] }`.

The core technical challenge is mapping selected text back to the correct scene (ListItem) so the shot's `scene_item_id` is populated correctly. Scenes are ListItems under `phase="scenes"`, `subsection_key="scene_list"`, and screenplays reference scenes by `episode_index`. The approach is: render screenplay content organized by scene, use `data-scene-id` attributes on DOM elements, and resolve the scene from the selection's anchor/focus nodes.

**Primary recommendation:** Use the native `window.getSelection()` API with `Range.getBoundingClientRect()` for positioning a custom floating bar. No third-party library needed -- this project avoids heavy dependencies and the use case is read-only text selection (not rich text editing).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SELC-01 | Left panel in breakdown mode shows a read-only rendering of the screenplay content | Fetch screenplay from phase_data API (`write/screenplay_editor`), render as `<pre>` blocks organized by scene with `data-scene-id` attributes. Replace placeholder in BreakdownLayout. |
| SELC-02 | User can highlight/select text in the read-only script view | Native browser text selection on non-editable content. Use `mouseup` and `selectionchange` events to detect selection. |
| SELC-03 | On text selection, a floating bar appears showing line count and "+ Add Shot" button | Use `window.getSelection().getRangeAt(0).getBoundingClientRect()` to position an absolutely-positioned bar. Count newlines in `selection.toString()` for line count. |
| SELC-04 | Clicking "+ Add Shot" creates a new shot pre-populated with the selected script text and linked to the corresponding scene | Walk DOM from selection anchor to find nearest `[data-scene-id]` ancestor. Call existing `api.createShot()` with `script_text` and `scene_item_id`. |
| SELC-05 | Selection bar dismisses on click outside or pressing X | Listen for `mousedown` outside the bar and `Escape` key. Clear selection with `window.getSelection().removeAllRanges()`. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.2.x | Component framework | Already in project |
| @tanstack/react-query | 5.20.x | Data fetching and mutations | Already in project, used for all API calls |
| lucide-react | 0.314.x | Icons (Plus, X, FileText) | Already in project |
| Tailwind CSS | 3.4.x | Styling | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| window.getSelection() | Web API | Text selection detection | Core browser API, no library needed |
| Range.getBoundingClientRect() | Web API | Floating bar positioning | Returns rect relative to viewport |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native Selection API | @floating-ui/react | Adds 3kB dependency for a single floating element; overkill for this use case |
| Custom floating bar | Radix Popover | Would fight with selection behavior; Radix anchors to trigger elements, not arbitrary text ranges |
| Pre-rendered text | Rich text editor (Lexical/Tiptap) | Massive overhead for read-only view; project explicitly decided "Script view is read-only -- no rich text editor needed" |

**Installation:**
```bash
# No new dependencies required
```

## Architecture Patterns

### Recommended Component Structure
```
frontend/src/components/Breakdown/
  ScriptReadView.tsx       # Main component: fetches screenplay, renders scenes, manages selection
  SelectionBar.tsx         # Floating bar: positioned via getBoundingClientRect, shows line count + Add Shot
  BreakdownLayout.tsx      # Modified: passes projectId to ScriptReadView, wires shot creation callback
```

### Pattern 1: Data Flow for Screenplay Content
**What:** Fetch screenplay content and scene list items, render organized by scene
**When to use:** ScriptReadView mount
**Example:**
```typescript
// Fetch screenplay data from the write phase
const { data: screenplayData } = useQuery({
  queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, 'write', 'screenplay_editor'),
  queryFn: () => api.getSubsectionData(projectId, 'write', 'screenplay_editor'),
  enabled: !!projectId,
});

// Fetch scene list items to get scene IDs and titles
const { data: scenePhaseData } = useQuery({
  queryKey: QUERY_KEYS.PHASE_DATA(projectId, 'scenes'),
  queryFn: () => api.getPhaseData(projectId, 'scenes'),
  enabled: !!projectId,
});

// Find the scene_list phase_data entry
const sceneListPD = scenePhaseData?.find(pd => pd.subsection_key === 'scene_list');

const { data: sceneItems } = useQuery({
  queryKey: QUERY_KEYS.LIST_ITEMS(sceneListPD?.id ?? ''),
  queryFn: () => api.getListItems(sceneListPD!.id),
  enabled: !!sceneListPD?.id,
});

// screenplays are stored as: { screenplays: [{ episode_index, title, content }] }
const screenplays = (screenplayData?.content as any)?.screenplays ?? [];
```

### Pattern 2: Scene-to-Text Mapping via DOM Attributes
**What:** Each screenplay segment is wrapped in a `<div data-scene-id="...">` so selection can be mapped back to scene
**When to use:** Rendering screenplay content and resolving selection to scene_item_id
**Example:**
```typescript
// Rendering: each screenplay maps to a scene by episode_index
{screenplays.map((sp, idx) => {
  // Match scene by sort_order / index
  const sceneItem = sceneItems?.[idx];
  return (
    <div key={idx} data-scene-id={sceneItem?.id ?? ''} className="mb-6">
      <div className="text-xs font-semibold text-muted-foreground uppercase mb-2">
        {sp.title || `Scene ${idx + 1}`}
      </div>
      <pre className="font-screenplay text-[13px] text-foreground/90 whitespace-pre-wrap break-words">
        {sp.content}
      </pre>
    </div>
  );
})}

// Resolving scene from selection:
function getSceneIdFromSelection(selection: Selection): string | null {
  const anchorNode = selection.anchorNode;
  if (!anchorNode) return null;
  const el = anchorNode.nodeType === Node.ELEMENT_NODE
    ? (anchorNode as Element)
    : anchorNode.parentElement;
  const sceneEl = el?.closest('[data-scene-id]');
  return sceneEl?.getAttribute('data-scene-id') || null;
}
```

### Pattern 3: Floating Bar Positioning
**What:** Use Range.getBoundingClientRect() to position the floating bar near the selection
**When to use:** When text is selected (non-empty selection detected)
**Example:**
```typescript
function useTextSelection(containerRef: React.RefObject<HTMLElement>) {
  const [selectionState, setSelectionState] = useState<{
    text: string;
    lineCount: number;
    rect: DOMRect;
    sceneItemId: string | null;
  } | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleSelectionChange = () => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
        setSelectionState(null);
        return;
      }

      // Verify selection is within our container
      const range = selection.getRangeAt(0);
      if (!container.contains(range.commonAncestorContainer)) {
        setSelectionState(null);
        return;
      }

      const text = selection.toString().trim();
      if (!text) {
        setSelectionState(null);
        return;
      }

      const rect = range.getBoundingClientRect();
      const lineCount = text.split('\n').filter(l => l.trim()).length;
      const sceneItemId = getSceneIdFromSelection(selection);

      setSelectionState({ text, lineCount, rect, sceneItemId });
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, [containerRef]);

  return selectionState;
}
```

### Pattern 4: Selection Bar Dismiss Behavior
**What:** Dismiss bar on click outside or Escape key
**When to use:** When SelectionBar is visible
**Example:**
```typescript
// In SelectionBar component
useEffect(() => {
  const handleMouseDown = (e: MouseEvent) => {
    // If click is outside the bar, dismiss
    if (barRef.current && !barRef.current.contains(e.target as Node)) {
      onDismiss();
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onDismiss();
    }
  };

  document.addEventListener('mousedown', handleMouseDown);
  document.addEventListener('keydown', handleKeyDown);
  return () => {
    document.removeEventListener('mousedown', handleMouseDown);
    document.removeEventListener('keydown', handleKeyDown);
  };
}, [onDismiss]);
```

### Anti-Patterns to Avoid
- **Using a rich text editor for read-only display:** The project explicitly decided against this. Read-only `<pre>` text is sufficient and vastly simpler.
- **Using `useEffect` with `mouseup` only:** The `selectionchange` event is more reliable for tracking selection state changes, including keyboard-based selections (Shift+Arrow).
- **Positioning the bar with `top/left` relative to the page:** Must use the scroll container's offset. Use `position: fixed` with viewport-relative coords from `getBoundingClientRect()`, or calculate offset relative to the scroll container.
- **Creating the shot without scene_item_id:** The shot MUST be linked to the scene for proper grouping in the shotlist. Always resolve the scene from the DOM before creating.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shot creation | Custom fetch calls | Existing `api.createShot()` + React Query mutation from ShotlistPanel | Already tested, handles optimistic updates |
| Screenplay data fetching | Custom data loading | Existing `api.getSubsectionData()` + `api.getPhaseData()` + `api.getListItems()` | API wrapper already exists with auth, timeout |
| Floating element positioning | Full floating-ui integration | `Range.getBoundingClientRect()` + fixed positioning | Single use case, no reusable floating needed |
| Text selection API | Polyfill or library | Native `window.getSelection()` | Universal browser support since 2015 |

**Key insight:** This phase is entirely additive frontend work using existing APIs (both browser and project). No new backend endpoints, no new npm dependencies. The complexity is in the UX details (positioning, dismiss behavior, scene mapping), not in the technology.

## Common Pitfalls

### Pitfall 1: Selection Lost on Button Click
**What goes wrong:** Clicking the "+ Add Shot" button in the floating bar clears the text selection because the mousedown event on the button triggers deselection.
**Why it happens:** Browser default behavior clears selection when clicking outside the selected text.
**How to avoid:** Capture the selection text and scene_item_id in state BEFORE the click handler fires. Use `mousedown` with `preventDefault()` on the floating bar to prevent selection clearing, or store the selection data in React state when the bar appears so the click handler has access to the data regardless of whether the selection is still active.
**Warning signs:** Shot created with empty `script_text` despite user having selected text.

### Pitfall 2: Selection Outside Script Container Triggers Bar
**What goes wrong:** Selecting text in the shotlist panel or elsewhere in the app shows the floating bar.
**Why it happens:** `selectionchange` fires globally, not scoped to a specific element.
**How to avoid:** In the selection handler, verify `range.commonAncestorContainer` is contained within the script view's container ref. Bail out early if not.
**Warning signs:** Floating bar appears when selecting text in unrelated UI areas.

### Pitfall 3: Floating Bar Position Shifts on Scroll
**What goes wrong:** The floating bar stays at the original viewport position while the user scrolls the script panel.
**Why it happens:** `getBoundingClientRect()` returns viewport-relative coordinates, but if the bar is positioned within a scrollable container, the coordinates become stale.
**How to avoid:** Either use `position: fixed` (always relative to viewport, recalculate on scroll) or convert viewport coords to container-relative coords. Dismiss the bar on scroll for simplicity.
**Warning signs:** Bar floats away from the selected text when scrolling.

### Pitfall 4: Screenplay-to-Scene Mapping Mismatch
**What goes wrong:** Shot gets linked to the wrong scene or no scene.
**Why it happens:** Screenplays are stored with `episode_index` but scenes are separate ListItems. The mapping is by index/order, which can drift if scenes are added/removed.
**How to avoid:** Match screenplays to scenes by `episode_index` to `sort_order`. Handle the case where no matching scene exists by falling back to `scene_item_id: null`.
**Warning signs:** Shots appear in wrong scene groups in the shotlist.

### Pitfall 5: Empty Screenplay State
**What goes wrong:** The script read view shows nothing or errors when no screenplay content has been generated.
**Why it happens:** User enters breakdown mode before running the Script Writer Wizard.
**How to avoid:** Show a clear empty state with guidance: "No screenplay content yet. Switch to Screenwriting mode and generate a script first."
**Warning signs:** Blank panel or loading spinner that never resolves.

### Pitfall 6: Cross-Browser Selection Quirks (Safari)
**What goes wrong:** Selection detection behaves differently in Safari.
**Why it happens:** Safari has known quirks with `selectionchange` event timing and `Selection` object behavior.
**How to avoid:** Use both `selectionchange` and `mouseup` as redundant event listeners. Test in Safari. The `selectionchange` event may fire more or fewer times in Safari than Chrome.
**Warning signs:** Floating bar doesn't appear in Safari despite text being selected.

## Code Examples

### Shot Creation from Selection (Integration with Existing Mutation)
```typescript
// In BreakdownLayout or ScriptReadView, reuse the createShot API
const createMutation = useMutation({
  mutationFn: (data: ShotCreate) => api.createShot(projectId!, data),
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
  },
});

const handleAddShotFromSelection = (text: string, sceneItemId: string | null) => {
  // Calculate shot_number based on existing shots in the scene
  const groupShots = (shots ?? []).filter(s =>
    sceneItemId === null
      ? s.scene_item_id === null
      : s.scene_item_id === sceneItemId
  );
  const maxNumber = groupShots.reduce((max, s) => Math.max(max, s.shot_number), 0);
  const maxSortOrder = groupShots.reduce((max, s) => Math.max(max, s.sort_order), -1);

  createMutation.mutate({
    scene_item_id: sceneItemId,
    shot_number: maxNumber + 1,
    script_text: text,
    sort_order: maxSortOrder + 1,
    source: 'user',
  });

  // Clear the selection after creating the shot
  window.getSelection()?.removeAllRanges();
};
```

### SelectionBar Component Structure
```typescript
// Source: Project pattern (Tailwind + Lucide icons, consistent with existing components)
interface SelectionBarProps {
  rect: DOMRect;
  lineCount: number;
  onAddShot: () => void;
  onDismiss: () => void;
  isPending: boolean;
}

function SelectionBar({ rect, lineCount, onAddShot, onDismiss, isPending }: SelectionBarProps) {
  const barRef = useRef<HTMLDivElement>(null);

  // Position below the selection
  const style: React.CSSProperties = {
    position: 'fixed',
    top: rect.bottom + 8,
    left: rect.left + rect.width / 2,
    transform: 'translateX(-50%)',
    zIndex: 50,
  };

  return (
    <div ref={barRef} style={style}
      className="flex items-center gap-2 px-3 py-2 bg-card border border-border rounded-lg shadow-lg"
      onMouseDown={(e) => e.preventDefault()} // Prevent selection loss
    >
      <span className="text-xs text-muted-foreground">
        {lineCount} {lineCount === 1 ? 'line' : 'lines'}
      </span>
      <button onClick={onAddShot} disabled={isPending}
        className="flex items-center gap-1 px-3 py-1 text-xs font-semibold bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-40"
      >
        <Plus className="h-3 w-3" /> Add Shot
      </button>
      <button onClick={onDismiss}
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom polyfills for Selection API | Native `window.getSelection()` | 2015+ (universal support) | No polyfills needed |
| jQuery-based text selection | React hooks + native APIs | React 16.8+ (2019) | Clean hook-based pattern |
| `mouseup` only for detection | `selectionchange` event | Chrome 2015, Safari 2017 | Catches keyboard selections too |

**Deprecated/outdated:**
- `document.selection` (IE-only): Replaced by standard `window.getSelection()`
- `createTextRange()` (IE-only): Replaced by standard `Range` API

## Open Questions

1. **Screenplay-to-Scene Index Mapping Reliability**
   - What we know: Screenplays store `episode_index`, scenes are ListItems with `sort_order`. The Script Writer Wizard generates one screenplay per scene.
   - What's unclear: If scenes are manually reordered or deleted after screenplay generation, the index mapping may break.
   - Recommendation: Use `episode_index` as the primary key for matching, fall back to index position, and handle missing scenes gracefully by setting `scene_item_id: null`.

2. **Script Range JSONB Usage**
   - What we know: The `shots` table has a `script_range` JSONB column.
   - What's unclear: What format should `script_range` store? Character offsets? Line numbers?
   - Recommendation: Store `{ start_offset, end_offset, scene_index }` for future use (e.g., highlighting which text a shot references). For now, populate but don't depend on it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), no frontend test runner configured |
| Config file | backend/pytest.ini or pyproject.toml |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SELC-01 | Read-only script rendering | manual-only | N/A - frontend visual component, no frontend test runner | N/A |
| SELC-02 | Text highlight/selection | manual-only | N/A - browser Selection API interaction | N/A |
| SELC-03 | Floating bar with line count | manual-only | N/A - DOM positioning behavior | N/A |
| SELC-04 | Add Shot creates shot with selected text | integration | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -x` | Existing API tests cover shot creation with script_text |
| SELC-05 | Selection bar dismisses | manual-only | N/A - browser event handling | N/A |

### Sampling Rate
- **Per task commit:** `npm run build` (TypeScript compilation check)
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green + `npm run build` before verification

### Wave 0 Gaps
None -- this phase is purely frontend. Existing backend API tests already cover shot creation with `script_text`. The frontend has no test runner configured (no vitest/jest in package.json), so validation is via TypeScript compilation (`npm run build`) and manual testing. No new test files needed.

## Sources

### Primary (HIGH confidence)
- [MDN Selection API](https://developer.mozilla.org/en-US/docs/Web/API/Selection) - Selection properties, methods, browser compatibility
- [MDN Window.getSelection()](https://developer.mozilla.org/en-US/docs/Web/API/Window/getSelection) - API availability since July 2015
- Project codebase: `BreakdownLayout.tsx` - Current left panel placeholder ("Available in Phase 21")
- Project codebase: `ShotlistPanel.tsx` - Existing shot CRUD mutations with optimistic updates
- Project codebase: `ScreenplayEditorView.tsx` - Screenplay data structure (`{ screenplays: [{ episode_index, title, content }] }`)
- Project codebase: `shots.py` (backend) - Shot creation accepts `script_text`, `script_range`, `scene_item_id`
- Project codebase: `types/index.ts` - `ShotCreate` interface with `script_text` field

### Secondary (MEDIUM confidence)
- [Floating UI React](https://floating-ui.com/docs/react) - Verified as alternative, decided against for simplicity
- Project STATE.md - Decision: "Script view is read-only -- no rich text editor needed"
- Project STATE.md - Blocker flagged: "Text Selection API cross-browser testing needed (Safari quirks)"

### Tertiary (LOW confidence)
- Safari `selectionchange` event timing - Flagged in STATE.md as needing cross-browser testing

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all browser-native APIs universally supported
- Architecture: HIGH - Component structure follows existing project patterns exactly (BreakdownLayout children, React Query mutations)
- Pitfalls: HIGH - Selection API well-documented, pitfalls are well-known patterns
- Scene mapping: MEDIUM - Screenplay-to-scene index mapping depends on data integrity

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable browser APIs, no moving targets)
