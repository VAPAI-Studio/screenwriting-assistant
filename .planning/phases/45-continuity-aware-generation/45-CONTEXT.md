# Phase 45: Continuity-Aware Generation - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Each scene's screenplay is generated with awareness of what was *actually written* before — not just one-line plan summaries — so tone, voice, and setup/payoff stay consistent across the scene sequence.

The change is localized to `_generate_scripts` in `backend/app/services/template_ai_service.py:253`. The current loop writes each scene with only a `scene_outline` (one-line summaries of all scenes) as cross-scene context. This phase replaces that with: (a) the full text of the immediately preceding scene, plus (b) a maintained running "story so far" synopsis, injected into each scene's generation prompt.

**In scope (CONT-01/02/03):**
- Inject prior generated scene text into later scene prompts
- Maintain a running synopsis across the scene loop, kept within token limits
- Keep setups/payoffs consistent so a generated scene does not contradict an earlier one

**Out of scope (other v6.0 phases):**
- Native vs json_mode format evaluation → Phase 46 (FMT)
- Per-character voice profiles in the script prompt → Phase 47 (VOICE)
- Craft guidance (subtext, action-line economy, show-don't-tell) → Phase 48 (CRAFT)
- Side-by-side regeneration/compare UI → Phase 49 (EVAL)

Do NOT change the json_mode `{title, content}` return shape in this phase — that is Phase 46's decision. Continuity work must preserve the existing return contract.
</domain>

<decisions>
## Implementation Decisions

### Context injected per scene (CONT-01 / CONT-02)
- **D-01:** Each scene's generation prompt receives **the running synopsis (for all earlier scenes) + the full verbatim text of only the immediately preceding scene.** This bounds tokens while giving strong local continuity — the actual prose voice/tone of the scene just written carries forward. (Not: last-N-scenes full text; not: synopsis-only.)

### Running synopsis generation (CONT-02)
- **D-02:** The running "story so far" is produced by a **separate, small AI summarization call after each scene is written.** This updates a cumulative synopsis capturing what the story has established (facts, objects, character states, where things stand). One extra cheap call per scene, in exchange for the best continuity fidelity. (Not: reusing scene-plan summary fields; not: naive append of generated-scene summaries — both reflect the plan/coarse state rather than what was actually written.)
- **D-03:** The synopsis is **re-summarized to a cap each time** (the summarization call regenerates the whole synopsis, instructed to stay under a fixed length, e.g. ~300–500 words). This keeps it naturally bounded on long, many-scene scripts. (Not: fixed char/token truncation, which can cut mid-fact and lose early setups.)

### Continuity representation (CONT-03)
- **D-04:** The synopsis is **prose-only** ("story so far" narrative). Setup/payoff consistency is achieved via the prose synopsis carrying established facts forward, which the model reasons over well. No structured continuity ledger / checklist in this phase — keep it simple for v6.0; revisit only if prose proves insufficient.

### Sequencing & standalone path (CONT success criterion 4)
- **D-05:** Keep the existing **strict sequential** in-order loop — scene N+1 is generated with scene N's text + the updated synopsis. **When there is no preceding scene** (first scene of a run, or a single-scene generation), inject **no continuity context** → existing behavior is unchanged. This satisfies "existing single-scene / non-sequential generation still works unchanged when there is no prior scene."

### Synopsis persistence
- **D-06:** The running synopsis is **persisted to the DB**, stored in the **existing `screenplay_editor` `PhaseData.content` JSON** alongside the screenplays. **No migration** — reuses the JSONB `content` column already written at the end of the generation flow (see `wizards.py` script_writer_wizard apply path). (Not: a new column; not: project/ScreenplayContent-level storage — both would need a migration for something only generation uses.)
- **D-07:** A full script-generation run **rebuilds the synopsis fresh, scene-by-scene, from scratch.** The persisted synopsis is the *output record*, not an *input* — it is not reused as a seed on a later run. This avoids stale-context bugs after edits. (Trade-off acknowledged: single-scene regen does not get prior-story context from a persisted synopsis; that is acceptable for this phase and can be revisited in Phase 49's compare/regenerate work if needed.)

### Claude's Discretion
- Exact synopsis word cap, prompt wording for the summarization call, and the system/user message structure for both the summarization call and the augmented scene call are left to research/planning.
- Whether the summarization call uses the same `chat_completion` helper (it should, for provider abstraction) and its temperature/max_tokens settings.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` §"Continuity (CONT)" — CONT-01, CONT-02, CONT-03 definitions
- `.planning/ROADMAP.md` §"Phase 45: Continuity-Aware Generation" — goal + 4 success criteria

### Code to modify / integrate with
- `backend/app/services/template_ai_service.py:253` — `_generate_scripts`: the sequential scene loop; current `scene_outline` injection (lines 261–300) is what this phase replaces/augments. Mirror the existing scene-planner summarization call (lines 237–251) as the pattern for the new per-scene synopsis call.
- `backend/app/services/ai_provider.py:40` — `chat_completion`: the provider-abstracted call (OpenAI + Anthropic) that BOTH the scene-writing call and the new synopsis-summarization call MUST use, preserving `json_mode` usage where applicable.
- `backend/app/api/endpoints/wizards.py:249` — `script_writer_wizard` apply path: where `_generate_scripts` output is persisted into `PhaseData.content` (`screenplay_editor` subsection) and `ScreenplayContent`. This is where the persisted synopsis (D-06) attaches in the JSON.

No external ADRs/specs — requirements fully captured in decisions above.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Scene-planner summarization call** (`template_ai_service.py:237–251`): existing pattern for a small `chat_completion` JSON call — reuse its shape for the new per-scene synopsis-update call.
- **`chat_completion`** (`ai_provider.py:40`): provider-abstracted (OpenAI/Anthropic), supports `json_mode`, `temperature`, `max_tokens`. Use for the synopsis call so both providers work (no new provider wiring needed).
- **`PhaseData.content` JSONB** (`screenplay_editor` subsection, written in `wizards.py:270–281`): already persisted at end of generation; the synopsis rides along here (D-06) with no migration.

### Established Patterns
- **Sequential in-order scene loop** with `episode_index` tagging on each result (`template_ai_service.py:268, 314`) — preserved; continuity context is threaded through the loop's running state.
- **JSON-mode generation returning `{title, content}`** — the return contract; must NOT change in this phase (Phase 46 owns that).
- **Graceful per-scene failure handling** (`template_ai_service.py:316–323`): a failed scene appends an error placeholder. Note: with strict-sequential continuity, planning should decide what the *next* scene sees if a prior scene failed (current D-05 path injects the prior scene's text — which would be the error placeholder). Flag for planner: keep behavior simple, but ensure a failed prior scene doesn't poison the synopsis/continuity context badly.

### Integration Points
- Inside `_generate_scripts`: maintain running `synopsis` (str) and `prev_scene_text` (str) across loop iterations; inject both into the scene prompt; after a successful scene, call the synopsis-update summarization.
- At persistence (`wizards.py` script_writer_wizard branch): write the final synopsis into the `screenplay_editor` `PhaseData.content` JSON.
</code_context>

<specifics>
## Specific Ideas

- The injected context per scene = **running prose synopsis (all earlier scenes) + full text of the single immediately-preceding scene.** This specific combination is the core decision (D-01).
- First scene / single-scene generation: **zero continuity context** — identical to today's behavior (D-05).
- Synopsis is **regenerated to a word cap each scene** and **persisted but never reused as a seed** (D-03, D-07).
</specifics>

<deferred>
## Deferred Ideas

- **Structured continuity ledger** (explicit object/fact/character-state list injected as a checklist) — considered for CONT-03 but deferred; prose synopsis chosen for v6.0. Revisit only if prose-only continuity proves insufficient in practice.
- **Reusing a persisted synopsis as a seed** for single-scene regeneration (so a regenerated scene sees prior story) — deferred; relevant to Phase 49 (EVAL) regenerate/compare work, not this phase.
- **Persisting synopsis at project / ScreenplayContent level** (one canonical "story so far" per project) — deferred; PhaseData JSON storage chosen to avoid a migration.

None other — discussion stayed within phase scope.
</deferred>

---

*Phase: 45-continuity-aware-generation*
*Context gathered: 2026-06-06*
