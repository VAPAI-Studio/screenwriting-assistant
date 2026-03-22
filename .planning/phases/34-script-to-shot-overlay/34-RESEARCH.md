# Phase 34: Script-to-Shot Overlay - Research

**Researched:** 2026-03-22
**Domain:** Frontend text matching / overlay highlighting with popover interaction in React
**Confidence:** HIGH

## Summary

Phase 34 adds a visual overlay to the script read view that highlights passages of text referenced by shots in the shotlist. This is a purely frontend feature -- no backend changes are needed. The existing `listShots` API already returns all shot data including the `script_text` field, and `ScriptReadView` already queries shots via `QUERY_KEYS.SHOTS(projectId)`. The core challenge is substring matching (finding where each shot's `script_text` appears in the screenplay text) and layering a background tint on those ranges without conflicting with the existing element highlighting from Phase 33.

Phase 33 established a proven pattern: a pure utility function (`textHighlight.ts`) performs text segmentation, and a React component (`HighlightedScriptText.tsx`) renders the segments with interactive spans. For Phase 34, the approach should follow the same architecture: a new utility function that identifies shot-covered ranges in the text, and integration into `HighlightedScriptText` (or a wrapper) that applies a low-opacity background tint to those ranges. The two highlight layers (element underline + shot background) must coexist since they use different visual channels (underline vs. background-color).

Since `@radix-ui/react-popover` is not installed and the project avoids adding unnecessary dependencies, the popover for showing linked shots should be built as a simple positioned div (similar to the existing `SelectionBar` component pattern) rather than installing a new Radix primitive.

**Primary recommendation:** Build a `buildShotOverlaySegments` utility that performs substring matching of shot `script_text` values against screenplay text, integrate it as a background-tint layer in the existing `HighlightedScriptText` component, and add a custom popover component (no new dependencies) that appears on click to show linked shot details.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SSO-01 | Script passages referenced by a shot (via script_text field) are highlighted with a low-opacity background tint in the script read view. The highlight color matches the breakdown mode steel-blue accent. Clicking a highlighted passage opens a popover showing the linked shot(s) with their fields. Shots with no script_text reference do not create any highlight. | Shots already fetched in ScriptReadView (line 69-73); Shot.script_text field exists in DB model and TypeScript type; steel-blue accent is `hsl(213 80% 52%)` defined in `.breakdown-mode` CSS variables; popover pattern available from SelectionBar; element highlight + shot overlay can coexist (underline vs background) |
</phase_requirements>

## Standard Stack

### Core (already installed -- zero new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | ^18.2.0 | Component rendering, `useMemo` for segment computation | Already in use |
| TypeScript | ^5.2.2 | Type safety for shot overlay types | Already in use |
| Tailwind CSS | ^3.4.1 | Utility classes for overlay styling | Already in use |
| React Query | ^5.20.1 | `useQuery` for shots data (already fetched) | Already in use in ScriptReadView |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | ^0.314.0 | Icons in shot popover (Camera, Video, etc.) | Shot field display in popover |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom popover div | @radix-ui/react-popover | Would add a dependency; project pattern (SelectionBar) already demonstrates positioned floating UI without Radix Popover |
| Regex-based matching | Simple `indexOf`/`includes` | Regex adds complexity; since shot `script_text` is an exact substring copied from the screenplay, `indexOf` is sufficient and more reliable |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Approach: Two-Layer Highlighting

The key insight is that Phase 33's element highlights use **text-decoration (underline)** while Phase 34's shot overlay uses **background-color**. These are orthogonal visual channels that can coexist on the same `<span>` elements without conflict.

**Architecture:**

```
ScriptReadView
  |-- useQuery(SHOTS) ............... already exists (line 69-73)
  |-- useQuery(BREAKDOWN_ELEMENTS) .. already exists (line 76-80)
  |
  +-- HighlightedScriptText (modified)
        |-- buildHighlightSegments() .... Phase 33 element segmentation (unchanged)
        |-- buildShotOverlayMap() ....... NEW: maps text ranges to shots
        |-- Rendering: each segment <span> gets both:
              - element-highlight class (underline) if element match
              - shot-overlay background style if covered by shot
              - onClick: element click -> navigate; shot-overlay click -> popover
        |
        +-- ShotOverlayPopover (NEW)
              |-- Positioned near clicked text
              |-- Shows linked shot(s): shot_number, fields summary
              |-- Dismiss on click-outside or Escape
```

### Pattern 1: Substring Matching for Shot Overlay

**What:** Find where each shot's `script_text` appears within the full screenplay scene text using simple string indexOf.

**When to use:** When the source text (`script_text`) is an exact copy of a substring from the target text (the screenplay content). This is guaranteed because shots are created by selecting text in the script read view (Phase 21).

**Example:**

```typescript
// frontend/src/lib/shotOverlay.ts

import type { Shot } from '../types';

export interface ShotOverlayRange {
  start: number;
  end: number;
  shots: Shot[]; // Multiple shots may reference overlapping text
}

/**
 * Build a character-level coverage map indicating which characters
 * in `text` are covered by at least one shot's script_text.
 * Returns merged, non-overlapping ranges with associated shots.
 */
export function buildShotOverlayRanges(
  text: string,
  shots: Shot[],
): ShotOverlayRange[] {
  if (!text || !shots.length) return [];

  // Filter to shots that have non-empty script_text
  const relevantShots = shots.filter(s => s.script_text?.trim());
  if (!relevantShots.length) return [];

  // Build per-character shot coverage array
  const coverage: Set<Shot>[] = Array.from({ length: text.length }, () => new Set());

  for (const shot of relevantShots) {
    const needle = shot.script_text.trim();
    let idx = text.indexOf(needle);
    while (idx !== -1) {
      for (let i = idx; i < idx + needle.length; i++) {
        coverage[i].add(shot);
      }
      idx = text.indexOf(needle, idx + 1);
    }
  }

  // Merge contiguous covered characters into ranges
  const ranges: ShotOverlayRange[] = [];
  let rangeStart = -1;
  let currentShots: Set<Shot> | null = null;

  for (let i = 0; i <= text.length; i++) {
    const covered = i < text.length && coverage[i].size > 0;
    if (covered) {
      if (rangeStart === -1) {
        rangeStart = i;
        currentShots = new Set(coverage[i]);
      } else {
        // Extend range, accumulate shots
        for (const s of coverage[i]) currentShots!.add(s);
      }
    } else if (rangeStart !== -1) {
      ranges.push({ start: rangeStart, end: i, shots: [...currentShots!] });
      rangeStart = -1;
      currentShots = null;
    }
  }

  return ranges;
}
```

### Pattern 2: Integrating Shot Overlay into HighlightedScriptText

**What:** Extend the existing `HighlightedScriptText` component to accept shots data and apply background tinting to shot-covered text segments.

**When to use:** Always -- the two highlight layers must be computed together to produce correct span boundaries.

**Example concept:**

```typescript
// In HighlightedScriptText.tsx - add shots prop
interface HighlightedScriptTextProps {
  text: string;
  elements: BreakdownElement[];
  shots: Shot[];       // NEW
  projectId: string;
  onShotClick?: (shots: Shot[], rect: DOMRect) => void; // NEW
}

// In rendering, each span checks if it falls within a shot overlay range
// and applies: style={{ backgroundColor: 'hsl(213 80% 52% / 0.12)' }}
```

### Pattern 3: Custom Popover (No New Dependencies)

**What:** A positioned floating card that shows shot details when clicking a shot-highlighted passage. Follows the exact same pattern as `SelectionBar.tsx`.

**When to use:** On click of a shot-overlay-highlighted passage.

**Example:**

```typescript
// ShotOverlayPopover.tsx
interface ShotOverlayPopoverProps {
  shots: Shot[];
  rect: DOMRect;
  onDismiss: () => void;
}

// Renders a fixed-positioned card below the clicked text showing:
// - For each linked shot: shot number, scene, shot_size, camera_angle, description
// - Dismisses on click outside or Escape (same pattern as SelectionBar)
```

### Anti-Patterns to Avoid

- **Separate DOM layer for shot overlay:** Do NOT create a separate absolutely-positioned div overlaying the script text for highlighting. This breaks text selection, creates z-index issues, and does not track line wrapping. Instead, apply the background directly to the text `<span>` elements.
- **Re-rendering all text on shot hover:** The overlay ranges should be computed once in `useMemo` and not recomputed on hover/click interactions.
- **Installing @radix-ui/react-popover:** The project already demonstrates the floating-card pattern with `SelectionBar`. Adding a new Radix dependency for a single popover is unnecessary overhead.
- **Modifying the textHighlight.ts utility:** The existing `buildHighlightSegments` function should NOT be modified. Shot overlay logic should be a separate utility. The integration happens in the component layer, not the segmentation layer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Popover positioning | Custom absolute positioning math | `getBoundingClientRect()` + fixed positioning (SelectionBar pattern) | SelectionBar already does this correctly; the pattern handles viewport edges implicitly |
| Text substring search | Fuzzy matching or regex | `String.prototype.indexOf` | Shot script_text is an exact copy; indexOf is O(n*m) but for screenplay-length texts (< 50KB) this is instant |

**Key insight:** This phase is entirely frontend. All data is already available from existing API calls. The complexity is in the text-to-span mapping and the interaction between two highlight layers.

## Common Pitfalls

### Pitfall 1: Overlapping Shot Ranges Creating Duplicate Spans

**What goes wrong:** Two shots reference overlapping passages. Naive implementation creates nested or duplicate spans that break DOM structure.
**Why it happens:** Multiple shots can reference the same text (e.g., a wide establishing shot and a close-up both cite the same scene description).
**How to avoid:** Use the character-level coverage map approach (as in the code example above) to merge overlapping ranges into single spans with a `shots` array. Never nest shot-highlight spans.
**Warning signs:** Visual glitches where highlighted areas have double opacity, or clicking shows wrong shot data.

### Pitfall 2: Shot script_text Not Found in Current Screenplay Text

**What goes wrong:** A shot's `script_text` was captured from an earlier version of the screenplay. The user has since edited the script, and the substring no longer exists.
**Why it happens:** There is no automatic sync between screenplay edits and shot script_text. The staleness system flags this but does not update shot text.
**How to avoid:** Silently skip shots whose `script_text` is not found via `indexOf`. Do not show an error. Those shots simply produce no overlay (which is correct behavior -- SSO-01 says "Shots with no script_text reference do not create any highlight").
**Warning signs:** Console warnings about unmatched shots (should not produce warnings -- just skip).

### Pitfall 3: Element Highlight Click Conflicting with Shot Overlay Click

**What goes wrong:** A character name sits inside a shot-referenced passage. Clicking it could trigger both element navigation AND shot popover.
**Why it happens:** Both click handlers fire on the same DOM element.
**How to avoid:** Element highlights should take click priority (they already use `e.stopPropagation()`). The shot overlay click handler should be on a wrapper span that only fires if the click was not on an element-highlight span. Use event delegation or check `e.target` class.
**Warning signs:** Clicking an element name opens the popover instead of navigating to the element page.

### Pitfall 4: Performance with Many Shots

**What goes wrong:** For a project with 100+ shots, computing overlay ranges for every scene on every render is slow.
**Why it happens:** The overlay computation is O(shots * text_length) per scene.
**How to avoid:** Use `useMemo` with `[text, shots]` dependency. Pre-filter shots to only those belonging to the current scene (via `scene_item_id`). The per-scene shot count is typically 5-20, making this negligible.
**Warning signs:** Jank when switching scenes or after adding a new shot.

## Code Examples

### Existing Data Flow (Already Wired)

ScriptReadView already fetches shots at line 69-73:

```typescript
// ScriptReadView.tsx (existing)
const { data: shots } = useQuery({
  queryKey: QUERY_KEYS.SHOTS(projectId),
  queryFn: () => api.listShots(projectId),
  enabled: !!projectId,
});
```

The Shot type already has the `script_text` field:

```typescript
// types/index.ts (existing)
export interface Shot {
  id: string;
  project_id: string;
  scene_item_id: string | null;
  shot_number: number;
  script_text: string;          // <-- This is the key field
  fields: ShotFields;           // shot_size, camera_angle, etc.
  sort_order: number;
  source: 'user' | 'ai';
  ai_generated: boolean;
  // ...
}
```

### Steel-Blue Accent Color (Breakdown Mode)

The breakdown mode CSS variables define the accent:

```css
/* index.css (existing) */
.breakdown-mode {
  --accent: 213 80% 52%;  /* Steel blue */
}
```

For the shot overlay background tint, use: `hsl(213 80% 52% / 0.12)` for a low-opacity version of this accent. This can be a CSS class:

```css
.shot-overlay {
  background-color: hsl(213 80% 52% / 0.12);
  border-radius: 2px;
  cursor: pointer;
  transition: background-color 150ms ease;
}
.shot-overlay:hover {
  background-color: hsl(213 80% 52% / 0.22);
}
```

Using the raw HSL value rather than `hsl(var(--accent) / 0.12)` is acceptable here since this overlay is specific to breakdown mode and the steel-blue is a fixed design choice per the requirement.

### SelectionBar Positioning Pattern (Reuse for Popover)

```typescript
// SelectionBar.tsx (existing pattern to follow)
<div
  style={{
    position: 'fixed',
    top: rect.bottom + 8,
    left: rect.left + rect.width / 2,
    transform: 'translateX(-50%)',
    zIndex: 50,
  }}
>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate overlay div layer | Inline span background-color | Phase 33 established the inline-span pattern | All highlighting done via span styling, no overlay divs |
| Install Radix Popover | Custom positioned div | Project convention since Phase 21 (SelectionBar) | No new dependency for floating UI |

## Open Questions

1. **Multiple shots referencing identical text**
   - What we know: Multiple shots can have the same `script_text` (e.g., AI generates shots covering the same passage). The overlay should group them.
   - What's unclear: Should the popover display all linked shots, or only distinct shots? (Likely all -- the user needs to see each shot's different camera angle, etc.)
   - Recommendation: Show all linked shots in the popover, sorted by shot_number.

2. **Case sensitivity in substring matching**
   - What we know: Shot `script_text` is created by `window.getSelection().toString()` in `ScriptReadView`, which preserves the original casing.
   - What's unclear: Could AI-generated shots (Phase 26) have slightly different casing or whitespace?
   - Recommendation: Use case-sensitive `indexOf` first. If no match, fall back to case-insensitive match. If still no match, skip (the shot was created from a since-edited script).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), TypeScript compiler (frontend) |
| Config file | backend/pytest.ini or inline; frontend tsconfig.json |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/frontend && npx tsc --noEmit` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SSO-01a | Shot-covered text gets background highlight | manual-only | N/A -- visual CSS rendering | N/A |
| SSO-01b | Highlight color is steel-blue accent | manual-only | N/A -- visual CSS color | N/A |
| SSO-01c | Click highlighted passage opens shot popover | manual-only | N/A -- runtime click interaction | N/A |
| SSO-01d | Shots without script_text produce no highlight | manual-only | N/A -- requires running app | N/A |
| SSO-01e | TypeScript compiles without new errors | unit | `cd frontend && npx tsc --noEmit` | N/A |

**Justification for manual-only:** This phase is entirely frontend visual/interactive behavior. The key automated check is TypeScript compilation. All visual and interaction behaviors require a running browser.

### Sampling Rate

- **Per task commit:** `cd frontend && npx tsc --noEmit`
- **Per wave merge:** Full tsc + backend pytest
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

None -- this phase creates a new pure utility file (`shotOverlay.ts`) and modifies existing components. No test infrastructure changes needed. TypeScript compilation is the automated gate.

## Sources

### Primary (HIGH confidence)

- **Codebase inspection** -- `ScriptReadView.tsx` (231 lines), `HighlightedScriptText.tsx` (43 lines), `textHighlight.ts` (99 lines), `SelectionBar.tsx` (70 lines), `ShotRow.tsx` (62 lines)
- **Database model** -- `Shot` model in `database.py` with `script_text = Column(Text, default="")` at line 550
- **TypeScript types** -- `Shot` interface in `types/index.ts` with `script_text: string` at line 336
- **CSS theme** -- `index.css` breakdown-mode accent `213 80% 52%` at line 62
- **Existing API** -- `api.listShots(projectId)` in `api.tsx` at line 886; `QUERY_KEYS.SHOTS` in `constants.ts` at line 190

### Secondary (MEDIUM confidence)

- **Phase 33 verification** -- `33-VERIFICATION.md` confirms element highlighting works with underlines, click navigation, and `e.stopPropagation()` for event isolation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all existing packages
- Architecture: HIGH -- follows exact patterns from Phase 33 (text segmentation utility + component rendering) and Phase 21 (SelectionBar positioning)
- Pitfalls: HIGH -- identified from direct codebase analysis of interaction between element highlights and shot overlay; overlap/event conflict analysis based on reading actual code

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable -- no external dependencies, all internal codebase patterns)
