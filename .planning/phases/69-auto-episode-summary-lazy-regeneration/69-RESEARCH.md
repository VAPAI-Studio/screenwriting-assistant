# Phase 69: Auto Episode Summary & Lazy Regeneration - Research

**Researched:** 2026-06-17
**Domain:** AI text summarization + lazy regeneration over the existing provider abstraction; integration into the Phase 68 connected-mode read path
**Confidence:** HIGH (codebase verified end-to-end; no new external dependencies)

## Summary

Phase 69 closes the v10.0 continuity loop: every completed episode gets an AI-generated `episode_summary` (ESUM-01), and any summary marked stale by Phase 67's `episode_summary_stale` flag is regenerated **just-in-time** before it is read as prior-episode context for a *later* episode (ESUM-03). The data columns (`projects.episode_summary` TEXT, `projects.episode_summary_stale` Boolean) already exist (Phase 67), the staleness hook already fires on edit (Phase 67, ESUM-02), and the read site already injects prior summaries with a `(summary may be out of date)` marker (Phase 68). Phase 69 supplies the missing write path (initial generation) and the regenerate-before-read path.

The decisive architectural fact: `build_bible_context()` in `backend/app/utils/bible_context.py` is **synchronous** and is called from ~14 sites, most of them sync. But the connected-mode generation read site (`wizards.py::run_wizard`) computes `bible_context` **synchronously in the request handler and freezes it into a string** that is then handed to an `async` background task (`_run_wizard_background`). An AI regeneration call cannot safely live inside the sync `build_bible_context`. The clean seam is to perform lazy regen as an **async pre-pass inside the async generation path** (the background task / generation services), BEFORE the sync `build_bible_context` reads the rows — so the sync helper still just reads `episode_summary` text, but by the time it runs the stale priors have been refreshed and their flags cleared. This also neatly preserves Phase 68's marker path as the **failure fallback**: if regen fails, the flag stays True and Phase 68 injects the stale text with its existing marker.

**Primary recommendation:** Two distinct triggers, one shared summarizer. (1) **Initial generation = eager, on an explicit "complete episode" action** (satisfies ESUM-01 SC-1 literally). (2) **Regeneration of stale = lazy, an async pre-pass over strictly-prior episodes run at the start of the connected-mode generation flow**, before `build_bible_context` reads them. Build one `summarize_episode(db, project) -> str` service method on `template_ai_service` (provider-agnostic via `chat_completion`, `json_mode=False`, bounded ~250-word / `max_tokens≈500` target), used by both triggers. Read the episode's source text from `ScreenplayContent.content` joined **by `episode_index` only, never positionally** (project memory — this bug bit twice).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Generate `episode_summary` from screenplay text | API / Backend service (`template_ai_service`) | AI provider (`ai_provider.chat_completion`) | Summarization is business logic over stored screenplay; routes through the existing provider abstraction |
| Persist summary + clear stale flag | Database / Storage | API endpoint (owns the commit) | Same `*_stale` write pattern as breakdown/shotlist; helper must not commit (caller commits — Phase 67 convention) |
| Decide WHEN to (re)generate | API / Backend (endpoint for eager; generation flow for lazy) | — | Eager trigger is an explicit user/endpoint action; lazy trigger is a pre-pass in the connected-mode generation path |
| Read prior summaries into the prompt | API / Backend (`bible_context.py`) | — | Already built (Phase 68); stays a pure synchronous reader |
| Read episode source text to summarize FROM | Database / Storage (`ScreenplayContent`) | — | Join strictly by `formatted_content.episode_index`, never positional |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ESUM-01 | When an episode is completed, the AI generates and stores a summary (`episode_summary`) | New `summarize_episode` service method + an explicit "complete/generate summary" trigger; reads `ScreenplayContent.content` by `episode_index`; writes `episode_summary`, sets `episode_summary_stale=False`, caller commits |
| ESUM-03 | A stale summary is regenerated before it is used as context for later episodes (lazy regeneration) | Async pre-pass over strictly-prior episodes (same query shape as `_build_prior_episodes_block`) run before the sync `build_bible_context` read; regenerates ONLY rows with `episode_summary_stale=True` AND a non-empty existing summary; clears the flag on success; on failure leaves the flag set so Phase 68's marker path degrades gracefully |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `app.services.ai_provider.chat_completion` | in-repo | Provider-agnostic text generation (OpenAI/Anthropic) | Already the single chokepoint for every text-gen call (`template_ai_service` uses it throughout) `[VERIFIED: codebase]` |
| SQLAlchemy ORM (`Project`, `ScreenplayContent`) | in-repo | Read source text, write summary + flag | Existing models; `episode_summary`/`episode_summary_stale` already on `Project` `[VERIFIED: database.py:171-172]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `chat_completion_structured` | in-repo | Structured/JSON output | NOT needed — summary is plain prose. Use `chat_completion(json_mode=False)` (mirrors `_update_synopsis`) `[VERIFIED: template_ai_service.py:287]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `chat_completion(json_mode=False)` | `chat_completion_structured` with a `{summary: str}` model | Adds schema overhead for a single prose field; the synopsis precedent (`_update_synopsis`) uses plain prose — match it |
| Eager-on-complete + lazy-regen (two triggers) | Pure lazy (generate-on-first-read for both initial and regen) | Pure lazy fails ESUM-01 SC-1's literal "Completing an episode generates a summary"; also makes the first connected generation pay N summary calls at once. Two triggers is cleaner and cheaper. |

