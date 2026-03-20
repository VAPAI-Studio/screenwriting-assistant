# Phase 27: Generate Shotlist UI & AI Badge - Research

**Researched:** 2026-03-20
**Domain:** React frontend -- mutation trigger, loading states, AI badge rendering
**Confidence:** HIGH

## Summary

Phase 27 is a frontend-only phase. The backend endpoint (`POST /api/shots/{project_id}/generate`) and all data model changes (`ai_generated`, `user_modified` columns on the Shot model, `ShotResponse` schema returning both fields) are already complete from Phase 26. The work consists of four discrete changes: (1) add a `generateShotlist` API method to the frontend API client, (2) add a "Generate Shotlist" button with mutation and loading state to the `ShotlistPanel` or `BreakdownLayout`, (3) update the `Shot` TypeScript interface to include `ai_generated` and `user_modified` fields, and (4) add a sparkle icon badge to `ShotRow` for AI-generated shots.

The project already uses `Sparkles` from `lucide-react` extensively throughout the codebase (ReviewPanel, ChatSidebar, SectionEditor, BreakdownPage, AssetsPanel, WizardView). The exact same icon and styling pattern should be reused. The project also has an established pattern for source badges in `ElementCard.tsx` (using colored pill badges for "AI" vs "User"). The shot badge should follow a similar but more subtle pattern -- a small sparkle icon next to the shot number.

**Primary recommendation:** This is a straightforward frontend wiring phase. Use `useMutation` from React Query for the generate trigger, invalidate the `SHOTS` query key on success, and render the `Sparkles` icon conditionally based on `shot.ai_generated`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AISG-01 | User can trigger AI generation of a full shotlist via "Generate Shotlist" button in the breakdown panel (frontend trigger portion) | API method wiring + useMutation + button in ShotlistPanel header area |
| AISG-07 | AI-generated shots display a subtle visual indicator (sparkle icon badge) distinguishable from manually-created shots | Shot type update + Sparkles icon in ShotRow number cell |
</phase_requirements>

## Standard Stack

### Core (already installed -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 18.x | UI framework | Already in use |
| @tanstack/react-query | 5.x | Server state management | Already in use -- useMutation for generate trigger |
| lucide-react | 0.314.0 | Icons | Already in use -- Sparkles icon already imported elsewhere |
| tailwindcss | 3.x | Styling | Already in use |

### Supporting
No new libraries needed. All required functionality is covered by the existing stack.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sparkles icon | Custom SVG | No benefit -- Sparkles already used consistently in codebase |
| Inline loading text | Toast notification | Inline is better UX for long-running operations; toasts disappear |

**Installation:**
```bash
# No installation needed -- all dependencies already present
```

## Architecture Patterns

### Existing File Structure (files to modify)
```
frontend/src/
  lib/api.tsx              # Add generateShotlist() method
  types/index.ts           # Add ai_generated, user_modified to Shot interface
  components/Breakdown/
    ShotlistPanel.tsx       # Add generate button + mutation
    ShotRow.tsx             # Add sparkle badge for AI shots
    ShotlistEmptyState.tsx  # Add generate option to empty state
```

### Pattern 1: API Method for Generation Endpoint
**What:** Add `generateShotlist` to the `api` object in `lib/api.tsx`
**When to use:** When calling `POST /api/shots/{project_id}/generate`
**Details:**
- Endpoint: `POST /api/shots/{project_id}/generate`
- Uses `fetchWithTimeout` (generation may take 10-30 seconds with AI)
- Should use a longer timeout than the default 30s (use `CHAT_TIMEOUT` = 120s)
- Response shape: `{ status: string; shots_created?: number; shots_deleted?: number; shots_preserved?: number; message?: string }`
- Error case: `{ status: "error", message: "..." }` (when no screenplay or no scenes)

