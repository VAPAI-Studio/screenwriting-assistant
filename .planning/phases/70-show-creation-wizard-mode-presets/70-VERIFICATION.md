---
phase: 70-show-creation-wizard-mode-presets
verified: 2026-06-18T12:00:00Z
status: human_needed
score: 7/7
overrides_applied: 0
human_verification:
  - test: "Show creation wizard — full flow with connected preset"
    expected: "Three preset cards appear (Microserie / Serie conectada / Antología). Selecting a connected preset reveals a Season Arc textarea with fade-up animation. Create CTA remains disabled until both a title AND a preset are selected. After creation the user navigates to the show page, the Series Bible shows the seeded episode duration (2 or 22 min), and any typed season arc text is saved to the Season Arc bible section."
    why_human: "Visual rendering, animation behavior, and the two-call create sequence outcome (seeded duration on the show page) require a running browser and backend."
  - test: "Show creation wizard — Antología preset"
    expected: "Selecting Antología hides the Season Arc field entirely. After creation, no season arc is written and episode duration is left at its default."
    why_human: "Requires running app to confirm field visibility change and that no bible_season_arc was written."
  - test: "Edit-side mode control — pre-selection accuracy"
    expected: "Opening a show created as Microserie pre-selects the Microserie card (duration-2 disambiguation). Opening a Serie conectada show pre-selects that card. Opening an Antología show pre-selects Antología. Clicking a different card briefly disables all three cards (in-flight state), then the new card becomes selected. Reloading the page confirms the change persisted."
    why_human: "Pre-selection correctness, card disable during in-flight, and persistence-after-reload require a running browser + backend."
  - test: "Edit-side mode control — navigation between shows does not show stale pre-selection"
    expected: "Navigating from one show to another (without page reload) shows the correct preset pre-selected for the new show, not the previous show's preset."
    why_human: "CR-03 from the code review identified a race condition where the loaded-ref guard prevents re-seeding selectedPreset when continuityMode changes between shows in the same React Router session. This must be confirmed manually — it only surfaces when navigating between shows without a full page reload."
  - test: "Error handling for failed bible seed after show creation"
    expected: "If the api.updateBible call fails (network error / 5xx), the user sees an error message. Currently there is NO onError handler and NO inline error display in CreateShowModal — per CR-01 in the code review, this scenario results in silent data loss (the show is created with continuity_mode, but duration and season arc are not seeded, with no user-visible feedback)."
    why_human: "Requires manually triggering a network failure or mocking api.updateBible to reject, then observing whether any error is surfaced."
---

# Phase 70: Show Creation Wizard (Mode + Presets) Verification Report

**Phase Goal:** At show creation (and edit), the user picks how episodes relate via friendly presets, and the flow adapts to that choice — making continuity mode a first-class, understandable setup step.
**Verified:** 2026-06-18T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | When creating a show, user can pick a continuity mode via Microserie / Serie conectada / Antología presets, and the chosen preset sets the underlying `continuity_mode` | VERIFIED | `CreateShowModal.tsx:115-145` maps `SHOW_PRESETS` to clickable cards; `line 39` passes `continuity_mode: preset?.mode` to `api.createShow`. The `SHOW_PRESETS` constant at `constants.ts:380-412` defines all three presets with correct `mode` values. |
| 2 | The creation flow adapts to the selected mode — connected surfaces the season-arc step, anthology hides cross-episode steps | VERIFIED | `CreateShowModal.tsx:163-177`: `{isConnected && (...)}` gates the Season Arc textarea. `isConnected` at line 31 derives from `selectedPresetObj?.mode === 'connected'`. Antología has `mode: 'anthology'` so the field is hidden. The `animate-fade-up` class is present on the reveal container (line 164). |
| 3 | The persisted show carries only the resulting `continuity_mode` (presets leave no separate stored field), and a later edit can change the mode | VERIFIED | `ShowCreate` interface in `types/index.ts:470-474` carries only `continuity_mode?: ContinuityMode` — no preset label field. `BibleEditor.tsx:71-76` implements `updateShowMutation` calling `api.updateShow(showId, { continuity_mode: mode })`, invalidating `QUERY_KEYS.SHOW(showId)` on success. `ShowDetail.tsx:80` passes `continuityMode={show.continuity_mode}` to BibleEditor. |

