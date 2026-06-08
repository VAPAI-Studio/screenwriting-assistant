# Phase 54: Direct Screenplay Writing - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user requested the feature directly; decisions by Claude, one design question answered by the user — multi-scene by headings).

<domain>
## Phase Boundary

A user can write a screenplay directly in the Screenplay Editor starting from an empty project — without first running the Script Writer Wizard. Today the editor hard-blocks on empty content ("No screenplay content yet. Generate screenplays using the Script Writer Wizard first.") and never reaches its edit/save path. This phase makes the empty editor writable and persists hand-written screenplays, split into scenes by scene headings.

**User decision (captured):** when writing from scratch, the saved text is split into MULTIPLE scenes by screenplay scene headings (INT./EXT. ...) — fidelity to a real screenplay, not one blob.

**In scope:**
- Frontend: replace the empty-state dead-end in `ScreenplayEditorView` with a writable empty editor (an "Start writing" affordance → the existing edit textarea), and a save path that works when there were zero original screenplays.
- A heading-based splitter: parse the written document into scenes at scene-heading lines (INT./EXT./INT-EXT etc.), each becoming a `{title, content, episode_index}` screenplay item.
- Backend: make the `screenplay_editor` save path work when the PhaseData does not yet exist (the PATCH endpoint currently 404s if absent).

**Out of scope:**
- AI generation changes (wizard untouched).
- Rich screenplay formatting toolbar / fountain parser / pagination changes beyond what exists.
- Changing the per-screenplay contract `{title, content, episode_index}` or the `{screenplays, synopsis}` shape.
- Re-flowing breakdown/shotlist beyond the existing staleness hooks.
</domain>

<decisions>
## Implementation Decisions

### D-54-01 — Make the PATCH subsection endpoint upsert (create-if-absent) for screenplay_editor (DECIDED)
**Grey area / blocker (verified):** `PATCH /phase-data/{project_id}/{phase}/{subsection_key}` raises 404 "Phase data not found" when the PhaseData row doesn't exist (phase_data.py:208-209). Writing from an empty project means the `screenplay_editor` PhaseData does NOT exist yet → save would 404 and lose the text.
**Decision:** Change the PATCH handler to FETCH-OR-CREATE the PhaseData (copy the proven pattern from `wizards.py:255-269`: if `not data`, create `PhaseData(project_id, phase, subsection_key, content={})`, `db.add`, `db.flush`, then merge as today). This makes the endpoint a true upsert for any subsection, not just screenplay_editor — which is correct and low-risk (the merge logic is unchanged; only the not-found branch changes from 404 to create). Preserve `flag_modified`, the breakdown/shotlist staleness marking, ownership check, and the merge semantics. Owner-scoped (the existing `_verify_project_ownership` stays).
**Alternative considered & rejected:** a separate POST/create endpoint — more surface, and the frontend would need to know whether to POST vs PATCH. Upsert-on-PATCH is simpler and matches the wizard's own fetch-or-create behavior.

### D-54-02 — Writable empty state in ScreenplayEditorView (DECIDED)
**Decision:** Replace the `if (screenplays.length === 0)` dead-end (ScreenplayEditorView.tsx:185-204) so the empty state offers a "Start writing" / "Write screenplay" button that enters edit mode (`setIsEditing(true)`) with an empty `editText` and a helpful placeholder (e.g. "INT. LOCATION - DAY\n\nAction…"). The existing edit textarea, save/discard toolbar, and `saveMutation` are reused. When `screenplays.length === 0` AND not editing, show the writable empty state (not the wizard-only block). The wizard remains an alternative path (the message can mention "or generate with the Script Writer Wizard") but is no longer a prerequisite.

