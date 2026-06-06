---
phase: 46-format-fidelity-native-vs-json-mode
verified: 2026-06-06T01:05:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: none
---

# Phase 46: Format Fidelity (Native vs JSON Mode) Verification Report

**Phase Goal:** Screenplay output preserves industry-standard formatting, with the generation call shape (native output vs json_mode `{title, content}`) settled to whichever yields better formatting.
**Verified:** 2026-06-06T01:05:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Truths = 4 ROADMAP success criteria + 5 PLAN frontmatter truths, deduplicated. All verified against the actual source, not SUMMARY claims.

| #   | Truth (source)                                                                                                                                                | Status     | Evidence |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------- |
| 1   | Scene-writing `chat_completion` runs with `json_mode=False` (native), not `json_mode=True` (SC#1/#3, FMT-02, D-46-01)                                          | ✓ VERIFIED | `template_ai_service.py:384` `json_mode=False`; method-slice assert: `json_mode=True` absent from `_generate_scripts`. Test `test_scene_call_uses_native_json_mode_false` asserts `scene_json_modes == [False]`. |
| 2   | Scene body lands in `content` as native multi-line text with real newlines — no `\n`-escaped blob, no JSON braces (SC#2, FMT-01, D-46-01)                       | ✓ VERIFIED | `template_ai_service.py:391-416` (`(text or "").strip()`, fence-strip, no `json.loads`). Test `test_native_content_has_real_newlines_no_json_encoding`: asserts `"\n" in content`, `"\\n" not in content`, not `{`-prefixed, no `"content":`, `content == body`. |
| 3   | Title parsed off a leading `TITLE:` line; absent/empty → falls back to scene summary; scene never fails over missing title (D-46-01)                            | ✓ VERIFIED | `template_ai_service.py:401-416`: case-insensitive `title:` prefix parse; `if not title: title = summary; content = text`. Tests `test_title_parsed_from_title_line` (title=="Scene 1") and `test_title_falls_back_to_summary_when_absent` (title=="Scene 1 summary"). |
| 4   | Prompt demands industry-standard layout (heading on own line, present-tense action, CAPS cues, parentheticals own line, dialogue beneath, blank lines) and no longer requests JSON (SC#2, FMT-01, D-46-02) | ✓ VERIFIED | `template_ai_service.py:360-373` strict layout rules + "Output the screenplay NATIVELY as plain text (NOT JSON...)". System prompt `:379` "Return the screenplay as native plain text only — no JSON". Method-slice assert: `Return valid JSON only` absent. No markup library added (requirements.txt unchanged). |
| 5   | Phase 45 contract preserved: per-screenplay `{title, content, episode_index}`, top-level `{screenplays, synopsis}`, success-only continuity advance, `[Generation failed: ...]` except branch (SC#3, D-46-03) | ✓ VERIFIED | `:418-422` item dict; `:426-427` advance only on success; `:428-435` except placeholder; `:437` return. Tests `test_per_screenplay_contract_unchanged`, `test_failed_scene_does_not_advance_continuity`, `test_synopsis_update_called_after_each_success` all pass. |
| 6   | Better-formatting approach adopted as default; title/content still captured for storage in `ScreenplayContent` (SC#3)                                          | ✓ VERIFIED | Single committed native path (D-46-04, no runtime A/B). `wizards.py:280-282`: `ScreenplayContent(content=sp.get("content"), formatted_content=sp)` — both fields fed from the per-screenplay dict. |
| 7   | Chosen approach works for both OpenAI and Anthropic via the existing provider abstraction (SC#4)                                                               | ✓ VERIFIED | Scene call uses the shared `chat_completion`. `ai_provider.py:78` OpenAI omits `response_format` when `json_mode=False` (native); `:107-110,125` Anthropic skips JSON instruction + fence-strip when native. In-method fence tolerance (`:392-399`) handles Anthropic's native fence case. |
| 8   | Native channel mirrors the proven `_update_synopsis` pattern (D-46-01 key link)                                                                                | ✓ VERIFIED | `_update_synopsis` (`:287-300`) and scene call (`:377-385`) share `json_mode=False` + `(text or "").strip()` + empty-fallback idiom. |
| 9   | Tests updated to native shape and pass; no JSON-string mock; marker-based routing (D-46-01)                                                                     | ✓ VERIFIED | `test_continuity_generation.py:57` `_scene_writer` returns `f"TITLE: {title}\n\n{content}"`; `:86` routes by `"YOUR TASK: Write scene"`; `:90` records `json_mode`. 9 passed. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/app/services/template_ai_service.py` | `_generate_scripts` migrated to native + TITLE parser w/ summary fallback; contains `json_mode=False` | ✓ VERIFIED | Substantive (`:375-437`), wired (called by wizards flow), data flows (real model text → parse → dict → `ScreenplayContent`). Contains `json_mode=False`. |
| `backend/app/tests/test_continuity_generation.py` | Native mock + marker routing + FMT assertions; existing continuity tests pass; contains `json_mode` | ✓ VERIFIED | 9 tests (5 regression + 4 FMT). Contains `json_mode`. All pass. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `_generate_scripts` | `ai_provider.chat_completion` | `json_mode=False` scene call (mirrors `_update_synopsis`) | ✓ WIRED | `template_ai_service.py:377-385`. |
| `_generate_scripts` | `wizards.py:271` | `{screenplays, synopsis}` + per-screenplay `{title, content, episode_index}` | ✓ WIRED | Producer `:418-437`; consumer `wizards.py:271` (`phase_data.content`) + `:278-282` (`ScreenplayContent`). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `_generate_scripts` | `screenplays[].content` | native `chat_completion` result parsed inline (no `json.loads`) | Yes — real model text, fence-stripped, body verbatim (test asserts `content == body`) | ✓ FLOWING |
| `_generate_scripts` | `screenplays[].title` | `TITLE:` line parse with `summary` fallback | Yes | ✓ FLOWING |
| `wizards.py` | `ScreenplayContent.formatted_content` | per-screenplay dict from `_generate_scripts` | Yes — full dict stored | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Scene call native; native body, no JSON escaping; TITLE parse + fallback; contract + continuity intact | `pytest app/tests/test_continuity_generation.py -x -q` | `9 passed` | ✓ PASS |
| Persistence/contract shape unchanged | `pytest app/tests/test_wizard_injection.py -q` | `3 passed` | ✓ PASS |
| Scene-method source intent (precise method slice) | `json_mode=False` present; `Return valid JSON only`/`result = json.loads`/`json.loads(text)`/`json_mode=True` absent; `TITLE`, `title = summary`, `{screenplays, synopsis}`, `[Generation failed:` present | all pass | ✓ PASS |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` and no probe declared in PLAN/SUMMARY. Phase verification is unit-test + source-assertion based (declared in PLAN `<verification>`), executed above. SKIPPED (no probes declared or conventional).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| FMT-01 | 46-01 | Output preserves industry-standard formatting without JSON-wrapping degrading it | ✓ SATISFIED | `template_ai_service.py:360-373` layout prompt + `:384` native channel + `:391-416` native parse (no `json.loads`). Test `test_native_content_has_real_newlines_no_json_encoding` proves no JSON escaping/braces; body verbatim. |
| FMT-02 | 46-01 | Generation path evaluated native vs json_mode; better approach adopted | ✓ SATISFIED | Reasoned adoption (D-46-04, 46-CONTEXT.md:37-39): native committed as single path, no runtime A/B. `:384` `json_mode=False`; old `json_mode=True`/`json.loads` removed from scene method. Test `test_scene_call_uses_native_json_mode_false` confirms adoption. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | None | — | No TBD/FIXME/XXX/HACK/PLACEHOLDER in either modified file. No stubs, no hollow data sources, no empty returns. |

### Migration / Frontend / Dependency Check

| Check | Result |
| ----- | ------ |
| Alembic migration added | No — no `alembic/versions` change in commits `0418b9a..3cd36ee`. |
| Frontend change | No — `git diff --name-only 0418b9a~1 3cd36ee -- frontend/` empty. |
| New dependency (`requirements.txt`) | No — `git diff … -- backend/requirements.txt` empty. T-46-SC package-legitimacy gate not triggered. |
| Commits exist | Yes — `0418b9a` (feat), `3cd36ee` (test) in `git log`. |
| Files touched | Exactly 2, both backend: `template_ai_service.py`, `test_continuity_generation.py`. |

### Executor Deviation Review

SUMMARY documents one deviation: the plan's `<verify>` source-assertion slices on the first `_generate_scripts` occurrence (the call site at line 75), sweeping in unrelated methods that legitimately contain `"Return valid JSON only"`, causing a false assertion failure. **Confirmed tooling-only:**
- Coarse slice (`src.split('_generate_scripts')[1]`) contains `"Return valid JSON only"` → True (false alarm from other methods).
- Precise method slice (`src.split('async def _generate_scripts')[1]`) contains `"Return valid JSON only"` → False (scene method is clean).
- No production code change was made for this deviation (`files modified: none`). The implementation already satisfied intent. Verified independently — not a code defect.

`json` import correctly preserved (`:3`, used at `:356` `json.dumps(ep)` and elsewhere) — not orphaned.

### Human Verification Required

None. This phase is a backend generation-channel change fully verifiable by source inspection, the provider-abstraction read, and unit tests. There is no visual/UX, real-time, external-service, or performance-feel dimension introduced by this phase. (The actual LLM formatting *quality* comparison is explicitly Phase 49 / EVAL-01, per D-46-04 — out of scope here.)

### Gaps Summary

No gaps. All 9 truths verified against real source; both requirements (FMT-01, FMT-02) satisfied; all four decisions (D-46-01..D-46-04) satisfied; the Phase 45 contract is intact and consumed correctly at `wizards.py:271/280`; both test suites green; no migration, frontend, or dependency change; the single documented deviation is tooling-only with no code impact.

---

_Verified: 2026-06-06T01:05:00Z_
_Verifier: Claude (gsd-verifier)_
