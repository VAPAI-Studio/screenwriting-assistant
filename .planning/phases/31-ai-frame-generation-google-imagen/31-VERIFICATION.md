---
phase: 31-ai-frame-generation-google-imagen
verified: 2026-04-01T00:00:00Z
status: gaps_found
score: 4/5 success criteria verified
gaps:
  - truth: "Users can choose between style presets (Photorealistic, Cinematic, Animated)"
    status: partial
    reason: "ImagenService implements all three style prefixes and the backend reads project.storyboard_style, but there is no user-facing UI to select a style. The Project frontend type does not include storyboard_style, ProjectUpdate schema does not expose it, and no dropdown/selector exists in StoryboardView or FrameGalleryModal. The field defaults to null, falling back to 'Cinematic film still.' for all users."
    artifacts:
      - path: "frontend/src/components/Storyboard/FrameGalleryModal.tsx"
        issue: "No style selector UI; generateMutation calls api.generateFrame with no style argument"
      - path: "frontend/src/components/Storyboard/StoryboardView.tsx"
        issue: "No project-level style picker rendered"
      - path: "frontend/src/types/index.ts"
        issue: "Project interface does not include storyboard_style field"
      - path: "backend/app/models/schemas.py"
        issue: "ProjectUpdate schema does not expose storyboard_style, so it cannot be set via the API"
    missing:
      - "Add storyboard_style to Project interface and ProjectUpdate schema"
      - "Expose PATCH /api/projects/{id} with storyboard_style field OR add storyboard_style param to generate endpoint"
      - "Add a style preset selector (Photorealistic / Cinematic / Animated) in the StoryboardView header or FrameGalleryModal"
human_verification:
  - test: "Trigger AI frame generation end-to-end"
    expected: "Clicking 'Generate with AI' in FrameGalleryModal sends a POST request, and after Vertex AI responds, a new frame appears in the gallery"
    why_human: "Cannot call live Vertex AI API in automated tests; tests use monkeypatching"
  - test: "Verify 502 error display"
    expected: "If the Imagen API fails (e.g., missing credentials), the modal shows 'Generation failed: ...' below the gallery"
    why_human: "Error path requires a real (or fully mocked) failing network call"
---

# Phase 31: AI Frame Generation (Google Imagen) Verification Report

