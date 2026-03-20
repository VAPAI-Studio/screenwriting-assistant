# Phase 18: Two-Mode UI Shell - Research

**Researched:** 2026-03-19
**Domain:** React Router v6, CSS custom property scoping, resizable panel layout, mode-aware theming
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Toggle Placement**
- Lives in the main header, contextual — appears only when the user is inside a project route
- Visual form: dropdown button showing current mode name + caret icon ("Screenwriting ▾" / "Script Breakdown ▾")
- URL-based mode routing: switching to Breakdown navigates to `/projects/:id/breakdown`; switching back to Screenwriting navigates to the project's default workspace route
- App-level nav links (Projects, Books, Snippets) remain in the header alongside the mode dropdown

**Visual Identity**
- Breakdown mode palette: cool slate / blue-grey — dark backgrounds with blue-grey tones, accent shifts to steel blue or indigo
- Distinctness level: distinct but harmonious — same general darkness/contrast and depth; shared typography, spacing, and component shapes; accent color clearly different but both modes feel like the same product
- The entire chrome (including header) adopts the breakdown palette when in Breakdown mode
- Mode transitions use smooth CSS transitions (200–300ms) on color variables

**Old BreakdownPage**
- Phase 18 replaces `BreakdownPage.tsx` — the old v2.0 breakdown elements page is removed from the `/breakdown` route
- The old breakdown element content will be re-exposed in the Assets panel in Phase 23; it is temporarily inaccessible via UI between Phase 18 and Phase 23
- New breakdown layout lives at the same `/projects/:id/breakdown` URL

**Panel Layout**
- 3-panel skeleton: left (script/assets), center (shotlist), right (chat)
- Default widths: 25% / 50% / 25%
- Resizable via drag handles between panels; resize state persists in localStorage
- Each panel is collapsible via a collapse button; collapsed state persists in localStorage
- Placeholder content in each panel: labeled empty states with icon + description
- Minimum panel widths: Claude's discretion (reasonable for readability)

### Claude's Discretion
- Exact CSS variable values for the breakdown blue-grey palette (must look good, not just "different")
- Specific min-width constraints for resizable panels
- Collapse icon/button placement within each panel header
- Exact localStorage keys for panel state

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODE-01 | App has a top-level toggle in the header switching between "Screenwriting" and "Script Breakdown" modes | ModeToggle dropdown using `@radix-ui/react-dropdown-menu` (already in package.json), `useLocation`/`useNavigate` from react-router-dom v6, pattern already used in `Header.tsx` |
| MODE-02 | Screenwriting mode renders the existing workspace with zero changes to existing components | No changes to existing routes or components; the breakdown route is replaced, not the workspace route |
| MODE-03 | Script Breakdown mode renders a distinct 3-panel layout (left panel, center shotlist, right chat) | New `BreakdownLayout` component replaces `BreakdownPage` import in `App.tsx`; uses percentage-based flex layout with drag handle panels |
| MODE-04 | Screenwriting and Breakdown modes have visually distinct color schemes while maintaining design unity | CSS custom property overrides scoped to `.breakdown-mode` class on `<html>` or `<body>`; transitions on `color` and `background-color` properties; approach already implied in `index.css` `:root` structure |
| MODE-05 | Mode toggle preserves project context (no data loss on switch) | URL-based routing via React Router — no component state lost; `projectId` param is preserved in both `/projects/:id` and `/projects/:id/breakdown` routes |
</phase_requirements>

---

## Summary

Phase 18 is a pure frontend phase with no backend work. It introduces two capabilities: (1) a mode-switching dropdown in the header that navigates between Screenwriting and Breakdown URLs, and (2) a three-panel layout skeleton that replaces `BreakdownPage.tsx` at the `/projects/:id/breakdown` route. Visual identity switching uses CSS custom property overrides scoped by a class on the `<html>` element, enabling smooth transitions across all themed components simultaneously.

