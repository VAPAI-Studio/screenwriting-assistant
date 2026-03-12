# Phase 7: Frontend Pipeline Tree - Research

**Researched:** 2026-03-12
**Domain:** React frontend -- collapsible tree component, React Query data fetching, toggle state management
**Confidence:** HIGH

## Summary

Phase 7 is a frontend-only phase that builds a collapsible tree view inside the existing `AgentManager.tsx` component. The tree visualizes which agents are mapped to which pipeline steps (phases and subsections from the template system). The backend API (`GET /api/agents/pipeline-map`) already exists and returns a flat list of `PipelineMapEntry` objects. The frontend must fetch this data, group it into a tree hierarchy (phase -> subsection -> agent badges), and allow per-agent toggle via the existing `PATCH /api/agents/{agent_id}` endpoint with `{ is_active: true/false }`.

The project already uses React 18, TypeScript, Tailwind CSS, Radix UI, React Query (TanStack Query v5), and lucide-react for icons. No new dependencies are needed. The collapsible tree can be built with native HTML disclosure elements or simple React state -- Radix UI Accordion/Collapsible are available but not currently installed, and adding them is optional. Given the project's existing pattern of building interactive UI with useState + Tailwind transitions (see `CreateAgentForm` in `AgentManager.tsx`), a custom collapsible tree using `useState` and CSS transitions is the right approach.

**Primary recommendation:** Build `AgentPipelineTree.tsx` as a standalone component embedded below the agent list in `AgentManager.tsx`. Fetch pipeline-map data with a new React Query hook, group entries client-side into a phase->subsection->agents hierarchy, render with useState-driven collapse/expand, and toggle agents via PATCH mutation on `is_active`.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TREE-01 | Collapsible tree view component showing which agents activate at which pipeline steps | Backend `GET /api/agents/pipeline-map` returns flat `PipelineMapEntry[]` with `phase`, `subsection_key`, `agent_id`, `confidence`. Frontend groups by phase->subsection, renders collapsible hierarchy. Template config provides human-readable phase/subsection names. |
| TREE-02 | Tree view auto-refreshes when agents are created, edited, or deleted | React Query invalidation of `PIPELINE_MAP` query key on agent mutation `onSuccess`. Existing `createMutation` and `deleteMutation` in `AgentManager.tsx` already invalidate `QUERY_KEYS.AGENTS`; add `QUERY_KEYS.PIPELINE_MAP` to same callbacks. |
| TREE-03 | Per-agent toggle to exclude/include individual agents from the pipeline | Backend `PATCH /api/agents/{agent_id}` accepts `{ is_active: boolean }`. Backend `pipeline_composer.py` and `agent_review_middleware.py` already filter on `Agent.is_active == True`. Toggle UI sets `is_active=false` to exclude. `is_active` is NOT a semantic field, so toggling does NOT trigger re-composition (agent stays in map but gets filtered at review time). |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18.2.x | Component framework | Already installed; project standard |
| @tanstack/react-query | 5.20.x | Server state / caching | Already installed; project uses for all data fetching |
| TypeScript | 5.2.x | Type safety | Already installed |
| Tailwind CSS | 3.4.x | Styling | Already installed; project convention |
| lucide-react | 0.314.x | Icons (ChevronRight, ChevronDown, etc.) | Already installed; used everywhere |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| clsx | 2.1.x | Conditional class names | Already installed; used in UI components |
| tailwind-merge | 2.2.x | Class conflict resolution | Already installed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom collapsible with useState | @radix-ui/react-accordion | Would add a dependency; overkill for simple expand/collapse. Project does not currently use it. |
| Custom collapsible with useState | @radix-ui/react-collapsible | Would add a dependency; custom approach matches existing patterns in codebase. |
| Client-side grouping | Backend-grouped endpoint | Backend already returns flat entries (Phase 3 decision documented in STATE.md); grouping is trivial in frontend. |

**Installation:**
No new packages needed. All dependencies are already installed.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
  components/
    Books/
      AgentManager.tsx          # EXISTING - add PipelineTree embed
      AgentPipelineTree.tsx     # NEW - tree component
  lib/
    api.tsx                     # ADD getPipelineMap() method
    constants.ts                # ADD QUERY_KEYS.PIPELINE_MAP
  types/
    index.ts                    # ADD PipelineMapEntry, PipelineMapResponse types
