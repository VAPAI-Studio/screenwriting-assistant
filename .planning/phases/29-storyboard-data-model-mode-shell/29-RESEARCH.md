# Phase 29: Storyboard Data Model & Mode Shell - Research

**Researched:** 2026-03-21
**Domain:** SQLAlchemy data modeling, FastAPI CRUD endpoints, React mode switching / CSS theming
**Confidence:** HIGH

## Summary

Phase 29 introduces the third application mode -- Storyboard -- with a new database model (`StoryboardFrame` linked to `Shot`), a full CRUD API, a project-level `storyboard_style` setting, and a new CSS identity (deep purple/violet). This phase is heavily pattern-reuse: every component has a direct precedent in the existing codebase.

The backend work follows the exact same patterns used for the Shot model (Phase 17/19) and media upload (Phase 22): SQLAlchemy ORM model, Pydantic v2 schemas, FastAPI router, delta migration SQL. The frontend work follows the ModeToggle dropdown (Phase 18) and the `breakdown-mode` CSS class pattern for theming. No new libraries are needed.

**Primary recommendation:** Follow existing patterns exactly. The StoryboardFrame model mirrors the Shot model structure. The mode toggle extends the existing Radix UI dropdown from two to three options. The storyboard CSS theme follows the `breakdown-mode` CSS variable override pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Third mode is called "Storyboard"
- Color identity: deep purple/violet (distinct from green/screenwriting and steel-blue/breakdown)
- Mode toggle has three options: Screenwriting / Breakdown / Storyboard
- Mode stored in app state same way as existing two-mode toggle
- StoryboardFrame model links frames to shots via `shot_id` (FK to Shot, ON DELETE CASCADE)
- Fields: `shot_id`, `file_path`, `thumbnail_path`, `file_type` (image/video), `is_selected` (bool), `generation_source` (user/ai), `generation_style` (photorealistic/cinematic/animated/null)
- Multiple frames per shot allowed; exactly one can be `is_selected=true` at a time
- When `is_selected` is set on a frame, others for same shot are set to false
- `generation_style` stored per-frame
- `storyboard_style` field added to Project model: enum (photorealistic/cinematic/animated), nullable/default null
- CRUD API base route: `/api/storyboard/{project_id}`
- List frames by shot: `GET /api/storyboard/{project_id}/shots/{shot_id}/frames`
- Create frame: `POST /api/storyboard/{project_id}/shots/{shot_id}/frames` (multipart upload)
- Update is_selected: `PATCH /api/storyboard/{project_id}/frames/{frame_id}`
- Delete frame: `DELETE /api/storyboard/{project_id}/frames/{frame_id}` (also deletes file from disk)
- Reuse existing upload infrastructure from Phase 22
- Storyboard page route: same project page, third mode shows StoryboardView component
- Purple identity via accent color on mode tab and chrome elements
- Empty state when no shots/frames: minimal placeholder
- Delta migration for new table `storyboard_frames` and new column `storyboard_style` on `projects`

### Claude's Discretion
- Exact purple CSS color values (e.g., violet-600/purple-700 range)
- Thumbnail generation strategy (can skip, just copy file_path to thumbnail_path)
- Exact error handling and validation details
- File storage location for storyboard frames (use same `uploads/` directory as media)

### Deferred Ideas (OUT OF SCOPE)
- AI generation itself (Phase 31)
- Storyboard grid of shot cards (Phase 30)
- Frame gallery modal (Phase 30)
- Project settings UI for storyboard_style (Phase 30)
- Thumbnail generation pipeline (use file_path as thumbnail_path for now)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SB-01 | Storyboard mode shell with purple identity and three-option mode toggle | Mode toggle pattern from ModeToggle.tsx, CSS theming from index.css `.breakdown-mode` class, route from App.tsx |
| SB-02 | StoryboardFrame data model with CRUD API and project storyboard_style setting | ORM pattern from database.py Shot model, CRUD from shots.py, schemas from schemas.py, delta migration from 003_shot_ai_columns.sql |
</phase_requirements>

## Standard Stack

### Core (already in project -- no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | (existing) | ORM model for StoryboardFrame | Already used for all models |
| FastAPI | (existing) | CRUD API endpoints | Already used for all endpoints |
| Pydantic v2 | (existing) | Request/response schemas | Already used for all schemas |
| React 18 | (existing) | Frontend components | Already used |
| Radix UI DropdownMenu | (existing) | Mode toggle dropdown | Already used in ModeToggle.tsx |
| Tailwind CSS | (existing) | Styling/theming | Already used with HSL CSS variables |
| React Router | (existing) | Route for storyboard mode | Already used |
| React Query | (existing) | Data fetching for storyboard frames | Already used |
| Pillow (PIL) | (existing) | Thumbnail generation (if used) | Already in media_service.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | (existing) | Icon for Storyboard mode in toggle | Use `Film` or `LayoutGrid` icon |

