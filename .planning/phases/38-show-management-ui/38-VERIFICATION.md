---
phase: 38-show-management-ui
verified: 2026-03-24T20:10:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Create a show, open it, type in a bible section textarea, then blur out"
    expected: "A brief 'Saved' indicator appears in the section header, and after page refresh the text persists"
    why_human: "Cannot verify auto-save timing and visual indicator without running the browser"
  - test: "Select 'Custom...' from the Episode Duration dropdown"
    expected: "A number input appears below the select; entering a value saves immediately"
    why_human: "Cannot verify the select UI interaction and custom input reveal without running the browser"
  - test: "Click the delete button on a ShowCard"
    expected: "A confirmation dialog appears; confirming removes the card from the Shows section"
    why_human: "window.confirm interaction requires a real browser"
---

# Phase 38: Show Management UI Verification Report

**Phase Goal:** Users can see their shows and films as separate sections on the home page, and can open a show to view its bible and episode list
**Verified:** 2026-03-24T20:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Home page displays a Shows section with show cards showing title, description, and "0 episodes" badge | VERIFIED | `ProjectList.tsx` renders `<section>` with `<h2>Shows</h2>`, maps `shows` via `ShowCard`; `ShowCard.tsx` L54-56 renders `"0 episodes"` badge |
| 2 | Home page displays a Films section with existing ProjectCard grid unchanged | VERIFIED | `ProjectList.tsx` L136-177 renders `<section>` with `<h2>Films</h2>` and `ProjectCard` grid identical to prior implementation |
| 3 | User can create a new show via New Show button and CreateShowModal | VERIFIED | `ProjectList.tsx` L106 has "New Show" button wired to `setIsCreateShowModalOpen(true)`; `CreateShowModal.tsx` calls `api.createShow` via `useMutation`, invalidates `QUERY_KEYS.SHOWS`, navigates to `ROUTES.SHOW(show.id)` |
| 4 | Each section has an empty state when no items exist | VERIFIED | Shows empty state: `ProjectList.tsx` L112-119 (dashed border, "No shows yet"). Films empty state: L149-156 ("No film projects yet") |
| 5 | A single loading spinner waits for both queries before rendering | VERIFIED | `ProjectList.tsx` L29 `const isLoading = projectsLoading || showsLoading;` gates the spinner at L57-65 |
| 6 | User navigates to /shows/:showId and sees show title, description, and series bible | VERIFIED | `ShowDetail.tsx` fetches `api.getShow` + `api.getBible`, renders title + description header (L67-74) and `<BibleEditor>` (L79) |
| 7 | Series bible has four expandable/collapsible sections: Characters, World/Setting, Season Arc, Tone & Style | VERIFIED | `BibleEditor.tsx` L68-98 maps over `BIBLE_SECTIONS` (4 entries in `constants.ts` L319-325), each rendered as a collapsible panel with `expanded` state toggle |
| 8 | User can type in any bible section textarea and it auto-saves on blur via PUT /api/shows/{id}/bible | VERIFIED | `BibleEditor.tsx` L90 `onBlur={() => handleBlur(section.key)}` calls `updateBibleMutation.mutate({ [key]: values[key] })` at L58, which calls `api.updateBible` |
| 9 | Episode duration selector has presets (10, 22, 44, 60 min) and a Custom option with number input | VERIFIED | `EpisodeDurationPicker.tsx` maps `DURATION_PRESETS` (10/22/44/60 + Custom -1) in select; shows `<input type="number" min={1} max={480}>` when custom selected |
| 10 | Bible edits persist across page refresh | VERIFIED (structural) | `api.updateBible` calls `PUT /api/shows/{id}/bible` on blur; backend persists to DB. On reload `useQuery` fetches fresh bible. Functional persistence requires human verification |
| 11 | Show detail page has an empty episode list placeholder | VERIFIED | `ShowDetail.tsx` L83-89 renders "Episodes coming soon" placeholder with dashed border — intentional per plan (Phase 39 adds episodes) |
| 12 | Back button navigates to home | VERIFIED | `ShowDetail.tsx` L53-59 renders `<button onClick={() => navigate('/')}>Back to Home</button>` |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Exists | Substantive | Wired | Status |
|----------|-----------|-------------|--------|-------------|-------|--------|
| `frontend/src/types/index.ts` | — | 479 | Yes | Yes — Show, ShowCreate, BibleResponse, BibleUpdate at L450-479 | Yes — imported in api.tsx L10 | VERIFIED |
| `frontend/src/lib/api.tsx` | — | 1290+ | Yes | Yes — 7 show/bible methods at L1236-1295 | Yes — imported by all Show components | VERIFIED |
| `frontend/src/lib/constants.ts` | — | 330+ | Yes | Yes — QUERY_KEYS.SHOWS/SHOW/BIBLE at L196-198, ROUTES.SHOW at L272, BIBLE_SECTIONS at L319, DURATION_PRESETS at L326 | Yes — imported by all Show components | VERIFIED |
| `frontend/src/components/Shows/ShowCard.tsx` | — | 60 | Yes | Yes — full card render with title, Tv icon, description, date, "0 episodes" badge | Yes — imported in ProjectList.tsx L10, rendered at L129 | VERIFIED |
| `frontend/src/components/Shows/CreateShowModal.tsx` | — | 104 | Yes | Yes — Radix Dialog, title + description fields, api.createShow mutation | Yes — imported in ProjectList.tsx L11, rendered at L183-186 | VERIFIED |
| `frontend/src/components/Projects/ProjectList.tsx` | — | 189 | Yes | Yes — Shows + Films sections, dual useQuery, CreateShowModal | Yes — rendered at `/` route | VERIFIED |
| `frontend/src/components/Shows/ShowDetail.tsx` | 80 | 92 | Yes | Yes — show header, BibleEditor, episode placeholder | Yes — imported in App.tsx L20, used in ShowDetailRoute L46 | VERIFIED |
| `frontend/src/components/Shows/BibleEditor.tsx` | 60 | 114 | Yes | Yes — 4 collapsible sections, auto-save on blur, saved indicator, loaded ref pattern | Yes — imported in ShowDetail.tsx L6, rendered at L79 | VERIFIED |
| `frontend/src/components/Shows/EpisodeDurationPicker.tsx` | 30 | 82 | Yes | Yes — select with presets, custom number input, onChange callback | Yes — imported in BibleEditor.tsx L7, rendered at L110 | VERIFIED |
| `frontend/src/App.tsx` | — | 77 | Yes | Yes — ShowDetail imported at L20, ShowDetailRoute function at L43-47, /shows/:showId route at L72 | Yes — route wired to ProtectedRoute + ShowDetailRoute | VERIFIED |

