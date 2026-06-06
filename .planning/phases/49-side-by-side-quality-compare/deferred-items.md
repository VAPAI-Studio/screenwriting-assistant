# Deferred Items — Phase 49

## Pre-existing test failures (out of scope, NOT caused by 49-01)

The following suites fail under the full-suite run AND in isolation, and were
confirmed failing at the plan baseline commit `f38a254` (before any 49-01 work):

- `app/tests/test_session_isolation.py::test_orchestrate_uses_session_factory`
- `app/tests/test_yolo_integration.py::test_yolo_wizard_routes_through_middleware`
- `app/tests/test_yolo_integration.py::test_yolo_wizard_zero_agents_passthrough`
- `app/tests/test_yolo_integration.py::test_yolo_full_run_llm_call_count`

These are the documented order-sensitive yolo/session-isolation suites
(`.planning/v6.0-PREEXISTING-TEST-CONCERN.md`). They are explicitly out of scope
for this phase. The 49-01 target suites (`test_scene_compare.py`) and the 27-test
regression trio (continuity/voice/craft/wizard) all pass.

## Frontend lint script references a non-existent ESLint config (out of scope, NOT caused by 49-02)

`frontend/package.json` defines `"lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"`,
but **no ESLint configuration file exists anywhere in the repo** (`.eslintrc*`,
`eslint.config.js`, and a `package.json` `eslintConfig` key are all absent — and git
history shows one has never existed). Running `npm run lint` therefore fails
unconditionally with:

```
ESLint couldn't find a configuration file.
```

This failure is independent of source content — it fails identically on a clean tree
and is **not** caused by the 49-02 changes. Standing up an ESLint config is a tooling
decision outside the scope of phase 49 (it would surface pre-existing violations across
the entire `frontend/src` tree). The binding type-safety gate for 49-02 is therefore
`npm run build` (`tsc && vite build`), which passes with zero type errors. The lint-config
gap should be resolved in a dedicated tooling task before the lint gate can be enforced.

## ScreenplayContent duplicate-row disambiguation is best-effort, not bulletproof (WR-01 follow-up)

Code review finding WR-01 was fixed: `keep-scene-version` now orders candidate
`ScreenplayContent` rows NEWEST-first (`created_at.desc(), id.desc()`) so a kept
version aligns with the latest generation the breakdown/shotlist services read,
rather than a stale earlier duplicate (the batch-generate path appends rows and
never deletes, so re-generated projects accumulate duplicates per `episode_index`).

**Known limitation (in-scope acceptance):** on **Postgres** (production) `func.now()`
is sub-second, so newest-first reliably picks the most recent row. On **SQLite**
(test harness) `func.now()` is only second-resolution and the PK is a random UUID
(no autoincrement), so two rows created in the same second cannot be ordered
deterministically by the schema alone — the regression test
(`test_keep_scene_version_updates_newest_duplicate_row`) sets explicit `created_at`
values to exercise the ordering deterministically. A fully robust fix (an
autoincrement sequence or higher-resolution insertion-order column, or making
`ScreenplayContent` a pure projection of `content["screenplays"]` so duplicates
never accumulate) requires a schema change and is therefore **deferred** per D-49-03
(no migration this phase). Acceptable for the internal-tool MVP; revisit if the
duplicate-row accumulation causes breakdown/shotlist drift in practice.