```typescript
// Source: backend/app/api/endpoints/shots.py and shotlist_generation_service.py
async generateShotlist(projectId: string): Promise<{
  status: string;
  shots_created?: number;
  shots_deleted?: number;
  shots_preserved?: number;
  message?: string;
}> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT);
  try {
    const response = await fetch(`${API_BASE_URL}/shots/${projectId}/generate`, {
      method: 'POST',
      headers: getHeaders(),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!response.ok) throw new Error('Failed to generate shotlist');
    return response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') throw new Error('Request timeout');
    throw error;
  }
},
```

### Pattern 2: useMutation for Generate Trigger
**What:** React Query mutation that calls the generate endpoint and invalidates shot list on success
**When to use:** In `ShotlistPanel.tsx` or as a shared hook
**Details:**
- On success: invalidate `QUERY_KEYS.SHOTS(projectId!)` so the panel refreshes with new shots
- On error: show error state (the endpoint can return `{ status: "error", message }` for validation failures like missing screenplay)
- The mutation's `isPending` state drives the disabled button + loading spinner

```typescript
// Source: existing mutation pattern in ShotlistPanel.tsx
const generateMutation = useMutation({
  mutationFn: () => api.generateShotlist(projectId!),
  onSuccess: (data) => {
    if (data.status === 'error') {
      // Handle validation error (no screenplay, no scenes)
      // Show inline error or set error state
      return;
    }
    // Refresh the shots list
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) });
  },
  onError: () => {
    // Network/server error handling
  },
});
```

### Pattern 3: AI Badge in ShotRow
**What:** Conditionally render a Sparkles icon next to the shot number when `shot.ai_generated === true`
**When to use:** In the shot number cell of `ShotRow.tsx`
**Details:**
- The Sparkles icon should be small (h-3 w-3) and subtle (amber-400/60 or blue-400/60)
- Only shown when `shot.ai_generated` is true
- Must NOT appear on manually-created shots (where `ai_generated` is false)
- Follows the same pattern as `ElementCard.tsx` which shows a Pencil icon for `user_modified`

```typescript
// Source: existing ElementCard.tsx pattern for user_modified badge
<div className="flex items-center justify-center px-1 py-2 text-xs font-semibold text-primary min-h-[40px]">
  {shot.shot_number}
  {shot.ai_generated && (
    <Sparkles className="h-2.5 w-2.5 text-blue-400/60 ml-0.5 flex-shrink-0" />
  )}
</div>
```

### Pattern 4: Button Placement
**What:** "Generate Shotlist" button in the shotlist header area
**When to use:** Visible when the shotlist panel is displayed (both empty and data states)
**Details:**
- Place in the center panel header bar in `BreakdownLayout.tsx` (next to the "Shotlist" title)
- This is the most visible and accessible location
- Button disabled while `generateMutation.isPending`
- Shows `Loader2` spinner animation while pending
- Uses `Sparkles` icon when idle

### Anti-Patterns to Avoid
- **Polling for generation status:** The generate endpoint is synchronous (returns when done). Do NOT add polling -- just await the mutation response.
- **Optimistic updates for generation:** Do NOT try to optimistically add shots. The generate endpoint creates shots server-side and we should just refetch.
- **Custom loading overlay:** Do NOT build a full-page loading overlay. Use the mutation's `isPending` state to disable the button and show a spinner inline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Loading state management | Custom useState for loading | `useMutation.isPending` from React Query | Already handles loading, error, success states |
| Icon for AI badge | Custom SVG sparkle icon | `Sparkles` from lucide-react | Already used 10+ times in codebase |
| Button styling | Custom button CSS | `Button` component from `components/UI/Button.tsx` | Established variant system with disabled states |
| Query invalidation | Manual refetch logic | `queryClient.invalidateQueries` | Standard React Query pattern already used everywhere |

**Key insight:** Every piece of this phase already has a working pattern in the codebase. The implementation is pattern-matching, not invention.

## Common Pitfalls

### Pitfall 1: Missing Type Fields
**What goes wrong:** The `Shot` TypeScript interface lacks `ai_generated` and `user_modified` fields, causing TypeScript errors when accessing them
**Why it happens:** Phase 26 only modified backend schemas; frontend types were not updated
**How to avoid:** Update `Shot` interface in `types/index.ts` FIRST, before any component changes
**Warning signs:** TypeScript errors like `Property 'ai_generated' does not exist on type 'Shot'`

