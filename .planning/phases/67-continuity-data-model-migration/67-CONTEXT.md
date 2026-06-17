# Phase 67: Continuity Data Model & Migration - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

The data foundation for v10.0 Show-Type / Episode Continuity. This phase delivers:

1. `shows.continuity_mode` — the single continuity axis (`connected` | `anthology` | `standalone`), settable on Show create/edit and readable via the Show API (SCONT-01).
2. `projects.episode_summary` (TEXT, nullable) — storage for the AI-auto-summary an episode will eventually carry. **Storage only this phase**; generation is Phase 69.
3. `projects.episode_summary_stale` (Boolean, default False) — invalidation flag mirroring `breakdown_stale`/`shotlist_stale`, set True when an episode's content is edited (ESUM-02).

All three columns are added via ONE new idempotent `backend/migrations/delta/011_*.sql` applied on boot (Phase 62 mechanism) — never an in-place ALTER that breaks re-runs.

**NOT in this phase:** mode-aware generation/injection (Phase 68), auto-summary generation or lazy regeneration (Phase 69), the creation wizard / presets (Phase 70), mode-aware review (Phase 71). This phase only creates the columns, the Show set/edit surface, and the stale-on-edit hook.

</domain>

<decisions>
## Implementation Decisions

### Migration default mode (the roadmap's flagged open question)
- **D-01:** Existing shows (and the column default) backfill to **`anthology`**. Rationale: anthology injects only the shared bible — identical to today's bible-only injection behavior — so upgrading the DB causes **zero generation-behavior change**. Continuity is strictly opt-in (user picks `connected` later via the Phase 70 wizard). `connected` was rejected as the default because it would change generation behavior on upgrade AND depends on summaries that don't exist until Phase 69. `standalone` is the `show_id IS NULL` feature-film case, not a show default.