### Alternatives Considered
None -- this phase uses 100% existing stack.

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure (new files only)
```
backend/
  app/
    api/endpoints/
      storyboard.py          # New CRUD router
    models/
      database.py            # Add StoryboardFrame model, StoryboardStyle enum
      schemas.py             # Add StoryboardFrame schemas
  migrations/delta/
    004_storyboard_frames.sql # New table + project column

frontend/src/
  components/
    Layout/
      ModeToggle.tsx          # Extend from 2 to 3 options
    Storyboard/
      StoryboardView.tsx      # Empty shell component
  index.css                   # Add .storyboard-mode CSS class
  App.tsx                     # Add storyboard route
  lib/
    api.tsx                   # Add storyboard frame API methods
    constants.ts              # Add ROUTES.PROJECT_STORYBOARD, QUERY_KEYS
  types/
    index.ts                  # Add StoryboardFrame type
```

### Pattern 1: ORM Model (follow Shot model exactly)
**What:** SQLAlchemy model with UUID PK, FK to shots, standard timestamps
**When to use:** For the StoryboardFrame table
**Example:**
```python
# Source: backend/app/models/database.py (Shot model pattern)
class GenerationSource(str, enum.Enum):
    USER = "user"
    AI = "ai"

class StoryboardStyle(str, enum.Enum):
    PHOTOREALISTIC = "photorealistic"
    CINEMATIC = "cinematic"
    ANIMATED = "animated"

class StoryboardFrame(Base):
    __tablename__ = "storyboard_frames"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shot_id = Column(UUID(as_uuid=True), ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(1000), nullable=False)
    thumbnail_path = Column(String(1000), nullable=True)
    file_type = Column(String(20), nullable=False)  # "image" or "video"
    is_selected = Column(Boolean, default=False)
    generation_source = Column(String(20), default="user")  # "user" or "ai"
    generation_style = Column(String(30), nullable=True)  # photorealistic/cinematic/animated/null
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    shot = sa_relationship("Shot", back_populates="storyboard_frames")
```

### Pattern 2: CRUD Router (follow shots.py exactly)
**What:** FastAPI router with project ownership verification, standard CRUD
**When to use:** For `/api/storyboard/` endpoints
**Example:**
```python
# Source: backend/app/api/endpoints/shots.py (pattern)
router = APIRouter()

def _verify_project_ownership(db, project_id, user_id):
    project = db.query(database.Project).filter(
        database.Project.id == str(project_id),
        database.Project.owner_id == str(user_id)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

def _verify_shot_in_project(db, shot_id, project_id):
    shot = db.query(database.Shot).filter(
        database.Shot.id == str(shot_id),
        database.Shot.project_id == str(project_id)
    ).first()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found in project")
    return shot
```

### Pattern 3: CSS Mode Theming (follow breakdown-mode exactly)
**What:** CSS class on `<html>` that overrides HSL CSS variables
**When to use:** For storyboard mode's purple identity
**Example:**
```css
/* Source: frontend/src/index.css (.breakdown-mode pattern) */
.storyboard-mode {
    /* Backgrounds -- cool slate-noir with violet undertone */
    --background: 270 10% 5%;
    --foreground: 270 15% 95%;

    --card: 270 8% 9%;
    --card-foreground: 270 10% 92%;

    --muted: 270 8% 16%;
    --muted-foreground: 270 8% 52%;

    /* Accent -- deep violet (replaces warm amber / steel blue) */
    --accent: 263 70% 58%;
    --accent-foreground: 0 0% 98%;

    --primary: 263 70% 58%;
    --primary-foreground: 270 10% 8%;

    --secondary: 270 8% 16%;
    --secondary-foreground: 270 10% 88%;

    /* ... remaining overrides follow breakdown-mode structure ... */
    --border: 270 8% 18%;
    --input: 270 8% 12%;
    --ring: 263 70% 58%;

    --surface: 270 8% 12%;
    --surface-hover: 270 8% 16%;
    --border-strong: 270 8% 24%;
}
```

### Pattern 4: Mode Toggle Extension (follow ModeToggle.tsx)
**What:** Radix DropdownMenu with three items instead of two
**When to use:** Extending the mode toggle to include Storyboard
**Key insight:** The existing ModeToggle uses URL-based mode detection (`location.pathname.endsWith('/breakdown')`). Add a similar check for `/storyboard`.

