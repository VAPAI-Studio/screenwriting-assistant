# Requirements: Screenwriting Assistant

**Defined:** 2026-03-24 (v4.2) · updated 2026-06-05 (v6.0)
**Active Milestone:** v6.0 — Script Quality
**Core Value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## v6.0 Requirements — Script Quality

**Defined:** 2026-06-05 · Internal tool — focus is craft quality of generated scripts, no market/export/collab features.

### Continuity (CONT)

- [x] **CONT-01**: When generating a scene's screenplay, the AI receives the full text of the immediately preceding generated scene(s) as context, not just one-line summaries
- [x] **CONT-02**: A running synopsis / "story so far" is maintained across scene generations so later scenes stay consistent with established events without exceeding context limits
- [x] **CONT-03**: Setups and payoffs (objects, facts, character states introduced earlier) remain consistent across the generated scene sequence — a generated scene does not contradict an earlier generated scene

### Character Voice (VOICE)

- [x] **VOICE-01**: Per-character voice/diction profiles are injected into the script-writing prompt (not only scene planning), so each character's dialogue reflects their defined voice
- [x] **VOICE-02**: When a character has no defined voice, the system derives or maintains a consistent voice for them across scenes rather than defaulting to a uniform style
- [x] **VOICE-03**: Generated dialogue is distinguishable between characters — two characters in the same scene do not sound interchangeable

### Screenwriting Craft (CRAFT)

- [ ] **CRAFT-01**: The screenplay-generation prompt includes explicit craft guidance — subtext in dialogue, action-line economy, show-don't-tell, and page pacing / white space
- [ ] **CRAFT-02**: Action lines in generated output are visual and economical (present tense, no internal/unfilmable description) per the craft guidance
- [ ] **CRAFT-03**: Dialogue carries subtext rather than stating intentions on-the-nose, per the craft guidance

### Format Fidelity (FMT)

- [x] **FMT-01**: Screenplay output is produced in a way that preserves industry-standard formatting (scene headings, action, character cues, parentheticals, dialogue) without JSON-wrapping degrading it
- [x] **FMT-02**: The screenplay-generation path is evaluated native-output vs. json_mode-wrapped, and the better-formatting approach is adopted

### Quality Evaluation (EVAL)

- [ ] **EVAL-01**: User can regenerate a scene's screenplay with the new (improved) generation path and compare it side-by-side against the prior output, to judge the quality improvement

## v4.2 Requirements

### Show Management

- [x] **SHOW-01**: User can create a new show with a title and description
- [x] **SHOW-02**: Home page displays Shows and standalone Films as separate sections
- [x] **SHOW-03**: User can open a show to view its series bible and episode list
- [x] **SHOW-04**: User can edit a show's title and description, and delete a show

### Series Bible

- [x] **BIBL-01**: Each show has four bible sections: Characters, World/Setting, Season Arc, Tone & Style
- [x] **BIBL-02**: User can write and edit each bible section as freeform text
- [x] **BIBL-03**: Each show has a target episode duration setting (10 min, 22 min, 44 min, 60 min, or custom)
- [x] **BIBL-04**: Bible content (all four sections) and episode duration are automatically injected into AI context for episode script generation, agent reviews, and breakdown extraction

### Episodes

- [x] **EPIS-01**: User can create a new episode inside a show with an episode number and title
- [x] **EPIS-02**: Each episode has the full screenplay → breakdown → shotlist → storyboard pipeline identical to standalone projects
- [x] **EPIS-03**: User can view, open, and delete episodes from the show page
- [x] **EPIS-04**: Existing standalone projects are unaffected — no data migration required
- [x] **EPIS-05**: Episode views include breadcrumb navigation back to the parent show (Show > Episode N: Title)

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
| CONT-01 | Phase 45 | Complete |
| CONT-02 | Phase 45 | Complete |
| CONT-03 | Phase 45 | Complete |
| FMT-01 | Phase 46 | Complete |
| FMT-02 | Phase 46 | Complete |
| VOICE-01 | Phase 47 | Complete |
| VOICE-02 | Phase 47 | Complete |
| VOICE-03 | Phase 47 | Complete |
| CRAFT-01 | Phase 48 | Pending |
| CRAFT-02 | Phase 48 | Pending |
| CRAFT-03 | Phase 48 | Pending |
| EVAL-01 | Phase 49 | Pending |
| SHOW-01 | Phase 36 | Complete |
| SHOW-02 | Phase 38 | Complete |
| SHOW-03 | Phase 38 | Complete |
| SHOW-04 | Phase 36 | Complete |
| BIBL-01 | Phase 37 | Complete |
| BIBL-02 | Phase 37 | Complete |
| BIBL-03 | Phase 37 | Complete |
| BIBL-04 | Phase 41 | Complete |
| EPIS-01 | Phase 39 | Complete |
| EPIS-02 | Phase 39 | Complete |
| EPIS-03 | Phase 40 | Complete |
| EPIS-04 | Phase 39 | Complete |
| EPIS-05 | Phase 42 | Complete |

**Coverage:**
- v6.0 requirements: 12 total
- Mapped to phases: 12/12
- Unmapped: 0
- v4.2 requirements: 13 total — Mapped to phases: 13/13 (shipped)

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-06-05 after v6.0 roadmap creation*
