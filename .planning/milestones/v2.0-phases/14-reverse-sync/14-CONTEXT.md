# Phase 14: Reverse Sync - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

User-initiated action to push a character breakdown element into the project's `story.characters` PhaseData, creating a new supporting ListItem there. The screenplay stays as source of truth — this is advisory sync, not auto-rewriting. Only the `character` category supports reverse sync in this phase (SYNC-05).

</domain>

<decisions>
## Implementation Decisions

### Card group assignment
- Synced characters always land in the `supporting` card group (`item_type: "supporting"`)
- No dialog or picker — default to Supporting is safe since AI extraction doesn't know protagonist/antagonist intent; user reassigns in the Characters phase if needed
- Button appears on all character elements regardless of source (AI-extracted or user-created) — behavior is identical
- "Add to Characters" button only renders on the Characters category tab, not in any future combined view

### Character data mapping
- `element.name` → `content.name` (character name field)
- `element.description` → `content.role` (Role & Purpose field)
- `content.dialogue_style` is left blank — user fills in manually
- `item_type` = `"supporting"`
- `status` = `"draft"` (consistent with manually created items, no custom status needed)
- Endpoint lives under the breakdown router: `POST /api/breakdown/element/{element_id}/sync-to-project`
- Response is a lightweight status object: `{status: "created" | "already_exists", list_item_id: UUID}` — no full ListItem body needed

### Synced state & duplicate detection
- After sync, the "Add to Characters" button changes to a disabled "Synced" state on the ElementCard
- The frontend reads a `synced_to_characters` boolean on each BreakdownElementResponse — backend computes this at query time by checking whether a ListItem with a matching name exists in `story.characters` PhaseData
- Duplicate detection: case-insensitive name match (`LOWER()` comparison) against existing ListItems in `story.characters`
- When duplicate detected: endpoint returns `{status: "already_exists", list_item_id: <existing_id>}` with HTTP 200 — no new item created, no error
- Frontend response to already_exists: put button into "Synced" state (same as created), no error toast needed

### Extensibility scope
- Characters-only for this phase — no generic `target_phase`/`subsection_key` parameter
- No architectural prep for other categories (YAGNI)

</decisions>

<specifics>
## Specific Ideas

No specific references — standard approach preferred for all decisions.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ElementCard.tsx`: Already has `updateMutation`/`deleteMutation` infrastructure with optimistic updates — `syncMutation` follows the same pattern. Hover action row already exists for Edit/Delete icons.
- `_verify_element_ownership()` in `breakdown.py`: Reuse directly for the new sync endpoint
- `_verify_project_ownership()` in `breakdown.py`: Same pattern
- `list_items.py` create handler: `POST /{phase_data_id}` creates ListItems — sync endpoint calls this logic directly or queries the DB the same way

### Established Patterns
- `str()` cast on all UUID filter params for SQLite/PostgreSQL compat (established across all phases)
- `selectinload(BreakdownElement.scene_links)` on all element-returning queries
- Idempotent endpoints return 200 with a status field rather than 201 or 409 (scene link add already does this)
- `onSettled` in mutations invalidates both `BREAKDOWN_ELEMENTS` and `BREAKDOWN_SUMMARY` query keys

### Integration Points
- `story.characters` PhaseData: `phase="story"`, `subsection_key="characters"` — query must look up or create this PhaseData record
- `BreakdownElementResponse` schema: add `synced_to_characters: bool` field (computed, not stored)
- Supporting character card_group: `item_type="supporting"`, fields: `name`, `role`, `dialogue_style`
- `QUERY_KEYS.BREAKDOWN_ELEMENTS(projectId, 'character')`: invalidate after sync so synced_to_characters flag refreshes

</code_context>

<deferred>
## Deferred Ideas

- Reverse sync for other categories (locations, props, vehicles, wardrobe) — same pattern could extend to push locations into a locations list, etc. Not in scope for v2.0 but worth considering in a future milestone.

</deferred>

---

*Phase: 14-reverse-sync*
*Context gathered: 2026-03-17*
