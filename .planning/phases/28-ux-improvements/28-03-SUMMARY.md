---
plan: 28-03
phase: 28-ux-improvements
status: complete
completed: 2026-03-21
---

# Plan 28-03: Scene Reorder Staleness Fix

## Objective
Fix the known tech-debt gap: reordering scenes does not flag the shotlist as stale.

## What Was Built

Single backend change in `backend/app/api/endpoints/list_items.py`:

After the existing `db.commit()` in `reorder_list_items`, added:
```python
scene_pd = _is_scene_item(db, phase_data_id)
if scene_pd:
    _mark_shotlist_stale(db, scene_pd.project_id)
    db.commit()
```

This reuses the same helpers (`_is_scene_item`, `_mark_shotlist_stale`) already used in the delete handler. Only `_mark_shotlist_stale` is called — not `_mark_breakdown_stale` — because scene ordering does not affect element extraction (characters, locations, etc. are scene-independent).

## Key Files Modified

- `backend/app/api/endpoints/list_items.py` — staleness check added to reorder_list_items

## Commits

- `05dd613`: fix(28-03): mark shotlist stale on scene reorder

## Self-Check: PASSED

- reorder_list_items now calls _mark_shotlist_stale after db.commit ✓
- Only shotlist staleness flagged (not breakdown staleness) ✓
- Closes tech-debt gap noted in PROJECT.md ✓
