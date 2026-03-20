# Phase 22: Media Upload Backend - Research

**Researched:** 2026-03-19
**Domain:** File upload handling, image processing, media CRUD API (FastAPI + Pillow)
**Confidence:** HIGH

## Summary

Phase 22 implements backend infrastructure for uploading, storing, thumbnailing, and managing image and audio files linked to breakdown elements. The existing codebase already has the `AssetMedia` ORM model and Pydantic schemas (`AssetMediaCreate`, `AssetMediaResponse`) defined in Phase 17 (Data Foundation). The `docker-compose.yml` already mounts a `media_uploads` Docker volume at `/app/media`. The primary work is: (1) create a new `media.py` endpoint file, (2) add Pillow to requirements.txt for thumbnail generation, (3) bump the `RequestSizeLimitMiddleware` from 10MB to 25MB (to accommodate 20MB files plus form overhead), and (4) serve uploaded files via FastAPI's `StaticFiles` mount or a dedicated streaming endpoint.

The project already has an established upload pattern in `books.py` -- read file content, validate type/size, save to disk, create DB record. The media endpoint follows this exact pattern with the additions of thumbnail generation for images, linking to `element_id` (breakdown elements), and serving files back.

**Primary recommendation:** Create `backend/app/api/endpoints/media.py` following the `books.py` upload pattern. Add Pillow >=12.0 to requirements.txt. Store originals in `/app/media/{project_id}/` and thumbnails in `/app/media/{project_id}/thumbs/`. Mount `/app/media` as a StaticFiles directory at `/media` for direct file serving.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-05 | Media upload API endpoint exists (POST upload, GET list, DELETE) | New `media.py` endpoint with three routes; follows `shots.py` ownership pattern |
| MDIA-01 | User can upload image files (JPEG, PNG, WebP) to breakdown elements | POST endpoint accepts `UploadFile` + `element_id` form field; validates image extensions |
| MDIA-02 | User can upload audio files (MP3, WAV, M4A) to breakdown elements | Same POST endpoint handles audio; validates audio extensions; skips thumbnail step |
| MDIA-05 | User can delete uploaded media files | DELETE endpoint removes DB record + disk file + thumbnail file |
| MDIA-06 | Image uploads generate thumbnails on the server (via Pillow) | Pillow `Image.open().thumbnail((300,300))` with LANCZOS resampling, saved as WebP |
| MDIA-07 | Media upload endpoint enforces file type validation and size limits (20MB max) | Extension allowlist + file size check + Pillow open validation for images; middleware bump to 25MB |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.1.1 | Image open/validate, thumbnail generation, format conversion | De facto Python imaging library; only new dependency per project decision |
| FastAPI UploadFile | 0.110.0 (existing) | Multipart file upload handling | Already in stack; `python-multipart` 0.0.9 already installed |
| SQLAlchemy | 2.0.27 (existing) | AssetMedia model already defined | Existing ORM layer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| FastAPI StaticFiles | 0.110.0 (existing) | Serve uploaded media files via HTTP | Mount at `/media` for direct file access from frontend |
| uuid | stdlib | Generate unique filenames for stored files | Every upload -- never use user-provided filenames for disk storage |
| pathlib / os | stdlib | File path operations, directory creation | mkdir, file deletion, path joining |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pillow | python-magic for MIME validation | python-magic requires libmagic system dep not in slim Docker image; Pillow open() validates images sufficiently for MVP |
| StaticFiles mount | Custom FileResponse endpoint | StaticFiles is simpler and covers the use case; FileResponse needed only if auth-gated downloads required |
| Local disk storage | S3/MinIO | Project decision: local storage (Docker volume) for MVP; S3 is deferred |

**Installation:**
```bash
pip install Pillow>=12.0
```

