---
plan: 29-01
phase: 29-storyboard-data-model-mode-shell
status: complete
completed: 2026-03-21
---

# Plan 29-01: StoryboardFrame Model, Migration, Schemas, CRUD API + Tests

## Objective
Create the StoryboardFrame data model, delta migration, Pydantic schemas, and full CRUD API for storyboard frames, plus add storyboard_style to the Project model.

## What Was Built

- **Delta migration 004**: `backend/migrations/delta/004_storyboard_frames.sql` — Creates `storyboard_frames` table with FK `REFERENCES shots(id) ON DELETE CASCADE`, index on `shot_id`, and adds `storyboard_style VARCHAR(30)` column to `projects`.

- **StoryboardFrame ORM model**: Added to `backend/app/models/database.py`. Uses `String(20)`/`String(30)` for `file_type`, `generation_source`, `generation_style` (NOT Enum, for SQLite test compatibility). FK uses `ondelete="CASCADE"`. Shot model has `storyboard_frames = sa_relationship("StoryboardFrame", ...)` back-ref.

- **Project model update**: `storyboard_style = Column(String(30), nullable=True)` added after `shotlist_stale`.

- **Pydantic schemas**: `StoryboardFrameResponse` and `StoryboardFrameUpdate` in `backend/app/models/schemas.py`.

- **CRUD router**: `backend/app/api/endpoints/storyboard.py` — 4 endpoints:
  - `POST /{project_id}/shots/{shot_id}/frames` (multipart upload, 201)
  - `GET /{project_id}/shots/{shot_id}/frames` (list by shot)
  - `PATCH /{project_id}/frames/{frame_id}` (is_selected with exclusivity)
  - `DELETE /{project_id}/frames/{frame_id}` (with file disk cleanup)
  - Registered in `main.py` at prefix `/api/storyboard`

- **Tests**: `backend/app/tests/test_storyboard_api.py` — 7/7 tests pass including `test_selected_exclusivity` and `test_create_frame_wrong_project`.

## Key Files Modified

- `backend/migrations/delta/004_storyboard_frames.sql` — new
- `backend/app/models/database.py` — StoryboardFrame model, storyboard_style on Project, back-ref on Shot
- `backend/app/models/schemas.py` — StoryboardFrameResponse, StoryboardFrameUpdate
- `backend/app/api/endpoints/storyboard.py` — new CRUD router
- `backend/app/main.py` — router registration
- `backend/app/tests/test_storyboard_api.py` — new test file

## Commits

- `f58da67`: feat(29-01): StoryboardFrame model, migration 004, CRUD API, and tests

## Self-Check: PASSED

- Migration SQL has `CREATE TABLE IF NOT EXISTS storyboard_frames` ✓
- Migration SQL has `REFERENCES shots(id) ON DELETE CASCADE` ✓
- ORM model uses `String(20)` for file_type/generation_source (not Enum) ✓
- `is_selected` exclusivity handled with bulk UPDATE then single UPDATE ✓
- File disk cleanup on delete ✓
- Router registered at `/api/storyboard` ✓
- 7/7 tests pass ✓
- Full backend suite: 121 passed, 1 pre-existing failure (test_session_isolation) ✓
