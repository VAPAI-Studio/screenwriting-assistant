---
phase: 14-reverse-sync
plan: 02
subsystem: ui
tags: [react, typescript, react-query, lucide-react, breakdown, characters]

# Dependency graph
requires:
  - phase: 14-01
    provides: POST /api/breakdown/element/{id}/sync-to-project endpoint and synced_to_characters computed field on list query response
provides:
  - synced_to_characters boolean on BreakdownElement TypeScript interface
  - api.syncBreakdownElementToCharacters() method in frontend API client
  - ElementCard renders "+ Add to Characters" button only for character category elements
  - Button transitions to disabled "Synced" state after syncMutation.isSuccess or element.synced_to_characters=true
affects: [BreakdownPage, ElementList, ElementCard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "syncMutation pattern: useMutation with onSettled invalidation of BREAKDOWN_ELEMENTS query key"
    - "Optimistic visual feedback: syncMutation.isSuccess provides instant Synced state before re-fetch settles"
    - "stopPropagation on button wrapper div prevents card entering edit mode on sync button click"

key-files:
  created: []
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/api.tsx
    - frontend/src/components/Breakdown/ElementCard.tsx

key-decisions:
  - "syncMutation.isSuccess used for instant visual feedback covering both created and already_exists paths (both return 200)"
  - "No BREAKDOWN_SUMMARY invalidation in syncMutation.onSettled — sync does not change element counts"
  - "No optimistic update on sync — let onSettled re-fetch so synced_to_characters reflects actual DB state"

patterns-established:
  - "Sync button pattern: conditional render based on category prop + boolean flag from server"

requirements-completed: [SYNC-05]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 14 Plan 02: Frontend Sync Button Summary

**React Query syncMutation with UserCheck icon Synced state wired to POST /breakdown/element/{id}/sync-to-project for character breakdown elements**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T01:30:29Z
- **Completed:** 2026-03-18T01:32:00Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 3

## Accomplishments
- Added `synced_to_characters: boolean` to BreakdownElement TypeScript interface
- Added `api.syncBreakdownElementToCharacters(elementId)` method calling POST /breakdown/element/{id}/sync-to-project
- ElementCard renders "+ Add to Characters" button only when `category === 'character'` and not in editing mode
- Button shows "Adding..." while pending, transitions to UserCheck "Synced" indicator on success or when `element.synced_to_characters === true`
- syncMutation.onSettled invalidates BREAKDOWN_ELEMENTS query to re-fetch persisted synced_to_characters flag from backend

## Task Commits

Each task was committed atomically:

1. **Task 1: Add synced_to_characters type and API client method** - `66e22a6` (feat)
2. **Task 2: Add syncMutation and Add/Synced button to ElementCard** - `738ff2a` (feat)
3. **Task 3: Checkpoint — Verify end-to-end reverse sync flow** - human-verify approved

## Files Created/Modified
- `frontend/src/types/index.ts` - Added `synced_to_characters: boolean` to BreakdownElement interface
- `frontend/src/lib/api.tsx` - Added `syncBreakdownElementToCharacters()` method
- `frontend/src/components/Breakdown/ElementCard.tsx` - Added UserCheck import, syncMutation, and conditional Add/Synced button JSX

## Decisions Made
- `syncMutation.isSuccess` provides instant visual feedback before the `onSettled` re-fetch resolves, covering both `created` and `already_exists` response paths (both return HTTP 200, so mutation always succeeds)
- No BREAKDOWN_SUMMARY invalidation in syncMutation — sync doesn't change element counts, only the synced flag
- No optimistic update on sync mutation — let onSettled re-fetch so the server-side synced_to_characters reflects actual DB state

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
Pre-existing TypeScript errors in unrelated files (IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx) were present before this plan — not caused by these changes and out of scope.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Frontend sync button complete and wired to backend endpoint from Plan 14-01
- End-to-end flow verified by user: character elements show "+ Add to Characters", button transitions to UserCheck "Synced" state, synced character appears in story.characters phase, and persisted synced_to_characters=true survives page refresh
- Phase 14 (Reverse Sync) is complete — v2.0 Script Breakdown milestone pending Phase 13 completion (Breakdown Page plan 13-03)

## Self-Check: PASSED

- FOUND: `.planning/phases/14-reverse-sync/14-02-SUMMARY.md`
- FOUND: commit `66e22a6` (Task 1 — synced_to_characters type and API method)
- FOUND: commit `738ff2a` (Task 2 — syncMutation and Add/Synced button)

---
*Phase: 14-reverse-sync*
*Completed: 2026-03-18*
