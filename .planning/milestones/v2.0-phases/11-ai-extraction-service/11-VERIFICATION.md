---
phase: 11-ai-extraction-service
verified: 2026-03-13T21:10:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 11: AI Extraction Service Verification Report

**Phase Goal:** AI analyzes screenplay content and project data to produce structured JSON of production elements across 5 categories, with deduplication, user-modified protection, and scene link reconciliation
**Verified:** 2026-03-13T21:10:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Calling `BreakdownService.extract(project_id)` gathers screenplay content and character names, sends a structured-output AI call, and persists elements to the database with scene links | VERIFIED | `extract()` in `breakdown_service.py` lines 412–482: calls `_build_extraction_context`, `_call_ai_extraction`, `_upsert_elements`, `_reconcile_scene_links`, `_record_run`, `db.commit()`. `test_extraction_produces_elements` passes with 3 DB elements created. |
| 2 | The extraction uses low temperature (0.1-0.2) and the prompt restricts output to elements physically present on screen (not mentioned in dialogue or backstory) | VERIFIED | `_call_ai_extraction()` line 218: `temperature=0.15`. `EXTRACTION_SYSTEM_PROMPT` lines 80–102: CRITICAL RULES list "Only extract elements that PHYSICALLY APPEAR in the scene". `test_extraction_temperature` asserts `call_args.kwargs["temperature"] == 0.15` and passes. |
| 3 | The same element described differently across scenes (e.g., "GUN" and "revolver") maps to one master list entry with a canonical name | VERIFIED | `_deduplicate_elements()` lines 222–249: uses `(category, canonical_name.lower())` as merge key. Called in `extract()` at line 442 before upsert. `test_deduplication` and `test_deduplication_different_categories_not_merged` both pass. |
| 4 | Re-extraction preserves elements where `user_modified=true` (name, description, and metadata unchanged) and does not resurrect soft-deleted elements | VERIFIED | `_upsert_elements()` lines 284–287: `is_deleted=True` → skip (no element_map entry). Lines 289–294: `user_modified=True` → skip update, add to element_map. `test_user_modified_preserved` and `test_deleted_not_resurrected` both pass. |
| 5 | Each extracted element is linked to the scene ListItems where it appears via `element_scene_links` records | VERIFIED | `_map_scene_indices_to_ids()` lines 360–382: converts 1-based AI indices to ListItem UUIDs. `_reconcile_scene_links()` lines 323–358: deletes AI links, preserves user links, creates new AI links. `test_scene_linking` asserts 2 `ElementSceneLink` rows with correct IDs and passes. |

