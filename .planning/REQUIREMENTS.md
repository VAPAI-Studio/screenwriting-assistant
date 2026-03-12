# Requirements: Agent Orchestration Pipeline

**Defined:** 2026-03-11
**Core Value:** Agents you create actually influence the screenplay you generate — they don't just sit idle waiting for you to chat with them.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Pipeline Composition

- [x] **COMP-01**: AI analyzes all agents and maps each to relevant pipeline steps when an agent is created, edited, or deleted
- [x] **COMP-02**: Pipeline mappings stored in dedicated `agent_pipeline_maps` DB table with efficient lookup by phase/step
- [x] **COMP-03**: Re-composition only triggers when semantic fields change (system prompt, type), not cosmetic fields (name, icon, color)
- [x] **COMP-04**: GET endpoint exposes current pipeline mapping for frontend consumption

### Generation Review Loop

- [ ] **REVW-01**: Agent review middleware injected in `wizards.py` between `wizard_generate()` and `apply_wizard_result_to_db()`
- [ ] **REVW-02**: All agents mapped to a step review the generated output in parallel via `asyncio.gather`
- [ ] **REVW-03**: AI merge call synthesizes all agent feedback into refined output matching the expected wizard result schema
- [ ] **REVW-04**: If no agents are mapped to a step, generation passes through unchanged (zero-impact bypass)
- [x] **REVW-05**: Fix shared DB session bug in existing `run_multi_agent_review` for safe concurrent async context

### Frontend Pipeline Visualization

- [ ] **TREE-01**: Collapsible tree view component showing which agents activate at which pipeline steps
- [ ] **TREE-02**: Tree view auto-refreshes when agents are created, edited, or deleted
- [ ] **TREE-03**: Per-agent toggle to exclude/include individual agents from the pipeline

### YOLO Integration

- [ ] **YOLO-01**: Agent reviews fire during YOLO auto-generation flow through same middleware path
- [ ] **YOLO-02**: Token budget controls — configurable max agents per step and relevance threshold

## v2 Requirements

### Pipeline Composition

- **COMP-05**: Confidence scores per mapping (AI rates agent relevance 0-1 per step)
- **COMP-06**: Mapping versioning and history tracking

### Generation Review Loop

- **REVW-06**: Per-agent audit trail showing what each agent suggested before merge
- **REVW-07**: Explicit merge conflict-resolution rules in prompt engineering

### Frontend Pipeline Visualization

- **TREE-04**: Visual indicators showing which agents are actively reviewing during generation
- **TREE-05**: Per-step cost estimation display

### YOLO Integration

- **YOLO-03**: Progress indicators showing which agents are reviewing during auto-generation
- **YOLO-04**: Per-step cost estimation before YOLO run begins

## Out of Scope

| Feature | Reason |
|---------|--------|
| Agent-to-agent communication | Agents review independently — no inter-agent dialogue |
| User approval gates for reviews | Mapping is informational, reviews are automatic |
| Custom pipeline step ordering by users | AI decides optimal placement |
| Per-flow agent toggles (manual vs YOLO) | Agents activate equally in both flows |
| Sequential agent chaining | Parallel + merge avoids bias compounding |
| Real-time per-agent streaming | Over-complex for v1, undermines merge strategy |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| COMP-01 | Phase 2 + Phase 3 | Complete |
| COMP-02 | Phase 1 | Complete |
| COMP-03 | Phase 2 + Phase 3 | Complete |
| COMP-04 | Phase 3 | Complete |
| REVW-01 | Phase 5 + Phase 6 | Pending |
| REVW-02 | Phase 5 | Pending |
| REVW-03 | Phase 5 | Pending |
| REVW-04 | Phase 5 | Pending |
| REVW-05 | Phase 4 | Complete |
| TREE-01 | Phase 7 | Pending |
| TREE-02 | Phase 7 | Pending |
| TREE-03 | Phase 7 | Pending |
| YOLO-01 | Phase 8 | Pending |
| YOLO-02 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-11 after roadmap creation — all 14 requirements mapped*
