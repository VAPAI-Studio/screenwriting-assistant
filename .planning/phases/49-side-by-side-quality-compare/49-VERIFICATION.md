---
phase: 49-side-by-side-quality-compare
verified: 2026-06-06T00:00:00Z
status: human_needed
score: 3/3 success-criteria mechanisms verified (code complete; runtime UAT pending)
overrides_applied: 0
human_verification:
  - test: "Regenerate a NON-first scene, observe the two-pane compare"
    expected: "Modal opens; LEFT pane shows the current stored scene immediately; RIGHT pane shows the generating state ('Regenerating scene…', amber spinner) then the regenerated scene (up to ~60s). Both panes render in the same Courier screenplay style."
    why_human: "Requires the running stack + a live OpenAI call; the regeneration latency, visual rendering, and side-by-side layout can only be judged by a human at runtime."
  - test: "Click 'Keep current' (no-op path)"
    expected: "Modal closes; the screenplay view is unchanged (no persistence)."
    why_human: "Runtime UI behavior — observing that no state changed requires running the app."
  - test: "Click 'Keep new version' then reload (persistence path)"
    expected: "Button shows 'Saving…'; modal closes; the screenplay view re-renders with the NEW text for that scene ONLY; after a page reload the kept scene text persists."
    why_human: "End-to-end persistence + React Query invalidation re-render + reload survival can only be confirmed against the running stack."
  - test: "Confirm staleness after keep-new only"
    expected: "Project's breakdown and shotlist are flagged stale ONLY after keep-new, not after keep-current."
    why_human: "Cross-feature staleness indicators are visible only in the running app; unit tests prove the flag flips but the user-facing indicator is a runtime judgment."
  - test: "Error path (optional — break OPENAI_API_KEY)"
    expected: "Right pane shows 'Regeneration failed. Your current version is untouched.' with 'Try again' / 'Cancel'; the stored scene is unchanged."
    why_human: "Requires inducing a live generation failure against the running stack."
---

# Phase 49: Side-by-Side Quality Compare Verification Report

**Phase Goal:** The user can directly compare a scene regenerated with the improved path against its prior output to judge the cumulative quality improvement (EVAL-01).
**Verified:** 2026-06-06
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — EVAL-01)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| SC#1 | User can regenerate a scene's screenplay using the new (improved) generation path while preserving the prior output | ✓ VERIFIED (code) | `regenerate_single_scene` (template_ai_service.py:532-582) calls the shared `_generate_one_scene` (305-475) — the identical improved-path prompt builder (continuity block 337-346, voice block 352-359, unconditional `## Screenwriting Craft` 392-397, native `TITLE:` 410-412, `json_mode=False` 423). It does NOT advance the synopsis (no `_update_synopsis` call). The `POST /api/wizards/regenerate-scene` endpoint (wizards.py:367-428) writes NOTHING to the DB (no flag_modified/commit/ScreenplayContent create between owner-check and return) — preview-only, preserving the prior output (D-49-02). |
| SC#2 | The prior output and the newly generated output are displayed side-by-side for the same scene | ✓ VERIFIED (code) | `SceneCompareModal.tsx`: LEFT pane = CURRENT (`currentContent`, 213-226), RIGHT pane = NEW (regenerated `generated.content`, 229-274), both rendered with the identical 13px/20px `font-screenplay` paper renderer. The per-scene trigger rail in `ScreenplayEditorView.tsx:284-314` carries each scene's index via `setCompareIndex(i)`; the modal is opened for that specific `episodeIndex` with matching `currentTitle`/`currentContent` (356-367). |
| SC#3 | User can choose which version to keep, with the kept version persisting to `ScreenplayContent` | ✓ VERIFIED (code) | `keep_scene_version` endpoint (wizards.py:431-497) replaces `screenplays[episode_index]` in `screenplay_editor` PhaseData.content (flag_modified 474) AND updates the matching `ScreenplayContent` row (match by formatted_content.episode_index 484-489, fallback ordering — no migration), marks breakdown+shotlist stale (494-495), leaves `content["synopsis"]` untouched (472, D-49-05). Modal keep-new (SceneCompareModal.tsx:132-155) calls `api.keepSceneVersion` and on success `invalidateQueries(QUERY_KEYS.SUBSECTION_DATA)` + closes. "Keep current" is a pure no-op `onOpenChange(false)` (284-288). |