**Installation:** None — no new packages. (No `## Package Legitimacy Audit` required: phase installs zero external packages.)

## Architecture Patterns

### System Architecture Diagram

```
ESUM-01 (eager, initial)
  "Complete episode" action (endpoint, async)
        │
        ▼
  summarize_episode(db, project)
        │  reads ScreenplayContent.content  ── joined by episode_index ONLY
        ▼
  chat_completion(json_mode=False, max_tokens≈500)  ──► provider (anthropic default / openai)
        │
        ▼
  project.episode_summary = text ; project.episode_summary_stale = False
        │
        ▼
  db.commit()  (caller commits — helper does not)


ESUM-03 (lazy, regenerate-before-read)
  Connected-mode generation for episode N (wizards.py::run_wizard, async path)
        │
        ▼
  [NEW] async pre-pass: query strictly-prior episodes (episode_number < N, this show)
        │     for each prior P where episode_summary_stale AND episode_summary non-empty:
        │         summarize_episode(db, P)  ──► refresh text, set stale=False
        │         on AI failure: log, leave stale=True (DO NOT raise)
        │     db.commit()
        ▼
  build_bible_context(db, project_N)   ← SYNC, unchanged: now reads fresh summaries
        │     (any still-stale prior — i.e. regen failed — keeps Phase 68 marker)
        ▼
  frozen bible_context string → _run_wizard_background → generation
```

### Recommended Project Structure
```
backend/app/
├── services/
│   └── template_ai_service.py   # ADD: async summarize_episode(db, project) -> str
├── utils/
│   ├── bible_context.py         # UNCHANGED (stays a sync reader); marker path is the fallback
│   └── episode_summary.py       # NEW (optional): regen helpers (read-source-by-index, regen-priors pre-pass)
└── api/endpoints/
    ├── wizards.py               # WIRE: call the lazy pre-pass before build_bible_context in connected mode
    └── phase_data.py | wizards  # WIRE: eager "complete episode" trigger calls summarize_episode
```

### Pattern 1: Bounded prose summary via the provider abstraction (mirror `_update_synopsis`)
**What:** A single `summarize_episode` async method that loads the episode's scene text, calls `chat_completion` with a bounded prompt, and returns prose. Never the full script (D2), never JSON.
**When to use:** Both the eager and lazy triggers call this.
**Example:**
```python
# Pattern source: backend/app/services/template_ai_service.py::_update_synopsis (verified)
WORD_CAP = 250  # bounded — D2 says NOT the full prior script; bounds prompt size on long seasons

async def summarize_episode(self, db, project) -> str:
    scene_text = _read_episode_text_by_index(db, project.id)  # join by episode_index ONLY
    if not scene_text.strip():
        return ""  # nothing to summarize; caller decides whether to write
    prompt = f"""Summarize this episode's screenplay for use as continuity context when
writing LATER episodes of the same series. Capture: what happened (plot beats), changes in
character state/relationships, and any setups left unresolved. Be factual and concise.
Stay under {WORD_CAP} words. Prose only — no headings, no bullet lists, no JSON.

Episode: {project.title}
{scene_text}

Return only the summary prose."""
    text = await chat_completion(
        messages=[
            {"role": "system", "content": "You are a precise story editor who writes concise, factual episode summaries for series continuity."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=500,
        json_mode=False,
    )
    return (text or "").strip()
```