### Pitfall 2: Default Timeout Too Short
**What goes wrong:** AI generation can take 10-30 seconds; the default `API_TIMEOUT` (30s) may timeout for large scripts
**Why it happens:** `fetchWithTimeout` uses 30s default, but structured AI calls with 8000 max_tokens can be slow
**How to avoid:** Use `CHAT_TIMEOUT` (120s) for the generate endpoint, following the same pattern as `sendBreakdownChatStream`
**Warning signs:** Intermittent "Request timeout" errors during generation

### Pitfall 3: Generate Returning Error Status
**What goes wrong:** The generate endpoint returns `{ status: "error", message: "No screenplay content found" }` with a 200 HTTP status (not a 4xx)
**Why it happens:** The service returns validation errors as part of the response body, not as HTTP errors
**How to avoid:** Check `data.status` in the `onSuccess` callback and handle the "error" status case
**Warning signs:** Generation appears to succeed but no shots are created; user sees no feedback

### Pitfall 4: Optimistic Shot in ShotlistPanel Uses Wrong Type
**What goes wrong:** The optimistic shot creation in `createMutation.onMutate` creates a `Shot` object without `ai_generated` and `user_modified`
**Why it happens:** The optimistic shot literal in `ShotlistPanel.tsx` must also include the new fields
**How to avoid:** When updating the `Shot` type, also update the optimistic shot literal to include `ai_generated: false, user_modified: false`
**Warning signs:** TypeScript errors in the createMutation onMutate callback

### Pitfall 5: Existing Pre-existing TypeScript Build Errors
**What goes wrong:** 3 pre-existing TypeScript build errors in `IndividualEditorView`, `RepeatableCardsView`, `SidebarChat` (noted in STATE.md)
**Why it happens:** These are pre-existing issues from prior phases
**How to avoid:** Do NOT fix these -- they are out of scope. Only fix new errors introduced by this phase.
**Warning signs:** `npm run build` reports errors that are not in files touched by this phase

## Code Examples

### Example 1: Shot Type Update (types/index.ts)
```typescript
// Add ai_generated and user_modified to Shot interface
export interface Shot {
  id: string;
  project_id: string;
  scene_item_id: string | null;
  shot_number: number;
  script_text: string;
  script_range: Record<string, unknown>;
  fields: ShotFields;
  sort_order: number;
  source: 'user' | 'ai';
  ai_generated: boolean;    // NEW
  user_modified: boolean;   // NEW
  created_at: string;
  updated_at: string | null;
}
```

### Example 2: Generate Button in BreakdownLayout Header
```typescript
// Source: existing BreakdownLayout.tsx header pattern
// Place in center panel header alongside "Shotlist" title
<div className="flex items-center justify-between px-3 py-2 flex-shrink-0"
  style={{ borderBottom: '1px solid hsl(var(--border))' }}>
  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
    Shotlist
  </span>
  <button
    onClick={() => generateMutation.mutate()}
    disabled={generateMutation.isPending}
    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold
      text-primary bg-primary/10 hover:bg-primary/20 rounded-lg
      transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
  >
    {generateMutation.isPending
      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
      : <Sparkles className="h-3.5 w-3.5" />}
    {generateMutation.isPending ? 'Generating...' : 'Generate Shotlist'}
  </button>
</div>
```

### Example 3: Sparkle Badge in ShotRow
```typescript
// Source: existing ElementCard.tsx user_modified badge pattern
// In the shot number cell of ShotRow
<div className="flex items-center justify-center gap-0.5 px-1 py-2 text-xs font-semibold text-primary min-h-[40px]">
  {shot.shot_number}
  {shot.ai_generated && (
    <Sparkles
      className="h-2.5 w-2.5 text-blue-400/60 flex-shrink-0"
      title="AI generated"
    />
  )}
</div>
```

