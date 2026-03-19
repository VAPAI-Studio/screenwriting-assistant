---
phase: 18
slug: two-mode-ui-shell
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | No frontend test framework configured — manual verification + lint/build gates |
| **Config file** | none (no Vitest/Jest in frontend/package.json) |
| **Quick run command** | `cd frontend && npm run lint` |
| **Full suite command** | `cd frontend && npm run build` |
| **Estimated runtime** | ~15 seconds (lint), ~30 seconds (build) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run lint`
- **After every plan wave:** Run `cd frontend && npm run build`
- **Before `/gsd:verify-work`:** Full build must be green + manual smoke test checklist completed
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | MODE-04 | lint+build | `cd frontend && npm run lint && npm run build` | ✅ existing | ⬜ pending |
| 18-01-02 | 01 | 1 | MODE-01 | lint+manual | `cd frontend && npm run lint` | ❌ new file | ⬜ pending |
| 18-01-03 | 01 | 1 | MODE-01, MODE-05 | lint+manual | `cd frontend && npm run lint` | ❌ modified | ⬜ pending |
| 18-02-01 | 02 | 2 | MODE-03 | lint+build | `cd frontend && npm run lint && npm run build` | ❌ new file | ⬜ pending |
| 18-02-02 | 02 | 2 | MODE-03 | lint+build | `cd frontend && npm run lint && npm run build` | ❌ new file | ⬜ pending |
| 18-02-03 | 02 | 2 | MODE-02 | lint+build | `cd frontend && npm run lint && npm run build` | ✅ modified | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `cd frontend && npm run lint` passes with zero warnings before Phase 18 tasks begin

*Existing infrastructure covers all phase requirements (lint + build gates). No test stubs needed — frontend test framework does not exist in this project.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Header ModeToggle renders on project routes, absent on non-project routes | MODE-01 | No frontend test framework | Navigate to /projects/:id — see dropdown. Navigate to /books — no dropdown. |
| Screenwriting mode shows existing workspace unchanged | MODE-02 | Visual regression check | Open project → Screenwriting mode → workspace renders normally with amber palette |
| Breakdown route renders 3-panel skeleton with placeholders | MODE-03 | Visual layout check | Switch to Script Breakdown → see 3 panels with labeled placeholders |
| Breakdown mode applies cool blue-grey palette to entire chrome including header | MODE-04 | Visual design check | In breakdown mode: header, background, accents are steel-blue, not amber |
| Mode switch preserves project data (no data loss) | MODE-05 | React Query cache inspection | Switch modes repeatedly — project data stays loaded, no refetch required |
| .breakdown-mode class cleanup on navigation | MODE-04 | Browser DevTools inspection | Navigate away from /breakdown → inspect `<html>` classList → no `breakdown-mode` class |
| Panel resize persists across refresh | MODE-03 | Manual persistence check | Resize panels → refresh page → panels restore to saved widths |
| Panel collapse/expand works | MODE-03 | Manual interaction check | Click collapse button → panel collapses to strip → click expand → restores |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
