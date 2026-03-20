# Phase 24: AI Chat for Breakdown - Research

**Researched:** 2026-03-20
**Domain:** Frontend chat component + Backend streaming AI endpoint + Shot CRUD integration
**Confidence:** HIGH

## Summary

Phase 24 adds a breakdown-aware AI chat to the right sidebar of breakdown mode. The implementation is highly constrained by existing patterns -- the project already has a full-featured `SidebarChat.tsx` (737 lines) with streaming, session management, and a `ProposedChangesCard` confirmation flow. The backend has a complete streaming SSE endpoint pattern in `ai_chat.py`. The shots CRUD API and frontend API client functions (`createShot`, `updateShot`, `listShots`) are fully implemented. Breakdown elements have their own API (`getBreakdownElements`). The task is to wire these together into a new dedicated `BreakdownChat` component with a breakdown-specific backend endpoint.

The key technical challenge is the context injection pattern: serializing the full shotlist and all breakdown elements from the React Query cache into each chat request, then building a backend endpoint that uses this context to generate breakdown-aware responses and structured shot action proposals (create/modify). The confirmation UX follows the existing `ProposedChangesCard` pattern but adapted for shot-specific fields via a new `ShotProposalCard` component.

**Primary recommendation:** Create a new backend streaming endpoint (`POST /api/breakdown-chat/{project_id}/stream`) that accepts shots + elements context in the request body, streams conversational responses, and returns structured shot actions (create/modify) in the done event. Frontend `BreakdownChat` component follows `SidebarChat` streaming patterns exactly but is a separate, simpler component without panel modes, field groups, or agent selection.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- AI receives all shots in the project (not scoped to current scene) -- enables cross-scene awareness
- AI receives all breakdown elements across all categories (Characters, Locations, Props, etc.)
- Frontend passes context to the backend with each message -- React Query caches already hold shots + elements, so frontend serializes and includes them in the chat request body. Same pattern as existing `fieldContext` in `SidebarChat.tsx`'s `buildFieldContext()`
- New `BreakdownChat` component -- dedicated, single-purpose. Does NOT extend `SidebarChat` or add a mode prop
- Breakdown chat has no panel tabs -- single unified chat mode (no Template AI / Agent separation)
- Reuse `MarkdownContent` and `ProposedChangesCard` from `frontend/src/components/Shared/` -- both are pure presentational; avoid duplicating them
- Build new streaming and session management logic within `BreakdownChat` following the same patterns as `SidebarChat` but without the unused complexity (field_groups, subsection config, agent selector, YOLO button)
- `BreakdownLayout.tsx` right panel replaces the current "AI Chat -- available in Phase 24" placeholder with `<BreakdownChat projectId={projectId} />`
- Shot creation confirmation: Reuse `ProposedChangesCard` pattern, adapted for shots. Card shows: shot number, associated scene, and key fields (shot type, lens, notes). User sees "Create Shot" / Dismiss buttons
- Shot modification confirmation: Show proposed new values only (no before/after diff). Same card pattern. User sees "Apply changes" / Dismiss
- Post-confirm behavior: AI posts a brief confirmation message in the chat thread ("Shot #X created" / "Shot #X updated") AND React Query invalidates the shots query so the center ShotlistPanel refreshes automatically
- Breakdown chat uses the breakdown mode palette (cool slate/blue-grey) -- input ring color, active state accents shift from amber/violet to steel blue or indigo to stay in-mode