### Example 4: Generate Button in Empty State
```typescript
// Source: existing ShotlistEmptyState.tsx
// Add a second button or modify existing to also offer generation
<Button
  onClick={onGenerate}
  disabled={isGenerating}
  className="mt-2"
  variant="outline"
>
  {isGenerating
    ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> Generating...</>
    : <><Sparkles className="h-3.5 w-3.5 mr-1.5" /> Generate with AI</>}
</Button>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No AI generation | Backend endpoint ready (Phase 26) | 2026-03-20 | Frontend must wire trigger |
| Shot type has no ai_generated | Backend returns ai_generated in ShotResponse | Phase 26 | Frontend type must match |
| No source distinction in UI | ElementCard has source badge pattern | Phase 13 | Reusable pattern for shots |

**Deprecated/outdated:**
- None -- all technologies are current

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend only) |
| Config file | backend runs pytest directly |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_shotlist_generation.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AISG-01 | Generate button triggers backend endpoint and shots appear | manual-only | Manual: click "Generate Shotlist" in UI, verify shots render | N/A -- no frontend test framework |
| AISG-07 | AI-generated shots show sparkle badge | manual-only | Manual: verify Sparkles icon on AI shots, absent on user shots | N/A -- no frontend test framework |

**Note:** This project has no frontend test framework (no jest/vitest config, no test files). All frontend verification is manual.

### Sampling Rate
- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/frontend && npm run build` (TypeScript compilation check)
- **Per wave merge:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && source venv/bin/activate && pytest app/tests/ -x` (backend regression)
- **Phase gate:** Frontend builds without new errors + backend tests pass

### Wave 0 Gaps
None -- no frontend test infrastructure exists and adding it is out of scope for this phase. TypeScript compilation (`npm run build`) serves as the automated verification that types are correct and components compile.

## Open Questions

1. **Generate button placement: header vs inline?**
   - What we know: The center panel header in `BreakdownLayout.tsx` has space next to the "Shotlist" title. The `ShotlistEmptyState` also has its own CTA area.
   - What's unclear: Whether the button should only appear in the header, or also in the empty state.
   - Recommendation: Place in BOTH the header (always visible) AND the empty state (as an alternative to "Add First Shot"). The header button is the primary trigger; the empty state offers it as a discovery path.

2. **Error feedback for validation errors (no screenplay/scenes)?**
   - What we know: The endpoint returns `{ status: "error", message: "No screenplay content found" }` as 200.
   - What's unclear: How to surface this to the user.
   - Recommendation: Show the error message inline below the generate button or as a brief inline banner, since the user needs to take action (add screenplay content) before they can generate.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of `backend/app/api/endpoints/shots.py` -- verified generate endpoint exists at `POST /{project_id}/generate`
- Direct codebase inspection of `backend/app/services/shotlist_generation_service.py` -- verified response format
- Direct codebase inspection of `backend/app/models/schemas.py` -- verified `ShotResponse` includes `ai_generated: bool` and `user_modified: bool`
- Direct codebase inspection of `backend/app/models/database.py` -- verified `Shot` model has `ai_generated` and `user_modified` columns
- Direct codebase inspection of `frontend/src/types/index.ts` -- verified `Shot` interface is MISSING `ai_generated` and `user_modified`
- Direct codebase inspection of `frontend/src/lib/api.tsx` -- verified no `generateShotlist` method exists
- Direct codebase inspection of `frontend/src/components/Breakdown/ShotlistPanel.tsx` -- verified current component structure
- Direct codebase inspection of `frontend/src/components/Breakdown/ShotRow.tsx` -- verified shot number cell layout
- Direct codebase inspection of `frontend/src/components/Breakdown/BreakdownLayout.tsx` -- verified center panel header structure
- npm registry verification: `lucide-react` installed at 0.314.0, `Sparkles` icon confirmed present

### Secondary (MEDIUM confidence)
- Pattern inference from `ElementCard.tsx` source badge pattern -- appropriate for shot AI badge

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all verified in package.json and node_modules
- Architecture: HIGH -- all modifications are to existing files with established patterns
- Pitfalls: HIGH -- verified through direct codebase inspection (type mismatch, timeout, error status)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable stack, no moving parts)
