# Phase 17: Data Foundation - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Database schema for shots, asset media, and shotlist staleness. Creates SQLAlchemy models, Pydantic schemas, and an idempotent delta migration. No API endpoints or frontend — those are Phase 19+.

</domain>

<decisions>
## Implementation Decisions

### Shot-Element Linking
- Create `shot_elements` junction table in this phase (not deferred)
- Simple link only: shot_id + element_id, no role/context field
- Shots use hard delete (not soft delete) — user-created, no AI re-extraction concern
- Cascade deletes on junction rows when shot is deleted

### Media File Organization
- Per-project folders: `media/{project_id}/images/` and `media/{project_id}/audio/`
- Thumbnails alongside originals: `media/{project_id}/thumbnails/{uuid}_thumb.{ext}`
- No per-project total size limit for now — rely on 20MB per-file limit only
- Separate Docker volume for media (distinct from existing `uploads/` for books)

### Script Text Storage
- Store selected text + scene index + character offsets: `script_range` JSONB = `{scene_index, start_offset, end_offset, content_hash}`
- Include content hash of scene text at selection time — enables stale offset detection
- `scene_item_id` FK (nullable, ON DELETE SET NULL) for relational queries, PLUS `scene_index` in JSONB for position data
- FK breaks gracefully if scenes are regenerated (SET NULL, not CASCADE)

### Media Target
- `asset_media` has both `element_id` and `shot_id` FKs (both nullable) — media can attach to a breakdown element OR a specific shot

### Claude's Discretion
- Exact Pydantic schema field names and validation
- Index strategy on new tables
- Column type choices (VARCHAR lengths, etc.)
- Delta migration numbering (next after 001)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BreakdownElement` model: pattern for project-scoped, category-typed, source-tracked entities with JSONB metadata
- `ElementSceneLink` model: pattern for junction tables with source tracking
- `BreakdownRun` model: pattern for audit trail records
- `breakdown_stale` column on Project: pattern for `shotlist_stale`

### Established Patterns
- `metadata_` Column alias to avoid SQLAlchemy MetaData clash — use same pattern for JSONB columns
- VARCHAR(50) for extensible category-like columns (not PG ENUM)
- `source` field with values like 'ai'/'user' for tracking origin
- `sort_order` Integer column for orderable items
- `server_default=func.now()` for created_at, `onupdate=func.now()` for updated_at
- UUID primary keys via `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
- `sa_relationship` with `back_populates` and `cascade="all, delete-orphan"` for parent-owned collections

### Integration Points
- `database.py`: Add new models after the existing BreakdownRun class (~line 533)
- `Project` model: Add `shotlist_stale` column and relationships to new models
- `delta/`: Next migration file is `002_shotlist_tables.sql`
- `BreakdownElement` model: `asset_media` FK references this table

</code_context>

<specifics>
## Specific Ideas

- Follow the exact same pattern as v2.0 Phase 9 — that foundation worked well
- `script_range` JSONB shape: `{"scene_index": 1, "start_offset": 0, "end_offset": 150, "content_hash": "abc123"}`
- Shot `fields` JSONB stores all freeform fields: shot_size, camera_angle, camera_movement, lens, description, action, dialogue, sound, characters, environment, props, equipment, notes

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-data-foundation*
*Context gathered: 2026-03-19*
