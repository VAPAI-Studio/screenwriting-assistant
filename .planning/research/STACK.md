# Technology Stack: v3.0 Shotlist & Production Breakdown

**Project:** v3.0 Shotlist, Media Uploads, Two-Mode UI
**Researched:** 2026-03-19
**Confidence:** HIGH

---

## Core Verdict: Minimal New Dependencies

The existing stack handles 90%+ of v3.0 needs. Key addition is Pillow for image processing.

---

## Recommended Stack Additions

### Backend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `Pillow` | `>=10.0.0` | Image validation and thumbnail generation for media uploads | Standard Python imaging; lightweight; no conflicts |

No other new backend dependencies:
- FastAPI `StaticFiles` (built-in) serves uploaded media
- Existing upload patterns from `books.py` are reusable
- Existing `ai_provider.py` handles AI chat in breakdown mode

### Frontend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `@tanstack/react-table` | `^8.21.3` | Shotlist table with sorting/filtering | Check if already installed from v2.0 |

No other new frontend dependencies:
- Browser native `Selection API` for text selection -> Add Shot
- Browser native `<audio>` element for audio playback
- React Context (built-in) for two-mode state toggle
- Existing Radix UI (Dialog, Tabs, etc.) for all UI needs

---

## What NOT to Add

| Library | Why Not |
|---------|---------|
| Tiptap/Slate/Lexical | Script view is read-only |
| Howler.js/Wavesurfer.js | Native `<audio>` sufficient |
| ffmpeg/pydub | No transcoding needed |
| boto3/S3 | Local disk storage sufficient for MVP |
| Zustand/Jotai | Single boolean toggle doesn't warrant state library |
| React DnD/dnd-kit | Defer drag-and-drop reordering |
| shadcn/ui | Existing Radix + Tailwind sufficient |

---

## Config Changes

- Route-aware request size limits: 20MB for media uploads vs 10MB default
- Media-specific settings: allowed file types, max dimensions, storage path
- Separate media volume in Docker

## Database Schema Preview

- `shots` table with JSONB freeform fields, linked to project + script text range
- `shot_elements` junction table (shot <-> breakdown element)
- `asset_media` table (element_id FK, file_path, file_type, thumbnail_path)
- `shotlist_stale` flag on projects table (mirrors `breakdown_stale`)

## Integration Points

- Reuse upload pattern from `books.py`
- Reuse React Query patterns for CRUD
- Reuse Radix Dialog/Tabs components
- Reuse staleness hook pattern from v2.0
- Extend `SidebarChat` with breakdown mode context

---
*Stack research: 2026-03-19*