The existing codebase already contains nearly every primitive needed: `@radix-ui/react-dropdown-menu` (for the mode dropdown), `useLocation` and `useNavigate` from react-router-dom v6 (already used in `Header.tsx`), a `ResizablePanel.tsx` component with localStorage persistence (already built), and a CSS variable system on `:root` with HSL values (in `index.css`). The main work is composition and the new cool-palette CSS variable block.

The critical architectural decision is where to apply the `.breakdown-mode` class. Applying it to `<html>` (via `document.documentElement.classList`) or `<body>` means every component's `hsl(var(--accent))` references automatically pick up the overridden values — no prop drilling, no Context. The `BreakdownLayout` component mounts/unmounts via the React Router route, so `useEffect` in that component adds/removes the class on mount/unmount. This is the pattern to use.

**Primary recommendation:** Use a `.breakdown-mode` class applied to `document.documentElement` in a `useEffect` inside `BreakdownLayout`. Implement `ModeToggle` as a Radix DropdownMenu. Build `BreakdownLayout` as a flex-row container with three percentage-based panels sharing a new `ThreePanelLayout` component pattern.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-router-dom | ^6.21.3 (installed) | URL-based mode routing, `useLocation`, `useNavigate`, `useParams` | Already in project; v6 declarative route model |
| @radix-ui/react-dropdown-menu | ^2.0.6 (installed) | ModeToggle dropdown with keyboard accessibility | Already in project; used by existing components |
| Tailwind CSS | ^3.4.1 (installed) | Utility classes for layout, panel sizing | Already in project; all styling via Tailwind |
| CSS custom properties | native | Theme variable scoping via `.breakdown-mode` class | Already established pattern in `index.css` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | ^0.314.0 (installed) | Icons in panel placeholders, collapse buttons, ModeToggle caret | All icon needs |
| localStorage (native) | native | Panel width and collapsed state persistence | Panel resize/collapse handlers |
| clsx / tailwind-merge | installed | Conditional class composition | Complex panel className logic |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS class on `<html>` | React Context for mode state | Context requires prop threading; CSS class approach means all `hsl(var(--X))` references get theme for free, zero re-renders |
| CSS class on `<html>` | `data-mode` attribute on `<html>` | Both work; class is simpler to target with `.breakdown-mode` selector |
| Radix DropdownMenu | Custom dropdown | Radix already in project, handles keyboard nav, ARIA roles, portal rendering |
| Percentage flex widths | CSS Grid columns | Flex with pixel min-widths + percentage defaults is easier to implement resize handles for |

**Installation:** No new packages needed. All required libraries are already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── components/
│   ├── Layout/
│   │   ├── Header.tsx              # MODIFIED: add ModeToggle
│   │   ├── Layout.tsx              # unchanged
│   │   └── ModeToggle.tsx          # NEW: dropdown mode switcher
│   └── Breakdown/
│       ├── BreakdownLayout.tsx     # NEW: replaces BreakdownPage as route element
│       ├── BreakdownPanel.tsx      # NEW: reusable panel wrapper (header + content)
│       ├── BreakdownPage.tsx       # PRESERVED but no longer mounted at route
│       └── StalenessBar.tsx        # unchanged (reused in Phase 25)
├── lib/
│   └── constants.ts               # MODIFIED: add STORAGE_KEYS for panels, ROUTES.PROJECT_BREAKDOWN already exists
└── index.css                      # MODIFIED: add .breakdown-mode CSS variable overrides
```

### Pattern 1: CSS Variable Theme Override via Class

**What:** Add a `.breakdown-mode` class to `document.documentElement`. CSS selector `.breakdown-mode` overrides the same variable names established in `:root`, so every component using `hsl(var(--accent))` etc. automatically picks up the new palette.

**When to use:** Any time the entire chrome needs to shift visual identity on a route change.

**Example:**
```typescript
// Source: MDN CSS custom properties + React useEffect pattern
// In BreakdownLayout.tsx
import { useEffect } from 'react';

