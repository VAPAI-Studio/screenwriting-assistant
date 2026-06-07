# Phase 52: Expanded Categories - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user asleep; decisions by Claude, grounded in verified source).

<domain>
## Phase Boundary

The breakdown element taxonomy is broadened from the current 5 categories to cover more production-relevant categories, additively (existing categories + already-extracted data remain valid), and the breakdown UI displays + filters by the expanded set (CATG-01/02/03).

**Verified scope facts:**
- Categories live in FIVE places: `BreakdownCategory` enum (database.py:138-143), the system-prompt CATEGORIES list (breakdown_service.py:101-106), the schema regex `pattern="^(character|location|prop|wardrobe|vehicle)$"` (schemas.py:698), the frontend `BREAKDOWN_CATEGORIES` constant (constants.ts:278-284), and the frontend `BreakdownCategory` TS union type (types/index.ts:269).
- `category` is a `String(50)` column (database.py:548), NOT a DB enum — so adding values needs NO migration and existing rows stay valid (CATG-02 satisfied structurally).
- The frontend `CategoryTabs` ITERATES `BREAKDOWN_CATEGORIES` (CategoryTabs.tsx:20,38) to render tabs + counts + filtering — so adding to the constant auto-generates the UI tabs/filter (CATG-03 mostly automatic). No per-category icon map to maintain.

**In scope:** add the new categories to all five definition sites; ensure the system prompt teaches the AI when to use each (with on-screen-only discipline); confirm the UI tabs/filter pick them up.

**Out of scope:** per-category icons/colors (nice-to-have, not required by CATG-03); changing extraction logic beyond the category list + prompt guidance; phases 50/51/53 concerns. No migration.
</domain>

<decisions>
## Implementation Decisions

