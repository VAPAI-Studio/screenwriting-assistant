---
phase: 71-mode-aware-review
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - backend/app/services/agent_review_middleware.py
  - backend/app/api/endpoints/wizards.py
  - backend/app/tests/test_agent_review_middleware.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: resolved
---

# Phase 71: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 71 threads an optional `continuity_context` string through `review_step_output` →
`_merge_reviews` → the merge system prompt, and wires up the call site in `wizards.py`.
The session-boundary pattern (plain string, not ORM object) is correctly applied, D3
zero-agent pass-through is intact, and the D5 byte-identical default path is correct.

One blocker was found: `CONTINUITY_MERGE_BLOCK.format(continuity_context=...)` passes
AI-generated and user-supplied text through bare Python `.format()`, which crashes when
the input contains `{identifier}` sequences. Two test-quality warnings were also found.

---

## Structural Findings (fallow)

No structural pre-pass was provided for this phase.

---

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Format-string injection / crash in `_merge_reviews` via `CONTINUITY_MERGE_BLOCK`

**File:** `backend/app/services/agent_review_middleware.py:260`

**Issue:**

```python
system_prompt += CONTINUITY_MERGE_BLOCK.format(
    continuity_context=continuity_context.strip()
)
```

`CONTINUITY_MERGE_BLOCK` is a Python format-string template. The value being substituted
— `continuity_context` — is built from AI-generated `episode_summary` text and
user-supplied `title` fields inside `_build_prior_episodes_block` (see
`bible_context.py:68`):

```python
lines.append(f"\n**Episode {p.episode_number}: {p.title}**{marker}\n{p.episode_summary.strip()}")
```

Neither `p.title` nor `p.episode_summary` is sanitised for curly-brace sequences before
being concatenated into the string that becomes `continuity_context`. When either field
contains a `{word}` sequence (screenplay dialogue, scene instructions, or character
action lines routinely contain braces), `CONTINUITY_MERGE_BLOCK.format(...)` raises
`KeyError`. This is caught by the bare `except Exception` in `_run_wizard_background`,
which marks the run as `"failed"` and loses the result. Alternatively, if the exception
propagates out of `_merge_reviews` before the outer try/except catches it, `_merge_reviews`
returns `None` and review silently degrades to raw output without the merge step.

The implementation notes in the threat model (T-71-02) discuss token blow-up but miss
this crash vector entirely. Note that `_build_pipeline_system_prompt` at line 420 already
uses `format_map` with a `defaultdict` for exactly this reason — the new code regresses
from that established pattern.

**Fix:**

Replace `.format()` with string concatenation (or use a separator-based approach that
avoids template substitution entirely), mirroring how `bible_context.py` builds strings
with f-strings only on trusted values:

```python
# agent_review_middleware.py  _merge_reviews  ~line 259
if continuity_context and continuity_context.strip():
    # Do NOT use .format() — continuity_context is user/AI data and may contain
    # curly-brace sequences that crash str.format().  Use concatenation instead.
    system_prompt += (
        "\n\nCONNECTED-SHOW CONTINUITY REFERENCE:\n"
        "The following are summaries of PRIOR episodes in this show, provided ONLY "
        "as a coherence reference.\n"
        + continuity_context.strip()
        + "\n\nWhen applying the agent feedback, ADDITIONALLY flag any character or "
        "plot COHERENCE CONSIDERATIONS that read inconsistently against these prior "
        "episodes, and gently reconcile them where the agent feedback already supports it.\n"
        "Do NOT perform an exhaustive inconsistency audit or a correctness review of the "
        "prior episodes themselves — this is a light coherence pass, not full "
        "continuity-inconsistency detection. The prior summaries are reference only and "
        "must not be rewritten or emitted in the output."
    )
```

Alternatively, keep `CONTINUITY_MERGE_BLOCK` as a plain (non-template) string and
concatenate `continuity_context` at a fixed insertion point:

