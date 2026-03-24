# Phase 40: Episode Management UI - Research

**Researched:** 2026-03-24
**Domain:** React CRUD UI + FastAPI list endpoint for episodes within shows
**Confidence:** HIGH

## Summary

This phase replaces the "Episodes coming soon" placeholder in the ShowDetail page with a functional episode list. The work is narrowly scoped: one new backend endpoint (GET episodes), one new frontend API function, one new component (EpisodeList with embedded create dialog), and updates to ShowDetail.tsx to wire it all together. The entire pattern is already established in the codebase -- the ProjectList/ShowCard/CreateShowModal patterns provide exact templates to follow.

The backend create-episode endpoint already exists (POST /api/shows/{show_id}/episodes in shows.py). Delete-episode reuses the existing DELETE /api/projects/{id} endpoint since episodes ARE projects. The only backend addition needed is the GET list endpoint. On the frontend, no new types are needed -- episodes return the standard `Project` type with `show_id` and `episode_number` populated.

**Primary recommendation:** Follow the exact CreateShowModal + ShowCard patterns for the create dialog and episode row styling. Keep episode list items as simple rows (not full cards) per CONTEXT.md decisions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Replace the "Episodes coming soon" placeholder in ShowDetail.tsx with a real EpisodeList component
- Episodes ordered by episode_number ascending
- Each episode row shows: episode number (E1, E2...), title, framework badge
- Clicking a row navigates to /projects/{episode_project_id} (existing Editor route)
- "New Episode" button in the episode list header
- Dialog fields: Title (required text input), Framework (select, defaults to THREE_ACT)
- Episode number auto-calculated by backend (show it as "Episode N" preview in dialog)
- On submit: POST /api/shows/{show_id}/episodes, invalidate episode list query
- Follow existing CreateProjectModal pattern
- Each episode row has a delete button (trash icon)
- Confirm with window.confirm() -- same pattern as existing project delete
- DELETE /api/projects/{episode_id} (episodes are projects -- existing endpoint works)
- On success: invalidate episode list query
- Add GET /api/shows/{show_id}/episodes to shows.py
- Returns episodes ordered by episode_number
- Same auth pattern (current_user ownership check on show)
- Add getEpisodes(showId) to api.tsx
- Add QUERY_KEYS.EPISODES to constants.ts
- No new types needed (episodes return standard Project type)
- Episode rows styled as subtle list items (not full cards)
- Framework badge reuses existing framework color pattern from ProjectCard
- Empty state: "No episodes yet -- create your first episode"
- Episode number displayed as "Ep. 1", "Ep. 2" prefix
- The create dialog shows the next episode number as a preview ("Will be Episode 3")

### Claude's Discretion
- Loading/error states follow existing React Query patterns
- Row hover states follow existing table/list patterns in the codebase

### Deferred Ideas (OUT OF SCOPE)
- Episode reordering via drag -- future phase
- Episode status indicators -- not in requirements
- Bulk delete -- not in requirements
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EPIS-03 | User can view, open, and delete episodes from the show page | Full stack: GET endpoint for listing, EpisodeList component with navigation, delete via existing project endpoint |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.x | UI framework | Already in project |
| @tanstack/react-query | 5.x | Server state management | Already in project, standard for data fetching |
| react-router-dom | 6.x | Client routing | Already in project, useNavigate for episode navigation |
| @radix-ui/react-dialog | latest | Accessible modal dialog | Already used in CreateShowModal and CreateProjectModal |
| lucide-react | latest | Icons (Trash2, Plus, Film) | Already used throughout codebase |
| FastAPI | latest | Backend framework | Already in project |
| SQLAlchemy | latest | ORM for database queries | Already in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tailwind CSS | 3.x | Styling | All UI styling, already configured |

No new packages need to be installed for this phase.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/components/Shows/
  ShowDetail.tsx          # MODIFY: replace placeholder with EpisodeList
  EpisodeList.tsx         # NEW: episode listing + create/delete
  CreateEpisodeModal.tsx  # NEW: modal for creating episodes
  BibleEditor.tsx         # existing, no changes
  ShowCard.tsx            # existing, no changes

backend/app/api/endpoints/
  shows.py               # MODIFY: add GET /{show_id}/episodes endpoint