### D-52-01 — The expanded category set (DECIDED: +5 categories → 10 total)
**Grey area:** Which categories to add. Too few misses the point; too many dilutes extraction precision.
**Decision:** Add these 5 production-standard, physically-on-screen categories to the existing {character, location, prop, wardrobe, vehicle}:
1. **set_dressing** — furniture/décor that dresses a location but isn't handled as a prop (couch, paintings, rugs). Distinct from `prop` (handled/featured) and `location` (the place itself).
2. **animal** — animals appearing on screen (dogs, horses-as-animals, birds). (A horse ridden is also a vehicle-of-sorts, but as a living creature it's an animal; the prompt will guide precedence — animals are animals.)
3. **sfx** — practical/special effects that physically occur on screen (fire, smoke, rain, explosions, breaking glass). Production-relevant because they need an effects department. Still on-screen/visible (not abstract).
4. **makeup_hair** — notable makeup/hair/prosthetics that are a production element (wounds, aging, distinctive hairstyles, prosthetic appliances). On-screen and department-relevant.
5. **extras** — background performers / crowd (a crowd, restaurant patrons, soldiers in the background) as a production-staffing element. Visible on screen.
**Rationale:** these are the highest-value standard AD/production-breakdown categories beyond the base 5, each PHYSICALLY visible on screen (consistent with the existing "physically present" rule), and each maps to a real production department. Deferred (not added, to avoid dilution): stunts, greenery/plants, music cues (not visible), weapons-as-own-category (covered by prop). The final set is Claude's Discretion per the ROADMAP ("exact final list settled during phase discussion") — recorded here for review.
**snake_case values:** new multi-word categories use snake_case (`set_dressing`, `makeup_hair`) to match the existing single-word lowercase value convention and the String column; frontend labels are Title Case ("Set Dressing", "Makeup & Hair").

### D-52-02 — Additive everywhere, no data loss, no migration (DECIDED)
**Decision:** Add the 5 values to the enum, the schema regex pattern, the system-prompt CATEGORIES list (with a one-line on-screen description each + dedup/precedence guidance), the FE constant, and the FE type union. Do NOT remove or rename any existing category. The String(50) column already stores arbitrary values, so existing rows are untouched and no migration is needed (CATG-02). The schema regex MUST be extended to accept the new values (else POST/extract of a new-category element 422s).

### D-52-03 — UI picks up new categories automatically; verify (DECIDED)
**Decision:** Because `CategoryTabs` iterates `BREAKDOWN_CATEGORIES`, adding the constant entries auto-renders the new tabs with counts and filtering (CATG-03). No CategoryTabs code change required — but VERIFY the tabs render and the count/filter query works for a new category (the GET /elements/{project_id}?category= filter already accepts a string). If the tab strip overflows with 10 tabs, a minor responsive tweak (wrap/scroll) is acceptable but optional — do not over-engineer.

### D-52-04 — Preserve extraction discipline (DECIDED)
**Decision:** The EXTRACTION_SYSTEM_PROMPT's CRITICAL RULES (physically present on screen; no dialogue-only mentions; no abstractions) are preserved verbatim. New categories get on-screen-only descriptions consistent with those rules (e.g. sfx = effects that physically occur on screen, NOT implied/off-screen). The dedup/precedence note gains brief guidance for ambiguous cases (animal vs vehicle for a ridden horse → animal; set_dressing vs prop → handled/featured = prop, else set_dressing). Single AI call, structured output model, phases 50/51 behavior all unchanged.
</decisions>

<code_context>
## Existing Code Insights (verified)
- `BreakdownCategory(str, enum.Enum)` database.py:138-143 — add 5 members.
- `category = Column(String(50))` database.py:548 — free string; no migration needed.
- EXTRACTION_SYSTEM_PROMPT CATEGORIES list breakdown_service.py:101-106 — add 5 lines + precedence guidance.
- `BreakdownElementCreate.category` regex schemas.py:698 `pattern="^(character|location|prop|wardrobe|vehicle)$"` — MUST extend to include new values (the gating regex).
- `BREAKDOWN_CATEGORIES` constants.ts:278-284 — add 5 {value,label}.
- `BreakdownCategory` union types/index.ts:269 — add 5 string literals.
- `CategoryTabs.tsx` iterates the constant (20,38) — auto-renders; verify only.
- GET /elements filter accepts `category` string (breakdown.py) — works for new values.
- Tests: test_breakdown_service.py / test_breakdown_api.py. Add: an extracted element with a new category (e.g. set_dressing) persists and is returned; the schema accepts the new category (no 422); existing categories still work. Keep all green.

## Pre-existing test-isolation concern: see v6.0-PREEXISTING-TEST-CONCERN.md (not breakdown).
</code_context>

<specifics>
## Specific Ideas
- Single plan, mostly mechanical: 5 definition sites (3 backend, 2 frontend) + prompt guidance + tests + FE build.
- Tests: schema accepts a new category (BreakdownElementCreate with category="set_dressing" validates); an AI extraction returning a new-category element persists with that category and is returned by GET; existing 5 categories unaffected. Keep test_breakdown_service.py + test_breakdown_api.py + test_staleness.py green.
- Frontend: `npm run build` (tsc) clean with the new type-union members + constant; CategoryTabs renders 10 tabs (verify, no code change expected).
- No migration, no new dependency.

## Verification framing
- CATG-01: taxonomy broadened (enum + prompt + regex + FE) — assert the new values are present in all gating sites.
- CATG-02: additive, existing data valid — assert existing-category rows/tests still pass; no migration file added; String column unchanged.
- CATG-03: UI displays + filters new categories — CategoryTabs iterates the constant; verify a new tab renders and its filter query returns its elements.
</specifics>

<deferred>
## Deferred Ideas
- Per-category icons/colors in the UI.
- Further categories (stunts, greenery, weapons-as-own) — start with +5; expand later if needed.
- A DB-level enum/CHECK constraint on category (currently free String; out of scope, would need a migration).
- Responsive tab overflow polish beyond a minimal wrap/scroll.
</deferred>