```python
CONTINUITY_MERGE_BLOCK_PREFIX = "\n\nCONNECTED-SHOW CONTINUITY REFERENCE:\n..."
CONTINUITY_MERGE_BLOCK_SUFFIX = "\n\nWhen applying the agent feedback..."

system_prompt += CONTINUITY_MERGE_BLOCK_PREFIX + continuity_context.strip() + CONTINUITY_MERGE_BLOCK_SUFFIX
```

---

## Warnings

### WR-01: D4-bound test assertion is trivially satisfied — "not" already present in base prompt

**File:** `backend/app/tests/test_agent_review_middleware.py:445`

**Issue:**

```python
lowered = merge_system.lower()
assert "inconsistency" in lowered or "exhaustive" in lowered
assert "not" in lowered                          # <-- always true
```

The assertion `assert "not" in lowered` at line 445 is intended to verify that the
merged system message explicitly forbids an inconsistency audit (D4). However, the
base `MERGE_SYSTEM_PROMPT` already contains the substring "not" ("Do NOT blend
conflicting feedback...") regardless of whether `CONTINUITY_MERGE_BLOCK` is appended.
The assertion passes even when the continuity block is completely absent, providing zero
coverage for the requirement that D4's bounding language is present.

**Fix:**

Assert on a token that is unique to `CONTINUITY_MERGE_BLOCK`'s anti-audit clause, such
as `"exhaustive"` or the phrase `"do not perform"`:

```python
# Replace the vacuous "not" assertion with a specific D4 token check
assert "exhaustive" in lowered or "do not perform" in lowered
```

This makes the test actually red when the bounded instruction is missing.

---

### WR-02: `_merge_system_message` test helper raises bare `StopIteration` on unexpected call shape

**File:** `backend/app/tests/test_agent_review_middleware.py:404`

**Issue:**

```python
return next(m["content"] for m in messages if m["role"] == "system")
```

`next()` called without a default value raises `StopIteration` if no system-role
message is found. This turns into an opaque failure rather than a meaningful assertion
error, making diagnosis harder when a future refactor changes the message structure.

**Fix:**

Supply a default that fails with a descriptive message:

```python
return next(
    (m["content"] for m in messages if m["role"] == "system"),
    None,  # callers will get AttributeError / AssertionError with context
)
```

Or use an explicit guard:

```python
system_msgs = [m["content"] for m in messages if m["role"] == "system"]
assert system_msgs, "No system message found in merge call"
return system_msgs[0]
```

---

## Info

### IN-01: `_build_prior_episodes_block` imported by its private name across module boundary

**File:** `backend/app/api/endpoints/wizards.py:15`

**Issue:**

```python
from ...utils.bible_context import build_bible_context, _build_prior_episodes_block
```

`_build_prior_episodes_block` carries a leading underscore (module-private convention).
The D2 decision deliberately reuses it, but importing a private symbol from another
module creates an undocumented contract. There is no indication in `bible_context.py`
that this function is intended to be imported externally, so a future refactor may
rename or inline it without realising the import in `wizards.py` will break.

**Fix:**

Either rename to `build_prior_episodes_block` (drop the leading underscore) with a
docstring noting it is also called from `wizards.py`, or add a comment in
`bible_context.py`:

```python
# Semi-public: also imported by api/endpoints/wizards.py (Phase 71 D2).
# Do not rename without updating that import.
def _build_prior_episodes_block(db: Session, show: Show, project: Project) -> Optional[str]:
```

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_


## Resolution (commit 91b9726)

All findings resolved and re-reviewed: CR-01 (str.format crash) fixed via prefix/suffix concatenation + brace regression test; WR-01 (vacuous assertion) tightened to suffix-only tokens; WR-02 (bare StopIteration) guarded; IN-01 documented. No new bugs. One pre-existing low-severity note (no prompt-injection fence) accepted as out-of-scope for this light internal-tool phase.