frontend/src/lib/
  api.tsx                 # MODIFY: add getEpisodes, createEpisode functions
  constants.ts            # MODIFY: add QUERY_KEYS.EPISODES
```

### Pattern 1: Query Key for Episode List
**What:** Add EPISODES query key following the existing pattern
**When to use:** Any query fetching episodes for a show
**Example:**
```typescript
// In constants.ts, add to QUERY_KEYS:
EPISODES: (showId: string) => ['episodes', showId] as const,
```

### Pattern 2: API Function Pattern
**What:** Follow the existing fetch wrapper pattern from api.tsx
**When to use:** Adding getEpisodes and createEpisode to api.tsx
**Example:**
```typescript
// Source: existing api.tsx pattern (getShows, createShow)
async getEpisodes(showId: string): Promise<Project[]> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/shows/${showId}/episodes`,
    { headers: getHeaders() }
  );
  if (!response.ok) throw new Error('Failed to fetch episodes');
  return response.json();
},

async createEpisode(showId: string, data: { title: string; framework?: string }): Promise<Project> {
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/shows/${showId}/episodes`,
    {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    }
  );
  if (!response.ok) throw new Error('Failed to create episode');
  return response.json();
},
```

### Pattern 3: React Query CRUD Pattern
**What:** useQuery for list, useMutation for create/delete with invalidation
**When to use:** EpisodeList component
**Example:**
```typescript
// Source: existing ProjectList.tsx and CreateShowModal.tsx patterns
const { data: episodes = [], isLoading, isError } = useQuery({
  queryKey: QUERY_KEYS.EPISODES(showId),
  queryFn: () => api.getEpisodes(showId),
});

const createMutation = useMutation({
  mutationFn: (data: { title: string; framework: string }) =>
    api.createEpisode(showId, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EPISODES(showId) });
    // close dialog, reset form
  },
});

const deleteMutation = useMutation({
  mutationFn: (id: string) => api.deleteProject(id),  // reuse existing!
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EPISODES(showId) });
  },
});
```

### Pattern 4: Delete Confirmation Pattern
**What:** window.confirm() before delete, matching existing codebase pattern
**When to use:** Episode delete button click
**Example:**
```typescript
// Source: ProjectList.tsx handleDelete and handleDeleteShow
const handleDeleteEpisode = (id: string) => {
  if (window.confirm('Delete this episode? This cannot be undone.')) {
    deleteMutation.mutate(id);
  }
};
```

### Pattern 5: Radix Dialog for Create Modal
**What:** Controlled Dialog.Root with form, following CreateShowModal pattern
**When to use:** CreateEpisodeModal component
**Example:**
```typescript
// Source: CreateShowModal.tsx structure
<Dialog.Root open={open} onOpenChange={onOpenChange}>
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm ..." />
    <Dialog.Content className="fixed left-1/2 top-1/2 ... rounded-xl bg-card ...">
      <Dialog.Title>New Episode</Dialog.Title>
      <form onSubmit={handleSubmit}>
        {/* Title input, Framework select, preview text */}
      </form>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

### Pattern 6: Backend List Endpoint
**What:** GET endpoint with ownership check and ordered query
**When to use:** GET /api/shows/{show_id}/episodes
**Example:**
```python
# Source: existing shows.py patterns (list_shows, get_show)
@router.get("/{show_id}/episodes", response_model=List[schemas.Project])
async def list_episodes(
    show_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    show = (
        db.query(database.Show)
        .filter(database.Show.id == str(show_id),
                database.Show.owner_id == str(current_user.id))
        .first()
    )
    if not show:
        raise NotFoundException(resource="Show", identifier=str(show_id))
    return (
        db.query(database.Project)
        .filter(database.Project.show_id == str(show_id))
        .order_by(database.Project.episode_number.asc())
        .all()
    )
```

### Pattern 7: Framework Badge Display
**What:** Reuse FRAMEWORK_LABELS for display, existing badge color pattern from ProjectCard
**When to use:** Episode row framework badge
**Example:**
```typescript
// Source: ProjectCard.tsx line 53
import { FRAMEWORK_LABELS } from '../../lib/section-config';

<span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
  {FRAMEWORK_LABELS[episode.framework]}
</span>
```

