---
plan: 28-02
phase: 28-ux-improvements
status: complete
completed: 2026-03-21
---

# Plan 28-02: Drag-and-Drop Shot Reorder

## Objective
Replace the arrow-button shot reorder controls with drag-and-drop using @hello-pangea/dnd.

## What Was Built

Replaced arrow-button `ReorderControls` with smooth drag-and-drop within scene groups:

- **Installed `@hello-pangea/dnd`**: React 18 compatible maintained fork of react-beautiful-dnd.

- **SceneGroup.tsx rewritten**: Added `DragDropContext` + `Droppable` per scene group (droppableId = sceneItemId or 'unassigned'). Each shot wrapped in `Draggable` with `GripVertical` icon as the drag handle (using `dragHandleProps`). `handleDragEnd` reorders the sorted array and calls new `onReorderGroup` prop with the updated shot ID order.

- **ShotlistPanel.tsx updated**: Removed `ReorderControls` import and `handleMoveShot` handler. Added `handleReorderGroup` callback that builds `{id, sort_order}[]` from array position index and fires existing `reorderMutation`. Passes `onReorderGroup={handleReorderGroup}` to each `<SceneGroup>`. `renderActionCell` now only contains `<DeleteShotButton>`.

Drag is scoped per scene group — shots cannot cross scene boundaries. New sort_order persists to backend via existing reorder endpoint and survives page refresh.

## Key Files Modified

- `frontend/src/components/Breakdown/SceneGroup.tsx` — DragDropContext + Droppable + Draggable + GripVertical handle
- `frontend/src/components/Breakdown/ShotlistPanel.tsx` — ReorderControls removed, handleReorderGroup added
- `frontend/package.json` — @hello-pangea/dnd added

## Commits

- `3540f57`: feat(28-02): replace arrow-button reorder with drag-and-drop using @hello-pangea/dnd

## Self-Check: PASSED

- @hello-pangea/dnd installed and used ✓
- ReorderControls no longer imported or rendered ✓
- handleMoveShot removed ✓
- onReorderGroup wired to reorderMutation ✓
- Build passes with no new TypeScript errors ✓