### D-54-03 — Heading-based scene splitter for the from-scratch case (DECIDED: multi-scene by INT./EXT.)
**Grey area:** `splitToScreenplays(text, originals)` returns `[]` when `originals.length === 0` (ScreenplayEditorView.tsx:39) — so even if you could type, saving from empty would persist nothing.
**Decision:** Add a heading-based split used when there are no originals (or extend `splitToScreenplays` to handle the zero-originals case). Parse the document into scenes at scene-heading lines — a line matching a screenplay slugline pattern (case-insensitive, allowing leading spaces): starts with `INT.`/`EXT.`/`INT./EXT.`/`I/E`/`INT `/`EXT ` etc. Each heading starts a new scene; the heading line becomes (or seeds) that scene's `title`, and the text until the next heading is its `content`; assign `episode_index` sequentially (0,1,2…).
  - If the document has NO recognizable heading, fall back to a SINGLE scene: `{title: "Untitled", content: <whole text>, episode_index: 0}` — never lose the user's text, never save an empty `screenplays: []`.
  - Title derivation: use the heading line as the `title` (e.g. "INT. CASTLE - NIGHT"); `content` is the body AFTER the slugline — **do NOT keep the slugline in content** (CORRECTED post-plan-review: `buildDocument` re-prepends `title.toUpperCase()` as the header, so keeping the slugline in content too would render it TWICE. This mirrors generated scenes, where title and content are distinct and buildDocument renders the header once). The slugline MUST remain visible in the rendered screenplay (it is — via the title header) and round-trip safely (title=slugline → the existing title-anchor split is stable on re-save).
**Round-trip:** after the first save, the project HAS originals, so subsequent edits use the EXISTING `splitToScreenplays(text, originals)` title-anchor path. The heading-split is only the from-scratch (zero-originals) entry. Ensure the two paths are consistent enough that a save→reload→edit→save cycle is stable (no scene duplication/loss). This round-trip stability is the key correctness concern for the planner/verifier.

### D-54-04 — Preserve the contract and the pipeline (DECIDED: additive)
**Decision:** Hand-written scenes produce the same `{title, content, episode_index}` items and the same `{screenplays, synopsis}` content shape (synopsis stays "" / untouched when writing manually — no AI synopsis for hand-written scripts). Saving marks breakdown/shotlist stale via the existing hooks. The per-screenplay contract and the ScriptReadView consumer must keep working.

### D-54-05 — Hand-written scenes feed breakdown via ScreenplayContent (DECIDED: include now — user confirmed)
**User decision (confirmed):** a hand-written screenplay must feed the breakdown extraction the same way an AI-generated one does. Breakdown extraction reads `ScreenplayContent` rows (breakdown_service.py:131-145), which the generic PATCH path does NOT create — so without this, a hand-written script would show in the editor but extract nothing.
**Decision:** On saving the `screenplay_editor` content, (re)create `ScreenplayContent` rows from the saved `screenplays` (mirror the wizard apply pattern at wizards.py:274-281: one row per screenplay with `content=sp["content"]`, `formatted_content=sp` — and set `formatted_content.episode_index` so v7.0 scene-scoped alignment works), then mark breakdown + shotlist stale.
**WHERE this lives (important design point):** the generic `PATCH /phase-data/{phase}/{subsection_key}` handler must stay generic — it must NOT special-case ScreenplayContent for arbitrary subsections. So EITHER:
  (a) add a dedicated screenplay-save endpoint/path (e.g. `PATCH /phase-data/{project}/write/screenplay_editor` handled specially, or a new `POST /screenplay/{project}/save`) that does the upsert + ScreenplayContent sync + staleness; the frontend `saveMutation` calls it instead of the generic PATCH; OR
  (b) inside the generic PATCH handler, guard `if phase == "write" and subsection_key == "screenplay_editor": <sync ScreenplayContent from content["screenplays"]>` after the merge.
  Planner's Discretion which; (a) is cleaner separation, (b) is fewer moving parts. Either way: do NOT duplicate ScreenplayContent rows on every save — REPLACE/reconcile (delete the project's existing rows then recreate, OR upsert by episode_index) so repeated saves don't accumulate duplicates (this repo already has a documented duplicate-ScreenplayContent-row problem — see [[screenplaycontent-no-reliable-order]] / v6.0 WR-01; do NOT make it worse). The wizard apply currently APPENDS (a known issue); the manual-save path should REPLACE to stay clean. Reconcile policy is Claude's Discretion but MUST be idempotent across repeated saves.