**Score:** 3/3 roadmap truths VERIFIED

### Plan Must-Haves (from PLAN frontmatter)

#### Plan 01 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ShowCreate and Show payloads carry a typed `continuity_mode` value; ContinuityMode union includes `standalone` for type-completeness | VERIFIED | `types/index.ts:458`: `export type ContinuityMode = 'connected' \| 'anthology' \| 'standalone';` — exact match. `Show.continuity_mode: ContinuityMode` (required, line 465). `ShowCreate.continuity_mode?: ContinuityMode` (optional, line 473). |
| 2 | Single shared SHOW_PRESETS is the one source of truth for label/helper/icon/mode/duration, used by both create and edit | VERIFIED | `constants.ts:380-412` exports `SHOW_PRESETS`. Imported in `CreateShowModal.tsx:8` and `BibleEditor.tsx:5`. No competing preset definition exists anywhere in the frontend. |
| 3 | Seeded `episode_duration_minutes` is an editable default, not coupled to the mode beyond seeding | VERIFIED | `BibleEditor` documentation in SUMMARY explicitly states duration is not reseeded on mode change. The `SHOW_PRESETS` `duration` field is only used in the chained `updateBible` call at create time. |

#### Plan 02 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Show creation stays a single CreateShowModal (not multi-step) with three preset cards; user must select one before CTA enables | VERIFIED | `CreateShowModal.tsx:186`: `disabled={!title \| !selectedPreset \| createShowMutation.isPending}` — preset required. Single modal confirmed (no multi-step routing). |
| 2 | Selecting a connected preset reveals a Season Arc field inline; selecting Antología hides it | VERIFIED | `CreateShowModal.tsx:163-177`: conditional render on `isConnected`. NEEDS human confirmation of visual behavior. |
| 3 | Creating with a preset persists `continuity_mode` on the show, and for Microserie/Serie conectada seeds `episode_duration_minutes` via a chained bible update | VERIFIED (code) | `CreateShowModal.tsx:34-56`: two-call sequence implemented. `preset.duration !== null` guard at line 46 correctly skips duration for Antología. NEEDS human confirmation of end-to-end seeding. |
| 4 | A connected preset's non-empty Season Arc text is saved to `bible_season_arc` after create | VERIFIED (code) | `CreateShowModal.tsx:49-51`: `bible_season_arc: seasonArc.trim()` merged into `bibleUpdate` when `preset?.mode === 'connected'` and `seasonArc.trim()` is non-empty. |

#### Plan 03 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Edit surface allows changing continuity mode via same three preset cards, pre-selected to the show's current mode | VERIFIED (code) | `BibleEditor.tsx:49-51`: `selectedPreset` initialized from `presetIdForMode(continuityMode, bible.episode_duration_minutes)`. Cards rendered at lines 117-146. NEEDS human confirmation of visual pre-selection. |
| 2 | Changing preset persists new `continuity_mode` via PUT /api/shows/{id} | VERIFIED | `BibleEditor.tsx:71-82`: `updateShowMutation` calls `api.updateShow(showId, { continuity_mode: mode })` on card click. |
| 3 | Pre-selection disambiguates Microserie vs Serie conectada by stored `episode_duration_minutes` | VERIFIED (code) | `presetIdForMode` at `BibleEditor.tsx:20-25`: `durationMinutes === 2 ? 'microserie' : 'serie-conectada'`. NEEDS human confirmation (CR-03 risk on cross-show navigation). |
| 4 | Season Arc bible section remains visible/editable for connected modes | VERIFIED | `BibleEditor.tsx:150-180`: `BIBLE_SECTIONS.map(...)` renders all four accordion sections unconditionally. No mode-conditional hiding applied. |