export function BreakdownLayout() {
  useEffect(() => {
    document.documentElement.classList.add('breakdown-mode');
    return () => {
      document.documentElement.classList.remove('breakdown-mode');
    };
  }, []);

  return (/* 3-panel layout */);
}
```

```css
/* Source: index.css — add after :root block */
.breakdown-mode {
  /* Backgrounds — cool slate-noir */
  --background: 220 13% 5%;
  --foreground: 210 20% 95%;

  --card: 220 12% 9%;
  --card-foreground: 210 15% 92%;

  --muted: 220 10% 16%;
  --muted-foreground: 215 12% 52%;

  /* Accent — steel blue */
  --accent: 213 80% 52%;
  --accent-foreground: 0 0% 98%;

  --primary: 213 80% 52%;
  --primary-foreground: 220 15% 8%;

  --secondary: 220 10% 16%;
  --secondary-foreground: 210 15% 88%;

  --border: 220 10% 18%;
  --input: 220 12% 12%;
  --ring: 213 80% 52%;

  --surface: 220 12% 12%;
  --surface-hover: 220 10% 16%;
  --border-strong: 220 10% 24%;
}
```

**Transition hook — add to `body` in `index.css`:**
```css
/* Smooth palette transitions */
body {
  transition:
    background-color 200ms ease,
    color 200ms ease;
}
```

**Why `transition` on `body` and not on `:root`:** CSS transitions on custom property changes are not directly animatable in all browsers. Transitioning `background-color` and `color` on `body` (and optionally on `header`) achieves the visible 200ms fade between modes reliably.

### Pattern 2: ModeToggle Dropdown (Radix DropdownMenu)

**What:** A contextual dropdown in the header that shows only when on a `/projects/:id*` route. Reads current mode from URL, navigates on selection.

**When to use:** Mode switching that is URL-driven with no additional state.

**Example:**
```typescript
// Source: @radix-ui/react-dropdown-menu API + useLocation/useNavigate (react-router-dom v6)
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ChevronDown, PenLine, Clapperboard } from 'lucide-react';