**Interaction with v6.0/v7.0:** setting `formatted_content.episode_index` on the created rows means hand-written scenes get scene-scoped breakdown extraction (v7.0 Phase 50) and per-appearance context (v7.0 Phase 51) for free. Round-trip + re-save must keep episode_index aligned to scene order.
</decisions>

<code_context>
## Existing Code Insights (verified)
- `ScreenplayEditorView.tsx`: empty-state dead-end at :185-204; `splitToScreenplays` :37-74 returns `[]` for zero originals; `saveMutation` :156-168 → `api.updateSubsectionData` (PATCH); `startEditing`/`handleSave`/`handleDiscard` :170-182; edit textarea + toolbar already render for the non-empty path :255+.
- `api.updateSubsectionData` (api.tsx:531-535) → `PATCH /phase-data/{projectId}/{phase}/{subsectionKey}` with `{screenplays: [...]}`.
- `PATCH /phase-data/...` (phase_data.py:190-225): 404s if PhaseData absent (:208-209) — THE BLOCKER; merges `update.content` into existing JSONB otherwise; marks breakdown/shotlist stale; owner-checked.
- Fetch-or-create pattern to copy: `wizards.py:255-269`.
- ScriptReadView.tsx also reads `content.screenplays` (:84-85) and has its own empty state (:184-188) — should also benefit once content exists; no change needed there for the write feature but verify it renders hand-written scenes.

## OPEN QUESTION (planner to resolve, sensible default chosen)
- **ScreenplayContent rows for breakdown:** the wizard apply path creates `ScreenplayContent` rows (which breakdown extraction reads). The manual PATCH save path writes only `PhaseData.content.screenplays`. So a purely hand-written screenplay would appear in the editor/ScriptReadView but breakdown extraction (which queries ScreenplayContent) might find nothing. DEFAULT for this phase: keep scope to "write + persist + display in the editor" (the user's stated need). Making hand-written scenes flow into breakdown (creating ScreenplayContent rows on manual save) is a natural follow-up — flag it; only build it if cheap and low-risk. The planner should decide whether to include ScreenplayContent creation on manual save or defer it (and document the choice). The user's literal request is "escribir directo un guion" (write a screenplay directly) — the editor write+persist is the must-have.

## Pre-existing test-isolation concern: v6.0-PREEXISTING-TEST-CONCERN.md (not relevant here).
</code_context>

<specifics>
## Specific Ideas
- Backend: PATCH upsert (fetch-or-create) — small, copies wizards.py pattern. Add a backend test: PATCH to a non-existent screenplay_editor subsection creates it and stores screenplays.
- Frontend: writable empty state + heading-based splitter for zero-originals. Frontend gate is `npm run build` (tsc); no FE unit harness.
- Splitter tests would be ideal but there's no FE test runner — at minimum, exercise the split logic carefully by hand and keep it pure/simple; consider a tiny pure helper that COULD be unit-tested later. Verify round-trip (write 2 scenes → save → reload shape → edit → save) doesn't duplicate/lose scenes via the backend test + manual reasoning.
- Keep backend breakdown/staleness/phase-data tests green: test_breakdown_*, test_staleness.py, test_api.py (phase-data tests).
- No migration. No contract change.

## Verification framing
- Must-have: from an empty project, the editor lets you write and SAVE; reload shows the saved screenplay; it splits into scenes by INT./EXT. headings (or one "Untitled" scene if none).
- The backend upsert no longer 404s for a never-saved subsection.
- Round-trip stability (no scene dup/loss across save→reload→edit→save).
- Existing wizard-generated flow unaffected.
</specifics>

<deferred>
## Deferred Ideas
- Creating ScreenplayContent rows on manual save so hand-written scripts feed breakdown extraction (flag in open question — decide in plan).
- Rich formatting toolbar / fountain autocompletion / auto-slugline-uppercasing.
- A dedicated "new screenplay" template or scene-insert buttons.
</deferred>
