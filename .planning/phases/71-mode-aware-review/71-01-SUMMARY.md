---
phase: 71-mode-aware-review
plan: 01
subsection: mode-aware-review
tags: [continuity, agent-review, connected-mode, script-writer-wizard]
requires:
  - "agent_review_middleware.review_step_output (Phase 5)"
  - "_build_prior_episodes_block (Phase 68)"
  - "regenerate_stale_priors (Phase 68)"
provides:
  - "continuity_context parameter threaded review_step_output -> _merge_reviews -> merge prompt"
  - "connected-mode + script_writer_wizard call site that builds prior-episode coherence block"
  - "bounded coherence merge-prompt instruction (CONTINUITY_MERGE_BLOCK)"
affects:
  - "backend/app/services/agent_review_middleware.py"
  - "backend/app/api/endpoints/wizards.py"
tech-stack:
  added: []
  patterns:
    - "plain-string hand-off across request->background boundary (mirror bible_context)"
    - "additive optional kwarg, byte-identical default path (D5)"
key-files:
  created:
    - ".planning/phases/71-mode-aware-review/71-01-SUMMARY.md"
  modified:
    - "backend/app/services/agent_review_middleware.py"
    - "backend/app/api/endpoints/wizards.py"
    - "backend/app/tests/test_agent_review_middleware.py"
decisions:
  - "Continuity context enriches an existing review (D3) — never forces one; REVW-04 zero-agent pass-through preserved."
  - "Bounded merge instruction flags coherence considerations only and explicitly forbids exhaustive inconsistency auditing (D4)."
  - "Mode gating by construction (D5) — anthology/standalone/non-script_writer/zero-agent paths pass None, leaving the merge prompt byte-identical to today."
metrics:
  duration: "~15m"
  completed: 2026-06-18
  tasks: 2
  files_modified: 3
requirements: [SREV-01]
---

# Phase 71 Plan 01: Mode-Aware Review Summary

Connected-mode `script_writer_wizard` episode review now threads the existing Phase 68 prior-episode summary block into the agent-review merge step as an optional `continuity_context`, injecting a bounded character/plot coherence instruction into the merge prompt only when present; anthology, standalone, non-script-writer, and zero-agent paths stay byte-identical to today.

## What Was Built

### Task 1 — Middleware threading + bounded merge block (TDD)
- Added `continuity_context: Optional[str] = None` as the final parameter of both `AgentReviewMiddleware.review_step_output` and `_merge_reviews`; `review_step_output` forwards it to the `_merge_reviews(...)` call.
- Added module-level `CONTINUITY_MERGE_BLOCK` template — a single appended segment containing the prior-episode reference text plus a bounded instruction that asks the merger to flag character/plot **coherence considerations** and explicitly forbids an exhaustive inconsistency audit / correctness review of prior episodes (D4).
- `_merge_reviews` appends the block to the system prompt **only** when `continuity_context` is a non-whitespace string. When `None`/blank the system prompt is identical to the pre-Phase-71 output (D5). Temperature, `json_mode`, schema validation, and the user message are untouched.
- The zero-agent / no-successful-reviews early returns were left unchanged — REVW-04 pass-through is preserved regardless of `continuity_context` (D3).

### Task 2 — Connected-mode call site in wizards.py
- Imported `_build_prior_episodes_block` from `...utils.bible_context`.
- In `run_wizard`, after the existing connected pre-pass (`regenerate_stale_priors`), the prior-episode block is built **only** when the project's show is in `connected` mode AND `request.wizard_type == "script_writer_wizard"`. The `show` already fetched by the pre-pass is reused (no re-query). The result is captured as a plain string (or `None`) in the request session.
- Added `continuity_context: str = None` to `_run_wizard_background`, passed it via `background_tasks.add_task(...)`, and forwarded it into `review_step_output(...)` as `continuity_context=continuity_context` — mirroring the existing `bible_context: str = None` plain-string hand-off. No ORM object or live session crosses the background boundary (T-71-01).
- All other modes/wizards (anthology, standalone, `show_id` NULL, non-script-writer wizards) leave `continuity_context` as `None`, so review is called identically to today (D5).

## Tests

Added to `backend/app/tests/test_agent_review_middleware.py` (3 new, mirroring existing fixtures/mock patterns):
- `test_connected_threads_continuity_into_merge_prompt` — asserts the merge system message contains the prior-episode text, a coherence token, and a token forbidding exhaustive/inconsistency auditing.
- `test_no_continuity_context_merge_prompt_clean` — asserts the merge system message contains no continuity/coherence tokens when `continuity_context` is omitted.
- `test_zero_agents_passthrough_with_continuity` — asserts REVW-04 pass-through (raw output, `review_applied=False`, `chat_completion` never called) is preserved with `continuity_context` set.

Result: `pytest app/tests/test_agent_review_middleware.py` → **13 passed** (10 pre-existing + 3 new). Adjacent surface (`test_wizard_injection.py`, `test_bible_injection.py`, `test_continuity_generation.py`) → 35 passed. `python -c "import app.api.endpoints.wizards"` imports cleanly.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface

No new network endpoints, auth paths, or schema changes introduced. `continuity_context` crosses the request→background boundary as a plain string (T-71-01 mitigated); prior-episode block reuses `_build_prior_episodes_block`'s `PRIOR_EPISODE_CAP=8` bound (T-71-02 mitigated); no new dependencies installed (T-71-SC). Scope creep into inconsistency-detection (T-71-03) is held off by the bounded D4 instruction.

## TDD Gate Compliance

- RED: `test(71-01): add failing tests for continuity_context threading` (`f6a9274`) — 2 of 3 new tests failed before implementation as expected.
- GREEN: `feat(71-01): thread continuity_context into merge prompt` (`346fa23`) — all 13 tests pass.
- REFACTOR: none required.

## Commits

- `f6a9274` test(71-01): add failing tests for continuity_context threading
- `346fa23` feat(71-01): thread continuity_context into merge prompt
- `9bcd7a6` feat(71-01): wire connected-mode prior-episode block into wizard review

## Self-Check: PASSED

All modified files and all three task commits verified present.
