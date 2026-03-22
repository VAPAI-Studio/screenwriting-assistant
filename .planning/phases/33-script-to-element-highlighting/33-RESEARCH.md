# Phase 33: Script-to-Element Highlighting - Research

**Researched:** 2026-03-22
**Domain:** Frontend text highlighting, DOM text matching, tooltip/navigation UX
**Confidence:** HIGH

## Summary

Phase 33 adds inline highlighting to the ScriptReadView component so that every mention of a breakdown element (character name, prop mention, location heading) in the screenplay text is visually highlighted with a color-coded underline, shows a tooltip on hover, and navigates to the element's detail page on click. This is a purely frontend feature -- all required backend data (element names, categories, IDs) is already available via the existing `GET /api/breakdown/elements/{project_id}` endpoint, and the element detail page route (`/projects/:projectId/breakdown/elements/:elementId`) was built in Phase 32.

The core technical challenge is client-side text matching: given a list of element names, find every occurrence within the screenplay `<pre>` content and wrap each match in a clickable, hoverable `<span>`. This must coexist with the existing text-selection-to-shot feature without interference. The matching must be case-insensitive, whole-word aware (to avoid highlighting "arm" inside "farmer"), and handle multiple elements sharing overlapping text gracefully (longest match wins).

**Primary recommendation:** Build a pure React text-processing utility that splits screenplay text into segments (plain text vs. matched element), renders matched segments as styled `<span>` elements with inline event handlers, and uses a simple CSS-only tooltip (no new dependencies needed). Avoid DOM mutation approaches (MutationObserver, dangerouslySetInnerHTML) -- use React's rendering model.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEL-01 | Character names, prop mentions, and location headings in the script are highlighted with a color-coded underline matching their element category; hovering shows tooltip with element name and category; clicking navigates to element detail page | All data available via existing `getBreakdownElements` API; ScriptReadView renders screenplay text as `<pre>` content per scene; ROUTES.ELEMENT_DETAIL and useNavigate already wired; category-to-color mapping is new but trivial; tooltip can be CSS-only or Radix Tooltip |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 18 | 18.x | Component rendering, text segmentation | Already in project |
| @tanstack/react-query | 5.x | Fetch breakdown elements for a project | Already in project, used by ScriptReadView |
| react-router-dom | 6.x | `useNavigate` for click-to-detail navigation | Already in project |
| Tailwind CSS | 3.x | Underline colors, tooltip styling | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-tooltip | 1.1.x | Accessible tooltip on hover | Only if CSS-only tooltip is insufficient for accessibility needs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS-only tooltip | @radix-ui/react-tooltip | Radix adds ~5KB but is accessible (aria, focus management); CSS tooltip is zero-dep but less accessible. Recommend CSS-only for MVP since these are decorative hover hints, not critical UI. |
| React text segmentation | dangerouslySetInnerHTML | innerHTML breaks React's model, loses event handlers, creates XSS surface. Never use for this. |
| Client-side matching | Backend endpoint returning annotated text | Backend approach adds API complexity and latency for something that can be done efficiently client-side with ~50 elements max. |

**Installation:**
```bash
# No new packages needed for the recommended approach.
# If Radix Tooltip is desired:
cd frontend && npm install @radix-ui/react-tooltip
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
  components/Breakdown/
    ScriptReadView.tsx          # Modified: uses HighlightedScriptText
    HighlightedScriptText.tsx   # NEW: text segmentation + rendering
  lib/
    constants.ts                # Modified: add CATEGORY_COLORS map
    textHighlight.ts            # NEW: pure function for text matching
```

### Pattern 1: React Text Segmentation
**What:** A pure function that takes raw text and a list of elements, returns an array of segments (either plain text or element-match objects). A React component maps these segments to `<span>` elements.
**When to use:** Whenever you need to highlight known terms inside a block of text in React.
**Example:**
```typescript
// textHighlight.ts — pure function, no React dependency

interface ElementMatch {
  elementId: string;
  elementName: string;
  category: BreakdownCategory;
}

interface TextSegment {
  type: 'text' | 'highlight';
  content: string;
  match?: ElementMatch;
}

function buildHighlightSegments(
  text: string,
  elements: BreakdownElement[]
): TextSegment[] {
  // 1. Sort elements by name length descending (longest match first)
  // 2. Build a combined regex: /\b(name1|name2|name3)\b/gi
  // 3. Use regex.exec() in a loop to find all matches
  // 4. Build segments array alternating between plain text and highlights
  // 5. Return segments
}
```