### Pattern 5: Delta Migration (follow 003_shot_ai_columns.sql)
**What:** Idempotent SQL file in `backend/migrations/delta/`
**When to use:** For creating the storyboard_frames table and adding storyboard_style to projects
**Example:**
```sql
-- Migration 004: Storyboard frames table and project style setting
CREATE TABLE IF NOT EXISTS storyboard_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shot_id UUID NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
    file_path VARCHAR(1000) NOT NULL,
    thumbnail_path VARCHAR(1000),
    file_type VARCHAR(20) NOT NULL,
    is_selected BOOLEAN DEFAULT FALSE,
    generation_source VARCHAR(20) DEFAULT 'user',
    generation_style VARCHAR(30),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_storyboard_frames_shot_id ON storyboard_frames(shot_id);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS storyboard_style VARCHAR(30);
```

### Pattern 6: File Upload with Disk Cleanup (follow media.py)
**What:** Multipart upload, file validation, disk storage, DB record, cleanup on delete
**When to use:** For the create-frame endpoint
**Key detail:** Reuse the same `settings.MEDIA_DIR` and the `generate_thumbnail` function from `media_service.py`. Store frames under `media/{project_id}/storyboard/`.

### Anti-Patterns to Avoid
- **Don't create a separate file storage config:** Use the existing `settings.MEDIA_DIR` path. Just add a `storyboard/` subdirectory.
- **Don't use SQLAlchemy Enum type for file_type/generation_source:** The existing codebase uses `String(20)` for similar fields (see Shot.source). This avoids migration headaches.
- **Don't add video support in the upload endpoint yet:** Accept only image uploads in Phase 29 (the `file_type` column supports "video" for future use, but the upload validation should match existing ALLOWED_IMAGE_EXTENSIONS).
- **Don't build thumbnail generation pipeline:** Per CONTEXT.md, just copy `file_path` to `thumbnail_path` for now.
- **Don't forget to add the relationship back-reference on Shot:** Add `storyboard_frames = sa_relationship("StoryboardFrame", back_populates="shot", cascade="all, delete-orphan")` to the Shot model.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File upload handling | Custom multipart parser | FastAPI `UploadFile` + `File()` | FastAPI handles streaming, temp files, content-type |
| Thumbnail generation | Custom image resize | `media_service.generate_thumbnail()` | Already handles PIL, WebP, error cases |
| Mode theming | JS-based theme switching | CSS variable class on `<html>` | Existing pattern, zero JS overhead, CSS transitions work |
| Dropdown menu | Custom dropdown | Radix UI `DropdownMenu` | Already used, accessible, keyboard-nav |
| Project ownership check | Inline ownership SQL | `_verify_project_ownership()` helper | Duplicated in every endpoint file, same pattern |
| is_selected exclusivity | Application-level locking | Single UPDATE + WHERE in transaction | SQLAlchemy session handles atomicity |

**Key insight:** Every piece of this phase has a direct precedent. The risk is deviation from patterns, not missing functionality.

## Common Pitfalls

### Pitfall 1: is_selected Atomicity
**What goes wrong:** Two concurrent requests both set is_selected=true on different frames for the same shot, resulting in two selected frames.
**Why it happens:** The deselect-others + select-one sequence is not atomic without care.
**How to avoid:** In a single transaction: first `UPDATE storyboard_frames SET is_selected = FALSE WHERE shot_id = :shot_id`, then `UPDATE storyboard_frames SET is_selected = TRUE WHERE id = :frame_id`. SQLAlchemy session commit handles this atomically.
**Warning signs:** Multiple frames showing is_selected=true for the same shot in the database.

### Pitfall 2: Forgetting CASCADE on Shot Delete
**What goes wrong:** Deleting a shot orphans storyboard frames in the database.
**Why it happens:** Missing `ON DELETE CASCADE` on the shot_id FK.
**How to avoid:** Use `ForeignKey("shots.id", ondelete="CASCADE")` in the ORM model AND `REFERENCES shots(id) ON DELETE CASCADE` in the migration SQL.
**Warning signs:** storyboard_frames rows with shot_id pointing to non-existent shots.

### Pitfall 3: File Cleanup on Frame Delete
**What goes wrong:** Deleting a frame from the database leaves the image file on disk, consuming storage.
**Why it happens:** Forgetting to add the os.remove() call before/after the DB delete.
**How to avoid:** Follow the delete_media pattern from media.py: resolve file_path to absolute path, os.remove(), then db.delete().
**Warning signs:** Files accumulating in `media/{project_id}/storyboard/` with no DB references.

