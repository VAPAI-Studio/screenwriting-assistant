# Phase 45: Continuity-Aware Generation - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 3 (all modified, no new files)
**Analogs found:** 3 / 3 (all in-file analogs — the patterns to copy already live in the files being modified)

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `backend/app/services/template_ai_service.py` (`_generate_scripts`, line 253) | service | sequential generation loop / transform | `_generate_scenes` line 237-251 (synopsis-update call) + existing `_generate_scripts` loop body (lines 268-323) | exact (in-file) |
| `backend/app/services/ai_provider.py` (`chat_completion`, line 40) | service / provider | request-response | No change to signature; called as-is | n/a (consumed, not modified) |
| `backend/app/api/endpoints/wizards.py` (`apply_wizard_result_to_db`, line 250) | route / persistence | CRUD (JSONB write) | Same function's `script_writer_wizard` branch (lines 250-284) | exact (in-file) |

**Note for planner:** This phase has NO new files. All three "modified" files already contain the exact patterns the new code must mirror. The work is threading running state (`synopsis`, `prev_scene_text`) through an existing loop and adding one cheap `chat_completion` call per iteration. `ai_provider.py:chat_completion` is **not modified** — it is the call interface both the scene-writing and synopsis-update calls share; it is listed only because the synopsis call MUST go through it (D-02 discretion note, line 49 of CONTEXT).

## Pattern Assignments

### `backend/app/services/template_ai_service.py` — `_generate_scripts` (service, sequential generation loop)

**Analog 1 — the synopsis-update call shape:** `_generate_scenes` JSON `chat_completion` block (lines 237-251). This is the canonical small-JSON-call pattern in this file. The new per-scene synopsis-update call (D-02) copies this exact shape: build a prompt, call `chat_completion(... json_mode=True)`, `json.loads`, return field, wrap in try/except that logs and degrades gracefully.

```python
# template_ai_service.py:237-251 — COPY THIS SHAPE for the synopsis-update call
try:
    text = await chat_completion(
        messages=[
            {"role": "system", "content": "You are an expert short film scene structure planner. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=4000,
        json_mode=True,
    )
    result = json.loads(text)
    return {"scenes": result.get("scenes", [])}
except Exception as e:
    logger.error(f"Scene generation error: {e}")
    return {"scenes": [], "error": str(e)}
```

For the synopsis call, planner should use lower `max_tokens` (synopsis cap is ~300-500 words, D-03) and may use lower temperature for stable summarization. Exact wording/temperature/max_tokens are Claude's Discretion (CONTEXT line 48-49). Recommend extracting a private helper, e.g. `async def _update_synopsis(self, prev_synopsis: str, new_scene_text: str, scene_summary: str) -> str:` returning the regenerated synopsis string, so the loop body stays readable.

**Analog 2 — the loop body to augment:** existing `_generate_scripts` (lines 261-325).

Current cross-scene context is `scene_outline` (one-line summaries of ALL scenes), built once before the loop and injected into every prompt:

```python
# template_ai_service.py:261-265 — the context this phase REPLACES/AUGMENTS
scene_outline = "\n".join(
    f"  {i + 1}. {ep.get('summary', f'Scene {i + 1}')}"
    for i, ep in enumerate(episodes)
)
```

The scene prompt currently injects `scene_outline` at lines 279-280:

```python
## Full scene outline (for pacing context):
{scene_outline}
```

**Required changes (mirror existing patterns):**
1. Initialize running state before the loop: `synopsis = ""` and `prev_scene_text = ""`.
2. In the prompt (lines 271-300), inject continuity context **only when present** (D-05): the running `synopsis` + the verbatim `prev_scene_text`. When both are empty (first scene / single scene), inject nothing → behavior identical to today. The existing prompt already uses the conditional-injection idiom `{f'...' if cond else ''}` (e.g. line 276, 288) — reuse it for the new continuity block.
3. After a successful scene (right after `screenplays.append(result)` at line 315), set `prev_scene_text = result.get("content", "")` and call the synopsis-update helper to regenerate `synopsis`.

**Core loop pattern (lines 302-323) — preserve `episode_index` tagging and graceful failure:**

```python
# template_ai_service.py:302-323 — PRESERVE this structure
try:
    logger.info(f"Generating script for scene {i + 1}/{len(episodes)}: {summary}")
    text = await chat_completion(
        messages=[
            {"role": "system", "content": "You are an expert screenwriter. Return valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=4000,
        json_mode=True,
    )
    result = json.loads(text)
    result["episode_index"] = i        # preserved — wizards.py relies on this
    screenplays.append(result)
except Exception as e:
    logger.error(f"Script generation error for scene {i + 1}: {e}")
    screenplays.append({
        "episode_index": i,
        "title": summary,
        "content": f"[Generation failed: {str(e)}]",
        "error": str(e),
    })
```

**Failed-scene continuity (flagged in CONTEXT line 80):** On a failed scene the `except` branch appends an error placeholder. With strict-sequential D-05, the next scene's `prev_scene_text` would be that `[Generation failed: ...]` placeholder, and the synopsis-update call would run on garbage. Planner decision needed: keep it simple but do NOT advance `prev_scene_text` / do NOT run the synopsis-update on a failed scene (i.e. only update running state inside the success path). This keeps continuity context clean and is the least-surprising behavior.