```tsx
// HighlightedScriptText.tsx — React component

function HighlightedScriptText({ text, elements, projectId }: Props) {
  const navigate = useNavigate();
  const segments = useMemo(
    () => buildHighlightSegments(text, elements),
    [text, elements]
  );

  return (
    <>
      {segments.map((seg, i) =>
        seg.type === 'text' ? (
          <span key={i}>{seg.content}</span>
        ) : (
          <span
            key={i}
            className={`element-highlight element-highlight--${seg.match!.category}`}
            title={`${seg.match!.elementName} (${seg.match!.category})`}
            onClick={(e) => {
              e.stopPropagation();
              navigate(ROUTES.ELEMENT_DETAIL(projectId, seg.match!.elementId));
            }}
            style={{ cursor: 'pointer' }}
          >
            {seg.content}
          </span>
        )
      )}
    </>
  );
}
```

### Pattern 2: Category Color Map
**What:** A constant mapping each BreakdownCategory to an underline color, defined in constants.ts alongside the existing BREAKDOWN_CATEGORIES.
**When to use:** For color-coding highlights by element type.
**Example:**
```typescript
// constants.ts addition

export const CATEGORY_COLORS: Record<BreakdownCategory, string> = {
  character:  'rgb(251, 191, 36)',    // amber-400
  location:   'rgb(96, 165, 250)',    // blue-400
  prop:       'rgb(74, 222, 128)',    // green-400
  wardrobe:   'rgb(192, 132, 252)',   // purple-400
  vehicle:    'rgb(248, 113, 113)',   // red-400
};
```

### Pattern 3: CSS-Only Tooltip
**What:** Using `position: relative` and a `::after` pseudo-element with `attr(data-tooltip)` for hover tooltips, or a simple `title` attribute for zero-effort tooltips.
**When to use:** When tooltip content is static text and accessibility requirements are basic.
**Example:**
```css
/* In index.css or as Tailwind @layer component */
.element-highlight {
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
  cursor: pointer;
  position: relative;
  transition: background-color 150ms ease;
}
.element-highlight:hover {
  background-color: hsl(var(--muted) / 0.3);
  border-radius: 2px;
}

/* Category underline colors */
.element-highlight--character { text-decoration-color: rgb(251, 191, 36); }
.element-highlight--location  { text-decoration-color: rgb(96, 165, 250); }
.element-highlight--prop      { text-decoration-color: rgb(74, 222, 128); }
.element-highlight--wardrobe  { text-decoration-color: rgb(192, 132, 252); }
.element-highlight--vehicle   { text-decoration-color: rgb(248, 113, 113); }
```

### Anti-Patterns to Avoid
- **dangerouslySetInnerHTML for highlighting:** Breaks React event handling, creates XSS vulnerabilities, and prevents the SelectionBar from working properly.
- **DOM manipulation outside React:** Using `document.querySelectorAll` to find text nodes and wrap them. This fights React's reconciliation and causes bugs on re-render.
- **Re-computing segments on every render:** The `buildHighlightSegments` function should be memoized with `useMemo` keyed on `[text, elements]`.
- **Highlighting inside the `<pre>` tag directly:** Instead, replace the `<pre>` content rendering with the segmented component. The `<pre>` wrapper remains, but its children are now React elements.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip on hover | Custom floating div with position calc | HTML `title` attribute or Radix Tooltip | Native `title` is zero-effort; Radix handles edge cases (viewport clipping, accessibility) |
| Text matching with word boundaries | Character-by-character string scanning | JavaScript `RegExp` with `\b` word boundaries | RegExp is well-tested, handles Unicode, and is ~10x faster than manual scanning |
| Navigation to detail page | Custom link wrapper | `useNavigate` + `ROUTES.ELEMENT_DETAIL()` | Already used in ElementCard.tsx -- proven pattern |

**Key insight:** The entire feature is achievable with zero new dependencies. The existing API returns all elements needed, the existing route handles detail page navigation, and native browser features handle tooltips. The only new code is the text-segmentation utility and a thin wrapper component.

## Common Pitfalls

### Pitfall 1: Partial Word Matches
**What goes wrong:** Highlighting "arm" inside "farmer", "Art" inside "Arthur", "an" inside "Manhattan".
**Why it happens:** Naive `String.includes()` or regex without word boundaries.
**How to avoid:** Use `\b` word boundaries in the regex. For names that start/end with special characters, escape them with a regex escape function.
**Warning signs:** Short element names (2-3 chars) getting spurious highlights throughout the script.

### Pitfall 2: Overlapping Matches
**What goes wrong:** Element "John Smith" and element "John" both exist. The regex finds "John" inside "John Smith", creating nested or duplicate highlights.
**How to avoid:** Sort elements by name length descending before building the regex alternation. The regex engine will try longer matches first. Since JavaScript regex alternation is ordered (left-to-right), `John Smith|John` will match "John Smith" as a whole before trying just "John".
**Warning signs:** Double-underlined text, duplicate tooltips.

