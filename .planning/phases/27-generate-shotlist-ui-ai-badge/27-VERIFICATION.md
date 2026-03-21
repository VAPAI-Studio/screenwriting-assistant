---
phase: 27-generate-shotlist-ui-ai-badge
verified: 2026-03-21T18:30:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Generate Shotlist button renders in shotlist panel header"
    expected: "Button labeled 'Generate Shotlist' with Sparkles icon is visible in the center panel header bar above the shotlist"
    why_human: "Button is conditionally rendered — it appears only when generateState is non-null (set via useEffect after ShotlistPanel mounts). Cannot verify conditional mount timing programmatically."
  - test: "Button disabled with spinner during generation"
    expected: "Clicking Generate Shotlist triggers a POST to /api/shots/{projectId}/generate; button becomes disabled and shows Loader2 spinner until response arrives"
    why_human: "Loading/disabled state is async UI behavior requiring live HTTP interaction"
  - test: "Shotlist panel refreshes after generation completes"
    expected: "New shots appear grouped by scene without a page reload; React Query cache is invalidated and refetch completes"
    why_human: "Requires end-to-end execution: live backend call + React Query cache invalidation + re-render"
  - test: "Sparkles badge visible on AI-generated shots, absent on manual shots"
    expected: "Shots created by the generate endpoint (ai_generated=true) show a small blue sparkle icon next to the shot number; manually-created shots show no icon"
    why_human: "Visual badge presence depends on actual data returned by backend — cannot verify without live data"
---

# Phase 27: Generate Shotlist UI & AI Badge — Verification Report