```

### Pattern 1: Pipeline Map Data Flow
**What:** Fetch flat entries from backend, group client-side, render tree.
**When to use:** Always -- this is the only data source for the tree.
**Example:**
```typescript
// Source: Backend GET /api/agents/pipeline-map response shape
interface PipelineMapEntry {
  id: string;
  owner_id: string;
  agent_id: string;
  phase: string;           // e.g., "idea", "story", "scenes", "write"
  subsection_key: string;  // e.g., "core", "characters", "scene_wizard"
  confidence: number;       // 0.0 - 1.0
  rationale: string | null;
  pipeline_dirty: boolean;
  created_at: string | null;
  updated_at: string | null;
}

interface PipelineMapResponse {
  owner_id: string;
  entries: PipelineMapEntry[];
  total_mappings: number;
}

// Client-side grouping for tree rendering:
interface TreePhase {
  phase: string;
  phaseName: string;       // human-readable from template config
  subsections: TreeSubsection[];
}

interface TreeSubsection {
  key: string;
  name: string;            // human-readable from template config
  agents: TreeAgent[];
}

interface TreeAgent {
  agentId: string;
  name: string;
  color: string;
  icon: string;
  agentType: AgentType;
  confidence: number;
  isActive: boolean;       // from Agent.is_active, controls toggle state
}
```

### Pattern 2: React Query Invalidation Chain
**What:** When agent CRUD mutations fire, invalidate both AGENTS and PIPELINE_MAP query keys.
**When to use:** On every agent create, update, or delete.
**Example:**
```typescript
// Source: Existing pattern in AgentManager.tsx
const createMutation = useMutation({
  mutationFn: (data) => api.createAgent(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.AGENTS] });
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.PIPELINE_MAP] });
    setShowCreateForm(false);
  },
});
```
**Note:** Pipeline recomposition happens in a BackgroundTask on the backend (see `_recompose_pipeline_background` in `agents.py`). There may be a brief delay (1-3 seconds) between agent mutation and pipeline-map reflecting the change. The tree should show the stale data initially and auto-update when React Query refetches.

### Pattern 3: Toggle State via is_active
**What:** Per-agent pipeline exclusion uses the existing `is_active` boolean field.
**When to use:** When user clicks toggle switch on an agent badge in the tree.
**Example:**
```typescript
// Toggle agent active state
const toggleMutation = useMutation({
  mutationFn: ({ agentId, isActive }: { agentId: string; isActive: boolean }) =>
    api.updateAgent(agentId, { is_active: isActive }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.AGENTS] });
    // Note: is_active is NOT a semantic field, so backend does NOT recompose pipeline.
    // Agent stays in map but is filtered out at review time.
  },
});
```

### Pattern 4: Template-Enriched Tree Labels
**What:** Map bare `phase`/`subsection_key` strings to human-readable names using the template config.
**When to use:** When rendering tree nodes.
**Example:**
```typescript
// Template config provides name mapping:
// phase "story" -> "Story"
// subsection_key "core" -> "Core"
// subsection_key "characters" -> "Characters"
function buildTreeData(
  entries: PipelineMapEntry[],
  agents: Agent[],
  templateConfig: TemplateConfig
): TreePhase[] {
  const agentMap = new Map(agents.map(a => [a.id, a]));
  const grouped = new Map<string, Map<string, PipelineMapEntry[]>>();

  for (const entry of entries) {
    if (!grouped.has(entry.phase)) grouped.set(entry.phase, new Map());
    const phaseMap = grouped.get(entry.phase)!;
    if (!phaseMap.has(entry.subsection_key)) phaseMap.set(entry.subsection_key, []);
    phaseMap.get(entry.subsection_key)!.push(entry);
  }

  return templateConfig.phases
    .filter(p => grouped.has(p.id))
    .map(phase => ({
      phase: phase.id,
      phaseName: phase.name,
      subsections: phase.subsections
        .filter(s => grouped.get(phase.id)?.has(s.key))
        .map(sub => ({
          key: sub.key,
          name: sub.name,
          agents: (grouped.get(phase.id)?.get(sub.key) || [])
            .map(entry => {
              const agent = agentMap.get(entry.agent_id);
              return agent ? {
                agentId: entry.agent_id,
                name: agent.name,
                color: agent.color,
                icon: agent.icon,
                agentType: agent.agent_type,
                confidence: entry.confidence,
                isActive: agent.is_active,
              } : null;
            })
            .filter(Boolean) as TreeAgent[],
        })),
    }));
}
```

### Anti-Patterns to Avoid
- **Fetching template config separately for the tree:** The template config is already available via `ProjectWorkspace` or can be fetched with the existing `QUERY_KEYS.TEMPLATE` query. Do NOT duplicate template fetching.
- **Storing toggle state in React state or localStorage:** The `is_active` field is persisted on the backend via PATCH. Do NOT manage a separate client-side toggle map.
- **Re-fetching pipeline map on a timer/interval:** Use React Query invalidation, not polling. Background recomposition is event-driven (agent CRUD), not time-based.
- **Building a deep component tree for each node:** Keep the tree flat -- one component with mapped arrays and conditional rendering. Over-componentizing a 3-level tree (phase -> subsection -> agent) adds complexity without benefit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Collapsible sections | Custom animation library | Tailwind `max-h-0 overflow-hidden transition-all` + boolean state | CSS transitions are simpler and performant; project already uses this pattern |
| Toggle switch UI | Custom checkbox logic | A styled `<button>` with conditional bg-color + circle offset (Tailwind toggle pattern) | Standard toggle pattern, no accessibility library needed for MVP |
| Data grouping | Backend endpoint change | Client-side `Map` grouping | Data set is small (typically <50 entries), grouping is trivial |
| Agent name/color lookup | Separate API call per agent | Join with already-fetched `agents` query data | `QUERY_KEYS.AGENTS` data is already cached in React Query |

**Key insight:** The pipeline-map response contains only IDs and structural data (phase, subsection_key, confidence). Agent metadata (name, color, icon, is_active) must come from the already-cached agents query, not a separate fetch. This is a client-side join, not a network request.

## Common Pitfalls

### Pitfall 1: Race Condition Between Agent CRUD and Pipeline Map Refresh
**What goes wrong:** User creates an agent, tree refreshes, but pipeline-map hasn't been recomposed yet (background task is still running). Tree shows old data without the new agent.
**Why it happens:** Pipeline recomposition is async (BackgroundTasks). The POST response returns immediately, React Query invalidates pipeline-map, the refetch fires, but recomposition hasn't finished.
**How to avoid:** Accept eventual consistency. The tree will update on the next refetch (React Query stale time is 5 minutes by default, but manual invalidation triggers immediate refetch). Optionally show a brief "Updating pipeline..." indicator if `pipeline_dirty` flags are true.
**Warning signs:** New agents appear in the agent list but not in the tree for several seconds.

### Pitfall 2: Template Config Not Available When Tree Renders
**What goes wrong:** The tree component tries to look up human-readable phase/subsection names from template config, but it hasn't loaded yet or the user is on the Books page (not inside a project workspace).
**Why it happens:** `AgentManager.tsx` is rendered inside `BookManager.tsx` on the `/books` route, which has no project context and thus no template config.
**How to avoid:** Either (a) fetch template config independently in the tree component using a hardcoded template ID (the system currently only has one template: "short_movie"), or (b) fall back to displaying raw phase/subsection_key strings when template config is unavailable.
**Warning signs:** Tree nodes show "undefined" or blank labels.

### Pitfall 3: Toggling is_active Hides Agent From Agent List
**What goes wrong:** Setting `is_active=false` on an agent causes it to disappear from the agent list because the backend `list_agents` endpoint filters `Agent.is_active == True`.
**Why it happens:** The `list_agents` endpoint at line 63 of `agents.py` filters on `is_active == True`.
**How to avoid:** This is a significant concern. The TREE-03 requirement says "exclude from pipeline reviews" but `is_active=false` would hide the agent entirely. Two options: (1) Add a separate `pipeline_enabled` field to the Agent model, or (2) change the backend to include inactive agents in the list response (with an `is_active` flag). Option 2 is simpler and backward-compatible -- the frontend can filter display as needed, and the middleware already checks `is_active` independently. The planner should decide: either remove the `is_active == True` filter from `list_agents` or add a new `pipeline_enabled` field.
**Warning signs:** Agent disappears from both the agent list and the tree when toggled off.

### Pitfall 4: Missing `updateAgent` API Method in Frontend
**What goes wrong:** The toggle tries to call `api.updateAgent()` but this method doesn't exist in `api.tsx`.
**Why it happens:** The backend `PATCH /api/agents/{agent_id}` exists but no corresponding frontend API function was created.
**How to avoid:** Add `updateAgent(agentId: string, data: Partial<AgentUpdate>)` to `api.tsx` as part of the first plan.
**Warning signs:** TypeScript compile error on `api.updateAgent`.

## Code Examples

Verified patterns from the existing codebase:

### Fetching Pipeline Map (New API Method)
```typescript
// Add to frontend/src/lib/api.tsx
async updateAgent(agentId: string, data: {
  name?: string;
  description?: string;
  system_prompt_template?: string;
  personality?: string;
  color?: string;
  icon?: string;
  is_active?: boolean;
  agent_type?: AgentType;
  tags_filter?: string[];
}): Promise<Agent> {
  const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update agent');
  return response.json();
},

