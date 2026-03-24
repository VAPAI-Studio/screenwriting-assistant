# Phase 38: Show Management UI - Research

**Researched:** 2026-03-24
**Domain:** React frontend -- home page split, new page + route, CRUD UI, auto-save bible editor
**Confidence:** HIGH

## Summary

Phase 38 is a frontend-only phase. The backend is fully complete: Phase 36 delivered Show CRUD at `/api/shows` and Phase 37 added bible GET/PUT at `/api/shows/{id}/bible`. The frontend currently has zero show-related code -- no types, no API methods, no components, no routes. Everything must be built from scratch, but every pattern has a direct existing analog in the codebase.

The home page (`ProjectList.tsx`) must be split into two sections: "Shows" (TV series) and "Films" (standalone projects). A new `ShowDetail` page at `/shows/:showId` must render the show title/description, a four-section collapsible bible editor with auto-save on blur, an episode duration selector, and a placeholder episode list area. A `CreateShowModal` is needed, following the exact pattern of `CreateProjectModal`.

**Primary recommendation:** Build this as two plan waves -- (1) data layer + home page split, (2) show detail page with bible editor. All code follows existing patterns exactly: React Query for data, Radix Dialog for modals, Tailwind for styling, lucide-react for icons.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Split home page into two sections: "Shows" (TV series) and "Films" (standalone projects)
- Shows section: card grid showing title, description, episode count (0 until Phase 39)
- Films section: existing ProjectCard grid (unchanged behavior)
- "New Show" button in Shows section, existing "New Project" in Films section
- Empty states for both sections when no items exist
- Show detail page route: /shows/:showId
- Shows: title, description (editable inline or via modal), series bible with 4 sections
- Bible sections rendered as expandable textareas (Characters, World/Setting, Season Arc, Tone & Style)
- Episode duration selector: dropdown with presets (10, 22, 44, 60 min) + custom integer input
- Auto-save bible on blur (debounced PUT /api/shows/{id}/bible)
- Episode list area at bottom -- empty placeholder "Episodes coming soon" for now
- Header navigation links to home (/) which now shows both Shows and Films
- Back button on show detail navigates to home
- Follows existing Tailwind + HSL CSS variable theming
- Bible sections use subtle card/panel styling consistent with existing Editor panels
- Bible sections are collapsible/expandable textareas, not a separate page
- Auto-save on blur with a subtle "Saved" toast or indicator
- Episode duration uses a `<select>` with 10/22/44/60 min options plus "Custom..." that reveals a number input

### Claude's Discretion
- Exact card layout dimensions and spacing follow existing ProjectCard patterns
- Error handling follows existing patterns (same as ProjectList)
- Loading states follow existing Loader2 spinner pattern

### Deferred Ideas (OUT OF SCOPE)
- Show cover image / artwork -- deferred to future phase
- Show genre/tags -- not in requirements
- Episode count badge updates in real time -- Phase 40 wires this
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SHOW-02 | Home page displays Shows and standalone Films as separate sections | ProjectList.tsx split pattern, two parallel useQuery calls, section headers with separate New buttons |
| SHOW-03 | User can open a show to view its series bible and episode list | New /shows/:showId route, ShowDetail component, useQuery for show + bible, four collapsible textarea sections |
| BIBL-01 | Each show has four bible sections: Characters, World/Setting, Season Arc, Tone & Style | Bible API returns all four fields; frontend renders as expandable panels with textareas |
| BIBL-02 | User can write and edit each bible section as freeform text | Textarea with onChange + auto-save on blur via useMutation calling PUT /api/shows/{id}/bible |
| BIBL-03 | Each show has a target episode duration setting (10, 22, 44, 60, or custom) | Select dropdown + conditional number input; persisted via same PUT /api/shows/{id}/bible endpoint |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^18.2.0 | UI framework | Project standard |
| react-router-dom | ^6.21.3 | Client routing for /shows/:showId | Already handles all routes |
| @tanstack/react-query | ^5.20.1 | Server state -- fetching shows, bible, mutations | Project-wide data layer |
| @radix-ui/react-dialog | ^1.0.5 | CreateShowModal | Same as CreateProjectModal |
| lucide-react | ^0.314.0 | Icons (Tv, Plus, ChevronDown, Loader2, ArrowLeft, Save) | Project icon library |
| tailwindcss | ^3.4.1 | Styling | Project standard |
| class-variance-authority | ^0.7.0 | Button variants | Used by Button.tsx |

### No New Dependencies Required
This phase uses only libraries already in `package.json`. No `npm install` needed.

## Architecture Patterns

### New Files to Create

