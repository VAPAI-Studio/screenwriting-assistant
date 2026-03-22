---
plan: 31-01
phase: 31-ai-frame-generation-google-imagen
status: complete
completed: 2026-03-22
---

# Plan 31-01: ImagenService, Generate Endpoint, Config, Tests

## Objective
Create Google Vertex AI Imagen integration service, wire it into a generate endpoint on the storyboard router, update config/env/requirements, and add tests.

## What Was Built

- **`backend/app/services/imagen_service.py`**: `ImagenService` class with:
  - `build_prompt(shot_fields, storyboard_style, scene_context="")` — static method assembling prompt from style prefix, scene context (truncated 200 chars), camera composition, description, action, and professional suffix.
  - `generate_image(prompt)` — calls `vertexai.init` + `ImageGenerationModel.from_pretrained` + `generate_images`, returns PNG bytes. Raises `RuntimeError` on ImportError or API failure.

- **`backend/app/api/endpoints/storyboard.py`**: Added `generate_frame` endpoint:
  - `POST /{project_id}/shots/{shot_id}/generate` → 201 `StoryboardFrameResponse`
  - Reads `shot.script_text` as `scene_context`, `project.storyboard_style`, `shot.fields`
  - Saves PNG to `MEDIA_DIR/{project_id}/storyboard/{uuid}.png`
  - Auto-selects frame if no prior selected frame for that shot
  - Returns 502 on generation failure; cleans up partial file

- **`backend/app/config.py`**: Added `GOOGLE_CLOUD_PROJECT: str = ""`, `IMAGEN_MODEL: str = "imagen-3.0-generate-001"`, `IMAGEN_REGION: str = "us-central1"`

- **`backend/.env.example.txt`**: Added Google Cloud section with `GOOGLE_CLOUD_PROJECT`, `IMAGEN_MODEL`, `IMAGEN_REGION`

- **`backend/requirements.txt`**: Added `google-cloud-aiplatform>=1.60.0` under `# Google Cloud` section

- **`backend/app/tests/test_storyboard_api.py`**: Added 2 new tests:
  - `test_generate_frame` — monkeypatches `ImagenService.generate_image`, asserts 201, `generation_source=ai`, `generation_style=cinematic`, `is_selected=True`, file_path contains `/storyboard/` and `.png`
  - `test_generate_frame_auto_select_false_when_existing` — existing selected frame → new frame `is_selected=False`

## Key Files Modified/Created

- `backend/app/services/imagen_service.py` — new
- `backend/app/api/endpoints/storyboard.py` — generate_frame endpoint added
- `backend/app/config.py` — 3 new settings
- `backend/.env.example.txt` — Google Cloud section
- `backend/requirements.txt` — google-cloud-aiplatform
- `backend/app/tests/test_storyboard_api.py` — 2 new tests

## Commits

- `e20f673`: feat(31-01): ImagenService, generate endpoint, config, tests

## Self-Check: PASSED

- All 9 storyboard API tests pass ✓
- `ImagenService.build_prompt` includes scene_context, camera, description, action ✓
- Generate endpoint reads shot.script_text as scene_context ✓
- Auto-select logic correct (is_selected = not has_selected) ✓
- GOOGLE_CLOUD_PROJECT, IMAGEN_MODEL, IMAGEN_REGION in config ✓
- google-cloud-aiplatform>=1.60.0 in requirements.txt ✓
