---
phase: 49-side-by-side-quality-compare
reviewed: 2026-06-06T20:26:04Z
depth: deep
files_reviewed: 6
files_reviewed_list:
  - backend/app/services/template_ai_service.py
  - backend/app/api/endpoints/wizards.py
  - backend/app/models/schemas.py
  - frontend/src/lib/api.tsx
  - frontend/src/types/index.ts
  - frontend/src/components/Patterns/SceneCompareModal.tsx
  - frontend/src/components/Patterns/ScreenplayEditorView.tsx
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: findings
---

# Phase 49: Code Review Report

**Reviewed:** 2026-06-06T20:26:04Z
**Depth:** deep
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 49 adds single-scene regenerate (preview, no persist) + keep-scene-version (persist) on the backend, and a two-pane `SceneCompareModal` + per-scene trigger on the frontend. The refactor extracting `_generate_one_scene` is clean and the byte-identical prompt contract is preserved (the existing source-pin test was correctly redirected to the new helper). Authorization is correct on both endpoints — both are owner-scoped via a `Project.owner_id == current_user.id` filter that returns 404 for non-owners, and `episode_index` is bounds-checked against the owner's own `episodes`/`screenplays`, so no IDOR or cross-project indexing is possible. The regenerate endpoint genuinely writes nothing. No new injection/eval surface — persisted text follows the same trust path as the existing generate flow.

Two real WARNING-tier issues remain: (1) the keep-version write to `ScreenplayContent` can target a **stale duplicate row** because the batch generate path never deletes old rows, so the JSONB editor state and the breakdown/shotlist source rows can diverge; (2) `keepError` is not cleared when the user dismisses a failed-keep and the modal stays open across re-open in some flows. The remainder are INFO-level documented design tradeoffs and minor robustness notes.

No CRITICAL findings — there is no data-loss-on-the-happy-path, no auth bypass, and no injection.

## Warnings

### WR-01: keep-scene-version may update the WRONG / a STALE `ScreenplayContent` row when duplicates exist

**File:** `backend/app/api/endpoints/wizards.py:158-171`
**Issue:** The keep path updates the JSONB `screenplays[episode_index]` slot correctly (with `flag_modified`), but the matching `ScreenplayContent` row is selected via `next((r for r in rows if formatted_content.episode_index == request.episode_index), ...)` over rows ordered by `created_at, id` ascending — i.e. it picks the **oldest** matching row. The batch generate path (`apply_wizard_result_to_db`, `wizards.py:274-280`) **appends** new `ScreenplayContent` rows on every run and never deletes prior ones (confirmed: no `delete()` of `ScreenplayContent` anywhere in the backend). After any second batch run, there are duplicate rows per `episode_index`; keep-version then overwrites the *oldest* duplicate while the newest (the one actually reflecting current state) is left untouched. Downstream `breakdown_service` / `shotlist_generation_service` read **all** rows unordered, so the persisted JSONB editor state and the breakdown/shotlist inputs silently diverge after a keep. The `target.formatted_content = new_slot` write also makes a previously-newest row look like episode N's current text while the editor shows it elsewhere.
**Fix:** Select the row deterministically against the freshest set — e.g. order by `created_at.desc()` for the primary match, or (better) reconcile by replacing all rows for the project from the JSONB `screenplays[]` after the slot update, so `ScreenplayContent` is a pure projection of the editor state:
```python
target = next(
    (r for r in reversed(rows)
     if (r.formatted_content or {}).get("episode_index") == request.episode_index),
    None,
)
# or rebuild ScreenplayContent rows from content["screenplays"] to guarantee 1:1
```

### WR-02: `keepError` persists across a failed-keep dismissal and can leak into the next session

**File:** `frontend/src/components/Patterns/SceneCompareModal.tsx:118-127, 175-178, 247`
**Issue:** On a keep failure, `onError` sets `keepError`. The footer "Keep current" / overlay-close paths call `onOpenChange(false)`; the reset of `keepError` only happens in the `useEffect([open])` else-branch when `open` flips to false. That reset is fine for a full close, but the `genError` "Cancel" button and the "Keep new version" button only reset `keepError` on the *next* mutate (`setKeepError(null)` at line 247). If the keep fails and the user then triggers a *re-regenerate* via "Try again" (`runRegenerate`, line 96-104), `runRegenerate` resets `genError` and `generated` but **also** resets `keepError` — so that path is covered. However, the stale `keepError` banner remains visible during the entire generating/loaded window after a failed keep until either close or a new keep attempt, which contradicts the UI intent ("your stored scene is unchanged — try again") once a fresh regenerate is in flight. Minor data-integrity-adjacent UX bug, not a corruption risk.
**Fix:** Clear `keepError` in `runRegenerate` (it already clears it) — good — but also clear it when a new `generated` result arrives:
```ts
onSuccess: (result) => {
  if (result.error) { setGenError(result.error); setGenerated(null); }
  else { setGenerated(result); setGenError(null); setKeepError(null); }
},
```

