---
phase: 48-screenwriting-craft-guidance
reviewed: 2026-06-06T00:00:00Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - backend/app/services/template_ai_service.py
  - backend/app/tests/test_craft_guidance.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 48: Code Review Report

**Reviewed:** 2026-06-06T00:00:00Z
**Depth:** deep (cross-suite: voice + continuity regression run)
**Files Reviewed:** 2
**Status:** clean

## Summary

Phase 48 adds an unconditional `## Screenwriting Craft` block to the per-scene
script-writing prompt in `_generate_scripts` plus a new test module. I reviewed
both files against the four review axes (correctness, contract preservation,
collision, quality) and ran the new suite plus the two sibling suites
(`test_character_voice_injection.py`, `test_continuity_generation.py`).

Result: **6 new tests pass, 18 sibling tests pass — no regressions.** No MEDIUM+
findings. Two INFO observations only.

Verification highlights:

- **Unconditional / byte-identical**: The craft block
  (`template_ai_service.py:391-396`) is a plain literal inside the single shared
  f-string. It is NOT inside any `if/else` guard and is not duplicated across
  paths, so it is necessarily identical on the empty-characters, absent-characters,
  and with-characters paths. The Phase 47 byte-identical contract is preserved:
  the only per-path variance remains `character_block` (`:351-358`) and
  `continuity_block` (`:336-345`), both unchanged.
- **Additive placement**: The block sits between the optional `Custom guidance`
  line (`:389`) and the strict-layout rules (`:398+`). It does not displace the
  layout rules, the continuity block (`:383`), the voice block (`:376`), or the
  SCENE_MARKER (`:383`, `## YOUR TASK: Write scene {i+1} of {len}`). SCENE_MARKER
  substring "YOUR TASK: Write scene" intact.
- **Contract preservation**: `json_mode=False` (`:422`), `max_tokens=4000`
  (`:421`), TITLE parser (`:439-460`), return shape `{title, content,
  episode_index}` (`:462-466`) and `{screenplays, synopsis}` (`:481`) all
  untouched. Success-only continuity advance (`:468-471`) and the
  `[Generation failed: ...]` branch (`:472-478`) intact.
- **Collision guard (verified programmatically)**: The craft text contains NONE
  of "Story so far", "Previous scene", "distinct, consistent voice",
  "## Characters", "## Character Voice". Confirmed by direct substring scan and by
  green sibling suites that assert those markers absent in first-scene /
  no-character runs.
- **Tests are order-independent**: each test builds its own `_MockChat`, runs an
  isolated `asyncio.run`, and asserts only on locally captured prompts. Continuity
  state is rebuilt fresh per run inside `_generate_scripts` (`:327-328`), so there
  is no cross-test global state. No dead code; the "asserted anchor" comment
  convention is present (`:360-371` source, `:39-52` test).

## Info

### IN-01: Em-dash ellipsis chars in craft block are not anchor-asserted (low fragility risk)

**File:** `backend/app/services/template_ai_service.py:393-396`
**Issue:** The block uses Unicode em dashes (`—`) and the ellipsis-style examples
(`"she feels…"`). None of these non-ASCII glyphs are part of the test-asserted
anchors (the anchors are all plain ASCII: `on-the-nose`, `economical`,
`show, don't tell`, `no internal or unfilmable description`, `white space`), so an
accidental glyph change would not silently break a test that should fail. This is
fine today; just noting the anchors and the prose can drift independently.
**Fix:** No action required. If stricter pinning is ever wanted, add the literal
example phrases to the anchor set — but current coverage is adequate.

### IN-02: Bloat guard is a loose absolute bound, not a delta

**File:** `backend/app/tests/test_craft_guidance.py:190`
**Issue:** `assert len(later) < 20000` is a generous absolute ceiling. It will
catch gross runaway concatenation but would not catch a moderate-but-unintended
prompt-size regression (e.g. the craft block being accidentally duplicated per
scene). Given the craft block is a single literal and other tests pin its single
presence indirectly, the risk is minimal.
**Fix:** Optional — assert the craft header appears exactly once
(`later.count(CRAFT_HEADER) == 1`) to guard against accidental duplication. Not
required for ship.

---

_Reviewed: 2026-06-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
