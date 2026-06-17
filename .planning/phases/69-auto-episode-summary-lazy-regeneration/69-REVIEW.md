---
phase: 69-auto-episode-summary-lazy-regeneration
reviewed: 2026-06-17T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/app/services/template_ai_service.py
  - backend/app/api/endpoints/projects.py
  - backend/app/api/endpoints/wizards.py
  - backend/app/utils/episode_summary.py
  - backend/app/tests/test_episode_summary.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 69: Code Review Report

**Reviewed:** 2026-06-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 69 diff against base `9460bcc^`: the new `summarize_episode` +
`_read_episode_text_by_index` in `template_ai_service.py`, the new
`POST /api/projects/{id}/episode-summary` endpoint in `projects.py`, the
`regenerate_stale_priors` pre-pass in `episode_summary.py`, and its wiring into
`run_wizard` in `wizards.py`.

The implementation is careful and well-commented: owner-scoping on the endpoint is
correct (404 on cross-user), the caller-commits convention is honored, the
existence-gate and graceful per-prior failure handling are implemented as described,
and the integer-key (non-positional) join honors the documented project memory. The
test suite is thorough.

No blockers found. The most important concern is a behavioral regression in
`run_wizard`'s "returns immediately" contract: the new pre-pass makes one inline,
serialized AI call per stale prior in the request thread before the handler returns,
which can stall the synchronous HTTP response unboundedly. The remaining findings are
robustness and consistency issues.

## Warnings

### WR-01: Pre-pass makes serialized blocking AI calls in the synchronous request path of an endpoint documented to "return immediately"

**File:** `backend/app/api/endpoints/wizards.py:135-143`
**Issue:** `run_wizard`'s docstring (line 125) states "Returns immediately; generation
runs in the background." The new pre-pass `await regenerate_stale_priors(db, show, project)`
runs *inline in the request handler*, before `build_bible_context` and before the
background task is even scheduled. `regenerate_stale_priors` loops over *every* stale
prior and `await`s `summarize_episode` for each one sequentially — each is a full
provider round-trip (GPT-4, `max_tokens=500`). For a connected show with N stale prior
episodes, the POST `/run` request now blocks for roughly N sequential model calls
before the 200 response is sent, defeating the immediate-return contract and risking
the frontend's 30s fetch timeout (`frontend/src/lib/api.tsx`). This is a behavior change
that the structural wiring test (`test_lazy_regen_call_precedes_build_bible_context_in_run_wizard`)
asserts as required ordering, so it is intentional — but the blocking/latency cost is
not bounded or surfaced.
**Fix:** Bound the work or move it off the request path. Minimum: cap the number of
priors regenerated per request (e.g., only the immediately-preceding episode, or a small
constant), since the bible context typically injects a limited prior window anyway. Better:
perform the regeneration inside the existing `_run_wizard_background` task (it already owns
a session and runs `build_bible_context`-equivalent reads off-thread) rather than in the
synchronous handler, or document explicitly that `/run` is no longer immediate in connected
mode and raise the frontend timeout accordingly.

### WR-02: `_read_episode_text_by_index` can raise `TypeError` from `sorted()` if `episode_index` values are not mutually orderable

**File:** `backend/app/services/template_ai_service.py:37`
**Issue:** `by_index` keys come directly from `formatted_content.get("episode_index")`
with no type coercion, then `sorted(by_index)` is called. If the JSON column ever yields
a mix of `int` and `str` keys (or all-`str` keys from legacy/externally-written rows),
`sorted()` raises `TypeError: '<' not supported between instances of 'str' and 'int'`,
which propagates out of `summarize_episode`. In the endpoint path this becomes a 500; in
the pre-pass path it is swallowed by the per-prior `try/except` (so a single bad prior
silently disables its regeneration). The sibling precedent in
`breakdown_service._align_screenplay_to_scenes` sidesteps this because it compares each
stored index against an `int` loop counter (`_ep_index(r) == i`) and wraps the whole loop
in a `try/except` returning `{}` — it never calls `sorted()` over heterogeneous keys, so
this helper is *less* robust than the precedent it cites.
**Fix:** Coerce/validate the index to `int` and skip non-coercible values:
```python
idx = (getattr(r, "formatted_content", None) or {}).get("episode_index")
if idx is None or not r.content:
    continue
try:
    idx = int(idx)
except (TypeError, ValueError):
    continue
by_index.setdefault(idx, r.content)
```

