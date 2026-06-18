---
phase: 70-show-creation-wizard-mode-presets
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - frontend/src/types/index.ts
  - frontend/src/lib/constants.ts
  - frontend/src/components/Shows/CreateShowModal.tsx
  - frontend/src/components/Shows/BibleEditor.tsx
  - frontend/src/components/Shows/ShowDetail.tsx
findings:
  critical: 3
  warning: 3
  info: 2
  total: 8
status: issues_found
---

# Phase 70: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 70 adds a continuity-mode wizard to show creation and a matching edit-side preset control. The types and constants file (Plan 01) are clean. The bulk of defects are in `CreateShowModal.tsx` and `BibleEditor.tsx`.

Three blockers were found: (1) the two-call create sequence swallows `updateBible` failures silently — the user sees "Creating…" disappear, gets navigated to the new show, but the bible seed never applied and there is zero feedback; (2) the `onSuccess` handler navigates and resets state on a component that may already be unmounted, producing React "can't perform state update on unmounted component" warnings and potential crashes in strict mode; (3) the `loaded` ref in `BibleEditor` incorrectly seeds `selectedPreset` a second time inside the `useEffect`, defeating its own "mount-only" guard for the new `continuityMode` prop — a show-query refetch after a mode change will reset the card highlight to its pre-change value under race-condition timing.

