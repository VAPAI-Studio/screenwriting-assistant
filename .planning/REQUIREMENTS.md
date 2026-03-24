# Requirements: Screenwriting Assistant

**Defined:** 2026-03-24
**Milestone:** v4.2 — TV Show Mode
**Core Value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## v4.2 Requirements

### Show Management

- [x] **SHOW-01**: User can create a new show with a title and description
- [ ] **SHOW-02**: Home page displays Shows and standalone Films as separate sections
- [ ] **SHOW-03**: User can open a show to view its series bible and episode list
- [x] **SHOW-04**: User can edit a show's title and description, and delete a show

### Series Bible

- [x] **BIBL-01**: Each show has four bible sections: Characters, World/Setting, Season Arc, Tone & Style
- [x] **BIBL-02**: User can write and edit each bible section as freeform text
- [x] **BIBL-03**: Each show has a target episode duration setting (10 min, 22 min, 44 min, 60 min, or custom)
- [ ] **BIBL-04**: Bible content (all four sections) and episode duration are automatically injected into AI context for episode script generation, agent reviews, and breakdown extraction

### Episodes

- [ ] **EPIS-01**: User can create a new episode inside a show with an episode number and title
- [ ] **EPIS-02**: Each episode has the full screenplay → breakdown → shotlist → storyboard pipeline identical to standalone projects
- [ ] **EPIS-03**: User can view, open, and delete episodes from the show page
- [ ] **EPIS-04**: Existing standalone projects are unaffected — no data migration required
- [ ] **EPIS-05**: Episode views include breadcrumb navigation back to the parent show (Show > Episode N: Title)

## v5.0 Requirements (Deferred)

### AI Shotlist Generation (deferred from v3.1)

- **AISG-08**: AI auto-generates shotlist on script save (YOLO mode)
- **AISG-09**: Shot duplication — user can duplicate an existing shot
- **AISG-10**: Batch shot operations (select multiple, bulk delete/move)

## Out of Scope

| Feature | Reason |
|---------|--------|
| PDF/print breakdown export | Different product domain — scheduling/budgeting tools handle this |
| Department assignments per shot | Production management feature, out of MVP scope |
| Real-time AI suggestions while typing | Too complex, staleness-flag pattern is sufficient |
| Movie Magic / Final Draft export | Industry format integration deferred indefinitely |
| Cross-episode shared breakdown elements | High complexity, per-episode breakdown is sufficient for v4.2 |
| Episode scheduling / production calendar | Different product domain |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SHOW-01 | Phase 36 | Complete |
| SHOW-02 | Phase 38 | Pending |
| SHOW-03 | Phase 38 | Pending |
| SHOW-04 | Phase 36 | Complete |
| BIBL-01 | Phase 37 | Complete |
| BIBL-02 | Phase 37 | Complete |
| BIBL-03 | Phase 37 | Complete |
| BIBL-04 | Phase 41 | Pending |
| EPIS-01 | Phase 39 | Pending |
| EPIS-02 | Phase 39 | Pending |
| EPIS-03 | Phase 40 | Pending |
| EPIS-04 | Phase 39 | Pending |
| EPIS-05 | Phase 42 | Pending |

**Coverage:**
- v4.2 requirements: 13 total
- Mapped to phases: 13/13
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after v4.2 roadmap creation*
