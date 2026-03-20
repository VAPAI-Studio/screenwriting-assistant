# Phase 25: Staleness & Sync - Research

**Researched:** 2026-03-20
**Domain:** Backend staleness flag wiring, frontend staleness banner, cross-mode data sync
**Confidence:** HIGH

## Summary

Phase 25 mirrors the v2.0 Phase 12 staleness hooks pattern exactly, but for the `shotlist_stale` column instead of `breakdown_stale`. The existing codebase already has `shotlist_stale` as a boolean column on the `Project` model (added in Phase 17 data foundation), but no code currently reads or writes it. The task is to: (1) create a `_mark_shotlist_stale` helper function alongside the existing `_mark_breakdown_stale`, (2) call it from the same code locations, (3) expose it via a new or existing API endpoint, and (4) display a staleness banner in the v3.0 breakdown mode layout.

The v2.0 staleness pattern is well-established and documented in the RETROSPECTIVE. The `_mark_breakdown_stale` function in `phase_data.py` is imported into `wizards.py` and `list_items.py`. The same locations need `_mark_shotlist_stale` calls. The frontend pattern is also well-established: `StalenessBar.tsx` renders an amber warning banner with a refresh button, driven by the `is_stale` field from the breakdown summary endpoint. For shotlist staleness, a similar pattern applies but the banner goes into `BreakdownLayout.tsx` (the v3.0 3-panel view) rather than `BreakdownPage.tsx` (the v2.0 element extraction page).

Character name changes (SYNC-03) flow through `list_items.py` PATCH/POST/DELETE endpoints. The existing `_is_scene_item` check triggers `_mark_breakdown_stale` for scene list items. A parallel `_is_character_item` check must trigger `_mark_shotlist_stale` for character name changes, since character names appear in shot fields. This is the lightest possible sync mechanism -- it flags staleness rather than attempting automatic propagation.

**Primary recommendation:** Create `_mark_shotlist_stale` in `phase_data.py` alongside `_mark_breakdown_stale`, call it from every location that calls `_mark_breakdown_stale` plus character list item mutations, add a shotlist-staleness-aware endpoint (either new or by adding `shotlist_stale` to an existing project response), and add a `ShotlistStalenessBar` component in `BreakdownLayout.tsx`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNC-01 | Script content changes (save/generate) set `shotlist_stale = true` on the project | `_mark_shotlist_stale` helper mirrors `_mark_breakdown_stale`; called from `phase_data.py` PATCH (write/scenes phases), `wizards.py` script_writer_wizard and scene_wizard branches |
| SYNC-02 | Breakdown mode shows a staleness banner when shotlist is stale | New `ShotlistStalenessBar` component in BreakdownLayout center panel; needs project query or dedicated endpoint to read shotlist_stale |
| SYNC-03 | Character name changes in Screenwriting mode propagate to Breakdown via existing staleness pattern | `list_items.py` PATCH/POST/DELETE must also call `_mark_shotlist_stale` when mutating story.characters items (parallel to `_is_scene_item` pattern) |
| SYNC-04 | Staleness hooks are placed in the same locations as v2.0 breakdown_stale hooks | 7 hook locations identified: phase_data.py PATCH, wizards.py script_writer_wizard, wizards.py scene_wizard, list_items.py POST, list_items.py PATCH, list_items.py DELETE, plus extraction/clear path |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Backend API | Already in stack |
| SQLAlchemy | existing | ORM for Project.shotlist_stale | Already in stack |
| React Query | existing | Frontend data fetching + cache invalidation | Already in stack |
| lucide-react | existing | Icons for staleness banner | Already in stack |

### Supporting
No new dependencies needed. This phase uses only existing libraries.

## Architecture Patterns

### Pattern 1: Staleness Flag Helper (Backend)

**What:** A function that sets `shotlist_stale = True` on a project, mirroring `_mark_breakdown_stale`.
**When to use:** Called from every code path that modifies script content.

**Source:** `backend/app/api/endpoints/phase_data.py` lines 20-35

```python
# Existing pattern (breakdown_stale):
def _mark_breakdown_stale(db: Session, project_id) -> None:
    """Set breakdown_stale=True if a breakdown exists for this project."""
    has_breakdown = db.query(BreakdownElement).filter(
        BreakdownElement.project_id == str(project_id),
        BreakdownElement.is_deleted == False,
    ).first() is not None
    if has_breakdown:
        project = db.query(database.Project).filter(
            database.Project.id == str(project_id)
        ).first()
        if project:
            project.breakdown_stale = True

# New pattern (shotlist_stale) -- same structure, different guard:
def _mark_shotlist_stale(db: Session, project_id) -> None:
    """Set shotlist_stale=True if shots exist for this project."""
    has_shots = db.query(database.Shot).filter(
        database.Shot.project_id == str(project_id),
    ).first() is not None
    if has_shots:
        project = db.query(database.Project).filter(
            database.Project.id == str(project_id)
        ).first()
        if project:
            project.shotlist_stale = True
```

