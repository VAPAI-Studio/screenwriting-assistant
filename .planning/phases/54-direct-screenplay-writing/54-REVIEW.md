---
phase: 54-direct-screenplay-writing
reviewed: 2026-06-07T00:00:00Z
depth: deep
files_reviewed: 3
files_reviewed_list:
  - backend/app/api/endpoints/phase_data.py
  - frontend/src/components/Patterns/ScreenplayEditorView.tsx
  - backend/app/tests/test_api.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-06-07
**Depth:** deep
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the direct-screenplay-writing change set: the PATCH upsert + screenplay-scoped
ScreenplayContent reconcile (`phase_data.py`), the writable empty-state + `splitByHeadings`
splitter (`ScreenplayEditorView.tsx`), and the new `TestScreenplayWriteSave` suite. All 6 new
tests pass.

The two highest-risk properties called out in scope hold up:

- **2b (over-broad delete):** The reconcile is correctly gated by
  `phase == "write" and subsection_key == "screenplay_editor"`. A generic PATCH to any other
  subsection (even one carrying a `screenplays` key) does NOT touch ScreenplayContent. Verified
  in code and by `test_generic_subsection_save_creates_no_screenplaycontent`. No data-wipe risk
  on unrelated saves. **Clean.**
- **2a (non-idempotent accumulation):** Delete-then-recreate inside a single transaction yields N
  rows, not 2N, and the delete is `project_id`-scoped. Verified in code and by
  `test_screenplay_save_is_idempotent`. **Clean.**

`episode_index` is preserved (the whole scene dict is stored in `formatted_content`), the
transaction is atomic (a failed recreate rolls back the delete — no zero-row-committed window),
and staleness still fires via the existing `*_SENSITIVE_PHASES` calls with no duplication.

Remaining findings are real but lower-severity: a from-scratch data-loss edge in `splitByHeadings`
(preamble before the first slugline is silently dropped), an explicit-empty-screenplays save that
does not clear stale ScreenplayContent rows, and a test-coverage gap that does not actually guard
the cross-project scoping property it claims to protect.

## Warnings

### WR-01: `splitByHeadings` silently drops preamble text before the first slugline (data loss)

**File:** `frontend/src/components/Patterns/ScreenplayEditorView.tsx:78-88`
**Issue:** In the from-scratch path, any text typed before the first recognized `INT./EXT.`
slugline is discarded. Lines arriving while `currentTitle === null` hit neither branch (no heading,
and the `else if (currentTitle !== null)` guard is false), so they are dropped entirely. A user who
writes a standard opener like `FADE IN:` (or a title block) above the first scene heading loses that
text on save — and on reload `buildDocument` renders only the scenes, so the loss is silent and
permanent. The inline comment acknowledges this as intentional, but silently discarding typed
content is a correctness defect, not a style choice.
**Fix:** Capture preamble into a leading scene rather than dropping it. When the first heading is
encountered and `currentBody`/preamble is non-empty, emit a `{title:"", content:<preamble>}` (or
"Untitled") scene before starting the first real scene:
```ts
let preamble: string[] = [];
for (const line of lines) {
  if (headingRe.test(line)) {
    if (currentTitle === null && preamble.join('').trim()) {
      scenes.push({ episode_index: scenes.length, title: 'Untitled',
        content: preamble.join('\n').trim() });
    }
    flush();
    currentTitle = line.trim();
  } else if (currentTitle !== null) {
    currentBody.push(line);
  } else {
    preamble.push(line);
  }
}
```

### WR-02: Saving an explicit empty `screenplays: []` does not clear stale ScreenplayContent rows

**File:** `backend/app/api/endpoints/phase_data.py:241-244`
**Issue:** The reconcile is guarded by `if screenplays:`. When `screenplays` is an empty list, the
delete/recreate block is skipped, so any previously persisted ScreenplayContent rows survive while
`PhaseData.content.screenplays` is set to `[]`. The breakdown extraction reads ScreenplayContent
directly, so it would continue to see deleted scenes — PhaseData and ScreenplayContent drift out of
sync. In the current frontend this list is hard to produce (single-original clears collapse to one
empty-content scene, not `[]`), so impact is limited today, but the endpoint is a public contract
and the guard hides a "clear all scenes" operation.
**Fix:** Distinguish "key absent" (skip) from "key present but empty" (clear). Run the delete
unconditionally when the screenplays key is explicitly provided, and only recreate when non-empty:
```python
if phase == "write" and subsection_key == "screenplay_editor":
    if "screenplays" in (update.content or {}):
        screenplays = update.content["screenplays"] or []
        db.query(database.ScreenplayContent).filter(
            database.ScreenplayContent.project_id == str(project_id)
        ).delete(synchronize_session=False)
        for sp in screenplays:
            db.add(database.ScreenplayContent(
                project_id=str(project_id),
                content=sp.get("content", ""),
                formatted_content=sp,
            ))
```

