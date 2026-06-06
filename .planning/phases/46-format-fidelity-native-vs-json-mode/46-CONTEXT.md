# Phase 46: Format Fidelity (Native vs JSON Mode) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (user unattended; grey areas decided by Claude with codebase-grounded rationale, recorded below for review)

<domain>
## Phase Boundary

Screenplay output preserves industry-standard formatting (scene headings, action, character cues, parentheticals, dialogue). The script-generation call shape — currently `json_mode=True` returning `{title, content}` where `content` is a single JSON-string-encoded screenplay — is evaluated against a native (non-JSON) output path, and the path that yields better formatting is adopted (FMT-01, FMT-02).

**In scope:**
- The scene-writing `chat_completion` call inside `_generate_scripts` (backend/app/services/template_ai_service.py).
- Preserving the existing return contract: each screenplay item still exposes `{title, content, episode_index}`, and `_generate_scripts` still returns `{"screenplays": [...], "synopsis": ...}` (Phase 45 contract — must not break wizards.py persistence or downstream breakdown/shotlist staleness).

**Out of scope (deferred / other phases):**
- Character voice (Phase 47), craft guidance (Phase 48), side-by-side compare UI (Phase 49).
- Any frontend rendering change — this phase is backend generation-path only. The frontend already renders `content` as preformatted text; this phase only changes how `content` is produced, not how it is displayed.
- No DB schema change, no migration.
</domain>

<decisions>
## Implementation Decisions

### D-46-01 — Adopt native text output for the screenplay body; derive title separately (DECIDED: native-with-separate-title)
**Grey area:** FMT-02 asks to evaluate native vs json_mode and adopt the better one. The two were: (a) keep `json_mode=True` `{title, content}`; (b) go fully native and parse a title heuristically.
**Decision:** Move the scene-writing call to **native output** (`json_mode=False`) for the screenplay body, and obtain the title cheaply without JSON-wrapping the screenplay. Rationale: json_mode forces the entire multi-line screenplay through JSON string-encoding (`\n` escaping, quote escaping), which (1) spends output tokens on JSON syntax instead of screenplay text — raising truncation risk against the 4000-token cap on long scenes, and (2) biases the model toward "emit a JSON value" rather than "lay out a screenplay," the exact degradation FMT-01 names. The provider layer already strips code fences and the Phase 45 synopsis call already uses `json_mode=False` successfully, so native prose is a proven shape in this codebase.
**Title handling (Claude's Discretion, locked here to keep the per-screenplay contract intact):** Prefer a single native call that returns a short title line followed by the screenplay body under a clear, parseable delimiter (e.g. a `TITLE:` first line, then the screenplay). Parse the title off the top and treat the remainder as `content`. If the title line is absent/empty, fall back to the scene `summary` as the title (never fail the scene over a missing title). Planner may instead choose a tiny second `chat_completion` title call if cleaner — but the verbatim screenplay body must come from a native (non-JSON) generation, and the per-screenplay `{title, content, episode_index}` dict must be preserved exactly.

### D-46-02 — Strengthen the formatting instruction in the prompt (DECIDED: explicit fountain-style layout rules)
**Grey area:** Whether adopting native output alone is enough, or the prompt should also assert formatting rules.
**Decision:** Along with native output, make the prompt explicitly demand industry-standard layout: scene heading line (INT./EXT. LOCATION - TIME) on its own line, action in present tense, character cues in CAPS centered-by-convention, parentheticals on their own line, dialogue beneath the cue, blank line between elements. Rationale: FMT-01 is about the *output preserving* formatting; the most reliable lever is an unambiguous instruction plus an output channel (native) that doesn't fight the layout. Do NOT introduce a new screenplay-markup dependency (no fountain/Final Draft library) — plain text with conventional layout is sufficient for this internal tool and keeps the frontend's existing preformatted-text rendering valid.

### D-46-03 — Failure handling and continuity contract unchanged (DECIDED: preserve Phase 45 behavior)
**Decision:** The success/except branch structure, the continuity threading (synopsis + prev_scene_text advance only on success), and the `[Generation failed: ...]` placeholder behavior from Phase 45 are preserved unchanged. Only the *output channel* of the successful scene call changes (json → native) plus title parsing. `prev_scene_text` continues to be the screenplay body (now the native text), which is strictly cleaner for continuity injection than the old JSON-escaped string.

### D-46-04 — How "better formatting" is decided (DECIDED: reasoned adoption, not a runtime A/B harness)
**Grey area:** FMT-02 says "evaluated native vs json_mode." Does that mean ship a runtime toggle / comparison harness, or evaluate and commit to one?
**Decision:** Evaluate by reasoning + a focused test, then **commit to the native path** (no runtime dual-path toggle, no A/B flag persisted). Rationale: this is an internal tool; carrying two generation shapes forever is maintenance debt. The side-by-side *quality* comparison the user actually wants is Phase 49 (EVAL-01), which compares old vs new *output*, not two live code paths. Phase 46 evaluates and adopts; Phase 49 lets the user judge the cumulative result. Tests will assert the call now uses `json_mode=False` and that a JSON-wrapped screenplay is no longer required for a scene to parse.
</decisions>

<code_context>
## Existing Code Insights

- `_generate_scripts` (backend/app/services/template_ai_service.py ~line 305) builds the scene prompt and currently calls `chat_completion(..., json_mode=True, max_tokens=4000)`, then `json.loads(text)` and reads `result["title"]` / `result["content"]`.
- The Phase 45 synopsis-update call already uses `json_mode=False` and uses the returned string directly — the native-prose pattern to mirror.
- `ai_provider.chat_completion` strips markdown code fences and handles Anthropic system-prompt separation; native output needs no `json.loads`.
- Return contract consumed by `backend/app/api/endpoints/wizards.py:271` (`phase_data.content = {"screenplays": screenplays, "synopsis": synopsis}` with `flag_modified`) and by breakdown/shotlist staleness — the per-screenplay `{title, content, episode_index}` shape and the top-level `synopsis` key must remain.
- Existing test references: `test_continuity_generation.py`, `test_wizard_injection.py`, `test_bible_injection.py` all patch `app.services.template_ai_service.chat_completion`. New/updated tests must keep working with whatever output shape the scene call returns — they currently assume the scene call returns a JSON string, so they will need to be updated to the native shape (planner: update mocks to return the native title+body shape, not a JSON string).
</code_context>

<specifics>
## Specific Ideas

- Keep the change surgical: modify the scene-writing call shape + title parsing in `_generate_scripts`; update the scene prompt's formatting instructions and its "Return a JSON object…" tail (remove it — it no longer returns JSON).
- Add/adjust tests proving: (1) the scene call now runs with `json_mode=False`; (2) a normal native screenplay body lands in `content` with newlines intact (not `\n`-escaped); (3) the title is parsed (or falls back to summary); (4) the per-screenplay `{title, content, episode_index}` contract and top-level `synopsis` key are unchanged; (5) continuity/failure behavior from Phase 45 still holds (regression guard against `test_continuity_generation.py`).
- No migration. No frontend change. No new dependency.
</specifics>

<deferred>
## Deferred Ideas

- Runtime per-project format style toggle (e.g., screenplay vs teleplay vs stage) — not requested; out of scope.
- A real fountain/Final Draft parser or exporter — explicitly Out of Scope per REQUIREMENTS.md.
- Runtime A/B dual-path generation — folded into Phase 49's output-level side-by-side compare instead.
</deferred>