export function ModeToggle() {
  const location = useLocation();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();

  // Only render when inside a project route
  if (!projectId) return null;

  const isBreakdown = location.pathname.endsWith('/breakdown');
  const currentMode = isBreakdown ? 'breakdown' : 'screenwriting';

  const handleSelect = (mode: 'screenwriting' | 'breakdown') => {
    if (mode === 'breakdown') {
      navigate(`/projects/${projectId}/breakdown`);
    } else {
      navigate(`/projects/${projectId}`);
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md
          bg-muted/40 hover:bg-muted/70 text-foreground transition-colors">
          {currentMode === 'screenwriting'
            ? <PenLine className="h-3.5 w-3.5" />
            : <Clapperboard className="h-3.5 w-3.5" />}
          {currentMode === 'screenwriting' ? 'Screenwriting' : 'Script Breakdown'}
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className="z-50 min-w-[180px] rounded-lg border border-border
          bg-card shadow-lg p-1" sideOffset={4}>
          <DropdownMenu.Item
            onSelect={() => handleSelect('screenwriting')}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md cursor-pointer
              hover:bg-muted/60 text-foreground outline-none"
          >
            <PenLine className="h-3.5 w-3.5" />
            Screenwriting
            {currentMode === 'screenwriting' && <span className="ml-auto text-accent text-xs">Active</span>}
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onSelect={() => handleSelect('breakdown')}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md cursor-pointer
              hover:bg-muted/60 text-foreground outline-none"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            Script Breakdown
            {currentMode === 'breakdown' && <span className="ml-auto text-accent text-xs">Active</span>}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
```

### Pattern 3: Three-Panel Flex Layout with Percentage Widths

**What:** A flex-row container where left and right panels have pixel widths derived from percentage of viewport, and center panel gets `flex: 1` to fill remaining space. Drag handles rewrite the pixel widths. Collapse removes panel from flex flow (or sets width to 0 with overflow hidden).

**When to use:** Any 3-panel layout needing resize + collapse + localStorage persistence.

**Example:**
```typescript
// Source: ResizablePanel.tsx existing pattern extended to percentage-based defaults

interface PanelState {
  width: number;       // pixel width
  collapsed: boolean;
}

// Default widths from percentages at mount time
const DEFAULT_LEFT_PCT = 0.25;
const DEFAULT_RIGHT_PCT = 0.25;
const MIN_PANEL_PX = 200;  // minimum readable width

// Storage keys (add to STORAGE_KEYS in constants.ts)
const BREAKDOWN_LEFT_WIDTH = 'breakdown_left_width';
const BREAKDOWN_RIGHT_WIDTH = 'breakdown_right_width';
const BREAKDOWN_LEFT_COLLAPSED = 'breakdown_left_collapsed';
const BREAKDOWN_RIGHT_COLLAPSED = 'breakdown_right_collapsed';
```

**Layout skeleton:**
```tsx
// BreakdownLayout.tsx — outer structure
<div className="flex h-[calc(100vh-56px)] overflow-hidden">
  {/* Left panel */}
  <LeftPanel state={leftState} onResize={...} onCollapse={...} />
  {/* Drag handle L */}
  <DragHandle onMouseDown={handleLeftDragStart} />
  {/* Center panel — flex:1 */}
  <div className="flex-1 overflow-auto">
    <CenterPlaceholder />
  </div>
  {/* Drag handle R */}
  <DragHandle onMouseDown={handleRightDragStart} />
  {/* Right panel */}
  <RightPanel state={rightState} onResize={...} onCollapse={...} />
</div>
```

**Critical note:** The existing `ResizablePanel.tsx` is a right-side panel (drag handle on left edge, dragging left increases width). The new three-panel layout needs two drag handles: one between left and center, one between center and right. The left panel's handle drags right to increase left width; the right panel's handle drags left to increase right width. A new `ThreePanelLayout` component should own the drag logic rather than reusing `ResizablePanel.tsx` directly, because the existing component assumes a single-direction panel.

### Pattern 4: Collapse with localStorage

**What:** Collapsed panels hide their content and shrink to a minimal width (e.g., 36px for a vertical collapse button strip), or collapse to zero width with the expand button living in the center panel edge.

**Recommended approach:** Show a narrow 36px strip with a vertical label and expand icon when collapsed. This preserves spatial awareness.

**Example:**
```typescript
// BreakdownPanel.tsx
function BreakdownPanel({ title, collapsed, onCollapse, children, side }: BreakdownPanelProps) {
  if (collapsed) {
    return (
      <div className="w-9 flex-shrink-0 border-r border-border flex flex-col items-center py-3">
        <button onClick={onCollapse} className="text-muted-foreground hover:text-foreground">
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    );
  }
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border flex-shrink-0">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{title}</span>
        <button onClick={onCollapse}><ChevronLeft className="h-4 w-4" /></button>
      </div>
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  );
}
```

### Anti-Patterns to Avoid

- **Applying mode class to a React state variable rendered as a prop:** This causes re-renders on every mode change and doesn't propagate to portals (Radix dialogs, toasts). `document.documentElement.classList` is the correct target.
- **CSS `transition` on custom property values directly:** CSS doesn't animate `var()` changes. Animate `background-color`, `color`, `border-color` on concrete properties. The `:root`/`.breakdown-mode` override is instant; transitions on rendered elements smooth the visual.
- **Reusing the existing `ResizablePanel.tsx` for the center panel:** The center panel is `flex: 1`, not a fixed-width panel. Only left and right have fixed pixel widths. Don't wrap the center in `ResizablePanel`.
- **Hardcoding the breakdown mode as a path-detection boolean in multiple places:** Compute `isBreakdown` once in `ModeToggle` and `BreakdownLayout`. Don't duplicate `location.pathname.endsWith('/breakdown')` across files.
- **Forgetting to clean up the `.breakdown-mode` class on unmount:** Without the `useEffect` cleanup, navigating away from breakdown leaves the entire app styled in the cool palette.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accessible dropdown with keyboard nav | Custom `<select>` or div-based dropdown | `@radix-ui/react-dropdown-menu` (already installed) | Focus management, ARIA roles, portal rendering are complex |
| Mode detection across components | Custom React Context for mode | React Router's `useLocation()` + URL pattern | URL IS the mode state; no sync needed |
| CSS variable transition | JS-based style interpolation | CSS `transition` on `body`/`header` `background-color` | Browser handles interpolation; no JS frames |
| Panel resize logic | Event handler re-invention | Extend the `mousemove`/`mouseup` pattern from existing `ResizablePanel.tsx` | Tested, handles cleanup correctly |

**Key insight:** The entire mode identity problem collapses to a CSS class on `<html>`. React Router handles mode state via URL. No Redux, no Context, no extra state management is needed.

---

## Common Pitfalls

### Pitfall 1: Mode Class Leaks After Navigation
**What goes wrong:** User navigates from `/projects/:id/breakdown` to `/books`. The `.breakdown-mode` class stays on `<html>`, making the books page render in the cool palette.
**Why it happens:** `useEffect` cleanup wasn't implemented, or component tree was replaced without proper unmount.
**How to avoid:** The `useEffect` in `BreakdownLayout` MUST return a cleanup function that removes the class. React Router v6 fully unmounts the previous route component when navigating away.
**Warning signs:** Books or Projects pages showing steel-blue accent after visiting breakdown.

### Pitfall 2: Tailwind JIT Not Scanning Breakdown CSS Class
**What goes wrong:** Custom Tailwind utilities referencing `breakdown-mode` selectors get purged in production build.
**Why it happens:** Tailwind scans `./src/**/*.{js,ts,jsx,tsx}` but not `index.css` — actually `index.css` IS included in processing via `@tailwind base/components/utilities`. The `.breakdown-mode` CSS variable block lives in `index.css` under `@layer base` and uses standard CSS properties, not Tailwind classes, so purging is not an issue.
**How to avoid:** Put the `.breakdown-mode {}` block directly in `index.css` inside `@layer base` (same layer as `:root`). No Tailwind classes inside that block — just raw CSS custom property assignments.

### Pitfall 3: ResizablePanel Direction Mismatch
**What goes wrong:** Left panel drag handle configured for right-panel direction (dragging increases width when moving left, i.e., current `ResizablePanel.tsx` behavior). For the left panel, dragging right should increase width.
**Why it happens:** Copying existing `ResizablePanel.tsx` logic (which assumes right-side panel: `delta = startX - e.clientX`).
**How to avoid:** For the left panel handle, use `delta = e.clientX - startX` (dragging right = positive delta = wider left panel). For the right panel handle, use `delta = startX - e.clientX` (matches existing pattern).

### Pitfall 4: Panel Width Initialization Without Window Width
**What goes wrong:** Percentage-based default widths (25%) cannot be stored in localStorage as percentages and then read back correctly if the viewport size changed. Storing the initial pixel value (25% of `window.innerWidth`) and then reading it back will be wrong if the window was resized between sessions.
**How to avoid:** Store pixel widths in localStorage but initialize from percentage of `window.innerWidth` when no stored value exists. On resize of the browser window, clamp panel widths to not exceed (window.innerWidth - MIN_CENTER_WIDTH) / 2. Or, simpler: accept that stored pixel widths may produce sub-optimal initial sizes after viewport resize — this is acceptable MVP behavior. The user can drag to adjust.

### Pitfall 5: `useParams` Returns `undefined` Outside Route
**What goes wrong:** `ModeToggle` tries to read `projectId` from `useParams` but Header renders at all routes, including `/books` where `:projectId` is undefined.
**Why it happens:** `useParams` returns an empty object outside a route match.
**How to avoid:** Guard with `if (!projectId) return null` inside `ModeToggle`. This is already the pattern recommended in the code examples above.

### Pitfall 6: Route Conflict Between `/projects/:projectId/breakdown` and `/projects/:projectId/:phase`
**What goes wrong:** React Router v6 matches `/projects/:id/breakdown` against the `/projects/:projectId/:phase` route before the specific breakdown route, passing "breakdown" as the `:phase` param to `ProjectWorkspace`.
**Why it happens:** React Router v6 uses "best match" ranking, but if the breakdown route is declared after the `:phase` wildcard, the wildcard may win.
**How to avoid:** In `App.tsx`, declare the specific `/projects/:projectId/breakdown` route BEFORE the wildcard `/projects/:projectId/:phase` route. React Router v6 selects the most specific match when routes are ordered correctly. The existing `App.tsx` already has this correct order (line 31 before line 32).

---

## Code Examples

### Verified: Route Order in App.tsx (existing, correct)
```typescript
// Source: frontend/src/App.tsx — current state
<Route path="/projects/:projectId" element={<Editor />} />
<Route path="/projects/:projectId/breakdown" element={<BreakdownPage />} />  // specific FIRST
<Route path="/projects/:projectId/:phase" element={<ProjectWorkspace />} />  // wildcard after
```
Phase 18 replaces `BreakdownPage` with `BreakdownLayout` — the route ordering stays the same.

### Verified: Existing CSS Variable Structure (index.css)
```css
/* Source: frontend/src/index.css */
@layer base {
  :root {
    --background: 240 6% 3.5%;
    --foreground: 0 0% 97%;
    --accent: 38 92% 50%;          /* warm amber */
    --primary: 38 92% 50%;
    --ring: 38 92% 50%;
    /* ... */
  }
}
/* Phase 18 adds: */
@layer base {
  .breakdown-mode {
    --background: 220 13% 5%;
    --foreground: 210 20% 95%;
    --accent: 213 80% 52%;          /* steel blue */
    --primary: 213 80% 52%;
    --ring: 213 80% 52%;
    /* ... */
  }
}
```

### Verified: Existing ResizablePanel.tsx Pattern
```typescript
// Source: frontend/src/components/UI/ResizablePanel.tsx
// Pattern: localStorage init, mousemove/mouseup on document, drag handle div
// Reuse this pattern for left and right panel resize in ThreePanelLayout
const [width, setWidth] = useState(() => {
  if (storageKey) {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      const parsed = parseInt(stored, 10);
      if (!isNaN(parsed) && parsed >= minWidth && parsed <= maxWidth) return parsed;
    }
  }
  return defaultWidth;
});
```

### Verified: Header.tsx useLocation Pattern
```typescript
// Source: frontend/src/components/Layout/Header.tsx
import { Link, useLocation } from 'react-router-dom';
const location = useLocation();
const isActive = (path: string) => {
  if (path === '/') return location.pathname === '/';
  return location.pathname.startsWith(path);
};
```
Phase 18 extends this: `ModeToggle` uses the same `useLocation` to detect `/projects/:id/breakdown` pattern.

### Verified: STORAGE_KEYS Pattern (constants.ts)
```typescript
// Source: frontend/src/lib/constants.ts
export const STORAGE_KEYS = {
  THEME: 'theme',
  LAST_PROJECT_ID: 'last_project_id',
  SIDEBAR_COLLAPSED: 'sidebar_collapsed',
  SIDEBAR_CHAT_WIDTH: 'sidebar_chat_width',
  // Phase 18 adds:
  BREAKDOWN_LEFT_WIDTH: 'breakdown_left_width',
  BREAKDOWN_RIGHT_WIDTH: 'breakdown_right_width',
  BREAKDOWN_LEFT_COLLAPSED: 'breakdown_left_collapsed',
  BREAKDOWN_RIGHT_COLLAPSED: 'breakdown_right_collapsed',
} as const;
```

### Recommended Breakdown Mode Color Palette (Claude's discretion)
```css
/* Cool slate/blue-grey — complements "Cinematic Amber" without clashing */
.breakdown-mode {
  /* Backgrounds — deeper blue-tinged noir */
  --background: 220 13% 5%;       /* was 240 6% 3.5% — adds blue undertone */
  --foreground: 210 20% 95%;      /* was 0 0% 97% — cooler white */

  --card: 220 12% 9%;             /* was 240 5% 7% */
  --card-foreground: 210 15% 92%;

  --muted: 220 10% 16%;           /* was 240 4% 14% */
  --muted-foreground: 215 12% 52%;

  /* Accent — steel blue / slate-indigo */
  --accent: 213 80% 52%;          /* was 38 92% 50% amber → steel blue */
  --accent-foreground: 0 0% 98%;

  --primary: 213 80% 52%;
  --primary-foreground: 220 15% 8%;

  --secondary: 220 10% 16%;
  --secondary-foreground: 210 15% 88%;

  --destructive: 0 72% 51%;       /* unchanged — red stays red */
  --destructive-foreground: 0 0% 98%;

  --border: 220 10% 18%;          /* was 240 4% 15% */
  --input: 220 12% 12%;           /* was 240 5% 10% */
  --ring: 213 80% 52%;            /* matches accent */

  --surface: 220 12% 12%;
  --surface-hover: 220 10% 16%;
  --border-strong: 220 10% 24%;

  /* Phase colors — unchanged */
  --phase-idea: 263 70% 58%;
  --phase-story: 217 91% 60%;
  --phase-scenes: 38 92% 50%;
  --phase-write: 160 84% 39%;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| React Context for theme switching | CSS class on `<html>` with `@layer base` selectors | CSS custom properties widely supported since ~2017 | No re-renders, portals inherit theme automatically |
| Fixed-width sidebar panels | Percentage-default + pixel-stored resizable panels | Standard production app pattern (e.g., VS Code) | Better UX across screen sizes |
| `react-router-dom` v5 `useHistory` | v6 `useNavigate()` | v6 released 2021 | Already using v6 in this project |

**Deprecated/outdated:**
- `useHistory`: Replaced by `useNavigate` in react-router-dom v6. Not used in this project.
- `ReactDOM.createPortal` for dropdown: Radix handles this internally. Not needed manually.

---

## Open Questions

1. **Panel height calculation: `100vh - 56px` vs `flex-1`**
   - What we know: Header is `h-14` (56px), Layout wraps content in `<main>`. Layout.tsx uses `min-h-screen bg-background` on the wrapper div.
   - What's unclear: Whether `<main>` has `flex-1` + `overflow-hidden` to fill remaining height, or whether `BreakdownLayout` needs to use `calc(100vh - 56px)`.
   - Recommendation: `BreakdownLayout` should use `h-[calc(100vh-3.5rem)]` (3.5rem = 56px = h-14) as the panel container height. This is safe regardless of whether Layout.tsx wraps `<main>` with flex.

2. **Project context preservation on mode switch (MODE-05)**
   - What we know: Both routes contain `:projectId`. React Query cache is keyed by projectId. Navigating `/projects/X` → `/projects/X/breakdown` doesn't clear the cache.
   - What's unclear: Nothing — this is satisfied automatically by URL-based routing + React Query cache.
   - Recommendation: No special implementation needed. MODE-05 is satisfied by architecture.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Pytest (backend only) — no frontend test framework configured |
| Config file | `backend/app/tests/conftest.py` |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/` |

### Phase Requirements → Test Map

Phase 18 is entirely frontend (React components, CSS, routing). No backend code changes. No existing frontend test framework (no Vitest, Jest, or Playwright configured).

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODE-01 | Header ModeToggle renders on project routes | manual-only | N/A | N/A |
| MODE-02 | Screenwriting mode shows existing workspace unchanged | manual-only | N/A | N/A |
| MODE-03 | Breakdown route renders 3-panel skeleton | manual-only | N/A | N/A |
| MODE-04 | Breakdown mode applies cool palette to entire chrome | manual-only | N/A | N/A |
| MODE-05 | Mode switch preserves project context | manual-only | N/A | N/A |

**Manual-only justification:** No frontend test infrastructure exists in this project (confirmed: no `*.test.*` files in `frontend/src/`, no Vitest/Jest in `package.json`). All verification is visual/manual via `npm run dev`. The backend pytest suite covers no frontend concerns and need not be run for Phase 18.

### Sampling Rate
- **Per task commit:** Run `npm run lint` from `frontend/` — confirms TypeScript compiles and ESLint passes (`--max-warnings 0`)
- **Per wave merge:** `npm run build` from `frontend/` — confirms production build succeeds
- **Phase gate:** Manual smoke test checklist (see below) before `/gsd:verify-work`

**Manual Smoke Test Checklist (Phase Gate):**
- [ ] Header shows "Screenwriting" dropdown on `/projects/:id` route
- [ ] Header shows "Script Breakdown" dropdown on `/projects/:id/breakdown` route
- [ ] Header shows NO mode dropdown on `/projects`, `/books`, `/snippets` routes
- [ ] Selecting "Script Breakdown" navigates to `/projects/:id/breakdown`
- [ ] Selecting "Screenwriting" navigates back to `/projects/:id`
- [ ] Breakdown mode header/chrome is visually blue-grey (not amber)
- [ ] Returning to screenwriting mode restores amber palette
- [ ] No `.breakdown-mode` class on `<html>` after navigating away from breakdown
- [ ] 3 panels render with placeholder content
- [ ] Left and right panels are resizable via drag
- [ ] Left and right panels are collapsible
- [ ] Panel widths restore from localStorage on page refresh

### Wave 0 Gaps
- [ ] `npm run lint` must pass with zero warnings after new files are added
- [ ] `npm run build` must succeed before marking phase complete

*(No new test files to create — frontend test infrastructure does not exist for this project and is out of scope for Phase 18)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `frontend/src/App.tsx`, `Header.tsx`, `index.css`, `constants.ts`, `ResizablePanel.tsx`, `BreakdownPage.tsx`, `Layout.tsx`, `tailwind.config.js`, `package.json`
- `.planning/phases/18-two-mode-ui-shell/18-CONTEXT.md` — user locked decisions
- `.planning/REQUIREMENTS.md` — MODE-01 through MODE-05 definitions

### Secondary (MEDIUM confidence)
- React Router v6 API (`useNavigate`, `useLocation`, `useParams`) — stable since v6.0 (2021), confirmed in use in `Header.tsx`
- `@radix-ui/react-dropdown-menu` v2.0.6 — confirmed installed in `package.json`; API stable
- CSS custom properties + class scoping — MDN-documented, widely supported, no library needed

### Tertiary (LOW confidence)
- None — all findings are based on direct codebase inspection or well-established browser APIs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — entire stack verified from installed package.json and existing component files
- Architecture: HIGH — CSS class approach is established pattern; all integration points inspected directly
- Pitfalls: HIGH — derived from direct code inspection (route ordering, direction logic in ResizablePanel, cleanup pattern)
- Color palette: MEDIUM — values are Claude's discretion per CONTEXT.md; subjective aesthetic judgment

**Research date:** 2026-03-19
**Valid until:** 2026-06-19 (stable CSS/React foundations; no fast-moving dependencies)