## Info

### IN-01: Regenerate continuity is NOT byte-identical to the original batch prompt for non-first scenes (documented, but worth flagging)

**File:** `backend/app/api/endpoints/wizards.py:96-105`; `backend/app/services/template_ai_service.py:555-605`
**Issue:** The endpoint passes `synopsis = sp_content.get("synopsis", "")`, which is the **global running synopsis after all scenes**, into `regenerate_single_scene`. At batch time, scene `i` was generated with a synopsis covering only scenes `0..i-1`. So for any non-first scene the regenerate prompt's "Story so far" block differs from what the batch produced. This is explicitly called out as intended (D-49-05: "a single-scene regenerate is a quality spot-check, not a full re-thread"), and the docstring on `_generate_one_scene` correctly scopes its "byte-identical" guarantee to a *given* set of inputs. No fix required — flagging so the divergence is a conscious, reviewed decision rather than an accident.
**Fix:** None required. Optionally document in the modal copy that "New" uses full-story context, not the original at-that-point context.

### IN-02: `regenerate-scene` assumes `project.template` is set; screenplay projects without a template will 500

**File:** `backend/app/api/endpoints/wizards.py:393-394` (via `_get_project_context` → `_build_project_context`)
**Issue:** `_get_project_context` reads `project.template` and passes it to `_build_project_context`. The phase-49 test had to manually set `proj.template = "short_movie"` because the v1 create endpoint leaves it unset. If a real project somehow reaches the screenplay_editor stage without a template (unexpected, but not guarded), regenerate raises rather than returning a clean error. The existing `run_wizard` path shares this assumption, so this is consistent with prior code, not a regression.
**Fix:** Optional defensive guard returning a 422/404 with a clear message when `project.template` is falsy, rather than letting `_build_project_context` raise.

### IN-03: `_latest_script_wizard_config` silently falls back to empty runtime/guidance

**File:** `backend/app/api/endpoints/wizards.py:36-43, 82-88`
**Issue:** When no prior `script_writer_wizard` `WizardRun` exists, `runtime_target`/`custom_guidance` default to `""`. That changes the regenerate prompt versus what the original batch may have used if the WizardRun was pruned or the project was seeded another way. Acceptable best-effort behavior (the docstring says so), but it means the "New" pane is not guaranteed to use the same runtime/guidance the original scene used.
**Fix:** None required; consider surfacing in logs when the fallback is hit so prompt drift is debuggable.

### IN-04: Mount-effect depends only on `[open]`; stable today but fragile to a future "swap scene without closing" change

**File:** `frontend/src/components/Patterns/SceneCompareModal.tsx:106-117`; `ScreenplayEditorView.tsx:355-368`
**Issue:** The modal regenerates in `useEffect([open])`. It works only because the parent always sets `compareIndex` to `null` (closing the modal) before opening a different scene, so `open` toggles false→true each time and the effect re-fires with the new `episodeIndex` captured via `runRegenerate`'s deps. If a future change lets `episodeIndex` change while `open` stays `true`, the modal would show scene A's regenerate against scene B's `currentContent` (stale). The per-scene trigger's `e.stopPropagation()` correctly prevents the page-level click-to-edit from firing. The `RegenerateSceneResponse` TS type, the 120s `CHAT_TIMEOUT`, and the soft-`200 {error}` routing (`!response.ok` is false on 200, so `onSuccess` inspects `result.error`) all match the backend contract correctly.
**Fix:** Add `episodeIndex` to the gate, e.g. re-run when either `open` becomes true or `episodeIndex` changes while open, or remount via a `key={compareIndex}` on `<SceneCompareModal>` to guarantee fresh state per scene.

---

_Reviewed: 2026-06-06T20:26:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