### Key Link Verification

| From | To | Via | Pattern Found | Status |
|------|----|-----|--------------|--------|
| `ProjectList.tsx` | `/api/shows` (GET) | `useQuery` calling `api.getShows` | `api.getShows` at L26 | WIRED |
| `ShowCard.tsx` | `/shows/:showId` | `Link` to `ROUTES.SHOW(show.id)` in ProjectList.tsx | `ROUTES.SHOW` at ProjectList.tsx L125 | WIRED |
| `CreateShowModal.tsx` | `/api/shows` (POST) | `useMutation` calling `api.createShow` | `api.createShow` at L22 | WIRED |
| `ShowDetail.tsx` | `/api/shows/{id}` (GET) | `useQuery` calling `api.getShow` | `api.getShow` at L17 | WIRED |
| `ShowDetail.tsx` | `/api/shows/{id}/bible` (GET) | `useQuery` calling `api.getBible` | `api.getBible` at L21 | WIRED |
| `BibleEditor.tsx` | `/api/shows/{id}/bible` (PUT) | `useMutation` calling `api.updateBible` on blur | `api.updateBible` at L49, `onBlur` at L90 | WIRED |
| `EpisodeDurationPicker.tsx` | `BibleEditor` parent | `onChange` callback triggering `handleDurationChange` | `onChange` prop at L110 wired to `handleDurationChange` | WIRED |
| `App.tsx` | `ShowDetail` component | Route element at `/shows/:showId` | `import { ShowDetail }` at L20, route at L72 | WIRED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SHOW-02 | 38-01-PLAN | Home page displays Shows and standalone Films as separate sections | SATISFIED | `ProjectList.tsx` renders two `<section>` blocks — Shows (L100-134) with ShowCards and Films (L136-177) with ProjectCards |
| SHOW-03 | 38-02-PLAN | User can open a show to view its series bible and episode list | SATISFIED | `ShowDetail.tsx` renders show header, BibleEditor with all 4 sections, and Episodes placeholder at `/shows/:showId` |
| BIBL-01 | 38-02-PLAN | Each show has four bible sections: Characters, World/Setting, Season Arc, Tone & Style | SATISFIED | `BibleEditor.tsx` maps `BIBLE_SECTIONS` (4 entries); `BIBLE_SECTIONS` in `constants.ts` exactly matches the required sections; data model established in Phase 37 |
| BIBL-02 | 38-02-PLAN | User can write and edit each bible section as freeform text | SATISFIED | `BibleEditor.tsx` renders `<textarea>` for each section with `onChange` local state update and `onBlur` auto-save via `api.updateBible` |
| BIBL-03 | 38-02-PLAN | Each show has a target episode duration setting (10/22/44/60 min or custom) | SATISFIED | `EpisodeDurationPicker.tsx` renders all four presets plus Custom with number input (min=1, max=480); `handleDurationChange` saves immediately via `updateBibleMutation` |