**Key design decision:** The guard condition for `_mark_shotlist_stale` checks for the existence of at least one Shot (parallel to checking for BreakdownElement in the breakdown version). No point flagging staleness if there's nothing to be stale.

### Pattern 2: Hook Placement Locations

**What:** The exact code locations where `_mark_breakdown_stale` is called (and where `_mark_shotlist_stale` must also be called).

**7 locations identified:**

| # | File | Location | Trigger |
|---|------|----------|---------|
| 1 | `phase_data.py:199-200` | `update_subsection_data()` | PATCH write/scenes phase data |
| 2 | `wizards.py:274` | `apply_wizard_result_to_db()` | script_writer_wizard apply |
| 3 | `wizards.py:317` | `apply_wizard_result_to_db()` | scene_wizard apply |
| 4 | `list_items.py:113-114` | `create_list_item()` | POST scene_list item |
| 5 | `list_items.py:143-144` | `update_list_item()` | PATCH scene_list item |
| 6 | `list_items.py:163-165` | `delete_list_item()` | DELETE scene_list item |
| 7 | `breakdown_service.py:468-473` | `extract()` | Extraction clears breakdown_stale=False |

For SYNC-04, locations 1-6 need `_mark_shotlist_stale` calls co-located with the existing `_mark_breakdown_stale` calls. Location 7 is the "clear" path -- shotlist has no extraction equivalent yet, so no clear path is needed.

### Pattern 3: Character Item Detection (SYNC-03)

**What:** Parallel to `_is_scene_item()`, detect when a list item mutation affects story.characters.
**When to use:** list_items.py POST/PATCH/DELETE to trigger shotlist staleness on character name changes.

**Source:** `backend/app/api/endpoints/list_items.py` lines 43-53

```python
# Existing pattern for scene items:
def _is_scene_item(db: Session, phase_data_id) -> database.PhaseData | None:
    pd = db.query(database.PhaseData).filter(
        database.PhaseData.id == str(phase_data_id)
    ).first()
    if pd and str(pd.phase) == "scenes" and pd.subsection_key == "scene_list":
        return pd
    return None

# New pattern for character items:
def _is_character_item(db: Session, phase_data_id) -> database.PhaseData | None:
    pd = db.query(database.PhaseData).filter(
        database.PhaseData.id == str(phase_data_id)
    ).first()
    if pd and str(pd.phase) == "story" and pd.subsection_key == "characters":
        return pd
    return None
```

### Pattern 4: Frontend Staleness Exposure

**What:** How the frontend reads `shotlist_stale` to display the banner.

**Two options (recommend Option A):**

**Option A: Dedicated lightweight endpoint**
Add a GET `/api/shots/{project_id}/status` endpoint returning `{ shotlist_stale: boolean, shot_count: number }`. Queried with 30s staleTime in BreakdownLayout. Mirrors how BreakdownPage uses `/api/breakdown/summary/{project_id}`.

**Option B: Piggyback on existing project response**
Add `shotlist_stale` to `ProjectResponseV2` schema and `ProjectV2` frontend type. The BreakdownLayout would query the project and read the field.

**Recommendation: Option A** -- it's more consistent with the breakdown pattern and avoids changing the project response schema that many other components consume.

### Pattern 5: Frontend Staleness Banner

**What:** A banner component that appears in the BreakdownLayout center panel.
**Source:** `frontend/src/components/Breakdown/StalenessBar.tsx` (existing breakdown version)

```tsx
// Existing StalenessBar pattern -- amber warning with refresh action
<div className="flex items-center justify-between px-6 py-3 bg-amber-500/10 border-b border-amber-500/20">
  <div className="flex items-center gap-2 text-sm text-amber-400">
    <AlertTriangle className="h-4 w-4" />
    <span>Your breakdown may be outdated -- script has changed since last extraction.</span>
  </div>
  <button onClick={refresh}>Refresh</button>
</div>
```

For shotlist staleness, the banner message would be: "Shotlist may be outdated -- script has changed since shots were last reviewed." The action button could be "Dismiss" (sets `shotlist_stale = false` via API) rather than "Refresh" since there's no auto-regeneration of shotlists (that's deferred to v3.1 AUTO-01).

