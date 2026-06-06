# Phase 47: Character Voice Injection - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 3 (2 production modified, 1 test new/extended)
**Analogs found:** 3 / 3 (all exact, in-repo)

This phase is surgical and backend-only. Every change has an exact, already-shipped analog **inside the same two files being modified** (`_generate_scenes` mirrors `_generate_scripts`; the `scene_wizard` injection guard mirrors what `script_writer_wizard` now needs). The planner should copy these patterns near-verbatim, not invent new structure.

## File Classification

| Modified/New File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/api/endpoints/wizards.py` | route (background-task dispatcher) | request-response → config injection | same file, `scene_wizard` guard (wizards.py:138-139) | exact (extend existing branch) |
| `backend/app/services/template_ai_service.py` | service (AI prompt builder) | batch / transform (per-scene loop) | same file, `_generate_scenes` (template_ai_service.py:177-251) | exact (sibling method already does this) |
| `backend/app/tests/test_character_voice_injection.py` (new) | test | request-response (mocked LLM) | `test_continuity_generation.py` (`_MockChat`, `_make_config`, SCENE_MARKER) | exact (same target method) |

---

## Pattern Assignments

### `backend/app/api/endpoints/wizards.py` (route, config injection)

**Analog:** the existing `scene_wizard` injection in the same function (`run_wizard`).

**The exact line to extend** (wizards.py:136-139):
```python
# Inject character data for scene wizard before handing off to background
config = dict(request.config)
if request.wizard_type == "scene_wizard":
    config["_characters"] = _get_character_data(db, project.id)
```

**Change (D-47-01):** broaden the guard so `_characters` is injected for the script writer too. Per CONTEXT, the literal mechanism:
```python
if request.wizard_type in ("scene_wizard", "script_writer_wizard"):
    config["_characters"] = _get_character_data(db, project.id)
```

**Data source helper — reuse unchanged** (`_get_character_data`, wizards.py:46-58). It already returns the exact shape `_build_character_section` consumes:
```python
def _get_character_data(db: Session, project_id) -> list:
    """Fetch character ListItems for the project."""
    characters_pd = db.query(database.PhaseData).filter(
        database.PhaseData.project_id == project_id,
        database.PhaseData.phase == "story",
        database.PhaseData.subsection_key == "characters",
    ).first()
    if not characters_pd:
        return []
    items = db.query(database.ListItem).filter(
        database.ListItem.phase_data_id == characters_pd.id
    ).order_by(database.ListItem.sort_order).all()
    return [{"item_type": li.item_type, **(li.content or {})} for li in items]
```

**Why this is sufficient (no other plumbing):** `config` flows verbatim through `run_wizard` → `background_tasks.add_task(_run_wizard_background, ..., config=config, ...)` (wizards.py:152-162) → `template_ai_service.wizard_generate(config=config, ...)` (wizards.py:82-87) → `_generate_scripts(config, ...)` (template_ai_service.py:74-75). So once injected here, `config.get("_characters")` is available inside `_generate_scripts` with zero new parameters.

**Do NOT touch:** `apply_wizard_result_to_db` (wizards.py:216-329). The `_characters` key lives only on the in-memory `config` passed to the background task; the persisted `request.config` (wizards.py:146) is intentionally written WITHOUT `_characters`. Keep that split — the injection is request-time only.

---

### `backend/app/services/template_ai_service.py` (service, per-scene prompt builder)

**Analog:** `_generate_scenes` (template_ai_service.py:177-251) — the sibling wizard method that ALREADY reads `_characters` and injects a built character section into its prompt. This is the precise template for `_generate_scripts`.

**Step 1 — read `_characters` from config.** Copy the read idiom from `_generate_scenes` (template_ai_service.py:180):
```python
characters = config.get("_characters", [])
```
Add this at the top of `_generate_scripts`, alongside the existing `episodes` / `runtime_target` / `guidance` reads (template_ai_service.py:306-308).

**Step 2 — build the section once, before the loop.** Copy from `_generate_scenes` (template_ai_service.py:194):
```python
character_section = self._build_character_section(characters)
```
Build it once (it does not change per scene), before the `for i, ep in enumerate(episodes):` loop at template_ai_service.py:325.

**The formatter to reuse/extend** (`_build_character_section`, template_ai_service.py:163-175). Returns `""` for an empty list — this is what guarantees D-47-04 (empty `_characters` ⇒ no block, no behavior change):
```python
def _build_character_section(self, characters: list) -> str:
    """Build a formatted character section for the prompt."""
    if not characters:
        return ""
    parts = ["\n## Characters"]
    for char in characters:
        item_type = char.get("item_type", "character")
        name = char.get("name", "Unnamed")
        parts.append(f"\n### {item_type.replace('_', ' ').title()}: {name}")
        for k, v in char.items():
            if v and k not in ("item_type", "name"):
                parts.append(f"- {k.replace('_', ' ').title()}: {v}")
    return "\n".join(parts)
