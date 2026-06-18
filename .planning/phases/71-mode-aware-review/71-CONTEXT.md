---
phase: 71-mode-aware-review
created: 2026-06-18
requirements: [SREV-01]
source: autonomous (ROADMAP scope + codebase research; no interactive discuss-phase)
---

# Phase 71 Context — Mode-Aware Review

## Scope (from ROADMAP, locked)

- **In:** In `connected` shows, episode review *additionally* considers character/plot
  coherence against prior-episode summaries (Phase 69 output, ordered by `episode_number`).
- **Out:** Automatic continuity-inconsistency detection ("character X dies in ep2 but
  appears in ep4"). That is explicitly deferred beyond this milestone.
- **Unchanged:** Anthology and standalone review keep current standalone-quality scope —
  no cross-episode checks.

## Locked decisions

- **D1 — Seam is the agent review middleware, not a new endpoint.** Episode review happens
  via `agent_review_middleware.review_step_output` after `script_writer_wizard` generation.
  Phase 71 threads connected-mode prior-episode context into that existing review. No new
  review endpoint, no schema migration, no new service.

- **D2 — Reuse Phase 68/69 building blocks.** Use `_build_prior_episodes_block` for the
  coherence reference and the existing `regenerate_stale_priors` pre-pass for freshness.
  Do not duplicate ordering/staleness logic. Order ONLY by `episode_number`.

- **D3 — Enrichment, not forcing (resolved assumption).** Connected-mode continuity context
  *enriches an existing* agent review. It does NOT force a review when the user has zero
  review agents mapped — zero-agent pass-through (REVW-04) is preserved in all modes. This
  is the conservative, in-scope reading of "review additionally considers"; forcing reviews
  would exceed the deliberately-light scope.

- **D4 — Bounded prompt instruction.** The injected instruction asks the reviewer to flag
  character/plot *coherence considerations* against the prior summaries. It must explicitly
  NOT ask for exhaustive inconsistency auditing of prior episodes (keeps D-out honored).

- **D5 — Mode gating by construction.** Anthology/standalone pass no continuity context
  (`None`), so their review path and prompt are byte-identical to today. Success criterion
  #2 is satisfied structurally, not by an extra check.

## Success criteria (must be TRUE)

1. In a `connected` show, `script_writer_wizard` review surfaces continuity considerations
   checked against the prior-episode summaries (character/plot coherence).
2. In `anthology` and `standalone` modes, review performs no cross-episode continuity
   checks (current behavior preserved exactly).

## Requirement traceability

- **SREV-01** — connected-mode episode review considers coherence against prior-episode
  summaries. Covered by D1–D5.