### Anti-Patterns to Avoid
- **Creating a new Episode type:** Episodes ARE projects. Reuse the existing `Project` type -- it already has `show_id` and `episode_number` fields.
- **Adding episode count to ShowCard in this phase:** The ShowCard currently hardcodes "0 episodes". While tempting to fix, the CONTEXT.md does not mention this -- it is a future concern.
- **Using a separate route for episode editor:** Episodes navigate to `/projects/{id}` using the existing Editor route. Do NOT create a `/shows/{showId}/episodes/{episodeId}` route.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal dialogs | Custom modal with portals | @radix-ui/react-dialog | Accessibility, focus trapping, animation -- already used in codebase |
| Server state | useState + fetch | useQuery/useMutation from react-query | Caching, invalidation, loading states -- project convention |
| Delete confirmation | Custom confirmation modal | window.confirm() | Matches existing codebase pattern exactly (ProjectList.tsx) |
| Framework display labels | Inline strings | FRAMEWORK_LABELS from section-config.ts | Single source of truth, already defined |
| Episode number calculation | Frontend calculation | Backend auto-calculates via MAX+1 | Race condition safe, already implemented in create_episode endpoint |

**Key insight:** This phase is almost entirely pattern reuse. Every single UI interaction pattern (list, create modal, delete confirm, navigation) already exists in the codebase and should be copied, not reimagined.

## Common Pitfalls

### Pitfall 1: Query Key Collision
**What goes wrong:** Using a generic key like `['episodes']` without the showId causes cache collisions between different shows.
**Why it happens:** Forgetting to scope the query key.
**How to avoid:** Always use `QUERY_KEYS.EPISODES(showId)` which returns `['episodes', showId]`.
**Warning signs:** Episodes from one show appearing on another show's detail page.

### Pitfall 2: Forgetting to Invalidate on Delete
**What goes wrong:** After deleting an episode, the list still shows it until page refresh.
**Why it happens:** Delete uses `api.deleteProject(id)` which invalidates `QUERY_KEYS.PROJECTS` but NOT `QUERY_KEYS.EPISODES`.
**How to avoid:** Explicitly invalidate `QUERY_KEYS.EPISODES(showId)` in the delete mutation's onSuccess.
**Warning signs:** Stale episode appearing in list after delete.

### Pitfall 3: str() Cast on UUID in Backend Query
**What goes wrong:** SQLite (used in tests) stores UUIDs as strings, PostgreSQL as native UUID. Direct comparison fails in one environment.
**Why it happens:** Mismatch between UUID types across databases.
**How to avoid:** Always use `str(show_id)` when filtering, matching the pattern already used in shows.py.
**Warning signs:** Tests pass but production queries return empty results (or vice versa).

### Pitfall 4: Episode Number Preview Calculation
**What goes wrong:** The "Will be Episode N" preview shows the wrong number because it uses stale data.
**Why it happens:** Calculating next episode number from the cached query data while another create is in flight.
**How to avoid:** Calculate from the current episodes list length + 1. For the preview, this is acceptable -- the backend does the authoritative auto-increment.
**Warning signs:** Preview says "Episode 3" but the backend creates Episode 4.

### Pitfall 5: Missing Sections in List Response
**What goes wrong:** The GET episodes endpoint returns projects with their full sections array, causing a large payload.
**Why it happens:** SQLAlchemy eager-loads sections by default via the relationship.
**How to avoid:** The list endpoint should still return full Project objects (to match the schema). The sections array is small (6 items). If performance becomes an issue, a future optimization could use a leaner response schema, but this is not needed for MVP.
**Warning signs:** Slow load times on the episode list -- unlikely with < 50 episodes per show.

## Code Examples

### Episode List Component Structure
```typescript
// Source: derived from existing ProjectList.tsx and ShowDetail.tsx patterns

interface EpisodeListProps {
  showId: string;
}

export function EpisodeList({ showId }: EpisodeListProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: episodes = [], isLoading } = useQuery({
    queryKey: QUERY_KEYS.EPISODES(showId),
    queryFn: () => api.getEpisodes(showId),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EPISODES(showId) });
    },
  });

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this episode? This cannot be undone.')) {
      deleteMutation.mutate(id);
    }
  };

  // ... render list with header, create button, episode rows
}
```

