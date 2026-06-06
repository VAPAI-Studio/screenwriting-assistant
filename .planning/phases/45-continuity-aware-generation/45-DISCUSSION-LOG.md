# Phase 45: Continuity-Aware Generation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 45-continuity-aware-generation
**Areas discussed:** Context mix, Synopsis generation, Continuity representation, Sequencing, Token bounding, Persistence, Synopsis home, Reuse policy

---

## Context mix (how much prior-scene context per prompt)

| Option | Description | Selected |
|--------|-------------|----------|
| Synopsis + last scene full text | Running synopsis for earlier scenes + full verbatim text of immediately preceding scene. Bounds tokens, strong local continuity. | ✓ |
| Synopsis + last N scenes full | Synopsis + full text of last 2–3 scenes. More local context, higher token cost. | |
| Synopsis only | Synopsis only, no verbatim prior text. Cheapest, weaker tone carry-over. | |

**User's choice:** Synopsis + last scene full text
**Notes:** Balances CONT-01 (real prior text) with CONT-02 (token-bounded synopsis).

---

## Synopsis generation (how the "story so far" is produced)

| Option | Description | Selected |
|--------|-------------|----------|
| Separate AI summarization call | Small AI call after each scene updates cumulative synopsis. Best fidelity, one extra cheap call/scene. | ✓ |
| Reuse scene-plan summary fields | Concatenate existing planner fields (summary, fallout, push_forward). Zero extra calls, reflects plan not actual text. | |
| Append generated scene summaries | Keep short summary per generated scene and append. Cheaper, coarser. | |

**User's choice:** Separate AI summarization call
**Notes:** Mirror existing scene-planner summarization pattern; use `chat_completion` for provider abstraction.

---

## Continuity representation (structured vs prose)

| Option | Description | Selected |
|--------|-------------|----------|
| Prose "story so far" only | Flowing narrative synopsis; model reasons over prose well; satisfies CONT-03 via carried facts. | ✓ |
| Structured continuity ledger | Explicit object/fact/character-state checklist alongside prose. Stronger but more complex. | |

**User's choice:** Prose "story so far" only
**Notes:** Ledger deferred — avoid over-engineering for v6.0.

---

## Sequencing (loop + standalone path)

| Option | Description | Selected |
|--------|-------------|----------|
| Strict sequential, skip when no prior | Keep in-order loop; no continuity context for first/single scene → existing behavior unchanged. | ✓ |
| Sequential + tolerate gaps | Fall back to plan summary if a prior scene failed, so chain doesn't break. | |

**User's choice:** Strict sequential, skip when no prior
**Notes:** Directly satisfies success criterion 4 (single-scene/non-sequential unchanged). Failed-prior-scene handling flagged to planner.

---

## Token bounding (keeping synopsis within limits)

| Option | Description | Selected |
|--------|-------------|----------|
| Re-summarize to a cap | Summarization call regenerates whole synopsis under a fixed length (~300–500 words). Naturally bounded. | ✓ |
| Fixed char/token truncation | Append + hard-truncate. Simple but can cut mid-fact. | |
| Don't worry about it yet | Assume scripts short enough; revisit if problem. | |

**User's choice:** Re-summarize to a cap

---

## Persistence (synopsis saved vs in-memory)

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory during the run | Build/update in loop, discard after. No schema change. | |
| Persist to DB | Store synopsis so it survives runs. | ✓ |

**User's choice:** Persist to DB
**Notes:** Combined with "Synopsis home" below to avoid a migration.

---

## Synopsis home (where in the DB)

| Option | Description | Selected |
|--------|-------------|----------|
| PhaseData row (JSON content) | Store in existing screenplay_editor PhaseData.content JSON. No migration. | ✓ |
| New column on PhaseData | Dedicated column via delta/ migration. More explicit, needs migration. | |
| Project/ScreenplayContent level | One canonical synopsis per project. More wiring + migration. | |

**User's choice:** PhaseData row (JSON content)
**Notes:** Reuses JSONB content column already written at end of generation — no migration required.

---

## Reuse policy (seed vs rebuild)

| Option | Description | Selected |
|--------|-------------|----------|
| Rebuild fresh each full run | Synopsis rebuilt scene-by-scene; persisted copy is output, not input. Avoids stale context. | ✓ |
| Reuse as seed when present | Seed generation from existing synopsis. More continuity for partial regens, risks stale facts. | |

**User's choice:** Rebuild fresh each full run
**Notes:** Seed-reuse deferred to Phase 49 (EVAL) regenerate/compare work.

---

## Claude's Discretion

- Exact synopsis word cap, prompt wording, and message structure for both the summarization call and the augmented scene call.
- Temperature/max_tokens for the summarization call (must use `chat_completion`).

## Deferred Ideas

- Structured continuity ledger (object/fact/character-state checklist) — revisit only if prose proves insufficient.
- Reusing a persisted synopsis as a seed for single-scene regeneration — relevant to Phase 49 (EVAL).
- Persisting synopsis at project / ScreenplayContent level — deferred to avoid a migration.