**Version verification:**
- Pillow 12.1.1 verified via `pip install --dry-run Pillow` (published 2026-02-11)
- All other dependencies already in `requirements.txt`

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/endpoints/
│   └── media.py          # NEW: upload, list, delete endpoints
├── services/
│   └── media_service.py  # NEW: thumbnail generation, file validation
├── models/
│   ├── database.py       # AssetMedia model (EXISTING from Phase 17)
│   └── schemas.py        # AssetMediaCreate/Response (EXISTING from Phase 17)
└── ...
```

```
/app/media/                      # Docker volume mount point
└── {project_id}/
    ├── {uuid}.jpg               # Original uploads (UUID-named)
    ├── {uuid}.mp3
    └── thumbs/
        └── {uuid}_thumb.webp    # Generated thumbnails (WebP format)
```

### Pattern 1: File Upload Endpoint (follows books.py pattern)
**What:** POST endpoint accepting multipart form data with file + metadata fields
**When to use:** Every media upload
**Example:**
```python
# Source: Adapted from existing books.py upload pattern
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from uuid import UUID, uuid4
import os

router = APIRouter()

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

@router.post("/{project_id}", response_model=schemas.AssetMediaResponse, status_code=201)
async def upload_media(
    project_id: UUID,
    file: UploadFile = File(...),
    element_id: UUID = Form(None),
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_project_ownership(db, project_id, current_user.id)

    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        file_type = "image"
    elif ext in ALLOWED_AUDIO_EXTENSIONS:
        file_type = "audio"
    else:
        raise HTTPException(400, detail="Unsupported file type")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, detail="File too large. Max 20MB.")

    # Generate safe filename and save
    safe_name = f"{uuid4()}.{ext}"
    media_dir = os.path.join(MEDIA_ROOT, str(project_id))
    os.makedirs(media_dir, exist_ok=True)
    file_path = os.path.join(media_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Generate thumbnail for images
    thumbnail_path = None
    if file_type == "image":
        thumbnail_path = generate_thumbnail(file_path, media_dir)

    # Create DB record
    media = AssetMedia(
        project_id=str(project_id),
        element_id=str(element_id) if element_id else None,
        file_type=file_type,
        file_path=f"/media/{project_id}/{safe_name}",
        thumbnail_path=f"/media/{project_id}/thumbs/{safe_name.rsplit('.', 1)[0]}_thumb.webp" if thumbnail_path else None,
        original_filename=file.filename,
        file_size_bytes=len(content),
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media
```

### Pattern 2: Thumbnail Generation Service
**What:** Separate service function for image thumbnail generation using Pillow
**When to use:** After saving an image file to disk
**Example:**
```python
# Source: Pillow documentation + project conventions
from PIL import Image
import os

THUMBNAIL_SIZE = (300, 300)

def generate_thumbnail(original_path: str, media_dir: str) -> str:
    """Generate a WebP thumbnail from an image file.

    Returns the absolute path to the generated thumbnail.
    Raises ValueError if the file is not a valid image.
    """
    try:
        with Image.open(original_path) as img:
            # Convert RGBA to RGB for WebP compatibility
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            thumbs_dir = os.path.join(media_dir, "thumbs")
            os.makedirs(thumbs_dir, exist_ok=True)

            basename = os.path.splitext(os.path.basename(original_path))[0]
            thumb_path = os.path.join(thumbs_dir, f"{basename}_thumb.webp")
            img.save(thumb_path, "WEBP", quality=80)

            return thumb_path
    except Exception as e:
        raise ValueError(f"Invalid image file: {e}")
```

### Pattern 3: Project Ownership Verification (existing pattern)
**What:** Copy `_verify_project_ownership` locally into `media.py` as done in `shots.py`
**When to use:** Every media endpoint
**Example:**
```python
# Source: Copied from shots.py -- project convention to avoid cross-module coupling
def _verify_project_ownership(db: Session, project_id: UUID, user_id: UUID) -> database.Project:
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(user_id)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

### Pattern 4: StaticFiles Mount for Media Serving
**What:** Mount the media directory as a StaticFiles endpoint in main.py
**When to use:** To serve uploaded files directly via HTTP URL
**Example:**
```python
# In main.py
from fastapi.staticfiles import StaticFiles
import os

MEDIA_DIR = os.environ.get("MEDIA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media"))
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
```

### Anti-Patterns to Avoid
- **Using user-provided filenames for disk storage:** Filenames can contain path traversal attacks (`../../etc/passwd`). Always generate UUID-based filenames on the server; store original_filename in DB only.
- **Trusting Content-Type header alone:** Clients can send any Content-Type. Validate file extension AND attempt to open with Pillow for images.
- **Reading entire file into memory without size check:** Always check Content-Length header first (middleware), then validate after reading. For MVP with 20MB limit this is acceptable; for production, use streaming.
- **Storing absolute paths in the database:** Store relative URL paths (`/media/{project_id}/{filename}`) so the system works across deployments.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image thumbnailing | Custom resize with raw bytes | `Pillow Image.thumbnail()` | Handles aspect ratio, resampling, format conversion, edge cases |
| File serving | Custom endpoint reading bytes from disk | `FastAPI StaticFiles` mount | Handles Content-Type headers, caching, range requests automatically |
| Multipart parsing | Manual content-type parsing | `FastAPI UploadFile + File()` | python-multipart handles all encoding edge cases |
| UUID generation | Custom random strings | `uuid.uuid4()` | Collision-safe, standard library |
| Image format validation | Regex on magic bytes | `Pillow Image.open().verify()` or `.thumbnail()` | Pillow handles all format-specific validation internally |

**Key insight:** Pillow is the only new dependency. Everything else (UploadFile, StaticFiles, UUID) is already in the stack or stdlib.

## Common Pitfalls

### Pitfall 1: RequestSizeLimitMiddleware blocks 20MB uploads
**What goes wrong:** The existing middleware in `main.py` limits request bodies to 10MB (`RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024`). Any media upload over 10MB will be rejected with HTTP 413 before reaching the endpoint.
**Why it happens:** The middleware was configured for text/JSON payloads, not binary file uploads.
**How to avoid:** Increase the middleware limit to 25MB (20MB file + multipart overhead + form fields). The endpoint itself enforces the 20MB file-specific limit.
**Warning signs:** HTTP 413 "Request body too large" errors on file uploads.

### Pitfall 2: StaticFiles mount order conflicts with API routes
**What goes wrong:** If `app.mount("/media", StaticFiles(...))` is placed before `app.include_router(...)`, it can intercept API routes. But more critically, `mount()` creates a sub-application that is independent -- it won't go through the normal middleware stack.
**Why it happens:** StaticFiles is a separate ASGI application mounted at a path prefix.
**How to avoid:** Place the `app.mount("/media", ...)` call AFTER all `app.include_router()` calls in `main.py`. This is safe because mount paths don't conflict with `/api/` prefixed routes.
**Warning signs:** 404 errors on API routes that appear to be shadowed.

### Pitfall 3: RGBA/P mode images fail WebP thumbnail save
**What goes wrong:** PNG images with transparency (RGBA mode) or palette mode (P) can fail or produce unexpected results when saved as WebP/JPEG.
**Why it happens:** WebP lossy doesn't support all color modes natively.
**How to avoid:** Convert to RGB before thumbnailing: `if img.mode in ("RGBA", "P"): img = img.convert("RGB")`
**Warning signs:** Pillow raises `OSError` or produces corrupt thumbnails for transparent PNGs.

### Pitfall 4: File cleanup on DB save failure
**What goes wrong:** File is saved to disk but DB commit fails (unique constraint, connection error). Orphan files accumulate on disk.
**Why it happens:** File write and DB commit are not transactional.
**How to avoid:** Wrap in try/except -- if DB commit fails, delete the file and thumbnail from disk before re-raising.
**Warning signs:** Files on disk with no corresponding DB records.

### Pitfall 5: Forgetting to update Dockerfile for Pillow system deps
**What goes wrong:** Pillow 12.x on `python:3.11-slim` may need system libraries for certain image formats.
**Why it happens:** The slim image lacks some optional C libraries.
**How to avoid:** Pillow wheels for Python 3.11 are pre-built with most common formats (JPEG, PNG, WebP). The existing `gcc` and `libpq-dev` in the Dockerfile should be sufficient. Verify by running `python -c "from PIL import features; print(features.check('webp'))"` in the Docker build.
**Warning signs:** `ImportError` or `PIL.Image.open()` fails for specific formats.

### Pitfall 6: Test file uploads with TestClient
**What goes wrong:** Tests using `client.post()` with JSON body don't work for multipart uploads.
**Why it happens:** File uploads require multipart/form-data, not JSON.
**How to avoid:** Use `client.post(url, files={"file": (filename, content, mime_type)}, data={"element_id": str(uuid)})` format for TestClient.
**Warning signs:** 422 Validation Error saying `file` field is required.

## Code Examples

### Media Upload Test Pattern
```python
# Source: FastAPI TestClient docs + existing test patterns
import io
from PIL import Image

def _create_test_image(width=100, height=100, format="JPEG"):
    """Create a minimal test image in memory."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf

def test_upload_image(client, mock_auth_headers, db_session):
    project_id = _create_project_via_api(client, mock_auth_headers)
    img_buf = _create_test_image()

    resp = client.post(
        f"/api/media/{project_id}",
        files={"file": ("test.jpg", img_buf, "image/jpeg")},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_type"] == "image"
    assert data["original_filename"] == "test.jpg"
    assert data["thumbnail_path"] is not None
```

### Audio Upload Test Pattern
```python
def test_upload_audio(client, mock_auth_headers, db_session):
    project_id = _create_project_via_api(client, mock_auth_headers)
    # Audio files don't need real content for the upload endpoint
    # (no server-side processing beyond storage)
    audio_content = b"\x00" * 1024  # Minimal placeholder

    resp = client.post(
        f"/api/media/{project_id}",
        files={"file": ("test.mp3", audio_content, "audio/mpeg")},
        headers=mock_auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_type"] == "audio"
    assert data["thumbnail_path"] is None
```

### Delete with Disk Cleanup Pattern
```python
@router.delete("/{project_id}/{media_id}", status_code=204)
async def delete_media(
    project_id: UUID,
    media_id: UUID,
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_project_ownership(db, project_id, current_user.id)

    media = db.query(AssetMedia).filter(
        AssetMedia.id == str(media_id),
        AssetMedia.project_id == str(project_id),
    ).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete files from disk (best effort -- don't fail if already gone)
    for path_attr in [media.file_path, media.thumbnail_path]:
        if path_attr:
            abs_path = os.path.join(MEDIA_ROOT, path_attr.lstrip("/media/"))
            if os.path.exists(abs_path):
                os.remove(abs_path)

    db.delete(media)
    db.commit()
    return Response(status_code=204)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Image.ANTIALIAS` | `Image.Resampling.LANCZOS` | Pillow 9.1.0 (2022) | `ANTIALIAS` deprecated; use `Resampling.LANCZOS` enum |
| Saving thumbnails as JPEG | Save as WebP | Pillow 9+ / general trend | 25-34% smaller files; better quality at same size |
| `Image.resize()` for thumbnails | `Image.thumbnail()` | Always preferred | `thumbnail()` preserves aspect ratio automatically |
| Manual Content-Type checks | Extension + Pillow validation | Current best practice for MVP | Extension check is fast; Pillow open validates actual content |

**Deprecated/outdated:**
- `Image.ANTIALIAS`: Deprecated since Pillow 9.1.0. Use `Image.Resampling.LANCZOS` instead.
- `Image.open().verify()`: Can be used for validation but leaves the file in an unusable state. Prefer opening and calling `thumbnail()` directly -- if the file is invalid, Pillow raises an exception.

## Open Questions

1. **Element ID validation on upload**
   - What we know: `element_id` links media to a `BreakdownElement`. The FK has `ondelete="SET NULL"`.
   - What's unclear: Should the upload endpoint validate that the element exists and belongs to the project? The existing shot API doesn't validate `scene_item_id` exists.
   - Recommendation: Validate that `element_id` belongs to the project if provided (prevents cross-project data leaks). This is a simple query.

2. **Media directory path in config vs. hardcoded**
   - What we know: Docker Compose mounts `media_uploads` volume at `/app/media`. Config has `UPLOAD_DIR` for books.
   - What's unclear: Whether to add a `MEDIA_DIR` config setting or use a constant.
   - Recommendation: Add `MEDIA_DIR` to `config.py` Settings class, defaulting to `/app/media` (or `../media` relative to app). Mirrors existing `UPLOAD_DIR` pattern.

3. **Should `shot_id` be accepted on upload?**
   - What we know: AssetMedia has both `element_id` and `shot_id` FK columns.
   - What's unclear: Requirements only mention linking to breakdown elements, not shots. ADVM-03 (media on shots) is deferred to v3.1.
   - Recommendation: Accept `element_id` only for now. The `shot_id` column exists in the model but the form field is not exposed in this phase. Phase 23 or v3.1 can add it.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.2 |
| Config file | none -- pytest runs from `backend/` directory |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_media_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MDIA-01 | POST accepts JPEG/PNG/WebP images linked to elements | integration | `pytest app/tests/test_media_api.py::TestUploadMedia::test_upload_image -x` | No -- Wave 0 |
| MDIA-02 | POST accepts MP3/WAV/M4A audio files | integration | `pytest app/tests/test_media_api.py::TestUploadMedia::test_upload_audio -x` | No -- Wave 0 |
| MDIA-05 | DELETE removes DB record and disk file | integration | `pytest app/tests/test_media_api.py::TestDeleteMedia::test_delete_removes_file -x` | No -- Wave 0 |
| MDIA-06 | Image upload generates thumbnail via Pillow | integration | `pytest app/tests/test_media_api.py::TestUploadMedia::test_thumbnail_generated -x` | No -- Wave 0 |
| MDIA-07 | Upload rejects invalid types and files over 20MB | integration | `pytest app/tests/test_media_api.py::TestUploadValidation -x` | No -- Wave 0 |
| DATA-05 | GET lists media for project/element | integration | `pytest app/tests/test_media_api.py::TestListMedia -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_media_api.py -x`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `app/tests/test_media_api.py` -- covers MDIA-01, MDIA-02, MDIA-05, MDIA-06, MDIA-07, DATA-05
- [ ] Pillow install: `pip install Pillow>=12.0` and add to `requirements.txt`
- [ ] `MEDIA_DIR` temp directory fixture in conftest or test file for isolated test runs

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/models/database.py` lines 576-594 -- AssetMedia model already defined
- Existing codebase: `backend/app/models/schemas.py` lines 779-801 -- AssetMediaCreate/Response already defined
- Existing codebase: `backend/app/api/endpoints/books.py` -- established upload pattern (read, validate, save, DB record)
- Existing codebase: `docker-compose.yml` -- `media_uploads` volume already mounted at `/app/media`
- Existing codebase: `backend/app/middleware.py` -- `RequestSizeLimitMiddleware` currently 10MB
- [Pillow 12.1.1 documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html) -- thumbnail(), Resampling, save()
- `pip install --dry-run Pillow` -- verified 12.1.1 is current (published 2026-02-11)

### Secondary (MEDIUM confidence)
- [FastAPI Request Files tutorial](https://fastapi.tiangolo.com/tutorial/request-files/) -- UploadFile + Form() pattern
- [FastAPI Static Files tutorial](https://fastapi.tiangolo.com/tutorial/static-files/) -- StaticFiles mount pattern
- [FastAPI secure file upload guide](https://noone-m.github.io/2025-12-10-fastapi-file-upload/) -- UUID filename, extension validation, size limits

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Pillow is the only new dep; version verified via pip; all other deps exist
- Architecture: HIGH - Follows exact patterns from existing `books.py` and `shots.py` endpoints
- Pitfalls: HIGH - Middleware limit, file cleanup, RGBA conversion are well-documented issues
- Validation: HIGH - Test patterns match existing `test_shots_api.py` structure exactly

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable -- no fast-moving dependencies)
