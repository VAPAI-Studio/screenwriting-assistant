# Phase 12: Staleness Hooks - Research

**Researched:** 2026-03-13
**Domain:** Backend staleness detection / cross-cutting side-effects on save and generate
**Confidence:** HIGH

## Summary

Phase 12 implements the "staleness hooks" that automatically mark a project's breakdown as stale when screenplay content changes, and clear that flag when a new extraction completes. This is a purely backend phase touching 4 existing files with surgical additions -- no new files, no new API endpoints, no frontend changes, no new dependencies.

The `breakdown_stale` boolean column already exists on the Project model (added in Phase 9, BKDN-04). The summary endpoint already reads and returns this flag (API-07). The only missing pieces are the side-effects that SET the flag to `true` (on content saves and scene mutations) and CLEAR it to `false` (on successful extraction).

**Primary recommendation:** Add a reusable helper function `_mark_breakdown_stale(db, project_id)` that checks for an existing breakdown (at least one non-deleted BreakdownElement) before setting the flag, then call it from 3 trigger points: phase_data PATCH, `apply_wizard_result_to_db()`, and list_items CRUD. Clear the flag in `BreakdownService.extract()` after successful commit.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNC-03 | Saving screenplay content or regenerating scenes sets `breakdown_stale=true` on the project | Trigger points identified: `phase_data.update_subsection_data()` for write/scenes phases, `wizards.apply_wizard_result_to_db()` for script_writer_wizard, `list_items.create_list_item()` / `update_list_item()` / `delete_list_item()` for scene ListItems |
| SYNC-04 | Re-extraction clears the stale flag and creates a new `breakdown_runs` audit record | `BreakdownService.extract()` already creates audit records; add `project.breakdown_stale = False` before the final `db.commit()` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API endpoints being modified | Already in place |
| SQLAlchemy | existing | ORM queries for Project model | Already in place |

### Supporting
No new libraries needed. This phase only adds logic to existing files.

## Architecture Patterns

### Recommended Project Structure (files to modify)
```
backend/app/
  api/endpoints/
    phase_data.py         # Add staleness hook to PATCH endpoint
    list_items.py         # Add staleness hook to create/update/delete endpoints
    wizards.py            # Add staleness hook to apply_wizard_result_to_db()
  services/
    breakdown_service.py  # Clear stale flag on successful extract()
```

### Pattern 1: Reusable Staleness Helper
**What:** A shared helper function that checks for breakdown existence and sets the flag
**When to use:** Called from every trigger point to avoid duplicated logic
**Example:**
```python
# Source: Project codebase convention (see _verify_project_ownership patterns)
def _mark_breakdown_stale(db: Session, project_id) -> None:
    """Set breakdown_stale=True if a breakdown exists for this project.

    Only sets the flag when at least one non-deleted BreakdownElement exists,
    preventing false staleness on projects that have never been extracted.
    """
    has_breakdown = db.query(BreakdownElement).filter(
        BreakdownElement.project_id == str(project_id),
        BreakdownElement.is_deleted == False,
    ).first() is not None

    if has_breakdown:
        db.query(Project).filter(
            Project.id == str(project_id)
        ).update({"breakdown_stale": True})
```

### Pattern 2: Phase/Subsection Guard for phase_data PATCH
**What:** Only trigger staleness for phases that affect screenplay content (write, scenes)
**When to use:** In `update_subsection_data()` -- not all phase_data saves invalidate the breakdown
**Example:**
```python
# In phase_data.py update_subsection_data():
BREAKDOWN_SENSITIVE_PHASES = {"write", "scenes"}

# After existing commit:
if phase in BREAKDOWN_SENSITIVE_PHASES:
    _mark_breakdown_stale(db, project_id)
    # No extra commit needed if done before existing commit,
    # or call db.commit() if done after
```

### Pattern 3: Wizard-Type Guard for apply_wizard_result_to_db
**What:** Only the `script_writer_wizard` type invalidates the breakdown
**When to use:** In `apply_wizard_result_to_db()` after the commit for script_writer_wizard
**Example:**
```python
# In wizards.py apply_wizard_result_to_db(), inside the script_writer_wizard branch:
# After db.commit()
_mark_breakdown_stale(db, project.id)
db.commit()
```

### Pattern 4: Scene ListItem Guard for list_items
**What:** Only scene ListItems invalidate the breakdown (not characters, episodes, etc.)
**When to use:** In create/update/delete endpoints, after determining the item is a scene
**Example:**
```python
# The item_type field on ListItem tells us if it's a scene.
# But more reliably: check the phase_data's phase (scenes) or subsection_key (scene_list).
# The _verify_phase_data_ownership already loads the PhaseData.
# Extend to return project too, then check the phase.
```

