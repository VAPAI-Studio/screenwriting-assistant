# Phase 38: Show Management UI - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the UI layer for Show management: a split home page (Shows vs Films), a show detail page with editable series bible, and an empty episode list placeholder. No episode CRUD yet — that's Phase 40.

</domain>

<decisions>
## Implementation Decisions

### Home Page Layout
- Split home page into two sections: "Shows" (TV series) and "Films" (standalone projects)
- Shows section: card grid showing title, description, episode count (0 until Phase 39)
- Films section: existing ProjectCard grid (unchanged behavior)
- "New Show" button in Shows section, existing "New Project" in Films section
- Empty states for both sections when no items exist

### Show Detail Page
- Route: /shows/:showId
- Shows: title, description (editable inline or via modal), series bible with 4 sections
- Bible sections rendered as expandable textareas (Characters, World/Setting, Season Arc, Tone & Style)
- Episode duration selector: dropdown with presets (10, 22, 44, 60 min) + custom integer input
- Auto-save bible on blur (debounced PUT /api/shows/{id}/bible)
- Episode list area at bottom — empty placeholder "Episodes coming soon" for now

### Navigation & Routing
- /shows/:showId — new show detail page
- Header navigation links to home (/) which now shows both Shows and Films
- Back button on show detail navigates to home

### Styling
- Follows existing Tailwind + HSL CSS variable theming
- Show cards styled similarly to ProjectCard but with TV-specific metadata (episode count)
- Bible sections use subtle card/panel styling consistent with existing Editor panels

### Claude's Discretion
- Exact card layout dimensions and spacing follow existing ProjectCard patterns
- Error handling follows existing patterns (same as ProjectList)
- Loading states follow existing Loader2 spinner pattern

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ProjectCard.tsx` — card component to adapt for ShowCard
- `CreateProjectModal.tsx` — modal pattern to adapt for CreateShowModal
- `ProjectList.tsx` — home page to extend with Shows section
- `Button`, `Input`, `Modal`, `Card` from `components/UI/`
- `useQuery`, `useMutation` from React Query — same pattern throughout
- `api.tsx` — fetch wrapper with Bearer token auth to extend with show methods

### Established Patterns
- React Query with `queryKey: [QUERY_KEYS.X]` and 5-min stale time
- `useMutation` + `queryClient.invalidateQueries` for write ops
- Tailwind classes with `animate-fade-in`, `animate-fade-up` for transitions
- `ProtectedRoute` wrapper for all authenticated routes

### Integration Points
- `App.tsx` — add `/shows/:showId` route
- `frontend/src/lib/api.tsx` — add `getShows`, `createShow`, `updateShow`, `deleteShow`, `getBible`, `updateBible`
- `frontend/src/types/index.ts` — add `Show`, `BibleResponse`, `BibleUpdate` types
- `frontend/src/lib/constants.ts` — add QUERY_KEYS for shows and bible

</code_context>

<specifics>
## Specific Ideas

- Bible sections are collapsible/expandable textareas, not a separate page
- Auto-save on blur with a subtle "Saved" toast or indicator
- Episode duration uses a `<select>` with 10/22/44/60 min options plus "Custom..." that reveals a number input

</specifics>

<deferred>
## Deferred Ideas

- Show cover image / artwork — deferred to future phase
- Show genre/tags — not in requirements
- Episode count badge updates in real time — Phase 40 wires this

</deferred>