```
frontend/src/
  types/index.ts              # ADD Show, BibleResponse, BibleUpdate interfaces
  lib/api.tsx                 # ADD getShows, getShow, createShow, updateShow, deleteShow, getBible, updateBible
  lib/constants.ts            # ADD QUERY_KEYS.SHOWS, QUERY_KEYS.SHOW, QUERY_KEYS.BIBLE, ROUTES.SHOW, ROUTES.SHOWS
  components/
    Projects/
      ProjectList.tsx         # MODIFY -- split into Shows section + Films section
    Shows/                    # NEW directory
      ShowCard.tsx            # Card component for show grid
      CreateShowModal.tsx     # Radix Dialog for creating shows
      ShowDetail.tsx          # Full show detail page (bible + episode placeholder)
      BibleEditor.tsx         # Four-section collapsible editor with auto-save
      EpisodeDurationPicker.tsx  # Select with preset + custom input
  App.tsx                     # ADD /shows/:showId route
```

### Pattern 1: Two-Query Home Page
**What:** ProjectList fetches both `api.getShows()` and `api.getProjects()` in parallel.
**When to use:** Always -- the home page needs both datasets.
**Example:**
```typescript
// Two independent queries in ProjectList
const { data: shows, isLoading: showsLoading } = useQuery({
  queryKey: [QUERY_KEYS.SHOWS],
  queryFn: api.getShows,
});

const { data: projects, isLoading: projectsLoading } = useQuery({
  queryKey: [QUERY_KEYS.PROJECTS],
  queryFn: api.getProjects,
});
```

### Pattern 2: Auto-Save on Blur with Debounce
**What:** Bible textarea saves on blur. The `useMutation` calls `PUT /api/shows/{id}/bible` with only the changed field.
**When to use:** For each of the four bible sections and the duration picker.
**Example:**
```typescript
const updateBibleMutation = useMutation({
  mutationFn: (data: Partial<BibleUpdate>) => api.updateBible(showId, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BIBLE(showId) });
    // Show brief "Saved" indicator
  },
});

const handleBlur = (field: keyof BibleUpdate, value: string) => {
  updateBibleMutation.mutate({ [field]: value });
};
```

### Pattern 3: Collapsible Section Panel
**What:** Each bible section is a collapsible panel with header + textarea.
**When to use:** Bible editor sections.
**Example:**
```typescript
const [expanded, setExpanded] = useState<Record<string, boolean>>({
  bible_characters: true,
  bible_world_setting: false,
  bible_season_arc: false,
  bible_tone_style: false,
});
```

### Pattern 4: Episode Duration Picker
**What:** `<select>` with presets, plus "Custom" option that reveals a number `<input>`.
**When to use:** Show detail page duration setting.
**Example:**
```typescript
const DURATION_PRESETS = [
  { value: 10, label: '10 min' },
  { value: 22, label: '22 min' },
  { value: 44, label: '44 min' },
  { value: 60, label: '60 min' },
  { value: -1, label: 'Custom...' },
];
// When "Custom" selected, show <input type="number" min={1} max={480} />
```

### Anti-Patterns to Avoid
- **Do NOT create a separate ShowList page:** The home page simply gets two sections. No new route for `/shows`.
- **Do NOT use local component state for bible text without syncing:** Use useQuery to initialize state, useMutation on blur to persist. If query refetches, merge with local.
- **Do NOT duplicate the full ProjectCard for ShowCard:** Extract shared card styling, then specialize. ShowCard only differs in metadata line (episode count vs framework label).
- **Do NOT use `useEffect` for auto-save:** Use `onBlur` handler with `useMutation`, not a timer-based `useEffect`. The context decision says "auto-save on blur," not on keystroke.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal dialog | Custom overlay + portal | `@radix-ui/react-dialog` | Already used for CreateProjectModal, handles focus trap + escape + overlay |
| Client routing | Manual URL parsing | `react-router-dom` useParams, useNavigate | Standard in project |
| Server state | useState + useEffect + fetch | `@tanstack/react-query` useQuery + useMutation | Standard in project, handles caching/invalidation |
| Icon set | SVG files or custom icons | `lucide-react` | Already used everywhere, has Tv icon |
| CSS utility merging | Manual className strings | `cn()` from `lib/utils.ts` using `clsx` + `tailwind-merge` | Existing utility |

## Common Pitfalls

### Pitfall 1: Stale Bible Data After Blur-Save
**What goes wrong:** User types in bible textarea, blurs to save. The mutation triggers a query invalidation that refetches, replacing the textarea value mid-edit if the user has already started typing in another section.
**Why it happens:** `queryClient.invalidateQueries` triggers a refetch that overwrites local state.
**How to avoid:** Use local state for textarea values, initialize from query data on mount. Only sync back from server on explicit refetch (e.g., page load). Do NOT overwrite local state on every query refetch. Use `initialData` or `useEffect` with a "loaded" flag.
**Warning signs:** Textarea content flickering or reverting after saving.