### Anti-Patterns to Avoid
- **Triggering on every phase_data save:** Idea phase or story phase saves do NOT affect the screenplay breakdown. Only write and scenes phases matter.
- **Setting stale without checking breakdown exists:** Projects without any breakdown should not have `breakdown_stale=True` -- it would confuse the frontend into showing a "refresh" banner for a non-existent breakdown.
- **Multiple commits in a single endpoint:** Where possible, set `breakdown_stale` before the existing `db.commit()` rather than adding a second commit. This keeps the operation atomic.
- **Circular staleness:** Do NOT set stale when extraction itself creates/updates elements. The stale flag should only respond to USER-initiated content changes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Breakdown existence check | Custom query per trigger point | Shared `_mark_breakdown_stale()` helper | DRY -- 4 trigger points would duplicate 5 lines each |
| Project lookup from ListItem | Navigate relationships manually | Leverage existing `_verify_phase_data_ownership` which already loads PhaseData -> Project | Already verified in every list_items endpoint |

## Common Pitfalls

### Pitfall 1: Setting Stale After Commit (Transaction Boundary)
**What goes wrong:** If you set `breakdown_stale = True` AFTER `db.commit()`, you need a second commit, creating a window where the save succeeded but staleness wasn't recorded.
**Why it happens:** Easy to add the hook as an afterthought at the end of the function.
**How to avoid:** Set the flag BEFORE the existing `db.commit()` where possible. In `apply_wizard_result_to_db`, this is straightforward since the project object is already loaded.
**Warning signs:** Two `db.commit()` calls in a single code path.

### Pitfall 2: Stale Flag on Projects Without Breakdowns
**What goes wrong:** A project that has never been extracted shows a "refresh breakdown" banner in the UI.
**Why it happens:** Setting `breakdown_stale=True` unconditionally on every content save.
**How to avoid:** Check that at least one non-deleted BreakdownElement exists before setting the flag. The check is fast (single indexed query with LIMIT 1 via `.first()`).
**Warning signs:** `breakdown_stale=True` on projects where the summary endpoint returns `total_elements=0` and `last_run=null`.

### Pitfall 3: Scene vs Non-Scene ListItems
**What goes wrong:** Editing a character ListItem triggers breakdown staleness.
**Why it happens:** Not filtering by phase/subsection when hooking into list_items endpoints.
**How to avoid:** Check that the ListItem belongs to a PhaseData with `phase="scenes"` and `subsection_key="scene_list"` before marking stale. The PhaseData is already loaded by `_verify_phase_data_ownership`.
**Warning signs:** Staleness triggered when editing idea-phase or story-phase list items.

### Pitfall 4: Missing str() Casts for UUID Filters
**What goes wrong:** SQLAlchemy filters fail silently or return no results on SQLite test DB.
**Why it happens:** PostgreSQL UUIDs and SQLite String(36) columns handle UUID objects differently.
**How to avoid:** Always cast UUID values to `str()` in filter queries, per project convention (Phase 10 decision).
**Warning signs:** Tests pass with no assertion errors but staleness flag never gets set.

### Pitfall 5: Forgetting YOLO Path Through apply_wizard_result_to_db
**What goes wrong:** YOLO auto-generation of screenplays doesn't trigger staleness.
**Why it happens:** YOLO calls `apply_wizard_result_to_db` from `ai_chat.py` (line 956), so the hook inside `apply_wizard_result_to_db` covers both manual and YOLO paths.
**How to avoid:** Put the staleness hook inside `apply_wizard_result_to_db()` itself, not in the `apply_wizard_results` endpoint handler. This ensures both the `/wizards/{run_id}/apply` endpoint AND the YOLO `_yolo_run_wizard` path trigger it.
**Warning signs:** Manual wizard apply sets stale but YOLO fill does not.

## Code Examples

### Trigger Point 1: phase_data PATCH (update_subsection_data)
```python
# backend/app/api/endpoints/phase_data.py
# Add import at top:
from ...models.database import BreakdownElement

BREAKDOWN_SENSITIVE_PHASES = {"write", "scenes"}

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

# In update_subsection_data(), before db.commit():
if phase in BREAKDOWN_SENSITIVE_PHASES:
    _mark_breakdown_stale(db, project_id)
```

### Trigger Point 2: apply_wizard_result_to_db (script_writer_wizard)
```python
# backend/app/api/endpoints/wizards.py
# Inside the script_writer_wizard branch, before db.commit():
from ...models.database import BreakdownElement

# Before the final db.commit() in the script_writer_wizard block:
_mark_breakdown_stale(db, project.id)
```

### Trigger Point 3: list_items create/update/delete (scene items only)
```python
# backend/app/api/endpoints/list_items.py
# Modify _verify_phase_data_ownership to also return the phase_data object
# (it already does). Use it to check if this is a scenes phase.

def _is_scene_item(db: Session, phase_data_id: UUID) -> bool:
    """Check if a phase_data represents scenes (scene_list subsection)."""
    pd = db.query(database.PhaseData).filter(
        database.PhaseData.id == str(phase_data_id)
    ).first()
    return pd is not None and pd.phase in ("scenes",) and pd.subsection_key == "scene_list"

# In create_list_item, after db.commit():
phase_data = _verify_phase_data_ownership(db, phase_data_id, current_user.id)
# ... existing create logic ...
if _is_scene_item(db, phase_data_id):
    _mark_breakdown_stale(db, phase_data.project_id)
```

