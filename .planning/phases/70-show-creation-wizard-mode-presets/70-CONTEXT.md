# Phase 70: Show Creation Wizard (mode + presets) - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

At show **creation** (and edit), the user picks how episodes relate via friendly **presets**, and the creation flow **adapts** to that choice — making continuity mode a first-class, understandable setup step.

This is a **frontend-only** phase. All backend scaffolding already landed in Phase 67:
- `shows.continuity_mode` (VARCHAR, default `anthology`) exists on the model.
- `ShowCreate` / `ShowUpdate` / `ShowResponse` already carry `continuity_mode` (Pydantic `ContinuityMode` enum: `connected` | `anthology` | `standalone`).
- `POST /api/shows` and `PUT /api/shows/{id}` already read and persist `continuity_mode`.

Phase 70 adds the **UI** that lets a user actually set/change the mode via presets, and adapts the create flow to the chosen mode. It does NOT touch the backend contract, generation behavior (Phase 68), summaries (Phase 69), or review (Phase 71).

**Presets are pure UI sugar (locked D5):** the model stores ONLY `continuity_mode` (+ the standard `episode_duration_minutes` metadata). No preset label is ever persisted as a separate field.
</domain>

<decisions>
## Implementation Decisions

### Preset set & mapping (the core decision)
- **D-01:** **Three presets**, each with a distinct effect:
  | Preset (Spanish label) | Sets `continuity_mode` | Seeds default `episode_duration_minutes` |
  |---|---|---|
  | **Microserie** | `connected` | **2** |
  | **Serie conectada** | `connected` | **22** |
  | **Antología** | `anthology` | *(none — leaves duration unset/default)* |
- **D-02:** `standalone` is **NOT offered** in the show creation wizard. `standalone` is the `show_id IS NULL` feature-film case (a project created without a show), not a show-level choice. The wizard only exposes the two show-meaningful modes (`connected` via the two series presets, `anthology`).
- **D-03:** The seeded duration is a **default the user can still change** — durations stay editable metadata (locked D4). The preset only sets the initial value of the existing `episode_duration_minutes` field; it is not coupled to the mode beyond seeding.
- **D-04:** Microserie and Serie conectada both resolve to `continuity_mode=connected` and are disambiguated **only** by the seeded duration (2 vs 22 min). That duration difference is what makes them distinct presets — without it they would collapse into one.

### Label language
- **D-05:** **Spanish preset labels** exactly as the vision specifies — *Microserie / Serie conectada / Antología* — with a short **English helper line** under each card explaining what the mode does. Rationale: the product owner works in Spanish; the domain terms stay native, while the helper keeps the otherwise-English UI legible.

### Flow structure & mode adaptation
- **D-06:** Keep show creation as a **single modal** (`CreateShowModal`), NOT a multi-step `WizardView`. Add a **preset-card section** to the existing modal, reusing the clickable-card selection pattern from `CreateProjectModal` (selected-state border/glow + indicator).
- **D-07:** "Flow adapts to the mode" = the **season-arc field is revealed inline** within the create modal when a **connected** preset (Microserie / Serie conectada) is selected, and hidden for **Antología**. This satisfies SC-2 ("connected surfaces the season-arc step; anthology hides cross-episode steps") without a multi-step flow.

### Adaptation scope (what's in vs. deferred)
- **D-08:** Phase 70 covers (a) the **creation flow's** mode adaptation and (b) **changing the mode on edit** (SC-3 requires a later edit can change the mode — reuse the Phase 67 `PUT /api/shows/{id}` contract). It does **NOT** retrofit the full `BibleEditor` to be section-visibility mode-aware; that broader edit-surface adaptation is deferred (see Deferred Ideas).

### Claude's Discretion
- Exact card layout/copy of the English helper lines, the precise place the season-arc field is revealed within the modal, and the edit-side mode-change control (e.g., a mode selector reusing the same preset cards vs. a simpler control) are left to the planner/UI-spec, as long as D-01..D-08 hold.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked product decisions (vision)
- `.planning/v10.0-SHOW-TYPE-VISION.md` §D1–D5 — D1 (single extensible `continuity_mode` axis), D4 (scale/duration stays metadata, NOT part of the type), **D5 (presets are pure UI sugar over the single mode)**. These are the source of truth for the preset→mode relationship.

