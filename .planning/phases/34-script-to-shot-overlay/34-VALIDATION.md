---
phase: 34
slug: script-to-shot-overlay
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | TypeScript compiler check (frontend only — no new backend) |
| **Config file** | `frontend/tsconfig.json` |
| **Quick run command** | `cd frontend && npx tsc --noEmit 2>&1 \| head -20` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -q --ignore=app/tests/test_session_isolation.py --ignore=app/tests/test_yolo_integration.py 2>&1 \| tail -5` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** `cd frontend && npx tsc --noEmit 2>&1 | head -20`
- **After every plan wave:** Full backend suite (non-pre-existing failures must be 0)
- **Before `/gsd:verify-work`:** Both must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 1 | SSO-01 | unit (tsc) | `cd frontend && npx tsc --noEmit 2>&1 \| head -20` | N/A (new files) | ⬜ pending |
| 34-01-02 | 01 | 1 | SSO-01 | manual | Click shot overlay → popover shows shot fields | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No new test files needed — purely frontend, no new API endpoints.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shot passages show steel-blue background tint | SSO-01 | Visual rendering | Open script read view → passages with linked shots should show low-opacity blue bg |
| Clicking tinted passage opens popover with shot details | SSO-01 | Interaction | Click tinted passage → popover shows shot number, size, angle, description |
| Passages with no script_text link are untinted | SSO-01 | Visual non-rendering | Confirm un-linked passages have no background color |
| Element highlights still work alongside shot overlay | SSO-01 | Non-regression | Hover/click element underline still shows tooltip and navigates |
| Text selection for shots still works | SSO-01 | Non-regression | Select text → SelectionBar still appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
