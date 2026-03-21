---
phase: 28-ux-improvements
verified: 2026-03-21T00:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 28: UX Improvements Verification Report

**Phase Goal:** Users can delete media assets, reorder shots by dragging, and scene reordering correctly flags the shotlist as stale
**Verified:** 2026-03-21
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Each expanded asset card shows a delete button on each media item | VERIFIED | `MediaThumbnail.tsx` renders `onDelete` overlay (Trash2 button, absolute top-right, hover-visible) on both image and error/fallback states; `AssetElementCard.tsx` passes `onDelete` to every `<MediaThumbnail>` |
| 2  | Clicking delete shows a confirmation prompt before removing | VERIFIED | `handleDeleteMedia` in `AssetElementCard.tsx` line 36: `if (!window.confirm(...)) return;` |
| 3  | Confirmed deletion removes the media item from the UI and calls the backend | VERIFIED | `deleteMutation` calls `api.deleteMedia(projectId, mediaId)` on confirm; `onSuccess` invalidates `QUERY_KEYS.ELEMENT_MEDIA(element.id)` triggering re-fetch |
| 4  | After deletion the element's media list refreshes and the deleted item is gone | VERIFIED | `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.ELEMENT_MEDIA(element.id) })` in mutation `onSuccess` — cache bust forces re-render without deleted item |
| 5  | Shots within a scene group can be reordered by dragging a drag handle | VERIFIED | `SceneGroup.tsx` wraps each shot in `<Draggable>` with `<GripVertical>` drag handle using `dragHandleProps`; `@hello-pangea/dnd` installed at `^18.0.1` |
| 6  | Arrow up/down buttons (ReorderControls) are removed from the action cell | VERIFIED | `ReorderControls` is absent from both `ShotlistPanel.tsx` and `SceneGroup.tsx` (grep confirms zero occurrences); `handleMoveShot` also removed |
| 7  | After dragging, the new sort_order is persisted to the backend and survives page refresh | VERIFIED | `handleReorderGroup` in `ShotlistPanel.tsx` lines 252-258 builds `{id, sort_order}[]` from drop position index and calls `reorderMutation.mutate(items)` with optimistic update |
| 8  | Drag is scoped within a scene group — shots cannot be dragged between scenes | VERIFIED | Each `<SceneGroup>` has its own `<DragDropContext>` + `<Droppable droppableId={droppableId}>` wrapper — DnD contexts are independent so cross-group drag is not possible |
| 9  | Reordering scenes in the script editor marks the shotlist stale | VERIFIED | `reorder_list_items` in `list_items.py` lines 220-223: calls `_is_scene_item(db, phase_data_id)` then `_mark_shotlist_stale(db, scene_pd.project_id)` + `db.commit()` |
| 10 | The staleness flag follows the same pattern as scene add/edit/delete already do | VERIFIED | Pattern matches `create_list_item` (line 125-129), `update_list_item` (line 161-165), and `delete_list_item` (line 188-192) — identical `_is_scene_item` + `_mark_shotlist_stale` guard |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/Breakdown/MediaThumbnail.tsx` | Optional `onDelete` prop renders trash icon overlay | VERIFIED | Lines 8, 19-29, 43-53 — overlay rendered in both image and fallback states, `relative group` on container, `opacity-0 group-hover:opacity-100` |
| `frontend/src/components/Breakdown/AssetElementCard.tsx` | `useMutation` calling `api.deleteMedia`, `window.confirm` guard, cache invalidation | VERIFIED | Lines 28-38 — `deleteMutation` with `api.deleteMedia`, `handleDeleteMedia` with `window.confirm`, `onSuccess` invalidates `ELEMENT_MEDIA` query key |
| `frontend/src/components/Breakdown/SceneGroup.tsx` | `DragDropContext` + `SortableContext` wrapping shot rows | VERIFIED | Lines 1, 52-90 — `DragDropContext onDragEnd={handleDragEnd}`, `Droppable`, `Draggable` per shot with `GripVertical` handle |
| `frontend/src/components/Breakdown/ShotlistPanel.tsx` | `onReorderGroup` handler passed to SceneGroup; `ReorderControls` import removed | VERIFIED | Lines 252-258: `handleReorderGroup` callback; line 363: `onReorderGroup={handleReorderGroup}` on `<SceneGroup>`; no `ReorderControls` import anywhere |
| `backend/app/api/endpoints/list_items.py` | `reorder_list_items` calls `_mark_shotlist_stale` when reordering scene_list items | VERIFIED | Lines 220-223: `scene_pd = _is_scene_item(db, phase_data_id)` → `_mark_shotlist_stale(db, scene_pd.project_id)` → `db.commit()` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `AssetElementCard.tsx deleteMutation` | `api.deleteMedia(projectId, mediaId)` | `useMutation` mutationFn | WIRED | Line 29: `mutationFn: (mediaId: string) => api.deleteMedia(projectId, mediaId)` |
| `deleteMutation.onSuccess` | `queryClient.invalidateQueries` | `QUERY_KEYS.ELEMENT_MEDIA(element.id)` | WIRED | Lines 30-32: `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.ELEMENT_MEDIA(element.id) })` |
| `SceneGroup DragDropContext onDragEnd` | `ShotlistPanel.handleReorderGroup` | `onReorderGroup` prop callback | WIRED | `SceneGroup.tsx` line 35: `onReorderGroup?.(group.sceneItemId, reordered.map(s => s.id))`; `ShotlistPanel.tsx` line 363: `onReorderGroup={handleReorderGroup}` |
| `ShotlistPanel.handleReorderGroup` | `api.reorderShots` | `reorderMutation.mutate` with `{id, sort_order}[]` payload | WIRED | Lines 254-255: `const items = orderedShotIds.map((id, idx) => ({ id, sort_order: idx })); reorderMutation.mutate(items)` |
| `reorder_list_items endpoint` | `_mark_shotlist_stale(db, scene_pd.project_id)` | `_is_scene_item(db, phase_data_id)` check | WIRED | Lines 220-223 of `list_items.py` — guard + call present after `db.commit()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MDIA-01 | 28-01-PLAN.md | User can delete an uploaded media asset from the assets panel | SATISFIED | `deleteMutation` in `AssetElementCard.tsx` calls `api.deleteMedia`; `window.confirm` guard; cache invalidated on success |
| SMGT-01 | 28-02-PLAN.md | User can reorder shots via drag-and-drop within the shotlist panel (replacing existing arrow buttons) | SATISFIED | `@hello-pangea/dnd` installed; `SceneGroup.tsx` implements `DragDropContext`+`Droppable`+`Draggable`; `ReorderControls` removed; `handleReorderGroup` persists order to backend |
| SYNC-01 | 28-03-PLAN.md | Reordering scenes in the screenplay marks the shotlist as stale | SATISFIED | `reorder_list_items` in `list_items.py` now calls `_mark_shotlist_stale` via `_is_scene_item` check; closes tech-debt gap noted in PROJECT.md |