Three warnings were found: no error is surfaced to the user when the two-call sequence fails; the `Saved` indicator for mode changes in `BibleEditor` relies on `isSuccess` which persists permanently after the first success (a second card click won't show the indicator unless the status resets); and missing BIBLE cache invalidation after `updateShow` causes stale duration data to be used for re-disambiguation.

---

## Critical Issues

### CR-01: Silent data loss when `updateBible` fails in the two-call create sequence

**File:** `frontend/src/components/Shows/CreateShowModal.tsx:43-66`

**Issue:** The `mutationFn` calls `await api.updateBible(show.id, bibleUpdate)` but provides no `try/catch` and no `onError` handler on the mutation. If `updateBible` throws (network error, 5xx, 401 token expiry), the promise rejects and React Query marks the mutation as errored — but `onSuccess` is never called, so the modal stays open showing a non-pending button. The show **has already been created** with `continuity_mode` persisted, but the episode duration (2 or 22 min) and any typed Season Arc text are silently discarded. The user has no indication that a partial write happened, and there is no recovery path.

The plan threat register (T-70-04) acknowledges this failure mode but says "surface the failure via the existing inline error copy." No error copy was actually implemented.

**Fix:**

```tsx
// Add onError to the mutation config:
const createShowMutation = useMutation({
  mutationFn: async (): Promise<Show> => { /* unchanged */ },
  onSuccess: (show) => { /* unchanged */ },
  onError: (err, _vars, context) => {
    // show was created but bible seed failed — still navigate so the user
    // doesn't lose the show, but surface the partial failure.
    console.error('Bible seed failed after show creation:', err);
    // If show id is available via context, navigate and show a toast:
    // navigate(ROUTES.SHOW(createdShowId)); + error toast
  },
});

// Also render the error below the form:
{createShowMutation.isError && (
  <p className="text-xs text-red-400 mt-1">
    Show created, but the bible seed failed. You can set duration and season arc on the show page.
  </p>
)}
```

The cleaner fix is to wrap `api.updateBible` in a `try/catch` inside `mutationFn`, continue to return `show` (so `onSuccess` runs and navigates), and attach a warning state that is rendered in the modal before navigation closes it — or pass it as context to `onSuccess`.

---

### CR-02: State resets called on unmounted component in `onSuccess`

**File:** `frontend/src/components/Shows/CreateShowModal.tsx:58-66`

**Issue:** The `onSuccess` handler calls `onOpenChange(false)` (which unmounts the dialog content), then immediately calls `setTitle('')`, `setDescription('')`, `setSelectedPreset(null)`, and `setSeasonArc('')` on the now-unmounted component. In React 18 strict mode (and in practice when the dialog is removed from the DOM synchronously), these `setState` calls trigger the "Can't perform a React state update on an unmounted component" warning, and in future React versions this is being hardened to an error.

```tsx
onSuccess: (show) => {
  queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SHOWS] });
  // Reset state BEFORE closing the modal to avoid updating unmounted component:
  setTitle('');
  setDescription('');
  setSelectedPreset(null);
  setSeasonArc('');
  onOpenChange(false);           // close after resets
  navigate(ROUTES.SHOW(show.id));
},
```

Alternatively, reset state inside the `Dialog.Root`'s `onOpenChange` callback so it runs whenever the dialog closes for any reason (cancel or success).

---

### CR-03: `loaded` ref guard does not protect `selectedPreset` from a post-mutation refetch

**File:** `frontend/src/components/Shows/BibleEditor.tsx:53-69`

**Issue:** The `useEffect` sets `loaded.current = true` only after the first execution. However, `updateShowMutation.onSuccess` calls `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOW(showId) })`, which triggers a background refetch of the show query. When the parent (`ShowDetail`) re-renders with the new `show.continuity_mode` and a new `bible` prop (if the bible also refetches), the `useEffect` dependency array `[bible, continuityMode]` fires again. At that point `loaded.current` is already `true`, so the guard correctly skips the re-seeding — this part is correct.

BUT: `selectedPreset` is also initialized in the `useState` lazy initializer (line 49-51), and a separate call to `setSelectedPreset(presetIdForMode(...))` exists inside the `useEffect` body at line 66. This second call inside the effect is **dead code when `loaded.current` is already true** (the guard prevents it), but there is a real problem: when `continuityMode` changes as a prop (the parent re-renders after a different show is loaded, e.g., navigation from one show to another without remounting), the `useEffect` fires with `loaded.current === true` and the block is skipped entirely. The selected card will show the stale preset from the previous show because the lazy initializer only runs once per mount.

This is a real bug in apps that navigate between shows without remounting `ShowDetail` (React Router's default behavior with keep-alive). The fix is to reset `loaded.current` when `showId` changes, or to use `showId` as a key on `BibleEditor` (simpler):

```tsx
// In ShowDetail.tsx — add key prop so BibleEditor fully remounts per show:
{bible && (
  <BibleEditor
    key={showId}
    showId={showId}
    bible={bible}
    continuityMode={show.continuity_mode}
  />
)}
```

Or in `BibleEditor.tsx`, guard on `showId` change in the effect:

```tsx
const loadedShowId = useRef<string | null>(null);
useEffect(() => {
  if (loadedShowId.current !== showId) {
    // first load for this showId — seed from props
    setValues({ ... });
    setDuration(bible.episode_duration_minutes);
    setSelectedPreset(presetIdForMode(continuityMode, bible.episode_duration_minutes));
    loadedShowId.current = showId;
  }
}, [bible, continuityMode, showId]);
```

---

## Warnings

### WR-01: No user-visible error feedback for any mutation failure

**File:** `frontend/src/components/Shows/CreateShowModal.tsx:33-67`

**Issue:** `createShowMutation` has no `onError` handler and `createShowMutation.isError` is never rendered. If `api.createShow` itself fails (400, 422 from the backend enum validator, 500, network timeout), the button re-enables silently, `isPending` returns to `false`, and the user gets no explanation. The plan specifically called out "Surface the create/update failure via the existing inline error copy (UI-SPEC :159)."

Similarly, `BibleEditor` has no `onError` on `updateShowMutation` — a failed mode-change PUT leaves the card appearing selected locally while the backend still has the old value, with no error message.

**Fix:** Add inline error display:

```tsx
// CreateShowModal — after the Season Arc block:
{createShowMutation.isError && (
  <p className="text-xs text-red-400">
    {(createShowMutation.error as Error)?.message ?? 'Failed to create show. Please try again.'}
  </p>
)}

// BibleEditor — next to the Saved indicator:
{updateShowMutation.isError && (
  <span className="text-xs text-red-400">Failed to save mode.</span>
)}
```

---

### WR-02: `updateShowMutation.isSuccess` persists permanently — "Saved" indicator never reappears

**File:** `frontend/src/components/Shows/BibleEditor.tsx:110-114`

**Issue:** React Query's `isSuccess` flag on a `useMutation` stays `true` indefinitely after the first successful call (unlike `useQuery`, mutations do not reset to idle). The condition `updateShowMutation.isSuccess && !updateShowMutation.isPending` on line 110 means the "Saved" indicator shows permanently after the first successful mode change, and on a subsequent card click it will be visible during the pending state (since `isPending` takes a tick to become `true`).

The existing bible-field "Saved" flash uses a `setTimeout`-based `savedField` state pattern (lines 86-90) precisely to avoid this. The mode-change indicator should use the same approach:

```tsx
// Replace isSuccess check with a timed flash state:
const [modeSaved, setModeSaved] = useState(false);

const updateShowMutation = useMutation({
  mutationFn: (mode: ContinuityMode) => api.updateShow(showId, { continuity_mode: mode }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOW(showId) });
    setModeSaved(true);
    setTimeout(() => setModeSaved(false), 2000);
  },
});

// In JSX:
{modeSaved && (
  <span className="flex items-center gap-1 text-xs text-emerald-400">
    <Check className="h-3 w-3" /> Saved
  </span>
)}
```

---

### WR-03: Missing BIBLE cache invalidation after mode-change `updateShow` causes stale disambiguation

**File:** `frontend/src/components/Shows/BibleEditor.tsx:71-76`

**Issue:** When the user changes the continuity mode card in `BibleEditor`, `updateShowMutation.onSuccess` invalidates `QUERY_KEYS.SHOW(showId)` but does NOT invalidate `QUERY_KEYS.BIBLE(showId)`. The `bible` prop (including `episode_duration_minutes`) used by `presetIdForMode` is sourced from the BIBLE query. If the user then navigates away and returns, the SHOW query refetches with the updated `continuity_mode`, but the BIBLE query may return a cached (stale) response with `episode_duration_minutes` still at 2 or 22. The `presetIdForMode` function would then re-disambiguate based on stale duration, potentially pre-selecting the wrong card (e.g., "Microserie" when the mode was changed to "Serie conectada" with duration still at 2).

This is especially likely when the BIBLE query is still within its stale time (5 minutes per CLAUDE.md convention).

**Fix:**

```tsx
const updateShowMutation = useMutation({
  mutationFn: (mode: ContinuityMode) => api.updateShow(showId, { continuity_mode: mode }),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOW(showId) });
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.BIBLE(showId) });
  },
});
```

---

## Info

### IN-01: `selectedPresetObj` computed every render but `mutationFn` re-derives preset inline

**File:** `frontend/src/components/Shows/CreateShowModal.tsx:30-35`

**Issue:** `selectedPresetObj` is computed at line 30 (`SHOW_PRESETS.find(...)`) for use by `isConnected` at line 31. The `mutationFn` at line 35 calls `SHOW_PRESETS.find(...)` again as a separate derivation (`const preset = ...`). This is harmless (the array has 3 elements) but duplicates the lookup. The summary notes this was a deliberate deviation from the plan (to avoid a TS unused-binding error), but the end result is the `mutationFn` could use a stale closure value if `selectedPreset` changes between render and mutation execution. Since `useMutation`'s `mutationFn` captures the latest closure (React Query calls it at invoke time), this is functionally fine, but it is unnecessary duplication.

**Fix:** Not urgent; accepted tradeoff noted in the summary. If cleaned up, use `selectedPresetObj` directly inside `mutationFn` since it is already in scope.

---

### IN-02: `presetIdForMode` returns `'antologia'` for `standalone` mode — no dedicated preset

**File:** `frontend/src/components/Shows/BibleEditor.tsx:20-25`

**Issue:** The `presetIdForMode` function maps `standalone` (and anything that is not `'connected'`) to `'antologia'`. A show with `continuity_mode === 'standalone'` (the feature-film path, D-02) will display the "Antología" card as pre-selected, which is semantically incorrect — a standalone feature film is not an anthology series. There is no wizard preset for `standalone`, so the user would see a misleading UI state. The comment on line 19 documents this (`anthology/standalone -> Antología`) but does not flag it as a concern.

Since `standalone` shows can only be created outside the current wizard (the wizard only offers `connected`/`anthology`), a user could encounter this if they have pre-existing standalone shows.

**Fix:** Add a guard or a fourth display-only state. Minimum viable fix:

```tsx
function presetIdForMode(mode: ContinuityMode, durationMinutes: number | null): string {
  if (mode === 'connected') {
    return durationMinutes === 2 ? 'microserie' : 'serie-conectada';
  }
  if (mode === 'anthology') {
    return 'antologia';
  }
  // standalone: no matching preset card; return 'antologia' as closest
  // approximation, or consider a disabled/none state in a future phase.
  return 'antologia';
}
```

At minimum add a comment making the standalone case explicit rather than relying on the catch-all `else`. If standalone shows exist in production, consider rendering the mode control in a read-only or "not applicable" state rather than falsely highlighting a preset.

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
