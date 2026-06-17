# Phase 67: Continuity Data Model & Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 67-Continuity Data Model & Migration
**Areas discussed:** Migration default mode, Stale-flag trigger scope, Enum storage shape, API exposure surface

---

## Migration default mode

| Option | Description | Selected |
|--------|-------------|----------|
| anthology | Safest: anthology injects only the shared bible — identical to today's bible-only behavior. Zero behavior change on upgrade. Opt-in to continuity. | ✓ |
| connected | Preserves implicit season intent, but changes generation behavior on upgrade and depends on summaries that don't exist until Phase 69. | |
| standalone | No cross-episode context; really the show_id=NULL feature-film case, not a show default. | |

**User's choice:** anthology
**Notes:** Resolves the open question the roadmap explicitly deferred to this phase (ROADMAP §Phase 67, line 580). Becomes both the backfill value for existing shows and the column default.

---

## Stale-flag trigger scope

| Option | Description | Selected |
|--------|-------------|----------|
| Only if summary exists | Mirror breakdown_stale exactly: flip stale=True only when episode_summary is non-empty. | ✓ |
| Always on edit | Set stale=True on every episode-content edit regardless; Phase 69 would no-op on empty summaries. | |

**User's choice:** Only if summary exists
**Notes:** Existence-gated, same as `_mark_breakdown_stale`/`_mark_shotlist_stale`. Hook fires at `phase_data.py:256–261`.

---

## Enum storage shape

| Option | Description | Selected |
|--------|-------------|----------|
| String + app validation | VARCHAR + Pydantic/Python Enum validation. Trivial idempotent delta; extensible without ALTER TYPE. | ✓ |
| Postgres ENUM type | CREATE TYPE + column, consistent with Framework/TemplateType; but fiddly idempotent CREATE TYPE and ALTER TYPE to extend. | |

**User's choice:** String + app validation
**Notes:** Intentional, conscious deviation from the repo's PG-enum convention for this 3-value, extensible (D1) field. Plan should flag it as deliberate.

---

## API exposure surface

| Option | Description | Selected |
|--------|-------------|----------|
| Mode on Show + stale on episode read | continuity_mode editable+returned on Show; episode_summary_stale read-only in episode reads; episode_summary text stays internal until Phase 69. | ✓ |
| Mode on Show only | Only continuity_mode; phases 68/69 add episode read exposure later. | |
| Expose everything now | Surface mode + full summary text + stale flag everywhere immediately. | |

**User's choice:** Mode on Show + stale on episode read
**Notes:** Minimal-but-complete foundation so phases 68–71 read without re-touching schemas. Summary text deferred to Phase 69.

## Claude's Discretion

- Exact delta filename and idempotent SQL phrasing (follow `delta/*.sql` README conventions).
- Placement of the Python validation Enum (schemas.py vs database.py — match existing enums).
- Test file placement (mirror test_staleness.py / test_breakdown_api.py).

## Deferred Ideas

- Acknowledge/clear-stale endpoint for episode summaries — deferred to Phase 69 (lazy regen clears the flag automatically).
- Surfacing `episode_summary` text in API responses — deferred to Phase 69.
- Frontend staleness banner for episode summaries — flag exposed now, banner UI not in v10.0's mapped phases.
