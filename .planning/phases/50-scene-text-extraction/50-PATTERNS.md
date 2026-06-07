# Phase 50: Scene-Scoped Fidelity - Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 2 (1 service modified, 1 test module extended)
**Analogs found:** 2 / 2 (both in-file / in-codebase — this is a surgical restructure of existing methods)

## Re-scope Anchor (read before planning)

The genuine gap is **scene-scoped attribution**, NOT "extract against text vs summaries" (already satisfied). See `.planning/v7.0-RESCOPE-NOTE.md` finding #1. Phase 50 only restructures how the screenplay TEXT is laid out in the user prompt so the AI's per-element `scene_index` is reliable. No schema change, no migration, single `chat_completion_structured` call preserved (D-50-02). On-screen-only rules preserved verbatim (D-50-03).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/services/breakdown_service.py` (`_build_extraction_context` + `_build_user_prompt`, + optional alignment helper) | service (prompt builder) | transform (DB rows → AI prompt string) | itself (in-place restructure) + `wizards.py:keep_scene_version` alignment pattern | exact (self) |
| `backend/app/tests/test_breakdown_service.py` (new Phase-50 tests) | test | request-response (mocked AI) | `test_scene_linking` / `_setup_project_with_screenplay` in same file | exact |

Both targets are restructures/extensions of existing, working code. The "analog" for the prompt-builder is the method itself (current shape shown below, to be replaced); the analog for the robust alignment join is `wizards.py:keep_scene_version` (lines 484-499). The analog for tests is the existing scaffold in the same test file.

---

## Pattern Assignments

### `backend/app/services/breakdown_service.py` — `_build_user_prompt` (service, transform)

**Analog:** itself — the method being restructured. THE FILE TO RESTRUCTURE.

**Current structure to REPLACE** (`breakdown_service.py:178-207`):
```python
def _build_user_prompt(self, ctx: ExtractionContext) -> str:
    parts = [f"# Screenplay: {ctx.project_title}\n"]

    # Known characters (helps AI match names consistently)
    if ctx.character_names:
        parts.append("## Known Characters")
        for name in ctx.character_names:
            parts.append(f"- {name}")
        parts.append("")

    # Scene list with indices for reliable matching
    parts.append("## Scenes")
    for i, scene in enumerate(ctx.scene_summaries):
        parts.append(f"Scene {i + 1}: {scene['summary']}")
    parts.append("")

    # Full screenplay text  <-- THE PROBLEM: separate concatenated blob
    parts.append("## Screenplay Content")
    for text in ctx.screenplay_texts:
        parts.append(text)
        parts.append("---")

    parts.append("\nExtract all production elements from this screenplay.")
    return "\n".join(parts)
```

**The defect (D-50-01):** Two parallel lists the AI must mentally align — a `## Scenes` 1-based summary list AND a separate `## Screenplay Content` blob where scene texts are concatenated with `---` and carry NO index label. On longer scripts the AI mis-attributes `scene_index`.

**Target pattern (merge into one indexed structure):** Emit each scene's summary + its full text together under its own explicit 1-based header, in the SAME index space `scene_summaries`, `_map_scene_indices_to_ids`, and `ExtractedSceneAppearance.scene_index` already use. Keep `## Known Characters` block unchanged. Keep the `"\n".join(parts)` builder idiom. Example shape (planner finalizes exact wording):
```python
parts.append("## Scenes (extract elements against the scene under which their text appears)")
for i, scene in enumerate(ctx.scene_summaries):
    parts.append(f"### Scene {i + 1}: {scene['summary']}")
    text = per_scene_text.get(i)  # aligned per-scene text; see helper below
    parts.append(text if text else "[scene text unavailable]")
    parts.append("")
```
The closing instruction must change to "attribute each element to the scene index/indices under which its text appears" (D-50-01).

**Preserve the builder idiom** (lines 185, 207): `parts = [...]` accumulation + `return "\n".join(parts)`. Do not switch to f-string concatenation.

---

### `backend/app/services/breakdown_service.py` — `_build_extraction_context` + alignment helper (service, transform)

**Analog (where the flat lists are built today):** `breakdown_service.py:112-176`.

**Current context shape** (`breakdown_service.py:171-176`) — `screenplay_texts` is a FLAT list, `scene_summaries` is a SEPARATE ordered list:
```python
return ExtractionContext(
    screenplay_texts=[sc.content for sc in screenplays if sc.content],
    character_names=character_names,
    scene_summaries=scene_summaries,
    project_title=project.title if project else "",
)
```