**Phase Goal:** Wire the frontend trigger for AI shotlist generation and add a visual sparkle badge on AI-generated shots.
**Verified:** 2026-03-21T18:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | User can click 'Generate Shotlist' button in the breakdown panel center header | VERIFIED | `BreakdownLayout.tsx` lines 242-255 render a `<button>` with text "Generate Shotlist" and Sparkles icon, conditioned on `generateState` being non-null; `generateState` is set via `onGenerateStateChange={setGenerateState}` at line 263 |
| 2 | Button is disabled and shows spinner while generation is in progress | VERIFIED | `BreakdownLayout.tsx` line 245: `disabled={generateState.isPending}`; lines 250-252: ternary swaps Sparkles for Loader2 with `animate-spin` when `isPending` |
| 3 | After generation completes, the shotlist panel refreshes to show new shots grouped by scene | VERIFIED | `ShotlistPanel.tsx` line 208: `queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SHOTS(projectId!) })` inside `generateMutation.onSuccess`; grouping via `groupShotsByScene()` on line 39 |
| 4 | AI-generated shots display a small Sparkles icon next to the shot number | VERIFIED | `ShotRow.tsx` lines 36-40: `{shot.ai_generated && (<span title="AI generated"><Sparkles className="h-2.5 w-2.5 text-blue-400/60 flex-shrink-0" /></span>)}` |
| 5 | Manually-created shots do NOT display the Sparkles icon | VERIFIED | `ShotRow.tsx` line 36: guard is `shot.ai_generated` — optimistic shot sets `ai_generated: false` (`ShotlistPanel.tsx` line 124); user-created shots will always have `ai_generated === false` |
| 6 | Empty state offers a 'Generate with AI' button as an alternative to 'Add First Shot' | VERIFIED | `ShotlistEmptyState.tsx` lines 29-40: `{onGenerate && (<Button ... >Generate with AI</Button>)}`; prop is passed at `ShotlistPanel.tsx` line 318 |
| 7 | Validation errors from backend (no screenplay) are shown inline to the user | VERIFIED | `ShotlistPanel.tsx` lines 202-205: `if (data.status === 'error') { setGenerateError(data.message) }` + error banner at lines 351-362 (data state) and `generateError` passed to `ShotlistEmptyState` at line 320 |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/types/index.ts` | Shot interface with `ai_generated` and `user_modified` boolean fields | VERIFIED | Lines 333-334 of index.ts: `ai_generated: boolean;` and `user_modified: boolean;` present inside the `Shot` interface |
| `frontend/src/lib/api.tsx` | `generateShotlist` API method calling `POST /shots/{projectId}/generate` | VERIFIED | Lines 939-962 of api.tsx: `async generateShotlist(projectId: string)` uses `fetch(...shots/${projectId}/generate`, method POST, with `CHAT_TIMEOUT` (120s) |
| `frontend/src/components/Breakdown/BreakdownLayout.tsx` | Generate Shotlist button in center panel header | VERIFIED | Lines 242-255: full button implementation with Sparkles/Loader2 icons, disabled state, and "Generate Shotlist"/"Generating..." text |
| `frontend/src/components/Breakdown/ShotlistPanel.tsx` | Generate mutation wired to API, passed down to children | VERIFIED | Lines 199-221: `generateMutation` using `useMutation`, `api.generateShotlist`, `onGenerateStateChange` callback via `useEffect` |
| `frontend/src/components/Breakdown/ShotRow.tsx` | Sparkles icon badge for AI-generated shots | VERIFIED | Lines 2-3: `import { Sparkles } from 'lucide-react'`; lines 36-40: conditional Sparkles render wrapped in `<span title="AI generated">` |
| `frontend/src/components/Breakdown/ShotlistEmptyState.tsx` | Generate with AI button in empty state | VERIFIED | Lines 1, 29-40: Sparkles/Loader2 imported and used; "Generate with AI" text in button; full props interface includes `onGenerate?`, `isGenerating?`, `generateError?` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `BreakdownLayout.tsx` | `ShotlistPanel.tsx` | `onGenerateStateChange={setGenerateState}` prop | WIRED | Line 263 of BreakdownLayout.tsx passes `setGenerateState` as the `onGenerateStateChange` prop; ShotlistPanel calls it via `useEffect` at lines 215-221 |
| `ShotlistPanel.tsx` | `api.generateShotlist` | `useMutation` calling `api.generateShotlist` | WIRED | Line 201: `mutationFn: () => api.generateShotlist(projectId!)`; response handling on lines 202-212 |
| `ShotRow.tsx` | `Shot.ai_generated` | `shot.ai_generated` boolean check | WIRED | Line 36 of ShotRow.tsx: `{shot.ai_generated && (...)}` directly reads the `ai_generated` field from the `Shot` interface |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| AISG-01 (frontend trigger) | 27-01-PLAN.md | User can trigger AI generation of a full shotlist via "Generate Shotlist" button | SATISFIED | Button exists in BreakdownLayout header (lines 242-255); wired through ShotlistPanel generateMutation to POST /shots/{projectId}/generate |
| AISG-07 | 27-01-PLAN.md | AI-generated shots display a subtle visual indicator (sparkle icon badge) | SATISFIED | ShotRow.tsx conditionally renders Sparkles icon when `shot.ai_generated === true` |

No orphaned requirements: REQUIREMENTS.md maps AISG-01 and AISG-07 to Phase 27, and both are claimed in the plan frontmatter and verified in code.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None detected | — | — |

Files scanned: `types/index.ts`, `lib/api.tsx`, `ShotlistPanel.tsx`, `BreakdownLayout.tsx`, `ShotRow.tsx`, `ShotlistEmptyState.tsx`. No TODOs, FIXMEs, empty implementations, or stub returns found in the phase-modified files.

---

### TypeScript Compilation

`npx tsc --noEmit` produces exactly 3 errors, all in pre-existing files (`IndividualEditorView.tsx`, `RepeatableCardsView.tsx`, `SidebarChat.tsx`). Zero new errors introduced by Phase 27.

---

### Human Verification Required

#### 1. Generate Shotlist Button Renders

**Test:** Open the app in breakdown mode for any project. Observe the center panel header bar (above the shotlist columns).
**Expected:** A button labeled "Generate Shotlist" with a sparkle icon is visible in the top-right of the center panel header.
**Why human:** The button is conditionally rendered — it only appears after `ShotlistPanel` mounts and fires the `onGenerateStateChange` callback via `useEffect`. The conditional `{generateState && (...)}` means the button will not appear until the child panel has mounted and set state. This timing behavior cannot be verified by static analysis.

#### 2. Loading State During Generation

**Test:** Click "Generate Shotlist" and observe the button while the POST request is in flight.
**Expected:** Button becomes disabled, "Generate Shotlist" text changes to "Generating...", and the Sparkles icon is replaced by a Loader2 spinner with `animate-spin`.
**Why human:** Async UI behavior requires live HTTP interaction.

#### 3. Shotlist Refreshes After Generation

**Test:** Click "Generate Shotlist" and wait for the response to complete.
**Expected:** New shots appear in the shotlist grouped by scene, without a page reload.
**Why human:** Requires a live backend call + React Query cache invalidation + re-render cycle.

#### 4. Sparkles Badge on AI Shots vs. Manual Shots

**Test:** After generation, inspect each shot row. Then manually create a new shot via "Add First Shot" and inspect its row.
**Expected:** Generated shots show a small blue sparkle icon next to their shot number. The manually-created shot shows no sparkle icon.
**Why human:** Badge visibility depends on real data from the backend (`ai_generated` field value). Cannot verify with static analysis alone.

---

### Gaps Summary

No gaps detected. All 7 observable truths are satisfied by substantive, wired implementation. The four items flagged for human verification are behavioral/visual tests that cannot be confirmed by static code analysis — they require the running application with a live backend.

---

_Verified: 2026-03-21T18:30:00Z_
_Verifier: Claude (gsd-verifier)_
