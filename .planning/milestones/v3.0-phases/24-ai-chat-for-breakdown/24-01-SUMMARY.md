---
phase: 24-ai-chat-for-breakdown
plan: 01
subsystem: api, ui
tags: [fastapi, streaming, sse, react, typescript, openai, chat, breakdown]

# Dependency graph
requires:
  - phase: 20-shotlist-panel
    provides: Shot CRUD API and frontend API client
  - phase: 18-two-mode-ui-shell
    provides: BreakdownLayout with right panel placeholder
provides:
  - Breakdown chat streaming endpoint at POST /api/breakdown-chat/{project_id}/stream
  - BreakdownChat frontend component with streaming and context injection
  - Pydantic schemas for breakdown chat request/response
  - Frontend types for BreakdownChatMessage and ShotAction
affects: [24-02-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [stateless chat with context-per-request, SSE streaming for breakdown chat]

key-files:
  created:
    - backend/app/api/endpoints/breakdown_chat.py
    - backend/app/tests/test_breakdown_chat_api.py
    - frontend/src/components/Breakdown/BreakdownChat.tsx
  modified:
    - backend/app/models/schemas.py
    - backend/app/main.py
    - frontend/src/lib/api.tsx
    - frontend/src/types/index.ts
    - frontend/src/components/Breakdown/BreakdownLayout.tsx

key-decisions:
  - "Stateless chat pattern: full message history + context sent with every request, no backend session persistence"
  - "System prompt injects shots as numbered list and elements grouped by category"
  - "shot_action always None in Plan 01; extraction deferred to Plan 02"

patterns-established:
  - "Context injection via request body: frontend serializes React Query cache data into chat request"
  - "Breakdown chat SSE format: data: {chunk} for streaming, data: {done, shot_action} for completion, data: [DONE] sentinel"

requirements-completed: [CHAT-01, CHAT-02, CHAT-03]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 24 Plan 01: AI Chat for Breakdown Summary

**Breakdown-aware AI chat with SSE streaming endpoint and BreakdownChat component replacing right panel placeholder, injecting shots and elements context from React Query cache into every request**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T14:02:29Z
- **Completed:** 2026-03-20T14:07:21Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Backend streaming endpoint at POST /api/breakdown-chat/{project_id}/stream with shots and elements context injection into AI system prompt
- BreakdownChat frontend component with streaming, auto-scroll, empty state, error handling, and MarkdownContent rendering
- Right panel placeholder in BreakdownLayout replaced with functional BreakdownChat component
- 7 backend tests covering auth, project ownership, context injection, and SSE chunk format

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend breakdown chat endpoint + schemas + tests + router registration** - `4e484d1` (feat)
2. **Task 2: Frontend BreakdownChat component + API client + wire into BreakdownLayout** - `681045d` (feat)

## Files Created/Modified
- `backend/app/api/endpoints/breakdown_chat.py` - Streaming endpoint with system prompt builder and project ownership verification
- `backend/app/tests/test_breakdown_chat_api.py` - 7 tests for auth, context injection, SSE format
- `backend/app/models/schemas.py` - BreakdownChatRequest, BreakdownChatShotContext, BreakdownChatElementContext, BreakdownChatMessage schemas
- `backend/app/main.py` - Router registration for breakdown-chat endpoint
- `frontend/src/components/Breakdown/BreakdownChat.tsx` - Main chat component with streaming, context building, message display
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` - Replaced placeholder with BreakdownChat
- `frontend/src/lib/api.tsx` - sendBreakdownChatStream API function with SSE parsing
- `frontend/src/types/index.ts` - BreakdownChatMessage and ShotAction type interfaces

## Decisions Made
- Stateless chat pattern: full message history and breakdown context sent with every request (no backend session persistence per RESEARCH.md recommendation)
- System prompt formats shots as numbered list with scene association and key fields, elements grouped by category
- shot_action is always None in Plan 01; Plan 02 will add extraction via second JSON-mode call
- BreakdownChat reads shots and elements from React Query cache synchronously via getQueryData in the send handler (not in an effect), ensuring fresh data

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- 3 pre-existing TypeScript errors in unrelated files (IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx) cause `tsc --noEmit` and `npm run build` (which runs tsc first) to fail. These are NOT caused by this plan's changes. Vite build (`npx vite build`) succeeds, confirming all new code is valid.
- 1 pre-existing test failure in test_session_isolation.py unrelated to this plan's changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend endpoint ready for Plan 02 to add shot action extraction (second JSON-mode call after streaming)
- Frontend ShotAction type and shotAction state already wired in BreakdownChat, ready for ShotProposalCard component in Plan 02
- Comment placeholder in BreakdownChat marks where ShotProposalCard will render

## Self-Check: PASSED

All files verified present, all commits verified in git log.

---
*Phase: 24-ai-chat-for-breakdown*
*Completed: 2026-03-20*
