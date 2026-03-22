---
plan: 31-02
phase: 31-ai-frame-generation-google-imagen
status: complete
completed: 2026-03-22
---

# Plan 31-02: Frontend Generate Button

## Objective
Enable the "Generate with AI" button in FrameGalleryModal, wire it to the generate endpoint, and show loading/error/success states.

## What Was Built

- **`frontend/src/lib/api.tsx`**: Added `generateFrame(projectId, shotId)` method:
  - `POST /storyboard/{projectId}/shots/{shotId}/generate`
  - Uses `getHeaders()` (JSON Content-Type + Bearer auth)
  - Returns `Promise<StoryboardFrame>`
  - Throws descriptive error from response JSON on failure

- **`frontend/src/components/Storyboard/FrameGalleryModal.tsx`**:
  - Added `generateMutation` using `useMutation` with `api.generateFrame`
  - `onSuccess` invalidates `QUERY_KEYS.STORYBOARD_FRAMES(shot.id)` to refresh gallery
  - Replaced disabled placeholder button with enabled violet-styled button:
    - `bg-violet-500/10 hover:bg-violet-500/20 text-violet-400 border-violet-500/20`
    - Shows `Loader2` spinner + "Generating..." during pending
    - Disabled only while pending (prevents double-clicks)
  - Added generate error display below gallery following same pattern as upload error

## Key Files Modified

- `frontend/src/lib/api.tsx` — generateFrame method
- `frontend/src/components/Storyboard/FrameGalleryModal.tsx` — generateMutation, enabled button, error display

## Commits

- `89baf80`: feat(31-02): enable Generate with AI button in FrameGalleryModal

## Self-Check: PASSED

- `api.generateFrame` calls POST generate endpoint ✓
- `generateMutation` wired to `api.generateFrame` ✓
- Button enabled by default, disabled only during pending ✓
- Spinner + "Generating..." shown during pending ✓
- Violet color scheme matches storyboard identity ✓
- `onSuccess` invalidates STORYBOARD_FRAMES cache ✓
- Generate error displayed below gallery ✓
- No "Coming in Phase 31" title remains ✓
- TypeScript: only pre-existing errors in unrelated files ✓
