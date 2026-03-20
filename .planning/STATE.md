---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Shotlist & Production Breakdown
status: unknown
stopped_at: Phase 24 context gathered
last_updated: "2026-03-20T13:25:03.982Z"
progress:
  total_phases: 9
  completed_phases: 7
  total_plans: 10
  completed_plans: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** From blank page to production-ready breakdown — AI helps you write the screenplay and then extracts everything you need to produce it.
**Current focus:** Phase 23 — assets-panel-media-display

## Current Position

Phase: 23 (assets-panel-media-display) — EXECUTING
Plan: 2 of 2

## Performance Metrics

**Velocity:**

- Total plans completed: 6 (v3.0) / 38 (lifetime)
- Average duration: 3.3min (v3.0) / see milestones for historical
- Total execution time: 0.33 hours (v3.0)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 17-data-foundation | 1 | 5min | 5min |
| 19-shot-crud-api-core-model | 1 | 3min | 3min |
| 20-shotlist-panel | 2 | 6min | 3min |
| 21-script-read-view-text-selection | 1 | 2min | 2min |
| 22-media-upload-backend | 1 | 4min | 4min |

**Recent Trend:**

- Last 5 plans: 19-01 (3min), 20-01 (4min), 20-02 (2min), 21-01 (2min), 22-01 (4min)
- Trend: improving

*Updated after each plan completion*
| Phase 18-two-mode-ui-shell P01 | 12 | 3 tasks | 4 files |
| Phase 18-two-mode-ui-shell P02 | 3 | 3 tasks | 3 files |
| Phase 20 P02 | 2 | 2 tasks | 5 files |
| Phase 21 P01 | 2 | 2 tasks | 3 files |
| Phase 22 P01 | 4 | 3 tasks | 7 files |
| Phase 23 P01 | 3 | 2 tasks | 7 files |
| Phase 23 P02 | 3 | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.

v2.0 decisions carried forward:

- Breakdown is NOT a template phase — cross-cutting derived view
- Bidirectional sync on save/generate (staleness flag), not real-time
- Single breakdown_elements table with category column + JSONB metadata
- `delta/` directory for incremental migrations

v3.0 decisions (from research):

- JSONB for shot fields — extensible, matches freeform requirement
- CSS variables scoped to mode context for visual identity separation
- Pillow only new backend dep; lean on existing stack
- Media stored locally (Docker volume), not S3/CDN for MVP
- Extend SidebarChat — don't create separate chat component
- Script view is read-only — no rich text editor needed

v3.0 decisions (from execution):

- Shot.scene_item_id uses ON DELETE SET NULL so shots survive scene deletion
- AssetMedia has dual nullable FKs (element_id, shot_id) with SET NULL
- AssetMedia.shot cascade="all, delete-orphan" cleans up media when shot deleted
- [Phase 18-two-mode-ui-shell]: Used .breakdown-mode CSS class for palette override — consistent with Tailwind class-based theming
- [Phase 18-two-mode-ui-shell]: ModeToggle self-guards via useParams returning null when projectId absent
- [Phase 18-two-mode-ui-shell]: BreakdownPage import commented out (not deleted) in App.tsx — reserved for Phase 23; TypeScript noUnusedLocals prevented keeping as live unused import
- [Phase 19-shot-crud-api-core-model]: _verify_project_ownership copied locally into shots.py -- avoids cross-module coupling
- [Phase 19-shot-crud-api-core-model]: Reorder returns 403 for foreign shot IDs (not 404) -- ownership violation vs not-found
- [Phase 19-shot-crud-api-core-model]: PUT fields replacement (not merge) -- consistent with JSONB column semantics
- [Phase 20-shotlist-panel]: Frontend spreads existing fields before overriding changed key in update mutation -- prevents JSONB wipe since PUT replaces entire fields dict
- [Phase 20-shotlist-panel]: Scene grouping is frontend-only -- flat API response grouped by scene_item_id with unassigned shots last
- [Phase 20-shotlist-panel]: 5 visible columns in table (shot_size, camera_angle, camera_movement, description, action); remaining 8 fields deferred to detail/expansion view
- [Phase 20-shotlist-panel]: Empty state CTA creates shot with scene_item_id: null (unassigned) -- simplest approach, user can reassign later
- [Phase 20-shotlist-panel]: Reorder swaps sort_order values between adjacent shots -- minimizes API payload vs recalculating all
- [Phase 20-shotlist-panel]: Action controls (reorder + delete) use opacity-0 group-hover:opacity-100 for hover-reveal
- [Phase 20]: Empty state CTA creates shot with scene_item_id: null (unassigned)
- [Phase 20]: Reorder swaps sort_order values between adjacent shots -- minimizes API payload
- [Phase 20]: Action controls use opacity-0 group-hover:opacity-100 for hover-reveal
- [Phase 21-script-read-view-text-selection]: Text selection uses selectionchange event with Safari mouseup fallback for cross-browser support
- [Phase 21-script-read-view-text-selection]: Scene resolution walks from selection anchor to nearest [data-scene-id] ancestor via closest()
- [Phase 21-script-read-view-text-selection]: No new dependencies -- reused existing React Query, lucide-react
- [Phase 22-media-upload-backend]: UUID-based filenames on disk prevent path traversal; original filename stored in DB only
- [Phase 22-media-upload-backend]: Element ownership validated on upload to prevent cross-project data leaks
- [Phase 22-media-upload-backend]: RequestSizeLimitMiddleware bumped from 10MB to 25MB for 20MB files + multipart overhead
- [Phase 22-media-upload-backend]: shot_id not exposed as upload form field (ADVM-03 deferred to v3.1)
- [Phase 23-assets-panel-media-display]: Both Script and Assets views always mounted in DOM (display:none toggle) to preserve scroll position and expanded state across toggles (ASST-05)
- [Phase 23-assets-panel-media-display]: Audio overlap prevention refs in AssetsPanel as useRef for Plan 02 consumption
- [Phase 23-assets-panel-media-display]: Empty categories hidden entirely rather than shown with zero count
- [Phase 23-assets-panel-media-display]: uploadMedia uses Authorization-only header (no Content-Type) for browser multipart boundary
- [Phase 23]: Audio overlap uses stopCurrentAudioRef pattern -- stores stop function, not tracking ID

### Pending Todos

None yet.

### Blockers/Concerns

- Scene ListItem ID stability: element_scene_links cascades on ListItem deletion; links break if scenes regenerated (carried from v2.0)
- Text Selection API cross-browser testing needed (Safari quirks) — research P2

## Session Continuity

Last session: 2026-03-20T13:25:03.979Z
Stopped at: Phase 24 context gathered
Resume file: .planning/phases/24-ai-chat-for-breakdown/24-CONTEXT.md
