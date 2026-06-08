---
phase: 54-direct-screenplay-writing
plan: 01
subsystem: screenplay-editor
tags: [screenplay, phase-data, breakdown, frontend, backend, upsert]
requires:
  - "PATCH /phase-data/{project}/{phase}/{subsection_key} (existing generic handler)"
  - "wizards.py fetch-or-create + ScreenplayContent creation pattern"
  - "breakdown_service._build_extraction_context (reads ScreenplayContent rows)"
provides:
  - "Upserting PATCH handler (no 404 from empty project)"
  - "Screenplay-scoped ScreenplayContent reconcile (delete-then-recreate, idempotent)"
  - "Writable ScreenplayEditorView empty state (Start writing affordance)"
  - "Pure splitByHeadings() zero-originals scene splitter"
affects:
  - backend/app/api/endpoints/phase_data.py
  - frontend/src/components/Patterns/ScreenplayEditorView.tsx
tech-stack:
  added: []
  patterns:
    - "Fetch-or-create upsert on PATCH (mirrors wizards.py)"
    - "Delete-then-recreate idempotent reconcile scoped by guard"
    - "Pure top-level text splitter (unit-testable, no React deps)"
key-files:
  created: []
  modified:
    - backend/app/api/endpoints/phase_data.py
    - backend/app/tests/test_api.py
    - frontend/src/components/Patterns/ScreenplayEditorView.tsx
decisions:
  - "D-54-01: PATCH is now a generic upsert (fetch-or-create) for all subsections"
  - "D-54-05 (option b): ScreenplayContent sync lives in a guarded branch inside the generic PATCH; no new endpoint, no frontend client change"
  - "D-54-05 reconcile: delete-then-recreate scoped to project_id, idempotent"
  - "D-54-03: heading split strips the slugline from content (buildDocument re-prepends title)"
metrics:
  duration: ~4m
  completed: 2026-06-08
requirements: [WRITE-01, WRITE-02, WRITE-03, WRITE-04]
---

# Phase 54 Plan 01: Direct Screenplay Writing Summary

Made the Screenplay Editor writable from an empty project and persist hand-written screenplays exactly like generated ones: the PATCH handler now upserts the `screenplay_editor` PhaseData (no 404), idempotently reconciles `ScreenplayContent` rows from the saved screenplays (so breakdown extraction sees the hand-written scenes), the editor offers a "Start writing" affordance instead of a wizard-only dead-end, and a pure `splitByHeadings` splitter turns from-scratch text into INT./EXT. scenes (or one "Untitled" scene).

## What Was Built

### Task 1 — Upsert PATCH + screenplay-scoped ScreenplayContent reconcile (backend)
`backend/app/api/endpoints/phase_data.py` `update_subsection_data`:
- Replaced the `if not data: raise HTTPException(404)` branch with fetch-or-create (mirrors `wizards.py:261-269`). The upsert is generic and safe for every subsection (D-54-01).
- Added a guarded branch `if phase == "write" and subsection_key == "screenplay_editor":` that, when `screenplays` is non-empty, deletes this project's existing `ScreenplayContent` rows and recreates one per screenplay (`content=sp["content"]`, `formatted_content=sp` so `episode_index` is preserved for v7.0 scene-scoped alignment). Delete-then-recreate keeps repeated saves idempotent (D-54-05).
- Staleness is unchanged: the existing `phase in BREAKDOWN/SHOTLIST_SENSITIVE_PHASES` calls already fire for `phase=="write"`, so no duplicate staleness calls inside the branch. Single `db.commit()` + `db.refresh(data)` preserved. Generic subsections never create `ScreenplayContent`.

