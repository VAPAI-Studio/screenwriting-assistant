---
phase: 71-mode-aware-review
created: 2026-06-18
requirements: [SREV-01]
---

# Phase 71 Research — Mode-Aware Review

## Goal restated

In a `connected` show, episode review should *additionally* consider character/plot
coherence against the **prior-episode summaries** (Phase 69 output). Anthology and
standalone shows keep their current review scope (no cross-episode checks). This is a
deliberately LIGHT phase — NOT the deferred automatic continuity-inconsistency
detection engine.

## Where episode review actually happens (the seam)

The real episode-production-and-review flow is the **wizard path**, not the MVP
section-review endpoint:

- `script_writer_wizard` generates screenplays (`backend/app/api/endpoints/wizards.py`,
  `_run_wizard_background` → result applied at `apply_wizard_results`, screenplays stored
  in `ScreenplayContent` + `PhaseData`).
- After generation, wizard output is reviewed by the **agent review middleware**:
  `agent_review_middleware.review_step_output(...)` at `wizards.py:91`.
- `AgentReviewMiddleware.review_step_output` (`backend/app/services/agent_review_middleware.py:79`)
  looks up user-mapped review agents, fans out reviews (REVW-02), and AI-merges them
  (REVW-03), with graceful fallback to raw output when there are no agents or the merge
  fails (REVW-04).

**Key finding:** the review middleware currently receives NO prior-episode / continuity
context. The merge prompt (`MERGE_SYSTEM_PROMPT`, middleware ~line 44) is mode-agnostic.
This is the insertion point for SREV-01.

The MVP section-review path (`/api/review` → `openai_service.review_section`,
`review.py` / `openai_service.py`) is the three-act section reviewer and is NOT the
episode-level review this phase targets. Leave it untouched.

## Reusable building blocks (do NOT rebuild)

- **Prior-episode block builder:** `_build_prior_episodes_block(db, show, project)` in
  `backend/app/utils/bible_context.py:33`. Already:
  - filters strictly-prior episodes (`episode_number < current`),
  - drops null/whitespace summaries,
  - orders by `Project.episode_number.asc()` (the reliable integer key — NEVER positional;
    `ScreenplayContent` has no reliable order, join by `episode_index` only — bit twice
    historically),
  - caps to most-recent 8 (`PRIOR_EPISODE_CAP = 8`),
  - tags stale summaries with `STALE_SUMMARY_MARKER`.
  This is the exact coherence reference the review needs. `build_bible_context` already
  branches on `show.continuity_mode == ContinuityMode.CONNECTED.value` (line 86) and calls
  this builder only in connected mode.

- **Stale-summary lazy regen:** `regenerate_stale_priors(db, show, project)` in
  `backend/app/utils/episode_summary.py:37`, already run as a connected-mode pre-pass in
  `wizards.py:143` BEFORE `build_bible_context`. So by the time review runs in the same
  request, prior summaries are already fresh — no new staleness handling needed.

- **Mode enum:** `ContinuityMode` (`backend/app/models/schemas.py`); `Show.continuity_mode`
  and `Project.episode_summary` columns (`database.py`).

## Recommended approach (lightest seam)

Make the agent review middleware **mode-aware for `script_writer_wizard` only**:

1. In the connected-mode branch of the wizard request (`wizards.py`, where
   `regenerate_stale_priors` + `build_bible_context` already run), build the prior-episode
   coherence block (reuse `_build_prior_episodes_block`, or extract the already-built
   connected portion) and pass it into `review_step_output` as a new optional
   `continuity_context: Optional[str] = None` parameter.
2. In `review_step_output` / `_merge_reviews`, when `continuity_context` is present,
   inject it into the merge/review prompt with an instruction to additionally check
   character & plot coherence against these prior-episode summaries — explicitly bounded:
   "flag coherence considerations; do NOT attempt exhaustive inconsistency detection."
3. Anthology/standalone → `continuity_context` stays `None` → behavior identical to today
   (the zero-context path), satisfying success criterion #2 by construction.

This keeps the change additive: a new optional parameter threaded from one connected-mode
call site, plus one conditional prompt block. No new endpoint, no schema migration, no
new engine.

## Pitfalls

- **Ordering:** only ever order prior episodes by `episode_number`; never positional /
  `created_at` for the *episode sequence*. (`created_at` is only a newest-wins tiebreaker
  inside `_read_episode_text_by_index`.)
- **Scope creep:** resist building diff/inconsistency detection. The prompt must ask for
  *coherence considerations*, not a correctness audit of prior episodes.
- **Don't regress zero-agent pass-through (REVW-04):** if the user has no review agents
  mapped, connected mode must still pass through unchanged — continuity context only
  enriches an existing review, it must not force a review where none was configured.
  (Decision point for planner: confirm whether SREV-01 requires continuity review even
  with zero mapped agents, or only enriches existing agent review. ROADMAP says review
  "additionally considers" coherence → enrichment of existing review is the conservative,
  in-scope reading.)
- **Async/session safety:** the middleware already uses a `session_factory` and dedicated
  sessions; build the continuity block in the request session before fan-out, pass it as a
  plain string (same pattern as `bible_context` being passed as a string to the background
  task).

## Test surface

- `test_yolo_integration.py`, `test_session_isolation.py`, `test_mcp_foundation.py` are
  PRE-EXISTING failures unrelated to this phase (phases 04/08/55) — do not be alarmed.
- New tests should cover: (a) connected mode threads continuity context into the merge
  prompt; (b) anthology/standalone pass `None` and the prompt has no continuity block;
  (c) zero-agent pass-through still holds in connected mode.
