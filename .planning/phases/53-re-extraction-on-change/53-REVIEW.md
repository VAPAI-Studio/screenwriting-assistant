---
phase: 53-re-extraction-on-change
reviewed: 2026-06-07T00:00:00Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - backend/app/services/breakdown_service.py
  - backend/app/tests/test_breakdown_service.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
---

# Phase 53: Code Review Report

**Reviewed:** 2026-06-07T00:00:00Z
**Depth:** deep
**Files Reviewed:** 2
**Status:** clean

## Summary

Phase 53 (Re-Extraction Hardening, v7.0) adds a single 9-line guard to the scene-link
reconciliation loop in `breakdown_service.extract()` and 3 new tests. The guard skips
`_reconcile_scene_links` for `user_modified` elements so a user's curated scene links are
not wiped/recreated on re-extraction.

The implementation is correct and tightly scoped. All five review concerns are satisfied:

- **Guard placement (item 1):** `if db_element.user_modified: continue` at
  `breakdown_service.py:572` sits AFTER the `if db_element is None: continue` check
  (line 570), so it cannot NPE on a `None` lookup result. It uses `continue` (not `break`),
  skipping only the reconcile call for that one element; the loop and element_map are intact.
- **No over-broad skip (item 2 — the key risk):** Condition is exactly
  `db_element.user_modified`. Non-user_modified elements fall through to
  `_reconcile_scene_links`. Verified by `test_non_user_modified_links_still_reconcile`,
  which pre-seeds an AI link to scene 0, re-extracts attributing the element to scene 3, and
  asserts the link MOVED (old gone, new present). No silent freeze of AI link tracking.
- **Edge: never-reconciled user element (item 3):** A user_modified element with no links
  simply stays link-less — the skipped call is the only effect. No crash path; `continue`
  short-circuits before any link access.
- **Test quality (item 4):** Test A (`test_user_modified_links_not_churned_on_reextract`)
  uses a pre-existing link with `source="ai"`, which `_reconcile_scene_links` WOULD delete
  absent the guard — so the assertion (link unchanged) genuinely proves the guard rather than
  a tautology. Test B proves scoping. Test C
  (`test_reextraction_chain_preserves_user_and_clears_stale`) proves the full
  stale -> re-extract -> user-preserved + fresh-AI-created + stale-cleared chain.
- **Quality/regression (item 5):** `test_user_modified_preserved` and
  `test_deleted_not_resurrected` remain green. Guard is consistent with the pre-existing
  SYNC-01 logic in `_upsert_elements` (lines 395-400) which already includes user_modified
  elements in element_map but skips overwriting them.

Verification: ran the 3 new tests plus both named regression tests — **5 passed, 0 failed**.
`_mark_breakdown_stale` resolves at the imported path
(`app/api/endpoints/phase_data.py:21`); all test helpers exist.

No CRITICAL/HIGH/MEDIUM findings. Status: clean.

## Narrative Findings (AI reviewer)

### Info

#### IN-01: Guarded user element bypasses link reconciliation even on legitimate scene deletion

**File:** `backend/app/services/breakdown_service.py:572`
**Severity:** LOW / INFO
**Issue:** By design the guard leaves user_modified links entirely untouched. If a scene
that a user-curated link points to is later deleted from the script, that link is not
re-pointed or cleaned by re-extraction (the reconcile call is the mechanism that would
prune it). This is the accepted product tradeoff for REEX-02/D-53-01 (user ownership wins),
and dangling-link cleanup on scene deletion is presumably handled elsewhere (e.g., FK
cascade or the scene-delete path), not here. No action required for this phase; noting only
so the contract is explicit.
**Fix:** None needed. If stale-link cleanup on scene deletion is NOT handled in the
scene-delete path, track that as a separate concern; it is out of scope for this guard.

---

_Reviewed: 2026-06-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
