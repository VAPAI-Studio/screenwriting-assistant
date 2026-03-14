# Requirements: Screenwriting Assistant

**Defined:** 2026-03-11
**Updated:** 2026-03-13 (v2.0 Script Breakdown)

## v1 Requirements (Agent Orchestration Pipeline) -- COMPLETE

### Pipeline Composition

- [x] **COMP-01**: AI analyzes all agents and maps each to relevant pipeline steps when an agent is created, edited, or deleted
- [x] **COMP-02**: Pipeline mappings stored in dedicated `agent_pipeline_maps` DB table with efficient lookup by phase/step
- [x] **COMP-03**: Re-composition only triggers when semantic fields change (system prompt, type), not cosmetic fields (name, icon, color)
- [x] **COMP-04**: GET endpoint exposes current pipeline mapping for frontend consumption

### Generation Review Loop

- [x] **REVW-01**: Agent review middleware injected in `wizards.py` between `wizard_generate()` and `apply_wizard_result_to_db()`
- [x] **REVW-02**: All agents mapped to a step review the generated output in parallel via `asyncio.gather`
- [x] **REVW-03**: AI merge call synthesizes all agent feedback into refined output matching the expected wizard result schema
- [x] **REVW-04**: If no agents are mapped to a step, generation passes through unchanged (zero-impact bypass)
- [x] **REVW-05**: Fix shared DB session bug in existing `run_multi_agent_review` for safe concurrent async context

### Frontend Pipeline Visualization

- [x] **TREE-01**: Collapsible tree view component showing which agents activate at which pipeline steps
- [x] **TREE-02**: Tree view auto-refreshes when agents are created, edited, or deleted
- [x] **TREE-03**: Per-agent toggle to exclude/include individual agents from the pipeline

### YOLO Integration

- [x] **YOLO-01**: Agent reviews fire during YOLO auto-generation flow through same middleware path
- [x] **YOLO-02**: Token budget controls -- configurable max agents per step and relevance threshold

## v2 Requirements (Script Breakdown)

**Core Value:** AI extracts production elements from the screenplay into master lists, users refine them, and changes sync bidirectionally on save/generate.

### Data Foundation

- [x] **BKDN-01**: `breakdown_elements` table with category column, JSONB metadata, `user_modified` flag, `is_deleted` soft-delete, unique constraint on `(project_id, category, name)`
- [x] **BKDN-02**: `element_scene_links` junction table linking breakdown elements to scene ListItems with context notes and source tracking
- [x] **BKDN-03**: `breakdown_runs` audit table tracking extraction runs (status, element counts, errors, timestamps)
- [x] **BKDN-04**: `breakdown_stale` boolean column on projects table, set when script content changes

### AI Extraction

- [x] **EXTR-01**: AI extraction service analyzes screenplay content + character names to produce structured JSON of production elements across 5 categories (character, location, prop, wardrobe, vehicle)
- [x] **EXTR-02**: Extraction uses structured outputs (schema-enforced JSON) via upgraded OpenAI/Anthropic SDKs for guaranteed response shape
- [x] **EXTR-03**: Deduplication -- same element described differently across scenes maps to one master list entry with canonical name
- [x] **EXTR-04**: Low temperature (0.1-0.2) for extraction calls; only extract elements physically present on screen, not mentioned in dialogue or backstory
- [x] **EXTR-05**: Scene linking -- each extracted element tracks which scenes it appears in by matching to scene ListItem records

### User Refinement & Sync

- [x] **SYNC-01**: Re-extraction preserves user modifications -- elements with `user_modified=true` keep their user-edited name, description, and metadata
- [x] **SYNC-02**: Soft-deleted elements (`is_deleted=true`) are not resurrected by re-extraction
- [x] **SYNC-03**: Staleness detection -- saving screenplay content or regenerating scenes sets `breakdown_stale=true` on the project
- [x] **SYNC-04**: Re-extraction clears the stale flag and creates a new `breakdown_runs` audit record
- [ ] **SYNC-05**: Reverse sync is user-initiated -- "Add to Characters" action from breakdown creates a ListItem in the characters phase, not automatic script modification

### API

