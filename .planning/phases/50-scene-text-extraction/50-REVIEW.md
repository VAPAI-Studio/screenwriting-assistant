---
phase: 50-scene-text-extraction
reviewed: 2026-06-07T00:00:00Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - backend/app/services/breakdown_service.py
  - backend/app/tests/test_breakdown_service.py
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
status: clean
---

# Phase 50: Code Review Report

**Reviewed:** 2026-06-07
**Depth:** deep
**Files Reviewed:** 2
**Status:** clean (no MEDIUM+ findings)

## Summary

Phase 50 adds scene-scoped fidelity to the breakdown extractor: deterministic
newest-first ordering of `ScreenplayContent`, a new `_align_screenplay_to_scenes`
helper that maps per-scene text by `episode_index` with a positional fallback, and
a `_build_user_prompt` restructure that emits per-scene `### Scene {i+1}` headers
behind a strict full-coverage gate (falling back to the unchanged concatenated form
otherwise). I traced all five focus areas, ran the suite (12 passed), and cross-
checked the alignment logic against the proven `wizards.py:keep_scene_version` join.

**Verdict on the high-risk item (reversed-order positional fallback): correct.**
The implementation faithfully mirrors `wizards.py:484-499`. With newest-first rows
and ascending insertion order (the batch-append loop at `wizards.py:274` iterates
`screenplays` in scene order), `rows[len(rows)-1-i]` correctly recovers scene `i`.
No off-by-one, no reversal. Walk-through:
- N rows, none carry `episode_index`: scene 0 -> `rows[N-1]` (oldest = scene 0),
  scene N-1 -> `rows[0]` (newest = last scene). Ascending order recovered. Correct.
- Empty-content rows skipped; missing scenes omitted; gate then drops the aligned
  path. No mis-attribution.

**Other focus areas:**
1. **Full-coverage gate (item 2):** Strict. `full_coverage` requires
   `ctx.scene_summaries` non-empty AND `by_index.get(i)` truthy for every
   `i in range(len(scene_summaries))`. Any gap or empty string -> fallback. A
   partial/ambiguous map cannot reach the aligned path. Confirmed strict.
2. **Attribution integrity (item 3):** The `### Scene {i+1}` header iterates
   `enumerate(ctx.scene_summaries)`; `_map_scene_indices_to_ids` resolves
   `ctx.scene_summaries[scene_index-1]["id"]`. Both index the same `sort_order`-
   ordered `scene_summaries` list in the same 1-based emit / 1-based response space.
   No mismatch. `test_aligned_attribution_maps_to_scene_ids` proves index 1->id[0],
   3->id[2].
3. **Preservation (item 4):** Single `chat_completion_structured` call intact;
   `EXTRACTION_SYSTEM_PROMPT` byte-for-byte unchanged (guarded by
   `test_on_screen_only_rules_preserved`); dedup / upsert / reconcile / staleness /
   audit and the `ExtractedElement`/`ExtractionResponse` models untouched. Confirmed.

All findings below are INFO. None block shipping.

## Info

### IN-01: Positional-fallback ordering path is not exercised by any test

**File:** `backend/app/tests/test_breakdown_service.py:545-589`
**Issue:** The flagged highest-risk path — multiple `ScreenplayContent` rows that
lack `episode_index`, where the newest-first + index-from-end logic actually
determines mapping — has no test. The aligned test
(`_setup_project_with_aligned_screenplay`) gives every row an `episode_index`, so
the `next()` match always wins and the positional branch (`rows[len(rows)-1-i]`)
never runs. The fallback test uses a single row, where positional logic is trivial.
A future regression that reverses the index (`rows[i]` instead of
`rows[len(rows)-1-i]`) would silently mis-attribute elements and pass all 12 tests.
**Fix:** Add a fixture with 3 rows lacking `episode_index`, each with distinct
content inserted in scene order, then assert `_align_screenplay_to_scenes` returns
`{0: <oldest text>, 1: ..., 2: <newest text>}` — i.e. that scene 0 maps to the
first-inserted (oldest) row's text. This directly pins the reversed-order contract.

### IN-02: Positional fallback indexes the duplicate-inflated row list

**File:** `backend/app/services/breakdown_service.py:229-232`
**Issue:** When a project holds duplicate rows per `episode_index` (re-generation
case the docstring calls out), the `next()` episode_index match correctly picks the
most-recent duplicate. But if alignment ever reaches the positional branch in a
*mixed* state (some scenes match by index, some fall through), `len(rows)` and
`rows[len(rows)-1-i]` are computed against the duplicate-inflated list, so a
positionally-recovered scene could land on a duplicate of the wrong scene. In
practice this is unreachable for real data (batch-generated rows uniformly carry
`episode_index`, so the gate either fully matches by index or fully falls through),
which is why this is INFO not a defect. The strict full-coverage gate also means an
ambiguous mix simply degrades to the concatenated fallback rather than mis-labeling.
**Fix:** Optional hardening — dedupe `rows` to one entry per `episode_index`
(keeping the newest) before computing the positional fallback, so the positional
index space matches the logical scene count. Document the mixed-state assumption if
left as-is.

### IN-03: `screenplay_texts` ordering changed as a side effect of the new sort

**File:** `backend/app/services/breakdown_service.py:131-136, 188`
**Issue:** The concatenated fallback blob (`ctx.screenplay_texts`) is now emitted
newest-first because the query gained `order_by(created_at.desc, id.desc)`.
Previously it was unordered (DB default). For the fallback path the AI sees scenes
in reverse chronological insertion order, which may slightly degrade the model's
implicit scene-position inference in the concatenated form. The aligned path is
unaffected (it uses explicit headers). Not a correctness bug — `_map_scene_indices_
to_ids` keys off `scene_summaries` (sort_order), not blob position — but a behavior
change worth being aware of.
**Fix:** If concatenated-fallback readability matters, reverse the list for the
blob: `for text in reversed(ctx.screenplay_texts)` at line 294, or build
`screenplay_texts` in ascending order while keeping `screenplays` newest-first for
alignment. Low priority.

### IN-04: Redundant `list(screenplays)` and `getattr` defensive shims

**File:** `backend/app/services/breakdown_service.py:216, 222, 235`
**Issue:** `rows = list(screenplays)` re-wraps an already-materialized list (`.all()`
result), and `getattr(r, "formatted_content", None)` / `getattr(target, "content",
None)` defend against attributes that always exist on `ScreenplayContent`. Harmless,
but the defensive style obscures the actual contract (rows are always ORM instances)
and slightly hurts readability versus the cleaner `wizards.py` original which uses
`r.formatted_content` directly.
**Fix:** Drop `list()` and use direct attribute access
(`(r.formatted_content or {}).get("episode_index")`, `target.content`). The outer
`try/except` already satisfies the "never raises" guarantee. Cosmetic.

---

_Reviewed: 2026-06-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