**Score:** 3/3 success-criteria mechanisms verified in code. Runtime user-facing behavior deferred to human UAT (intentional — Task 4 checkpoint:human-verify).

### Decision Compliance (D-49-01 .. D-49-05)

| Decision | Requirement | Status | Evidence |
| -------- | ----------- | ------ | -------- |
| D-49-01 | Regenerate reuses the improved path (not divergent) | ✓ SATISFIED | `regenerate_single_scene` delegates to `_generate_one_scene`; `_generate_scripts` delegates to the SAME helper (template_ai_service.py:509-520) — single shared prompt source. |
| D-49-02 | Preview → explicit keep; stale only on keep-new | ✓ SATISFIED | regenerate-scene writes nothing (wizards.py:367-428); stale-marking lives only in keep-scene-version (494-495). Tested: `test_regenerate_endpoint_returns_preview_and_does_not_persist` asserts `not breakdown_stale / not shotlist_stale` (389-390). |
| D-49-03 | episode_index key; NO migration/column | ✓ SATISFIED | Match-by-`formatted_content.episode_index` with ordering fallback (wizards.py:484-489). git diff across all phase-49 commits shows NO alembic/migration files, NO new DB column. |
| D-49-04 | Modal per UI-SPEC; targets a specific scene | ✓ SATISFIED | SceneCompareModal built on the Radix Dialog skeleton with two-pane compare, CURRENT/NEW badges, header pill, states per UI-SPEC; per-scene rail carries `episode_index`. |
| D-49-05 | Synopsis untouched on single-scene keep | ✓ SATISFIED | `regenerate_single_scene` does not call `_update_synopsis`; keep endpoint leaves `content["synopsis"]` untouched (wizards.py:472). Tested: `test_keep_scene_version_persists_and_marks_stale` asserts `pd.content["synopsis"] == "ORIGINAL SYNOPSIS"` (426). |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| backend/app/services/template_ai_service.py | `_generate_one_scene` + `regenerate_single_scene` | ✓ VERIFIED | Helper at 305, public method at 532; `_generate_scripts` delegates at 509. |
| backend/app/api/endpoints/wizards.py | regenerate-scene (preview) + keep-scene-version (persist) | ✓ VERIFIED | 367-428 and 431-497; both owner-scoped. |
| backend/app/models/schemas.py | RegenerateSceneRequest/Response + KeepSceneVersionRequest | ✓ VERIFIED | 565-587, correct fields. |
| backend/app/tests/test_scene_compare.py | regenerate-prompt + persist + no-persist + owner-auth tests | ✓ VERIFIED | 475 lines, 10 tests, all pass in isolation. |
| frontend/src/lib/api.tsx | regenerateScene (CHAT_TIMEOUT) + keepSceneVersion | ✓ VERIFIED | 1028 (CHAT_TIMEOUT AbortController), 1050 (fast fetchWithTimeout). |
| frontend/src/types/index.ts | RegenerateSceneResponse + request types | ✓ VERIFIED | Imported and used by modal + api client; build resolves them. |
| frontend/src/components/Patterns/SceneCompareModal.tsx | Two-pane Radix Dialog compare with keep actions | ✓ VERIFIED | 313 lines, full states + keep wiring. |
| frontend/src/components/Patterns/ScreenplayEditorView.tsx | Per-scene trigger opening SceneCompareModal | ✓ VERIFIED | Rail at 284-314, modal mount at 356-367. |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| `regenerate_single_scene` | `_generate_one_scene` | single-episode call | ✓ WIRED (template_ai_service.py:571) |
| `_generate_scripts` | `_generate_one_scene` | per-iteration delegation | ✓ WIRED (509) |
| keep-scene-version | `flag_modified(phase_data,"content")` | JSONB single-slot write | ✓ WIRED (wizards.py:474) |
| ScreenplayEditorView trigger | SceneCompareModal | local useState `compareIndex` + episode_index | ✓ WIRED (107-108, 303, 356) |
| SceneCompareModal (on open) | api.regenerateScene | useEffect gated on `open` → mutation, CHAT_TIMEOUT | ✓ WIRED (91-130) |
| SceneCompareModal keep-new | QUERY_KEYS.SUBSECTION_DATA | queryClient.invalidateQueries on keep success | ✓ WIRED (142-144) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Scene-compare suite passes in isolation | `pytest app/tests/test_scene_compare.py -x -q` | 10 passed | ✓ PASS |
| Regression trio (continuity/voice/craft/wizard) stays green | `pytest test_continuity_generation.py test_character_voice_injection.py test_craft_guidance.py test_wizard_injection.py -q` | 27 passed | ✓ PASS |
| Frontend type-checks + builds | `npm run build` (tsc && vite build) | ✓ built, 1912 modules, 0 type errors | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| EVAL-01 | 49-01, 49-02 | Regenerate a scene with the improved path and compare side-by-side against the prior output | ✓ SATISFIED (code) | SC#1/2/3 mechanisms all verified above; runtime UX pending human UAT. |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| ---- | ------- | -------- | ------ |
| (none) | No TBD/FIXME/XXX/HACK/PLACEHOLDER in any phase-49 modified file | — | Clean |

