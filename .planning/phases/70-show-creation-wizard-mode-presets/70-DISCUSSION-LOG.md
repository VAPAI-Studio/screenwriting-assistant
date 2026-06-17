# Phase 70: Show Creation Wizard (mode + presets) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 70-show-creation-wizard-mode-presets
**Areas discussed:** Flow structure, Label language, Preset→mode mapping, Adaptation scope, Preset durations (with mid-discussion correction)

---

## Flow structure

| Option | Description | Selected |
|--------|-------------|----------|
| Single modal + preset section | Extend CreateShowModal with a preset-card row; reveal season-arc inline for connected | ✓ |
| True multi-step wizard | Convert to WizardView multi-step flow | |
| Let planner decide | Capture both as acceptable | |

**User's choice:** Single modal + preset section
**Notes:** Lowest churn; reuses the existing basic modal and the CreateProjectModal card pattern.

---

## Label language

| Option | Description | Selected |
|--------|-------------|----------|
| Spanish labels | Microserie / Serie conectada / Antología + English helper line | ✓ |
| English labels | Translate to Mini-series / Connected series / Anthology | |
| Bilingual | Spanish title + English subtitle | |

**User's choice:** Spanish labels
**Notes:** Product owner works in Spanish; domain terms stay native, English helper keeps it legible.

---

## Preset → mode mapping

| Option | Description | Selected |
|--------|-------------|----------|
| 3 presets → connected/connected/anthology | Both series presets = connected (differ by duration); Antología = anthology; standalone not offered | ✓ |
| Each preset a distinct mode | 1:1 onto connected/anthology/standalone | |
| Let planner resolve from vision doc | Defer to planning | |

**User's choice:** 3 presets → connected/connected/anthology; `standalone` excluded from the wizard
**Notes:** Matches D4/D5 and Phase 67's anthology default. standalone stays the show_id-NULL feature-film path.

---

## Adaptation scope

| Option | Description | Selected |
|--------|-------------|----------|
| Create + mode change on edit only | Creation flow adapts; edit can change mode (SC-3); BibleEditor not made fully mode-aware | ✓ |
| Also make BibleEditor mode-aware | Hide/show bible sections by mode on edit too | |
| Create flow only | Strictly creation; minimal edit handling | |

**User's choice:** Create + mode change on edit only
**Notes:** Keeps scope to the wizard; full BibleEditor section-hiding deferred.

---

## Preset durations (corrected mid-discussion)

**Initial answer:** "No duration defaults" — which collapsed Microserie and Serie conectada into a functionally identical pair, prompting a follow-up that tentatively dropped Microserie (two-preset set: Serie conectada + Antología).

**User correction:** "perdon, si duration default, serie es 22, microserie es 2" — there ARE duration defaults, restoring all three presets.

**Final confirmed mapping:**

| Preset | continuity_mode | default episode_duration_minutes | Selected |
|--------|-----------------|----------------------------------|----------|
| Microserie | connected | 2 | ✓ |
| Serie conectada | connected | 22 | ✓ |
| Antología | anthology | none | ✓ |

**Notes:** Durations remain editable metadata (D4); presets only seed the initial value. The 2 vs 22 min difference is what distinguishes the two connected presets. Note: 2 min is not currently in DURATION_PRESETS — planner to decide add-as-preset vs custom value.

---

## Claude's Discretion

- Exact card layout and English helper-line copy.
- Precise placement of the revealed season-arc field within the modal.
- The edit-side mode-change control's exact form (preset cards vs simpler selector).

## Deferred Ideas

- Full BibleEditor mode-awareness (all bible sections, not just season-arc).
- A standalone show path in the wizard (standalone stays the show_id-NULL project case).
- Adding `2` to the shared DURATION_PRESETS as a globally-offered chip.