**Scene summaries are already index-ordered** (`breakdown_service.py:154-164`) — ordered by `sort_order`, carrying `id` per scene (this is the join target):
```python
scene_items = db.query(database.ListItem).filter(
    database.ListItem.phase_data_id == str(scenes_pd.id)
).order_by(database.ListItem.sort_order).all()
scene_summaries = [
    {
        "id": str(li.id),
        "summary": li.content.get("summary", f"Scene {li.sort_order + 1}"),
        "sort_order": li.sort_order,
    }
    for li in scene_items
]
```

**Screenplay query has NO order_by today** (`breakdown_service.py:125-127`) — alignment-critical gap:
```python
screenplays = db.query(database.ScreenplayContent).filter(
    database.ScreenplayContent.project_id == str(project_id)
).all()   # <-- unordered; per-scene alignment needs deterministic ordering
```

**Alignment join key (v6.0): `formatted_content.episode_index`.** ScreenplayContent rows carry it. The robust alignment analog is `wizards.py:keep_scene_version` (`wizards.py:484-499`) — copy this exact "prefer episode_index match, fall back to positional, handle duplicate/append rows" pattern:
```python
# wizards.py:484-499 — THE ROBUST ALIGNMENT PATTERN TO COPY
rows = db.query(database.ScreenplayContent).filter(
    database.ScreenplayContent.project_id == project.id
).order_by(
    database.ScreenplayContent.created_at.desc(), database.ScreenplayContent.id.desc()
).all()
target = next(
    (r for r in rows if (r.formatted_content or {}).get("episode_index") == request.episode_index),
    None,
)
if target is None and request.episode_index < len(rows):
    # rows is newest-first; index from the end to keep positional alignment
    target = rows[len(rows) - 1 - request.episode_index]
```
Key facts the planner must honor (from the comment at `wizards.py:476-483`): the batch-generate path APPENDS ScreenplayContent rows and never deletes them, so **a project can hold duplicate rows per episode_index**. Map by `formatted_content.episode_index` first; fall back to positional ordering only when no row carries the index (NO migration — D-49-03 / D-50-01).

**Where episode_index is set** (`wizards.py:274-279`, batch apply) — each row's `formatted_content` is the whole screenplay slot dict, which includes `episode_index` for v6.0+ generations:
```python
for sp in screenplays:   # sp == {"title", "content", "episode_index": i, ...}
    sc = database.ScreenplayContent(
        project_id=project.id,
        content=sp.get("content", ""),
        formatted_content=sp,   # <-- carries episode_index
    )
    db.add(sc)
```
And on keep-scene-version (`wizards.py:466-499`): `new_slot = {"title","content","episode_index": request.episode_index}` is written to `target.formatted_content`. So the join key is reliably present for any scene generated/kept under v6.0+, and ABSENT for older rows — hence the mandatory fallback.