### Claude's Discretion
- Exact serialization format for shots + elements in the chat request body
- Backend endpoint path (extend existing `/api/ai_chat/` or new breakdown-specific route)
- Session management approach (reuse existing AI session model or new chat session type)
- Exact fields included in the shot creation/modification confirmation card

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CHAT-01 | Right sidebar in breakdown mode shows the AI chat (extends existing SidebarChat) | BreakdownChat component replaces placeholder in BreakdownLayout.tsx right panel. BreakdownPanel wrapper already handles panel chrome (title, collapse). Component follows SidebarChat patterns but is separate per CONTEXT.md decision. |
| CHAT-02 | AI chat in breakdown mode has context awareness of the current project's shotlist data | Frontend serializes all shots from React Query cache (`QUERY_KEYS.SHOTS(projectId)`) into the request body. Backend injects this into the AI system prompt as structured context. |
| CHAT-03 | AI chat in breakdown mode has context awareness of the current project's breakdown elements | Frontend serializes all breakdown elements from React Query cache (`QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId)`) into the request body. Backend includes in system prompt alongside shots. |
| CHAT-04 | AI chat can create new shots via conversation (user confirms before creation) | Backend returns `shot_action: { type: "create", data: {...} }` in the SSE done event. Frontend renders ShotProposalCard with "Create Shot" / "Dismiss". On confirm, calls `api.createShot()` then invalidates shots query. |
| CHAT-05 | AI chat can modify existing shot fields via conversation (user confirms before changes) | Backend returns `shot_action: { type: "modify", shot_id: "...", data: {...} }` in done event. Frontend renders ShotProposalCard with "Apply Changes" / "Dismiss". On confirm, calls `api.updateShot()` with field spread then invalidates. |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 18 | UI framework | Project standard |
| TypeScript | Project version | Type safety | Project standard |
| @tanstack/react-query | Project version | Server state management, cache | Project standard; shots + elements already cached |
| FastAPI | Project version | Backend API framework | Project standard |
| SQLAlchemy | Project version | ORM | Project standard |
| OpenAI / Anthropic SDK | Project version | AI provider | `ai_provider.py` abstracts both |
| react-markdown + remark-gfm | Project version | Markdown rendering in chat | Already used by MarkdownContent |
| lucide-react | Project version | Icons | Project standard |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic v2 | Project version | Request/response schemas | New endpoint schemas |
| Tailwind CSS | Project version | Styling | All component styles |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New BreakdownChat component | Extend SidebarChat with mode prop | Rejected by user decision -- SidebarChat is already 737 lines with unused complexity for breakdown context |
| New backend endpoint | Extend existing ai_chat.py router | Either works; new file is cleaner separation since breakdown chat has different context model (shots/elements vs phases/subsections) |
| Dedicated session model | Reuse AISession model | AISession has `phase` and `subsection_key` columns (Enum/String) which don't map to breakdown context; recommend a lightweight "breakdown_chat_sessions" approach or adapt AISession with special-case values |

**Installation:** No new packages needed. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/api/endpoints/
    breakdown_chat.py           # NEW: Breakdown chat streaming endpoint

frontend/src/components/Breakdown/
    BreakdownChat.tsx            # NEW: Main chat component
    ShotProposalCard.tsx         # NEW: Confirmation card for shot create/modify
    BreakdownLayout.tsx          # MODIFY: Replace placeholder with <BreakdownChat>

frontend/src/lib/
    api.tsx                      # MODIFY: Add breakdown chat API functions
    constants.ts                 # MODIFY: Add QUERY_KEYS and STORAGE_KEYS entries

frontend/src/types/
    index.ts                     # MODIFY: Add BreakdownChatMessage type (optional)

backend/app/models/
    schemas.py                   # MODIFY: Add BreakdownChatMessageCreate schema
```

### Pattern 1: Context Injection via Request Body
**What:** Frontend serializes shots + elements from React Query cache and sends them in every chat request body.
**When to use:** Every chat message send.
**Example:**
```typescript
// Source: Follows existing buildFieldContext() pattern in SidebarChat.tsx (line 260-285)
const buildBreakdownContext = () => {
  const shots = queryClient.getQueryData<Shot[]>(QUERY_KEYS.SHOTS(projectId)) || [];
  const elements = queryClient.getQueryData<BreakdownElement[]>(
    QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId)
  ) || [];

  return {
    shots: shots.map(s => ({
      id: s.id,
      shot_number: s.shot_number,
      scene_item_id: s.scene_item_id,
      fields: s.fields,
      source: s.source,
    })),
    elements: elements.map(e => ({
      id: e.id,
      category: e.category,
      name: e.name,
      description: e.description,
    })),
  };
};
```

### Pattern 2: SSE Streaming with Done Event Action Payload
**What:** Backend streams text chunks via SSE, then sends a final `done` event containing optional shot actions.
**When to use:** Every AI response.
**Example:**
```python
# Source: Follows existing action_stream() pattern in ai_chat.py (line 417-549)
async def breakdown_chat_stream():
    full_text = ""
    # Phase 1: Stream conversational text
    async for chunk in chat_completion_stream(messages=messages):
        full_text += chunk
        yield f"data: {json.dumps({'chunk': chunk})}\n\n"

    # Phase 2: Extract shot action (if any) via JSON-mode call
    shot_action = await extract_shot_action(
        user_message=content,
        assistant_message=full_text,
        shots_context=shots_context,
        elements_context=elements_context,
    )

    # Phase 3: Save message + return done event
    # shot_action = None | {"type": "create", "data": {...}} | {"type": "modify", "shot_id": "...", "data": {...}}
    yield f"data: {json.dumps({'done': True, 'shot_action': shot_action})}\n\n"
    yield "data: [DONE]\n\n"