```
**Discretion (D-47-02):** the planner may reuse this as-is OR add a voice-emphasis variant (e.g. `_build_character_voice_section`) that foregrounds voice/diction cues. Either way the script prompt MUST surface per-character voice guidance, not merely list characters. If a variant is added, mirror this same `if not characters: return ""` empty-guard and the same `char.get(...)` field-iteration shape so the empty-list contract (D-47-04) is preserved.

**Step 3 — inject into the per-scene prompt f-string** (template_ai_service.py:341-373). The existing prompt already interleaves an optional `continuity_block` (built at 330-339) right before the `## YOUR TASK` marker (template_ai_service.py:352). Mirror exactly how `_generate_scenes` places its `character_section` immediately after `## Project Context` (template_ai_service.py:204-207):
```python
prompt = f"""You are an expert short film screenwriting assistant...

## Project Context
{project_context}
{character_section}

## Scene Generation Task
...
```
For `_generate_scripts`, land `{character_section}` in the f-string alongside `{project_context}` (template_ai_service.py:343-344) and the existing `{continuity_block}` (template_ai_service.py:352) — additive, not replacing either. Plus add the explicit distinct/consistent-voice instruction text (VOICE-03) into the prompt body — model the phrasing on the existing guideline bullets in `_generate_scenes` (template_ai_service.py:226-231, "Reference characters BY NAME...") and the continuity instruction already in `_generate_scripts` ("match its tone, voice, and continuity", template_ai_service.py:334).

**Critical invariants to preserve (D-47-04):**
- Return contract unchanged: `{"screenplays": [...], "synopsis": synopsis}` (template_ai_service.py:443).
- `chat_completion(..., json_mode=False)` native channel (template_ai_service.py:377-385) — do NOT switch to json_mode.
- The success-only continuity advance (template_ai_service.py:430-433) and the `[Generation failed: ...]` except branch (template_ai_service.py:434-441) stay exactly as-is.
- The TITLE-line parse + summary fallback (template_ai_service.py:391-423) is untouched.

**SCENE_MARKER must remain intact:** the string `YOUR TASK: Write scene` (template_ai_service.py:352) is the discriminator the continuity tests route on (`test_continuity_generation.py:41`). Inserting the character section must not alter that literal substring.

---

### `backend/app/tests/test_character_voice_injection.py` (test) — new file or additions to `test_continuity_generation.py`

**Analog:** `test_continuity_generation.py` — same target method (`_generate_scripts`), same mock surface, same native (json_mode=False) routing. Copy its scaffold wholesale.

**Module-singleton patch idiom** (test_continuity_generation.py:30-32, 110-115):
```python
from unittest.mock import patch, AsyncMock
from app.services.template_ai_service import template_ai_service

with patch(
    "app.services.template_ai_service.chat_completion",
    new_callable=AsyncMock,
    side_effect=mock,
):
    ...
```

**Config builder — extend to carry `_characters`** (base from test_continuity_generation.py:44-50). The new tests add a `_characters` list:
```python
def _make_config(num_scenes, characters=None):
    cfg = {
        "episodes": [
            {"summary": f"Scene {i + 1} summary"} for i in range(num_scenes)
        ]
    }
    if characters is not None:
        cfg["_characters"] = characters
    return cfg
```
Each character dict mirrors the `_get_character_data` shape: `{"item_type": "protagonist", "name": "MAYA", "personality": "...", ...}`.

