# Phase 68: Mode-Aware Generation Context Injection - Research

**Researched:** 2026-06-17
**Domain:** AI prompt-context assembly / SQLAlchemy ORM querying / FastAPI service threading
**Confidence:** HIGH (this is an internal codebase investigation, not an external-library question; all claims verified by reading the live source)

## Summary

Phase 68 branches episode-generation context on `shows.continuity_mode` (shipped in Phase 67). The roadmap text claims episode-writing prompts are built in `openai_service.py` / "anthropic" — **this is wrong and is the single biggest landmine for the planner.** `openai_service.py` only does *section review*, and there is no `anthropic_service.py`. The actual, single, provider-agnostic injection point is **`backend/app/utils/bible_context.py::build_bible_context(db, project)`** (52 lines). Every generation path — the wizard background task, the MCP `screenplay_generate_scene` tool, breakdown extraction, AI chat, and review — calls this one helper and threads its string output downstream. [VERIFIED: grep of `bible_context` across `app/` — 30+ call sites, all routing through this one builder.]

The cleanest implementation is therefore: **extend `build_bible_context` (or add a sibling helper it composes) to read the show's `continuity_mode` and, in `connected` mode, append prior-episode summaries** — exactly mirroring how the existing Season Arc / Characters / Tone sections are appended. The function already (a) returns `None` for standalone (`show_id` NULL) projects, and (b) reads `Show` by `project.show_id`. Mode-branching is a localized change to this one file plus one new query for prior episodes. No generation-loop code (`template_ai_service.py`) needs to change — it already receives `bible_context` as an opaque prepended string.

**Primary recommendation:** Branch inside `build_bible_context` on `show.continuity_mode`. `standalone` and `show_id IS NULL` → behave exactly as today (bible only / None). `anthology` → behave exactly as today (bible only — this IS the current behavior, so SCONT-03 is essentially "no change beyond confirming the mode gate"). `connected` → current bible PLUS a new `## Prior Episodes` block built from `Project.episode_summary` of episodes with a *strictly lower* `episode_number`, ordered `episode_number.asc()`, skipping null/empty/whitespace summaries, capped to the most-recent-N (recommend N=8) by `episode_number`. Stale summaries: inject them but tag `(summary may be out of date)` — Phase 69 owns regeneration, Phase 68 must never fail or block on staleness.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read `continuity_mode` from show | API / Backend (`bible_context.py`) | DB | Already loads `Show` here; mode is a column on it |
| Query prior-episode summaries (ordered) | API / Backend (`bible_context.py`) | DB | Needs a `Project` query scoped by `show_id` + `episode_number` |
| Assemble mode-branched context string | API / Backend (`bible_context.py`) | — | Single existing assembly point; string is prepended downstream |
| Inject string into the LLM prompt | API / Backend (`template_ai_service._build_project_context`) | — | Already prepends `bible_context` unchanged; **no change needed** |
| Graceful skip of missing/stale summary | API / Backend (`bible_context.py`) | — | Pure read-and-filter logic; never raises |
| Provider call (OpenAI/Anthropic) | API / Backend (`ai_provider.chat_completion`) | — | Provider-agnostic; downstream of injection; **out of scope** |

## User Constraints (from CONTEXT.md)

No `68-CONTEXT.md` exists (config `skip_discuss: true`). Constraints below are lifted from the ROADMAP Phase 68 "Constraints to honor" block and the v10.0 VISION locked decisions, which are authoritative.

