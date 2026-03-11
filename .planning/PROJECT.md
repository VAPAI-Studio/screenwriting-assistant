# Agent Orchestration Pipeline

## What This Is

A system that turns user-created AI agents from passive chat companions into active participants in screenplay generation. When a user creates an agent (e.g., a character development expert or a structure coach), an AI orchestrator automatically maps that agent to relevant pipeline steps. During generation — both manual and YOLO — mapped agents review and refine output at each step, making every agent's knowledge actively shape the screenplay.

## Core Value

Agents you create actually influence the screenplay you generate — they don't just sit idle waiting for you to chat with them.

## Requirements

### Validated

- Existing multi-agent system with user-created agents (custom prompts, types, book associations)
- Template-based project system with phases and subsections
- Step-by-step generation pipeline (phase by phase) via `template_ai_service.py`
- AI provider abstraction supporting OpenAI and Anthropic
- RAG-based knowledge retrieval for agent context
- SidebarChat for manual agent interaction
- Book processing with concept extraction and embeddings

### Active

- [ ] AI orchestrator that analyzes all agents and maps them to pipeline steps on agent create/edit
- [ ] Pipeline mapping uses agent type as a hint but AI infers best fit from agent description/prompt
- [ ] Collapsible tree view UI showing which agents activate at which pipeline steps
- [ ] During generation, mapped agents review step output in parallel
- [ ] AI merges parallel agent feedback into refined output before pipeline continues
- [ ] Agent review loop works in both manual Generate Screenplay and YOLO auto-generation flows
- [ ] Pipeline re-composes automatically when agents are created, edited, or deleted

### Out of Scope

- Agent-to-agent communication (agents review independently, don't talk to each other)
- User approval gates for agent reviews (mapping is informational, reviews are automatic)
- Custom pipeline step ordering by users (AI decides optimal placement)
- Per-flow agent toggle (agents activate in both manual and YOLO equally)

## Context

The existing codebase is a screenwriting assistant with a template-based workflow system. Projects use templates (e.g., `short_movie.json`) that define phases (Character, Structure, Scene Creation, etc.) with subsections. Each phase has AI generation capabilities via `template_ai_service.py`.

Users can create AI agents with custom system prompts, types (character, structure, dialogue, etc.), and associate them with books for RAG context. Currently these agents only respond when directly chatted with via `SidebarChat`.

The generation pipeline already works step-by-step through phases. The key change is injecting agent review passes into this existing pipeline — agents become quality gates that refine output before it's finalized.

Key existing files:
- `backend/app/services/agent_service.py` — agent orchestration, knowledge graph
- `backend/app/services/template_ai_service.py` — phase-based content generation
- `backend/app/services/ai_provider.py` — provider abstraction (OpenAI/Anthropic)
- `backend/app/models/database.py` — Agent model with system_prompt_template, type, books
- `backend/app/api/endpoints/agents.py` — agent CRUD endpoints
- `backend/app/api/endpoints/wizards.py` — wizard-driven generation
- `frontend/src/components/Books/AgentManager.tsx` — agent creation UI

## Constraints

- **AI Provider**: Must work with both OpenAI and Anthropic via existing `ai_provider.py`
- **Performance**: Parallel agent reviews add latency — must be reasonable for UX
- **Token Budget**: Each agent review is an additional API call; cost scales with agent count
- **Existing Templates**: Must integrate with existing template phase system without breaking current workflows

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agent reviews run in parallel, not sequential | Reduces latency when multiple agents map to same step | -- Pending |
| AI merges feedback rather than chaining | Avoids compounding bias from sequential review | -- Pending |
| Pipeline re-composes on agent CRUD, not at generation time | Pre-computed mapping avoids generation-time overhead | -- Pending |
| Agent type used as hint, not binding constraint | Gives AI flexibility to place agents optimally based on full prompt analysis | -- Pending |
| Tree view is informational only | Reduces friction — users see the mapping but don't need to approve it | -- Pending |

---
*Last updated: 2026-03-11 after initialization*
