# Phase 18: Two-Mode UI Shell - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Project-level mode toggle in the header switching between "Screenwriting" and "Script Breakdown" modes. Breakdown mode renders a new 3-panel layout skeleton at `/projects/:id/breakdown`. The existing BreakdownPage.tsx is replaced by this new layout. Visual identities for both modes are established via CSS variable scoping.

</domain>

<decisions>
## Implementation Decisions

### Toggle Placement
- Lives in the main header, contextual — appears only when the user is inside a project route
- Visual form: dropdown button showing current mode name + caret icon ("Screenwriting ▾" / "Script Breakdown ▾")
- URL-based mode routing: switching to Breakdown navigates to `/projects/:id/breakdown`; switching back to Screenwriting navigates to the project's default workspace route
- App-level nav links (Projects, Books, Snippets) remain in the header alongside the mode dropdown

### Visual Identity
- Breakdown mode palette: cool slate / blue-grey — dark backgrounds with blue-grey tones, accent shifts to steel blue or indigo
- Distinctness level: distinct but harmonious — same general darkness/contrast and depth; shared typography, spacing, and component shapes; accent color clearly different but both modes feel like the same product
- The entire chrome (including header) adopts the breakdown palette when in Breakdown mode
- Mode transitions use smooth CSS transitions (200–300ms) on color variables

### Old BreakdownPage
- Phase 18 replaces `BreakdownPage.tsx` — the old v2.0 breakdown elements page (Characters, Locations, Props tabs) is removed from the `/breakdown` route
- The old breakdown element content (category tabs) will be re-exposed in the Assets panel in Phase 23; it is temporarily inaccessible via UI between Phase 18 and Phase 23
- New breakdown layout lives at the same `/projects/:id/breakdown` URL

### Panel Layout
- 3-panel skeleton: left (script/assets), center (shotlist), right (chat)
- Default widths: 25% / 50% / 25%
- Resizable via drag handles between panels; resize state persists in localStorage
- Each panel is collapsible via a collapse button; collapsed state persists in localStorage
- Placeholder content in each panel: labeled empty states with icon + description (e.g., left panel: "Script View — available in Phase 21"; center: "Shotlist — available in Phase 20"; right: "AI Chat — available in Phase 24")
- Minimum panel widths: Claude's discretion (reasonable for readability)

### Claude's Discretion
- Exact CSS variable values for the breakdown blue-grey palette (must look good, not just "different")
- Specific min-width constraints for resizable panels
- Collapse icon/button placement within each panel header
- Exact localStorage keys for panel state

</decisions>

<specifics>
## Specific Ideas

- Transition feel: like switching from "writer mode" to "director mode" — the chrome visibly shifts so user knows they're in a different context
- Header should feel transformed in breakdown mode, not just the page content below
- The dropdown replaces the concept of an active route indicator for breakdown — current mode is self-labeling

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Header.tsx` (frontend/src/components/Layout/Header.tsx): existing header with app nav links — mode dropdown inserts here, conditionally rendered based on route
- `BreakdownPage.tsx` (frontend/src/components/Breakdown/BreakdownPage.tsx): replaced by new BreakdownLayout; content preserved for reference when building Phase 23 Assets panel
- `StalenessBar.tsx` (frontend/src/components/Breakdown/StalenessBar.tsx): reusable in breakdown layout for Phase 25
- `index.css`: existing CSS variable system (HSL values, `:root` scope) — breakdown mode adds a `.breakdown-mode` class or `data-mode="breakdown"` attribute on `<html>` or `<body>` to scope overridden variables
- `useLocation()` from react-router-dom: already used in Header — use to detect project context and determine which mode is active for the dropdown

### Established Patterns
- CSS variables on `:root` (HSL format): `--background`, `--foreground`, `--accent`, `--primary`, `--ring`, etc. — override the same variables under a mode selector class
- `useLocation()` for active route detection — same pattern for detecting project context in header
- `localStorage` with `STORAGE_KEYS` constants (`frontend/src/lib/constants.ts`) — add panel state keys following same pattern
- React Router `useNavigate()` for programmatic navigation from the dropdown

### Integration Points
- `App.tsx`: `/projects/:id/breakdown` route points to old `BreakdownPage` — Phase 18 replaces import with new `BreakdownLayout` component
- `Header.tsx`: mode dropdown renders conditionally when path matches `/projects/:id` pattern
- `index.css`: breakdown mode CSS variable overrides live here alongside the existing `:root` block
- `frontend/src/lib/constants.ts` (`STORAGE_KEYS`): add new keys for panel widths and collapsed state

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-two-mode-ui-shell*
*Context gathered: 2026-03-19*
