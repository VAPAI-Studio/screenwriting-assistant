---
plan: 30-02
phase: 30-storyboard-grid-ui
status: complete
completed: 2026-03-21
---

# Plan 30-02: FrameGalleryModal + StoryboardView Wiring

## What Was Built

- **FrameGalleryModal** (`frontend/src/components/Storyboard/FrameGalleryModal.tsx`):
  - Radix Dialog (`@radix-ui/react-dialog`) following AddElementDialog.tsx pattern
  - Props: `shot`, `projectId`, `sceneLabel`, `open`, `onOpenChange`
  - Queries: `useQuery(QUERY_KEYS.STORYBOARD_FRAMES(shot.id))` with `enabled: open`
  - Mutations: upload (`api.uploadFrame`), select (`api.updateFrame`), delete (`api.deleteFrame`)
  - All mutations invalidate `STORYBOARD_FRAMES(shot.id)` on success
  - Hidden file input (`accept="image/jpeg,image/png,image/webp"`) triggered by Upload button
  - Frame grid: `border-primary` ring on selected frames, Check badge with "Selected" text
  - Hover overlay: "Select" button (hidden if already selected), red "Delete" button
  - `window.confirm` before delete
  - Disabled "Generate with AI" button with `title="Coming in Phase 31"`
  - Upload error display below gallery
  - Empty state: Image icon + "No frames yet" + "Upload or generate" hint

- **StoryboardView updates** (`frontend/src/components/Storyboard/StoryboardView.tsx`):
  - Added `import { FrameGalleryModal } from './FrameGalleryModal'`
  - `selectedShot` derived: `shots.find(s => s.id === selectedShotId) ?? null`
  - `selectedShotSceneLabel` derived: finds group containing selected shot
  - `FrameGalleryModal` renders conditionally when `selectedShot` is truthy
  - `onOpenChange` handler clears `selectedShotId` when modal closes

## Commits

- `fa69eb5`: feat(30-02): FrameGalleryModal with upload, select, delete; wire to StoryboardView

## Self-Check: PASSED

- FrameGalleryModal uses Radix Dialog pattern ✓
- `useQuery` with `QUERY_KEYS.STORYBOARD_FRAMES(shot.id)` ✓
- `api.uploadFrame`, `api.updateFrame`, `api.deleteFrame` all wired ✓
- file input with `accept="image/jpeg,image/png,image/webp"` ✓
- `is_selected` → `border-primary` visual highlight ✓
- Disabled "Generate with AI" with Phase 31 tooltip ✓
- `window.confirm` before delete ✓
- Empty state "No frames yet" ✓
- Selected badge with Check icon and "Selected" text ✓
- StoryboardView wired with `selectedShot`, `onOpenChange` clears selection ✓
- No new TypeScript errors in Storyboard files ✓