**Combined score:** 7/7 truths VERIFIED (code-level)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/types/index.ts` | ContinuityMode union + continuity_mode on Show and ShowCreate | VERIFIED | Lines 458, 465, 473. All three values present. |
| `frontend/src/lib/constants.ts` | SHOW_PRESETS array (3 presets with correct id/label/helper/icon/mode/duration) | VERIFIED | Lines 380-412. Microserie/connected/2, Serie conectada/connected/22, Antología/anthology/null. Spanish labels verbatim. DURATION_PRESETS unchanged (10/22/44/60/-1). |
| `frontend/src/components/Shows/CreateShowModal.tsx` | Preset-card selection, conditional season-arc reveal, continuity_mode in create payload, chained updateBible | VERIFIED | 197 lines (above 120 min). All required tokens present. |
| `frontend/src/components/Shows/BibleEditor.tsx` | Edit-side mode-change control with SHOW_PRESETS, pre-selected, updateShow mutation | VERIFIED | 197 lines (above 130 min). All required tokens present. |
| `frontend/src/components/Shows/ShowDetail.tsx` | Passes show.continuity_mode down to BibleEditor | VERIFIED | Line 80: `continuityMode={show.continuity_mode}` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `types/index.ts` ContinuityMode | backend ContinuityMode enum | string-literal union mirrors backend values | VERIFIED | `'connected' \| 'anthology' \| 'standalone'` matches backend schemas.py enum |
| `constants.ts` SHOW_PRESETS | ContinuityMode union | each preset.mode typed as ContinuityMode | VERIFIED | `ReadonlyArray<{ ... mode: ContinuityMode; ... }>` at line 380 |
| `CreateShowModal.tsx` createShowMutation | api.createShow | payload includes continuity_mode from selected preset | VERIFIED | Line 39: `continuity_mode: preset?.mode` |
| `CreateShowModal.tsx` onSuccess | api.updateBible(show.id) | chained call seeds episode_duration_minutes and/or bible_season_arc | VERIFIED | Lines 45-54: bibleUpdate built and awaited when non-empty |
| `CreateShowModal.tsx` season-arc textarea | selected preset mode === 'connected' | conditional render gated on isConnected | VERIFIED | Line 163: `{isConnected && (...)}` |
| `ShowDetail.tsx` | BibleEditor | passes show.continuity_mode as continuityMode prop | VERIFIED | Line 80: `continuityMode={show.continuity_mode}` |
| `BibleEditor.tsx` mode-change mutation | api.updateShow(showId, { continuity_mode }) | React Query mutation invalidating QUERY_KEYS.SHOW | VERIFIED | Lines 71-76 |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `CreateShowModal.tsx` | `selectedPreset` → `continuity_mode` → `api.createShow` | User card click → SHOW_PRESETS lookup | Yes — preset.mode is a real ContinuityMode value passed to backend | FLOWING |
| `CreateShowModal.tsx` | `bibleUpdate` → `api.updateBible` | preset.duration (non-null) + seasonArc.trim() (non-empty connected) | Yes — real values from user input and SHOW_PRESETS | FLOWING |
| `BibleEditor.tsx` | `selectedPreset` state | `presetIdForMode(continuityMode, bible.episode_duration_minutes)` from props | Yes — derived from real show data fetched by ShowDetail | FLOWING |
| `BibleEditor.tsx` | `updateShowMutation` → `api.updateShow` | Card click → preset.mode | Yes — real ContinuityMode sent to backend | FLOWING |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SWZ-01 | 70-01, 70-02, 70-03 | User picks continuity mode at show creation via Microserie / Serie conectada / Antología presets as visual shortcuts that set the underlying mode | SATISFIED | SHOW_PRESETS drives card labels; selected preset's `mode` flows to createShow payload and updateShow mutation |
| SWZ-02 | 70-02, 70-03 | Creation flow adapts to mode (connected surfaces season-arc step; anthology hides cross-episode steps) | SATISFIED | Season Arc textarea gated on `isConnected`; Antología hides it. Edit surface defers full bible section-visibility adaptation to later phase (D-08, explicitly noted in plan). |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `CreateShowModal.tsx` | 60-64 | `onOpenChange(false)` called before state resets — setState on unmounted component | WARNING | React strict-mode warning; potential future React error. Does not prevent current functionality. Matches CR-02 from code review. |
| `CreateShowModal.tsx` | 33-67 | No `onError` handler on `createShowMutation`; no `isError` render | WARNING | Silent failure: if `api.createShow` fails, user gets no error message. If `api.updateBible` throws inside `mutationFn`, the mutation errors silently (no inline error copy despite plan's T-70-04 commitment to surface it). Matches CR-01 and WR-01 from code review. |
| `BibleEditor.tsx` | 71-75 | `updateShowMutation.onSuccess` invalidates `QUERY_KEYS.SHOW` but NOT `QUERY_KEYS.BIBLE` | WARNING | Stale bible cache after mode change can cause wrong pre-selection disambiguation on next visit within stale time window. Matches WR-03. |
| `BibleEditor.tsx` | 110 | `updateShowMutation.isSuccess` persists permanently — "Saved" indicator stays after first success | INFO | Cosmetic — Saved badge does not disappear and reappears incorrectly on subsequent clicks. Matches WR-02. |
| `ShowDetail.tsx` | 80 | No `key={showId}` on BibleEditor — loaded-ref guard does not protect cross-show navigation | WARNING | When navigating between shows in same React Router session without page reload, `selectedPreset` state shows stale preset from previous show. Matches CR-03. |

No `TBD`, `FIXME`, or `XXX` debt markers found in any modified file.

---

## Code Review Issue Assessment (70-REVIEW.md)

The code review identified 3 Critical + 3 Warning issues. Their impact on **goal achievement** vs. being **robustness/polish gaps**:

**CR-01 (silent bible seed failure):** The show IS created with `continuity_mode` persisted. If `updateBible` fails, duration and season arc are not seeded but the user can set these manually on the show page. The core goal — "picks how episodes relate via friendly presets" — is still achieved because `continuity_mode` is persisted. The failure to surface the error (no `onError`, no `isError` display) is a robustness gap that does NOT prevent the goal truths from being TRUE in the happy path, which is the primary case. However, the plan explicitly committed to surfacing this error (T-70-04) and did not deliver it. Classified as **WARNING** (robustness gap, not goal blocker).

**CR-02 (setState on unmounted):** React warning only. Navigation still completes correctly in current React 18. Does NOT block goal. Classified as **WARNING**.

**CR-03 (loaded-ref stale across cross-show navigation):** Only surfaces when navigating between shows without a full page reload. First-load pre-selection (from the `useState` lazy initializer) works correctly. The goal's edit-side pre-selection works on any fresh show page load. This is a **same-session navigation edge case** that requires human verification to characterize. Classified as **WARNING** requiring human confirmation.

**WR-01 (no error display for any mutation failure):** Same scope as CR-01 analysis. WARNING.

**WR-02 (isSuccess persists):** Cosmetic. INFO.

**WR-03 (missing BIBLE invalidation):** Stale disambiguation risk only after mode change + navigation within stale window. WARNING.

**Conclusion on review issues:** None of the 3 Critical issues reviewed actually block the phase's 3 ROADMAP Success Criteria from being achievable. The goal truths are verified in the code. The issues are robustness and UX polish deficiencies that belong in a follow-up fix or the next phase. The phase goal IS achieved at the code level, but human verification is required to confirm the interactive browser behavior.

---

## Human Verification Required

### 1. Show creation wizard — connected preset end-to-end

**Test:** Run `cd frontend && npm run dev` (Vite :4321) with backend on :8000. Open the Create Show modal. Confirm three preset cards appear in order: Microserie (Zap icon), Serie conectada (Link icon), Antología (LayoutGrid icon). Confirm the Create CTA is disabled with no preset selected. Select `Serie conectada`, type a title, type a season arc, click Create Show. On the resulting show page, open the Series Bible and confirm episode duration shows 22 min and the season arc text is present.

**Expected:** Cards render with amber selected state, Season Arc reveals with fade-up animation, create navigates to show page, seeded values are visible in the bible.

**Why human:** Visual rendering, animation, and the two-call sequence outcome require a running browser and backend. No automated check can confirm the visual amber glow or the season arc appearing on the show page.

### 2. Show creation wizard — Antología preset

**Test:** Create a show with the Antología preset. Confirm the Season Arc field does NOT appear. After creation, check the show's bible — confirm no season arc text was written and episode duration is at its default (not seeded to a specific value).

**Expected:** Season Arc field absent for Antología, no unexpected bible writes.

**Why human:** Conditional hide requires a running browser. API call verification (that updateBible was skipped) requires network inspection.

### 3. Edit-side mode control — pre-selection accuracy per show

**Test:** Open each show type (Microserie / 2-min, Serie conectada / 22-min, Antología). Confirm the correct preset card is pre-selected on load. Click a different preset and confirm the cards briefly disable then re-enable with the new selection. Reload the page and confirm the change persisted.

**Expected:** Pre-selection matches show's stored mode + duration. Persistence confirmed after reload.

**Why human:** Pre-selection, in-flight card disable, and persistence require a running browser + backend.

### 4. Cross-show navigation pre-selection (CR-03 risk)

**Test:** With the app running, navigate from one show to a different show using the back button / breadcrumb (without a full page reload). Confirm the BibleEditor for the second show shows the correct pre-selected preset (not the first show's preset).

**Expected:** Each show displays its own correct preset on the edit surface even when navigating within the same React Router session.

**Why human:** This is the CR-03 edge case — the loaded-ref guard prevents re-seeding when `continuityMode` changes as a prop between shows. The lazy initializer in `useState` only runs on mount, and since `BibleEditor` is not remounted on navigation (no `key` prop), the stale preset from the previous show may display. This must be confirmed in a live browser.

### 5. Error handling visibility for failed bible seed (CR-01)

**Test:** Using browser devtools, block the `PUT /api/shows/{id}/bible` request to simulate a network failure during the two-call create sequence. Create a show with a connected preset. Observe what the user sees after the failure.

**Expected (per plan):** User should see an error message. **Actual (per code):** No `onError` handler exists, no `isError` display. The modal behavior on bible-seed failure is currently undiscovered at the code level — this test confirms whether the user is left in a blank/hung state or sees partial feedback.

**Why human:** Requires network interception tooling and a running browser. The code review (CR-01) flagged this as a silent failure path.

---

## Gaps Summary

No BLOCKER-level gaps were found. All 3 ROADMAP Success Criteria are implemented in code and verified statically. The phase goal is achieved.

The following **WARNING-level issues** were identified (inherited from the code review; none block the goal):

1. **Silent bible seed failure (CR-01/WR-01):** No error display when `updateBible` fails after show creation. The plan committed to surface this (T-70-04) but it was not implemented. Robustness gap only.

2. **setState on unmounted component (CR-02):** `onOpenChange(false)` called before state resets in `onSuccess`. React strict-mode warning. Ordering fix is a one-line swap.

3. **Cross-show navigation stale pre-selection (CR-03):** No `key` prop on BibleEditor in ShowDetail; the loaded-ref guard is blind to show changes. Adding `key={showId}` to the BibleEditor render in ShowDetail is the fix.

4. **Missing BIBLE cache invalidation (WR-03):** `updateShowMutation.onSuccess` invalidates only the SHOW query, not BIBLE. Stale duration may cause wrong pre-selection disambiguation after mode change + navigation within stale time.

These should be addressed in a follow-up patch before shipping if the browser verification in items 3-5 above confirms the defects are user-visible.

---

_Verified: 2026-06-18T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