### Recommended Project Structure Changes

```
backend/app/api/endpoints/
  phase_data.py     # ADD _mark_shotlist_stale, call from PATCH
  wizards.py        # ADD _mark_shotlist_stale calls at lines 274, 317
  list_items.py     # ADD _is_character_item, call _mark_shotlist_stale
  shots.py          # ADD status endpoint (GET /{project_id}/status)

frontend/src/components/Breakdown/
  ShotlistStalenessBar.tsx   # NEW -- banner for shotlist staleness
  BreakdownLayout.tsx        # MODIFY -- add banner above center panel

backend/app/tests/
  test_shotlist_staleness.py # NEW -- mirrors test_staleness.py structure
```

### Anti-Patterns to Avoid
- **Calling `_mark_shotlist_stale` from different locations than `_mark_breakdown_stale`:** SYNC-04 explicitly requires the same locations. If breakdown gets a new hook later, shotlist must too.
- **WebSocket or real-time push for staleness:** The RETROSPECTIVE and PROJECT.md explicitly chose save-triggered sync, not real-time.
- **Automatic shotlist regeneration on staleness:** Auto-generation is v3.1 (AUTO-01). The banner should only flag staleness, not trigger AI regeneration.
- **Modifying project response schemas broadly:** Adding fields to `ProjectResponseV2` affects all consumers. A dedicated endpoint is cleaner.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Staleness detection | Custom change tracking or diff system | Boolean flag set on write paths | Proven v2.0 pattern; simple, zero overhead |
| Banner component | New UI pattern | Clone StalenessBar.tsx structure | Existing component is 30 lines, proven design |
| State propagation | React Context or global state | React Query with 30s staleTime polling | Existing pattern from BreakdownPage |

## Common Pitfalls

### Pitfall 1: Missing a Hook Location
**What goes wrong:** One of the 7 hook locations gets missed, and script changes through that path don't flag staleness.
**Why it happens:** Multiple files, multiple branches in `apply_wizard_result_to_db`.
**How to avoid:** Systematic checklist -- the plan must enumerate all 7 locations and verify each one.
**Warning signs:** Test for each hook location independently (as `test_staleness.py` does for breakdown).

### Pitfall 2: Forgetting the Guard Condition
**What goes wrong:** `_mark_shotlist_stale` fires even when no shots exist, creating confusing staleness state.
**Why it happens:** Copy-paste from breakdown pattern without adapting the guard.
**How to avoid:** The guard must check `Shot` existence (not `BreakdownElement`).
**Warning signs:** New projects with no shots showing stale banner.

### Pitfall 3: Double Commit in list_items.py
**What goes wrong:** The existing `list_items.py` pattern commits BEFORE checking `_is_scene_item`, then commits AGAIN. Adding `_is_character_item` with another commit could cause issues.
**Why it happens:** The existing code has a subtle pattern where the main operation commits first, then staleness is set in a second commit.
**How to avoid:** Add the character check alongside the scene check, using the same commit pattern. Do NOT add a third commit.
**Warning signs:** Transaction errors or partial updates.

### Pitfall 4: Cache Invalidation on Frontend
**What goes wrong:** Banner appears but doesn't disappear after user acknowledges or takes action.
**Why it happens:** React Query cache for the staleness endpoint isn't invalidated.
**How to avoid:** Invalidate the staleness query key on dismiss/acknowledge action.
**Warning signs:** Stale banner persists after dismissal.

### Pitfall 5: `_is_character_item` Also Needs Shotlist Staleness for Scene Items
**What goes wrong:** Scene list item changes trigger `_mark_breakdown_stale` but NOT `_mark_shotlist_stale`, even though scene changes affect shotlists too (shots are grouped by scene).
**Why it happens:** Only adding character detection, forgetting that scene changes also affect the shotlist.
**How to avoid:** At all 6 mutation locations (1-6 in the hook table), add `_mark_shotlist_stale` -- not just at character-item locations. Scene changes already trigger breakdown_stale and should also trigger shotlist_stale.
**Warning signs:** Scene edits don't show staleness banner in breakdown mode.

## Code Examples

### Backend: _mark_shotlist_stale function