### WR-03: Tests do not actually guard the cross-project scoping property they claim to protect

**File:** `backend/app/tests/test_api.py:251-271` (idempotence) and `352-373` (generic non-sync)
**Issue:** The scope's highest-risk property — "the delete is scoped to THIS project's rows only,
not other projects'" — is asserted nowhere. `test_screenplay_save_is_idempotent` uses a single
project, so it would still pass if a future edit dropped the `project_id` filter from the delete and
wiped every project's screenplays. The idempotence test cannot detect an over-broad delete regression.
**Fix:** Add a test that creates two owned projects, saves screenplays to project A, then saves to
project B, and asserts project A's ScreenplayContent rows are untouched (count unchanged, content
intact). This is the regression that would be catastrophic in production and is currently unguarded.

## Info

### IN-01: Upsert can 500 on an invalid `phase` string where it previously returned a clean 404

**File:** `backend/app/api/endpoints/phase_data.py:212-220`
**Issue:** `phase` is an unvalidated `str` and `PhaseData.phase` is a SQLAlchemy `Enum(PhaseType)`.
Before this change, a PATCH to a non-existent row always 404'd, so an invalid phase (e.g.
`/api/phase-data/{id}/foobar/key`) never reached an INSERT. The new fetch-or-create now constructs
`PhaseData(phase="foobar")`, which raises on flush/commit and surfaces as a 500 instead of a clean
4xx. Same family of risk for an unknown-but-syntactically-valid `subsection_key` is benign (free
text), but the phase enum is not.
**Fix:** Validate `phase` against `PhaseType` early and raise `400` (or `404`) before the upsert:
```python
if phase not in {p.value for p in database.PhaseType}:
    raise HTTPException(status_code=400, detail=f"Invalid phase '{phase}'")
```

### IN-02: Concatenated `screenplay_texts` ordering is non-deterministic for same-transaction rows

**File:** `backend/app/api/endpoints/phase_data.py:245-250` (writer) / `breakdown_service.py:142-145`
(reader)
**Issue:** All reconciled rows are inserted in one transaction, so `created_at` (server `now()`) is
identical across them; the extraction context orders by `created_at.desc(), id.desc()`, leaving
`id` (a random UUID) as the effective tiebreaker. The concatenated-fallback `screenplay_texts` list
can therefore come back in arbitrary scene order. The primary aligned path is unaffected (it joins
strictly on `formatted_content.episode_index`, which the reconcile preserves), so impact is limited
to the degraded fallback prompt. This is a pre-existing reader characteristic the phase inherits, not
introduced here, but the manual-save path now makes same-timestamp batches the common case.
**Fix:** Have the reader order by `formatted_content.episode_index` when present (or sort
`screenplay_texts` by episode_index) so the concatenated fallback is also scene-stable.

### IN-03: Concurrent first-save race surfaces as a 500 (IntegrityError) rather than a graceful retry

**File:** `backend/app/api/endpoints/phase_data.py:202-220`
**Issue:** Two simultaneous first-time PATCHes for the same `(project_id, phase, subsection_key)`
both see `data is None` and both attempt an INSERT. The `uq_phase_data_lookup` unique constraint
prevents a silent duplicate (good — no data corruption), but the loser gets an IntegrityError → 500.
This matches the existing wizard upsert pattern, so it is not a new regression, just an inherited
sharp edge. No duplicate PhaseData can be created.
**Fix (optional):** Catch `IntegrityError`, rollback, re-query the now-existing row, and continue the
merge — or rely on DB-level `ON CONFLICT` upsert.

### IN-04: `splitByHeadings` heading regex misses `INT.`/`EXT.` with no separator and embeds `\r` on CRLF input

**File:** `frontend/src/components/Patterns/ScreenplayEditorView.tsx:57,59,73`
**Issue:** The regex requires `[\s.]` after the prefix, so `INT.CASTLE` (period immediately followed
by a non-space) is not recognized as a slugline and collapses into the prior scene's body. Separately,
`text.split('\n')` on CRLF input leaves a trailing `\r` on each body line; `title.trim()` cleans the
title, but body `\r`s are re-joined verbatim. Both are low-likelihood (browsers normalize textarea
newlines to `\n`, and writers usually put a space after `INT.`), but they are silent-text-shape
issues in the from-scratch path.
**Fix:** Allow an immediate word boundary in the heading regex (e.g. accept `[\s.]` or end-aware
matching) and normalize CRLF first: `text.replace(/\r\n?/g, '\n')` at the top of `splitByHeadings`.

---

_Reviewed: 2026-06-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
