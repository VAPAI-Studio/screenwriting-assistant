# Phase 50: Scene-Scoped Fidelity - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user asleep; decisions by Claude, grounded in verified source — see .planning/v7.0-RESCOPE-NOTE.md). Review on waking.

<domain>
## Phase Boundary

Breakdown extraction attributes each production element to the correct scene(s) reliably, by giving the AI explicit per-scene structure to extract against — rather than a single concatenated text blob it must self-segment. The "physically present on screen" extraction rules are preserved (BFID-01/02/03).

**Re-scope context (verified):** The original BFID-01 framing ("extract against scene text not summaries") is ALREADY satisfied — `_build_extraction_context` feeds full `ScreenplayContent.content` text and `_build_user_prompt` emits a `## Screenplay Content` section with every scene's full text. The genuine gap is **scene-scoped attribution accuracy**: today all scenes are concatenated with `---` separators into one `## Screenplay Content` block, and the AI self-reports a `scene_index` per appearance against the separate `## Scenes` summary list. On longer scripts this self-segmentation is error-prone. Phase 50 makes the per-scene boundaries EXPLICIT in the prompt so `scene_index` attribution is reliable.

**In scope:**
- Restructure the extraction user prompt so each scene's full text is clearly delimited and labeled with its 1-based index (the same index space `ExtractedSceneAppearance.scene_index` already uses), so the AI attributes elements to the right scene.
- Preserve the single structured-output call (one `chat_completion_structured`), the on-screen-only rules, and all existing element/scene-link behavior.

**Out of scope:**
- Per-scene separate AI calls (N calls = N× cost/latency; rejected — see D-50-02).
- Surfacing the per-appearance `context` string in links/UI — that is Phase 51 (the context is currently discarded; 51 threads it through).
- Expanded categories (Phase 52); re-extraction hardening (Phase 53).
- No schema change, no migration.
</domain>

<decisions>
## Implementation Decisions

### D-50-01b — Align ONLY by episode_index; no positional fallback (CORRECTED post-review, 2026-06-07)
**What changed:** The first implementation added a positional fallback (index ScreenplayContent rows from the end of a newest-first list) for rows lacking `episode_index`. Code review + a targeted regression test (`test_legacy_rows_without_index_use_safe_concatenated_fallback`) proved this **silently reverses scene order** when `created_at` ties (SQLite is second-resolution; insertion order is not recoverable), mis-attributing every element to the wrong scene — a data-correctness bug. **Corrected:** `_align_screenplay_to_scenes` now aligns STRICTLY by `formatted_content.episode_index` (the only reliable join key, set by the v6.0 generation path). Scenes without an episode_index match are omitted → the strict full-coverage gate fails → the prompt falls back to the SAFE concatenated form (all scene text still reaches the AI; no mis-attribution). This is the same lesson as v6.0 WR-01 (no reliable ordering signal without a schema change). Duplicate rows per episode_index: first match wins (newest-first), consistent with keep-scene-version.

### D-50-01 — Explicit per-scene delimited prompt structure (DECIDED: label each scene's full text with its index)
**Grey area:** How to make extraction reliably scene-scoped without per-scene calls.
**Decision:** Restructure `_build_user_prompt` so the screenplay is presented scene-by-scene with explicit, indexed delimiters — each scene's FULL text under a clear `### Scene {i+1}: {summary}` (or equivalent) header, in the SAME 1-based index space the `## Scenes` list and `ExtractedSceneAppearance.scene_index` already use. Today the prompt has a `## Scenes` summary list AND a separately-concatenated `## Screenplay Content` blob; the AI must mentally align them. Merging them — each scene's summary + its full text together under its index — removes the alignment ambiguity and makes `scene_index` attribution reliable. The AI instruction is updated to "attribute each element to the scene index/indices under which its text appears."
**Constraint:** This requires the per-scene screenplay text to be available keyed by scene. Today `screenplay_texts` is a flat `List[str]` (from ScreenplayContent rows) and `scene_summaries` is a separate list. The plan must align them by index — ScreenplayContent rows carry `formatted_content.episode_index` (v6.0) which maps to scene order. Where a per-scene mapping is unavailable/misaligned, fall back gracefully to the current concatenated form (never crash an extraction). Exact alignment mechanism is Claude's Discretion for the planner, but it MUST be robust to count mismatches between ScreenplayContent rows and scene_list ListItems.

