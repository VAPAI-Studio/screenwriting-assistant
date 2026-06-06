# Phase 49: Side-by-Side Quality Compare - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user unattended; grey areas decided by Claude with codebase-grounded rationale, recorded below for review). This is the milestone-completing, USER-FACING phase — decisions here shape product UX, so review these when you wake.

<domain>
## Phase Boundary

The user can regenerate a single scene's screenplay using the improved generation path (continuity + voice + craft from phases 45–48) while preserving the prior output, see the prior and new versions side-by-side for that scene, and choose which to keep — the kept version persisting to the screenplay store (EVAL-01).

**In scope:**
- Backend: a regenerate-ONE-scene path (generate a single scene by its episode_index, preserving continuity context from surrounding scenes), returning the new screenplay WITHOUT clobbering the stored prior version.
- Frontend: a per-scene "Regenerate & Compare" action that opens a side-by-side compare view (old vs new), with a "Keep this version" choice that persists the chosen text.
- Persisting the chosen version back into the canonical store (`PhaseData(phase="write", subsection_key="screenplay_editor").content.screenplays[episode_index]` and the corresponding `ScreenplayContent`), and marking breakdown/shotlist stale (existing staleness pattern) only when a NEW version is kept.

**Out of scope (deferred):**
- Inline word-level diff highlighting — side-by-side full-text panes are sufficient for v6.0; a diff view is a later enhancement.
- Keeping a full version history / unlimited alternates — this phase compares exactly TWO versions (current stored vs one freshly regenerated) and keeps one. No version-history UI.
- Regenerating multiple scenes at once into a compare (one scene at a time).
- Automated quality scoring of the two versions — the user judges; no LLM-judge in this phase.
- No new model/dependency.
</domain>

<decisions>
## Implementation Decisions

### D-49-01 — Regenerate a SINGLE scene via the existing generation path, continuity-aware (DECIDED: new backend regenerate-scene endpoint reusing _generate_scripts)
**Grey area:** There is no single-scene generation today; `_generate_scripts` always loops all episodes.
**Decision:** Add a backend path to regenerate ONE scene by its `episode_index`. It fetches that scene's input (the scene ListItem / the episode entry that produced it), the project context, characters, and — critically — the continuity context (the running synopsis up to that scene + the immediately preceding scene's stored text) so the regenerated scene is consistent with its neighbors and benefits from the phase 45–48 improvements. Implementation approach is Claude's Discretion for the planner, but it MUST reuse the improved prompt construction in `_generate_scripts` (continuity block, voice block, craft block, native output) rather than a separate divergent prompt — the whole point is to regenerate with the IMPROVED path. Simplest faithful approach: a small helper that runs the existing scene-generation logic for a single episode with supplied `synopsis`/`prev_scene_text`, returning the `{title, content, episode_index}` dict. Expose via a new endpoint (e.g. `POST /api/wizards/regenerate-scene` or a screenplay-scoped route) that returns the new scene WITHOUT writing it to the store yet (preview-before-keep).

### D-49-02 — Compare exactly two versions; do not auto-persist the regenerated one (DECIDED: preview → explicit keep)
**Decision:** Regeneration returns the new scene text to the client as a PREVIEW; nothing is persisted until the user explicitly chooses. The compare shows: LEFT = the currently-stored version for that scene (from `screenplays[episode_index]`), RIGHT = the freshly regenerated version. The user picks one. "Keep old" = no-op (close). "Keep new" = persist the new text into `screenplays[episode_index].content` (+ title) in the `screenplay_editor` PhaseData.content (with `flag_modified`, the established Phase 45/46 JSONB pattern) AND update the matching `ScreenplayContent` row, then mark breakdown + shotlist stale (reuse `_mark_breakdown_stale`/`_mark_shotlist_stale`). Rationale: preserving the prior output until an explicit choice is the literal SC#1 ("regenerate … while preserving the prior output") and SC#3 ("choose which version to keep, kept version persists to ScreenplayContent").

