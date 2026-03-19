# Research Summary: v3.0 Shotlist & Production Breakdown

**Synthesized:** 2026-03-19

---

## Key Findings

### Stack
- **1 new backend dep:** Pillow (image processing/thumbnails)
- **0-1 new frontend dep:** @tanstack/react-table (may already be installed)
- Everything else uses existing stack: FastAPI StaticFiles, Selection API, native audio, React Context, Radix UI
- Do NOT add: Tiptap/Slate, Howler.js, ffmpeg, boto3, Zustand

### Features
- Core interaction: highlight script text → floating "Add Shot" bar → create shot in shotlist
- All shot fields are freeform text (JSONB) — no rigid dropdowns per user requirement
- Standard fields: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes
- Two-mode UI: Screenwriting (unchanged) vs Script Breakdown (new layout)
- Media: image + audio uploads for pre-production references on breakdown elements
- AI chat: extend existing SidebarChat with shotlist awareness and modification capability

### Architecture
- **Data model:** `shots` table with JSONB fields, `asset_media` table for uploads, `shotlist_stale` on projects
- **Two-mode UI:** Top-level toggle in header, conditional layout rendering, CSS variable scoping for distinct visual identity
- **Breakdown layout:** 3 panels — left (script/assets toggle), center (shotlist), right (AI chat)
- **Build order:** DB → Two-Mode Shell → Script View → Shot CRUD → Shotlist UI → Selection → Media → Assets → AI Chat → Staleness

### Pitfalls
- **P1:** Two-mode refactor must NOT change existing Screenwriting components
- **P2:** Selection API needs cross-browser testing (Safari quirks)
- **P3:** Media storage needs cleanup on delete + size limits
- **P4:** JSONB fields tradeoff accepted — flexibility over queryability
- **P5:** AI-created shots need source tracking and scene links
- **P6:** Staleness pattern reused exactly from v2.0 (no circular triggers)
- **P7:** Left panel toggle must preserve state (mount both, toggle visibility)

---

## Consensus Recommendations

1. **Minimal deps** — Pillow only new backend dep; lean on existing stack
2. **JSONB for shot fields** — extensible, matches freeform requirement
3. **Separate visual identity via CSS variables** — not separate stylesheets
4. **Reuse staleness pattern** — proven in v2.0, no redesign needed
5. **Extend SidebarChat** — don't create separate chat component
6. **Script view is read-only** — no rich text editor, just rendered text with Selection API
7. **Media stored locally** — Docker volume, not S3/CDN for MVP
8. **Build two-mode shell first** — all other features nest inside it

---

## Risk Areas

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Two-mode refactor destabilizes existing workspace | HIGH | Screenwriting mode = exact existing code, no modifications |
| Text selection → shot mapping reliability | MEDIUM | Store selected text + offsets, test cross-browser |
| Media storage unbounded growth | MEDIUM | Per-project limits, cleanup on delete |
| AI chat modifying shots incorrectly | LOW | Source tracking, preview before apply |

---

## Scope Boundaries

**In scope for v3.0:**
- Two-mode UI (Screenwriting / Script Breakdown)
- Interactive shotlist (text selection → Add Shot → freeform fields)
- Shot CRUD API + table UI
- Media uploads (image + audio) for breakdown elements
- AI chat in breakdown mode with shot awareness
- Shotlist staleness hooks

**Explicitly out of scope:**
- Scheduling, budgeting, department assignments
- Export (PDF, storyboards)
- Video uploads, transcoding
- Real-time collaborative editing
- Camera/lens presets
- Storyboard drawing tools
- AI auto-storyboard generation

---
*Summary: 2026-03-19*
