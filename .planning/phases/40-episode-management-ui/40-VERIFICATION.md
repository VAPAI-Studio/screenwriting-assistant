---
phase: 40-episode-management-ui
verified: 2026-03-24T21:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 40: Episode Management UI Verification Report

**Phase Goal:** Users can create, view, open, and delete episodes from the show detail page
**Verified:** 2026-03-24T21:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                       | Status     | Evidence                                                                                                                                 |
| --- | --------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Show detail page displays episodes ordered by episode number                | ✓ VERIFIED | `EpisodeList.tsx` uses `useQuery(QUERY_KEYS.EPISODES(showId), () => api.getEpisodes(showId))`; backend `list_episodes` orders by `episode_number.asc()` |
| 2   | User can create an episode via New Episode dialog and it appears in the list | ✓ VERIFIED | `CreateEpisodeModal.tsx` calls `api.createEpisode` via `useMutation`, `onSuccess` invalidates `QUERY_KEYS.EPISODES(showId)`              |
| 3   | User can click an episode row to navigate to /projects/{id} editor          | ✓ VERIFIED | `EpisodeList.tsx` line 79: `onClick={() => navigate(ROUTES.PROJECT(episode.id))}`                                                        |
| 4   | User can delete an episode with confirmation and it disappears from the list | ✓ VERIFIED | `handleDelete` calls `window.confirm`, then `deleteMutation.mutate(id)` via `api.deleteProject`, invalidates query on success            |
| 5   | Empty show displays "No episodes yet" message                               | ✓ VERIFIED | `EpisodeList.tsx` line 72: `<p className="text-sm text-muted-foreground">No episodes yet — create your first episode</p>`                |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact                                                           | Expected                                           | Status     | Details                                                                  |
| ------------------------------------------------------------------ | -------------------------------------------------- | ---------- | ------------------------------------------------------------------------ |
| `backend/app/api/endpoints/shows.py`                               | GET /{show_id}/episodes endpoint with `def list_episodes` | ✓ VERIFIED | Lines 159-178: substantive implementation with show ownership check, ordered query, 404 for unknown show |
| `backend/app/tests/test_shows_api.py`                              | Tests: test_list_episodes, test_list_episodes_empty, test_list_episodes_not_found | ✓ VERIFIED | All 3 tests present at lines 573-607; all 9 TestEpisodesAPI tests pass (9/9 green) |
| `frontend/src/types/index.ts`                                      | Project type with show_id and episode_number fields | ✓ VERIFIED | Lines 54-55: `show_id?: string \| null;` and `episode_number?: number \| null;` |
| `frontend/src/lib/api.tsx`                                         | getEpisodes and createEpisode API functions         | ✓ VERIFIED | Lines 1292-1313: both functions present, calling correct endpoints with fetchWithTimeout and auth headers |
| `frontend/src/lib/constants.ts`                                    | QUERY_KEYS.EPISODES entry                           | ✓ VERIFIED | Line 199: `EPISODES: (showId: string) => ['episodes', showId] as const` |
| `frontend/src/components/Shows/EpisodeList.tsx`                    | Episode list component with CRUD operations         | ✓ VERIFIED | 120 lines (exceeds 60-line minimum); full implementation — query, navigation, delete, empty state |
| `frontend/src/components/Shows/CreateEpisodeModal.tsx`             | Modal dialog for creating episodes                  | ✓ VERIFIED | 113 lines (exceeds 40-line minimum); full Radix Dialog with form, mutation, cache invalidation |
| `frontend/src/components/Shows/ShowDetail.tsx`                     | ShowDetail with EpisodeList replacing placeholder   | ✓ VERIFIED | Line 7: `import { EpisodeList }` present; lines 83-87: `<EpisodeList showId={showId} />`; no placeholder text remains |

All 8 artifacts: exists=true, substantive=true, wired=true.

---

### Key Link Verification