### Trigger Point 4: BreakdownService.extract() -- clear stale flag (SYNC-04)
```python
# backend/app/services/breakdown_service.py
# In extract(), after recording the run and before db.commit():

# 6b. Clear staleness flag (SYNC-04)
project = db.query(database.Project).filter(
    database.Project.id == str(project_id)
).first()
if project:
    project.breakdown_stale = False

# 7. Single commit
db.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| breakdown_stale column exists but is never set | Phase 12 adds hooks to set/clear it | Phase 12 | Enables frontend staleness banner (Phase 13 UI-06) |

**No deprecated/outdated concerns** -- this is all internal application logic.

## Open Questions

1. **Should the helper be a standalone utility or duplicated per-file?**
   - What we know: 4 trigger points across 4 files need the same logic
   - What's unclear: Whether to put the helper in a shared utils module or duplicate in each file
   - Recommendation: Create a shared helper in a utils or services module (e.g., `breakdown_service.py` or a new `staleness.py` utility) and import it. Alternatively, since the helper is only ~8 lines, inlining in each file is acceptable for this project's scale.

2. **Exact behavior of "when a breakdown exists" guard**
   - What we know: Success criterion #1 says "when a breakdown exists"
   - What's unclear: Does "exists" mean at least one BreakdownElement, or at least one completed BreakdownRun?
   - Recommendation: Check for at least one non-deleted BreakdownElement. This is more reliable because a run could have completed with 0 elements extracted (empty screenplay), and we don't want to set stale in that edge case either.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with async support via pytest-asyncio) |
| Config file | `backend/pytest.ini` or pyproject.toml (session-scoped SQLite engine in conftest.py) |
| Quick run command | `cd backend && python -m pytest app/tests/test_staleness.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-03a | PATCH phase_data for write phase sets breakdown_stale=true when breakdown exists | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_write_phase_sets_stale -x` | Wave 0 |
| SYNC-03b | PATCH phase_data for scenes phase sets breakdown_stale=true when breakdown exists | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_scenes_phase_sets_stale -x` | Wave 0 |
| SYNC-03c | PATCH phase_data for idea/story phase does NOT set breakdown_stale | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_non_write_phase_no_stale -x` | Wave 0 |
| SYNC-03d | apply_wizard_result_to_db for script_writer_wizard sets breakdown_stale=true | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_script_wizard_sets_stale -x` | Wave 0 |
| SYNC-03e | Creating a scene ListItem sets breakdown_stale=true | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_create_scene_sets_stale -x` | Wave 0 |
| SYNC-03f | Updating a scene ListItem sets breakdown_stale=true | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_update_scene_sets_stale -x` | Wave 0 |
| SYNC-03g | Deleting a scene ListItem sets breakdown_stale=true | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_delete_scene_sets_stale -x` | Wave 0 |
| SYNC-03h | No stale flag set when no breakdown exists | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_no_stale_without_breakdown -x` | Wave 0 |
| SYNC-04a | Successful extraction clears breakdown_stale to false | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_extraction_clears_stale -x` | Wave 0 |
| SYNC-04b | Successful extraction creates breakdown_runs audit record | integration | Already covered by `test_breakdown_service.py::TestBreakdownService::test_extraction_produces_elements` | Exists |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_staleness.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_staleness.py` -- new test file covering SYNC-03 and SYNC-04
- [ ] No framework install needed -- pytest already configured
- [ ] No conftest changes needed -- existing fixtures sufficient

## Sources

### Primary (HIGH confidence)
- Project codebase: `backend/app/models/database.py` -- Project.breakdown_stale column (line 99)
- Project codebase: `backend/app/api/endpoints/phase_data.py` -- PATCH endpoint (line 150)
- Project codebase: `backend/app/api/endpoints/wizards.py` -- `apply_wizard_result_to_db()` (line 178)
- Project codebase: `backend/app/api/endpoints/list_items.py` -- CRUD endpoints (lines 69-134)
- Project codebase: `backend/app/services/breakdown_service.py` -- `extract()` method (line 412)
- Project codebase: `backend/app/api/endpoints/ai_chat.py` -- YOLO path calling `apply_wizard_result_to_db` (line 956)
- Project codebase: `backend/app/api/endpoints/breakdown.py` -- summary endpoint reading stale flag (line 285)

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` -- SYNC-03, SYNC-04 requirement definitions
- `.planning/STATE.md` -- Project decisions including staleness design

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, purely existing codebase modifications
- Architecture: HIGH -- all trigger points identified by reading existing code; patterns follow established project conventions
- Pitfalls: HIGH -- identified from codebase analysis (UUID casting, transaction boundaries, YOLO path)

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable -- internal application logic, no external dependency changes)
