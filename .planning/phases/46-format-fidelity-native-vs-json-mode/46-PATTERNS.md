# Phase 46: Format Fidelity (Native vs JSON Mode) - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 2 modified (+ 1 optional new test file)
**Analogs found:** 2 / 2 (both in-file; this is a surgical modification of an existing method)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/services/template_ai_service.py` (`_generate_scripts` scene call) | service | request-response (LLM generation, native text out) | `_update_synopsis` (same file, lines 253-303) — native `json_mode=False` prose call | exact (same file, same call shape, same pattern target) |
| `backend/app/tests/test_continuity_generation.py` (`_scene_writer` helper + `_MockChat`) | test | request-response mock | `_MockChat` itself (lines 50-86) — already routes scene-vs-synopsis by `json_mode` kwarg | exact (in-place mock update) |

**Note on scope:** This is a deliberately surgical change, not new-file creation. The single best analog (`_update_synopsis`) already lives in the file being modified and is the canonical proven native-output shape in this codebase (per D-46-01). No external analog search beyond this file plus `ai_provider.py` (consumed, not modified) and the sibling tests is warranted — early-stop applies.

## Pattern Assignments

### `backend/app/services/template_ai_service.py` — `_generate_scripts` scene call (service, request-response)

**Analog:** `_update_synopsis` (same file, lines 253-303) — the canonical native-prose call in this codebase.

**Native-output call pattern to MIRROR** (from `_update_synopsis`, lines 286-300):
```python
text = await chat_completion(
    messages=[
        {
            "role": "system",
            "content": "...Return prose only.",
        },
        {"role": "user", "content": prompt},
    ],
    temperature=0.3,
    max_tokens=700,
    json_mode=False,          # ← native channel: no response_format forced
)
updated = (text or "").strip()
return updated if updated else prev_synopsis   # ← graceful empty-fallback idiom
```
Key idioms to copy from this analog:
- `json_mode=False` (no JSON wrapper) — the whole point of D-46-01.
- `(text or "").strip()` — guard against `None`/whitespace before use.
- Empty-result fallback (`return X if X else fallback`) — the title-parse fallback to `summary` (D-46-01) should follow this exact shape.
- System prompt asserts the output channel in words ("Return prose only.") — for the scene call this becomes a screenplay-layout instruction (D-46-02), NOT "Return valid JSON only."

**Code BEING CHANGED** (current scene call, lines 372-390) — what to replace:
```python
text = await chat_completion(
    messages=[
        {"role": "system", "content": "You are an expert screenwriter. Return valid JSON only."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=4000,
    json_mode=True,                 # → becomes json_mode=False
)
result = json.loads(text)           # → REMOVE: no JSON parse; parse title off native text instead
result["episode_index"] = i
screenplays.append(result)
prev_scene_text = result.get("content", "")   # → prev_scene_text = the native body directly
synopsis = await self._update_synopsis(synopsis, prev_scene_text, summary)
```

**Prompt tail BEING CHANGED** (current, lines 360-370):
```python
Write a proper screenplay for THIS scene with:
- Scene headings (INT./EXT. LOCATION - TIME)
- Action lines (visual, present tense)
- Character dialogue with character names in CAPS
- Parentheticals where needed
...
Return a JSON object with:
- "title": a short title for this scene
- "content": the full screenplay text          # → REMOVE this JSON tail (D-46-02)
```
Per D-46-02 the layout rules above get strengthened (explicit: heading on its own line, parentheticals on their own line, blank line between elements) and the "Return a JSON object" tail is replaced with a native-output directive plus a parseable title convention (e.g. `TITLE:` first line then the screenplay body — see D-46-01 title handling).

**System-prompt string to change** (line 376): drop `"Return valid JSON only."`; replace with a prose/screenplay directive mirroring `_update_synopsis`'s `"Return prose only."` idiom.

**Per-screenplay contract that MUST be preserved exactly** (lines 384-385, 393-398, 400):
- Each appended item is `{"title", "content", "episode_index"}` (the `episode_index = i` assignment must remain).
- The except-branch placeholder `{"episode_index", "title": summary, "content": "[Generation failed: ...]", "error"}` is unchanged (D-46-03).
- `_generate_scripts` still returns `{"screenplays": [...], "synopsis": synopsis}` (line 400) — consumed by `wizards.py:271`.

**Continuity / failure structure that MUST stay byte-for-byte** (D-46-03, lines 387-398): the success-only advance of `prev_scene_text` and `synopsis`, and the `except` placeholder. Only the *successful* call's output channel + title derivation changes. `prev_scene_text` now holds the native body (cleaner than the old JSON-escaped string — explicitly noted as a benefit in D-46-03).

---

### `backend/app/tests/test_continuity_generation.py` — mock update (test, request-response mock)

**Analog:** the file's own `_MockChat.__call__` (lines 65-85) — already routes scene vs synopsis on the `json_mode` kwarg.

**Mocking pattern to KEEP** (lines 65-85) — the `json_mode`-routing side_effect is the established cross-test convention (also used in `test_bible_injection.py`, `test_wizard_injection.py` which patch `chat_completion` with `new_callable=AsyncMock`):
```python
def __call__(self, *args, **kwargs):
    json_mode = kwargs.get("json_mode", False)
    messages = kwargs.get("messages", [])
    user_msg = next((m["content"] for m in messages if m.get("role") == "user"), "")
    if json_mode:
        ...scene-writing branch...
    else:
        ...synopsis-update branch...
```
**Routing inversion required:** after Phase 46 the SCENE call is `json_mode=False` (like synopsis). The mock can no longer disambiguate scene vs synopsis by `json_mode` alone — BOTH are now `json_mode=False`. Planner must re-route, e.g. by call order (scene then its synopsis-update fire in a known sequence per loop iteration) or by a prompt-content marker (the synopsis prompt contains `"story so far" synopsis` / the scene prompt contains `"YOUR TASK: Write scene"`). The scene/synopsis prompt markers already used by the assertions (`SYNOPSIS_MARKER = "Story so far"`, `PREV_SCENE_MARKER = "Previous scene"`, lines 32-33) are reliable discriminators.

**Helper BEING CHANGED** (`_scene_writer`, lines 45-47) — currently returns a JSON string; must return the native title+body shape the new code parses:
```python
def _scene_writer(content, title="A Scene"):
    return json.dumps({"title": title, "content": content})   # → return native "TITLE: ...\n<body>" string (matching D-46-01 title convention)
```

**Assertions to add (per CONTEXT.md specifics, success criteria 1-5):**
1. Scene call runs with `json_mode=False` — assert on the recorded scene-call kwargs.
2. Native body lands in `content` with newlines intact (assert a multi-line body is NOT `\n`-escaped, i.e. `"\n" in item["content"]` and the literal `\\n` substring is absent).
3. Title is parsed off the native text (or falls back to `summary` when the title line is absent/empty — assert both branches).
4. Per-screenplay `{title, content, episode_index}` + top-level `synopsis` key unchanged (existing `test_per_screenplay_contract_unchanged` lines 181-197 is the regression guard — keep it green).
5. Continuity/failure behavior from Phase 45 unchanged — existing `test_failed_scene_does_not_advance_continuity` (lines 152-178) and `test_first_scene_has_no_continuity_block` (lines 94-107) are the regression guards.

---

## Shared Patterns

### Native (non-JSON) generation channel
**Source:** `_update_synopsis`, `backend/app/services/template_ai_service.py` lines 286-300
**Apply to:** the `_generate_scripts` scene call
```python
text = await chat_completion(messages=[...], temperature=..., max_tokens=4000, json_mode=False)
body = (text or "").strip()
# parse/fallback rather than json.loads
```
This is the only existing `json_mode=False` *generation* (non-stream) call in the service — every other method (`_generate_idea`, `_generate_scenes`, `fill_blanks`, `give_notes`, `analyze_structure`, `chat_action_extract_updates`, `chat_with_action`) uses `json_mode=True` + `json.loads`. `_generate_scripts`' scene call is migrating OUT of that JSON cohort and INTO the `_update_synopsis` native cohort.

### Provider-layer code-fence stripping (consumed, NOT modified)
**Source:** `chat_completion` → `_anthropic_completion`, `backend/app/services/ai_provider.py` lines 124-134
```python
# Strip markdown code fences if present (LLM sometimes wraps JSON)
if json_mode and text.startswith("```"):
    ...
```
**Note for planner:** fence-stripping is **gated on `json_mode=True`** (line 125). With the scene call moving to `json_mode=False`, the provider will NOT strip code fences from the screenplay body. This is fine for plain-text screenplay output, but if the model wraps the screenplay in ``` fences, the new title/body parser in `_generate_scripts` is responsible for tolerating/stripping a leading fence itself — the provider won't do it in native mode. The OpenAI path (`_openai_completion`, lines 65-82) does no stripping in either mode. Do not modify `ai_provider.py`.

### json_mode-routed AsyncMock side_effect (test convention)
**Source:** `_MockChat`, `test_continuity_generation.py` lines 50-85; patch idiom shared with `test_bible_injection.py:243` and `test_wizard_injection.py:84,172`
**Apply to:** the updated continuity test mock — but the routing key must shift from `json_mode` to prompt-content/call-order (see test assignment above), because scene and synopsis calls will both be `json_mode=False` post-change.

## No Analog Found

None. Both target files have exact in-codebase analogs (the native-prose pattern already exists in the same method's sibling call, and the test mock already exists in the same file). The phase is a channel-switch + parse change, not greenfield construction — RESEARCH.md fallback patterns are not needed.

## Metadata

**Analog search scope:** `backend/app/services/template_ai_service.py` (full read), `backend/app/services/ai_provider.py` (full read, consumed-only), `backend/app/tests/test_continuity_generation.py` (full read), `backend/app/tests/{test_wizard_injection,test_bible_injection}.py` (grep for mock convention), `backend/app/api/endpoints/wizards.py` lines 255-284 (consumer contract).
**Files scanned:** 5
**Pattern extraction date:** 2026-06-06
