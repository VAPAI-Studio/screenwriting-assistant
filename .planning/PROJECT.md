# Screenwriting Assistant

## What This Is

A full-stack screenwriting assistant that helps users create screenplays using story frameworks (Three-Act, Save the Cat, Hero's Journey) with AI-powered generation and review. Users create AI agents that actively participate in screenplay generation, and a production breakdown system automatically extracts and tracks all production elements from the script.

## Core Value

From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## Current Milestone: v2.0 Script Breakdown

**Goal:** AI-powered script breakdown that extracts production elements (characters, locations, props, wardrobe, vehicles) into master lists linked to scenes, with full bidirectional sync between breakdown and script.

**Target features:**
- AI extraction of production elements from script + project data
- Dedicated breakdown page with master lists per category
- Each element tracks which scenes it appears in
- User can refine AI-generated breakdown
- Bidirectional sync: script changes update breakdown on save/generate, breakdown edits propagate back to script

## Requirements

### Validated

- ✓ Template-based project system with phases and subsections — v1.0
- ✓ Step-by-step generation pipeline (phase by phase) via `template_ai_service.py` — v1.0
- ✓ AI provider abstraction supporting OpenAI and Anthropic — v1.0
- ✓ Multi-agent system with user-created agents, pipeline mapping, and review middleware — v1.0
- ✓ RAG-based knowledge retrieval for agent context — v1.0
- ✓ Frontend pipeline tree with per-agent toggles — v1.0
- ✓ YOLO auto-generation with agent reviews and token budgets — v1.0
- ✓ Book processing with concept extraction and embeddings — v1.0

### Active

- [ ] AI analyzes script + project data to extract production elements
- [ ] Dedicated breakdown page with master lists per category (Characters, Locations, Props, Wardrobe, Vehicles)
- [ ] Each element links to the scenes where it appears
- [ ] User can refine AI-generated breakdown (edit, add, remove elements)
- [ ] Bidirectional sync between breakdown and script on save/generate

### Out of Scope

- Scheduling/calendar integration — deferred to future milestone
- Budget line items and cost tracking — deferred to future milestone
- Department assignments — deferred to future milestone
- Day/Night and INT/EXT scene classification — deferred to future milestone
- Real-time sync (changes propagate on save/generate, not as user types)
- Export to industry formats (PDF breakdown sheets, Movie Magic) — deferred

## Context

The existing codebase is a screenwriting assistant with a template-based workflow system. Projects use templates (e.g., `short_movie.json`) that define phases (Character, Structure, Scene Creation, etc.) with subsections. Each phase has AI generation capabilities via `template_ai_service.py`.

v1.0 added an agent orchestration pipeline: AI maps user-created agents to generation steps, agents review output in parallel during generation, and a frontend tree view shows the mappings.

The script breakdown builds on this foundation — the generated screenplay content and all project phase data feed into an AI extraction service that identifies production elements and tracks them across scenes.

Key existing files:
- `backend/app/services/template_ai_service.py` — phase-based content generation
- `backend/app/services/ai_provider.py` — provider abstraction (OpenAI/Anthropic)
- `backend/app/models/database.py` — Project, Section, Agent, AgentPipelineMap models
- `backend/app/api/endpoints/wizards.py` — wizard-driven generation
- `frontend/src/components/Workspace/ProjectWorkspace.tsx` — main workspace layout

## Constraints

- **AI Provider**: Must work with both OpenAI and Anthropic via existing `ai_provider.py`
- **Performance**: Breakdown extraction from a full script may be token-heavy — consider chunked processing
- **Existing Templates**: Must integrate with existing template phase system without breaking current workflows
- **Data Model**: Breakdown elements need their own DB tables with foreign keys to projects and scenes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agent reviews run in parallel, not sequential | Reduces latency when multiple agents map to same step | ✓ Good |
| AI merges feedback rather than chaining | Avoids compounding bias from sequential review | ✓ Good |
| Pipeline re-composes on agent CRUD, not at generation time | Pre-computed mapping avoids generation-time overhead | ✓ Good |
| Master list + scene links (not per-scene breakdown) | Gives production overview while preserving scene-level detail | — Pending |
| Bidirectional sync on save/generate (not real-time) | Simpler to implement, avoids conflict resolution complexity | — Pending |
| AI generates, user refines | Reduces manual work while keeping user in control | — Pending |

---
*Last updated: 2026-03-12 after v2.0 milestone start*
