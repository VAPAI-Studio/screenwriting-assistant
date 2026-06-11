# Requirements: Screenwriting Assistant

**Defined:** 2026-03-24 (v4.2) · updated 2026-06-07 (Phase 54 — direct screenplay writing)
**Active Milestone:** v7.0 — Breakdown Fidelity (complete; v6.0 still open pending EVAL-01 UAT). Phase 54 is a standalone post-v7.0 enhancement.
**Core Value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## Phase 54 Requirements — Direct Screenplay Writing (standalone enhancement)

**Defined:** 2026-06-07 · User-requested: write a screenplay directly in the editor without first running the Script Writer Wizard. Internal tool.

### Direct Writing (WRITE)

- [x] **WRITE-01**: From an empty project, the user can write a screenplay directly in the Screenplay Editor (no Script Writer Wizard prerequisite) and save it
- [x] **WRITE-02**: A hand-written screenplay is split into scenes by scene headings (INT./EXT. sluglines); a document with no recognizable heading saves as a single "Untitled" scene (text never lost)
- [x] **WRITE-03**: Saving from an empty project creates the screenplay_editor data (no 404); save→reload→edit→save round-trips without scene duplication or loss
- [x] **WRITE-04**: A hand-written screenplay feeds the breakdown the same as a generated one — saving (re)creates ScreenplayContent rows (idempotently, no duplicate accumulation) and marks breakdown/shotlist stale

## v7.0 Requirements — Breakdown Fidelity

**Defined:** 2026-06-06 · Internal tool — focus is the FIDELITY of the production breakdown (the AI extraction of physical on-screen elements from the script). Symmetric with v6.0: v6.0 deepened the *script*, v7.0 deepens the *breakdown* extracted from it. No market/export/collab features.

**Premise:** v6.0 made generated scene text richer (continuity, voice, craft). The breakdown extraction in `backend/app/services/breakdown_service.py` should now read that actual per-scene screenplay text rather than one-line scene summaries, capture where/how each element appears, cover a broader element taxonomy, and refresh when a scene changes.

### Scene-Text Extraction (BFID)

- [x] **BFID-01**: Breakdown extraction runs against the full per-scene screenplay text (from `ScreenplayContent.content`), not one-line scene summaries — so elements present in action/dialogue are caught
- [x] **BFID-02**: Extraction is scene-scoped — each scene's elements are extracted from that scene's text, so an element can be attributed to the scene(s) it actually appears in
- [x] **BFID-03**: Existing "physically present on screen" extraction rules are preserved (no elements merely mentioned in dialogue/backstory, no abstract concepts) while operating on the fuller scene text

### Per-Appearance Context (APPR)

- [x] **APPR-01**: Each extracted element records the scene(s) it appears in (per-appearance context), not just a flat global element list
- [x] **APPR-02**: For each appearance, a short context note captures how/where the element appears (the action or moment), surfaced in the breakdown UI
- [x] **APPR-03**: The same element appearing across multiple scenes is consolidated into one element with multiple appearances (not duplicated)

### Expanded Categories (CATG)

- [x] **CATG-01**: The element taxonomy is broadened beyond the current set to cover additional production-relevant categories (e.g. wardrobe, makeup/hair, SFX/VFX, vehicles, animals, stunts) — exact final list settled during phase discussion
- [x] **CATG-02**: Existing breakdown categories and existing extracted data remain valid — new categories are additive, no data migration that drops prior elements
- [x] **CATG-03**: The breakdown UI displays and lets the user filter/group by the expanded categories

### Re-Extraction on Change (REEX)

- [x] **REEX-01**: When a scene's screenplay changes (regenerate-and-keep from v6.0, or a manual script edit), the breakdown is flagged stale via the existing staleness mechanism
- [x] **REEX-02**: Re-extraction refreshes the breakdown against the changed scene text without discarding user-added/edited breakdown elements (preserve manual edits where feasible — exact merge policy settled during phase discussion)

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

- [x] **CRAFT-01**: The screenplay-generation prompt includes explicit craft guidance — subtext in dialogue, action-line economy, show-don't-tell, and page pacing / white space
- [x] **CRAFT-02**: Action lines in generated output are visual and economical (present tense, no internal/unfilmable description) per the craft guidance
- [x] **CRAFT-03**: Dialogue carries subtext rather than stating intentions on-the-nose, per the craft guidance

### Format Fidelity (FMT)

- [x] **FMT-01**: Screenplay output is produced in a way that preserves industry-standard formatting (scene headings, action, character cues, parentheticals, dialogue) without JSON-wrapping degrading it
- [x] **FMT-02**: The screenplay-generation path is evaluated native-output vs. json_mode-wrapped, and the better-formatting approach is adopted

### Quality Evaluation (EVAL)

- [x] **EVAL-01**: User can regenerate a scene's screenplay with the new (improved) generation path and compare it side-by-side against the prior output, to judge the quality improvement (UAT confirmed by user 2026-06-11)

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
| CRAFT-01 | Phase 48 | Complete |
| CRAFT-02 | Phase 48 | Complete |
| CRAFT-03 | Phase 48 | Complete |
| EVAL-01 | Phase 49 | Complete |
| BFID-01 | Phase 50 | Complete |
| BFID-02 | Phase 50 | Complete |
| BFID-03 | Phase 50 | Complete |
| APPR-01 | Phase 51 | Complete |
| APPR-02 | Phase 51 | Complete |
| APPR-03 | Phase 51 | Complete |
| CATG-01 | Phase 52 | Complete |
| CATG-02 | Phase 52 | Complete |
| CATG-03 | Phase 52 | Complete |
| REEX-01 | Phase 53 | Complete |
| REEX-02 | Phase 53 | Complete |
| WRITE-01 | Phase 54 | Complete |
| WRITE-02 | Phase 54 | Complete |
| WRITE-03 | Phase 54 | Complete |
| WRITE-04 | Phase 54 | Complete |
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
- v7.0 requirements: 12 total (BFID/APPR/CATG/REEX) — Mapped to phases 50-53: 12/12 — Planned (execution gated on v6.0 close)
- v6.0 requirements: 12 total
- Mapped to phases: 12/12
- Unmapped: 0
- v4.2 requirements: 13 total — Mapped to phases: 13/13 (shipped)

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-06-05 after v6.0 roadmap creation*
