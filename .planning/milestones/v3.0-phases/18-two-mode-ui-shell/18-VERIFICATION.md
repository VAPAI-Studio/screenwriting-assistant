---
phase: 18-two-mode-ui-shell
verified: 2026-03-19T19:00:00Z
status: human_needed
score: 15/15 must-haves verified
re_verification: false
human_verification:
  - test: "Navigate to /projects/:id — confirm ModeToggle dropdown appears in the header between logo and nav"
    expected: "Dropdown button shows 'Screenwriting' text with PenLine icon and a caret; does not appear on /projects or /books"
    why_human: "Route-conditional rendering and visual placement cannot be verified without a browser"
  - test: "On /projects/:id, open ModeToggle and click 'Script Breakdown'"
    expected: "Browser navigates to /projects/:id/breakdown; layout changes to 3-panel view; header palette shifts from amber to steel-blue"
    why_human: "Visual color-scheme switch and actual route transition require browser observation"
  - test: "On /projects/:id/breakdown, navigate away (click Projects link)"
    expected: "Palette reverts to amber; no .breakdown-mode class remains on <html>; no visual artifact"
    why_human: "useEffect cleanup correctness and palette restoration require browser verification"
  - test: "On /projects/:id/breakdown, drag the left panel handle right to widen it, then refresh"
    expected: "Widened panel width is restored after refresh; collapsed state also persists"
    why_human: "localStorage persistence of panel widths requires runtime interaction"
  - test: "On /projects/:id/breakdown, click collapse button on left and right panels"
    expected: "Panel collapses to ~36px strip showing vertical title; expand button restores the panel"
    why_human: "Collapse animation and visual strip rendering need visual confirmation"
---

# Phase 18: Two-Mode UI Shell Verification Report

**Phase Goal:** Implement a two-mode UI shell that allows switching between Screenwriter mode and Breakdown mode, with mode-specific visual identity and a three-panel breakdown layout.
**Verified:** 2026-03-19T19:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | A dropdown appears in the header on /projects/:id routes | ? HUMAN | ModeToggle renders in Header.tsx (line 32); self-guards via useParams returning null when no projectId — browser confirmation needed |
| 2  | The dropdown shows current mode name with caret icon | ? HUMAN | ModeToggle renders PenLine/Clapperboard icon + mode name + ChevronDown (lines 32-38); visual check needed |
| 3  | Clicking 'Script Breakdown' navigates to /projects/:id/breakdown | ? HUMAN | `navigate(ROUTES.PROJECT_BREAKDOWN(projectId))` confirmed at line 19 of ModeToggle; actual navigation needs browser check |
| 4  | Clicking 'Screenwriting' navigates back to /projects/:id | ? HUMAN | `navigate(ROUTES.PROJECT(projectId))` confirmed at line 21 of ModeToggle; actual navigation needs browser check |
| 5  | Dropdown does not appear on /projects, /books, /snippets | ✓ VERIFIED | `if (!projectId) return null` at line 12 — component returns null when useParams yields no projectId |
| 6  | .breakdown-mode CSS variable block is defined and ready | ✓ VERIFIED | Block found at index.css line 50-88; 24 custom property overrides including --accent: 213 80% 52%, --primary: 213 80% 52%, --background, --ring |
| 7  | STORAGE_KEYS exports four panel state keys | ✓ VERIFIED | constants.ts lines 154-157: BREAKDOWN_LEFT_WIDTH, BREAKDOWN_RIGHT_WIDTH, BREAKDOWN_LEFT_COLLAPSED, BREAKDOWN_RIGHT_COLLAPSED |
| 8  | /projects/:id/breakdown renders a 3-panel layout | ? HUMAN | BreakdownLayout renders left/center/right panels structurally; visual layout needs browser check |
| 9  | Each panel shows labeled placeholder with icon and description | ✓ VERIFIED | BreakdownLayout lines 142-146 (Script View / Phase 21), 166-170 (Shotlist / Phase 20), 190-194 (AI Chat / Phase 24) |
| 10 | Left and right panels are resizable via drag handles | ✓ VERIFIED | handleLeftDragStart/handleRightDragStart wired to onMouseDown on drag handle divs (lines 150-156, 173-180); mousemove/mouseup handlers set width state |
| 11 | Left and right panels can be collapsed and expanded | ✓ VERIFIED | BreakdownPanel accepts collapsed prop; renders 36px strip with vertical label when true; toggleLeft/toggleRight callbacks wired |
| 12 | Panel widths and collapsed state persist in localStorage | ✓ VERIFIED | readStoredWidth/readStoredBool init state from localStorage; mouseup handler and toggleLeft/Right write back via STORAGE_KEYS constants |
| 13 | .breakdown-mode class added on mount and removed on unmount | ✓ VERIFIED | useEffect at BreakdownLayout lines 27-32: classList.add on mount, classList.remove in cleanup return |
| 14 | Existing /projects/:id screenwriting workspace is unchanged | ✓ VERIFIED | App.tsx routes Editor to /projects/:projectId; BreakdownLayout only replaces BreakdownPage on the /breakdown sub-route; no Editor files modified |
| 15 | Route order correct — breakdown before wildcard /:phase | ✓ VERIFIED | App.tsx lines 32-35: /projects/:projectId/breakdown precedes /projects/:projectId/:phase |

