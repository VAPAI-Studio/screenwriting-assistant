# Requirements: v3.0 Shotlist & Production Breakdown

**Defined:** 2026-03-19
**Core Value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.

## v3.0 Requirements

### Two-Mode UI

- [x] **MODE-01**: App has a top-level toggle in the header switching between "Screenwriting" and "Script Breakdown" modes
- [x] **MODE-02**: Screenwriting mode renders the existing workspace with zero changes to existing components
- [x] **MODE-03**: Script Breakdown mode renders a distinct 3-panel layout (left panel, center shotlist, right chat)
- [x] **MODE-04**: Screenwriting and Breakdown modes have visually distinct color schemes while maintaining design unity (shared typography, spacing, component shapes)
- [x] **MODE-05**: Mode toggle preserves project context (no data loss on switch)

### Shotlist

- [x] **SHOT-01**: User can create a shot manually via "Add Shot" button with freeform text fields
- [x] **SHOT-02**: Shots have freeform text fields: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes
- [x] **SHOT-03**: Shots are grouped by scene with scene headers in the shotlist panel
- [x] **SHOT-04**: User can edit shot fields inline in the shotlist table
- [x] **SHOT-05**: User can delete shots
- [x] **SHOT-06**: Shots have a sort_order and can be reordered within a scene
- [x] **SHOT-07**: Shotlist panel displays as a table/grid in the center-right area of breakdown mode
- [x] **SHOT-08**: Empty state shows clear CTA when no shots exist

### Script Selection

- [ ] **SELC-01**: Left panel in breakdown mode shows a read-only rendering of the screenplay content
- [ ] **SELC-02**: User can highlight/select text in the read-only script view
- [ ] **SELC-03**: On text selection, a floating bar appears showing line count and "+ Add Shot" button
- [ ] **SELC-04**: Clicking "+ Add Shot" creates a new shot pre-populated with the selected script text and linked to the corresponding scene
- [ ] **SELC-05**: Selection bar dismisses on click outside or pressing X

### Media Uploads

- [ ] **MDIA-01**: User can upload image files (JPEG, PNG, WebP) to breakdown elements (characters, locations, props, etc.)
- [ ] **MDIA-02**: User can upload audio files (MP3, WAV, M4A) to breakdown elements
- [ ] **MDIA-03**: Uploaded images display as thumbnails in the assets panel
- [ ] **MDIA-04**: Uploaded audio files have playable controls (play, pause, stop) in the assets panel
- [ ] **MDIA-05**: User can delete uploaded media files
- [ ] **MDIA-06**: Image uploads generate thumbnails on the server (via Pillow)
- [ ] **MDIA-07**: Media upload endpoint enforces file type validation and size limits (20MB max)

### Assets Panel

- [ ] **ASST-01**: Left panel has a toggle between "Script" view and "Assets" view
- [ ] **ASST-02**: Assets view shows existing breakdown elements grouped by category (Characters, Locations, Props, Wardrobe, Vehicles)
- [ ] **ASST-03**: Each element in assets view shows its attached media (image thumbnails, audio players)
- [ ] **ASST-04**: User can upload media directly from the assets panel via drag-and-drop or file picker
- [ ] **ASST-05**: Toggling between Script and Assets preserves panel state (scroll position, expanded items)

### AI Chat in Breakdown

- [ ] **CHAT-01**: Right sidebar in breakdown mode shows the AI chat (extends existing SidebarChat)
- [ ] **CHAT-02**: AI chat in breakdown mode has context awareness of the current project's shotlist data
- [ ] **CHAT-03**: AI chat in breakdown mode has context awareness of the current project's breakdown elements
- [ ] **CHAT-04**: AI chat can create new shots via conversation (user confirms before creation)
- [ ] **CHAT-05**: AI chat can modify existing shot fields via conversation (user confirms before changes)

### Sync

- [ ] **SYNC-01**: Script content changes (save/generate) set `shotlist_stale = true` on the project
- [ ] **SYNC-02**: Breakdown mode shows a staleness banner when shotlist is stale
- [ ] **SYNC-03**: Character name changes in Screenwriting mode propagate to Breakdown (via existing staleness pattern)
- [ ] **SYNC-04**: Staleness hooks are placed in the same locations as v2.0 breakdown_stale hooks

### Data Model & API

