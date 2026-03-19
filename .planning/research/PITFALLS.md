# Pitfalls: v3.0 Shotlist & Production Breakdown

**Domain:** Shotlist system, media uploads, and two-mode UI added to existing app
**Researched:** 2026-03-19
**Confidence:** HIGH

---

## Critical Pitfalls

### P1: Two-Mode UI Refactor Breaks Existing Screenwriting Workflow

**What goes wrong:** Restructuring the app into two modes accidentally changes routing, state, or layout for the existing Screenwriting mode. Users open their project and the workspace looks different or navigation breaks.

**How to avoid:**
- The Screenwriting mode must be the EXACT existing workspace with zero changes to its components
- Mode toggle only controls which layout renders — existing routes/components untouched
- Add breakdown routes ALONGSIDE existing routes, never replace
- Test all existing Screenwriting workflows after adding mode toggle

**Phase to address:** Two-Mode UI Shell (first UI phase)

---

### P2: Text Selection API Unreliable Across Browsers

**What goes wrong:** `window.getSelection()` returns different results in Safari vs Chrome vs Firefox. Selected text doesn't map back to the correct script position. The "Add Shot" floating bar appears in wrong position or doesn't appear at all.

**How to avoid:**
- Use `mouseup` event to capture selection, not `selectionchange` (which fires too often)
- Store selection as `{sceneIndex, startOffset, endOffset, selectedText}` — not DOM positions
- Calculate floating bar position from selection bounding rect (`getRangeAt(0).getBoundingClientRect()`)
- Test in Safari explicitly — it handles selection differently in scrollable containers
- Dismiss selection bar on `mousedown` outside the script view

**Phase to address:** Text Selection → Add Shot phase

---

### P3: Media File Storage Grows Unbounded in Docker

**What goes wrong:** Images and audio files accumulate in the container's filesystem or mounted volume. No cleanup when elements are deleted. Docker volume grows to gigabytes. Container restart is slow.

**How to avoid:**
- Store media in a dedicated `MEDIA_DIR` (not mixed with book uploads)
- When an `asset_media` record is deleted, also delete the file from disk
- Set per-project media size limits (e.g., 500MB total)
- Generate thumbnails at upload time (not on-demand) to avoid repeated processing
- Add `file_size_bytes` to the model for tracking

**Phase to address:** Media Upload phase

---

### P4: Shotlist JSONB Fields Make Querying Difficult

**What goes wrong:** All shot fields stored in a single JSONB column means you can't easily query "all shots with camera_movement = 'dolly'" or sort by shot_size. JSONB querying in PostgreSQL is possible but verbose and non-obvious.

**How to avoid:**
- Accept this tradeoff — JSONB flexibility is more important than query convenience for freeform fields
- For common queries (by scene, by project), use proper indexed columns
- If specific field queries become needed later, add GIN index on the JSONB column
- Frontend does client-side filtering/sorting within the loaded shotlist

**Phase to address:** Data Model phase — acceptable tradeoff, just be aware

---

### P5: AI Chat Creates Invalid Shots

**What goes wrong:** AI chat can create/modify shots, but generates shots with missing required context (no scene link, no script text reference) or with field values that don't match the user's style.

**How to avoid:**
- AI-created shots must always link to a scene (require scene_item_id)
- AI-created shots get `source: 'ai'` flag so user can identify them
- AI modifications should show a diff/preview before applying
- Limit AI to modifying fields, not deleting shots

**Phase to address:** AI Chat for Breakdown phase

---

### P6: Bidirectional Sync Creates Circular Updates

**What goes wrong:** Same pitfall as v2.0 — script change marks shotlist stale, AI re-generates shots, which triggers another staleness check.

**How to avoid:**
- Reuse exact same pattern from v2.0: `shotlist_stale` is a flag, not a trigger
- User must explicitly click "Refresh" to re-process
- AI shot suggestions from re-extraction are additive, never replace user shots
- `source` field distinguishes user vs AI shots — AI never touches user-created shots

**Phase to address:** Staleness Hooks phase

---

### P7: Left Panel Toggle Loses State

**What goes wrong:** User is viewing assets panel, switches to script view to select text, adds a shot, switches back to assets — and the assets panel has reset (scroll position lost, category tab reset, expanded elements collapsed).

**How to avoid:**
- Both panels stay mounted in DOM, toggle via CSS `display: none` / `display: block`
- Do NOT unmount/remount — this destroys React component state
- React Query cache preserves data regardless of mount state

**Phase to address:** Assets Panel / Left Panel Toggle phase

---

## Technical Debt Patterns

| Shortcut | Cost | When Acceptable |
|----------|------|-----------------|
| All shot fields in JSONB (no typed columns) | Can't enforce field-level constraints | Always acceptable — freeform is the requirement |
| Local disk media storage (no CDN) | Slow for remote users, no redundancy | Acceptable for MVP; CDN is future |
| No audio waveform visualization | Less polished audio UX | Acceptable — native `<audio>` controls work |
| No shot thumbnail generation from script | Manual image upload only | Acceptable — AI storyboarding is future |

---

## Integration Gotchas

| Integration | Mistake | Correct Approach |
|-------------|---------|-----------------|
| Existing `Header.tsx` | Replacing header entirely for mode toggle | Add toggle component INSIDE existing header |
| Existing `BreakdownPage.tsx` | Trying to reuse it as the breakdown mode | Breakdown mode is a NEW layout; existing page components (CategoryTabs, etc.) can be imported individually |
| Existing `SidebarChat` | Creating a separate chat for breakdown | Extend existing SidebarChat with mode-aware context |
| Existing `api.tsx` | Creating a separate API module for breakdown | Add functions to existing api.tsx (consistent pattern) |
| `SelectionBar` positioning | Positioning relative to viewport | Position relative to the script view scroll container |
| Media upload | Mixing media and book upload directories | Separate `MEDIA_DIR` from `UPLOAD_DIR` |

---

## Performance Traps

| Trap | Prevention |
|------|-----------|
| Loading all shots + all media for all scenes | Load shots per scene lazily; thumbnails only |
| Full-size image rendering in asset panel | Generate and serve thumbnails (200px max) |
| Audio autoplay on shot expand | Play only on explicit user action |
| Re-rendering entire shotlist on single field edit | Memoize ShotRow components |
| Fetching breakdown elements + shots + media in parallel on page load | Waterfall: elements first, shots second, media thumbnails lazy |

---

## "Looks Done But Isn't" Checklist

- [ ] Text selection works when script view is scrolled down
- [ ] Shot numbering updates when shots are reordered or deleted
- [ ] Media files are deleted from disk when records are deleted
- [ ] AI chat sees the shotlist data (not just breakdown elements)
- [ ] Mode toggle preserves project context (don't lose unsaved work)
- [ ] Assets panel shows media thumbnails (not just element names)
- [ ] Audio playback has stop/pause (not just play)
- [ ] Shotlist is empty-state friendly (clear CTA when no shots exist)
- [ ] Two modes have visually distinct color schemes

---
*Pitfalls research: 2026-03-19*
