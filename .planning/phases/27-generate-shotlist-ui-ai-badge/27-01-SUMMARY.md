---
phase: 27-generate-shotlist-ui-ai-badge
plan: 01
subsystem: ui
tags: [react, react-query, lucide-react, useMutation, shotlist, ai-generation]

# Dependency graph
requires:
  - phase: 26-ai-shotlist-generation-service
    provides: POST /api/shots/{project_id}/generate endpoint
provides:
  - generateShotlist API client method
  - Generate Shotlist button in breakdown center panel header
  - Sparkles icon badge for AI-generated shots
  - Generate with AI button in empty state
  - ai_generated and user_modified fields on Shot interface
affects: [28-polish, shotlist-panel, breakdown-layout]

# Tech tracking
tech-stack:
  added: []
  patterns: [useEffect callback prop for lifting mutation state to parent]

key-files:
  created: []
  modified:
    - frontend/src/types/index.ts
    - frontend/src/lib/api.tsx
    - frontend/src/components/Breakdown/ShotlistPanel.tsx
    - frontend/src/components/Breakdown/BreakdownLayout.tsx
    - frontend/src/components/Breakdown/ShotRow.tsx
    - frontend/src/components/Breakdown/ShotlistEmptyState.tsx

key-decisions:
  - "Used useEffect callback to lift generate mutation state from ShotlistPanel to BreakdownLayout for header button"
  - "Wrapped Sparkles icon in span for title attribute since lucide-react LucideProps does not support title prop"

patterns-established:
  - "Lifted mutation state pattern: child exposes mutation state via onStateChange callback prop + useEffect, parent stores in useState"

requirements-completed: [AISG-01, AISG-07]

# Metrics
duration: 4min
completed: 2026-03-21
---

# Phase 27 Plan 01: Generate Shotlist UI and AI Badge Summary

**Frontend Generate Shotlist button with React Query useMutation, Sparkles AI badge on shot rows, and Generate with AI empty state CTA**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-21T17:46:44Z
- **Completed:** 2026-03-21T17:50:46Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Shot interface extended with ai_generated and user_modified boolean fields matching backend ShotResponse
- API client generateShotlist method using CHAT_TIMEOUT (120s) for long-running AI generation
- Generate Shotlist button in breakdown center panel header with Sparkles icon (idle) / Loader2 spinner (generating)
- Sparkles icon badge on AI-generated shots, absent on manually-created shots
- Generate with AI button in empty state alongside Add First Shot
- Inline error banner for validation errors (e.g., no screenplay content)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Shot type fields, API method, and generate mutation** - `c1bc447` (feat)
2. **Task 2: Add generate button in header, sparkle badge on shots, and generate in empty state** - `6837e2c` (feat)

## Files Created/Modified
- `frontend/src/types/index.ts` - Added ai_generated and user_modified boolean fields to Shot interface
- `frontend/src/lib/api.tsx` - Added generateShotlist API method with CHAT_TIMEOUT
- `frontend/src/components/Breakdown/ShotlistPanel.tsx` - Added generateMutation, error state, props interface, optimistic shot fields
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Added Generate Shotlist button in center panel header with state lifted from ShotlistPanel
- `frontend/src/components/Breakdown/ShotRow.tsx` - Added Sparkles icon badge for AI-generated shots
- `frontend/src/components/Breakdown/ShotlistEmptyState.tsx` - Added Generate with AI button and error display

## Decisions Made
- Used useEffect callback prop pattern to lift mutation state from ShotlistPanel to BreakdownLayout, avoiding prop drilling or context for a single concern
- Wrapped Sparkles lucide icon in a span element for the title tooltip since lucide-react LucideProps does not support the HTML title attribute directly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Expanded ShotlistEmptyState props in Task 1**
- **Found during:** Task 1 (adding generate props to empty state render)
- **Issue:** ShotlistEmptyState props interface did not include onGenerate/isGenerating/generateError, causing TypeScript compilation failure
- **Fix:** Added optional generate props to ShotlistEmptyState interface in Task 1 (planned for Task 2) to enable compilation
- **Files modified:** frontend/src/components/Breakdown/ShotlistEmptyState.tsx
- **Verification:** TypeScript compilation passes
- **Committed in:** c1bc447 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed Sparkles title prop TypeScript error**
- **Found during:** Task 2 (adding Sparkles icon to ShotRow)
- **Issue:** lucide-react LucideProps does not have a `title` attribute, causing TS2322
- **Fix:** Wrapped Sparkles in a `<span title="AI generated">` element instead
- **Files modified:** frontend/src/components/Breakdown/ShotRow.tsx
- **Verification:** TypeScript compilation passes
- **Committed in:** 6837e2c (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for TypeScript compilation. No scope creep.

## Issues Encountered
None - both deviations were minor and resolved immediately.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Frontend fully wired to backend generate endpoint
- AI badge visual distinction operational
- Ready for end-to-end testing or further polish phases

## Self-Check: PASSED

All 7 files verified present. Both task commits (c1bc447, 6837e2c) verified in git history.

---
*Phase: 27-generate-shotlist-ui-ai-badge*
*Completed: 2026-03-21*
