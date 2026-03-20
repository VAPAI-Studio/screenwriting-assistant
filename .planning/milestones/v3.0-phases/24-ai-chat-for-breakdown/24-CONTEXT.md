# Phase 24: AI Chat for Breakdown - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the right sidebar in breakdown mode with a breakdown-aware AI chat. The AI has context about the current project's full shotlist and all breakdown elements, and can propose creating new shots or modifying existing ones — with user confirmation before any changes are written. Rendering the right panel and the broader breakdown layout are already done (Phase 18/20).

</domain>

<decisions>
## Implementation Decisions

### Context Injection Scope
- AI receives all shots in the project (not scoped to current scene) — enables cross-scene awareness
- AI receives all breakdown elements across all categories (Characters, Locations, Props, etc.)
- Frontend passes context to the backend with each message — React Query caches already hold shots + elements, so frontend serializes and includes them in the chat request body. Same pattern as existing `fieldContext` in `SidebarChat.tsx`'s `buildFieldContext()`

### Component Integration
- New `BreakdownChat` component — dedicated, single-purpose. Does NOT extend `SidebarChat` or add a mode prop
- Breakdown chat has no panel tabs — single unified chat mode (no Template AI / Agent separation)
- Reuse `MarkdownContent` and `ProposedChangesCard` from `frontend/src/components/Shared/` — both are pure presentational; avoid duplicating them
- Build new streaming and session management logic within `BreakdownChat` following the same patterns as `SidebarChat` but without the unused complexity (field_groups, subsection config, agent selector, YOLO button)
- `BreakdownLayout.tsx` right panel replaces the current "AI Chat — available in Phase 24" placeholder with `<BreakdownChat projectId={projectId} />`

### Shot Confirmation UX
- **Shot creation confirmation:** Reuse `ProposedChangesCard` pattern, adapted for shots. Card shows: shot number, associated scene, and key fields (shot type, lens, notes). User sees "Create Shot" / Dismiss buttons
- **Shot modification confirmation:** Show proposed new values only (no before/after diff). Same card pattern. User sees "Apply changes" / Dismiss
- **Post-confirm behavior:** AI posts a brief confirmation message in the chat thread ("Shot #X created" / "Shot #X updated") AND React Query invalidates the shots query so the center ShotlistPanel refreshes automatically

### Chat Styling
- Breakdown chat uses the breakdown mode palette (cool slate/blue-grey) — input ring color, active state accents shift from amber/violet to steel blue or indigo to stay in-mode
- Message bubbles follow the same rounded-xl / border pattern as `SidebarChat` but with breakdown-palette accent colors

### Claude's Discretion
- Exact serialization format for shots + elements in the chat request body
- Backend endpoint path (extend existing `/api/ai_chat/` or new breakdown-specific route)
- Session management approach (reuse existing AI session model or new chat session type)
- Exact fields included in the shot creation/modification confirmation card

</decisions>

<specifics>
## Specific Ideas

- No specific references or "I want it like X" moments — open to standard approaches within the decisions above
- The confirmation flow should feel familiar — it already exists in SidebarChat for field updates, so users who use both modes will recognize the pattern

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing chat infrastructure
- `frontend/src/components/Shared/SidebarChat.tsx` — Full existing chat component: streaming, session management, ProposedChangesCard, field context building pattern to follow
- `frontend/src/components/Shared/MarkdownContent.tsx` — Shared markdown renderer (reuse)
- `backend/app/api/endpoints/ai_chat.py` — Existing AI chat endpoint: session creation, streaming, field context injection — extend or model new breakdown endpoint after this
- `backend/app/api/endpoints/chat.py` — Existing agent chat endpoint for reference

### Shot API
- `backend/app/api/endpoints/shots.py` — CRUD for shots: create, update, list endpoints that BreakdownChat will call after user confirmation
- `frontend/src/lib/api.tsx` — Existing API client: `createShot`, `updateShot`, `listShots` functions

### Breakdown elements API
- `backend/app/api/endpoints/breakdown.py` — Breakdown element endpoints for fetching elements by category to inject into chat context
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` — Current layout: right panel placeholder location, projectId prop passing, breakdown mode context

### Data types
- `frontend/src/types/index.ts` — `Shot`, `BreakdownElement`, `AssetMedia` types
- `frontend/src/lib/constants.ts` — `QUERY_KEYS`, `STORAGE_KEYS` conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SidebarChat.tsx` (`frontend/src/components/Shared/SidebarChat.tsx`): `ProposedChangesCard` sub-component and `AgentMessageBubble` sub-component are independently usable. The `buildFieldContext()` pattern shows exactly how to serialize React Query cache data into a context payload
- `MarkdownContent.tsx` (`frontend/src/components/Shared/MarkdownContent.tsx`): renders streamed markdown — import directly into BreakdownChat
- `ProposedChangesCard` (defined inside `SidebarChat.tsx`): should be extracted to its own file or imported — currently co-located with SidebarChat
- `ResizablePanel` (`frontend/src/components/UI/ResizablePanel.tsx`): BreakdownLayout already handles panel resizing; BreakdownChat renders inside the right panel container directly, no need to wrap in ResizablePanel again

### Established Patterns
- AI sessions: `api.createAISession()` / `api.lookupAISession()` — session-per-context-key pattern
- Streaming: `api.sendAIMessageStream()` with chunk + done callbacks — follow same signature
- React Query invalidation: `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId) })` after shot create/update
- `STORAGE_KEYS` constants in `frontend/src/lib/constants.ts` — add any new localStorage keys here
- CSS variables: breakdown palette already defined in `index.css` under breakdown mode scope — use `var(--accent)` etc. within the breakdown layout context, colors auto-correct

### Integration Points
- `BreakdownLayout.tsx`: right panel currently renders `<p>AI Chat — available in Phase 24</p>` placeholder — replace with `<BreakdownChat projectId={projectId} />`
- `frontend/src/lib/api.tsx`: add new `sendBreakdownChatMessage()` function following existing `sendChatMessageStream()` pattern, passing shot + element context
- `backend/app/main.py` or router: register new breakdown chat endpoint (or extend existing ai_chat router with a breakdown-specific stream handler)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-ai-chat-for-breakdown*
*Context gathered: 2026-03-20*