### Pitfall 3: Regex Special Characters in Element Names
**What goes wrong:** An element named "Mr. Smith" or "O'Brien" causes regex syntax errors because `.` and `'` are regex metacharacters.
**Why it happens:** Constructing a regex from user-supplied names without escaping.
**How to avoid:** Use a regex escape function: `name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')` before inserting into the pattern.
**Warning signs:** Uncaught SyntaxError in console, blank script view.

### Pitfall 4: Conflict with Text Selection for Shots
**What goes wrong:** Clicking a highlighted element also triggers the selection-based "Add Shot" flow, or vice versa.
**Why it happens:** The highlight `<span>` click and the document `selectionchange` event both fire.
**How to avoid:** Use `e.stopPropagation()` on highlight click. The SelectionBar already handles `mousedown` outside its bounds. The highlight click should clear any active selection via `window.getSelection()?.removeAllRanges()`.
**Warning signs:** SelectionBar appearing when clicking a highlight, or navigation happening when trying to select text.

### Pitfall 5: Performance with Large Scripts
**What goes wrong:** Re-computing segments on every render for a 100-page script with 200 elements causes visible lag.
**Why it happens:** Text segmentation is O(n*m) where n is text length and m is number of elements, and React re-renders the scene on any state change.
**How to avoid:** `useMemo` on the segments computation. The elements list changes rarely (only on breakdown extraction). The script text changes only when switching scenes. Both are stable across most renders.
**Warning signs:** Typing lag in other parts of the breakdown view, slow tab switching.

### Pitfall 6: Case Sensitivity Mismatch
**What goes wrong:** Script says "JOHN" (all-caps screenplay convention for character introductions) but element name is "John". Highlight doesn't match.
**Why it happens:** Case-sensitive matching.
**How to avoid:** Use the `i` flag on the regex: `/\b(John|Smith)\b/gi`. The displayed text remains as-is in the script; only matching is case-insensitive.
**Warning signs:** Character names in ALL CAPS (standard screenplay format) not getting highlighted.

## Code Examples

### Existing ScriptReadView Rendering (source: codebase inspection)
```tsx
// Current rendering in ScriptReadView.tsx lines 200-204:
<pre className="text-[13px] text-foreground/90 whitespace-pre-wrap break-words leading-relaxed font-mono">
  {sp.content}
</pre>

// This needs to become:
<pre className="text-[13px] text-foreground/90 whitespace-pre-wrap break-words leading-relaxed font-mono">
  <HighlightedScriptText
    text={sp.content}
    elements={allElements ?? []}
    projectId={projectId}
  />
</pre>
```

### Fetching All Elements (using existing API)
```tsx
// Add to ScriptReadView.tsx:
const { data: allElements } = useQuery({
  queryKey: QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId),
  queryFn: () => api.getBreakdownElements(projectId),
  enabled: !!projectId,
});
```

### Regex Escape Utility
```typescript
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
```

### Full Text Segmentation Function
```typescript
function buildHighlightSegments(
  text: string,
  elements: BreakdownElement[]
): TextSegment[] {
  if (!elements.length || !text) return [{ type: 'text', content: text }];

  // Sort by name length desc (longest match first)
  const sorted = [...elements]
    .filter(e => e.name.trim().length > 0 && !e.is_deleted)
    .sort((a, b) => b.name.length - a.name.length);

  if (!sorted.length) return [{ type: 'text', content: text }];

  // Build name-to-element lookup (case-insensitive)
  const lookup = new Map<string, BreakdownElement>();
  for (const el of sorted) {
    lookup.set(el.name.toLowerCase(), el);
  }

  // Build regex alternation
  const pattern = sorted.map(e => escapeRegex(e.name)).join('|');
  const regex = new RegExp(`\\b(${pattern})\\b`, 'gi');

  const segments: TextSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    // Add plain text before match
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }

    const matchedText = match[0];
    const element = lookup.get(matchedText.toLowerCase());

    if (element) {
      segments.push({
        type: 'highlight',
        content: matchedText,
        match: {
          elementId: element.id,
          elementName: element.name,
          category: element.category,
        },
      });
    } else {
      segments.push({ type: 'text', content: matchedText });
    }

    lastIndex = regex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) });
  }

  return segments;
}
```