**Orphaned requirements:** None. All three IDs mapped to Phase 28 in REQUIREMENTS.md are claimed by plans 28-01, 28-02, 28-03 respectively.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `SceneGroup.tsx` | 86 | `{provided.placeholder}` | Info | Required `@hello-pangea/dnd` DnD placeholder node — NOT a stub; necessary for correct drag animation |

No blockers. No warnings. The single "placeholder" occurrence is the DnD library's required slot element.

---

### Human Verification Required

#### 1. Delete confirmation flow

**Test:** Open Breakdown mode, expand an asset card with at least one image. Hover over the thumbnail — trash icon should appear in top-right corner. Click it.
**Expected:** Browser `window.confirm` dialog appears with `Delete "<filename>"? This cannot be undone.` message. Cancelling does nothing. Confirming removes the item from the grid and triggers `DELETE /api/media/{projectId}/{mediaId}`.
**Why human:** `window.confirm` behavior and visual hover-opacity cannot be verified programmatically.

#### 2. Drag-and-drop shot reorder

**Test:** Open Breakdown mode with an existing shotlist. Grab the `GripVertical` handle on a shot row and drag it to a different position within the same scene group.
**Expected:** Shot snaps to new position immediately (optimistic update). Refreshing the page preserves the new order. No up/down arrow buttons are visible anywhere.
**Why human:** Drag interaction, visual smoothness, and cross-page persistence require browser interaction.

#### 3. Scene reorder triggers staleness banner

**Test:** In Script (editor) mode, go to the Scenes phase and drag two scenes to swap their order. Then switch to Breakdown mode and open the Shotlist panel.
**Expected:** Amber staleness banner appears. Clicking "Acknowledge" dismisses it.
**Why human:** Requires cross-mode interaction spanning editor and breakdown views.

---

### Gaps Summary

No gaps. All 10 observable truths are verified, all 5 artifacts pass all three levels (exists, substantive, wired), all 5 key links are wired, and all 3 requirements are satisfied. The three commits (973c1cf, 3540f57, 05dd613) are confirmed present in git history.

---

_Verified: 2026-03-21_
_Verifier: Claude (gsd-verifier)_