### D-50-02 — Keep ONE structured-output call, not per-scene calls (DECIDED: single call)
**Decision:** Extraction stays a SINGLE `chat_completion_structured` call returning `ExtractionResponse` with all elements + their `scene_appearances`. Do NOT switch to one AI call per scene. Rationale: per-scene calls multiply cost and latency by the scene count and lose cross-scene consolidation (the existing `_deduplicate_elements` unions appearances across scenes — APPR-03, already working). A single call with explicit per-scene structure in the prompt gets the attribution benefit without the cost/consolidation downsides. `max_tokens=8000` and `temperature=0.15` unchanged.

### D-50-03 — Preserve on-screen-only rules and all existing behavior (DECIDED: additive prompt restructure only)
**Decision:** The existing extraction RULES (only physically-present-on-screen elements; no dialogue-only mentions; no abstractions) are preserved verbatim in the system prompt. The dedup (`_deduplicate_elements`), upsert (`_upsert_elements` honoring user_modified/is_deleted), scene-link reconcile, staleness clear, and audit run are all unchanged. Phase 50 only restructures how the screenplay TEXT is laid out in the user prompt for better attribution. The `ExtractedElement`/`ExtractionResponse` models are unchanged. Existing tests (`test_breakdown_service.py`, `test_breakdown_api.py`, `test_staleness.py`) MUST stay green.
</decisions>

<code_context>
## Existing Code Insights (verified)

- `breakdown_service.py:_build_extraction_context` (~112-176): builds `ExtractionContext(screenplay_texts=[sc.content ...], character_names, scene_summaries=[{id, summary, sort_order}], project_title)`. `screenplay_texts` is flat; `scene_summaries` carries the scene ListItem `id` per scene (used to map scene_index → ListItem id).
- `_build_user_prompt` (~178-207): emits `## Known Characters`, `## Scenes` (1-based summary list), `## Screenplay Content` (all scene texts concatenated with `---`). THE FILE TO RESTRUCTURE.
- `ExtractedSceneAppearance{scene_index:int(1-based), context:str}`, `ExtractedElement{category, canonical_name, description, scene_appearances:[...]}`, `ExtractionResponse{elements:[...]}` — unchanged by Phase 50.
- `_map_scene_indices_to_ids` (~364): maps 1-based scene_index → ListItem id via `scene_summaries[zero_based]["id"]`. Relies on scene_index aligning to scene_summaries order — exactly what D-50-01 makes reliable.
- ScreenplayContent rows carry `formatted_content.episode_index` (v6.0) — the key to align per-scene text with scene_summaries order.
- `extract()` (~416): the pipeline; only `_build_user_prompt`/context-building changes.
- Tests: `test_breakdown_service.py` mocks `chat_completion_structured`; `_setup_project_with_screenplay` seeds project+screenplay+characters+3 scenes; `_mock_extraction_response` wraps elements. New Phase-50 tests follow this pattern.

## Pre-existing test-isolation concern
`.planning/v6.0-PREEXISTING-TEST-CONCERN.md`: yolo/session-isolation suites are order-sensitive (NOT breakdown). New tests must pass in isolation; do not touch those suites.
</code_context>

<specifics>
## Specific Ideas

- Surgical, backend-only. Touch `_build_extraction_context` (to carry per-scene text keyed by index) and `_build_user_prompt` (to emit per-scene delimited structure). Possibly a small helper to align ScreenplayContent rows ↔ scene_summaries by episode_index/order with a graceful fallback.
- Tests (add to or beside test_breakdown_service.py): assert the built prompt presents each scene's text under its own indexed header; assert a mocked AI response with scene_index attribution maps elements to the correct scene ListItem ids; assert the on-screen-only rules text is still present; assert graceful fallback when ScreenplayContent count ≠ scene count (no crash, extraction still runs).
- Keep test_breakdown_service.py / test_breakdown_api.py / test_staleness.py green.
- No schema change, no migration, no new dependency.
- BFID-01 (already satisfied) is VERIFIED in this phase's verification (full text reaches the AI), not rebuilt. BFID-02 (scene-scoped) is the build. BFID-03 (on-screen rules) is the regression guard.
</specifics>

<deferred>
## Deferred Ideas
- Per-scene separate AI calls (cost/latency/consolidation downsides) — rejected.
- Surfacing per-appearance context — Phase 51.
- Token-budget windowing for very long scripts (chunked extraction) — only if a real script blows the 8000-token budget; not now.
</deferred>