### Task 2 — Backend tests
`backend/app/tests/test_api.py` `TestScreenplayWriteSave` (6 DB-backed tests, all asserting real rows/flags via the shared `db_session`):
- `test_screenplay_save_upserts_when_absent` — empty project save returns 200 (not 404) and persists 2 scenes.
- `test_screenplay_save_creates_screenplaycontent_rows` — row count == #scenes; each row's `formatted_content` carries the matching `episode_index`/`title`.
- `test_screenplay_save_is_idempotent` — second identical save leaves 2 rows, not 4.
- `test_screenplay_save_marks_breakdown_stale` — with a `BreakdownElement` present, `breakdown_stale` flips True.
- `test_saved_screenplay_feeds_breakdown_alignment` (W3) — `_build_extraction_context` returns both scenes' text (`len(screenplay_texts)==2`, both bodies present).
- `test_generic_subsection_save_creates_no_screenplaycontent` — a `story/some_key` PATCH (even carrying a `screenplays` key) creates zero `ScreenplayContent` rows.

### Task 3 — Writable empty state + heading splitter (frontend)
`frontend/src/components/Patterns/ScreenplayEditorView.tsx`:
- Added pure top-level `splitByHeadings(text)`: slugline regex `/^\s*(INT\.?\/?EXT\.?|EXT\.?\/?INT\.?|INT\.?|EXT\.?|I\/E|E\/I)[\s.]/i`; each heading starts a scene with `title`=slugline and `content`=body-after-slugline (slugline + one following blank line stripped so `buildDocument` does not double-render it). No heading → one `{title:"Untitled", content:<all>, episode_index:0}`; empty → `[]`; never `[]` for non-empty text. Sequential `episode_index`.
- Wired `splitToScreenplays` zero-originals path: `if (originals.length === 0) return splitByHeadings(text);` (was `return [];`). The title-anchor path for ≥1 originals is unchanged, so save→reload→edit→save round-trips through the existing anchor (title=slugline anchors stably, no dup/loss/compounding).
- Replaced the wizard-only dead-end: when `screenplays.length === 0 && !isEditing`, show a "Start writing" button that enters edit mode with a blank buffer; when editing, fall through to the existing edit textarea/toolbar/saveMutation. Added the `INT. LOCATION - DAY\n\nAction…` placeholder. `startEditing` seeds an empty buffer when there are no scenes.

## Verification Results

| Gate | Command | Result |
|------|---------|--------|
| Backend suites | `pytest test_api.py test_breakdown_service.py test_staleness.py test_wizard_injection.py -q` | **50 passed** |
| Frontend build | `npm run build` (tsc && vite build) | **clean** (pre-existing chunk-size warning only) |
| Source: 404 gone | `grep 'Phase data not found' phase_data.py` | only the GET helper at :185 (expected) |
| Source: sync guard | `grep 'screenplay_editor' phase_data.py` | guard at :237 |
| Source: splitter wired | `grep 'splitByHeadings' ScreenplayEditorView.tsx` | def at :53, wired at :99 |

## Deviations from Plan

**1. [Rule 1 - Bug] BreakdownElement column name in the staleness test**
- **Found during:** Task 2 (first test run)
- **Issue:** The plan's behavior text referenced `canonical_name` for `BreakdownElement`; the actual model column is `name` (`database.py:554`), so the test raised `TypeError: 'canonical_name' is an invalid keyword argument`.
- **Fix:** Used `name="Sword"` when constructing the test `BreakdownElement`.
- **Files modified:** `backend/app/tests/test_api.py`
- **Commit:** bf5d69d

No other deviations — backend handler and frontend changes followed the plan exactly, including all five baked-in constraints (upsert, scoped delete-then-recreate sync, writable empty state, heading splitter, round-trip stability).

## Threat Flags

None. The reconcile is scoped to the verified-owned project's `project_id`; the generic PATCH stays generic (test-enforced); no new endpoint, contract, dependency, or migration.

## Known Stubs

None. The empty state is fully wired (Start writing → edit → save → ScreenplayContent rows → breakdown).

## Self-Check: PASSED

- FOUND: backend/app/api/endpoints/phase_data.py (modified)
- FOUND: backend/app/tests/test_api.py (modified)
- FOUND: frontend/src/components/Patterns/ScreenplayEditorView.tsx (modified)
- FOUND commit 2ff66f0 (Task 1)
- FOUND commit bf5d69d (Task 2)
- FOUND commit 0f49a10 (Task 3)