async getPipelineMap(): Promise<PipelineMapResponse> {
  const response = await fetch(`${API_BASE_URL}/agents/pipeline-map`, {
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error('Failed to fetch pipeline map');
  return response.json();
},
```

### Collapsible Section Pattern (Existing Codebase Convention)
```typescript
// Source: CreateAgentForm in AgentManager.tsx uses this pattern
const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());

const togglePhase = (phaseId: string) => {
  setExpandedPhases(prev => {
    const next = new Set(prev);
    if (next.has(phaseId)) next.delete(phaseId);
    else next.add(phaseId);
    return next;
  });
};

// Render:
<button onClick={() => togglePhase(phase.id)} className="flex items-center gap-1.5">
  {expandedPhases.has(phase.id)
    ? <ChevronDown className="h-3.5 w-3.5" />
    : <ChevronRight className="h-3.5 w-3.5" />}
  <span className="text-sm font-medium">{phase.name}</span>
</button>
{expandedPhases.has(phase.id) && (
  <div className="ml-4 mt-1 space-y-1">
    {/* subsection nodes */}
  </div>
)}
```

### Agent Badge with Toggle
```typescript
// Toggle switch pattern using Tailwind
function AgentToggleBadge({ agent, onToggle, isToggling }: {
  agent: TreeAgent;
  onToggle: (agentId: string, newState: boolean) => void;
  isToggling: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border transition-colors ${
      agent.isActive
        ? 'border-border bg-muted/20'
        : 'border-border/50 bg-muted/5 opacity-50'
    }`}>
      <span
        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: agent.color }}
      />
      <span className="text-xs font-medium text-foreground truncate">{agent.name}</span>
      <button
        onClick={() => onToggle(agent.agentId, !agent.isActive)}
        disabled={isToggling}
        className={`ml-auto w-7 h-4 rounded-full transition-colors flex-shrink-0 relative ${
          agent.isActive ? 'bg-emerald-500' : 'bg-muted-foreground/30'
        }`}
      >
        <span className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${
          agent.isActive ? 'left-3.5' : 'left-0.5'
        }`} />
      </button>
    </div>
  );
}
```

### Empty State (Matches Existing Convention)
```typescript
// Source: AgentManager.tsx empty state pattern
{agents.length === 0 && (
  <div className="text-center py-8 text-muted-foreground">
    <Network className="h-8 w-8 mx-auto mb-2 opacity-30" />
    <p className="text-sm">Create agents to see how they map to your pipeline</p>
  </div>
)}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate toggle field per pipeline step | Global `is_active` on Agent model | Phase 1 (DB Foundation) | One toggle controls all pipeline participation; simpler but less granular |
| Backend-grouped tree data | Frontend groups flat entries | Phase 3 (API decision) | Client-side grouping from flat `PipelineMapResponse.entries` |

