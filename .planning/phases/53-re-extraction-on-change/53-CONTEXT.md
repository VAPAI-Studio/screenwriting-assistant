# Phase 53: Re-Extraction Hardening - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user asleep; decisions by Claude, grounded in verified source — see .planning/v7.0-RESCOPE-NOTE.md).

<domain>
## Phase Boundary

When a scene's screenplay changes (v6.0 regenerate-and-keep, or a manual script/scene edit), the breakdown is flagged stale (REEX-01), and re-extraction refreshes the breakdown against the changed scene text WITHOUT discarding user-added/edited breakdown elements OR their curated scene links (REEX-02).

**Re-scope context (verified):** Most of this already works.
- **REEX-01 (stale on change): ALREADY SATISFIED.** `keep_scene_version` (v6.0) calls `_mark_breakdown_stale` (wizards.py:501); script/scene edits via `phase_data` call it (phase_data.py:218); the script_writer/scene wizard apply paths call it (wizards.py:282,326). `extract()` clears `breakdown_stale=False` after a successful run (breakdown_service.py:588-593).
- **REEX-02 (preserve user edits): MOSTLY SATISFIED, ONE GAP.** `_upsert_elements` skips `is_deleted` (no resurrection) and `user_modified` elements (no description overwrite) — breakdown_service.py:390-400. The element PUT endpoint sets `user_modified=True` (breakdown.py:222). `_reconcile_scene_links` deletes only `source="ai"` links and preserves `source="user"` links.
- **THE GAP:** a `user_modified` element is still added to `element_map` (line 398) and therefore `_reconcile_scene_links` IS called for it in the extract loop (lines 568-573) — which WIPES and recreates its AI-sourced scene links on every re-extract. A user who has taken ownership of an element (edited it) can have its scene-link set churned underneath them. REEX-02 ("preserve user edits") should extend to NOT touching a user-modified element's links at all.

**In scope:**
- Harden REEX-02: do NOT reconcile (wipe/recreate) scene links for a `user_modified` element — leave its links entirely alone (the user owns it). Surgical guard in the reconcile loop / reconcile method.
- Verify REEX-01 + the full v6.0→v7.0 chain with a test: keep-scene-version → breakdown_stale=True → re-extract → user-modified element (description + links) preserved → stale cleared.

**Out of scope:** changing the staleness triggers (already correct); a merge UI; re-extracting only the changed scene (current extract re-runs the whole project — acceptable; per-scene incremental re-extract is a future optimization). No schema change, no migration.
</domain>

<decisions>
## Implementation Decisions

### D-53-01 — Do not reconcile scene links for user_modified elements (DECIDED: skip reconcile when user owns the element)
**Grey area:** Re-extraction currently churns a user-modified element's AI-sourced scene links.
**Decision:** In the extract loop (breakdown_service.py:568-573), skip `_reconcile_scene_links` for any element whose `user_modified` is True (or, equivalently, guard inside `_reconcile_scene_links`). Once a user has edited an element (PUT sets `user_modified=True`), the system treats that element — including its scene links — as user-owned and leaves it untouched on re-extraction. New (AI) and unmodified elements continue to reconcile normally so their links track the current script. Rationale: this is the literal REEX-02 intent ("without discarding user-added/edited breakdown elements") extended to the links that belong to those elements, and it's consistent with the existing SYNC-01 (skip user_modified description) philosophy. Exact placement (loop guard vs. method guard) is Claude's Discretion; a loop guard checking `db_element.user_modified` before calling reconcile is simplest and avoids an extra query.
**Note on `element_map` membership:** user_modified elements stay in `element_map` (other code may rely on it); only the reconcile CALL is skipped for them.

### D-53-02 — Verify the full v6.0→v7.0 re-extraction chain (DECIDED: an integration test)
**Decision:** Add a test proving the end-to-end REEX flow: (1) seed a project with a breakdown; (2) mark a breakdown element `user_modified` (edited description + ideally a user-curated link); (3) simulate a scene change that marks breakdown stale (call `_mark_breakdown_stale` or the keep path); assert `breakdown_stale==True`; (4) run `extract()` again with an AI response that WOULD overwrite that element; (5) assert: the user-modified element's description is preserved, its links are NOT churned (D-53-01), AI elements refresh, and `breakdown_stale` is cleared. This is the REEX-01+REEX-02 proof.

