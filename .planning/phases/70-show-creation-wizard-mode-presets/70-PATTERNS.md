# Phase 70: Show Creation Wizard (mode + presets) - Pattern Map

**Mapped:** 2026-06-17
**Files analyzed:** 5 (4 modified, 1 new helper module possible)
**Analogs found:** 5 / 5 (all in-repo, exact or role-match)

> Frontend-only phase. All analogs are real components in this repo — prefer them over RESEARCH/UI-SPEC generic snippets. The dominant reuse target is the `CreateProjectModal` clickable-card pattern, copied verbatim into `CreateShowModal`.

## CRITICAL Integration Findings (read before planning)

These three facts change how plans must be written — they are not obvious from CONTEXT.md alone:

1. **`continuity_mode` does NOT exist anywhere in the frontend yet.** `grep` for `continuity_mode`/`ContinuityMode` across `frontend/src` returns zero hits. The frontend `Show` interface (`src/types/index.ts:453-460`) and `ShowCreate` (`:462-465`) both omit it. The TS union must be created from scratch — there is no existing frontend enum to follow. Mirror the backend `ContinuityMode` str-enum (`backend/app/models/schemas.py:914-921`, values `connected | anthology | standalone`), but the **wizard only offers `connected` + `anthology`** (D-02).

2. **`episode_duration_minutes` is a BIBLE field, NOT a Show field.** It lives on `BibleUpdate`/`BibleResponse` (backend `schemas.py:972,982`; frontend `types/index.ts:473,481`), and is persisted via `PUT /api/shows/{id}/bible` (`api.updateBible`, `api.tsx:1323`). It is **absent from `ShowCreate`/`ShowResponse`** (backend `schemas.py:922-963`). Consequence: a preset that seeds duration (Microserie=2, Serie conectada=22) **cannot send duration in the `createShow` payload** — `createShow` only carries `{ title, description, continuity_mode }`. The seeded duration must be written with a **second call to `api.updateBible(show.id, { episode_duration_minutes })`** chained after `createShow` succeeds (the new show auto-provisions a bible; `ShowDetail.tsx:21-23` fetches it via `getBible`). The planner MUST account for this two-call sequence; do NOT assume a single create payload.

3. **There is no frontend `ShowUpdate` type.** `api.updateShow` is typed `Partial<ShowCreate>` (`api.tsx:1299`). Once `continuity_mode` is added to `ShowCreate`, `Partial<ShowCreate>` automatically allows sending `{ continuity_mode }` on edit — no new type needed, but the planner should add `continuity_mode` to `ShowCreate` (not a separate interface).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/components/Shows/CreateShowModal.tsx` (modify) | component (modal) | request-response (mutation) | `frontend/src/components/Projects/CreateProjectModal.tsx` | exact |
| `frontend/src/types/index.ts` (modify) | model (type defs) | n/a | existing `Show`/`ShowCreate` block + backend `ContinuityMode` enum | role-match |
| `frontend/src/lib/api.tsx` (modify, likely no change) | service (fetch wrapper) | request-response | existing `createShow`/`updateShow`/`updateBible` | exact (already supports payload) |
| `frontend/src/components/Shows/BibleEditor.tsx` (modify) OR new edit-mode control near it | component | request-response (mutation) | `CreateProjectModal` card pattern + `BibleEditor` `updateBibleMutation` | role-match |
| `frontend/src/lib/constants.ts` (maybe — preset card config) | config | n/a | `BIBLE_SECTIONS`/`DURATION_PRESETS` arrays | role-match |

## Pattern Assignments

### `frontend/src/components/Shows/CreateShowModal.tsx` (component, request-response)

**Analog:** `frontend/src/components/Projects/CreateProjectModal.tsx` (clickable-card pattern) + the file's own existing structure.

**Modal shell, imports & mutation pattern** — `CreateShowModal.tsx:1-35` is the base to extend. It already has the Radix Dialog shell, `useMutation(api.createShow)`, `onSuccess` invalidate+navigate, and a `handleSubmit`. Add `continuity_mode` + `seasonArc` state and a chained bible update (see Integration Finding #2). Current submit:
```typescript
// CreateShowModal.tsx:32-35  — extend payload with continuity_mode; chain updateBible for seeded duration
const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  createShowMutation.mutate({ title, description: description || undefined });
};
```

**Clickable-card pattern to copy VERBATIM** — `CreateProjectModal.tsx:131-164`. This is the single most load-bearing excerpt for the phase. The three preset cards reuse it exactly (selected styling, amber icon chip, amber dot, `space-y-2.5` wrapper):
```tsx
{mode === 'template' && (
  <div className="space-y-2.5">
    {templates.map((tmpl: TemplateListItem) => {
      const isSelected = selectedTemplate === tmpl.id;
      const Icon = TEMPLATE_ICON_MAP[tmpl.icon] || Film;
      return (
        <button
          key={tmpl.id}
          type="button"
          onClick={() => setSelectedTemplate(tmpl.id)}
          className={`w-full text-left flex items-center gap-4 p-4 rounded-xl border transition-all duration-200
            ${isSelected
              ? 'border-amber-500/40 bg-amber-500/5 glow-amber'
              : 'border-border hover:border-muted-foreground/20 hover:bg-muted/30'
            }`}
        >
          <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-colors
            ${isSelected ? 'bg-amber-500/15 text-amber-400' : 'bg-muted text-muted-foreground'}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-foreground">{tmpl.name}</div>
            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{tmpl.description}</p>
          </div>
          {isSelected && (
            <div className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
          )}
        </button>
      );
    })}
  </div>
)}
```
Adaptation for presets: replace `templates.map` with a static array of 3 presets (`{ label, helper, icon, mode, duration }`), `isSelected = selectedPreset === preset.id`, single-select state, Spanish `label` in the title slot, English `helper` in the `<p>` slot. UI-SPEC `70-UI-SPEC.md:88-104` pins the exact icons (`Zap`/`Link`/`LayoutGrid`), copy, and a `Continuity` section label above the cards. Note: UI-SPEC `text-sm font-semibold` for card titles vs. the analog's `font-medium` — follow the UI-SPEC (semibold).

**Season-arc conditional reveal (D-07)** — reuse the modal's own description-textarea styling, `CreateShowModal.tsx:77-84`, gated on a connected preset:
```tsx
<textarea
  className="w-full rounded-lg border border-border bg-input px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 transition-all resize-none"
  rows={3}
