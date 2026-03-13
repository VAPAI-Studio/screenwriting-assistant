# Research Summary: v2.0 Script Breakdown

**Synthesized:** 2026-03-13
**Sources:** ARCHITECTURE.md, FEATURES.md, STACK.md, PITFALLS.md

## Executive Summary

The Script Breakdown milestone adds AI-powered production element extraction to the screenwriting assistant. AI analyzes the screenplay + project data and produces master lists of Characters, Locations, Props, Wardrobe, and Vehicles — each linked to scenes. Users refine the AI output, and changes sync bidirectionally on save/generate.

**Core architecture decision:** The breakdown is NOT a template phase. It is a cross-cutting derived view that reads from ALL phases. Dedicated DB tables, API router, service, and frontend page.

## Key Findings

### Stack (No Major Additions)
- **AI extraction** via existing `ai_provider.py` — upgrade to structured outputs (openai>=1.40.0, anthropic>=0.42.0) for schema-enforced JSON responses
- **DeepDiff** (new, backend) for diff-based merge on re-extraction
- **TanStack Table** (new, frontend) for master list views
- **No NLP libraries** — LLMs outperform spaCy/NLTK for domain-specific screenplay extraction
- **No real-time sync** — staleness flag + manual refresh matches PROJECT.md constraints

### Architecture
- **Single `breakdown_elements` table** with category column + JSONB metadata (not table-per-category)
- **`element_scene_links` junction table** linking elements to scene ListItems by UUID
- **`breakdown_runs` audit table** tracking each extraction run
- **`breakdown_stale` boolean on projects** — set when script changes, cleared on re-extraction
- **Staleness lifecycle:** content change → flag → user sees "Refresh" → re-extract with user_modified protection
- **Reverse sync is user-initiated actions** (e.g., "Add to Characters"), not automatic script rewriting
- **Frontend:** Dedicated BreakdownPage with category tabs, ElementCard with inline editing, SceneChips

### Features (MVP Scope)
- **Table stakes:** AI extraction, 5 core categories, master lists, scene-element links, user refinement, re-extraction, dedicated page
- **Differentiators:** Context-aware extraction (uses project phase data, not just script text), extraction possible before screenplay exists
- **Defer:** Scheduling, budgeting, department assignments, 23-category parity, color-coded script highlighting, export

### Critical Pitfalls
1. **AI hallucination** — extraction prompt must specify "on-screen only", use low temperature (0.1-0.2), require line citations
2. **Duplicate elements** — single-call extraction + dedup pass; canonical name + aliases
3. **Circular sync loop** — sync_origin flag, never auto-modify script from breakdown edits
4. **Re-extraction destroys user edits** — `user_modified` flag, `is_deleted` soft-delete, diff-based merge
5. **Scene ID instability** — ListItem IDs are volatile on regeneration; need stable scene references or ON DELETE SET NULL
6. **Context overload** — separate extraction context (screenplay + character names only), not full `_build_project_context`

## Build Order Consensus

All research files converge on this dependency-driven order:

1. **DB Foundation** — migration, models, schemas (everything depends on this)
2. **API CRUD** — endpoints for element CRUD (enables frontend development)
3. **AI Extraction Service** — core extraction with structured outputs, dedup, user_modified protection
4. **Staleness Hooks** — wire into existing save/generate paths
5. **Frontend Page** — BreakdownPage with category tabs, master lists, inline editing
6. **Reverse Sync** — user-initiated actions (breakdown → script), lowest priority

## New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `openai` | >=1.40.0 (upgrade) | Structured output support |
| `anthropic` | >=0.42.0 (upgrade) | Structured output support |
| `deepdiff` | 8.6.1 (new) | Diff-based merge on re-extraction |
| `@tanstack/react-table` | ^8.21.3 (new) | Headless table for master lists |

## Confidence

| Area | Level |
|------|-------|
| Data model design | HIGH |
| API structure | HIGH |
| AI extraction approach | HIGH (prompt tuning needs testing) |
| Sync mechanism | HIGH |
| Frontend structure | HIGH |
| DeepDiff suitability | HIGH |
| Three-way merge algorithm | MEDIUM (needs refinement during implementation) |
| Structured output SDK versions | MEDIUM (exact minimum versions need verification) |

---
*Synthesized from 4 research files: 2026-03-13*
