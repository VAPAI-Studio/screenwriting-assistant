# Requirements: Screenwriting Assistant

**Defined:** 2026-03-20
**Milestone:** v3.1 — AI Shotlist Generation
**Core Value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## v1 Requirements

### AI Shotlist Generation

- [ ] **AISG-01**: User can trigger AI generation of a full shotlist via "Generate Shotlist" button in the breakdown panel
- [ ] **AISG-02**: AI populates all standard shot fields for each generated shot (shot_size, camera_angle, camera_movement, description, action)
- [ ] **AISG-03**: AI assigns each generated shot to the correct scene from the script
- [ ] **AISG-04**: AI determines logical shot ordering within each scene
- [ ] **AISG-05**: AI links each generated shot to the source script passage it covers (script_text field)
- [x] **AISG-06**: Regenerating the shotlist preserves shots the user has manually edited (smart merge via user_modified flag)
- [ ] **AISG-07**: AI-generated shots display a subtle visual indicator (sparkle icon badge) distinguishable from manually-created shots

### Media Management

- [ ] **MDIA-01**: User can delete an uploaded media asset from the assets panel (backend endpoint `DELETE /api/media/{id}` already exists)

### Shot Management

- [ ] **SMGT-01**: User can reorder shots via drag-and-drop within the shotlist panel (replacing existing arrow buttons)

### Staleness Sync

- [ ] **SYNC-01**: Reordering scenes in the screenplay marks the shotlist as stale

## v2 Requirements

### AI Shotlist Generation (deferred)

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

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AISG-01 | Phase 26, Phase 27 (frontend trigger) | Pending |
| AISG-02 | Phase 26 | Pending |
| AISG-03 | Phase 26 | Pending |
| AISG-04 | Phase 26 | Pending |
| AISG-05 | Phase 26 | Pending |
| AISG-06 | Phase 26 | Complete |
| AISG-07 | Phase 27 | Pending |
| MDIA-01 | Phase 28 | Pending |
| SMGT-01 | Phase 28 | Pending |
| SYNC-01 | Phase 28 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

**Note on AISG-01:** This requirement spans two phases. Phase 26 delivers the backend endpoint (API + service). Phase 27 delivers the frontend trigger (button + loading state). The requirement is fully satisfied only when Phase 27 completes.

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after roadmap creation*