```python
# In phase_data.py, right after _mark_breakdown_stale:

SHOTLIST_SENSITIVE_PHASES = {"write", "scenes"}  # Same as BREAKDOWN_SENSITIVE_PHASES

def _mark_shotlist_stale(db: Session, project_id) -> None:
    """Set shotlist_stale=True if shots exist for this project.

    Does not commit -- caller's existing commit covers the change.
    Only marks stale when at least one Shot exists.
    """
    has_shots = db.query(database.Shot).filter(
        database.Shot.project_id == str(project_id),
    ).first() is not None
    if has_shots:
        project = db.query(database.Project).filter(
            database.Project.id == str(project_id)
        ).first()
        if project:
            project.shotlist_stale = True
```

### Backend: Hook co-location in phase_data.py PATCH

```python
# In update_subsection_data(), after existing breakdown hook:
if phase in BREAKDOWN_SENSITIVE_PHASES:
    _mark_breakdown_stale(db, project_id)
if phase in SHOTLIST_SENSITIVE_PHASES:
    _mark_shotlist_stale(db, project_id)
```

### Backend: Hook co-location in wizards.py

```python
# Import both in wizards.py:
from .phase_data import _mark_breakdown_stale, _mark_shotlist_stale

# In script_writer_wizard branch (line ~274):
_mark_breakdown_stale(db, project.id)
_mark_shotlist_stale(db, project.id)

# In scene_wizard branch (line ~317):
_mark_breakdown_stale(db, project.id)
_mark_shotlist_stale(db, project.id)
```

### Backend: Character and scene item detection in list_items.py

```python
from .phase_data import _mark_breakdown_stale, _mark_shotlist_stale

def _is_character_item(db: Session, phase_data_id) -> database.PhaseData | None:
    """Return PhaseData if it represents story.characters, else None."""
    pd = db.query(database.PhaseData).filter(
        database.PhaseData.id == str(phase_data_id)
    ).first()
    if pd and str(pd.phase) == "story" and pd.subsection_key == "characters":
        return pd
    return None

# In create_list_item, after existing scene check:
scene_pd = _is_scene_item(db, phase_data_id)
if scene_pd:
    _mark_breakdown_stale(db, scene_pd.project_id)
    _mark_shotlist_stale(db, scene_pd.project_id)
    db.commit()

char_pd = _is_character_item(db, phase_data_id)
if char_pd:
    _mark_shotlist_stale(db, char_pd.project_id)
    db.commit()
```

### Backend: Shotlist status endpoint

```python
# In shots.py:
@router.get("/{project_id}/status")
async def get_shotlist_status(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get shotlist staleness status and shot count."""
    project = _verify_project_ownership(db, project_id, current_user.id)
    shot_count = db.query(database.Shot).filter(
        database.Shot.project_id == str(project_id)
    ).count()
    return {
        "shotlist_stale": project.shotlist_stale or False,
        "shot_count": shot_count,
    }
```

### Backend: Dismiss staleness endpoint

```python
# In shots.py:
@router.post("/{project_id}/acknowledge-stale")
async def acknowledge_shotlist_stale(
    project_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear shotlist_stale flag (user acknowledged the staleness)."""
    project = _verify_project_ownership(db, project_id, current_user.id)
    project.shotlist_stale = False
    db.commit()
    return {"status": "success"}
```

### Frontend: ShotlistStalenessBar component

```tsx
// ShotlistStalenessBar.tsx
import { AlertTriangle, X } from 'lucide-react';

interface ShotlistStalenessBarProps {
  onDismiss: () => void;
  isPending: boolean;
}

export function ShotlistStalenessBar({ onDismiss, isPending }: ShotlistStalenessBarProps) {
  return (
    <div className="flex items-center justify-between px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 flex-shrink-0">
      <div className="flex items-center gap-2 text-xs text-amber-400">
        <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
        <span>Shotlist may be outdated -- script has changed since shots were last reviewed.</span>
      </div>
      <button
        onClick={onDismiss}
        disabled={isPending}
        className="p-1 text-amber-400/60 hover:text-amber-400 transition-colors flex-shrink-0 ml-3"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
```

### Frontend: Integration in BreakdownLayout.tsx