### D-49-03 — Identify the scene by episode_index (DECIDED: reuse the existing implicit array-position key; no schema change)
**Grey area:** ScreenplayContent has no explicit per-scene FK (list_item_id is unused); screenplays are keyed by array position / `episode_index` in formatted_content.
**Decision:** Use `episode_index` (array position in `screenplays[]`) as the scene identifier for regenerate + keep, matching today's implicit keying. To update the right `ScreenplayContent` row on keep, match by project + the screenplay's stored `formatted_content.episode_index` (or, if ambiguous, by the existing ordering). NO migration, NO new column, NO populating `list_item_id`. Rationale: the existing pipeline (breakdown/shotlist) already reads `ScreenplayContent` by project and tolerates the current keying; introducing a schema change here would be scope creep beyond EVAL-01. If matching `ScreenplayContent` rows by episode_index proves unreliable (e.g. the row lacks episode_index), the planner may fall back to updating by stable ordering — but must NOT add a migration.

### D-49-04 — Compare UI: a modal launched from the screenplay view, per scene (DECIDED: SceneCompareModal in the write/screenplay_editor view)
**Decision:** Add a per-scene "Regenerate & Compare" affordance in the screenplay view (`ScreenplayEditorView` — the component rendering `screenplay_editor` content). Clicking it for a given scene opens a `SceneCompareModal` (reuse the existing Radix Dialog pattern from CreateProjectModal/AddElementDialog) with a two-column layout (left: current stored scene text; right: regenerated text, with a loading state while the regenerate call + poll completes). Footer actions: "Keep current" (close, no change) and "Keep new version" (persist + invalidate the subsection-data query + close). Reuse the existing wizard run/poll/apply infra patterns and React Query invalidation (`QUERY_KEYS.SUBSECTION_DATA`). No new route. Rationale: matches the codebase's established modal + React-Query mutation conventions; keeps the compare close to where the screenplay is read; minimal new surface. The exact per-scene trigger placement (a button per scene header vs. a scene picker in the modal) is Claude's Discretion — but the user MUST be able to target a specific scene and see old-vs-new for THAT scene.

### D-49-05 — Preserve all prior contracts and the generation improvements (DECIDED: additive feature, no regression)
**Decision:** The full-batch `script_writer_wizard` generation path (phases 45–48) is unchanged. Regenerate-scene is an ADDITIVE path that reuses the same improved prompt construction. The per-screenplay `{title, content, episode_index}` shape, the `{screenplays, synopsis}` PhaseData.content shape, and the staleness hooks are all preserved. Keeping a new version updates only that one scene's content (and optionally does NOT recompute the global synopsis in this phase — the synopsis was built for the original sequence; regenerating one scene for comparison need not rewrite it. The planner may leave synopsis untouched on a single-scene keep; document whichever choice is made). No change to breakdown/shotlist logic beyond the existing stale-marking.
</decisions>

<code_context>
## Existing Code Insights