```

### Pattern 3: Confirmation-Then-Execute (ShotProposalCard)
**What:** AI proposes a shot action; frontend renders a confirmation card; user confirms; frontend calls existing shot CRUD API.
**When to use:** When AI response includes a shot_action payload.
**Example:**
```typescript
// Source: Follows existing ProposedChangesCard pattern in SidebarChat.tsx (line 56-115)
// On confirm (create):
const handleCreateShot = async () => {
  setApplying(true);
  try {
    const result = await api.createShot(projectId, {
      scene_item_id: shotAction.data.scene_item_id,
      shot_number: shotAction.data.shot_number,
      fields: shotAction.data.fields,
      source: 'ai',
    });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId) });
    // Post confirmation message to local chat
    addLocalMessage({ role: 'assistant', content: `Shot #${result.shot_number} created` });
  } finally {
    setApplying(false);
    setShotAction(null);
  }
};
```

### Pattern 4: Session Management (Lightweight)
**What:** Reuse the existing `AISession` model with a special-case phase value for breakdown chat sessions, or create a dedicated lightweight session table.
**When to use:** Session init on component mount.
**Recommendation:** Create a new "breakdown_chat_sessions" table or adapt by adding a `session_type` column. However, the simplest approach is to use the existing AISession model with a sentinel phase value (e.g., `phase="breakdown"`) and `subsection_key="chat"`. This avoids a new migration but requires the `phase` column to accept non-PhaseType values.

**Preferred approach:** Since AISession uses a `PhaseType` Enum column (`Enum(PhaseType)`), we cannot store arbitrary strings. Options:
1. **Add "breakdown" to PhaseType enum** -- requires an ALTER TYPE migration
2. **Create a new lightweight table** -- cleanest; no enum pollution
3. **Use in-memory sessions (no persistence)** -- simplest for MVP; messages live only in frontend state; no session/message history across page reloads

**Recommendation:** Option 3 (in-memory sessions) for MVP simplicity. The breakdown chat is a transient tool, not a persistent conversation. This eliminates backend session management entirely. The backend endpoint is stateless: it receives the full message history + context in each request and streams back a response. This is the pattern used by many chat UIs and avoids the session model problem entirely.

### Anti-Patterns to Avoid
- **Adding mode prop to SidebarChat:** User explicitly decided against this. SidebarChat is 737 lines with template-specific logic (field_groups, phase/subsection binding, agent panel). Adding breakdown mode would create a god component.
- **Storing shot context on the backend session:** The shots change frequently (user edits in center panel). Sending fresh context with each message ensures the AI always has current data.
- **Mutating shots directly in the AI endpoint:** The AI should ONLY propose; the frontend MUST confirm then call the existing shots CRUD API. This keeps the CRUD path as the single source of truth.
- **Duplicating ProposedChangesCard:** The CONTEXT.md says to "reuse" it. However, ProposedChangesCard is currently defined inside SidebarChat.tsx (not exported). It will need to be either extracted to a shared file or the new `ShotProposalCard` can follow the same pattern but with shot-specific fields (which is what the UI-SPEC defines).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE streaming | Custom WebSocket protocol | FastAPI `StreamingResponse` + `text/event-stream` | Already established pattern in ai_chat.py; frontend reader pattern in api.tsx |
| Markdown rendering | Custom markdown parser | `MarkdownContent` component (react-markdown + remark-gfm) | Already built and shared |
| Shot CRUD | Direct DB calls from chat endpoint | Existing `api.createShot()` / `api.updateShot()` from frontend | Shot validation, ownership checks already handled in shots.py |
| React Query cache invalidation | Manual state updates | `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId) })` | Pattern already used throughout app |
| Panel resizing/collapse | Custom resize logic in BreakdownChat | BreakdownLayout already handles panel resize + BreakdownPanel handles collapse | BreakdownChat renders inside the content area |
| AI provider abstraction | Direct OpenAI/Anthropic calls | `chat_completion_stream` from `ai_provider.py` | Handles provider switching, lazy client init |

**Key insight:** Nearly every technical component needed already exists in the codebase. The work is integration and adaptation, not creation from scratch.

## Common Pitfalls

### Pitfall 1: AISession PhaseType Enum Mismatch
**What goes wrong:** The existing `AISession.phase` column uses `Enum(PhaseType)` which only allows `idea`, `story`, `scenes`, `write`. Cannot store `"breakdown"`.
**Why it happens:** The AI session model was designed for template-based screenwriting phases, not breakdown mode.
**How to avoid:** Use stateless/in-memory session approach. Send full message history in each request. No backend session persistence needed for MVP breakdown chat.
**Warning signs:** `DataError` or `InvalidParameterValue` from PostgreSQL when trying to insert a non-enum value.

### Pitfall 2: Stale Context Between Chat Messages
**What goes wrong:** User creates/modifies a shot in the center ShotlistPanel, but the next chat message still sends old shot data because the React Query cache was invalidated but the closure captured the old value.
**Why it happens:** `buildBreakdownContext()` captures React Query cache at call time. If a mutation just invalidated the cache, the refetch may not have completed.
**How to avoid:** Call `buildBreakdownContext()` inside the send handler (not in an effect or ref). React Query's `getQueryData` returns the latest cache synchronously.
**Warning signs:** AI response references shots that were just deleted or doesn't know about just-created shots.

### Pitfall 3: ProposedChangesCard Import Issue
**What goes wrong:** Trying to import `ProposedChangesCard` from `SidebarChat.tsx` fails because it's not exported.
**Why it happens:** ProposedChangesCard is defined as a local function component inside SidebarChat.tsx (line 56-115) without `export`.
**How to avoid:** Build `ShotProposalCard` as a dedicated component per the UI-SPEC. It has shot-specific fields anyway (shot number, scene association, shot fields) which differ from the template field-update card.
**Warning signs:** Import errors during build.

### Pitfall 4: JSONB Fields Replacement on Update
**What goes wrong:** When AI proposes modifying a shot's fields, the frontend calls `updateShot` with only the changed fields, but the PUT endpoint REPLACES the entire `fields` JSONB column.
**Why it happens:** Existing decision from Phase 20: "PUT fields replacement (not merge) -- consistent with JSONB column semantics".
**How to avoid:** Frontend must spread existing fields before applying changes: `fields: { ...existingShot.fields, ...proposedChanges }`.
**Warning signs:** Shot loses all fields except the ones AI modified.

### Pitfall 5: Large Context Payload
**What goes wrong:** Sending all shots + all elements in every request body could hit the `RequestSizeLimitMiddleware` (25MB) or slow down requests.
**Why it happens:** Projects with many shots (50+) and elements (100+) produce large JSON payloads.
**How to avoid:** Serialize only essential fields (id, shot_number, scene_item_id, fields for shots; id, category, name, description for elements). Skip metadata, media, timestamps. The current 25MB limit is very generous; this is unlikely to be a real issue for MVP but worth being deliberate about serialization.
**Warning signs:** 413 Request Entity Too Large responses.

### Pitfall 6: BreakdownPanel Overflow Conflict
**What goes wrong:** BreakdownChat has its own `overflow-y-auto` on the message area, but `BreakdownPanel` also has `overflow-auto` on the content wrapper (line 74).
**Why it happens:** Nested scroll containers.
**How to avoid:** BreakdownChat should use `h-full flex flex-col` and the message area should be `flex-1 overflow-y-auto`. BreakdownPanel's content wrapper may need `overflow-hidden` instead of `overflow-auto` for the chat case, OR BreakdownChat fills it with `h-full` which prevents double scrolling.
**Warning signs:** Double scrollbars, janky scroll behavior.

## Code Examples

### Backend Endpoint: Breakdown Chat Stream
```python
# Source: Pattern from ai_chat.py stream endpoint (line 325-549)

