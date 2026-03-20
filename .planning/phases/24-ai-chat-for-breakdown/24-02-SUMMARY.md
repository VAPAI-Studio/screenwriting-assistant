---
phase: 24-ai-chat-for-breakdown
plan: 02
subsystem: ai, ui
tags: [openai, json-mode, react-query, sse, shot-crud, confirmation-ux]

# Dependency graph
requires:
  - phase: 24-ai-chat-for-breakdown-01
    provides: BreakdownChat component with streaming, ShotAction type, breakdown chat endpoint
  - phase: 19-shot-crud-api-core-model
    provides: Shot CRUD API (createShot, updateShot)
  - phase: 20-shotlist-panel
    provides: ShotlistPanel with React Query cache, QUERY_KEYS.SHOTS
provides:
  - Two-phase AI shot action extraction (stream + JSON-mode extraction call)
  - ShotProposalCard confirmation UI for create/modify shots
  - Full create/modify shot flow via AI chat with confirmation gate
  - React Query invalidation for ShotlistPanel auto-refresh after shot changes
affects: [shotlist-panel, breakdown-layout]

# Tech tracking
tech-stack:
  added: []
  patterns: [two-phase-ai-extraction, confirmation-card-pattern, jsonb-field-merge-on-modify]

key-files:
  created:
    - frontend/src/components/Breakdown/ShotProposalCard.tsx
  modified:
    - backend/app/api/endpoints/breakdown_chat.py
    - backend/app/tests/test_breakdown_chat_api.py
    - frontend/src/components/Breakdown/BreakdownChat.tsx

key-decisions:
  - "Two-phase AI call: stream conversational response first, then JSON-mode extraction for shot action"
  - "ShotProposalCard spreads existing fields before proposed changes to prevent JSONB wipe on modify"
  - "Confirmation message added to chat thread after successful shot create/modify"

patterns-established:
  - "Two-phase AI extraction: stream response for UX, then separate JSON-mode call for structured data"
  - "ShotProposalCard confirmation gate: no data changes without user approval"

requirements-completed: [CHAT-04, CHAT-05]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 24 Plan 02: Shot Action Extraction & ShotProposalCard Summary

**Two-phase AI shot action extraction with ShotProposalCard confirmation flow for creating and modifying shots via chat**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T14:10:17Z
- **Completed:** 2026-03-20T14:14:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Backend extracts shot create/modify actions via a second JSON-mode AI call after streaming completes
- ShotProposalCard renders proposed shot details with Create Shot / Apply Changes / Dismiss buttons
- On confirm, calls existing CRUD API and invalidates React Query cache so ShotlistPanel refreshes
- Fields correctly merged on modify (spread existing before proposed) to prevent JSONB replacement
- All 7 breakdown chat tests pass including new create and modify action tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend shot action extraction + update tests** - `0c8a4c4` (feat)
2. **Task 2: ShotProposalCard component + wire confirmation flow** - `05626fd` (feat)

## Files Created/Modified
- `backend/app/api/endpoints/breakdown_chat.py` - Added _extract_shot_action function with JSON-mode AI call and wired into generate() SSE stream
- `backend/app/tests/test_breakdown_chat_api.py` - Replaced stub tests with real create/modify action tests using mocked AI responses
- `frontend/src/components/Breakdown/ShotProposalCard.tsx` - New component: confirmation card for AI-proposed shot create/modify with CRUD API integration
- `frontend/src/components/Breakdown/BreakdownChat.tsx` - Imported ShotProposalCard, added getExistingShots/handleShotConfirmed/handleShotDismiss callbacks

## Decisions Made
- Two-phase AI call pattern: stream the conversational response first for immediate UX feedback, then make a separate JSON-mode `chat_completion` call to extract structured shot action data
- ShotProposalCard spreads `existingShot.fields` before proposed changes on modify to prevent the JSONB replacement pitfall (PUT replaces entire fields dict, per Phase 20 decision)
- Confirmation messages ("Shot #N created" / "Shot #N updated") appear as assistant messages in the chat thread for user feedback

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing TypeScript errors in 3 unrelated files (IndividualEditorView, RepeatableCardsView, SidebarChat) cause `tsc` to fail, but these errors exist on the base branch before any changes. Our files compile cleanly (verified with `tsc --noEmit | grep ShotProposalCard` showing no matches). Vite build succeeds.
- Pre-existing test failure in `test_session_isolation.py` unrelated to our changes (verified by running test with changes reverted).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- AI chat-driven shot management workflow is complete (CHAT-01 through CHAT-05)
- ShotProposalCard can be reused for future shot-related confirmation flows
- Phase 24 is fully complete

## Self-Check: PASSED

All 4 files verified present. Both commit hashes verified. All 22 acceptance criteria pass.

---
*Phase: 24-ai-chat-for-breakdown*
*Completed: 2026-03-20*