```tsx
// In BreakdownLayout, add query for shotlist status:
const { data: shotlistStatus } = useQuery({
  queryKey: ['shotlist-status', projectId],
  queryFn: () => api.getShotlistStatus(projectId!),
  enabled: !!projectId,
  staleTime: 30_000,
});

// In center panel, above ShotlistPanel:
{shotlistStatus?.shotlist_stale && shotlistStatus.shot_count > 0 && (
  <ShotlistStalenessBar
    onDismiss={() => dismissMutation.mutate()}
    isPending={dismissMutation.isPending}
  />
)}
<ShotlistPanel />
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A | `breakdown_stale` boolean + StalenessBar | v2.0 Phase 12 (2026-03-14) | Proven pattern for staleness UX |
| N/A | `shotlist_stale` column exists but unwired | v3.0 Phase 17 (2026-03-19) | Column ready, hooks needed |

**No deprecated/outdated concerns** -- this phase simply wires an existing, proven pattern.

## Open Questions

1. **Should the dismiss/acknowledge endpoint exist, or should staleness only clear on regeneration?**
   - What we know: v2.0 breakdown clears staleness on re-extraction (automated). Shotlist has no auto-regeneration yet (deferred to v3.1 AUTO-01).
   - What's unclear: If there's no regeneration, how does the user clear the stale flag?
   - Recommendation: Provide a dismiss button that calls `acknowledge-stale` endpoint. When AUTO-01 ships in v3.1, regeneration will also clear the flag. This gives the user control now without waiting for the v3.1 feature.

2. **Should `_mark_shotlist_stale` use the same `BREAKDOWN_SENSITIVE_PHASES` set or its own?**
   - What we know: Both breakdown and shotlist depend on the same script content (write/scenes phases).
   - What's unclear: Whether future phases might differ.
   - Recommendation: Use a separate `SHOTLIST_SENSITIVE_PHASES` constant even though it will have the same values. This keeps the two concerns independent.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | backend/app/tests/conftest.py |
| Quick run command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_shotlist_staleness.py -x` |
| Full suite command | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-01 | PATCH write phase sets shotlist_stale=True | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_patch_write_phase_sets_shotlist_stale -x` | Wave 0 |
| SYNC-01 | PATCH scenes phase sets shotlist_stale=True | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_patch_scenes_phase_sets_shotlist_stale -x` | Wave 0 |
| SYNC-01 | script_writer_wizard sets shotlist_stale=True | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_script_wizard_sets_shotlist_stale -x` | Wave 0 |
| SYNC-01 | scene_wizard sets shotlist_stale=True | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_scene_wizard_sets_shotlist_stale -x` | Wave 0 |
| SYNC-01 | No shots = no stale flag set | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_no_stale_without_shots -x` | Wave 0 |
| SYNC-02 | ShotlistStalenessBar renders in breakdown mode | manual-only | Visual check: banner appears when shotlist_stale=True | N/A |
| SYNC-03 | Create/update/delete character item sets shotlist_stale | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_create_character_sets_shotlist_stale -x` | Wave 0 |
| SYNC-04 | Scene item CRUD sets shotlist_stale (same as breakdown locations) | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_create_scene_sets_shotlist_stale -x` | Wave 0 |
| SYNC-04 | Acknowledge-stale endpoint clears flag | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_acknowledge_clears_stale -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_shotlist_staleness.py -x`
- **Per wave merge:** `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_shotlist_staleness.py` -- covers SYNC-01, SYNC-03, SYNC-04 (modeled on existing `test_staleness.py`)
- [ ] No framework install needed -- pytest already configured
- [ ] No conftest changes needed -- existing fixtures (client, db_session, mock_auth_headers) cover all test needs

## Sources

### Primary (HIGH confidence)
- `backend/app/api/endpoints/phase_data.py` -- existing `_mark_breakdown_stale` function and `BREAKDOWN_SENSITIVE_PHASES` constant (lines 16-35)
- `backend/app/api/endpoints/wizards.py` -- existing hook calls at lines 274 and 317
- `backend/app/api/endpoints/list_items.py` -- existing `_is_scene_item` and hook calls at lines 113-114, 143-144, 163-165
- `backend/app/tests/test_staleness.py` -- complete test pattern for breakdown staleness (8 test cases)
- `frontend/src/components/Breakdown/StalenessBar.tsx` -- existing banner component (30 lines)
- `frontend/src/components/Breakdown/BreakdownPage.tsx` -- existing staleness banner integration (lines 69-71)
- `backend/app/models/database.py:100` -- `shotlist_stale = Column(Boolean, default=False)` already exists
- `.planning/RETROSPECTIVE.md` -- staleness flag + banner pattern documented as established pattern

### Secondary (MEDIUM confidence)
- `.planning/research/FEATURES.md` -- staleness pattern documented in feature landscape

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, exact mirror of v2.0 pattern
- Architecture: HIGH -- all 7 hook locations identified from direct code inspection
- Pitfalls: HIGH -- v2.0 Phase 16 bug (missed scene_wizard hook) is documented and informs the systematic approach
- Frontend: HIGH -- StalenessBar.tsx is 30 lines, BreakdownLayout integration point is clear

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable -- internal codebase pattern, no external dependency concerns)