### Locked Decisions (ROADMAP §Phase 68 + VISION D1–D5)
- Branch at the existing `bible_context` assembly point (the roadmap *names* `breakdown_service.py:312` as the pattern to mirror, but the live single assembly helper is `app/utils/bible_context.py` — see Critical Finding #1).
- `connected` → season arc + `episode_summary` of prior episodes ordered by `episode_number` (**reliable integer key, NEVER positional** — recurring project bug, see Pitfall 1).
- `anthology` → ONLY the shared bible (world/tone). No other-episode plot.
- `standalone` (and `show_id` NULL projects) → NO cross-episode context. Current feature-film behavior unchanged.
- This phase **only READS** summaries. It does NOT generate or regenerate them (Phase 69). A missing/stale/empty summary must degrade gracefully (skip that episode's contribution), NEVER fail generation. [VISION D2/D3]
- Summary text is AI-auto-generated (D2), invalidated on edit via `episode_summary_stale` (D3) — both already shipped in Phase 67.

### Claude's Discretion (open question to LOCK in plan)
- **Token-budget / truncation policy** for long connected seasons. See Pitfall 3 + recommendation: most-recent-N=8 prior summaries by `episode_number`, oldest dropped first. Planner should lock a concrete default.
- Whether stale summaries are injected-with-warning vs skipped. Recommendation: **inject with a `(may be out of date)` marker** (Phase 69 makes this moot via lazy regen). Planner locks.

### Deferred Ideas (OUT OF SCOPE)
- Auto-summary generation / lazy regeneration (Phase 69).
- Continuity-inconsistency detection ("X dead in ep2, appears in ep4") — deferred entire milestone.
- Mode-aware review (Phase 71). Show-creation wizard / presets (Phase 70).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCONT-02 | `connected` mode feeds season arc + prior-episode summaries, ordered by `episode_number` (never positional) | New `## Prior Episodes` block in `build_bible_context`; query `Project.show_id == show.id, episode_number < current, episode_summary truthy`, `.order_by(Project.episode_number.asc())` — exact ordering precedent at `shows.py:182` |
| SCONT-03 | `anthology` mode receives only the shared bible (world/tone), no other-episode context | This is the CURRENT behavior of `build_bible_context`. Gate: only the `connected` branch adds prior episodes; anthology falls through to the existing bible-only return |
| SCONT-04 | `standalone` (or `show_id` NULL) injects no cross-episode context (feature-film behavior) | `build_bible_context` already returns `None` for `show_id` NULL (line 18-19). For `standalone` shows, gate the prior-episode block off so only the bible (if any) is returned — but ROADMAP §3 success-criterion says standalone shows inject NO cross-episode context, which the bible-only fallthrough satisfies |

## Critical Research Questions — Answered

### Q1 (TOP DELIVERABLE) — WHERE is the episode-writing prompt actually assembled?
**Answer:** The mode-injection edit happens in **`backend/app/utils/bible_context.py::build_bible_context()` (lines 16–52).** [VERIFIED: file read]

The ROADMAP's pointer to `openai_service.py` / "anthropic" is **incorrect**:
- `openai_service.py` (116 lines) contains only `OpenAIService.review_section` — *section review*, not screenplay generation. [VERIFIED: full file read]
- There is **no `anthropic_service.py`**. The provider split lives in `app/services/ai_provider.py::chat_completion(provider=...)`, downstream of all prompt assembly. [VERIFIED: grep]

The real generation prompt is built in **`app/services/template_ai_service.py`** (`_generate_scripts` → `_generate_one_scene`, `_generate_scenes`, `wizard_generate`). But generation receives context via the `project_context` string, which is built by `_build_project_context(...)` — and that function (lines 16–58) **prepends `bible_context` verbatim** (`if bible_context: context_parts.append(bible_context)`). [VERIFIED: lines 27–29].

So the call chain is:
```
endpoint (wizards.py:134 / mcp screenwriting.py:86 / ai_chat.py / review.py / breakdown.py)
  └─ build_bible_context(db, project)          ← THE EDIT SITE (app/utils/bible_context.py)
       └─ _get_project_context(db, project, bible_context=...)   (wizards.py:22 / ai_chat.py:27 / screenwriting.py via import)
            └─ template_ai_service._build_project_context(..., bible_context=...)   (prepends it)
                 └─ _generate_scripts / _generate_one_scene → ai_provider.chat_completion
```
Editing `build_bible_context` propagates to ALL generation paths with zero downstream changes. [VERIFIED: 30+ call sites all funnel through `build_bible_context`.]

### Q2 — How is prior-episode context currently assembled? Net-new or partial?
**Net-new.** Today `build_bible_context` appends ONLY the show's *bible* fields (`bible_characters`, `bible_world_setting`, `bible_season_arc`, `bible_tone_style`, `episode_duration_minutes`). [VERIFIED: lines 33–52]. There is **no** existing cross-episode / prior-`episode_summary` injection anywhere. The Season Arc that's injected is the *show-level bible field* `show.bible_season_arc`, NOT per-episode summaries. The `synopsis` / `prev_scene_text` continuity in `template_ai_service` (Phase 45/v6.0) is **intra-episode** (scene-to-scene within one generation run), unrelated to cross-episode continuity. So connected-mode prior-episode injection is entirely new code.

### Q3 — Episode ordering
**Confirmed.** Episodes ARE `Project` rows linked by `show_id` (nullable UUID FK, `database.py:175`) with an integer `episode_number` (`database.py:176`). [VERIFIED]. **There is an exact in-repo precedent for correct ordering:** `app/api/endpoints/shows.py:181-182`:
```python
.filter(database.Project.show_id == str(show_id))
.order_by(database.Project.episode_number.asc())
```
The planner MUST reuse this exact pattern. **LANDMINE (see Pitfall 1):** never order positionally / by insertion / by `created_at` / by list index. This ordering bug bit the project twice (v6.0 WR-01, v7.0 ph50 — see MEMORY: "ScreenplayContent has no reliable order — join by episode_index only, never positionally").

### Q4 — Token-budget / truncation policy (the open question)
**Recommendation to LOCK:** most-recent-**N = 8** prior summaries, selected by highest `episode_number` below the current episode, then rendered in ascending `episode_number` order. Drop oldest (lowest `episode_number`) first when over budget. Rationale: `episode_summary` is a bounded AI auto-summary (Phase 69 will keep them short — D2 explicitly rejects full scripts to avoid token blow-up), so a simple count cap is sufficient and far simpler than a char/token budget. 8 episodes of bounded summaries comfortably fits alongside the bible within `MAX_TOKENS`. If the planner prefers a belt-and-suspenders cap, add a secondary per-summary char clamp (e.g. truncate each summary to ~1500 chars with an ellipsis) — but count-cap alone is the recommended simple default. This is `[ASSUMED]` on the eventual summary length (Phase 69 hasn't shipped); flag for the planner to confirm N.

### Q5 — Graceful degradation of missing/empty/stale summaries
- **Missing / null / empty / whitespace-only `episode_summary`:** skip that episode's contribution. Use the same truthy-after-strip test Phase 67 established (`project.episode_summary` truthy after `.strip()`). [VERIFIED: 67-03-SUMMARY documents this existence-gate convention.] A connected episode where ALL priors are empty must still generate (it just gets bible-only) — SCONT/ROADMAP success-criterion #4.
- **Stale (`episode_summary_stale == True`):** **Recommendation: still inject, with a `(summary may be out of date)` marker.** Phase 68 explicitly does NOT regenerate (that's Phase 69's lazy regen, which runs *before* Phase 68 reads in the final wired flow). Skipping stale summaries would silently drop legitimate prior context; injecting stale-but-present text is strictly better than nothing and never blocks generation. Planner locks this; it's low-risk either way because Phase 69 will clear the flag before the read.

### Q6 — Which AI provider path is live?
**`AI_PROVIDER` defaults to `"anthropic"`** (`config.py:16`), model `claude-sonnet-4-6` (`config.py:24`); OpenAI (`gpt-4o`) is the alternate. [VERIFIED]. **CLAUDE.md's "OpenAI GPT-4" is stale.** *This does not affect Phase 68:* injection happens in `build_bible_context` (provider-agnostic, plain string) upstream of `ai_provider.chat_completion(provider=...)`. The planner edits no provider code and no model-specific builder — both providers receive the identical prepended context string.

## Standard Stack

No new external packages. This phase is pure internal-code change against the existing stack. [VERIFIED: CLAUDE.md + live imports]

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | (existing) | ORM query for prior episodes by `show_id` + `episode_number` | Already the project ORM |
| Pydantic v2 | (existing) | No schema change required (summary text stays internal per D-04) | Already in use |
| pytest + unittest.mock | (existing) | Test the mode branch by asserting on the assembled string + mocked `chat_completion` | Established test pattern (`test_bible_injection.py`, `test_continuity_generation.py`) |

**Installation:** none.

## Package Legitimacy Audit

Not applicable — this phase installs **no external packages**. All work uses already-installed, already-verified project dependencies (SQLAlchemy, Pydantic v2, pytest). slopcheck gate skipped (nothing to check).

## Architecture Patterns

### System Architecture Diagram (the injection flow this phase modifies)
```
                 generation entry points (UNCHANGED)
   wizards.py:134   mcp/screenwriting.py:86   ai_chat.py   review.py   breakdown.py
        │                  │                      │            │            │
        └──────────────────┴──────────┬───────────┴────────────┴───────────┘
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │  build_bible_context(db, project)        │  ◄── THE ONLY EDIT SITE
                  │  app/utils/bible_context.py              │
                  │                                          │
                  │  if project.show_id is None: return None │  (standalone film — UNCHANGED)
                  │  show = load Show                        │
                  │  parts = [ bible sections... ]           │  (UNCHANGED bible block)
                  │                                          │
                  │  ── NEW: branch on show.continuity_mode ─│
                  │  if connected:                           │
                  │    priors = query Project                │
                  │      .filter(show_id == show.id,         │
                  │              episode_number < current,   │
                  │              episode_summary truthy)     │
                  │      .order_by(episode_number.asc())     │  ◄── reliable key, NOT positional
                  │      [most-recent-N, skip empty]         │
                  │    parts += "## Prior Episodes" + priors │
                  │  # anthology / standalone: no priors     │
                  └───────────────────┬──────────────────────┘
                                      ▼  (returns prepended string — UNCHANGED contract)
            _build_project_context(..., bible_context=str)  template_ai_service.py:27 (UNCHANGED)
                                      ▼
            _generate_scripts / _generate_one_scene → ai_provider.chat_completion (UNCHANGED)
```

### Pattern 1: Append a new section to the bible-context list (mirror existing bible blocks)
**What:** Add a `## Prior Episodes` block to the `parts` list in `build_bible_context`, exactly as `### Season Arc` etc. are appended.
**When:** Only when `show.continuity_mode == "connected"` AND at least one prior summary is non-empty.
```python
# Source: extends app/utils/bible_context.py (existing append pattern, lines 40-50)
# inside build_bible_context, after the existing bible blocks, before `return`:
if show.continuity_mode == ContinuityMode.CONNECTED.value:  # str compare; column is VARCHAR
    priors = (
        db.query(Project)
        .filter(
            Project.show_id == str(show.id),
            Project.episode_number < project.episode_number,   # strictly prior
            Project.episode_summary.isnot(None),
        )
        .order_by(Project.episode_number.asc())                # RELIABLE KEY — never positional
        .all()
    )
    priors = [p for p in priors if (p.episode_summary or "").strip()]  # existence-gate (Phase 67 convention)
    priors = priors[-PRIOR_EPISODE_CAP:]                        # most-recent-N (recommend 8)
    if priors:
        parts.append("\n### Prior Episodes (for continuity)")
        for p in priors:
            stale = " (summary may be out of date)" if p.episode_summary_stale else ""
            parts.append(f"\n**Episode {p.episode_number}: {p.title}**{stale}\n{p.episode_summary.strip()}")
```
Note: `current episode_number` may be `None` for some episode rows — guard with `if project.episode_number is not None` before the `<` filter, else fall back to bible-only (no priors).

### Anti-Patterns to Avoid
- **Ordering episodes by anything other than `episode_number.asc()`** — positional/insertion/`created_at` ordering is the recurring project bug (Pitfall 1).
- **Editing `template_ai_service.py` or `openai_service.py` to branch on mode** — wrong layer; the mode branch belongs in the single `build_bible_context` helper. Editing generation loops duplicates logic across 5+ call sites.
- **Comparing `continuity_mode` to a Python enum object** — the column is `VARCHAR` (`String(20)`), so compare to `.value` strings or normalize. [VERIFIED: `database.py:109`, schemas comment "NOT a PG Enum".]
- **Raising / failing on missing/stale summary** — violates the graceful-degradation constraint.
- **Generating or regenerating summaries here** — that's Phase 69; this phase is read-only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Episode ordering | A custom sort over a fetched list | `.order_by(Project.episode_number.asc())` (precedent at `shows.py:182`) | The reliable integer key; positional sorting is the documented recurring bug |
| Standalone detection | New `show_id is None` checks scattered in generation code | Existing `build_bible_context` early-return (line 18-19) | One gate already exists and is tested |
| Stale gating | New flag logic | Existing `episode_summary_stale` column + the truthy-after-strip existence convention from Phase 67 | Convention already established and tested |
| Context prepending | New prompt-assembly code | `_build_project_context` already prepends `bible_context` | Zero downstream change |

**Key insight:** The entire phase is a localized extension of ONE 52-line helper plus one ORM query. Resist any urge to touch the generation loop — the existing `bible_context` string contract makes that unnecessary.

## Runtime State Inventory

Not a rename/refactor/migration phase — this is additive read-only behavior. **No runtime-state migration needed.** (Phase 67 already shipped the columns; no data backfill, no OS/service state, no secrets touched.) Explicitly verified: no new DB columns, no new env vars, no external service config.

## Common Pitfalls

### Pitfall 1: Positional / non-`episode_number` ordering of prior episodes
**What goes wrong:** Prior episodes injected out of true broadcast order → AI gets continuity in the wrong sequence → setups/payoffs scramble.
**Why it happens:** Defaulting to insertion order, `created_at`, or Python list index instead of the integer key. **This bug bit the project twice** (v6.0 WR-01, v7.0 ph50; MEMORY note "ScreenplayContent has no reliable order — join by episode_index only, never positionally").
**How to avoid:** `.order_by(Project.episode_number.asc())` — copy the exact precedent at `shows.py:182`. Add a test asserting injected order matches `episode_number` ascending even when rows are created/returned out of order.
**Warning signs:** Any `sorted(..., key=lambda: i)`, reliance on query result order without `order_by`, or `enumerate`-based ordering.

### Pitfall 2: Comparing the VARCHAR mode to a Python enum object
**What goes wrong:** `show.continuity_mode == ContinuityMode.CONNECTED` is `False` (str vs enum), so connected mode silently never triggers → SCONT-02 quietly fails, tests on the string pass-through still appear green.
**Why it happens:** `continuity_mode` is stored as `String(20)`, not a SQLAlchemy Enum (deliberate, per schemas comment — avoids `ALTER TYPE`).
**How to avoid:** Compare to `ContinuityMode.CONNECTED.value` (`"connected"`) or normalize the column value through the str-enum. Add a test with a real `connected` show row.

### Pitfall 3: Token blow-up on long connected seasons
**What goes wrong:** A 30-episode connected show injects 30 summaries → prompt exceeds `MAX_TOKENS`, generation degrades or errors.
**Why it happens:** No cap.
**How to avoid:** Cap to most-recent-N (recommend 8) by `episode_number`. Summaries are bounded (D2), so a count cap suffices. See Q4.

### Pitfall 4: `episode_number` is NULL on the current or a prior episode
**What goes wrong:** `Project.episode_number < None` is undefined/empty in SQL → either no priors or an error.
**Why it happens:** `episode_number` is nullable (`database.py:176`); standalone projects always have it NULL, and a malformed episode could too.
**How to avoid:** Guard: if `project.episode_number is None`, return bible-only (treat as no prior context). In the filter, prior rows with NULL `episode_number` are naturally excluded by the `<` comparison.

### Pitfall 5: Forgetting the `anthology`/`standalone` no-op is the *default* path
**What goes wrong:** Over-engineering a branch for every mode. Anthology behavior == current behavior == bible-only; standalone-show behavior == bible-only (and `show_id` NULL == None). Only `connected` adds anything.
**How to avoid:** Single `if connected:` block appended to the existing function; all other modes fall through unchanged. This makes SCONT-03 / SCONT-04 essentially "prove the connected block does NOT fire."

## Code Examples

### Reading the show + mode (existing pattern to extend)
```python
# Source: app/utils/bible_context.py:16-23 (VERIFIED, live)
def build_bible_context(db: Session, project: Project) -> Optional[str]:
    if not project.show_id:
        return None
    show = db.query(Show).filter(Show.id == str(project.show_id)).first()
    if not show:
        return None
    # show.continuity_mode is a VARCHAR: "connected" | "anthology" | "standalone"
```

### Correct prior-episode query (mirror of shows.py:181-182)
```python
# Source: app/api/endpoints/shows.py:181-182 (VERIFIED ordering precedent)
priors = (
    db.query(database.Project)
    .filter(database.Project.show_id == str(show_id))
    .order_by(database.Project.episode_number.asc())   # reliable integer key
    .all()
)
```

## State of the Art

| Old Approach (per ROADMAP text) | Current Reality (verified) | Impact |
|--------------------------------|----------------------------|--------|
| Generation prompt built in `openai_service.py` / anthropic | Built via `build_bible_context` → `_build_project_context` → `template_ai_service`; `openai_service.py` is review-only; no anthropic_service | Planner must target `app/utils/bible_context.py`, not `openai_service.py` |
| Provider is OpenAI GPT-4 (CLAUDE.md) | `AI_PROVIDER` defaults to `anthropic` / `claude-sonnet-4-6` | Irrelevant to this phase (injection is provider-agnostic), but note CLAUDE.md is stale |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Most-recent-N=8 count cap is sufficient; per-summary char clamp unnecessary | Q4 / Pitfall 3 | If Phase 69 summaries turn out long, 8 could still bloat — mitigated by adding a char clamp; planner should confirm N after seeing Phase 69's summary length budget |
| A2 | Stale summaries should be injected-with-marker rather than skipped | Q5 | Low — Phase 69 lazy-regen clears the flag before Phase 68 reads in the wired flow; either choice is safe |
| A3 | `standalone`-mode shows should still get the bible (just no cross-episode), matching `anthology` | SCONT-04 | ROADMAP success-criterion #3 says standalone injects "no cross-episode context" (silent on bible). Bible-only fallthrough satisfies it. If the intent is "no context AT ALL for standalone shows," planner must add an explicit early-return for `continuity_mode == standalone`. Recommend confirming. |

## Open Questions (RESOLVED at plan-phase, 2026-06-17)

1. **`standalone` show vs bible:** Should a `standalone`-mode *show* (distinct from a `show_id` NULL film) still receive its bible? **RESOLVED → YES** (bible-only, like anthology; only the `## Prior Episodes` block is suppressed). D-STANDALONE-BIBLE.
2. **Prior-episode cap N:** **RESOLVED → 8** (`PRIOR_EPISODE_CAP = 8`, most-recent-8 by `episode_number`). D-CAP.

Also resolved: **stale summaries** → injected WITH `(summary may be out of date)` marker, only null/empty/whitespace skipped (D-STALE).

## Environment Availability

Skipped — no external dependencies. Pure in-repo code/test change against already-installed SQLAlchemy / Pydantic / pytest. No CLI tools, services, or runtimes beyond the existing backend.

## Validation Architecture

`nyquist_validation` is enabled (config: `true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ `unittest.mock` `patch`/`AsyncMock`) |
| Config file | none detected at root; tests run via `pytest app/tests/...` from `backend/` with venv active (CLAUDE.md) |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_bible_injection.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest` |

### Testable Seams (HIGH — pure-function injection)
The phase's core is `build_bible_context`, a **synchronous pure-ish function** (takes `db` + `project`, returns a string). This is the ideal seam: unit-test it directly against `db_session` fixtures without any LLM call, asserting on the returned string. End-to-end, mock `app.services.template_ai_service.chat_completion` (pattern from `test_continuity_generation.py`) and assert the assembled `project_context` contains/omits prior-episode text.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCONT-02 | connected: season arc + prior summaries present, ordered by `episode_number` (assert order with out-of-order rows) | unit | `pytest app/tests/test_bible_injection.py -k connected -x` | ❌ Wave 0 (extend existing file) |
| SCONT-02 | connected order is by `episode_number`, NOT positional (insert rows out of order) | unit | `pytest app/tests/test_bible_injection.py -k order -x` | ❌ Wave 0 |
| SCONT-03 | anthology: bible present, NO prior-episode text | unit | `pytest app/tests/test_bible_injection.py -k anthology -x` | ❌ Wave 0 |
| SCONT-04 | standalone show + `show_id` NULL: no cross-episode context | unit | `pytest app/tests/test_bible_injection.py -k standalone -x` | ❌ Wave 0 |
| SCONT-02 (degrade) | connected with missing/empty/stale prior summaries still returns (no error), skips empties | unit | `pytest app/tests/test_bible_injection.py -k degrade -x` | ❌ Wave 0 |
| SCONT-02 (cap) | connected with >N priors injects only most-recent-N | unit | `pytest app/tests/test_bible_injection.py -k cap -x` | ❌ Wave 0 |
| No-regression | existing bible-injection + continuity-generation tests stay green | unit | `pytest app/tests/test_bible_injection.py app/tests/test_continuity_generation.py` | ✅ exists |

### Sampling Rate
- **Per task commit:** `pytest app/tests/test_bible_injection.py -x`
- **Per wave merge:** `pytest app/tests/test_bible_injection.py app/tests/test_continuity_generation.py app/tests/test_shows_api.py app/tests/test_episode_summary_staleness.py`
- **Phase gate:** full suite green (tolerating the 4 documented pre-existing flakes per ROADMAP §65) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] Extend `backend/app/tests/test_bible_injection.py` — add `TestContinuityModeInjection` covering SCONT-02/03/04 + degrade + cap + ordering. (No new framework install; file + fixtures already exist.)
- [ ] Confirm `db_session` fixture can create a `Show` with `continuity_mode` and multiple `Project` episodes with `episode_number` + `episode_summary` (it already creates shows/projects per existing tests).

## Security Domain

`security_enforcement` not present in config → treated as enabled. Light surface for this phase.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unchanged; generation endpoints already auth via `get_current_user` / `sa_` gateway |
| V4 Access Control | yes (indirect) | The prior-episode query MUST stay scoped to the SAME `show_id` (which is owner-scoped at the endpoint). Do NOT widen the query beyond the project's own show — never inject another show's/user's episode summaries |
| V5 Input Validation | minimal | `continuity_mode` is constrained by the `ContinuityMode` enum on write (Phase 67); read path just string-compares |
| V6 Cryptography | no | n/a |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-show / cross-user summary leakage into a prompt | Information Disclosure | Filter prior episodes strictly by `show_id == project.show_id`; the endpoint already owner-scopes the project, and `episode_summary` text stays internal (D-04 — never returned in any API response, only embedded in the LLM prompt) |
| Prompt-injection via episode_summary content | Tampering | Out of scope here (summaries are AI-generated internal text, Phase 69); no user-supplied free text added by this phase beyond what already flows through bible fields |

## Sources

### Primary (HIGH confidence — live source read)
- `backend/app/utils/bible_context.py` (full) — the injection site
- `backend/app/services/template_ai_service.py` lines 16–58, 477–530 — context assembly + generation loop
- `backend/app/services/openai_service.py` (full) — confirmed review-only, NOT generation
- `backend/app/services/ai_provider.py` + `backend/app/config.py:16,24` — provider default = anthropic
- `backend/app/models/database.py:91-176` — Show.continuity_mode (VARCHAR), Project.{episode_summary, episode_summary_stale, show_id, episode_number}
- `backend/app/models/schemas.py:916-963` — ContinuityMode str-enum, Show schemas
- `backend/app/api/endpoints/shows.py:181-219` — episode ordering precedent + auto-increment
- `backend/app/api/endpoints/wizards.py`, `app/mcp_server/tools/screenwriting.py` — call-chain confirmation
- `.planning/phases/67-continuity-data-model-migration/67-03-SUMMARY.md` — existence-gated stale convention
- `.planning/ROADMAP.md §Phase 67/68`, `.planning/REQUIREMENTS.md` (SCONT-02/03/04), `.planning/v10.0-SHOW-TYPE-VISION.md` (D1-D5)
- grep of `bible_context` across `backend/app/` — 30+ call sites, all via `build_bible_context`

### Secondary
- `MEMORY.md` — recurring positional-ordering bug (v6.0/v7.0)

## Metadata

**Confidence breakdown:**
- Injection site / call chain: HIGH — directly read all files; verified the ROADMAP's `openai_service.py` claim is wrong
- Ordering pattern: HIGH — exact in-repo precedent at `shows.py:182`
- Mode branching: HIGH — column type and enum verified
- Token cap (N=8): MEDIUM/ASSUMED — depends on Phase 69 summary length (not yet shipped)
- Graceful-degradation policy: HIGH on mechanism, MEDIUM on inject-vs-skip choice (planner locks)

**Research date:** 2026-06-17
**Valid until:** until Phase 68 plan is written (internal-codebase facts are stable; only the N=8 cap and the standalone-bible question need a planner decision)