### Stale-flag trigger scope
- **D-02:** `episode_summary_stale` is set True on episode-content edit **only when an `episode_summary` already exists** (non-empty). This mirrors `_mark_breakdown_stale`/`_mark_shotlist_stale` exactly — those flip True only when the dependent artifact exists. Editing an episode that was never summarized leaves `episode_summary_stale = False` (nothing to invalidate). No wasted regeneration triggers for Phase 69 to no-op on.
- **D-02a:** The hook fires at the SAME site as the existing stale marks: `backend/app/api/endpoints/phase_data.py` lines 256–259, gated on `phase in BREAKDOWN_SENSITIVE_PHASES`/`SHOTLIST_SENSITIVE_PHASES` (= `{"write", "scenes"}` — episode screenplay/content edits). Add a `_mark_episode_summary_stale(db, project_id)` helper alongside the existing two and call it in the same block. Does not commit (caller's `db.commit()` at line 261 covers it).

### Enum storage shape
- **D-03:** Store `continuity_mode` as a **VARCHAR with a string default `'anthology'`**, validated at the app layer (Pydantic schema + a Python `Enum`), NOT as a Postgres `ENUM` type. Rationale: keeps the delta trivially idempotent (`ADD COLUMN IF NOT EXISTS continuity_mode VARCHAR ... DEFAULT 'anthology'`), and adding a future mode (D1 framed continuity as a single *extensible* axis) needs only an app-level change, no `ALTER TYPE`. This intentionally diverges from the repo's Framework/TemplateType/PhaseType PG-enum convention for this 3-value, extensible field — call this out in the plan so it's a conscious deviation, not an oversight.

### API exposure surface
- **D-04:** `continuity_mode` is editable on Show create/edit (`ShowCreate`/`ShowUpdate`) and returned in `ShowResponse`. `episode_summary_stale` (read-only) is surfaced in episode/Project **read** responses so the frontend can later light up the staleness-banner pattern (as breakdown/shotlist already do). `episode_summary` text stays **internal** — not added to any API response this phase (Phase 69 exposes it when generation lands). This is the minimal-but-complete foundation: phases 68–71 read these without re-touching the schema.

### Claude's Discretion
- Exact delta file name (`011_continuity_columns.sql` or similar) and SQL phrasing — planner/executor choose, must be idempotent and follow the existing `delta/*.sql` README conventions.
- Whether the Python validation `Enum` for continuity_mode lives in `models/schemas.py` or `models/database.py` — follow whichever placement the existing Framework/TemplateType enums use.
- Test placement — mirror `test_staleness.py` / `test_breakdown_api.py` patterns.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone vision & locked decisions
- `.planning/v10.0-SHOW-TYPE-VISION.md` §D1–D5 — locked decisions: D1 (single extensible `continuity_mode` axis), D2 (AI-auto-summary, not full script / not hand-written), D3 (invalidate on edit, lazy regen), D4 (scale/duration stays metadata, NOT part of the type), D5 (presets are pure UI sugar).
- `.planning/ROADMAP.md` §"Phase 67" (lines 576–586) — goal, constraints, the migration-default open question resolved here (D-01), and success criteria.
- `.planning/REQUIREMENTS.md` — SCONT-01 (set mode on create/edit) and ESUM-02 (edit marks summary stale) are this phase's requirements.

### Migration mechanism (must mirror)
- `backend/migrations/delta/` — existing `001`–`010` deltas + `README.md`. New file is `011_*.sql`. Boot-applied, idempotent (Phase 62 mechanism).
- `backend/migrations/delta/008_episode_columns.sql` — closest analog (added Project/episode columns) for the new `episode_summary` / `episode_summary_stale` columns.
- `backend/migrations/delta/007_bible_columns.sql` — closest analog for adding columns to `shows`.

### Stale-flag pattern (must mirror exactly)
- `backend/app/api/endpoints/phase_data.py:21–53` — `_mark_breakdown_stale` / `_mark_shotlist_stale` helpers (the existence-gated pattern D-02 mirrors).
- `backend/app/api/endpoints/phase_data.py:256–261` — the call site where `_mark_episode_summary_stale` slots in (D-02a).
- `backend/app/models/database.py:163–164` — `breakdown_stale` / `shotlist_stale` column definitions to mirror for `episode_summary_stale`.
- `backend/app/api/endpoints/shots.py:96–103` — the acknowledge-stale endpoint pattern (reference only; not required this phase).

### Show model & API surface
- `backend/app/models/database.py:91–106` — `Show` model (add `continuity_mode` here) and `Project` model (lines ~154+, add `episode_summary` / `episode_summary_stale`).
- `backend/app/models/schemas.py:912–936` — `ShowCreate` / `ShowUpdate` / `ShowResponse` (add `continuity_mode`).
- `backend/app/api/endpoints/shows.py` — Show CRUD router.

### Enum convention (the deviation reference for D-03)
- `backend/app/models/database.py:157–159` — `Framework` / `TemplateType` / `PhaseType` PG-enum usage. D-03 intentionally does NOT follow this for `continuity_mode`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_mark_breakdown_stale` / `_mark_shotlist_stale` (`phase_data.py:21–53`): copy the structure verbatim for `_mark_episode_summary_stale` — query existence of the dependent artifact (here: `episode_summary` non-empty on the Project), set the flag, don't commit.
- Existing `delta/*.sql` files: copy the idempotent `IF NOT EXISTS` ADD COLUMN style from `007`/`008`.
- `breakdown_stale`/`shotlist_stale` Boolean columns: direct template for `episode_summary_stale`.

### Established Patterns
- Migrations are additive boot-applied deltas, never in-place edits to prior deltas, never destructive (Phase 62 / `railway-deploy-gotchas` memory: app won't import without OPENAI_API_KEY — unrelated but the boot path is load-bearing).
- Stale flags are existence-gated and committed by the caller, not the helper.
- Episodes ARE `Project` rows (the Project model doubles as the episode entity; `show_id` links episode→show, NULL = standalone feature film).

### Integration Points
- New `_mark_episode_summary_stale` call in `phase_data.py` update flow (lines 256–261).
- New `continuity_mode` field threads through `shows.py` router via `ShowCreate`/`ShowUpdate`/`ShowResponse`.
- `episode_summary_stale` added to the Project/episode read serialization (whichever schema `shows.py`/episode endpoints return).

</code_context>

<specifics>
## Specific Ideas

- `anthology` must be byte-for-byte behavior-equivalent to today's bible-only generation — the upgrade must be a silent no-op for existing users. This is the test bar for Success Criterion 2 ("existing shows/episodes still valid").
- Standalone projects (`show_id IS NULL`) must be completely unaffected by the migration and the stale hook — verify explicitly.

</specifics>

<deferred>
## Deferred Ideas

- **Acknowledge / clear-stale endpoint for episode summaries** — the `shots.py:96–103` acknowledge pattern. Not needed until Phase 69's lazy regen clears the flag automatically. Note for Phase 69.
- **Surfacing `episode_summary` text in API responses** — deferred to Phase 69 when generation produces real content.
- **Frontend staleness banner for episode summaries** — the read-only flag is exposed now (D-04) so a future UI phase can consume it, but the banner UI itself is not in v10.0's mapped phases.

None of these are scope creep into Phase 67 — all are downstream-phase concerns deliberately left out.

</deferred>

---

*Phase: 67-Continuity Data Model & Migration*
*Context gathered: 2026-06-17*