### Refactor Safety

The `_generate_scripts` → `_generate_one_scene` extraction preserved all anchored contracts: SCENE_MARKER ("YOUR TASK: Write scene"), `json_mode=False`, the native TITLE parser + fence tolerance + empty-title→summary fallback, the `{title,content,episode_index}` per-item shape, the `{screenplays,synopsis}` batch return, the success-only `_update_synopsis` advance (526-528), and the `[Generation failed: ...]` failure branch (470-474). The 27 prior tests (continuity 10, voice 8, craft 6, wizard 3) stay green. `test_craft_guidance.py` was correctly repointed from `_generate_scripts` to `_generate_one_scene` (the new single prompt source) — protective intent preserved, only the inspected symbol changed.

### Note on `npm run lint`

`npm run lint` cannot run — no ESLint config has ever existed in the repo (pre-existing tooling gap, confirmed in 49-02-SUMMARY and deferred-items.md). This is NOT a phase-49 regression. The binding type-safety gate (`npm run build` / tsc) passes clean. Not counted against the phase.

### Migration / Column / Dependency Checks

- No Alembic migration files added (git diff across phase-49 commits: no `alembic`/`migration` files).
- No new DB column (D-49-03 honored; ScreenplayContent matched by existing `formatted_content.episode_index` + ordering fallback).
- No new pip dependency (template_ai_service.added: []).
- No new npm dependency (SceneCompareModal reuses Radix Dialog + Button + lucide-react already present).

### Authorization

Both endpoints are owner-scoped: `Project.id == str(request.project_id)` AND `Project.owner_id == str(current_user.id)` → 404 "Project not found" on miss (wizards.py:386-391, 443-448). The `str()` coercion is the established codebase convention (Postgres- and SQLite-test-safe) — a documented, semantically-identical deviation from the verbatim run_wizard filter. Tested: `test_regenerate_endpoint_non_owner_404` and `test_keep_scene_version_non_owner_404` both assert 404.

### Human Verification Required

5 items routed (see frontmatter `human_verification`). All concern runtime user-facing behavior of the compare flow against the running stack with a live OpenAI call — exactly the Task 4 `checkpoint:human-verify` UAT that was deliberately deferred (user unattended). The code/mechanism for every item is verified present and correct above; only the live runtime judgment remains.

### Gaps Summary

No code gaps. All three EVAL-01 success criteria are mechanically satisfied in the actual source, all five decisions (D-49-01..05) are honored, the refactor is behavior-safe (27 + 10 tests green), the frontend builds clean, and there is no migration/column/dependency creep. The phase implementation is COMPLETE. The single outstanding item is the intentionally-deferred human UAT (runtime behavior), which is why status is `human_needed` rather than `passed` — per the decision tree, a non-empty human-verification section forces `human_needed`. This is NOT a failure and NOT a gap.

---

_Verified: 2026-06-06_
_Verifier: Claude (gsd-verifier)_
