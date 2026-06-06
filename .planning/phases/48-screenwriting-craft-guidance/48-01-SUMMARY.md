---
phase: 48-screenwriting-craft-guidance
plan: 01
subsystem: api
tags: [openai, prompt-engineering, screenwriting, fastapi, pytest]

# Dependency graph
requires:
  - phase: 45-continuity-aware-generation
    provides: the per-scene continuity block (Story so far / Previous scene) the craft block composes with
  - phase: 46-screenplay-layout
    provides: the strict industry-standard layout-rules tail the craft block sits beside (distinct concern)
  - phase: 47-character-voice-injection
    provides: the conditional character/voice block + the asserted-anchor comment convention the craft block mirrors
provides:
  - "Unconditional '## Screenwriting Craft' section in the _generate_scripts per-scene prompt naming all four CRAFT-01 dimensions"
  - "Stable test-asserted craft anchors: on-the-nose (subtext), economical (action economy), show, don't tell + no internal or unfilmable description, white space (pacing)"
  - "test_craft_guidance.py — 6 tests pinning craft coverage, SC#4 composition, always-on no-regression, and a production-source assertion"
affects: [49-eval, screenwriting-craft, script-generation-prompt]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Unconditional labeled instruction block: a plain f-string literal (no if/else guard) added equally to both character paths so the byte-identical empty-vs-absent contract holds"
    - "Asserted-anchor + collision-guard comment beside the prompt block (mirrors the Phase 47 voice convention)"

key-files:
  created:
    - backend/app/tests/test_craft_guidance.py
  modified:
    - backend/app/services/template_ai_service.py

key-decisions:
  - "D-48-01: a distinct '## Screenwriting Craft' section rather than more layout bullets — coverage is auditable per-dimension"
  - "D-48-02: all four dimensions named with stable anchor substrings (on-the-nose, economical, show don't tell + no internal or unfilmable description, white space)"
  - "D-48-03: concise static block (~731 chars), fixed bounded cost; SC#4 bloat guard len(prompt) < 20000"
  - "D-48-04: additive + unconditional; lines 394-462 (TITLE parser, return contract, continuity advance, except branch) untouched"

patterns-established:
  - "Unconditional craft block: same literal text on the empty- and with-characters paths keeps Phase 47 byte-identical contract valid"
  - "Collision-guard comment documents the strings the craft text must NOT contain (Story so far / Previous scene / distinct, consistent voice / ## Characters / ## Character Voice)"

requirements-completed: [CRAFT-01, CRAFT-02, CRAFT-03]

# Metrics
duration: ~15min
completed: 2026-06-06
---

# Phase 48 Plan 01: Screenwriting Craft Guidance Summary

**Unconditional `## Screenwriting Craft` prompt section in `_generate_scripts` naming subtext, action economy, show-don't-tell, and white-space pacing — composing additively with the Phase 45 continuity and Phase 47 voice blocks under a length bound.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-06T12:02Z
- **Completed:** 2026-06-06T12:17Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added a distinct, UNCONDITIONAL `## Screenwriting Craft` block to the per-scene script-writing prompt, naming all four CRAFT-01 dimensions with stable, test-asserted anchors.
- Wired the CRAFT-02 levers (`economical`, `no internal or unfilmable description`) and the CRAFT-03 subtext lever (`on-the-nose`) as concrete, model-actionable phrasing.
- Verified the craft block composes with the Phase 45 continuity block and Phase 47 voice block in a later-scene prompt without colliding with any asserted-absent marker — all 21 prior tests stay green.
- New test module (6 tests) including a production-source assertion that pins the prompt independent of mock routing.

## Task Commits

Each task was committed atomically (TDD RED -> GREEN -> guard):

1. **Task 1: Write failing craft-guidance test module** - `6a1e12a` (test, RED)
2. **Task 2: Add the unconditional `## Screenwriting Craft` block** - `f68ebda` (feat, GREEN)
3. **Task 3: Regression-guard prior suites + source assertion** - `036f729` (test)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified
- `backend/app/services/template_ai_service.py` - Added the unconditional `## Screenwriting Craft` literal block (after the custom-guidance line, before the layout bullets) plus an anchor + collision-guard comment above the prompt f-string. Lines 394-462 untouched.
- `backend/app/tests/test_craft_guidance.py` - New: 6 tests (CRAFT-01 four-dimension coverage, CRAFT-02 levers, CRAFT-03 subtext, SC#4 composition + bloat guard, always-on no-regression, production-source assertion).

## Decisions Made
None beyond the locked D-48-01..D-48-04 — plan followed as specified. Block placed just before the layout bullets (the recommended placement), keeping layout and craft as distinct concerns.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- A one-off ad-hoc verification snippet used a fragile string split that produced a false-positive collision report. Re-ran the check anchored on the exact craft literal (block length 731 chars) — collision guard confirmed clean. No production change; the 6 tests (including the SC#4 composition and source assertion) already prove non-collision.

## Verification Results
- `pytest app/tests/test_craft_guidance.py -x -q` -> **6 passed** (was 5 RED before Task 2; +1 source-assertion test in Task 3).
- `pytest test_continuity_generation.py test_character_voice_injection.py test_wizard_injection.py -q` -> **21 passed** (continuity 10, voice 8, wizard 3 — zero regression).
- Combined craft + trio -> **27 passed** in isolation (no order dependence).
- Source proof: `inspect.getsource(_generate_scripts)` contains `## Screenwriting Craft` and all four dimension anchors -> **OK**.

## User Setup Required
None - no external service configuration required. No migration, no frontend change, no new dependency.

## Next Phase Readiness
- Craft guidance is in the generation prompt and auditable. Ready for Phase 49 EVAL-01 (side-by-side compare) which judges whether output reflects the guidance.
- No blockers. The pre-existing yolo/session-isolation test-ordering concern (v6.0-PREEXISTING-TEST-CONCERN.md) was not touched and remains out of scope.

## Self-Check: PASSED

---
*Phase: 48-screenwriting-craft-guidance*
*Completed: 2026-06-06*