**Scene-vs-synopsis routing mock — reuse `_MockChat` verbatim** (test_continuity_generation.py:60-99). It routes by `SCENE_MARKER = "YOUR TASK: Write scene"` (test_continuity_generation.py:41) and records `self.scene_prompts` — exactly what voice assertions inspect:
```python
class _MockChat:
    def __init__(self, scene_contents, synopsis_text="SYNOPSIS_PROSE", fail_scene_index=None):
        self.scene_prompts = []      # asserted against for character name/voice cues
        ...
    def __call__(self, *args, **kwargs):
        messages = kwargs.get("messages", [])
        user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
        if SCENE_MARKER in user_msg:
            self.scene_prompts.append(user_msg)
            ...
            return _scene_writer(content, title=f"Scene {idx + 1}")
        else:
            self.synopsis_calls += 1
            return self.synopsis_text
```

**Runner helper** (test_continuity_generation.py:102-105):
```python
def _run(config):
    return asyncio.run(
        template_ai_service._generate_scripts(config, "PROJECT CONTEXT", {})
    )
```

**Tests to write (from CONTEXT specifics §):**
1. **VOICE-01** — prompt reaches `_generate_scripts`: assert each provided character's `name` appears in `mock.scene_prompts[0]`. Mirror the marker-in-prompt assertion style of `test_later_scene_includes_prior_scene_and_synopsis` (test_continuity_generation.py:137-145).
2. **VOICE-03** — prompt carries an explicit distinct/consistent-voice instruction: assert a stable instruction substring (planner picks the exact phrase it injects) is in `mock.scene_prompts[0]`.
3. **No-regression / D-47-04** — with `_characters` absent (or `[]`), assert no character block: e.g. `assert "## Characters" not in prompt`. Pair with the directive that the existing `test_continuity_generation.py` suite must still pass unchanged (the SCENE_MARKER and continuity blocks are untouched).
4. **Wizards path (D-47-01)** — `script_writer_wizard` now gets `_characters` injected. Analog: `test_wizard_injection.py` exercises `run_wizard`/middleware. Assert the config handed to the background task includes `_characters` for `script_writer_wizard` (or that `_get_character_data` is invoked for that wizard type). Keep `test_wizard_injection.py` green.

---

## Shared Patterns

### Empty-list safety (the D-47-04 contract carrier)
**Source:** `_build_character_section` (template_ai_service.py:165-166)
**Apply to:** the `_generate_scripts` injection and any voice-variant formatter.
```python
if not characters:
    return ""
```
An absent/empty `_characters` yields an empty section ⇒ the script prompt is byte-identical to Phase 46 ⇒ no scene can fail from character injection.

### Config-passthrough (no new plumbing)
**Source:** wizards.py:137 (`config = dict(request.config)`) → 152-162 (`add_task(..., config=config)`) → template_ai_service.py:74-75.
**Apply to:** the `_characters` injection. The dict flows verbatim end-to-end; only the request-time `config` carries `_characters`, never the persisted `request.config` (wizards.py:146).

### Module-singleton LLM patch
**Source:** test_continuity_generation.py:111-115 / test_bible_injection.py (referenced at test_continuity_generation.py:13).
**Apply to:** every new voice-injection test.
```python
@patch("app.services.template_ai_service.chat_completion", new_callable=AsyncMock, side_effect=mock)
```

### Native-output routing discriminator
**Source:** SCENE_MARKER `"YOUR TASK: Write scene"` (template_ai_service.py:352 ↔ test_continuity_generation.py:41,86).
**Apply to:** mock routing in new tests, and as an invariant — production prompt edits must not break this literal substring.

---

## No Analog Found

None. Every change has an in-repo, already-shipped analog. There is no need to fall back to RESEARCH.md patterns for this phase.

## Metadata

**Analog search scope:** `backend/app/api/endpoints/`, `backend/app/services/`, `backend/app/tests/`
**Files scanned:** wizards.py, template_ai_service.py, test_continuity_generation.py, test_wizard_injection.py (plus tests dir listing)
**Pattern extraction date:** 2026-06-06