**Phase Goal:** Vertex AI / Imagen integration, per-shot "Generate Frame" button using shot fields as prompt, Photorealistic / Cinematic / Animated styles
**Verified:** 2026-04-01
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ImagenService calls Vertex AI / Google Imagen API | VERIFIED | `backend/app/services/imagen_service.py` uses `vertexai.init()` + `ImageGenerationModel.from_pretrained()` + `generate_images()`; SDK in `requirements.txt` |
| 2 | "Generate Frame" button in frame gallery modal for each shot | VERIFIED | `FrameGalleryModal.tsx` line 125-136: enabled violet button calls `generateMutation.mutate()` |
| 3 | Generation prompt constructed from shot fields (description, angle, movement, etc.) | VERIFIED | `ImagenService.build_prompt()` assembles style prefix + scene context (script_text, 200-char truncated) + camera (shot_size, camera_angle) + description + action |
| 4 | Users can choose between style presets (Photorealistic, Cinematic, Animated) | FAILED | Style prefixes implemented in `ImagenService`; backend reads `project.storyboard_style`; but no UI selector exists and `storyboard_style` is not settable via any API endpoint or frontend control |
| 5 | Generated frames saved to frames table and displayed in gallery | VERIFIED | Endpoint writes PNG to `MEDIA_DIR/{project_id}/storyboard/{uuid}.png`, inserts `StoryboardFrame` with `generation_source=ai`, `onSuccess` invalidates `QUERY_KEYS.STORYBOARD_FRAMES(shot.id)` to refresh gallery |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/imagen_service.py` | Imagen prompt builder and image generation client | VERIFIED | Exists, substantive (109 lines), imported by storyboard.py |
| `backend/app/api/endpoints/storyboard.py` | Generate endpoint on storyboard router | VERIFIED | `generate_frame` at `POST /{project_id}/shots/{shot_id}/generate`, returns 201 `StoryboardFrameResponse` |
| `backend/app/config.py` | GOOGLE_CLOUD_PROJECT setting | VERIFIED | Lines 74-77: `GOOGLE_CLOUD_PROJECT`, `IMAGEN_MODEL`, `IMAGEN_REGION` all present |
| `backend/app/tests/test_storyboard_api.py` | Tests for generate endpoint | VERIFIED | `test_generate_frame` and `test_generate_frame_auto_select_false_when_existing` both exist; all 9 tests pass |
| `backend/requirements.txt` | google-cloud-aiplatform dependency | VERIFIED | Line 29: `google-cloud-aiplatform>=1.60.0` |
| `frontend/src/lib/api.tsx` | `api.generateFrame` method | VERIFIED | Lines 1170-1183: `POST /storyboard/{projectId}/shots/{shotId}/generate`, returns `Promise<StoryboardFrame>` |
| `frontend/src/components/Storyboard/FrameGalleryModal.tsx` | Enabled AI generate button with mutation wiring | VERIFIED | Lines 50-55: `generateMutation`; lines 125-136: enabled button; lines 223-228: error display |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `storyboard.py` | `imagen_service.py` | `from ...services.imagen_service import ImagenService` | WIRED | Line 13 import; line 239 instantiation; line 244 `build_prompt` call; line 258 `generate_image` call |
| `imagen_service.py` | `google.cloud.aiplatform` (vertexai) | `vertexai.init()` + `ImageGenerationModel.from_pretrained()` | WIRED | Lines 95-101 in `generate_image`; lazy import avoids import-time side effects |
| `storyboard.py` | `database.StoryboardFrame` | ORM insert with `generation_source="ai"` | WIRED | Lines 273-281: `StoryboardFrame(... generation_source="ai", generation_style=project.storyboard_style)` |
| `FrameGalleryModal.tsx` | `api.tsx` `generateFrame` | `api.generateFrame` in `useMutation` | WIRED | Line 51: `mutationFn: () => api.generateFrame(projectId, shot.id)` |
| `api.tsx` | `POST /storyboard/{projectId}/shots/{shotId}/generate` | `fetchWithTimeout` | WIRED | Lines 1171-1172 |
| `FrameGalleryModal.tsx` | `QUERY_KEYS.STORYBOARD_FRAMES` | `invalidateQueries` on success | WIRED | Lines 52-54: `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.STORYBOARD_FRAMES(shot.id) })` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SB-06 | 31-01-PLAN.md | ImagenService backbone for storyboard frame generation | SATISFIED | `imagen_service.py` created with `build_prompt` and `generate_image`; generate endpoint wired |
| SB-07 | 31-02-PLAN.md | User-facing AI generation flow | PARTIALLY SATISFIED | Generate button wired and functional; style selection missing from user flow |

### Anti-Patterns Found

No blockers detected. No TODO/FIXME/placeholder comments, no stub implementations, no empty handlers in the phase files.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

### Human Verification Required

#### 1. Live Imagen API call

**Test:** With valid Google Cloud credentials set (`GOOGLE_CLOUD_PROJECT`, ADC configured), open a project in Storyboard mode, click a shot to open the frame gallery, then click "Generate with AI."
**Expected:** Button shows Loader2 spinner + "Generating..." while pending; after ~5-30 seconds, a new frame appears in the gallery grid with an AI badge (Sparkles icon at top-right).
**Why human:** Automated tests monkeypatch `ImagenService.generate_image`; cannot verify live Vertex AI connectivity without credentials.

#### 2. Error state display

**Test:** With invalid or missing Google Cloud credentials, trigger "Generate with AI" in the modal.
**Expected:** The modal shows "Generation failed: ..." in red text below the gallery grid.
**Why human:** Requires a controlled failure of the Imagen API call; cannot verify network error paths in static analysis.

### Gaps Summary

One gap blocks full goal achievement: **style preset selection is not user-facing.**

The ROADMAP goal and success criterion #4 require that "users can choose between style presets (Photorealistic, Cinematic, Animated)." The backend `ImagenService` implements all three style prefixes in `_STYLE_PREFIXES` and reads the style from `project.storyboard_style`. However:

1. `storyboard_style` is absent from the `Project` TypeScript interface (`frontend/src/types/index.ts`) and from `ProjectUpdate` schema (`backend/app/models/schemas.py`).
2. No API endpoint accepts `storyboard_style` as a writable field — `ProjectUpdate` only exposes `title` and `framework`.
3. No UI control (dropdown, radio group, or button group) exists in `StoryboardView.tsx` or `FrameGalleryModal.tsx` for choosing a style.
4. As a result, `project.storyboard_style` is always `None` for all projects, and every generated frame uses the fallback "Cinematic film still." prefix regardless of what the user might want.

The remaining four success criteria are fully verified with working implementation and passing tests (9/9 storyboard API tests pass, TypeScript compiles clean).

---

_Verified: 2026-04-01_
_Verifier: Claude (gsd-verifier)_
