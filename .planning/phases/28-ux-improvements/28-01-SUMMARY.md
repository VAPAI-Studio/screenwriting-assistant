---
plan: 28-01
phase: 28-ux-improvements
status: complete
completed: 2026-03-21
---

# Plan 28-01: Media Asset Deletion UI

## Objective
Add delete-with-confirmation to individual media assets inside the expanded AssetElementCard.

## What Was Built

Added trash-icon delete button to every media item in the assets panel:

- **MediaThumbnail.tsx**: Added optional `onDelete` prop. When provided, renders a `Trash2` icon button as an absolute overlay in the top-right corner, visible on hover via `opacity-0 group-hover:opacity-100`. Wrapped the thumbnail in a `relative group` div. Works for both the image case and the error/fallback case.

- **AssetElementCard.tsx**: Added `deleteMutation` via `useMutation` calling `api.deleteMedia(projectId, mediaId)`. On success, invalidates `QUERY_KEYS.ELEMENT_MEDIA(element.id)` so the list refreshes. Added `handleDeleteMedia` that calls `window.confirm` before firing. Images: `onDelete` prop passed to each `<MediaThumbnail>`. Audio: each `<AudioPlayer>` wrapped in a `relative group` div with a sibling `Trash2` button using the same hover pattern.

## Key Files Modified

- `frontend/src/components/Breakdown/MediaThumbnail.tsx` — added onDelete overlay
- `frontend/src/components/Breakdown/AssetElementCard.tsx` — added deleteMutation + handleDeleteMedia

## Commits

- `973c1cf`: feat(28-01): add media deletion UI with trash button overlay and confirm guard

## Self-Check: PASSED

- MediaThumbnail renders onDelete overlay on hover ✓
- AssetElementCard wires deleteMutation to api.deleteMedia with window.confirm guard ✓
- Query cache invalidated on success ✓
- Build passes with no new TypeScript errors ✓
