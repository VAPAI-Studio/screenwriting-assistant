---
phase: 13
slug: breakdown-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + TypeScript compiler + ESLint (frontend) |
| **Config file** | `backend/app/tests/test_breakdown_api.py` (existing) |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q && cd ../frontend && npm run build` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q && cd ../frontend && npm run build && npm run lint` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest app/tests/test_breakdown_api.py -x -q && cd ../frontend && npm run build`
- **After every plan wave:** Run `cd backend && pytest app/tests/ -x -q && cd ../frontend && npm run build && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-W0 | 01 | W0 | UI-03 | backend | `pytest app/tests/test_breakdown_api.py -x -q` | ❌ W0 | ⬜ pending |
| 13-01-01 | 01 | 1 | UI-01,UI-03 | typescript | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | UI-01,UI-02 | typescript | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | UI-02,UI-03 | typescript | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 1 | UI-01 | typescript | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | UI-01,UI-02 | typescript+manual | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-02-02 | 02 | 1 | UI-02 | typescript+manual | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-02-03 | 02 | 1 | UI-03,UI-04,UI-05 | typescript+manual | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-02-04 | 02 | 1 | UI-06 | typescript+manual | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-03-01 | 03 | 2 | UI-08 | typescript+manual | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-03-02 | 03 | 2 | UI-07 | backend+typescript | `pytest app/tests/test_breakdown_api.py -k create -x && cd ../frontend && npm run build` | ❌ W0 | ⬜ pending |
| 13-03-03 | 03 | 2 | UI-04 | typescript+manual | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_breakdown_api.py` — add `scene_links` field assertion to existing element list test
- [ ] `frontend/src/types/index.ts` — `BreakdownElement`, `BreakdownSummary`, `BreakdownRun`, `SceneLink` TypeScript types
- [ ] `frontend/src/lib/constants.ts` — `QUERY_KEYS.BREAKDOWN_*`, `BREAKDOWN_CATEGORIES` constants

*Note: No frontend test framework installed. TypeScript compilation + ESLint covers structural correctness; all behavioral testing is visual/manual.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Breakdown tab navigation | UI-01 | No route testing without jest/vitest | Click "Breakdown" tab, verify URL changes to `/projects/:id/breakdown` and page renders |
| Category tabs with count badges | UI-02 | Visual rendering requires browser | Verify each category tab shows correct element count after extraction |
| Element card full display | UI-03 | Visual layout verification | Check name, description, scene count, source badge, user-modified indicator all visible |
| Inline editing saves | UI-04 | Form interaction requires browser | Click element name, edit, press Enter, verify persisted after refresh |
| Scene chips navigate | UI-05 | Link navigation requires browser | Click scene chip, verify navigation to correct scene in workspace |
| Extract/staleness banner flow | UI-06 | Full UX flow requires running app | Run extraction, modify script, verify staleness banner appears with Refresh button |
| Add element dialog | UI-07 | Dialog interaction requires browser | Click Add, fill form, submit, verify element appears in list |
| Empty state CTA | UI-08 | Visual state requires empty project | Use project with no breakdown, verify empty state with Extract CTA renders |
| Optimistic update rollback | UI-04 | Requires network manipulation | Disable network, attempt edit, verify UI reverts on failure |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