### Pattern 2: Read source text by `episode_index` (NOT positional)
**What:** Reconstruct the episode's screenplay from `ScreenplayContent` rows aligned by `formatted_content.episode_index`.
**Why:** PROJECT MEMORY — `ScreenplayContent` has NO reliable order; positional joins bit the project twice (v6.0 WR-01, v7.0 ph50). `created_at` is only second-resolution on SQLite, so insertion order is not recoverable.
**Example:**
```python
# Pattern source: breakdown_service._align_screenplay_to_scenes (verified, lines 204-252)
def _read_episode_text_by_index(db, project_id) -> str:
    rows = (db.query(ScreenplayContent)
              .filter(ScreenplayContent.project_id == str(project_id))
              .order_by(ScreenplayContent.created_at.desc(), ScreenplayContent.id.desc())
              .all())
    by_index = {}
    for r in rows:
        idx = (getattr(r, "formatted_content", None) or {}).get("episode_index")
        if idx is None or not r.content:
            continue
        by_index.setdefault(idx, r.content)  # first wins = newest (rows are newest-first)
    return "\n\n".join(by_index[i] for i in sorted(by_index))
```

### Pattern 3: Lazy regen pre-pass — same query shape as Phase 68, in the async path
**What:** Before connected-mode generation reads priors, regenerate the stale ones.
```python
# Query MUST mirror bible_context._build_prior_episodes_block (verified, lines 45-54)
async def regenerate_stale_priors(db, show, project) -> None:
    if project.episode_number is None:
        return
    stale_priors = (db.query(Project)
        .filter(Project.show_id == str(show.id),
                Project.episode_number < project.episode_number,
                Project.episode_summary.isnot(None),
                Project.episode_summary_stale.is_(True))
        .order_by(Project.episode_number.asc())
        .all())
    for p in stale_priors:
        if not (p.episode_summary or "").strip():
            continue  # existence-gate (Phase 67 convention)
        try:
            fresh = await svc.summarize_episode(db, p)
            if fresh:
                p.episode_summary = fresh
                p.episode_summary_stale = False
        except Exception as e:
            logger.warning("Lazy episode-summary regen failed for ep %s: %s", p.episode_number, e)
            # leave stale=True → Phase 68 injects with the existing marker (graceful degrade)
    db.commit()
```

### Anti-Patterns to Avoid
- **Putting an AI call inside `build_bible_context`:** It is sync and called from ~14 sites (review, ai_chat, breakdown, mcp tools). An `await` there would force async-converting every caller and risk blocking. Keep it a pure reader.
- **Positional join of `ScreenplayContent`:** Forbidden by project memory. Always `episode_index`.
- **Regenerating up-to-date summaries:** SC-3 forbids it. Filter `episode_summary_stale.is_(True)` AND existing non-empty summary.
- **Letting regen failure abort generation:** ESUM-03/Phase 68 must degrade. Catch per-episode, leave the flag, fall through to the marker path.
- **Committing inside the summarizer helper:** Phase 67 convention is caller-commits. The summarizer returns text; the trigger writes + commits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Provider selection (OpenAI vs Anthropic) | A new client/branch | `ai_provider.chat_completion(...)` | Single existing chokepoint; handles system-prompt separation, JSON fences, streaming `[VERIFIED: ai_provider.py]` |
| Bounded re-summarization prompt | A novel prompt | Mirror `_update_synopsis` (word cap + prose-only + failure-returns-prior) | Proven pattern in the same service `[VERIFIED: template_ai_service.py:253-303]` |
| Scene-text reconstruction | Positional concat | `episode_index` align (breakdown_service pattern) | Recurring ordering bug; helper already exists to copy `[VERIFIED: breakdown_service.py:204]` |
| Stale-flag write semantics | New convention | Mirror `_mark_episode_summary_stale` / breakdown_stale (existence-gated, caller commits) | Consistency with Phase 67 `[VERIFIED: 67-03-SUMMARY.md]` |