- [x] **DATA-01**: `shots` table exists with project_id, scene_item_id, shot_number, script_text, script_range (JSONB), fields (JSONB), sort_order, source
- [x] **DATA-02**: `asset_media` table exists with project_id, element_id, shot_id, file_type, file_path, thumbnail_path, original_filename, file_size_bytes, metadata (JSONB)
- [x] **DATA-03**: `shotlist_stale` boolean column added to projects table
- [x] **DATA-04**: Shot CRUD API endpoints exist (GET list, POST create, GET single, PUT update, DELETE)
- [ ] **DATA-05**: Media upload API endpoint exists (POST upload, GET list, DELETE)
- [x] **DATA-06**: Idempotent delta migration for new tables (follows existing `delta/` pattern)

## v3.1 Requirements (Deferred)

### AI Auto-Generation

- **AUTO-01**: AI can auto-generate a full shotlist from script content
- **AUTO-02**: AI-generated shots are marked with source='ai' and distinguishable from user shots

### Advanced Media

- **ADVM-01**: Audio waveform visualization in media player
- **ADVM-02**: Image annotation/markup on reference images
- **ADVM-03**: Media can be attached to individual shots (not just elements)

### Shot Management

- **SMGT-01**: Drag-and-drop shot reordering
- **SMGT-02**: Shot duplication
- **SMGT-03**: Batch shot operations (multi-select, bulk delete)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Scheduling/calendar | Different product domain, PROJECT.md defers |
| Budget/cost tracking | Different product domain, PROJECT.md defers |
| Export to PDF/storyboard | Separate feature pass |
| Video upload/playback | Requires transcoding infrastructure |
| Real-time collaborative editing | Save-triggered sync per PROJECT.md |
| Camera/lens preset database | Freeform text sufficient per user requirement |
| Storyboard drawing tools | Different product; image upload covers this |
| Shot diagram / overhead view | Different product category |
| Department assignments | PROJECT.md defers |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MODE-01 | Phase 18 | Complete |
| MODE-02 | Phase 18 | Complete |
| MODE-03 | Phase 18 | Complete |
| MODE-04 | Phase 18 | Complete |
| MODE-05 | Phase 18 | Complete |
| SHOT-01 | Phase 19 | Complete |
| SHOT-02 | Phase 19 | Complete |
| SHOT-03 | Phase 20 | Complete |
| SHOT-04 | Phase 20 | Complete |
| SHOT-05 | Phase 20 | Complete |
| SHOT-06 | Phase 20 | Complete |
| SHOT-07 | Phase 20 | Complete |
| SHOT-08 | Phase 20 | Complete |
| SELC-01 | Phase 21 | Pending |
| SELC-02 | Phase 21 | Pending |
| SELC-03 | Phase 21 | Pending |
| SELC-04 | Phase 21 | Pending |
| SELC-05 | Phase 21 | Pending |
| MDIA-01 | Phase 22 | Pending |
| MDIA-02 | Phase 22 | Pending |
| MDIA-03 | Phase 23 | Pending |
| MDIA-04 | Phase 23 | Pending |
| MDIA-05 | Phase 22 | Pending |
| MDIA-06 | Phase 22 | Pending |
| MDIA-07 | Phase 22 | Pending |
| ASST-01 | Phase 23 | Pending |
| ASST-02 | Phase 23 | Pending |
| ASST-03 | Phase 23 | Pending |
| ASST-04 | Phase 23 | Pending |
| ASST-05 | Phase 23 | Pending |
| CHAT-01 | Phase 24 | Pending |
| CHAT-02 | Phase 24 | Pending |
| CHAT-03 | Phase 24 | Pending |
| CHAT-04 | Phase 24 | Pending |
| CHAT-05 | Phase 24 | Pending |
| SYNC-01 | Phase 25 | Pending |
| SYNC-02 | Phase 25 | Pending |
| SYNC-03 | Phase 25 | Pending |
| SYNC-04 | Phase 25 | Pending |
| DATA-01 | Phase 17 | Complete |
| DATA-02 | Phase 17 | Complete |
| DATA-03 | Phase 17 | Complete |
| DATA-04 | Phase 19 | Complete |
| DATA-05 | Phase 22 | Pending |
| DATA-06 | Phase 17 | Complete |

**Coverage:**
- v3.0 requirements: 45 total
- Mapped to phases: 45
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
