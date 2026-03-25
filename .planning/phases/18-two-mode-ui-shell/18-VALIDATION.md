---
phase: 18
slug: two-mode-ui-shell
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 18 — Validation Strategy

> Retroactively created 2026-03-25. Phase completed 2026-03-19.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | TypeScript tsc (frontend — no backend changes in this phase) |
| **Config file** | frontend/tsconfig.json |
| **Quick run command** | `cd frontend && npx tsc --noEmit` |
| **Full suite command** | `cd frontend && npx tsc --noEmit && npm run build` |
| **Estimated runtime** | ~10s |

---

## Sampling Rate

- **After every task commit:** Run `npx tsc --noEmit`
- **After every plan wave:** Full build
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 18-01-01 | ModeToggle component exists and compiles | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 18-01-02 | BreakdownLayout.tsx shell compiles (adds/removes breakdown-mode CSS class) | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 18-02-01 | App.tsx routes /breakdown and /storyboard to correct components | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 18-02-02 | ROUTES.PROJECT_BREAKDOWN and ROUTES.PROJECT_STORYBOARD defined in constants.ts | grep | `grep -n "PROJECT_BREAKDOWN\|PROJECT_STORYBOARD" frontend/src/lib/constants.ts` | ✅ verified |

---

## Key Files

| File | What it delivers |
|------|-----------------|
| `frontend/src/components/Layout/ModeToggle.tsx` | Screenwriting / Breakdown / Storyboard dropdown; saves last screenwriting path to localStorage |
| `frontend/src/components/Layout/Header.tsx` | Renders `<ModeToggle />` in sticky header |
| `frontend/src/components/Breakdown/BreakdownLayout.tsx` | Three-panel breakdown shell; adds `breakdown-mode` class to `document.documentElement` |
| `frontend/src/App.tsx` | Routes `/projects/:id/breakdown` → BreakdownLayout, `/projects/:id/storyboard` → StoryboardView |
| `frontend/src/index.css` | `.breakdown-mode` CSS variable block (slate-blue palette) |

---

## Manual-Only Verifications

| Behavior | Why Manual | Test Instructions |
|----------|------------|-------------------|
| Mode toggle switches visual theme (amber → slate-blue) | CSS class on `document.documentElement`, not testable via tsc | Navigate to /projects/{id}/breakdown, verify header turns slate-blue |
| Navigating between modes preserves last screenwriting path | localStorage state + navigation | Switch to breakdown, switch back, verify editor returns to previous section |

---

## Validation Sign-Off

- [x] All tasks have automated verify (tsc exits 0)
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive
