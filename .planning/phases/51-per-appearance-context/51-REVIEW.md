---
phase: 51-per-appearance-context
reviewed: 2026-06-07T00:00:00Z
depth: deep
files_reviewed: 3
files_reviewed_list:
  - backend/app/services/breakdown_service.py
  - backend/app/tests/test_breakdown_service.py
  - frontend/src/components/Breakdown/ElementCard.tsx
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 51: Code Review Report

**Reviewed:** 2026-06-07
**Depth:** deep (cross-file: service -> model -> tests -> frontend type)
**Files Reviewed:** 3
**Status:** clean

## Summary

Phase 51 threads per-appearance AI context through the breakdown scene-link
pipeline: `_map_scene_indices_to_ids` now returns `List[Tuple[scene_id, context]]`
instead of `List[scene_id]`, `_reconcile_scene_links` writes `context=context`
(was hardcoded `""`), and the frontend scene chip renders `title={link.context
|| undefined}`.

The key risk identified in the brief — cross-wiring context to the wrong
scene_id — does not occur. Each pair is constructed atomically from a single
`appearance` object (`(scene_summaries[zero_based]["id"], appearance.context)`),
so scene_id and context cannot drift apart regardless of iteration order. The
consumer unpacks `for scene_id, context in new_links` and writes both to the
same `ElementSceneLink`. Tuple unpacking, ordering, and the user-link skip are
all correct.

Preservation guarantees hold: deletion is still scoped to `source == "ai"`; the
user-link skip uses the correctly-unpacked `scene_id`; dedup/upsert/audit and the
Phase-50 prompt are untouched. The new tests genuinely prove persistence — they
map each link to its scene via a dict keyed on `scene_item_id` and assert two
distinct non-empty contexts ("Draws sword" / "Presents sword"), so a regression
back to `""` would fail. Frontend type (`SceneLink.context: string`) matches and
the `|| undefined` guard prevents an empty-string tooltip.

No CRITICAL/HIGH/MEDIUM findings. Two LOW/INFO items below are pre-existing
observations, not regressions introduced by this diff.

## Info

### IN-01: Duplicate scene_index within one element's appearances can violate uq_element_scene

**File:** `backend/app/services/breakdown_service.py:470-483` (and consumer `:440-456`)
**Issue:** `_deduplicate_elements` de-dups `scene_index` only *across* merged
elements (`backend/app/services/breakdown_service.py:331-336`), not *within* a
single element's own `scene_appearances` list. If the AI returns the same
`scene_index` twice for one element, `_map_scene_indices_to_ids` emits two pairs
with the same scene_id and `_reconcile_scene_links` calls `db.add` twice for the
same `(element_id, scene_item_id)`, violating the `uq_element_scene` unique
constraint (`backend/app/models/database.py:581`) and failing the whole
extraction transaction. This is a **pre-existing** latent risk (the old
`List[str]` shape had it too) — Phase 51 neither introduces nor worsens it, but
the new per-appearance focus makes duplicate appearances more plausible.
**Fix:** De-dup within `_map_scene_indices_to_ids`, keeping the first context per
scene_id:
```python
seen_ids: set[str] = set()
for appearance in scene_appearances:
    zero_based = appearance.scene_index - 1
    if 0 <= zero_based < len(ctx.scene_summaries):
        sid = ctx.scene_summaries[zero_based]["id"]
        if sid in seen_ids:
            continue
        seen_ids.add(sid)
        scene_links.append((sid, appearance.context))
    else:
        logger.warning(...)
```

### IN-02: Tests assert membership only, not link count, for context cases

**File:** `backend/app/tests/test_breakdown_service.py:485-494`
**Issue:** `test_scene_link_context_persisted` builds `context_by_scene` and
asserts two specific entries but does not assert `len(links) == 2`. If a spurious
extra AI link (e.g., empty-context duplicate) were created, the test would still
pass. The sibling consolidation test (`:540-541`) does assert the count, so the
pattern is inconsistent. Minor — the existing assertions already prove the core
"" -> real-context change.
**Fix:** Add `assert len(links) == 2` before the context assertions in
`test_scene_link_context_persisted`.

---

_Reviewed: 2026-06-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