**Key insight:** Every piece Phase 69 needs already has a verified in-repo precedent. The phase is wiring, not invention.

## Runtime State Inventory

> Phase 69 is additive (new write/regen logic), not a rename/refactor. No stored keys, OS registrations, secrets, or build artifacts change.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `projects.episode_summary` / `episode_summary_stale` already exist (Phase 67 migration 011). This phase populates them. | None — columns exist; phase writes values |
| Live service config | None — no external service stores this string | None |
| OS-registered state | None | None |
| Secrets/env vars | Uses existing `AI_PROVIDER` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — no new keys | None |
| Build artifacts | None | None |

## Common Pitfalls

### Pitfall 1: Sync/async mismatch at the read site
**What goes wrong:** Attempting lazy regen inside `build_bible_context` (sync) forces an `await`, breaking ~14 callers.
**Why it happens:** ESUM-03 says "before it is used" and the obvious place looks like the reader.
**How to avoid:** Regen is an async pre-pass in the connected-mode generation flow (`wizards.py::run_wizard`, already `async`), executed BEFORE the sync `build_bible_context(db, project)` call. The reader stays pure.
**Warning signs:** A diff that changes `build_bible_context`'s signature to `async def`, or adds `await` to it.

### Pitfall 2: Context frozen before regen
**What goes wrong:** `wizards.py::run_wizard` computes `bible_context` as a string at line 134 and passes it to the background task. If regen runs only inside the background task after the string is built, it has no effect on this run.
**Why it happens:** The context is materialized in the request handler, not in the generation loop.
**How to avoid:** Run the regen pre-pass in the request handler immediately BEFORE line 134's `build_bible_context(db, project)` — or move both into a small helper that regenerates-then-builds. The pre-pass commits; then `build_bible_context` reads fresh rows.
**Warning signs:** Tests show prior summaries still carry the `(summary may be out of date)` marker after a connected generation of a later episode.

### Pitfall 3: Positional `ScreenplayContent` read
**What goes wrong:** Summary built from scenes in the wrong order → garbage continuity. Already bit the project twice.
**How to avoid:** Join by `formatted_content.episode_index` only (Pattern 2).
**Warning signs:** No `episode_index` lookup in the source-text reader; a `.order_by(created_at)` used as the *content order* rather than as a tiebreaker.

### Pitfall 4: Regenerating non-stale or summary-less episodes
**What goes wrong:** Burns tokens / disturbs good summaries (violates SC-3), or writes an empty summary.
**How to avoid:** Filter `episode_summary_stale.is_(True)` AND `(episode_summary or "").strip()` truthy. Initial generation (ESUM-01) is the only path that writes a *first* summary.
**Warning signs:** A test where an up-to-date prior's summary text changes after generating a later episode.

### Pitfall 5: Concurrent double-regen
**What goes wrong:** Two later episodes generated near-simultaneously both see the same stale prior and both regenerate it (duplicate AI cost; last-write-wins, no corruption).
**Why it happens:** No lock between the read and the flag-clear.
**How to avoid (MVP):** Accept best-effort — last write wins, both produce valid summaries, no data corruption (idempotent in outcome). If a guard is wanted later, a `SELECT ... FOR UPDATE SKIP LOCKED` on the prior rows or a per-project advisory lock. Recommend documenting it as accepted best-effort for the internal-tool MVP; do NOT over-engineer.
**Warning signs:** None functionally harmful for MVP; only a cost concern.

