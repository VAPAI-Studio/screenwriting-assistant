---
phase: 46-format-fidelity-native-vs-json-mode
reviewed: 2026-06-06T00:00:00Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - backend/app/services/template_ai_service.py
  - backend/app/tests/test_continuity_generation.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 46: Code Review Report

**Reviewed:** 2026-06-06
**Depth:** deep
**Files Reviewed:** 2
**Status:** clean

## Summary

Phase 46 migrates the scene-writing call in `_generate_scripts` from JSON mode to
native plain-text output and replaces `json.loads(text)` with a hand-rolled
`TITLE:`-line parser plus a code-fence tolerance shim. The companion test file
updates its mock routing (now keyed on the positive `"YOUR TASK: Write scene"`
marker instead of `json_mode`) and adds FMT assertions for native newlines,
json_mode=False, TITLE parsing, and the summary fallback.

This is a clean, well-scoped diff. I traced every parser edge case the brief
called out and found no path that crashes or breaks the scene loop:

- **Empty response (`""`)**: no fence, `find("\n") == -1`, `first_line == ""`,
  no `title:` prefix → `if not title` fallback → `title = summary`, `content = ""`. Safe.
- **Fence-only (` ``` `)**: fence branch drops line 1 → `lines == []`; the trailing
  check is guarded by `if lines and ...` so no IndexError; `text` becomes `""` →
  summary fallback. Safe (the `if lines and` guard correctly prevents the empty-list crash).
- **Leading fence + body**: opening fence line dropped, optional closing fence
  dropped, then TITLE parse proceeds on the unwrapped text. Correct.
- **`TITLE:` with no body / no newline**: `first_nl == -1`, `rest == ""`,
  `content == ""`, title truthy → no fallback. Acceptable.
- **Content that itself contains the word TITLE**: only the first line is tested
  via `first_line.strip().lower().startswith("title:")`, so a mid-body "TITLE"
  is never mis-parsed. Correct.
- **Extra whitespace around the colon/value**: `split(":", 1)[1].strip()` handles
  leading/trailing whitespace on both the prefix (via `first_line.strip()`) and
  the value. Correct.

**Contract preservation** is intact: per-screenplay `{title, content, episode_index}`
(lines 418-422), top-level `{screenplays, synopsis}` return (line 437),
success-only continuity advance (`prev_scene_text`/synopsis updated only after the
append, inside the try, lines 426-427), and the `[Generation failed: ...]` except
branch (lines 428-435) are all unchanged. The 9 tests pass.

**Security**: No injection or unsafe-eval surface introduced. The scene result is
no longer passed to `json.loads` (the removed line); no `eval`/`exec`/`json.loads`
was added in `_generate_scripts`. The model text flows to `json.dumps` only when
re-serialized downstream, which is safe escaping, not evaluation. The comment at
line 388-390 claiming the provider does NOT strip fences in native mode is
**verified accurate**: `ai_provider.py:125` gates fence-stripping on `if json_mode and ...`.

**Quality**: The preserved `json` import is still used (17 references across the
file). No leftover JSON-mode remnants in the scene path, no debug artifacts, no
dead code. Comments are accurate and decision-ID-anchored.

No MEDIUM-or-higher findings. Two INFO notes below are minor observations only.

## Info

### IN-01: Empty-title fallback re-emits the `TITLE:` line into screenplay content

**File:** `backend/app/services/template_ai_service.py:414-416`
**Issue:** When the model emits a TITLE line with an empty value (e.g.
`"TITLE:\n\nINT. ROOM - DAY..."`), the parser correctly strips `title` to `""`,
but the `if not title:` fallback then sets `content = text` — the *original*
text, which still contains the literal `TITLE:` line at the top of the body. The
intended title is stripped, then re-glued into the screenplay content. This is
cosmetic (a stray `TITLE:` line in the rendered scene), never a crash, and only
triggers on an empty-title edge case. The far more common no-TITLE-line case is
unaffected (content correctly equals the full text, which is the desired behavior).
**Fix:** If a tighter result is wanted, fall back only the title and keep the
already-split body:
```python
if not title:
    title = summary
    # content already holds the post-TITLE body; only reset when no split occurred
    if first_nl == -1 or not first_line.strip().lower().startswith("title:"):
        content = text
```
Low priority — current behavior is acceptable for an MVP and matches the documented
empty-fallback idiom.

### IN-02: Fence-tolerance shim assumes a single-line opening fence

**File:** `backend/app/services/template_ai_service.py:392-399`
**Issue:** The shim unconditionally drops `lines[1:]` (the first line) when the text
starts with ` ``` `. This is correct for the normal ` ```text\n...` form. If a
provider ever emitted a bare ` ``` ` followed immediately by the TITLE line on the
*same* logical block, or a language tag spanning oddly, the first content line could
be consumed. In practice native-mode providers rarely wrap in fences at all (the
system prompt explicitly forbids it), so this is a defensive shim for a low-probability
case and the current handling is reasonable.
**Fix:** None required. Optionally guard with a comment noting the single-line-fence
assumption, or strip only a fence line matching `^```[a-zA-Z]*$`.

---

_Reviewed: 2026-06-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