### Pitfall 2: Loading State Flash on Home Page
**What goes wrong:** Two parallel queries mean `isLoading` could differ. If one resolves before the other, the page partially renders then re-renders.
**Why it happens:** Independent query timing.
**How to avoid:** Show a single loading state that waits for BOTH queries: `const isLoading = showsLoading || projectsLoading;`
**Warning signs:** Content appearing in sections at different times, causing layout shift.

### Pitfall 3: Episode Count Always Shows 0
**What goes wrong:** The ShowResponse schema from Phase 36 does NOT include an `episode_count` field. Showing a hardcoded "0 episodes" is fine per context, but if someone tries to fetch a real count, it won't exist until Phase 39.
**Why it happens:** The show model has no relationship to episodes yet.
**How to avoid:** Hardcode "0 episodes" on ShowCard as the context says. Do NOT add a backend endpoint or query for episode count.
**Warning signs:** Trying to add an `episode_count` field to ShowResponse.

### Pitfall 4: Missing Route Registration
**What goes wrong:** `/shows/:showId` route not matching because it's defined after a catch-all or wildcard route.
**Why it happens:** React Router v6 matches in order of specificity, but if a wildcard exists it could capture first.
**How to avoid:** Place `/shows/:showId` route before any catch-all. Looking at App.tsx, there are no wildcards so this is low risk, but be aware of route ordering.
**Warning signs:** Navigating to `/shows/abc-123` lands on the wrong page.

### Pitfall 5: TypeScript Build Errors from Missing Types
**What goes wrong:** Adding show API methods before defining Show/BibleResponse types in `types/index.ts` causes build failures.
**Why it happens:** `npm run build` runs `tsc` first. Types must be defined before API methods reference them.
**How to avoid:** Define types FIRST in `types/index.ts`, then add API methods, then build components.
**Warning signs:** `tsc` errors about missing type `Show` or `BibleResponse`.

## Code Examples

### TypeScript Types (add to types/index.ts)
```typescript
// Show types (v4.2 -- Phase 38)
export interface Show {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string | null;
}

export interface BibleResponse {
  show_id: string;
  bible_characters: string;
  bible_world_setting: string;
  bible_season_arc: string;
  bible_tone_style: string;
  episode_duration_minutes: number | null;
}

export interface BibleUpdate {
  bible_characters?: string;
  bible_world_setting?: string;
  bible_season_arc?: string;
  bible_tone_style?: string;
  episode_duration_minutes?: number | null;
}

export interface ShowCreate {
  title: string;
  description?: string;
}
```

### API Methods (add to lib/api.tsx)
```typescript
// Shows (v4.2)
async getShows(): Promise<Show[]> {
  const response = await fetch(`${API_BASE_URL}/shows/`, { headers: getHeaders() });
  if (!response.ok) throw new Error('Failed to fetch shows');
  return response.json();
},

async getShow(id: string): Promise<Show> {
  const response = await fetch(`${API_BASE_URL}/shows/${id}`, { headers: getHeaders() });
  if (!response.ok) throw new Error('Failed to fetch show');
  return response.json();
},

async createShow(data: { title: string; description?: string }): Promise<Show> {
  const response = await fetch(`${API_BASE_URL}/shows/`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create show');
  return response.json();
},

async updateShow(id: string, data: Partial<Show>): Promise<Show> {
  const response = await fetch(`${API_BASE_URL}/shows/${id}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update show');
  return response.json();
},

async deleteShow(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/shows/${id}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to delete show');
},

async getBible(showId: string): Promise<BibleResponse> {
  const response = await fetch(`${API_BASE_URL}/shows/${showId}/bible`, { headers: getHeaders() });
  if (!response.ok) throw new Error('Failed to fetch bible');
  return response.json();
},