### WR-03: Provider failure in the eager endpoint is unhandled, returning an opaque 500

**File:** `backend/app/api/endpoints/projects.py:175`
**Issue:** `summary = await template_ai_service.summarize_episode(db, project)` has no
error handling. `summarize_episode` calls `chat_completion`, which can raise on provider
timeout/rate-limit/network errors. Unlike the pre-pass (which deliberately degrades on
provider failure per T-69-05), this endpoint lets the exception escape, producing a bare
500 with no domain-specific message. While not data-corrupting (the write happens only
after a successful summary), it is inconsistent error handling for a user-triggered AI
action and gives the client no actionable signal.
**Fix:** Wrap the call and map provider failures to a 502/503 with a clear detail, e.g.:
```python
try:
    summary = await template_ai_service.summarize_episode(db, project)
except Exception as exc:
    logger.error("Episode summary generation failed for %s: %s", project_id, exc)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Episode summary generation failed; please retry.",
    )
```

### WR-04: `regenerate_stale_priors` issues a `db.commit()` that flushes unrelated pending session state mid-request

**File:** `backend/app/utils/episode_summary.py:84`
**Issue:** The helper calls `db.commit()` on the *shared request session* passed in from
`run_wizard`. At the current call site (`wizards.py:143`) the only pending change is the
prior-summary mutations, so this is benign today. But the helper is a reusable utility and
`db.commit()` commits the *entire* session, not just its own changes — any object the
caller has added/dirtied before invoking the pre-pass (now or in future refactors) would
be silently committed here, outside the caller's intended transaction boundary. The
module docstring claims "this pre-pass owns the single `db.commit()`" but a session-wide
commit cannot own only its own rows. This is a latent coupling/transaction-boundary hazard.
**Fix:** Document loudly at the call site that the pre-pass commits the whole session, or
restructure so the pre-pass flushes its changes and lets the caller own the single commit
(the existing caller-commits convention used by `summarize_episode` itself). At minimum,
ensure no caller has uncommitted state when invoking the pre-pass.

## Info

### IN-01: Word cap is enforced only via prompt text, not via `max_tokens`, and the two are loosely coupled

**File:** `backend/app/services/template_ai_service.py:344,371`
**Issue:** `WORD_CAP = 250` is injected into the prompt ("Stay under 250 words") while the
hard bound is `max_tokens=500`. 250 words is roughly 330-375 tokens, so the soft cap and
hard cap are consistent, but they are independent magic numbers with no asserted
relationship. A future change to one without the other could truncate mid-sentence (model
ignores the prompt cap, hits the token wall). Consider deriving `max_tokens` from `WORD_CAP`
or co-locating both as named constants with a comment on their relationship.

### IN-02: Duplicate-index tiebreaker is documented as nondeterministic on SQLite, and the test only asserts "one of" the values

**File:** `backend/app/services/template_ai_service.py:35`; `backend/app/tests/test_episode_summary.py:191-207`
**Issue:** `order_by(created_at.desc(), id.desc())` is intended to make "newest wins" for
duplicate indices, but the helper's own docstring and the test
(`test_by_index_dedupes_duplicate_index_to_one_value`) acknowledge that on SQLite
`created_at` is second-resolution and `id` is a random UUID, so "newest" is not reliably
recoverable. The behavior is acceptable (matches breakdown_service precedent) and the test
correctly asserts only the meaningful invariant (a single value, not a doubled one), but
reviewers/maintainers should be aware that "newest wins" is best-effort, not guaranteed,
when duplicate rows share a second.

### IN-03: Blank-line scene join can produce a misleading boundary if a scene's content already contains blank lines

**File:** `backend/app/services/template_ai_service.py:38`
**Issue:** Scenes are joined with `"\n\n"`. Scene `content` is free-form screenplay text
that frequently contains its own blank lines, so the `\n\n` delimiter is not a reliable
scene boundary marker in the assembled prompt. This is purely a prompt-quality nuance (the
summarizer is asked for prose continuity, not structural parsing) and does not affect
correctness, but a more explicit delimiter (e.g., `\n\n---\n\n` or a scene header) would
make episode-internal structure clearer to the model. Low priority.

---

_Reviewed: 2026-06-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