**Score:** 15/15 truths verified (5 require human browser confirmation for visual/runtime behavior)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/Layout/ModeToggle.tsx` | Mode dropdown component using Radix DropdownMenu | ✓ VERIFIED | 72 lines; exports `ModeToggle`; uses @radix-ui/react-dropdown-menu; self-guards via useParams; navigates on select |
| `frontend/src/index.css` | .breakdown-mode CSS variable override block + body transition | ✓ VERIFIED | .breakdown-mode block lines 50-88 with 24 custom properties; body transition at lines 97-99 |
| `frontend/src/lib/constants.ts` | STORAGE_KEYS for panel state | ✓ VERIFIED | Lines 154-157: all 4 breakdown panel keys present |
| `frontend/src/components/Breakdown/BreakdownLayout.tsx` | Root breakdown route component; mounts .breakdown-mode; renders three panels | ✓ VERIFIED | 199 lines; exports `BreakdownLayout`; useEffect lifecycle; three panels; drag + collapse logic |
| `frontend/src/components/Breakdown/BreakdownPanel.tsx` | Reusable panel wrapper with header, collapse button, collapsed strip | ✓ VERIFIED | 79 lines; exports `BreakdownPanel`; collapsed/expanded states; correct chevron directions per side |
| `frontend/src/App.tsx` | Route wiring: /projects/:projectId/breakdown uses BreakdownLayout | ✓ VERIFIED | Line 33: `<Route path="/projects/:projectId/breakdown" element={<BreakdownLayout />} />`; BreakdownLayout imported at line 13 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Header.tsx` | `ModeToggle` | import and render | ✓ WIRED | Line 4: `import { ModeToggle } from './ModeToggle'`; line 32: `<ModeToggle />` |
| `ModeToggle` | `/projects/:id/breakdown` | useNavigate on item select | ✓ WIRED | Line 19: `navigate(ROUTES.PROJECT_BREAKDOWN(projectId))`; ROUTES.PROJECT_BREAKDOWN confirmed in constants.ts |
| `BreakdownLayout` | `document.documentElement` | useEffect classList.add/remove | ✓ WIRED | Line 28: `classList.add('breakdown-mode')`; line 30 (cleanup): `classList.remove('breakdown-mode')` |
| `BreakdownLayout` | `STORAGE_KEYS.BREAKDOWN_LEFT_WIDTH` | localStorage read/write | ✓ WIRED | Line 36: `readStoredWidth(STORAGE_KEYS.BREAKDOWN_LEFT_WIDTH, 0.25)`; line 98: `localStorage.setItem(STORAGE_KEYS.BREAKDOWN_LEFT_WIDTH, ...)` |
| `App.tsx` | `BreakdownLayout` | Route element replacement | ✓ WIRED | Line 13 import; line 33 route element |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MODE-01 | 18-01 | App has a top-level toggle in the header switching between "Screenwriting" and "Script Breakdown" modes | ✓ SATISFIED | ModeToggle wired in Header.tsx; Radix DropdownMenu with both mode items; navigates on select |
| MODE-02 | 18-02 | Screenwriting mode renders existing workspace with zero changes to existing components | ✓ SATISFIED | Editor and ProjectWorkspace routes unchanged; BreakdownLayout only replaces BreakdownPage on /breakdown sub-route; no Editor/Workspace files modified in phase |
| MODE-03 | 18-02 | Script Breakdown mode renders a distinct 3-panel layout (left panel, center shotlist, right chat) | ✓ SATISFIED | BreakdownLayout renders Script/Assets (left), Shotlist (center), AI Chat (right); three distinct areas |
| MODE-04 | 18-01 | Screenwriting and Breakdown modes have visually distinct color schemes while maintaining design unity | ? NEEDS HUMAN | .breakdown-mode block with steel-blue palette (--accent: 213 80% 52%) vs amber (:root --accent: 38 92% 50%) verified in code; visual unity requires browser confirmation |
| MODE-05 | 18-01, 18-02 | Mode toggle preserves project context (no data loss on switch) | ✓ SATISFIED | ModeToggle uses useParams to extract projectId and passes it through ROUTES.PROJECT/PROJECT_BREAKDOWN; no data mutation on navigate |

