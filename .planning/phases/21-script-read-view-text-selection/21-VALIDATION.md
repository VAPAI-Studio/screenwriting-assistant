---
phase: 21
slug: script-read-view-text-selection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), TypeScript compiler (frontend — no jest/vitest configured) |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -x` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm run build` (TypeScript compilation check, frontend only)
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green + `npm run build` passing
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | SELC-01 | manual + build | `npm run build` | ✅ existing | ⬜ pending |
| 21-01-02 | 01 | 1 | SELC-02, SELC-03 | manual + build | `npm run build` | ✅ existing | ⬜ pending |
| 21-01-03 | 01 | 1 | SELC-04 | integration | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -x` | ✅ existing | ⬜ pending |
| 21-01-04 | 01 | 1 | SELC-05 | manual + build | `npm run build` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

This phase is purely frontend with no new test framework needed. The backend API already handles shot creation with `script_text`, `script_range`, and `scene_item_id`. No new test stubs are required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Read-only script text renders in left panel (breakdown mode) | SELC-01 | Frontend visual component; no frontend test runner | Open breakdown mode, verify left panel shows screenplay text, verify text is not editable |
| Selecting text shows floating bar with line count | SELC-02, SELC-03 | Browser Selection API interaction; DOM positioning behavior | Select text in script view, verify floating bar appears with correct line count and "+ Add Shot" button |
| Selection bar dismisses on outside click or X button | SELC-05 | Browser event handling | Select text, click outside the bar → verify dismissal; repeat, click X → verify dismissal |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