/>
```
Wrap in `{isConnected && (...)}` with `animate-fade-up` per UI-SPEC `:106-113`. Label/placeholder map to `BIBLE_SECTIONS` "Season Arc" (`constants.ts:360`) so it writes to `bible_season_arc` via `updateBible`.

**Submit/CTA disabled + pending pattern** — `CreateShowModal.tsx:88-98`. Extend the `disabled` guard to also require a selected preset (UI-SPEC validation `:139`):
```tsx
<Button type="submit" disabled={!title || createShowMutation.isPending}>
  {createShowMutation.isPending ? 'Creating...' : 'Create Show'}
</Button>
```

---

### `frontend/src/types/index.ts` (model)

**Analog:** the existing `Show`/`ShowCreate` block (`:450-465`) + backend `ContinuityMode` (`backend/app/models/schemas.py:914-921`).

Current state (must extend — no `continuity_mode` present):
```typescript
// types/index.ts:453-465
export interface Show {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string | null;
}
export interface ShowCreate {
  title: string;
  description?: string;
}
```
Add a TS union mirroring the backend enum and thread it through both interfaces:
```typescript
export type ContinuityMode = 'connected' | 'anthology' | 'standalone';
// Show: add  continuity_mode: ContinuityMode;
// ShowCreate: add  continuity_mode?: ContinuityMode;   // optional; backend defaults to 'anthology'
```
Convention note: the codebase uses string-literal unions and string enums (e.g. `Framework`); a plain union type matches the lighter existing `Show` types. Include all three values for type-completeness even though the wizard only offers two (D-02).

---

### `frontend/src/lib/api.tsx` (service) — likely NO change required

**Analog:** itself. `createShow` (`:1289-1297`) sends `JSON.stringify(data)` and `updateShow` (`:1299-1307`) is `Partial<ShowCreate>` — both transparently forward any new `ShowCreate` field once the type is extended. `updateBible` (`:1323`) already exists for the seeded-duration write. The planner should confirm no api change is needed beyond the type extension flowing through.
```typescript
async createShow(data: ShowCreate): Promise<Show> { /* body: JSON.stringify(data) */ }
async updateShow(id: string, data: Partial<ShowCreate>): Promise<Show> { /* ... */ }
async updateBible(showId: string, data: Partial<BibleUpdate>): Promise<BibleResponse> { /* ... */ }
```

---

### Edit-side mode-change control — `frontend/src/components/Shows/BibleEditor.tsx` (component, request-response)

**Analogs:** `CreateProjectModal.tsx:131-164` (same preset cards, per UI-SPEC `:121-123`) for the visual + `BibleEditor.tsx`'s own mutation pattern for the save.

`BibleEditor` is rendered from `ShowDetail.tsx:80` (`<BibleEditor showId={showId} bible={bible} />`). It currently has the bible but NOT the show's `continuity_mode` — the edit control needs the show's current mode to pre-select. `ShowDetail.tsx:16-18` already fetches `show` via `api.getShow` under `QUERY_KEYS.SHOW(showId)`; the planner can pass `show.continuity_mode` down or fetch it. Pre-selection rule (UI-SPEC `:102`): `2 → Microserie`, else `connected → Serie conectada`, `anthology → Antología` — duration comes from `bible.episode_duration_minutes`.

**Mutation + invalidate pattern to mirror** — `BibleEditor.tsx:48-64`:
```typescript
const updateBibleMutation = useMutation({
  mutationFn: (data: Partial<BibleUpdate>) => api.updateBible(showId, data),
  onSuccess: (_data, variables) => { /* saved-field flash */ },
});
const handleDurationChange = (val: number | null) => {
  setDuration(val);
  updateBibleMutation.mutate({ episode_duration_minutes: val });
};
```
For the mode change, the analogous mutation calls `api.updateShow(showId, { continuity_mode })` and on success invalidates `QUERY_KEYS.SHOW(showId)` (`constants.ts:197`). Per UI-SPEC `:137`, disable the cards while the PUT is in flight. If duration should also reseed on mode change (UI-SPEC `:123`: "only if the user has not set a custom duration"), chain `api.updateBible` + invalidate `QUERY_KEYS.BIBLE(showId)` (`constants.ts:198`).

---

### `frontend/src/lib/constants.ts` (config) — optional preset config home

**Analog:** `BIBLE_SECTIONS` / `DURATION_PRESETS` arrays (`:357-370`). If the planner extracts the three preset definitions into a shared `const` (so create + edit share one source), follow this `as const` shape:
```typescript
export const DURATION_PRESETS = [
  { value: 10, label: '10 min' },
  /* ... */
] as const;
```
**Duration decision (UI-SPEC `:115-119`, pinned):** do NOT add `2` to `DURATION_PRESETS`. The 2-min seed is a custom value; `EpisodeDurationPicker` (`EpisodeDurationPicker.tsx:10-13,63`) already renders any non-preset value through its `isPreset === false → showCustom` branch, so no constants edit is needed for duration.

## Shared Patterns

### Radix Dialog modal shell
**Source:** `CreateShowModal.tsx:38-52` (identical in `CreateProjectModal.tsx:71-85`)
**Apply to:** the create modal (already present — keep as-is).
```tsx
<Dialog.Root open={open} onOpenChange={onOpenChange}>
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm data-[state=open]:animate-fade-in" />
    <Dialog.Content className="fixed left-1/2 top-1/2 max-h-[85vh] w-[90vw] max-w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card border border-border p-0 shadow-2xl shadow-black/40 data-[state=open]:animate-scale-in overflow-hidden">
