---
phase: 15
slug: phase-13-documentation-closure-and-ui-05-fix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | TypeScript compiler (frontend); pytest (backend, no changes) |
| **Config file** | `frontend/tsconfig.json` (TypeScript) |
| **Quick run command** | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/frontend && npm run build` |
| **Full suite command** | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/frontend && npm run build && npm run lint && cd ../backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Run full suite command above
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | UI-05 | build-verify | `cd frontend && npm run build` | ✅ ElementCard.tsx | ⬜ pending |
| 15-01-02 | 01 | 1 | UI-07, UI-08 | grep-verify | `grep -n 'UI-07\|UI-08' .planning/REQUIREMENTS.md` | ✅ REQUIREMENTS.md | ⬜ pending |
| 15-01-03 | 01 | 1 | UI-07, UI-08 | grep-verify | `grep -n 'requirements-completed' .planning/phases/13-breakdown-page/13-03-SUMMARY.md` | ✅ 13-03-SUMMARY.md | ⬜ pending |
| 15-01-04 | 01 | 1 | UI-01..08 | file-exists | `test -f .planning/phases/13-breakdown-page/13-VERIFICATION.md && echo EXISTS` | ❌ must create | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed.

*Phase 15 has no new backend code. All verification is TypeScript compiler + file existence + grep checks.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scene chip click navigates to correct URL | UI-05 | TypeScript doesn't type-check string route args | Click a scene chip on a breakdown element; verify URL becomes `/projects/:id/scenes/scene_list/:scene_item_id` |
| AddElementDialog opens and submits | UI-07 | JSX render + dialog open/close requires browser | Click "Add Element"; fill form; submit; verify element appears in list |
| Empty state renders when no breakdown | UI-08 | Requires no-elements database state in browser | Open a project with no breakdown; verify CTA and empty state message render |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