### Pitfall 4: SQLite Test Compatibility for New Enum
**What goes wrong:** Tests fail because SQLite doesn't support PostgreSQL ENUM types.
**Why it happens:** The conftest.py patches Enum columns to String(50), but only for columns already in `Base.metadata` at fixture time.
**How to avoid:** Use `String(20)` or `String(30)` for `file_type`, `generation_source`, and `generation_style` columns instead of `Enum()`. This matches the existing Shot model's `source` field pattern (which uses `String(20)`).
**Warning signs:** `sqlalchemy.exc.CompileError` mentioning ENUM in test output.

### Pitfall 5: Mode Toggle URL Detection
**What goes wrong:** The mode toggle doesn't correctly identify which mode is active.
**Why it happens:** The existing code uses `pathname.endsWith('/breakdown')` which won't work for `/storyboard`.
**How to avoid:** Update the mode detection logic to check for both `/breakdown` and `/storyboard` suffixes.
**Warning signs:** Mode toggle shows wrong active mode indicator.

### Pitfall 6: Missing CSS Class Cleanup on Unmount
**What goes wrong:** Navigating from Storyboard to another page leaves purple theming.
**Why it happens:** The `storyboard-mode` class isn't removed from `<html>` on component unmount.
**How to avoid:** Follow the BreakdownLayout pattern: `useEffect(() => { document.documentElement.classList.add('storyboard-mode'); return () => { document.documentElement.classList.remove('storyboard-mode'); }; }, []);`
**Warning signs:** Purple accent colors persisting after leaving storyboard mode.

## Code Examples

### Backend: StoryboardFrame Pydantic Schemas
```python
# Source: backend/app/models/schemas.py (AssetMediaResponse pattern)
class StoryboardFrameCreate(BaseModel):
    file_type: str = Field(..., pattern="^(image|video)$")
    generation_source: str = Field(default="user", pattern="^(user|ai)$")
    generation_style: Optional[str] = Field(None, pattern="^(photorealistic|cinematic|animated)$")

class StoryboardFrameUpdate(BaseModel):
    is_selected: Optional[bool] = None

class StoryboardFrameResponse(BaseModel):
    id: UUID
    shot_id: UUID
    file_path: str
    thumbnail_path: Optional[str] = None
    file_type: str
    is_selected: bool = False
    generation_source: str = "user"
    generation_style: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
```

### Backend: is_selected Toggle Logic
```python
# Source: Pattern derived from Shot update logic
def _set_selected_frame(db: Session, shot_id: str, frame_id: str):
    """Set a frame as selected, deselecting all others for the same shot."""
    # Deselect all frames for this shot
    db.query(database.StoryboardFrame).filter(
        database.StoryboardFrame.shot_id == shot_id
    ).update({"is_selected": False})
    # Select the target frame
    db.query(database.StoryboardFrame).filter(
        database.StoryboardFrame.id == frame_id
    ).update({"is_selected": True})
    db.commit()
```

### Frontend: Mode Detection Logic
```typescript
// Source: frontend/src/components/Layout/ModeToggle.tsx (extended)
const isBreakdown = location.pathname.endsWith('/breakdown');
const isStoryboard = location.pathname.endsWith('/storyboard');
const currentMode = isStoryboard ? 'storyboard'
  : isBreakdown ? 'breakdown'
  : 'screenwriting';
```

### Frontend: StoryboardView Shell
```tsx
// Source: Pattern from BreakdownLayout.tsx (simplified)
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Film } from 'lucide-react';

export function StoryboardView() {
  const { projectId } = useParams<{ projectId: string }>();

  // Apply storyboard-mode CSS class
  useEffect(() => {
    document.documentElement.classList.add('storyboard-mode');
    return () => {
      document.documentElement.classList.remove('storyboard-mode');
    };
  }, []);

  return (
    <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
      <div className="text-center space-y-3">
        <Film className="h-12 w-12 mx-auto text-muted-foreground/40" />
        <h2 className="text-lg font-semibold text-foreground">Storyboard</h2>
        <p className="text-sm text-muted-foreground">
          Frame-by-frame visual planning for your shots.
        </p>
      </div>
    </div>
  );
}
```