**Score: 5/5 truths verified**

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/breakdown_service.py` | BreakdownService class with full extraction pipeline, Pydantic models, context builder | VERIFIED | 486 lines (min 200 required). Contains: `ExtractedSceneAppearance`, `ExtractedElement`, `ExtractionResponse`, `ExtractionContext`, `EXTRACTION_SYSTEM_PROMPT`, all 8 pipeline methods, module singleton. |
| `backend/app/services/ai_provider.py` | `chat_completion_structured()` function for dual-provider structured outputs | VERIFIED | Lines 137–235: `chat_completion_structured()`, `_openai_structured()`, `_anthropic_structured()` all present and importable. No existing functions modified. |
| `backend/requirements.txt` | Upgraded SDK version floors: `openai>=1.40.0`, `anthropic>=0.77.0` | VERIFIED | Line 9: `openai>=1.40.0`. Line 10: `anthropic>=0.77.0`. Both confirmed. |
| `backend/app/api/endpoints/breakdown.py` | Wired `trigger_extraction` endpoint calling real BreakdownService | VERIFIED | Line 13: `from ...services.breakdown_service import breakdown_service`. Lines 167–184: `trigger_extraction` calls `await breakdown_service.extract(db, project_id)`. No stub code present. |
| `backend/app/tests/test_breakdown_service.py` | Integration tests for all EXTR-* and SYNC-* requirements | VERIFIED | 400 lines (min 200 required). 8 tests covering all 7 requirements. All 8 pass. |
| `backend/app/tests/test_breakdown_api.py` | Updated extraction API tests with mocked AI | VERIFIED | `TestExtraction` class uses `@patch("app.services.breakdown_service.chat_completion_structured", new_callable=AsyncMock)` and creates `ScreenplayContent`. Both tests pass. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `breakdown_service.py` | `ai_provider.py` | `from .ai_provider import chat_completion_structured` | WIRED | Line 23 import confirmed. Used at line 215 in `_call_ai_extraction()`. |
| `breakdown_service.py` | `ai_provider.py` | `chat_completion_structured(messages, response_model=ExtractionResponse, temperature=0.15, ...)` | WIRED | `_call_ai_extraction()` calls with correct signature including `response_model=ExtractionResponse` and `temperature=0.15`. |
| `breakdown.py` | `breakdown_service.py` | `from ...services.breakdown_service import breakdown_service` + `breakdown_service.extract()` | WIRED | Import at line 13. `trigger_extraction` calls `await breakdown_service.extract(db, project_id)` at line 177. |
| `breakdown_service.py` | `database.py` | SQLAlchemy queries for `ScreenplayContent`, `PhaseData`, `ListItem`, `Project` | WIRED | `_build_extraction_context()`: 4 model query blocks. Pattern `database.ScreenplayContent`, `database.PhaseData`, `database.ListItem`, `database.Project` all used. |
| `breakdown_service.py` | `database.py` | `BreakdownElement` upsert and `ElementSceneLink` reconciliation | WIRED | `_upsert_elements()`: queries and creates `database.BreakdownElement`. `_reconcile_scene_links()`: deletes and creates `database.ElementSceneLink`. `_record_run()`: creates `database.BreakdownRun`. |
| `test_breakdown_service.py` | `breakdown_service.py` | Direct service method calls with mocked AI provider | WIRED | `@patch("app.services.breakdown_service.chat_completion_structured")` used in 5 async test methods. Direct calls to `breakdown_service.extract()`, `breakdown_service._deduplicate_elements()`. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EXTR-01 | 11-01, 11-02, 11-03 | AI extraction service analyzes screenplay content + character names to produce structured JSON of production elements across 5 categories | SATISFIED | `_build_extraction_context()` queries ScreenplayContent + character ListItems. `_call_ai_extraction()` sends structured output prompt. `_upsert_elements()` persists to DB. `test_extraction_produces_elements`: 3 elements across character/prop/location categories created. |
| EXTR-02 | 11-01, 11-02, 11-03 | Extraction uses structured outputs (schema-enforced JSON) via upgraded OpenAI/Anthropic SDKs | SATISFIED | `chat_completion_structured()` in `ai_provider.py`: OpenAI uses `client.chat.completions.parse(response_format=response_model)`, Anthropic uses `response_format` with `model_json_schema()`. `requirements.txt`: `openai>=1.40.0`, `anthropic>=0.77.0`. `test_structured_output_schema`: validates schema via `ExtractionResponse.model_json_schema()`. |
| EXTR-03 | 11-03 | Deduplication — same element described differently across scenes maps to one master list entry with canonical name | SATISFIED | `_deduplicate_elements()` merges on `(category, canonical_name.lower())`, keeps first description, merges scene_appearances. Called in `extract()` at line 442 before upsert. `test_deduplication`: "Gun" + "gun" → 1 element with 2 scene appearances. |
| EXTR-04 | 11-01, 11-02, 11-03 | Low temperature (0.1-0.2) for extraction calls; only extract elements physically present on screen | SATISFIED | `_call_ai_extraction()` uses `temperature=0.15`. `EXTRACTION_SYSTEM_PROMPT` explicitly states "Only extract elements that PHYSICALLY APPEAR in the scene -- visible to the camera". `test_extraction_temperature`: `assert call_kwargs["temperature"] == 0.15` passes. |
| EXTR-05 | 11-02, 11-03 | Scene linking — each extracted element tracks which scenes it appears in by matching to scene ListItem records | SATISFIED | `_map_scene_indices_to_ids()` converts 1-based AI indices to ListItem UUIDs. `_reconcile_scene_links()` creates `ElementSceneLink` records. `test_scene_linking`: scene_index=1 maps to `scene_ids[0]`, scene_index=3 maps to `scene_ids[2]`. |
| SYNC-01 | 11-02, 11-03 | Re-extraction preserves user modifications — elements with `user_modified=true` keep their user-edited name, description, and metadata | SATISFIED | `_upsert_elements()` lines 289–294: `user_modified=True` → skip description update, include in element_map for scene linking. `test_user_modified_preserved`: AI sends `description="AI description"`, element retains `"User's description"`. |
| SYNC-02 | 11-02, 11-03 | Soft-deleted elements (`is_deleted=true`) are not resurrected by re-extraction | SATISFIED | `_upsert_elements()` lines 284–287: `is_deleted=True` → `skipped += 1`, `continue` (no element_map entry, no scene links). `test_deleted_not_resurrected`: `is_deleted` remains `True`, no new "Broken Lamp" element created. |

**All 7 requirements satisfied. No orphaned requirements (SYNC-03, SYNC-04, SYNC-05 are correctly assigned to Phase 12/14).**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No anti-patterns detected in key phase files |

Scanned `breakdown_service.py`, `ai_provider.py`, `breakdown.py`: No TODO/FIXME/placeholder comments, no empty return stubs, no console.log-only implementations. The `extract()` stub from Plan 11-01 was fully replaced in Plan 11-02 as intended.

---

### Human Verification Required

No items require human verification. All phase requirements are testable programmatically and tests pass.

Items that would normally need human verification (live AI call quality) are explicitly out of scope for this phase — the phase design uses mocked AI for testing and relies on prompt engineering in `EXTRACTION_SYSTEM_PROMPT` for quality, which is reviewed through the prompt content itself.

---

### Test Results Summary

| Test Suite | Tests | Passed | Failed |
|------------|-------|--------|--------|
| `test_breakdown_service.py` | 8 | 8 | 0 |
| `test_breakdown_api.py` | 22 | 22 | 0 |
| Full suite (`app/tests/`) | 120 | 120 | 0 |

All 120 tests pass with no regressions.

---

### Gaps Summary

No gaps. All 5 success criteria from ROADMAP.md are verified, all 7 requirement IDs (EXTR-01 through SYNC-02) are satisfied with test evidence, all required artifacts exist and are substantive and wired, and all key links are confirmed.

---

_Verified: 2026-03-13T21:10:00Z_
_Verifier: Claude (gsd-verifier)_