**Return contract — DO NOT CHANGE (CONTEXT lines 24, 79):** `_generate_scripts` still returns `{"screenplays": [...]}` where each item has `{title, content, episode_index}`. The synopsis is attached at the persistence layer (wizards.py), NOT in the per-screenplay dict. Recommend `_generate_scripts` returns the final synopsis alongside, e.g. `{"screenplays": screenplays, "synopsis": synopsis}`, so wizards.py can persist it (see below) without changing per-screenplay shape.

---

### `backend/app/services/ai_provider.py` — `chat_completion` (service / provider, request-response)

**Not modified.** The synopsis-update call and the augmented scene call both go through this existing helper (D-02 discretion, CONTEXT line 49). Signature for reference:

```python
# ai_provider.py:40-46 — call interface for the new synopsis call (no change to this file)
async def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    json_mode: bool = False,
    provider: Optional[str] = None,
) -> str:
```

The synopsis-update call may use `json_mode=False` (a prose "story so far" synopsis is plain text per D-04, not JSON) OR `json_mode=True` returning `{"synopsis": "..."}`. Both work across OpenAI + Anthropic via this helper. Planner's choice (discretion). If plain text, no `json.loads` needed — just use the returned string directly (simpler, matches D-04 prose-only). Note: `chat_completion` already handles the Anthropic system-prompt separation and code-fence stripping (lines 85-134), so no provider-specific handling is needed in `template_ai_service.py`.

---

### `backend/app/api/endpoints/wizards.py` — `apply_wizard_result_to_db` script_writer branch (route / persistence, CRUD JSONB write)

**Analog:** the same function's existing `script_writer_wizard` branch (lines 250-284). This is the exact persistence pattern; the synopsis (D-06) attaches into the same `screenplay_editor` `PhaseData.content` JSON with **no migration**.

```python
# wizards.py:255-271 — the PhaseData.content write to AUGMENT with synopsis
phase_data = db.query(database.PhaseData).filter(
    database.PhaseData.project_id == project.id,
    database.PhaseData.phase == phase,
    database.PhaseData.subsection_key == "screenplay_editor"
).first()
if not phase_data:
    phase_data = database.PhaseData(
        project_id=project.id,
        phase=phase,
        subsection_key="screenplay_editor",
        content={},
    )
    db.add(phase_data)
    db.flush()

phase_data.content = {"screenplays": screenplays}   # <-- ADD synopsis here
flag_modified(phase_data, "content")
```

**Required change (single line):** Read the synopsis from `result` and include it in the content dict:

```python
synopsis = result.get("synopsis", "")
phase_data.content = {"screenplays": screenplays, "synopsis": synopsis}
flag_modified(phase_data, "content")   # REQUIRED — JSONB mutation tracking
```

**Critical pattern — `flag_modified`:** Every JSONB `content` write in this file calls `flag_modified(phase_data, "content")` (lines 243, 271, 322). SQLAlchemy does not detect in-place dict reassignment on JSONB columns without it. The synopsis write MUST keep this call.

The `ScreenplayContent` rows (lines 273-279) and the `_mark_breakdown_stale` / `_mark_shotlist_stale` calls (lines 281-282) are unchanged — synopsis does not affect them.

## Shared Patterns

### Provider-abstracted AI call
**Source:** `backend/app/services/ai_provider.py:40` (`chat_completion`)
**Apply to:** Both the augmented scene-writing call and the new synopsis-update call.
All AI calls in `template_ai_service.py` go through `chat_completion` / `chat_completion_stream` — never call OpenAI/Anthropic SDKs directly. This is what makes the new synopsis call work on both providers with zero extra wiring.

### Graceful AI-call failure
**Source:** `template_ai_service.py` — every method wraps the call in `try/except Exception`, logs via `logger.error(f"... error: {e}")`, and returns a safe degraded value (empty list/dict + `error` key). Lines 129-131, 249-251, 316-323, 377-379, 419-420.
**Apply to:** The synopsis-update call. On failure it should log and fall back (e.g. keep the previous synopsis, or empty) — never propagate and abort the whole script run.

### JSONB content persistence with flag_modified
**Source:** `wizards.py` lines 240-243, 270-271, 319-322
**Apply to:** The synopsis write into `screenplay_editor` content.
Pattern: fetch-or-create `PhaseData` for `(project_id, phase, subsection_key)`, reassign `.content`, call `flag_modified(phase_data, "content")`, `db.commit()`.

### Conditional prompt-section injection
**Source:** `template_ai_service.py` `_generate_scripts` prompt — `{f'## Overall Target Runtime: {runtime_target}' if runtime_target else ''}` (line 276), and `{f'Custom guidance: {guidance}' if guidance else ''}` (line 288).
**Apply to:** The continuity block (synopsis + prev scene text) — inject only when non-empty, satisfying D-05 (zero continuity context for first/single scene → unchanged behavior).

## No Analog Found

None. Every pattern this phase needs already exists in the three files being modified. The phase is an in-place augmentation of established patterns, not net-new architecture.

## Metadata

**Analog search scope:** `backend/app/services/template_ai_service.py`, `backend/app/services/ai_provider.py`, `backend/app/api/endpoints/wizards.py` (scope explicitly bounded by CONTEXT.md canonical refs — change is localized to `_generate_scripts`)
**Files scanned:** 3 (full reads of template_ai_service.py and ai_provider.py; targeted read of wizards.py lines 200-329)
**Pattern extraction date:** 2026-06-06