### Backend: Router Registration in main.py
```python
# Source: backend/app/main.py (shots_ep pattern)
from .api.endpoints import storyboard as storyboard_ep
app.include_router(storyboard_ep.router, prefix="/api/storyboard", tags=["storyboard"])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No mode system | Two-mode toggle (Screenwriting/Breakdown) | Phase 18 | URL-based mode detection + CSS class theming |
| No file uploads | Media upload with thumbnail generation | Phase 22 | Pillow + UUID filenames + `/media/` static mount |
| No delta migrations | Automatic delta migration at startup | Phase 17 | `db_migrator.py` applies numbered SQL files |

**Existing precedents this phase follows:**
- Shot model (Phase 17/19): Same ORM pattern, FK to project, cascade deletes
- Media upload (Phase 22): Same file handling, same `settings.MEDIA_DIR`
- ModeToggle (Phase 18): Same Radix dropdown, same URL-based detection
- breakdown-mode CSS (Phase 18): Same CSS variable override pattern
- Delta migration (Phase 26): Same `NNN_description.sql` naming convention

## Open Questions

1. **Video file upload support in Phase 29?**
   - What we know: The `file_type` field supports "video", but the current upload infrastructure (media.py) only allows image + audio extensions
   - What's unclear: Whether video uploads should be accepted now or only in Phase 30+
   - Recommendation: Accept only images for now (matching existing ALLOWED_IMAGE_EXTENSIONS). The schema supports video for forward compatibility.

2. **Storyboard style on ProjectUpdate schema?**
   - What we know: `storyboard_style` is added to the Project model
   - What's unclear: Whether to expose it via the existing ProjectUpdate schema or create a separate endpoint
   - Recommendation: Add it to ProjectUpdate (or create a PATCH `/api/storyboard/{project_id}/settings` endpoint). The CONTEXT.md defers the settings UI to Phase 30, but the API should be ready.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `backend/app/tests/conftest.py` (SQLite in-memory) |
| Quick run command | `cd backend && source venv/bin/activate && pytest app/tests/test_storyboard_api.py -x` |
| Full suite command | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SB-01 | Mode toggle renders three options, storyboard route loads | manual-only | Visual check in browser | N/A |
| SB-01 | Storyboard CSS class applies violet accent | manual-only | Visual check in browser | N/A |
| SB-02 | StoryboardFrame CRUD: create frame via upload | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_create_frame -x` | No -- Wave 0 |
| SB-02 | StoryboardFrame CRUD: list frames by shot | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_list_frames -x` | No -- Wave 0 |
| SB-02 | StoryboardFrame CRUD: update is_selected | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_update_selected -x` | No -- Wave 0 |
| SB-02 | StoryboardFrame CRUD: delete frame | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_delete_frame -x` | No -- Wave 0 |
| SB-02 | is_selected exclusivity (set one deselects others) | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_selected_exclusivity -x` | No -- Wave 0 |
| SB-02 | Project storyboard_style column exists | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_project_style -x` | No -- Wave 0 |
| SB-02 | Frontend TypeScript compiles | build | `cd frontend && npm run build` | Existing |

### Sampling Rate
- **Per task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_storyboard_api.py -x`
- **Per wave merge:** `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Phase gate:** Full suite green + `cd frontend && npm run build` before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/app/tests/test_storyboard_api.py` -- covers SB-02 (CRUD operations, is_selected exclusivity, project style)
- [ ] No new conftest fixtures needed -- existing `client`, `mock_auth_headers`, `db_session` cover all needs

## Sources

### Primary (HIGH confidence)
- `backend/app/models/database.py` -- Shot model, AssetMedia model patterns (lines 542-597)
- `backend/app/api/endpoints/shots.py` -- CRUD endpoint pattern (full file)
- `backend/app/api/endpoints/media.py` -- File upload pattern with disk cleanup (full file)
- `backend/app/models/schemas.py` -- Pydantic v2 schema patterns (ShotCreate, ShotResponse, AssetMediaResponse)
- `frontend/src/components/Layout/ModeToggle.tsx` -- Mode toggle implementation (full file)
- `frontend/src/index.css` -- CSS variable theming via `.breakdown-mode` class (lines 50-88)
- `backend/migrations/delta/README.md` -- Delta migration conventions
- `backend/app/services/db_migrator.py` -- Migration runner (auto-applies at startup)
- `backend/app/services/media_service.py` -- Thumbnail generation with Pillow

### Secondary (MEDIUM confidence)
- `backend/app/config.py` -- `MEDIA_DIR` configuration (line 65)
- `frontend/tailwind.config.js` -- HSL CSS variable color system

### Tertiary (LOW confidence)
- None -- all findings are from existing codebase analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- 100% existing libraries, no new dependencies
- Architecture: HIGH -- every pattern has a direct codebase precedent
- Pitfalls: HIGH -- derived from actual codebase patterns and known SQLite/Enum issues
- CSS theming: HIGH -- `.breakdown-mode` pattern is proven and documented

**Research date:** 2026-03-21
**Valid until:** Indefinite (patterns are internal to this codebase)