**Deprecated/outdated:**
- None relevant -- this is a greenfield frontend component.

## Open Questions

1. **is_active vs pipeline_enabled: granularity of the toggle**
   - What we know: `is_active=false` currently hides the agent from `list_agents` (backend filters on `is_active==True`). Setting it to false would remove the agent from both the agent list AND the pipeline.
   - What's unclear: Does the user want to "pause" an agent from pipeline reviews while keeping it visible for chat and other purposes?
   - Recommendation: The simplest v1 approach is to remove the `is_active == True` filter from the backend `list_agents` endpoint (show all agents, let frontend display inactive ones with visual distinction). Alternatively, add a new `pipeline_enabled` boolean to the Agent model. The planner must decide which approach to take. Removing the filter is a 1-line backend change; adding a field requires a migration.

2. **Template config availability on the Books page**
   - What we know: `AgentManager.tsx` renders inside `BookManager.tsx` at route `/books`. There is no project context here, so no template config is loaded.
   - What's unclear: Should the tree always show human-readable names, or is raw `phase`/`subsection_key` acceptable?
   - Recommendation: Fetch the template list and use the first (only) template ("short_movie") to populate labels. The tree component can call `api.getTemplate("short_movie")` with its own React Query hook. This is independent of project context.

3. **Stale pipeline data after background recomposition**
   - What we know: Agent CRUD triggers background recomposition. React Query invalidation fires immediately, but the refetched data may still be stale.
   - What's unclear: How long does recomposition typically take? Is there a mechanism to know when it completes?
   - Recommendation: For v1, rely on React Query's default refetch behavior. The tree will show stale data for 1-3 seconds. If needed later, add a polling interval (5s) specifically for pipeline-map, or check `pipeline_dirty` flags. This is a v2 concern.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None currently installed for frontend |