- [x] **API-01**: `POST /api/breakdown/extract/{project_id}` -- trigger AI extraction, return run result
- [x] **API-02**: `GET /api/breakdown/elements/{project_id}` -- list elements filtered by category, excluding soft-deleted by default
- [x] **API-03**: `PUT /api/breakdown/element/{element_id}` -- update element, sets `user_modified=true`
- [x] **API-04**: `POST /api/breakdown/elements/{project_id}` -- create element manually with `source='user'`
- [x] **API-05**: `DELETE /api/breakdown/element/{element_id}` -- soft-delete element
- [x] **API-06**: `POST/DELETE /api/breakdown/element/{element_id}/scenes` -- add/remove scene links
- [x] **API-07**: `GET /api/breakdown/summary/{project_id}` -- breakdown summary with staleness, category counts, last run info

### Frontend

- [ ] **UI-01**: Dedicated Breakdown page accessible from project workspace navigation (not a template phase)
- [ ] **UI-02**: Category tabs (Characters, Locations, Props, Wardrobe, Vehicles) with count badges
- [ ] **UI-03**: Master list per category with element name, description, scene count, source badge (AI/User), user-modified indicator
- [ ] **UI-04**: Inline editing of element names and descriptions; expand/collapse for details
- [ ] **UI-05**: Scene chips on each element showing linked scenes; clickable to navigate to scene
- [ ] **UI-06**: "Extract Breakdown" button for first extraction; "Refresh" button with staleness banner when breakdown is outdated
- [ ] **UI-07**: Add element dialog for manually creating new elements
- [ ] **UI-08**: Empty state with clear CTA when no breakdown exists yet

## Out of Scope (v2)

| Feature | Reason |
|---------|--------|
| Scheduling/calendar integration | Separate domain; deferred to future milestone |
| Budget line items and cost tracking | Requires rate cards, union rules; separate domain |
| Department assignments | Requires crew management system |
| Day/Night and INT/EXT classification | Scene header parsing not mature yet |
| Full 23-category Movie Magic parity | 5 core categories sufficient for v2; extensible design |
| Real-time sync (as user types) | Sync on save/generate per PROJECT.md; avoids conflict complexity |
| Export to industry formats | PDF/Movie Magic export deferred |
| Color-coded text highlighting in script | Major frontend undertaking; deferred |
| Automatic script rewriting from breakdown edits | Creates circular sync loops; reverse sync is advisory/user-initiated |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-01 | Phase 2 | Complete |
| COMP-02 | Phase 1 | Complete |
| COMP-03 | Phase 2 | Complete |
| COMP-04 | Phase 3 | Complete |
| REVW-01 | Phase 5, Phase 6 | Complete |
| REVW-02 | Phase 5 | Complete |
| REVW-03 | Phase 5 | Complete |
| REVW-04 | Phase 5 | Complete |
| REVW-05 | Phase 4 | Complete |
| TREE-01 | Phase 7 | Complete |
| TREE-02 | Phase 7 | Complete |
| TREE-03 | Phase 7 | Complete |
| YOLO-01 | Phase 8 | Complete |
| YOLO-02 | Phase 8 | Complete |
| BKDN-01 | Phase 9 | Complete |
| BKDN-02 | Phase 9 | Complete |
| BKDN-03 | Phase 9 | Complete |
| BKDN-04 | Phase 9 | Complete |
| EXTR-01 | Phase 11 | Complete |
| EXTR-02 | Phase 11 | Complete |
| EXTR-03 | Phase 11 | Complete |
| EXTR-04 | Phase 11 | Complete |
| EXTR-05 | Phase 11 | Complete |
| SYNC-01 | Phase 11 | Complete |
| SYNC-02 | Phase 11 | Complete |
| SYNC-03 | Phase 12 | Complete |
| SYNC-04 | Phase 12 | Complete |
| SYNC-05 | Phase 14 | Pending |
| API-01 | Phase 10 | Complete |
| API-02 | Phase 10 | Complete |
| API-03 | Phase 10 | Complete |
| API-04 | Phase 10 | Complete |
| API-05 | Phase 10 | Complete |
| API-06 | Phase 10 | Complete |
| API-07 | Phase 10 | Complete |
| UI-01 | Phase 13 | Pending |
| UI-02 | Phase 13 | Pending |
| UI-03 | Phase 13 | Pending |
| UI-04 | Phase 13 | Pending |
| UI-05 | Phase 13 | Pending |
| UI-06 | Phase 13 | Pending |
| UI-07 | Phase 13 | Pending |
| UI-08 | Phase 13 | Pending |

**Coverage:**
- v1 requirements: 14 total -- all complete
- v2 requirements: 29 total -- all mapped to phases
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*v2 requirements added: 2026-03-13*
*Traceability updated: 2026-03-13 (phases 9-14 assigned)*