### Upstream phase decisions (Phase 67 — what the wizard writes into)
- `.planning/phases/67-continuity-data-model-migration/67-CONTEXT.md` — D-01 (anthology is the default/backfill mode), D-03 (VARCHAR storage, app-validated enum), D-04 (`continuity_mode` editable on create/edit, returned in `ShowResponse`).

### Requirements
- `.planning/REQUIREMENTS.md` — SWZ-01 (pick mode at creation via presets), SWZ-02 (creation flow adapts to mode).
- `.planning/ROADMAP.md` §"Phase 70" — goal, constraints, 3 success criteria, UI hint=yes.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`frontend/src/components/Shows/CreateShowModal.tsx`** (~lines 1–104): the show-creation modal to extend. Today collects only `title` (required) + `description`; calls `api.createShow()`. This is where the preset-card section and the conditional season-arc field go.
- **`frontend/src/components/Projects/CreateProjectModal.tsx`** (~lines 138–163): the **clickable-card selection pattern** to reuse for preset cards — selected-state styling (`border-amber-500/40 bg-amber-500/5 glow-amber`), amber dot indicator, icon + title + description layout.
- **`frontend/src/components/Shows/EpisodeDurationPicker.tsx`** + `DURATION_PRESETS` (constants.ts ~lines 364–370, values 10/22/44/60): the existing duration control the preset seeds. NOTE: the preset defaults are **2** and **22**; **2 is not currently in `DURATION_PRESETS`** — the planner must confirm whether to add 2 as a preset value or set it as a custom value.
- **`frontend/src/components/Shows/BibleEditor.tsx`** (~lines 1–114): edits bible sections incl. `bible_season_arc` (constants.ts ~line 360 "Season Arc"); also where the edit-side mode-change control lives. Currently NOT mode-aware (full mode-awareness deferred per D-08).
- **`frontend/src/components/Patterns/WizardView.tsx`**: multi-step wizard pattern — **intentionally NOT used** per D-06, but noted in case the planner reconsiders.

### Established Patterns
- Radix `Dialog` modals (`@radix-ui/react-dialog`) — both CreateShowModal and CreateProjectModal use the same Dialog.Root/Portal pattern.
- CVA-based `Button` (`frontend/src/components/UI/Button.tsx`). No standalone Card component — cards are inline-styled divs (see CreateProjectModal).
- React Query for mutations (per CLAUDE.md: React Query, 5-min stale time, not Redux/Context).
- UI is **English** (en-US); no i18n library. Spanish preset labels are a deliberate per-D-05 exception (hardcoded), not a new i18n system.

### Integration Points
- **`frontend/src/types/index.ts`** (`Show` interface, ~lines 452–460): **missing `continuity_mode`** — must add `continuity_mode: ContinuityMode` (and a matching TS union) to the frontend type so the create/edit payloads are typed.
- **`frontend/src/lib/api.tsx`** `createShow` / `updateShow` (`ShowCreate`/`ShowUpdate` payloads): already accept `continuity_mode` on the backend; the frontend payloads just need to send it.
- Backend (read-only this phase): `backend/app/models/schemas.py` `ContinuityMode` enum (~lines 916–926) + `ShowCreate`/`ShowUpdate` (~928–943); `backend/app/api/endpoints/shows.py` POST (~15–31) / PUT (~65–89).
</code_context>

<specifics>
## Specific Ideas

- Preset labels are Spanish **verbatim**: `Microserie`, `Serie conectada`, `Antología`.
- Microserie default duration = **2 min**; Serie conectada = **22 min**; Antología = no duration default.
- Both connected presets reveal the **season-arc** field inline; Antología hides it.
</specifics>

<deferred>
## Deferred Ideas

- **Full `BibleEditor` mode-awareness** — conditionally hiding/showing all bible sections (beyond season-arc) based on `continuity_mode` in the edit surface. Out of scope for Phase 70 (D-08); candidate for a later UI-polish phase.
- **A `standalone` show path / feature-film mode in the wizard** — `standalone` remains the `show_id IS NULL` project path, not a show preset (D-02). If a future product decision wants standalone shows, that's a new scope.
- **Adding `2` to the shared `DURATION_PRESETS`** as a globally-offered duration — only if the planner decides the seeded 2-min value should also appear as a reusable preset chip (otherwise it's set as a custom value).
</deferred>

---

*Phase: 70-show-creation-wizard-mode-presets*
*Context gathered: 2026-06-17*