async updateBible(showId: string, data: Partial<BibleUpdate>): Promise<BibleResponse> {
  const response = await fetch(`${API_BASE_URL}/shows/${showId}/bible`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update bible');
  return response.json();
},
```

### Constants (add to lib/constants.ts)
```typescript
// In QUERY_KEYS:
SHOWS: 'shows',
SHOW: (id: string) => ['show', id] as const,
BIBLE: (id: string) => ['bible', id] as const,

// In ROUTES:
SHOW: (id: string) => `/shows/${id}`,
SHOWS: '/shows',
```

### Backend API Contract (verified from shows.py and schemas.py)
```
GET    /api/shows/              -> ShowResponse[]     (list all user's shows)
POST   /api/shows/              -> ShowResponse       (create: {title, description?})
GET    /api/shows/{id}          -> ShowResponse       (single show)
PUT    /api/shows/{id}          -> ShowResponse       (update: {title?, description?})
DELETE /api/shows/{id}          -> {status, message}
GET    /api/shows/{id}/bible    -> BibleResponse
PUT    /api/shows/{id}/bible    -> BibleResponse      (partial update: any combination of 5 fields)
```

### Bible Section Configuration
```typescript
export const BIBLE_SECTIONS = [
  { key: 'bible_characters', label: 'Characters', placeholder: 'Describe your main and recurring characters...' },
  { key: 'bible_world_setting', label: 'World / Setting', placeholder: 'Describe the world, time period, and locations...' },
  { key: 'bible_season_arc', label: 'Season Arc', placeholder: 'Outline the overarching story arc for the season...' },
  { key: 'bible_tone_style', label: 'Tone & Style', placeholder: 'Describe the visual style, tone, and mood...' },
] as const;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single entity home page | Multi-entity split home page | Phase 38 | Home page now queries two collections |
| Projects-only routing | Projects + Shows routing | Phase 38 | New /shows/:showId route |

**No deprecated approaches.** This phase introduces new frontend patterns using existing stable libraries.

## Open Questions

1. **Show title/description editing on detail page -- inline or modal?**
   - What we know: CONTEXT.md says "editable inline or via modal"
   - What's unclear: Which approach the user prefers
   - Recommendation: Use inline editing (click title to edit) for simplicity, matching common UX. A modal would be over-engineered for two fields. Implement as an editable text field with save on blur, consistent with bible auto-save pattern.

2. **Episode count on ShowCard before Phase 39?**
   - What we know: ShowResponse has no episode_count field. Context says "0 until Phase 39".
   - What's unclear: Whether to show "0 episodes" text or omit count entirely
   - Recommendation: Show "0 episodes" as static text. Phase 40 will make this dynamic.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend only -- no frontend test framework currently) |
| Config file | backend implicit (pytest discovers app/tests/) |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHOW-02 | Home page shows sections (Shows + Films) | manual-only | N/A -- frontend-only, no test framework | N/A |
| SHOW-03 | Show detail page with bible + episodes area | manual-only | N/A -- frontend-only, no test framework | N/A |
| BIBL-01 | Four bible sections rendered as expandable textareas | manual-only | N/A -- frontend-only, no test framework | N/A |
| BIBL-02 | Bible section edit + auto-save on blur | manual-only | N/A -- verify via backend API test that PUT /bible works | N/A |
| BIBL-03 | Episode duration with presets + custom | manual-only | N/A -- verify backend accepts any integer 1-480 | N/A |

**Justification for manual-only:** This project has no frontend test framework (no Jest, Vitest, Playwright, or Cypress). All 38 prior phases validated frontend work manually. Backend API tests already exist in `test_shows_api.py` to validate the data layer.

### Sampling Rate
- **Per task commit:** Visual inspection in browser -- create show, open show, edit bible, save, refresh
- **Per wave merge:** Full manual walkthrough: create show from home, verify Films section unchanged, edit all four bible sections, set duration to preset and custom, refresh to verify persistence
- **Phase gate:** `cd backend && source venv/bin/activate && pytest app/tests/ -x` (ensure no regression)

### Wave 0 Gaps
None -- backend API tests already exist. Frontend has no test infrastructure to gap-check against.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** -- Direct reading of all files listed in Architecture Patterns section
  - `frontend/src/App.tsx` -- Current route structure (line-by-line)
  - `frontend/src/lib/api.tsx` -- All existing API methods and fetch patterns
  - `frontend/src/types/index.ts` -- All current TypeScript interfaces
  - `frontend/src/lib/constants.ts` -- QUERY_KEYS, ROUTES, config objects
  - `frontend/src/components/Projects/ProjectList.tsx` -- Home page implementation
  - `frontend/src/components/Projects/ProjectCard.tsx` -- Card component pattern
  - `frontend/src/components/Projects/CreateProjectModal.tsx` -- Modal creation pattern
  - `frontend/src/components/Layout/Header.tsx` -- Navigation structure
  - `frontend/src/components/Auth/ProtectedRoute.tsx` -- Auth wrapper pattern
  - `backend/app/api/endpoints/shows.py` -- Complete Show + Bible API endpoints
  - `backend/app/models/schemas.py` -- ShowCreate, ShowUpdate, ShowResponse, BibleUpdate, BibleResponse schemas
  - `backend/app/models/database.py` -- Show model with bible columns

### Secondary (MEDIUM confidence)
- **CONTEXT.md decisions** -- User-locked UI/UX choices for this phase
- **REQUIREMENTS.md** -- Requirement IDs and acceptance criteria
- **ROADMAP.md** -- Phase dependencies and success criteria

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used extensively
- Architecture: HIGH -- every pattern has a direct existing analog in the codebase
- Pitfalls: HIGH -- identified from direct code reading, not speculation

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- all dependencies locked, no external factors)
