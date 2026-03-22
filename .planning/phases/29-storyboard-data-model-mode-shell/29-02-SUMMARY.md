---
plan: 29-02
phase: 29-storyboard-data-model-mode-shell
status: complete
completed: 2026-03-21
---

# Plan 29-02: Three-Mode Toggle, Storyboard CSS, StoryboardView Shell

## Objective
Extend the frontend with storyboard types, API client methods, deep purple CSS theme, three-mode toggle, and a StoryboardView shell component registered at `/projects/:id/storyboard`.

## What Was Built

- **Types** (`frontend/src/types/index.ts`): Added `GenerationSource`, `StoryboardStyle`, and `StoryboardFrame` interface mirroring the backend schema.

- **Constants** (`frontend/src/lib/constants.ts`):
  - `ROUTES.PROJECT_STORYBOARD: (id) => \`/projects/${id}/storyboard\``
  - `QUERY_KEYS.STORYBOARD_FRAMES: (shotId) => ['storyboard-frames', shotId]`

- **API client** (`frontend/src/lib/api.tsx`): Added 4 storyboard methods under `// Storyboard (v3.2 — Phase 29)` section:
  - `uploadFrame(projectId, shotId, formData)` — multipart POST, returns `StoryboardFrame`
  - `listFrames(projectId, shotId)` — GET list ordered by created_at
  - `updateFrame(projectId, frameId, { is_selected })` — PATCH for selection
  - `deleteFrame(projectId, frameId)` — DELETE

- **CSS theme** (`frontend/src/index.css`): Added `.storyboard-mode` class block with deep violet palette (`--accent: 263 70% 58%`, `--background: 263 15% 4%`). Mirrors `.breakdown-mode` structure.

- **ModeToggle** (`frontend/src/components/Layout/ModeToggle.tsx`): Extended from 2 to 3 modes:
  - `Film` icon from lucide-react for Storyboard
  - `isStoryboard = pathname.endsWith('/storyboard')`
  - `handleSelect` handles 'storyboard' → `ROUTES.PROJECT_STORYBOARD(projectId)`
  - Lookup table for modeIcon and modeLabel

- **StoryboardView** (`frontend/src/components/Storyboard/StoryboardView.tsx`): Shell component:
  - `useEffect` adds `storyboard-mode` class to `document.documentElement`, removes on unmount
  - Placeholder UI with Film icon and "Storyboard coming soon" message

- **App.tsx**: Added `useParams` import, `StoryboardViewRoute` wrapper, and route `/projects/:projectId/storyboard` before the `/:phase` catch-all.

## Key Files Modified/Created

- `frontend/src/types/index.ts` — StoryboardFrame types
- `frontend/src/lib/constants.ts` — ROUTES.PROJECT_STORYBOARD, QUERY_KEYS.STORYBOARD_FRAMES
- `frontend/src/lib/api.tsx` — 4 storyboard API methods
- `frontend/src/index.css` — .storyboard-mode CSS block
- `frontend/src/components/Layout/ModeToggle.tsx` — three-mode toggle
- `frontend/src/components/Storyboard/StoryboardView.tsx` — new shell component
- `frontend/src/App.tsx` — storyboard route registration

## Commits

- `ad173ab`: feat(29-02): three-mode toggle, storyboard CSS, StoryboardView shell

## Self-Check: PASSED

- StoryboardFrame interface matches backend schema ✓
- ROUTES.PROJECT_STORYBOARD registered and used in ModeToggle ✓
- .storyboard-mode CSS uses --accent: 263 70% 58% ✓
- ModeToggle shows Film icon for storyboard mode ✓
- StoryboardView adds/removes storyboard-mode class on mount/unmount ✓
- /projects/:projectId/storyboard route before /:phase catch-all ✓
- Pre-existing TypeScript errors confirmed pre-existing (not introduced here) ✓