No orphaned requirements — all MODE-01 through MODE-05 are claimed by Plans 18-01 or 18-02 and confirmed in REQUIREMENTS.md.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `ModeToggle.tsx` | 12 | `return null` | ℹ️ Info | Intentional self-guarding pattern — not a stub |

No blockers or warnings. The single `return null` is the documented self-guard pattern when outside project routes.

---

### Human Verification Required

#### 1. ModeToggle Visibility and Placement

**Test:** Navigate to `/projects/:id` (any project); inspect the header.
**Expected:** Dropdown button labeled "Screenwriting" with PenLine icon and ChevronDown appears between the logo and the nav links. Navigate to `/projects` or `/books` — button should not be visible.
**Why human:** Route-conditional rendering via useParams behavior and visual header layout require browser observation.

#### 2. Mode Switch Visual Identity

**Test:** On `/projects/:id`, open ModeToggle, click "Script Breakdown".
**Expected:** Browser navigates to `/projects/:id/breakdown`; entire UI palette shifts from warm amber to steel-blue (buttons, borders, accents change color); 3-panel layout appears.
**Why human:** CSS variable palette swap triggered by classList is a visual outcome requiring browser confirmation.

#### 3. Palette Restoration on Navigate Away

**Test:** From `/projects/:id/breakdown`, click the "Projects" nav link.
**Expected:** URL becomes `/projects`; amber palette fully restored; no steel-blue artifacts remain; confirm `document.documentElement.classList` does not contain `breakdown-mode`.
**Why human:** useEffect cleanup removal of .breakdown-mode class requires runtime verification of DOM state.

#### 4. Panel Resize Persistence

**Test:** On `/projects/:id/breakdown`, drag the left panel handle to make it wider, then hard-refresh the page.
**Expected:** Left panel restores to the widened width from localStorage on reload.
**Why human:** localStorage read/write persistence requires runtime interaction across page loads.

#### 5. Panel Collapse/Expand

**Test:** On `/projects/:id/breakdown`, click the collapse button on the left panel (ChevronLeft icon).
**Expected:** Panel collapses to a narrow ~36px vertical strip showing "SCRIPT / ASSETS" as a rotated label; expand button (ChevronRight) is visible; clicking it restores the panel to full width.
**Why human:** Visual collapse animation and collapsed strip rendering require browser observation.

---

### Gaps Summary

No structural gaps found. All artifacts exist, are substantive (not stubs), and all key links are wired. The phase goal is architecturally achieved:

- The two-mode shell is established with CSS identity separation and Radix-powered navigation.
- The breakdown layout is wired to its route with mode class lifecycle management.
- Panel state persistence and resize/collapse behavior are fully implemented.
- Existing screenwriting workspace is untouched.

The 5 human-verification items are runtime/visual confirmations of already-verified code logic, not gaps in implementation. TypeScript errors (3 pre-existing files: IndividualEditorView.tsx, RepeatableCardsView.tsx, SidebarChat.tsx) are confirmed pre-existing and out of scope for Phase 18.

---

_Verified: 2026-03-19T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