### Pitfall 6: Regen failure aborting generation
**What goes wrong:** An AI error in the pre-pass bubbles up and fails the user's episode generation.
**How to avoid:** Per-episode try/except in the pre-pass; on failure leave `episode_summary_stale=True` so Phase 68 injects the stale text WITH its marker. Generation always proceeds.
**Warning signs:** No try/except around `summarize_episode` in the pre-pass; an exception type that escapes the loop.

## Code Examples

(See Patterns 1-3 above — all derived from verified in-repo precedents:
`template_ai_service.py::_update_synopsis`, `breakdown_service.py::_align_screenplay_to_scenes`,
`bible_context.py::_build_prior_episodes_block`.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLAUDE.md "OpenAI GPT-4" | `AI_PROVIDER` defaults to `anthropic` / `claude-sonnet-4-6`; OpenAI default `gpt-4o` | config.py current | Summary gen must be provider-agnostic via `chat_completion` (do not hardcode OpenAI) `[VERIFIED: config.py:16,24]` |
| Phase 68: inject stale prior WITH marker | Phase 69: regenerate stale prior before read; marker path becomes the *failure fallback* | This phase | Phase 68 behavior is NOT removed — it becomes the graceful-degradation path when regen fails or is skipped |

**Deprecated/outdated:**
- CLAUDE.md "AI: OpenAI API (GPT-4)" line is stale (noted in Phase 68 research). Trust `config.py`.

## Trigger-Point Resolution (the ROADMAP open question)

**Recommendation: TWO triggers, ONE summarizer.**

- **Initial summary (ESUM-01) = EAGER, on an explicit "complete episode" action.** ESUM-01 SC-1 literally says "Completing an episode generates a summary." There is no existing single "complete episode" endpoint (the closest lifecycle signal is wizard `status="completed"` on a *run*, not the episode). The planner should pick the concrete trigger surface — recommended: a dedicated endpoint (e.g. `POST /api/projects/{id}/summary` or a "complete episode" action) that calls `summarize_episode`, writes the text, sets `episode_summary_stale=False`, commits. This also gives the frontend/MCP a clean call. Eager generation means the first connected generation does not pay N summary calls at once.
- **Regeneration of stale (ESUM-03) = LAZY**, the async pre-pass before the connected-mode read (Pattern 3). Only stale + already-existing summaries are touched.

These are genuinely two paths sharing one `summarize_episode` method: initial = "no summary yet, user completed it"; regen = "summary exists but stale, a later episode needs it now." The existence-gate (`episode_summary` non-empty) is exactly what distinguishes them and is already the Phase 67 convention.

**Lazy-regen hook location (ESUM-03):** In `backend/app/api/endpoints/wizards.py::run_wizard`, immediately before line 134 (`bible_context = build_bible_context(db, project)`), gated on connected mode — run `regenerate_stale_priors(db, show, project)` (Pattern 3), which commits, then let the existing sync `build_bible_context` read the now-fresh rows. The same guard belongs at any OTHER connected-mode generation read site that should consume fresh summaries (review.py:58, ai_chat generation paths, mcp screenwriting tool) — the planner should decide scope; the *generation* path (wizards) is the mandatory one per ESUM-03 ("used as context for later episodes").

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The "complete episode" action for ESUM-01 should be a NEW explicit endpoint/action (none exists today) | Trigger-Point Resolution | If the user expects auto-on-some-existing-event, the trigger surface differs — confirm at discuss/plan. Low risk: any chosen surface calls the same `summarize_episode`. |
| A2 | ~250-word / `max_tokens≈500` is the right summary bound | Pattern 1 | Too short loses continuity detail; too long bloats connected prompts. Tunable constant; mirror `_update_synopsis`'s 400-word/700-token synopsis as a reference. |
| A3 | Concurrent double-regen is acceptable best-effort for MVP | Pitfall 5 | If two later episodes are generated simultaneously a prior may be summarized twice (cost only, no corruption). Acceptable for an internal tool. |
| A4 | Lazy regen scope = the generation read site (wizards) is mandatory; other read sites (review/ai_chat/mcp) optional | Lazy-regen hook | If review (Phase 71) must also see fresh summaries, add the pre-pass there too — but that is arguably Phase 71's concern. |

## Open Questions (RESOLVED at plan-phase, 2026-06-17)

1. **Exact "complete episode" trigger surface** — **RESOLVED → dedicated owner-scoped endpoint** `POST /api/projects/{id}/episode-summary` calling `summarize_episode` (D-TRIGGER). ESUM-01 SC-1 wants completion → summary; no single endpoint existed, so we add one.
2. **Should review (Phase 71) / ai_chat / MCP read sites also trigger lazy regen?** — **RESOLVED → NO, generation path only this phase** (D-REGEN-SCOPE). Wire the wizards generation path in Phase 69; review/ai_chat/MCP are out of scope, left for Phase 71+.

Also locked: **regen failure → fall back to Phase 68's stale-with-marker injection, flag stays True, generation never fails** (D-REGEN-FAIL).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| AI provider (Anthropic default) | summary text gen | ✓ (configured; `AI_PROVIDER=anthropic`, `claude-sonnet-4-6`) | per config.py | OpenAI `gpt-4o` if `AI_PROVIDER=openai` |
| `ScreenplayContent` rows with `episode_index` | source text to summarize | ✓ (v6.0+ generation writes `formatted_content.episode_index`) | — | If no `episode_index` rows: summary source is empty → write empty/skip; existence-gate prevents bad data |

No new external dependency. No `## Package Legitimacy Audit` (zero installs).

## Validation Architecture

> `workflow.nyquist_validation` not explicitly false → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (SQLite-backed `db_session`, `client`, `mock_auth_headers` fixtures) |
| Config file | none — fixtures in existing test modules (`test_episode_summary_staleness.py`, `test_bible_injection.py`) |
| Quick run command | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/test_episode_summary.py -q` |
| Full suite command | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ESUM-01 | Completing an episode generates + stores a summary; stale flag cleared | unit (mock `chat_completion`) | `pytest app/tests/test_episode_summary.py -k initial -x` | ❌ Wave 0 |
| ESUM-01 | Source text read by `episode_index`, never positional (insert rows out-of-order) | unit | `pytest app/tests/test_episode_summary.py -k by_index -x` | ❌ Wave 0 |
| ESUM-03 | Stale prior regenerated before connected read; flag cleared; marker gone | integration (mock provider) | `pytest app/tests/test_episode_summary.py -k lazy_regen -x` | ❌ Wave 0 |
| ESUM-03 | Up-to-date prior NOT regenerated (SC-3) | unit | `pytest app/tests/test_episode_summary.py -k preserves_fresh -x` | ❌ Wave 0 |
| ESUM-03 | Regen failure → flag stays True, Phase 68 marker injected, generation proceeds | unit (provider raises) | `pytest app/tests/test_episode_summary.py -k regen_failure -x` | ❌ Wave 0 |
| ESUM-03 | Summary-less prior is not regenerated (existence-gate) | unit | `pytest app/tests/test_episode_summary.py -k existence_gate -x` | ❌ Wave 0 |

**Testable seams:** (1) `summarize_episode(db, project)` — mock `chat_completion`, assert prompt is bounded & prose-only and returns stripped text. (2) `_read_episode_text_by_index` — insert `ScreenplayContent` rows with shuffled `episode_index`, assert reconstructed order. (3) `regenerate_stale_priors` — seed mixed stale/fresh priors, assert only stale-with-summary touched, flags cleared, failure leaves flag. (4) End-to-end: connected `build_bible_context` after pre-pass shows fresh text and no marker for regenerated priors.

### Sampling Rate
- **Per task commit:** quick run on `test_episode_summary.py`
- **Per wave merge:** full suite (expect the 5 documented pre-existing failures: test_mcp_foundation / test_session_isolation / test_yolo_integration — out of scope)
- **Phase gate:** full suite green (minus the 5 known) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_episode_summary.py` — covers ESUM-01 + ESUM-03 (reuse `test_episode_summary_staleness.py` / `test_bible_injection.py` fixtures and the `Show`/`Project`/`ScreenplayContent` setup helpers there)
- [ ] A `chat_completion` mock/patch helper (patch `app.services.template_ai_service.chat_completion`) so summary tests are deterministic and offline

## Security Domain

> `security_enforcement` absent = enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Reuse existing `get_current_user` / API-key gateway on any new endpoint (eager trigger) |
| V3 Session Management | no | No new session surface |
| V4 Access Control | yes | Owner-scope every query: new endpoint must filter `Project.owner_id == current_user.id` (mirror existing wizards.py); regen pre-pass already scoped to `project.show_id` |
| V5 Input Validation | yes | Source text comes from owner's own stored screenplay; summary is bounded (`max_tokens`); no new free-text user input path |
| V6 Cryptography | no | None |

### Known Threat Patterns for FastAPI + AI summarization

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-user summary read/write (summarizing another user's episode) | Information Disclosure / Tampering | Owner-scope the eager endpoint; regen pre-pass scoped to `project.show_id` (same show, same owner) — mirror Phase 68 T-68-01 |
| Prompt-injection via screenplay content into the summary | Tampering | Low risk (owner summarizing own content for own later episodes); summary is bounded prose, not executed; no elevated action taken on its content |
| Token blow-up on long seasons | DoS | Bounded summary (`~250 words`) + Phase 68's `PRIOR_EPISODE_CAP=8` already bound the connected prompt |
| Info disclosure of summary text via API | Information Disclosure | Phase 67 D-04: `episode_summary_stale` is read-surfaced but the `episode_summary` TEXT is intentionally NOT on the Project read schema — preserve this; if the new endpoint returns the summary, it returns only the owner's own |

## Sources

### Primary (HIGH confidence)
- `backend/app/utils/bible_context.py` — sync reader, `_build_prior_episodes_block` query shape, `STALE_SUMMARY_MARKER`, `PRIOR_EPISODE_CAP=8`
- `backend/app/services/ai_provider.py` — `chat_completion(json_mode, provider)`, OpenAI/Anthropic branching
- `backend/app/services/template_ai_service.py` — `_update_synopsis` bounded-prose precedent (lines 253-303), `chat_completion` usage
- `backend/app/services/breakdown_service.py` — `_align_screenplay_to_scenes` episode_index join (lines 204-252)
- `backend/app/models/database.py` — `Project.episode_summary/episode_summary_stale` (171-172), `ScreenplayContent` (298-308)
- `backend/app/api/endpoints/wizards.py` — `run_wizard` computes bible_context at 134, freezes into async `_run_wizard_background` (61-113)
- `backend/app/config.py` — `AI_PROVIDER=anthropic` default, models, `MAX_TOKENS`
- `.planning/phases/67-.../67-03-SUMMARY.md` — existence-gated stale helper, caller-commits, D-04 info-disclosure
- `.planning/phases/68-.../68-01-SUMMARY.md` — Phase 68 marker path, prior-episode query, "seam where lazy regen will clear stale"
- `.planning/v10.0-SHOW-TYPE-VISION.md` — D2/D3 locked decisions
- `.planning/ROADMAP.md` §Phase 69; `.planning/REQUIREMENTS.md` ESUM-01/03

### Secondary (MEDIUM confidence)
- None required — all claims verified in-repo.

### Tertiary (LOW confidence)
- None.

## Project Constraints (from CLAUDE.md)
- Provider-agnostic AI calls via `ai_provider.py` (CLAUDE.md "OpenAI GPT-4" is stale; `AI_PROVIDER` defaults to anthropic).
- Tests use `Bearer mock-token`; run `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest`.
- Magic numbers (word cap, max_tokens) belong with the other tunables; backend keeps constants near usage (mirror `_update_synopsis`'s inline `word_cap`).
- 5 pre-existing test failures (test_mcp_foundation/test_session_isolation/test_yolo_integration) are out of scope.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; every primitive verified in-repo.
- Architecture / trigger + hook: HIGH — sync/async boundary and the frozen-context fact verified by reading `wizards.py`.
- Pitfalls: HIGH — derived from verified code + project memory (ScreenplayContent ordering).

**Research date:** 2026-06-17
**Valid until:** 2026-07-17 (stable; no fast-moving external deps)