**Helper signature (Claude's Discretion per D-50-01, but spec the contract):** produce a mapping `scene_zero_based_index -> scene_text` aligned to `scene_summaries` order. Recommended: a private method e.g. `_align_screenplay_to_scenes(screenplays, scene_summaries) -> Dict[int, str]` returning per-scene text keyed by 0-based scene index. Carry it on `ExtractionContext` (e.g. add a field `scene_texts_by_index: Optional[Dict[int, str]] = None`) so `_build_user_prompt` consumes it without re-querying. Keep `screenplay_texts: List[str]` on the dataclass for the graceful-fallback path.

**GRACEFUL FALLBACK — MANDATORY (D-50-01, flagged):** ScreenplayContent row count and scene_list ListItem count may differ (rows are appended/duplicated; scenes can be added/removed independently). When per-scene alignment is unavailable or count-mismatched (no episode_index on rows AND positional count differs, or mapping is empty), `_build_user_prompt` MUST fall back to the CURRENT concatenated `## Scenes` summary list + `## Screenplay Content` blob form (lines 194-204). **Never crash an extraction over alignment.** The decision of "aligned vs fallback" should be made in the builder based on whether the per-scene mapping covers the scenes; both code paths must be exercised by tests.

---

### `backend/app/tests/test_breakdown_service.py` — Phase 50 tests (test, request-response)

**Analog:** existing scaffold in the same file — reuse verbatim.

**Mock decorator pattern** (`test_breakdown_service.py:127`, repeated at 266, 282, 322, 360):
```python
@patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)
async def test_...(self, mock_ai, db_session):
    project_id, scene_ids = _setup_project_with_screenplay(db_session)
    mock_ai.return_value = _mock_extraction_response([...])
    await breakdown_service.extract(db_session, project_id)
```

**Fixture** (`test_breakdown_service.py:39-113`) — `_setup_project_with_screenplay` seeds project + ONE ScreenplayContent row (content only, NO `formatted_content` / NO `episode_index`) + 2 characters + 3 scene ListItems (sort_order 0,1,2). NOTE: the current fixture's single SC row has no `episode_index` and one content blob covering 3 scenes — so it naturally exercises the **fallback** path. To test the **aligned** path, new tests must seed multiple ScreenplayContent rows each with `formatted_content={"episode_index": i, "content": ...}` matching the 3 scenes.

**Scene-link assertion pattern to reuse** (`test_breakdown_service.py:299-317`) — proves scene_index → ListItem id mapping:
```python
links = db_session.query(ElementSceneLink).filter(
    ElementSceneLink.element_id == str(element.id),
).all()
linked_scene_ids = {link.scene_item_id for link in links}
assert scene_ids[0] in linked_scene_ids   # scene_index 1 -> scene_ids[0]
assert scene_ids[2] in linked_scene_ids   # scene_index 3 -> scene_ids[2]
```

**Prompt-shape assertion (new pattern — call the builder directly, no mock needed):** `_build_extraction_context` then `_build_user_prompt` are pure given a DB session; assert on the returned string:
```python
ctx = breakdown_service._build_extraction_context(db_session, project_id)
prompt = breakdown_service._build_user_prompt(ctx)
assert "### Scene 1:" in prompt          # each scene under its own indexed header
assert "### Scene 3:" in prompt
# on-screen-only rules live in EXTRACTION_SYSTEM_PROMPT, assert there too:
from app.services.breakdown_service import EXTRACTION_SYSTEM_PROMPT
assert "PHYSICALLY PRESENT ON SCREEN" in EXTRACTION_SYSTEM_PROMPT  # BFID-03 guard
```

**Required new tests (per D-50-01 / specifics):**
1. Aligned prompt: seed multi-row SC with `episode_index`, assert each scene's full text appears under its own `### Scene {i+1}` header.
2. Attribution mapping: mocked AI response with `scene_index` per appearance maps elements to the correct scene ListItem ids (reuse 299-317 pattern).
3. On-screen rules preserved (BFID-03 regression guard) — assert system-prompt rule text still present.
4. Graceful fallback: ScreenplayContent count != scene count (e.g. 1 SC row, 3 scenes, no episode_index) → `extract()` still completes (`run.status == "completed"`), no crash, falls back to concatenated form.

---

## Shared Patterns

### Robust index-alignment with graceful fallback (cross-cutting for this phase)
**Source:** `backend/app/api/endpoints/wizards.py:484-499` (`keep_scene_version`)
**Apply to:** the new alignment helper in `breakdown_service.py`
- Prefer `formatted_content.episode_index` match; positional fallback when absent.
- Tolerate duplicate/appended ScreenplayContent rows (batch path never deletes — `wizards.py:476-483`).
- Order deterministically (`created_at.desc(), id.desc()`); index from end for positional alignment.
- Never raise on mismatch — degrade to concatenated form.

### 1-based scene_index ↔ ListItem id mapping (the consumer that benefits)
**Source:** `backend/app/services/breakdown_service.py:364-386` (`_map_scene_indices_to_ids`) — UNCHANGED by Phase 50.
```python
zero_based = appearance.scene_index - 1
if 0 <= zero_based < len(ctx.scene_summaries):
    scene_ids.append(ctx.scene_summaries[zero_based]["id"])
else:
    logger.warning("Invalid scene_index %d ... -- skipping", ...)
```
**Apply to:** nothing new — this is why the prompt restructure must keep the SAME 1-based index space as `scene_summaries`. Better attribution from the prompt directly improves the reliability of this existing mapping. Do NOT change this method.

### Prompt-string builder idiom
**Source:** `breakdown_service.py:185-207` — `parts = [...]; parts.append(...); return "\n".join(parts)`. Keep this idiom in the restructured `_build_user_prompt`.

### Structured-output AI call (preserve verbatim — D-50-02)
**Source:** `breakdown_service.py:209-224` (`_call_ai_extraction`) — single `chat_completion_structured(messages, response_model=ExtractionResponse, temperature=0.15, max_tokens=8000)`. UNCHANGED. `EXTRACTION_SYSTEM_PROMPT` (lines 80-102) on-screen-only rules UNCHANGED (D-50-03 / BFID-03).

---

## No Analog Found

None. Every pattern this phase needs already exists in-codebase:
- prompt builder → the method itself
- robust index alignment + fallback → `wizards.py:keep_scene_version`
- test scaffold → `test_breakdown_service.py` existing fixtures/tests

## Metadata

**Analog search scope:** `backend/app/services/breakdown_service.py`, `backend/app/api/endpoints/wizards.py`, `backend/app/models/database.py`, `backend/app/tests/test_breakdown_service.py`
**Files scanned:** 4 source + grep across `backend/app` for `episode_index` / `formatted_content` / `ScreenplayContent(`
**Pattern extraction date:** 2026-06-07