```

### Field label style
**Source:** `CreateShowModal.tsx:57` / `:74`
**Apply to:** the `Continuity` section label and `Season Arc` label (UI-SPEC `:104,111` upgrades weight to `font-semibold`).
```tsx
<label className="block text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
```
Note divergence: existing components use `font-medium`; UI-SPEC `70-UI-SPEC.md:52-60` mandates exactly two weights (400/600) and explicitly bans `font-medium` (500) for THIS phase. For new markup in Phase 70, use `font-semibold`; do not retro-edit untouched existing labels.

### Mutation → invalidate query pattern
**Source:** `CreateShowModal.tsx:21-30` (create) and `BibleEditor.tsx:48-55` (update)
**Apply to:** all create/edit mutations in this phase. Create invalidates `[QUERY_KEYS.SHOWS]`; edit-mode-change invalidates `QUERY_KEYS.SHOW(showId)` (and `QUERY_KEYS.BIBLE(showId)` if reseeding duration).

### Input/textarea field styling
**Source:** `CreateShowModal.tsx:81` (textarea) / `:65` (input)
**Apply to:** the season-arc textarea (reuse the description-field classes verbatim, `resize-none`, `rows={3}`).

## No Analog Found

None. Every file in scope has a strong in-repo analog. The only genuinely net-new artifact is the `ContinuityMode` TS union (no frontend precedent) — but it directly mirrors the backend enum at `backend/app/models/schemas.py:914-921`, so the planner has an authoritative source.

## Metadata

**Analog search scope:** `frontend/src/components/{Shows,Projects,UI}`, `frontend/src/types`, `frontend/src/lib`, `backend/app/models/schemas.py`, `backend/app/api/endpoints/shows.py`
**Files scanned:** 9
**Pattern extraction date:** 2026-06-17
