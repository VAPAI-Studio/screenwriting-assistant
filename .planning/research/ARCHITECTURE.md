# Architecture: v3.0 Shotlist & Production Breakdown

**Domain:** Shotlist system, media uploads, and two-mode UI integration
**Researched:** 2026-03-19
**Confidence:** HIGH

---

## Two-Mode App Architecture

### Navigation Structure

Top-level toggle in Header: "Screenwriting" / "Script Breakdown"

- **Screenwriting mode:** Current workspace unchanged
- **Script Breakdown mode:** New 3-panel layout:
  - Left: Read-only script view OR assets view (toggle)
  - Center/Right: Shotlist table/panel
  - Right edge: AI chat sidebar

### Visual Identity Separation

- Screenwriting mode: Current color scheme (warm/neutral)
- Breakdown mode: Distinct scheme (cool/production — blues/greens/teals)
- Shared: Typography, spacing, component shapes maintain unity
- Implementation: CSS variables scoped to mode context class on root container

### Routing

```
/projects/:projectId              -> Screenwriting mode (existing)
/projects/:projectId/breakdown    -> Breakdown mode (new, default to shotlist)
```

---

## Data Model

### Shots Table

```sql
CREATE TABLE shots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_item_id UUID REFERENCES list_items(id) ON DELETE SET NULL,
    shot_number INTEGER NOT NULL,
    script_text TEXT,
    script_range JSONB,
    fields JSONB NOT NULL DEFAULT '{}',
    sort_order INTEGER NOT NULL DEFAULT 0,
    source VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);
CREATE INDEX idx_shots_project ON shots(project_id);
CREATE INDEX idx_shots_scene ON shots(scene_item_id);
```

`fields` JSONB stores all freeform text: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes, vfx.

### Asset Media Table

```sql
CREATE TABLE asset_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    element_id UUID REFERENCES breakdown_elements(id) ON DELETE SET NULL,
    shot_id UUID REFERENCES shots(id) ON DELETE SET NULL,
    file_type VARCHAR(20) NOT NULL,
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    original_filename TEXT NOT NULL,
    file_size_bytes INTEGER,
    metadata_ JSONB DEFAULT '{}',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_asset_media_element ON asset_media(element_id);
CREATE INDEX idx_asset_media_shot ON asset_media(shot_id);
```

### Project Table Addition

```sql
ALTER TABLE projects ADD COLUMN IF NOT EXISTS shotlist_stale BOOLEAN DEFAULT FALSE;
```

---

## API Endpoints

### Shots API (`/api/shots`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{project_id}` | List all shots grouped by scene |
| POST | `/{project_id}` | Create shot |
| GET | `/shot/{shot_id}` | Get single shot with media |
| PUT | `/shot/{shot_id}` | Update shot fields |
| DELETE | `/shot/{shot_id}` | Delete shot |
| PUT | `/{project_id}/reorder` | Batch reorder |

### Media API (`/api/media`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/upload/{project_id}` | Upload image or audio |
| GET | `/{project_id}` | List all media |
| GET | `/element/{element_id}` | Media for element |
| DELETE | `/{media_id}` | Delete media file + record |

### AI Chat Extension

Extend `/api/ai-chat` with breakdown context. When `mode=breakdown`, include shotlist data and breakdown elements. Support tool-use: create_shot, update_shot, add_element.

---

## Frontend Component Structure

```
BreakdownLayout
  +-- BreakdownHeader (mode toggle, project title)
  +-- BreakdownBody (3-column flex)
        +-- LeftPanel (toggleable)
        |     +-- PanelToggle [Script | Assets]
        |     +-- ScriptReadView (read-only with selection)
        |     |     +-- SelectionBar (floating "Add Shot")
        |     +-- AssetsPanel (breakdown elements + media)
        +-- CenterPanel
        |     +-- ShotlistPanel (table grouped by scene)
        |           +-- ShotRow (expandable, inline editable)
        +-- RightPanel
              +-- SidebarChat (extended for breakdown)
```

### New Files

| File | Purpose |
|------|---------|
| `Breakdown/BreakdownLayout.tsx` | 3-panel layout |
| `Breakdown/ScriptReadView.tsx` | Read-only script with selection |
| `Breakdown/SelectionBar.tsx` | Floating "Add Shot" bar |
| `Breakdown/ShotlistPanel.tsx` | Center shotlist table |
| `Breakdown/ShotRow.tsx` | Individual shot row |
| `Breakdown/AssetsPanel.tsx` | Assets with media |
| `Breakdown/MediaUploadZone.tsx` | Upload area |
| `Breakdown/MediaThumbnail.tsx` | Image/audio display |
| `Layout/ModeToggle.tsx` | Top-level mode switch |

### Modified Files

| File | Change |
|------|--------|
| `App.tsx` | Add breakdown routes |
| `Header.tsx` | Add mode toggle |
| `SidebarChat.tsx` | Add breakdown context |
| `api.tsx` | Add shots + media functions |
| `constants.ts` | Add query keys |

---

## Build Order

1. DB + Models (shots, asset_media, migrations)
2. Two-Mode UI Shell (ModeToggle, BreakdownLayout, routing)
3. Script Read View (read-only rendering, text selection)
4. Shot CRUD API
5. Shotlist Panel (table UI)
6. Text Selection -> Add Shot
7. Media Upload (backend + frontend, parallelizable with 4-6)
8. Assets Panel (left toggle, thumbnails, audio)
9. AI Chat for Breakdown
10. Staleness Hooks

---
*Architecture research: 2026-03-19*