### Create Episode Modal Structure
```typescript
// Source: derived from CreateShowModal.tsx pattern

interface CreateEpisodeModalProps {
  showId: string;
  nextEpisodeNumber: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateEpisodeModal({ showId, nextEpisodeNumber, open, onOpenChange }: CreateEpisodeModalProps) {
  const [title, setTitle] = useState('');
  const [framework, setFramework] = useState<Framework>(Framework.THREE_ACT);
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: { title: string; framework: string }) =>
      api.createEpisode(showId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EPISODES(showId) });
      onOpenChange(false);
      setTitle('');
      setFramework(Framework.THREE_ACT);
    },
  });

  // Dialog with title input, framework select, "Will be Episode N" preview
}
```

### ShowDetail Integration
```typescript
// In ShowDetail.tsx, replace the placeholder section:
{/* Episode List */}
<section>
  <h2 className="text-xl font-semibold text-foreground mb-4">Episodes</h2>
  <EpisodeList showId={showId} />
</section>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Placeholder text "Episodes coming soon" | Functional EpisodeList component | Phase 40 | Users can now CRUD episodes from show page |
| ShowCard hardcoded "0 episodes" | Remains hardcoded (not in scope) | Future phase | ShowCard still shows "0 episodes" |

**Deprecated/outdated:**
- None -- this phase uses well-established patterns already in the codebase.

## Open Questions

1. **ShowCard episode count**
   - What we know: ShowCard.tsx hardcodes "0 episodes" badge
   - What's unclear: Whether to update ShowCard to show actual count when episodes are fetched
   - Recommendation: Out of scope for EPIS-03. Could be a quick follow-up.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), no frontend test runner configured |
| Config file | backend/app/tests/conftest.py |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EPIS-03a | GET /api/shows/{id}/episodes returns episodes ordered by number | unit (API) | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_list_episodes -x` | No -- Wave 0 |
| EPIS-03b | GET /api/shows/{id}/episodes returns empty list for new show | unit (API) | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_list_episodes_empty -x` | No -- Wave 0 |
| EPIS-03c | GET /api/shows/{id}/episodes returns 404 for non-existent show | unit (API) | `pytest app/tests/test_shows_api.py::TestEpisodesAPI::test_list_episodes_not_found -x` | No -- Wave 0 |
| EPIS-03d | DELETE /api/projects/{id} removes episode (existing endpoint) | unit (API) | `pytest app/tests/test_api.py::TestProjectsAPI::test_delete_project -x` | Yes |
| EPIS-03e | Episode list UI renders, click navigates to editor | manual | Manual browser test | N/A |
| EPIS-03f | Create episode dialog creates episode and refreshes list | manual | Manual browser test | N/A |
| EPIS-03g | Delete episode with confirm removes from list | manual | Manual browser test | N/A |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -x`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `test_list_episodes` in `app/tests/test_shows_api.py::TestEpisodesAPI` -- covers EPIS-03a
- [ ] `test_list_episodes_empty` in `app/tests/test_shows_api.py::TestEpisodesAPI` -- covers EPIS-03b
- [ ] `test_list_episodes_not_found` in `app/tests/test_shows_api.py::TestEpisodesAPI` -- covers EPIS-03c

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `frontend/src/components/Shows/ShowDetail.tsx` -- current placeholder to replace
- Codebase inspection: `frontend/src/components/Shows/CreateShowModal.tsx` -- pattern for create dialog
- Codebase inspection: `frontend/src/components/Projects/ProjectCard.tsx` -- framework badge pattern
- Codebase inspection: `frontend/src/components/Projects/ProjectList.tsx` -- delete confirmation pattern
- Codebase inspection: `backend/app/api/endpoints/shows.py` -- existing create_episode endpoint, auth patterns
- Codebase inspection: `frontend/src/lib/api.tsx` -- fetch wrapper pattern for API calls
- Codebase inspection: `frontend/src/lib/constants.ts` -- QUERY_KEYS pattern
- Codebase inspection: `frontend/src/types/index.ts` -- Project type already includes show_id, episode_number
- Codebase inspection: `backend/app/models/schemas.py` -- Project schema, EpisodeCreate schema
- Codebase inspection: `backend/app/models/database.py` -- Project model with show_id FK

### Secondary (MEDIUM confidence)
- None needed -- all patterns are directly observable in the codebase

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- exact patterns exist in codebase (CreateShowModal, ProjectList, shows.py)
- Pitfalls: HIGH -- derived from direct codebase observation (UUID str casting, query key scoping)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependencies or fast-moving libraries)