### Element Highlight Span Component
```tsx
function ElementHighlightSpan({
  match,
  content,
  projectId,
}: {
  match: ElementMatch;
  content: string;
  projectId: string;
}) {
  const navigate = useNavigate();
  const categoryLabel = BREAKDOWN_CATEGORIES.find(
    c => c.value === match.category
  )?.label ?? match.category;

  return (
    <span
      className={`element-highlight element-highlight--${match.category}`}
      title={`${match.elementName} - ${categoryLabel}`}
      onClick={(e) => {
        e.stopPropagation();
        window.getSelection()?.removeAllRanges();
        navigate(ROUTES.ELEMENT_DETAIL(projectId, match.elementId));
      }}
    >
      {content}
    </span>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DOM text node walking (mark.js) | React component-level text segmentation | React 16+ (2018) | No DOM fighting, better perf, type-safe |
| title attribute tooltips | Radix Tooltip or CSS `::after` | 2023+ | Better positioning, accessible; `title` still fine for simple cases |
| Regex alternation (ordered) | Same, still the standard | Always | JS regex alternation is ordered/greedy by default, perfect for longest-match-first |

**Deprecated/outdated:**
- `mark.js` / `highlight.js` for DOM-based text highlighting: These fight with React's virtual DOM. Only use in non-React contexts.

## Open Questions

1. **Should highlights be toggleable?**
   - What we know: The success criteria don't mention an on/off toggle for highlights.
   - What's unclear: Users may find highlighting distracting when reading the script. A toggle could help.
   - Recommendation: Defer to a future UX improvement phase. Implement highlights as always-on for now; adding a toggle later is trivial (one boolean state + conditional rendering).

2. **Should the tooltip show a description excerpt or just name+category?**
   - What we know: Success criteria say "tooltip with the element name and category."
   - What's unclear: Whether including the element description (first ~50 chars) would be more useful.
   - Recommendation: Stick to name + category as specified. Adding description later is a one-line change.

3. **Word boundary behavior for multi-word names**
   - What we know: `\b` works well for single-word and multi-word names in English text.
   - What's unclear: Edge cases with screenplay formatting (e.g., `JOHN SMITH (CONT'D)` -- will `\b` match "JOHN SMITH" correctly before the parenthetical?).
   - Recommendation: `\b` handles this correctly since the space between words is not a boundary issue, and `(` is a non-word character that creates a boundary after "SMITH". Test with real screenplay content to confirm.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x (backend); no frontend test framework configured |
| Config file | backend: pytest.ini (or pyproject.toml); frontend: none |
| Quick run command | `cd backend && python -m pytest app/tests/test_breakdown_api.py -x -q` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEL-01 | Highlighted spans appear for element names in script text | manual | Open breakdown mode, view script panel, verify colored underlines on element names | N/A (frontend visual) |
| SEL-01 | Tooltip shows element name and category on hover | manual | Hover over highlighted text, verify tooltip content | N/A (frontend visual) |
| SEL-01 | Click navigates to element detail page | manual | Click highlighted text, verify URL changes to /projects/:id/breakdown/elements/:elementId | N/A (frontend visual) |
| SEL-01 | Text segmentation produces correct segments | unit | Could add a vitest/jest unit test for `buildHighlightSegments` pure function | No existing frontend test infra |

### Sampling Rate
- **Per task commit:** Visual inspection in browser (no automated frontend tests)
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x -q` (regression check -- no backend changes expected)
- **Phase gate:** Manual browser verification of all 3 success criteria

### Wave 0 Gaps
- No backend changes expected, so no new backend tests needed.
- Frontend has no test framework; the `buildHighlightSegments` pure function *could* be unit tested if vitest/jest were set up, but this is out of scope for this phase.
- All verification is manual (visual browser testing).

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `ScriptReadView.tsx` (219 lines) -- current rendering pattern, selection handling
- Codebase inspection: `ElementCard.tsx` (294 lines) -- navigation pattern using `ROUTES.ELEMENT_DETAIL`
- Codebase inspection: `ElementDetailPage.tsx` (124 lines) -- target page, confirmed route works
- Codebase inspection: `breakdown.py` (439 lines) -- `list_elements` endpoint returns all elements with category/name/id
- Codebase inspection: `constants.ts` -- `BREAKDOWN_CATEGORIES`, `ROUTES`, `QUERY_KEYS`
- Codebase inspection: `api.tsx` -- `getBreakdownElements(projectId)` method exists
- Codebase inspection: `index.css` -- breakdown-mode CSS variables, existing utility classes
- Codebase inspection: `types/index.ts` -- `BreakdownElement`, `BreakdownCategory` types

### Secondary (MEDIUM confidence)
- MDN Web Docs: JavaScript RegExp word boundaries, `String.prototype.replace`, `RegExp.prototype.exec` -- standard, stable APIs
- Tailwind CSS: `text-decoration-color`, `text-underline-offset` utility support

### Tertiary (LOW confidence)
- None -- all findings are from direct codebase inspection and standard web APIs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed; all existing
- Architecture: HIGH -- pattern is straightforward React text segmentation; verified ScriptReadView structure
- Pitfalls: HIGH -- pitfalls are well-known text-matching edge cases; verified against actual codebase patterns

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain; no dependencies changing)