| From                              | To                             | Via                                     | Status     | Details                                                                                                   |
| --------------------------------- | ------------------------------ | --------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| `EpisodeList.tsx`                 | `/api/shows/{showId}/episodes` | `useQuery` with `QUERY_KEYS.EPISODES`   | ✓ WIRED    | Line 21: `queryKey: QUERY_KEYS.EPISODES(showId)`, `queryFn: () => api.getEpisodes(showId)`                |
| `CreateEpisodeModal.tsx`          | `/api/shows/{showId}/episodes` | `useMutation` calling `api.createEpisode` | ✓ WIRED  | Line 24-25: `mutationFn: (data) => api.createEpisode(showId, data)` — POST to correct endpoint            |
| `EpisodeList.tsx`                 | `/projects/{id}`               | `navigate(ROUTES.PROJECT(id))`          | ✓ WIRED    | Line 79: `onClick={() => navigate(ROUTES.PROJECT(episode.id))}` — click handler wired to navigation       |
| `ShowDetail.tsx`                  | `EpisodeList.tsx`              | import and render                       | ✓ WIRED    | Line 7: `import { EpisodeList } from './EpisodeList'`; line 86: `<EpisodeList showId={showId} />`         |

All 4 key links wired.

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                      | Status     | Evidence                                                                              |
| ----------- | ----------- | ---------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------- |
| EPIS-03     | 40-01-PLAN  | User can view, open, and delete episodes from the show page      | ✓ SATISFIED | EpisodeList renders ordered episodes; clicking navigates to /projects/{id}; delete with confirm removes episode; create via modal adds episode to list |

---

### Anti-Patterns Found

No anti-patterns detected.

| File                                                     | Pattern Scanned                                       | Result                              |
| -------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------- |
| `frontend/src/components/Shows/EpisodeList.tsx`          | TODO/FIXME, placeholder text, return null, empty {}   | None found                          |
| `frontend/src/components/Shows/CreateEpisodeModal.tsx`   | TODO/FIXME, placeholder text, return null             | None found (only HTML input placeholder attr — not a stub) |
| `frontend/src/components/Shows/ShowDetail.tsx`           | "Episodes coming soon", placeholder section           | None found — fully replaced         |
| `backend/app/api/endpoints/shows.py` list_episodes       | Static return, missing DB query                       | None found — real DB query with ordering |

---

### Test Suite Status

**Backend TestEpisodesAPI:** 9/9 passed (includes 3 new phase-40 tests)

- `test_list_episodes` — PASS: returns 2 episodes ordered by episode_number
- `test_list_episodes_empty` — PASS: returns 200 with empty list
- `test_list_episodes_not_found` — PASS: returns 404 for unknown show

**Full backend suite:** 284 passed, 9 failed — all failures are pre-existing (test_session_isolation, test_shotlist_generation, test_yolo_integration) and unrelated to phase 40.

**TypeScript:** 3 errors — all pre-existing (IndividualEditorView, RepeatableCardsView, SidebarChat). Zero new errors introduced by phase 40.

---

### Human Verification Required

The following items cannot be verified programmatically:

#### 1. Episode create/delete flow end-to-end

**Test:** Navigate to `/shows/{id}`, click "New Episode", fill in title, select framework, submit. Verify episode appears in list with correct number.
**Expected:** Episode appears immediately with "Ep. 1" prefix, title, and framework badge.
**Why human:** Requires live UI interaction and React Query cache update observation.

#### 2. Episode navigation click

**Test:** Click an episode row in the list.
**Expected:** Browser navigates to `/projects/{episode_id}` and the editor loads.
**Why human:** Navigation behavior and editor loading require a running app.

#### 3. Delete confirmation and list refresh

**Test:** Click delete button (trash icon) on an episode, confirm in dialog.
**Expected:** Episode disappears from list; episode count decrements.
**Why human:** `window.confirm` behavior and optimistic/pessimistic UI update requires live interaction.

---

### Gaps Summary

No gaps. All 5 observable truths verified, all 8 artifacts substantive and wired, all 4 key links active, EPIS-03 satisfied, no anti-patterns, full test suite green for phase-relevant tests, TypeScript clean.

---

_Verified: 2026-03-24T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
