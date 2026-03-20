# Screenwriting Assistant

## What This Is

A full-stack screenwriting assistant that helps users create screenplays using story frameworks (Three-Act, Save the Cat, Hero's Journey) with AI-powered generation, multi-agent review, and production breakdown. The app has two distinct modes: **Screenwriting** (AI-assisted script writing with agent orchestration) and **Script Breakdown** (shotlist creation, media asset management, and AI chat for production planning).

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
- ✓ Two-mode UI: Screenwriting / Script Breakdown with distinct visual identity (amber vs steel-blue) — v3.0
- ✓ Interactive shotlist: highlight script text → Add Shot → freeform field entry — v3.0
- ✓ Shotlist data model and CRUD API with scene grouping, inline editing, reorder, delete — v3.0
- ✓ Media uploads backend: image/audio upload, WebP thumbnail generation, StaticFiles serving — v3.0
- ✓ Assets panel with breakdown elements grouped by category, media thumbnails, audio playback — v3.0
- ✓ AI chat in Breakdown mode with shotlist + element context awareness, shot create/modify via conversation — v3.0
- ✓ Bidirectional sync between screenplay and shotlist (staleness banner + acknowledge) — v3.0

### Active (v3.1)

- ✓ AI auto-generation of full shotlist from script content with smart merge and user_modified preservation (AUTO-01) — Validated in Phase 26: ai-shotlist-generation-service
- [ ] AI-generated shots display subtle AI badge (sparkle icon) to distinguish from manually-created shots
- [ ] Media deletion UI — delete button for uploaded assets (backend already exists)
- [ ] Drag-and-drop shot reordering replacing arrow buttons (SMGT-01)
- [ ] Scene reorder marks shotlist stale (SYNC-01 gap from v3.0 audit)

### Deferred (v3.2+)

- [ ] Shot duplication and batch operations (SMGT-02, SMGT-03)
- [ ] YOLO auto-generation of shotlist on script save

### Out of Scope

- Scheduling/calendar integration — different product domain
- Budget line items and cost tracking — different product domain
- Department assignments — deferred
- Export to industry formats (PDF breakdown sheets, Movie Magic) — deferred
- Real-time sync (changes propagate on save/generate, not as user types)
- Full 23-category Movie Magic parity — 5 core categories sufficient
- Offline mode — real-time connectivity assumed

## Context

Shipped v1.0 (agent orchestration, 2026-03-12), v2.0 (script breakdown, 2026-03-18), v3.0 (shotlist & production breakdown, 2026-03-20).

**Current codebase:**
- ~30,237 total LOC (Python + TypeScript/TSX)
- Tech stack: FastAPI, PostgreSQL, SQLAlchemy, React, React Query, Tailwind, Radix UI, OpenAI/Anthropic
- 25 total phases shipped, 47 plans
- 108 files changed in v3.0 (+21,108 lines)

**Key files added in v3.0:**
- `backend/app/api/endpoints/shots.py` — Shot CRUD + reorder + staleness status/acknowledge
- `backend/app/api/endpoints/media.py` — File upload, thumbnail generation, list, delete
- `backend/app/api/endpoints/breakdown_chat.py` — Streaming AI chat with context injection + shot action extraction
- `backend/app/services/media_service.py` — Pillow thumbnail generation (300x300 WebP)
- `backend/migrations/delta/002_shotlist_tables.sql` — Idempotent shots/asset_media/shotlist_stale migration
- `frontend/src/components/Breakdown/BreakdownLayout.tsx` — 3-panel root layout with mode class lifecycle
- `frontend/src/components/Breakdown/ShotlistPanel.tsx` — Scene-grouped shotlist with React Query mutations
- `frontend/src/components/Breakdown/ScriptReadView.tsx` — Read-only screenplay with text selection → shot creation
- `frontend/src/components/Breakdown/AssetsPanel.tsx` — Breakdown elements with media display + extract button
- `frontend/src/components/Breakdown/BreakdownChat.tsx` — AI chat with shot proposal confirmation flow
- `frontend/src/components/Breakdown/ShotlistStalenessBar.tsx` — Amber banner + dismiss

**Known tech debt:**
- Latent `selectinload` result discarded in breakdown create/update write endpoints (pre-v3.0)
- React Query `LIST_ITEMS` cache not invalidated after reverse sync — 5-min lag (pre-v3.0)
- `reorder_list_items` does not call `_mark_shotlist_stale` — scene reorder doesn't flag shotlist stale
- 3 pre-existing TypeScript build errors in unrelated files (IndividualEditorView, RepeatableCardsView, SidebarChat)

## Constraints

- **AI Provider**: Must work with both OpenAI and Anthropic via existing `ai_provider.py`
- **Existing Templates**: Must integrate with existing template phase system without breaking current workflows
- **Data Model**: All new tables use `delta/` idempotent migrations for Docker zero-downtime upgrades
- **Sync Pattern**: Staleness-flag pattern (save/generate triggers stale flag, user acknowledges) — not real-time

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agent reviews run in parallel, not sequential | Reduces latency when multiple agents map to same step | ✓ Good |
| AI merges feedback rather than chaining | Avoids compounding bias from sequential review | ✓ Good |
| Pipeline re-composes on agent CRUD, not at generation time | Pre-computed mapping avoids generation-time overhead | ✓ Good |
| Master list + scene links (not per-scene breakdown) | Gives production overview while preserving scene-level detail | ✓ Good |
| Bidirectional sync on save/generate (not real-time) | Simpler, avoids conflict resolution complexity | ✓ Good |
| AI generates, user refines | Reduces manual work while keeping user in control | ✓ Good |
| Breakdown is NOT a template phase | Cross-cutting derived view with dedicated tables, API, and page | ✓ Good |
| VARCHAR(50) category column (not PG ENUM) | Extensible without future migration | ✓ Good |
| Reverse sync is user-initiated only | Avoids circular sync loops; preserves screenplay as source of truth | ✓ Good |
| JSONB `fields` column for shot properties | Freeform schema without per-field columns; all 13 fields optional | ✓ Good |
| Two-mode UI via separate route + CSS class (not conditional render) | Clean separation; breakdown palette applied via `.breakdown-mode` on `<html>` | ✓ Good |
| Shot CRUD stores `script_text` as reference, not displayed column | Links shot to source material without cluttering grid UI | ✓ Good |
| `scene_item_id SET NULL` on scene delete | Shot survives scene deletion; can be reassigned | ✓ Good |
| StaticFiles mount at `/media` for uploaded files | Simple serving without additional infrastructure | ✓ Good |
| Two-phase AI call for breakdown chat (stream then extract action) | Streaming UX preserved; action extraction done post-stream | ✓ Good |

---

## Current Milestone: v3.1 — AI Shotlist Generation

**Goal:** AI generates a complete shotlist from the script, populating all fields, with smart merge that preserves user edits.

**Target features:**
- AI auto-generates shots from script (all fields: size, angle, movement, description, action, scene assignment, ordering, script link)
- Smart merge: user_modified shots preserved on regeneration
- AI badge on auto-generated shots
- Media deletion UI
- Drag-and-drop shot reorder
- Scene reorder marks shotlist stale

---

*Last updated: 2026-03-20 after Phase 26 (ai-shotlist-generation-service) complete*
