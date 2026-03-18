# Screenwriting Assistant

## What This Is

A full-stack screenwriting assistant that helps users create screenplays using story frameworks (Three-Act, Save the Cat, Hero's Journey) with AI-powered generation, multi-agent review, and production breakdown extraction. Users create AI agents that participate in screenplay generation, and a breakdown system automatically extracts all production elements (characters, locations, props, wardrobe, vehicles) from the script.

## Core Value

From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

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
- ✓ AI analyzes script + project data to extract production elements — v2.0
- ✓ Dedicated breakdown page with master lists per category (Characters, Locations, Props, Wardrobe, Vehicles) — v2.0
- ✓ Each element links to the scenes where it appears — v2.0
- ✓ User can refine AI-generated breakdown (edit, add, remove elements) — v2.0
- ✓ Bidirectional sync between breakdown and script on save/generate — v2.0
- ✓ Reverse sync: user-initiated action pushes breakdown element back to project data — v2.0

### Active

(None — planning next milestone)

### Out of Scope

- Scheduling/calendar integration — deferred to future milestone
- Budget line items and cost tracking — deferred to future milestone
- Department assignments — deferred to future milestone
- Day/Night and INT/EXT scene classification — deferred to future milestone
- Real-time sync (changes propagate on save/generate, not as user types)
- Export to industry formats (PDF breakdown sheets, Movie Magic) — deferred
- Full 23-category Movie Magic parity — 5 core categories sufficient; extensible design

## Context

Shipped v1.0 (agent orchestration, 2026-03-12) and v2.0 (script breakdown, 2026-03-18).

**Current codebase:**
- ~16,267 Python LOC (backend/app), ~8,667 TypeScript LOC (frontend/src)
- Tech stack: FastAPI, PostgreSQL, SQLAlchemy, React, React Query, Tailwind, Radix UI, OpenAI/Anthropic
- 16 total phases shipped, 32 plans

**Key existing files:**
- `backend/app/services/template_ai_service.py` — phase-based content generation
- `backend/app/services/ai_provider.py` — provider abstraction (OpenAI/Anthropic)
- `backend/app/services/breakdown_service.py` — AI extraction pipeline
- `backend/app/models/database.py` — Project, Section, Agent, AgentPipelineMap, BreakdownElement, ElementSceneLink, BreakdownRun models
- `backend/app/api/endpoints/wizards.py` — wizard-driven generation with staleness hooks
- `backend/app/api/endpoints/breakdown.py` — breakdown CRUD and extraction API
- `frontend/src/components/Workspace/ProjectWorkspace.tsx` — main workspace layout
- `frontend/src/components/Breakdown/BreakdownPage.tsx` — breakdown page with category tabs
- `backend/migrations/delta/` — idempotent migrations for Docker zero-downtime upgrades

**Known tech debt:**
- Latent `selectinload` result discarded in breakdown create/update write endpoints
- React Query `LIST_ITEMS` cache not invalidated after reverse sync (5-min lag)

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
| Master list + scene links (not per-scene breakdown) | Gives production overview while preserving scene-level detail | ✓ Good — overview + detail both accessible |
| Bidirectional sync on save/generate (not real-time) | Simpler to implement, avoids conflict resolution complexity | ✓ Good — users accept save-triggered updates |
| AI generates, user refines | Reduces manual work while keeping user in control | ✓ Good — user_modified flag works well |
| Breakdown is NOT a template phase | Cross-cutting derived view with dedicated tables, API, and page | ✓ Good — clean separation |
| VARCHAR(50) category column (not PG ENUM) | Extensible without future migration | ✓ Good |
| Reverse sync is user-initiated only | Avoids circular sync loops; preserves screenplay as source of truth | ✓ Good |
| Single breakdown_elements table with category column + JSONB metadata | Simpler schema vs per-category tables | ✓ Good |
| AI extraction uses structured outputs (schema-enforced JSON) | Guaranteed response shape; dual-provider support | ✓ Good |
| `delta/` directory for incremental migrations | Existing Docker volumes auto-upgrade on restart without volume wipe | ✓ Good |

---
*Last updated: 2026-03-18 after v2.0 milestone*
