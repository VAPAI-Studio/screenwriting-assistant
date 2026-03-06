# Deferred Items — Phase 02 Frontend Snippets Page

## Pre-existing TypeScript Errors (Out of Scope)

These errors existed before plan 02-04 execution and are in files not modified by this plan.

### AgentManager.tsx
- `api.createAgent` does not exist on api object
- `api.deleteAgent` does not exist on api object
- `agent_type`, `tags_filter` fields missing from Agent type
- `ORCHESTRATOR_PROMPT_TEMPLATE` not exported from constants

### BookManager.tsx
- `Book.progress`, `Book.chapters_total`, `Book.chapters_processed` fields missing from Book type
- BookStatus type missing 'paused' value

### ChatSidebar.tsx
- `ConsultedAgent` not exported from types
- `ChatMessage.consulted_agents` missing from ChatMessage type
- `api.sendChatMessageStream` missing (should be sendAIMessageStream)
- `Agent.agent_type`, `Agent.tags_filter` missing

### SidebarChat.tsx
- Same `ConsultedAgent`, `consulted_agents`, `sendChatMessageStream` issues
- `STORAGE_KEYS.SIDEBAR_CHAT_PANEL_MODE` missing from constants
- `sendAIMessageStream` called with wrong argument count (6 instead of 5)

These should be addressed in a dedicated type-alignment plan.
