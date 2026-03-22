---
plan: 30-01
phase: 30-storyboard-grid-ui
status: complete
completed: 2026-03-21
---

# Plan 30-01: ShotCard + StoryboardView Grid

## What Was Built

- **ShotCard** (`frontend/src/components/Storyboard/ShotCard.tsx`):
  - Fetches frames via `useQuery(QUERY_KEYS.STORYBOARD_FRAMES(shot.id))` → `api.listFrames`
  - Finds selected frame: `frames.find(f => f.is_selected) ?? frames[0] ?? null`
  - Renders: aspect-video frame area (selected thumbnail or Image placeholder), scene label, shot number, description (truncated/line-clamp), shot size badge, frame count badge (if >1)
  - AI badge (Sparkles) overlaid when `generation_source === 'ai'`
  - Clickable button invoking `onClick(shot.id)` for gallery modal

- **StoryboardView** (`frontend/src/components/Storyboard/StoryboardView.tsx`):
  - Replaced placeholder with full grid implementation
  - Preserved `useEffect` for `storyboard-mode` CSS class lifecycle
  - `groupShotsByScene(shots)` groups by `scene_item_id`, unassigned shots go last
  - Scene headers with shot count badges and separator line
  - Responsive grid: `grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6`
  - Shots sorted by `sort_order` then `shot_number` within each scene
  - `selectedShotId` state prepared for Plan 30-02 FrameGalleryModal
  - Loading state (Loader2 spinner), error state (AlertCircle + retry button), empty state (Film icon + instructions)
  - Header bar showing "Storyboard" label and shot count
  - TODO comment marking FrameGalleryModal insertion point

## Commits

- `45cf642`: feat(30-01): ShotCard component and StoryboardView shot grid

## Self-Check: PASSED

- ShotCard uses `useQuery` with `QUERY_KEYS.STORYBOARD_FRAMES(shot.id)` ✓
- ShotCard has `is_selected` check for selected frame ✓
- ShotCard has `onClick(shot.id)` callback ✓
- StoryboardView has `groupShotsByScene` with unassigned-last logic ✓
- StoryboardView has responsive grid classes ✓
- StoryboardView has `sort_order` sorting ✓
- StoryboardView preserves storyboard-mode useEffect ✓
- No new TypeScript errors in Storyboard files ✓
