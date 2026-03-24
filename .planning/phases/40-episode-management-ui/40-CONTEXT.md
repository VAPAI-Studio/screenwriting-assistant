# Phase 40: Episode Management UI - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase wires the episode list into the show detail page: display episodes ordered by number, "New Episode" button with create dialog, clicking an episode navigates to /projects/{id}, delete with confirmation. Also fetches episodes from the new GET /api/shows/{show_id}/episodes endpoint (to be added in this phase — the backend needs one endpoint for listing).

</domain>

<decisions>
## Implementation Decisions

### Episode List on Show Detail Page
- Replace the "Episodes coming soon" placeholder in ShowDetail.tsx with a real EpisodeList component
- Episodes ordered by episode_number ascending
- Each episode row shows: episode number (E1, E2...), title, framework badge
- Clicking a row navigates to /projects/{episode_project_id} (existing Editor route)

### Create Episode Dialog
- "New Episode" button in the episode list header
- Dialog fields: Title (required text input), Framework (select, defaults to THREE_ACT)
- Episode number auto-calculated by backend (show it as "Episode N" preview in dialog)
- On submit: POST /api/shows/{show_id}/episodes, invalidate episode list query
- Follow existing CreateProjectModal pattern

### Delete Episode
- Each episode row has a delete button (trash icon)
- Confirm with window.confirm() — same pattern as existing project delete
- DELETE /api/projects/{episode_id} (episodes are projects — existing endpoint works)
- On success: invalidate episode list query

### Backend: List Episodes Endpoint
- Add GET /api/shows/{show_id}/episodes to shows.py
- Returns episodes ordered by episode_number
- Same auth pattern (current_user ownership check on show)

### API & Types
- Add `getEpisodes(showId)` to api.tsx
- Add QUERY_KEYS.EPISODES to constants.ts
- No new types needed (episodes return standard Project type)

### Styling
- Episode rows styled as subtle list items (not full cards)
- Framework badge reuses existing framework color pattern from ProjectCard
- Empty state: "No episodes yet — create your first episode"

### Claude's Discretion
- Loading/error states follow existing React Query patterns
- Row hover states follow existing table/list patterns in the codebase

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ShowDetail.tsx` — extend to replace placeholder with EpisodeList
- `CreateProjectModal.tsx` — adapt pattern for CreateEpisodeModal
- `ProjectCard.tsx` — adapt framework badge logic
- `api.tsx` — add getEpisodes, episodes already have createEpisode from Phase 38
- React Query patterns — same invalidation pattern

### Established Patterns
- `useMutation` + `queryClient.invalidateQueries` for create/delete
- `navigate(ROUTES.PROJECT(id))` for navigation
- `window.confirm()` for delete confirmation
- `useQuery({ queryKey: [QUERY_KEYS.X, id], queryFn: () => api.getX(id) })`

### Integration Points
- `ShowDetail.tsx` — replace "Episodes coming soon" placeholder
- `backend/app/api/endpoints/shows.py` — add GET episodes endpoint
- `frontend/src/lib/api.tsx` — add getEpisodes
- `frontend/src/lib/constants.ts` — add QUERY_KEYS.EPISODES

</code_context>

<specifics>
## Specific Ideas

- Episode number displayed as "Ep. 1", "Ep. 2" prefix
- The create dialog shows the next episode number as a preview ("Will be Episode 3")

</specifics>

<deferred>
## Deferred Ideas

- Episode reordering via drag — future phase
- Episode status indicators — not in requirements
- Bulk delete — not in requirements

</deferred>
