---
phase: 52-expanded-categories
reviewed: 2026-06-07T00:00:00Z
depth: deep
files_reviewed: 7
files_reviewed_list:
  - backend/app/models/database.py
  - backend/app/models/schemas.py
  - backend/app/services/breakdown_service.py
  - frontend/src/types/index.ts
  - frontend/src/lib/constants.ts
  - backend/app/tests/test_breakdown_api.py
  - backend/app/tests/test_breakdown_service.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
---

# Phase 52: Code Review Report

**Reviewed:** 2026-06-07
**Depth:** deep (cross-site lockstep verification)
**Files Reviewed:** 7
**Status:** clean

## Summary

Phase 52 adds 5 production-breakdown categories (`set_dressing`, `animal`, `sfx`,
`makeup_hair`, `extras`) to the existing 5 (`character`, `location`, `prop`,
`wardrobe`, `vehicle`). This is a mechanical taxonomy expansion across 5 source
sites plus 2 test files. The primary risk — a spelling drift in any one site that
would silently 422 a valid category or leave a `Record` key unmatched — was the
focus of this review.

**Lockstep verified byte-identical.** I cross-checked each of the 5 new values
against every site individually (enum value, schema regex, prompt description,
service field description, FE union, FE `BREAKDOWN_CATEGORIES`, FE
`CATEGORY_COLORS`, FE `ELEMENT_EXTENDED_FIELDS`). All 50 occurrences match the
snake_case spelling exactly: `set_dressing`, `animal`, `sfx`, `makeup_hair`,
`extras`. No `makeup-hair`/`makeuphair`, no plural/singular drift, no casing
mismatch.

**Regex verified correct.** Executed the pattern
`^(character|location|prop|wardrobe|vehicle|set_dressing|animal|sfx|makeup_hair|extras)$`
against all 10 values (all accepted) and a set of near-miss/invalid inputs
(`set_dressings`, `makeup_hair_x`, `sfxx`, embedded newline, leading/trailing
space, etc.) — all correctly rejected. Anchored, no unescaped metacharacters, no
alternation gaps.

**Records exhaustive.** Both `CATEGORY_COLORS` and `ELEMENT_EXTENDED_FIELDS` are
typed `Record<BreakdownCategory, ...>`; TypeScript will fail compilation if any
of the 10 union members is missing — all 10 present in each. The new field shapes
are well-formed (`{ key, label, type }` with `type` in `'text' | 'textarea'`).

**Persistence safe without migration.** `BreakdownElement.category` is
`Column(String(50))` (free-text, not a native PG enum), so the new values persist
without a DB migration. The unique constraint `uq_breakdown_element` is on
`(project_id, category, name)` and is unaffected.

**Prompt quality good.** New category descriptions are all explicitly on-screen /
physically-present, consistent with the unchanged CRITICAL RULES (rules 1–2:
"PHYSICALLY APPEAR... visible to the camera", "do NOT extract elements merely
mentioned"). The PRECEDENCE block is coherent (living-creature-wins for
animal-vs-vehicle; handled-object-wins for prop-vs-set_dressing). CRITICAL RULES
and DEDUPLICATION sections are NOT in the diff (confirmed unchanged); section
order (CRITICAL RULES → DEDUPLICATION → CATEGORIES → PRECEDENCE) is intact.

**No regression.** None of the 5 pre-existing category values, colors, or field
shapes were altered. Tests cover accept-new (schema + extraction-persist) and
reject-unknown (`not_a_category` → ValidationError).

All reviewed files meet quality standards. No CRITICAL, HIGH, MEDIUM, or LOW
issues found. One INFO note below.

## Info

### IN-01: `extras` extended-field set diverges from siblings (intentional, noted for record)

**File:** `frontend/src/lib/constants.ts:350-353`
**Issue:** Four of the five new categories reuse the `specs / owner / status`
shape; `extras` instead uses `specs / count (Headcount) / status`. This is a
sensible domain choice (background performers are counted, not owned) and is
internally well-formed. Flagged only so a future reader does not "normalize" it
back to the `owner` shape by mistake.
**Fix:** None required. Optionally add a one-line comment noting `count` is
intentional for crowd headcount.

---

_Reviewed: 2026-06-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