**Note on REQUIREMENTS.md mapping:** BIBL-01, BIBL-02, BIBL-03 are mapped to Phase 37 in the requirements table (Phase 37 established the backend data model). Phase 38 Plan 02 claims these IDs because it delivers the UI layer. Both phases contribute to satisfying these requirements. This is consistent — Phase 37 provides persistence, Phase 38 provides the editing interface. No orphaned requirements detected for Phase 38.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ShowDetail.tsx` | 86 | `"Episodes coming soon"` | Info | Intentional placeholder — Phase 39 will implement episode management. Per plan spec. |
| `ShowCard.tsx` | 55 | `"0 episodes"` hardcoded | Info | Intentional — actual episode count deferred to Phase 39 when episode model exists. Per plan decision. |

No blockers. No functional stubs. No TODO/FIXME/HACK comments. The two noted items are documented design decisions from the PLAN and SUMMARY frontmatter.

**TypeScript:** `npx tsc --noEmit` produces exactly 3 pre-existing errors (in `IndividualEditorView.tsx`, `RepeatableCardsView.tsx`, `SidebarChat.tsx`). Zero new errors introduced by Phase 38.

**Git commits:** All 4 documented commits verified in git history:
- `a895bc5` feat(38-01): Add Show/Bible types, API methods, and constants
- `085bd02` feat(38-01): Create ShowCard, CreateShowModal, split home page, register show route
- `be64147` feat(38-02): Add BibleEditor and EpisodeDurationPicker components
- `333da5e` feat(38-02): Add ShowDetail page and wire App.tsx route

### Human Verification Required

#### 1. Bible Auto-Save Indicator

**Test:** Navigate to a show, open the Characters section, type some text, then click outside the textarea.
**Expected:** A green "Saved" checkmark appears briefly in the section header, then disappears after ~2 seconds.
**Why human:** The `savedField` state and 2-second timeout require a live browser; grep confirms the code path exists but timing/visual behavior requires human observation.

#### 2. Episode Duration Custom Input

**Test:** On a show detail page, select "Custom..." from the Episode Duration dropdown.
**Expected:** A number input appears below the dropdown labeled "Custom duration (minutes)". Entering a value saves it immediately.
**Why human:** The conditional render of the custom input depends on select interaction state (`showCustom`) — requires browser interaction to verify the flow.

#### 3. Show Delete Confirmation

**Test:** Hover a ShowCard on the home page and click the trash icon.
**Expected:** A `window.confirm` dialog appears with the message "Delete this show? This will remove all episodes. This cannot be undone." Confirming removes the card.
**Why human:** `window.confirm` cannot be triggered programmatically in static analysis.

### Gaps Summary

No gaps. All 12 must-have truths are verified. All 10 artifacts pass all three levels (exists, substantive, wired). All 8 key links are confirmed wired. All 5 requirement IDs are satisfied by the implementation. The only open items are the 3 human verification tests listed above, which verify visual/interactive behaviors that code analysis confirms are structurally correct.

---

_Verified: 2026-03-24T20:10:00Z_
_Verifier: Claude (gsd-verifier)_