| Config file | none -- see Wave 0 |
| Quick run command | N/A |
| Full suite command | N/A |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TREE-01 | Tree renders collapsible hierarchy | manual-only | Visual inspection in browser | N/A |
| TREE-02 | Tree auto-refreshes on agent CRUD | manual-only | Create agent, verify tree updates | N/A |
| TREE-03 | Toggle excludes agent from pipeline | manual-only | Toggle agent, verify visual + backend state | N/A |

**Note:** No frontend test framework (vitest, jest) is installed. All validation is manual for this phase. Adding a test framework is out of scope for Phase 7 (it would need its own plan).

### Sampling Rate
- **Per task commit:** `npm run build` (TypeScript compilation check)
- **Per wave merge:** `npm run build && npm run lint`
- **Phase gate:** Visual inspection of all 4 success criteria in browser

### Wave 0 Gaps
- No frontend test infrastructure exists (no vitest, no jest, no testing-library)
- Manual verification required for all requirements
- `npm run build` serves as the automated quality gate (catches type errors and unused imports)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `backend/app/api/endpoints/agents.py` -- GET /pipeline-map endpoint (line 130-146)
- Codebase inspection: `backend/app/models/database.py` -- AgentPipelineMap model (line 434-455)
- Codebase inspection: `backend/app/models/schemas.py` -- PipelineMapEntry/PipelineMapResponse (line 621-644)
- Codebase inspection: `frontend/src/components/Books/AgentManager.tsx` -- current component structure
- Codebase inspection: `frontend/src/lib/api.tsx` -- existing API methods and patterns
- Codebase inspection: `frontend/src/lib/constants.ts` -- QUERY_KEYS pattern
- Codebase inspection: `frontend/src/types/index.ts` -- Agent type definition with is_active field
- Codebase inspection: `backend/app/services/agent_review_middleware.py` -- is_active filtering (line 174)
- Codebase inspection: `backend/app/services/pipeline_composer.py` -- is_active filtering (line 98), SEMANTIC_FIELDS (line 68)

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` -- architectural decisions about pipeline composition and session patterns
- `.planning/ROADMAP.md` -- Phase 7 plan outlines (07-01 through 07-05)

### Tertiary (LOW confidence)
- None -- all findings verified against codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already installed and used in project
- Architecture: HIGH - follows exact patterns from existing codebase (React Query, mutation/invalidation, component structure)
- Pitfalls: HIGH - identified by direct codebase inspection (is_active filter on list_agents, missing updateAgent API method, template config availability)

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable -- no external dependencies, all codebase-internal)
