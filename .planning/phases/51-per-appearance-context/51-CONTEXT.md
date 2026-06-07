# Phase 51: Per-Appearance Context - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user asleep; decisions by Claude, grounded in verified source — see .planning/v7.0-RESCOPE-NOTE.md).

<domain>
## Phase Boundary

Each extracted breakdown element records, per appearance, a short context note describing how/where it appears in each scene, and that context is surfaced in the breakdown UI (APPR-01, APPR-02). Cross-scene consolidation into one element with multiple appearances already works and is verified, not rebuilt (APPR-03).

**Re-scope context (verified):** The per-appearance context pipeline is plumbed END-TO-END but the value is DISCARDED at the final write:
- The AI returns `ExtractedElement.scene_appearances: List[ExtractedSceneAppearance{scene_index, context}]`, and the system prompt already asks for context.
- The DB `ElementSceneLink` table has a `context` column.
- The API `SceneLinkResponse` schema has `context: str`, the GET element endpoint eager-loads scene_links, and the frontend `SceneLink` TS type has `context: string`.
- BUT `_map_scene_indices_to_ids` flattens `scene_appearances` to a bare `List[str]` of scene IDs (dropping context), and `_reconcile_scene_links` writes `context=""` (verified line 452). And the ElementCard scene chip renders only "Scene N" — it never shows the context.

So Phase 51 = (1) thread the AI's `context` through the `scene_appearances → _map_scene_indices_to_ids → _reconcile_scene_links` boundary so `ElementSceneLink.context` is populated, and (2) surface that context in the breakdown UI.

**In scope:**
- Backend: change `_map_scene_indices_to_ids` to return scene_id + context pairs (not bare ids); change `_reconcile_scene_links` to write `context=<appearance.context>` instead of `""`. Preserve the user-vs-ai link sourcing and dedup behavior.
- Frontend: surface per-appearance context on the scene chips (ElementCard) and/or the element detail scene list (ElementSceneList) — e.g. chip tooltip/title + context shown in the detail view.

**Out of scope:**
- APPR-03 consolidation (already works via `_deduplicate_elements` merging scene_appearances) — VERIFIED, not rebuilt.
- Expanded categories (Phase 52); re-extraction hardening (Phase 53).
- No schema change (the `context` column already exists), no migration.
</domain>

<decisions>
## Implementation Decisions

### D-51-01 — Thread context through the scene-id mapping boundary (DECIDED: return (scene_id, context) pairs)
**Grey area:** `_map_scene_indices_to_ids` currently returns `List[str]`; the context lives on the same `ExtractedSceneAppearance` but is dropped.
**Decision:** Change `_map_scene_indices_to_ids` to return a list of `(scene_id, context)` tuples (or a small dataclass/dict) so the per-appearance context survives the index→id mapping. `_reconcile_scene_links` takes the new shape and writes `context=context` into each AI-sourced `ElementSceneLink` instead of `""`. Keep the existing logic: delete only `source="ai"` links, preserve `source="user"` links, skip a pair when a user-sourced link already exists for that (element, scene). Invalid/out-of-range scene_index still skipped with a warning (unchanged). Exact return type (tuple vs dataclass) is Claude's Discretion for the planner.

### D-51-02 — Surface context in the UI without clutter (DECIDED: chip tooltip + detail-view context line)
**Decision:** In `ElementCard`, the scene chip (currently text "Scene N") gains the context as a hover tooltip (`title` attribute or a styled tooltip) so the card stays compact but the context is reachable. In the element detail scene list (`ElementSceneList`), show the context inline beneath/next to each scene entry (more room there). Both consume `link.context` which already flows through the API and the `SceneLink` TS type. Where context is empty (legacy links written before this phase, or user-added links), render gracefully (chip with no tooltip / no context line — never "undefined"). Exact visual treatment is Claude's Discretion within the existing dark-amber theme; do not introduce a new tooltip dependency if a simple `title`/existing primitive suffices.