@router.post("/{project_id}/stream")
async def breakdown_chat_stream(
    project_id: UUID,
    body: BreakdownChatRequest,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a breakdown-aware AI response with optional shot actions."""
    project = _verify_project_ownership(db, project_id, current_user.id)

    # Build system prompt with shots + elements context
    system_prompt = _build_breakdown_system_prompt(
        shots=body.shots_context,
        elements=body.elements_context,
    )

    async def generate():
        full_text = ""
        try:
            async for chunk in chat_completion_stream(
                messages=[
                    {"role": "system", "content": system_prompt},
                    *body.message_history,
                    {"role": "user", "content": body.content},
                ],
                temperature=0.7,
                max_tokens=2000,
            ):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Breakdown chat streaming error: {e}")
            full_text = full_text or "I had trouble generating a response."

        # Extract shot action from the AI's response
        shot_action = None
        try:
            shot_action = await _extract_shot_action(
                body.content, full_text, body.shots_context, body.elements_context
            )
        except Exception as e:
            logger.error(f"Shot action extraction error: {e}")

        yield f"data: {json.dumps({'done': True, 'shot_action': shot_action})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Frontend: BreakdownChat Send Handler
```typescript
// Source: Pattern from SidebarChat.tsx handleSend (line 323-358) + handleAgentSend (line 380-416)

const handleSend = async () => {
  const content = input.trim();
  if (!content || isStreaming) return;

  setInput('');
  setIsStreaming(true);
  setStreamingText('');
  setErrorText('');
  setShotAction(null);

  // Add user message to local state
  const userMsg = { id: Date.now().toString(), role: 'user', content, created_at: new Date().toISOString() };
  setMessages(prev => [...prev, userMsg]);

  const breakdownContext = buildBreakdownContext();

  try {
    await api.sendBreakdownChatStream(
      projectId,
      content,
      messages.map(m => ({ role: m.role, content: m.content })),
      breakdownContext,
      (chunk) => setStreamingText(prev => prev + chunk),
      (data) => {
        if (data.shot_action) {
          setShotAction(data.shot_action);
        }
      },
    );
  } catch (err) {
    setErrorText(err instanceof Error ? err.message : 'Something went wrong. Try sending your message again.');
  } finally {
    // Move streaming text to message list
    if (streamingTextRef.current) {
      setMessages(prev => [...prev, {
        id: Date.now().toString(), role: 'assistant',
        content: streamingTextRef.current, created_at: new Date().toISOString(),
      }]);
    }
    setStreamingText('');
    setIsStreaming(false);
  }
};
```

### Frontend: API Client Function
```typescript
// Source: Pattern from api.tsx sendChatMessageStream (line 381-434) + sendAIMessageStream (line 611-667)

async sendBreakdownChatStream(
  projectId: string,
  content: string,
  messageHistory: Array<{ role: string; content: string }>,
  breakdownContext: { shots: any[]; elements: any[] },
  onChunk: (chunk: string) => void,
  onDone: (data: { shot_action?: ShotAction | null }) => void,
): Promise<void> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT);
  try {
    const response = await fetch(`${API_BASE_URL}/breakdown-chat/${projectId}/stream`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        content,
        message_history: messageHistory,
        shots_context: breakdownContext.shots,
        elements_context: breakdownContext.elements,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!response.ok) throw new Error('Failed to send breakdown chat message');

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') return;
        try {
          const data = JSON.parse(payload);
          if (data.chunk) onChunk(data.chunk);
          else if (data.done) onDone({ shot_action: data.shot_action ?? null });
        } catch { /* skip */ }
      }
    }
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') throw new Error('Request timeout');
    throw error;
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Backend session persistence for all chat | Stateless request pattern for breakdown chat | This phase | No migration needed; simpler architecture for transient conversations |
| Single SidebarChat with mode switching | Dedicated component per context (SidebarChat for templates, BreakdownChat for breakdown) | CONTEXT.md decision | Avoids god-component; each chat has its own lifecycle |
| ProposedChangesCard for field updates only | ShotProposalCard for shot create/modify actions | This phase | New card type with shot-specific fields and scene association |

**Deprecated/outdated:**
- STATE.md says "Extend SidebarChat -- don't create separate chat component" (from v3.0 research). This was overridden by the Phase 24 CONTEXT.md discussion which explicitly decided on a new `BreakdownChat` component.

## Open Questions

1. **Backend endpoint path**
   - What we know: CONTEXT.md says "Extend existing `/api/ai_chat/` or new breakdown-specific route"
   - What's unclear: Whether to add routes to the existing `ai_chat.py` router or create a new `breakdown_chat.py`
   - Recommendation: New `breakdown_chat.py` file, registered at `/api/breakdown-chat` prefix. Clean separation from template AI which has PhaseType/subsection coupling.

2. **Message persistence**
   - What we know: SidebarChat persists messages via AISession + AIMessage models. Breakdown chat uses stateless pattern.
   - What's unclear: Whether users expect conversation history to survive page reload
   - Recommendation: No persistence for MVP. Chat is transient. This aligns with the "clear" button behavior (instant, no confirmation) in the UI-SPEC.

3. **Shot action extraction reliability**
   - What we know: The AI needs to determine whether a response implies a shot action (create/modify)
   - What's unclear: How reliably GPT-4 will produce structured shot actions from conversational responses
   - Recommendation: Use a two-phase approach (same as existing action mode): stream conversational text first, then make a second JSON-mode call to extract any shot action. The system prompt should explicitly define when to produce shot actions.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) |
| Config file | `backend/pytest.ini` or `pyproject.toml` |
| Quick run command | `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py -x` |
| Full suite command | `cd backend && python -m pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHAT-01 | Right sidebar renders BreakdownChat | manual-only | Visual verification (React component rendering) | N/A |
| CHAT-02 | AI has shotlist context | unit | `pytest app/tests/test_breakdown_chat_api.py::test_stream_includes_shots_context -x` | Wave 0 |
| CHAT-03 | AI has breakdown elements context | unit | `pytest app/tests/test_breakdown_chat_api.py::test_stream_includes_elements_context -x` | Wave 0 |
| CHAT-04 | AI can create shots with confirmation | integration | `pytest app/tests/test_breakdown_chat_api.py::test_shot_create_action -x` | Wave 0 |
| CHAT-05 | AI can modify shots with confirmation | integration | `pytest app/tests/test_breakdown_chat_api.py::test_shot_modify_action -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py -x`
- **Per wave merge:** `cd backend && python -m pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_breakdown_chat_api.py` -- covers CHAT-02 through CHAT-05 (backend endpoint tests)
- [ ] Verify existing test infrastructure supports new endpoint (conftest.py fixtures should work with new router)
- [ ] CHAT-01 is manual-only (visual rendering verification) -- no automated test needed

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/Shared/SidebarChat.tsx` -- Full existing chat pattern: streaming, session management, ProposedChangesCard, field context building (737 lines read in full)
- `backend/app/api/endpoints/ai_chat.py` -- Existing AI chat endpoint: SSE streaming, two-phase action mode, session management (full read)
- `backend/app/api/endpoints/shots.py` -- Shot CRUD: create, update, list, delete, reorder (full read)
- `frontend/src/lib/api.tsx` -- Full API client: all shot/element/AI functions (1009 lines read)
- `frontend/src/types/index.ts` -- Shot, ShotCreate, ShotUpdate, ShotFields, BreakdownElement types (full read)
- `frontend/src/lib/constants.ts` -- QUERY_KEYS.SHOTS, QUERY_KEYS.BREAKDOWN_ELEMENTS, STORAGE_KEYS (full read)
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` -- Right panel placeholder location, panel resize, projectId prop (full read)
- `frontend/src/components/Breakdown/BreakdownPanel.tsx` -- Panel wrapper with collapse/expand behavior (full read)
- `backend/app/models/database.py` -- AISession model (PhaseType enum constraint), Shot model, schema (read relevant sections)
- `backend/app/models/schemas.py` -- ShotCreate, ShotUpdate, ShotResponse schemas (full read)
- `backend/app/services/ai_provider.py` -- chat_completion_stream function (read)
- `frontend/src/components/Shared/MarkdownContent.tsx` -- Reusable markdown renderer (full read)
- `frontend/src/index.css` -- `.breakdown-mode` CSS variables (read)
- `frontend/tailwind.config.js` -- Animation keyframes: fade-up, scale-in, fade-in (read)
- `.planning/phases/24-ai-chat-for-breakdown/24-UI-SPEC.md` -- Visual contract (full read)
- `.planning/phases/24-ai-chat-for-breakdown/24-CONTEXT.md` -- User decisions (full read)

### Secondary (MEDIUM confidence)
- `backend/app/services/template_ai_service.py` -- Two-phase streaming pattern (stream + extract) for chat_action_stream_message / chat_action_extract_updates
- `backend/app/main.py` -- Router registration pattern for new endpoints

### Tertiary (LOW confidence)
- None. All findings verified from primary sources in the codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use; no new dependencies
- Architecture: HIGH - All patterns directly observed in existing codebase (SidebarChat, ai_chat.py, shots.py)
- Pitfalls: HIGH - Identified from actual code analysis (PhaseType enum, JSONB replacement, overflow nesting)
- Shot action extraction approach: MEDIUM - Two-phase pattern is proven for field updates but shot actions add complexity (need to identify which shot to modify, handle scene association)

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable; all findings are from project codebase, not external libraries)