**Backend:**
- `ScreenplayContent` model (database.py:286-297): `id, project_id, list_item_id (nullable, unused), content (Text), formatted_content (JSON — holds the full screenplay dict incl. episode_index), version (Int, default 1, currently never incremented), created_at, updated_at`. No back-relationship; read by breakdown_service + shotlist_generation_service by project_id.
- `_generate_scripts` (template_ai_service.py:305-481): loops all episodes; builds the improved prompt (continuity block, Phase 47 voice block, Phase 48 craft block, Phase 46 native output + TITLE parser); returns `{screenplays:[{title,content,episode_index}], synopsis}`. No single-scene entry — must add one that reuses this prompt logic for one episode with supplied synopsis/prev_scene_text.
- `apply_wizard_result_to_db` script_writer_wizard branch (wizards.py:250-283): writes `phase_data.content = {"screenplays", "synopsis"}` with `flag_modified`; creates a `ScreenplayContent(project_id, content=sp["content"], formatted_content=sp)` per screenplay; calls `_mark_breakdown_stale` + `_mark_shotlist_stale`. Reuse these helpers + the flag_modified pattern for the keep-new persistence.
- Wizard infra: `POST /api/wizards/run` (creates WizardRun, background gen), `GET /api/wizards/{id}` (poll), `POST /api/wizards/{id}/apply`. The regenerate-scene path can either follow this run/poll/apply shape OR be a simpler synchronous endpoint returning the new scene directly (planner's discretion; sync is simpler for a single scene but watch the existing 30s API timeout vs. generation latency — a single scene at max_tokens=4000 may exceed 30s, so the run/poll pattern or the longer CHAT_TIMEOUT=120s may be needed).
- Scene inputs: scene ListItems under PhaseData(phase="scenes", subsection_key="scene_list"), 10 fields each, ordered by sort_order; the script wizard consumes them as config.episodes. To regenerate scene i, fetch the matching scene input + the stored prior synopsis/prev-scene.

**Frontend:**
- `ScreenplayEditorView.tsx` (components/Patterns/): renders `phaseData.content.screenplays[]` (each `{episode_index, title, content, error?}`) as a merged paginated document; has view/edit modes. This is where the per-scene regenerate affordance + compare modal launch live.
- API client `lib/api.tsx`: `getSubsectionData`, `runWizard`, `getWizardRun`, `applyWizardResults`, `fetchWithTimeout` (API_TIMEOUT=30000, CHAT_TIMEOUT=120000). Auth via Bearer token (mock-token in dev). Add a `regenerateScene` method following the same pattern.
- Radix Dialog modal pattern: CreateProjectModal.tsx, AddElementDialog.tsx. Button primitive: components/UI/Button.tsx (variants incl. default/outline/ghost). React Query: useMutation + invalidate `QUERY_KEYS.SUBSECTION_DATA(projectId, phase, key)`.
- Types: types/index.ts — add types for the regenerate request/response.

**Testing:**
- Backend: pytest under backend/app/tests; reuse the _generate_scripts mocking pattern (patch `app.services.template_ai_service.chat_completion`). New backend tests should cover: regenerate-one-scene returns a single {title,content,episode_index} using the improved prompt (continuity/voice/craft present); keep-new persists into screenplays[i] + ScreenplayContent + marks stale; keep-old/preview does NOT persist.
- Frontend: check for an existing FE test setup (vitest/jest) — if none, backend tests + a manual UAT checklist suffice for this internal tool; do not stand up a new FE test harness from scratch unless one already exists.
- Pre-existing test-isolation concern (.planning/v6.0-PREEXISTING-TEST-CONCERN.md): yolo/session-isolation suites are order-sensitive and out of scope; new tests must pass in isolation.
</code_context>

<specifics>
## Specific Ideas

- Backend: a regenerate-single-scene helper in template_ai_service (reusing the improved per-scene prompt) + an endpoint that returns the new scene as a preview (no write) + a keep/persist path that updates screenplays[episode_index] in screenplay_editor content (flag_modified) and the matching ScreenplayContent row, then marks breakdown/shotlist stale. Mind the generation-latency vs API timeout (use poll pattern or 120s timeout).
- Frontend: a per-scene "Regenerate & Compare" trigger in ScreenplayEditorView → SceneCompareModal (two columns: current vs regenerated, loading state) → Keep current / Keep new → on keep-new, persist + invalidate SUBSECTION_DATA + close.
- Persist the kept version to ScreenplayContent (SC#3). Mark stale only on keep-new.
- Tests: backend regenerate + keep/no-keep persistence + improved-prompt-presence; keep existing suites (continuity 10, voice 8, craft 6, wizard 3) green.
- UI-SPEC: this is a frontend phase — a UI-SPEC.md for the SceneCompareModal (two-column compare, loading state, keep actions, where the per-scene trigger lives) should be produced before/with planning.
- No migration, no new dependency. Preserve phases 45–48 improvements and all contracts.

## Open question for the user (non-blocking — sensible default chosen)
- **Synopsis on keep-new (D-49-05):** I default to NOT rewriting the global running synopsis when a single scene is kept (the synopsis described the original sequence; one-scene compare is a quality spot-check, not a full re-thread). If you'd prefer keeping a new version to also re-thread continuity for later scenes, that's a richer follow-up — flagged, not built.
</specifics>

<deferred>
## Deferred Ideas

- Word-level / inline diff highlighting between the two versions.
- Full version history with N alternates per scene and a revert timeline.
- LLM-as-judge automatic quality scoring of old vs new.
- Re-threading the running synopsis + downstream scenes when a single regenerated scene is kept (continuity ripple) — flagged in the open question above.
- Batch regenerate-and-compare across multiple scenes.
- A frontend test harness if none currently exists (out of scope to stand one up for this phase).
</deferred>