### D-53-03 — Preserve all existing behavior (DECIDED: additive guard only)
**Decision:** No change to staleness triggers, the single AI call, EXTRACTION_SYSTEM_PROMPT, dedup, the per-appearance context (Phase 51), the scene-scoped prompt (Phase 50), the expanded categories (Phase 52), `is_deleted`/`user_modified` description skipping (SYNC-01/02), or the stale-clear. The ONLY behavior change is: user_modified elements' scene links are no longer reconciled on re-extract. Existing tests — including `test_user_modified_preserved` and the scene-link/context tests — MUST stay green (verify the change doesn't break the existing user_modified description-preservation test, which doesn't assert link churn). No schema change, no migration.
</decisions>

<code_context>
## Existing Code Insights (verified)
- `_upsert_elements` (breakdown_service.py:357-427): skips is_deleted (390), skips user_modified description overwrite but adds to element_map (395-400), updates/creates otherwise.
- extract loop (568-573): `for extracted_el in deduplicated: db_element = element_map.get(...); if None: continue; _reconcile_scene_links(...)` — calls reconcile for EVERY mapped element INCLUDING user_modified. THE GUARD GOES HERE (skip when db_element.user_modified).
- `_reconcile_scene_links` (429-466): deletes source="ai" links, recreates from new_links, preserves source="user" links + skips pairs with an existing user link. (Phase 51 added context to the recreated links.)
- Element PUT (breakdown.py:202-222): sets user_modified=True on edit. Scene-link POST/DELETE (breakdown.py ~276-308): source="user".
- Staleness: `_mark_breakdown_stale` (phase_data.py:21-36) sets project.breakdown_stale=True iff a non-deleted breakdown element exists; called from keep_scene_version (wizards.py:501), wizard applies (282,326), phase_data PATCH (218). `extract()` clears it (588-593).
- Tests: `test_user_modified_preserved` (SYNC-01) + `test_deleted_not_resurrected` (SYNC-02) in test_breakdown_service.py — the patterns to extend; test_staleness.py for the stale flag. AsyncMock chat_completion_structured pattern.

## Pre-existing test-isolation concern: see v6.0-PREEXISTING-TEST-CONCERN.md (not breakdown).
</code_context>

<specifics>
## Specific Ideas
- Backend (surgical): one guard in the extract loop — skip `_reconcile_scene_links` when `db_element.user_modified` is True. ~2-4 lines.
- Tests:
  1. REEX-02 link preservation: a user_modified element with existing scene links; re-extract with an AI response attributing it to DIFFERENT scenes; assert the element's links are UNCHANGED (not churned to the new AI scenes), and description preserved.
  2. Full chain (D-53-02): breakdown exists → mark stale (assert True) → extract() → user_modified element preserved + AI elements refreshed + breakdown_stale cleared (assert False).
  3. Regression: a NON-user_modified element's links DO still reconcile to the new AI scenes (proves the guard is scoped to user_modified only).
  - Keep test_breakdown_service.py + test_breakdown_api.py + test_staleness.py green.
- No schema change, no migration, no FE change (this is a backend-behavior hardening; the existing breakdown UI already shows whatever links exist).

## Verification framing
- REEX-01: stale-on-change already wired (keep_scene_version + phase_data + wizard applies) — VERIFIED via the chain test.
- REEX-02: user edits (description AND links) preserved on re-extract — the BUILD (link guard) + the chain test.
</specifics>

<deferred>
## Deferred Ideas
- Per-scene incremental re-extraction (only re-extract the changed scene) — current whole-project re-extract is acceptable; optimization for later.
- A breakdown "merge review" UI (show what re-extraction would change before applying) — out of scope.
- Marking an element user_modified when ONLY its links are user-edited (today PUT on the element body sets it; a pure link add/remove sets the link source="user" but not the element flag) — the link-source preservation already covers user links; the element-flag-on-link-edit nuance is a future refinement.
</deferred>