### D-51-03 — Preserve all existing breakdown behavior (DECIDED: additive)
**Decision:** The single AI call, EXTRACTION_SYSTEM_PROMPT, `_deduplicate_elements` (which already merges scene_appearances — APPR-03), `_upsert_elements` (user_modified/is_deleted honoring), the staleness clear, audit run, and the Phase 50 scene-scoped prompt are all unchanged. Only the scene-id mapping return shape, the one `context=""` write, and the chip/detail UI change. The existing breakdown tests (`test_breakdown_service.py` incl. Phase 50's, `test_breakdown_api.py`, `test_staleness.py`) MUST stay green. The DB `context` column and `SceneLinkResponse.context` schema are reused as-is (no schema/migration change).
</decisions>

<code_context>
## Existing Code Insights (verified, post-Phase-50 line numbers approximate)

- `_map_scene_indices_to_ids` (breakdown_service.py ~457-477): maps 1-based `scene_index` → ListItem id via `scene_summaries[zero_based]["id"]`, returns `List[str]`, drops `appearance.context`. THE BOUNDARY TO CHANGE.
- `_reconcile_scene_links` (~420-455): deletes `source="ai"` links, preserves `source="user"`, skips (element,scene) with an existing user link, writes new `ElementSceneLink(..., context="", source="ai")` at ~452. THE `context=""` TO FIX.
- Caller in `extract()` (~550-551): `scene_ids = self._map_scene_indices_to_ids(ctx, extracted_el.scene_appearances)` then `self._reconcile_scene_links(db, db_element, scene_ids)`. Both calls update for the new shape.
- `ExtractedSceneAppearance{scene_index:int, context:str}` (~schemas/service top) — the source of context; unchanged.
- `_deduplicate_elements` (~323-342): already unions scene_appearances across same-name elements (APPR-03) — VERIFY in tests, don't rebuild.
- DB `ElementSceneLink.context: Text` column already exists (database.py). API `SceneLinkResponse.context: str = ""` (schemas.py ~764) already exists; GET /element eager-loads scene_links and enriches titles (breakdown.py ~174-191). Frontend `SceneLink` TS type has `context: string` (types/index.ts ~274). All reused as-is.
- Frontend `ElementCard.tsx` scene chips (~251-269): renders "Scene N" buttons; add the context as tooltip. `ElementDetailPage.tsx` → `ElementSceneList` (sceneLinks prop, ~110): the detail scene list to add context display to.
- Tests: `test_breakdown_service.py::test_scene_linking` (~424) already drives scene_appearances with context strings (e.g. "Draws sword") — extend to assert the link's `context` is now persisted (was ""). Reuse the AsyncMock `chat_completion_structured` pattern.

## Pre-existing test-isolation concern
`.planning/v6.0-PREEXISTING-TEST-CONCERN.md`: yolo/session-isolation suites order-sensitive (NOT breakdown). New tests pass in isolation; don't touch those.
</code_context>

<specifics>
## Specific Ideas

- Backend (surgical): `_map_scene_indices_to_ids` returns (scene_id, context); `_reconcile_scene_links` writes that context. Update the `extract()` caller. ~10-20 lines.
- Frontend: chip tooltip in ElementCard; context line in ElementSceneList. Graceful empty-context handling.
- Tests: assert `ElementSceneLink.context` is populated with the AI's per-appearance context after extract (the key APPR-02 proof — previously "" ); assert APPR-03 consolidation still merges appearances across scenes (verify-not-rebuild); keep test_breakdown_service.py / test_breakdown_api.py / test_staleness.py green. Frontend: tsc build clean (no FE test harness — verify via npm run build).
- No schema change, no migration, no new dependency.

## Verification framing
- APPR-01 (element records its scenes): already true (scene_links) — verified.
- APPR-02 (per-appearance context note, surfaced in UI): the BUILD — backend populates context + UI shows it.
- APPR-03 (consolidate duplicates): already true (_deduplicate_elements) — verified.
</specifics>

<deferred>
## Deferred Ideas
- Editing per-appearance context in the UI (write path) — read/display is enough for APPR-02; editing a link's context is a future nicety.
- Rich tooltip component / popover library — use a simple title attribute or existing primitive.
</deferred>
