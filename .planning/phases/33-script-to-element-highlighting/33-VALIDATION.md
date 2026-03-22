---
phase: 33
slug: script-to-element-highlighting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + TypeScript compiler check (frontend) |
| **Config file** | `backend/app/tests/conftest.py` |
| **Quick run command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** `cd backend && python -m pytest app/tests/ -x -q`
- **After every plan wave:** `npx tsc --noEmit 2>&1 | head -20`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | SEL-01 | unit (frontend) | `npx tsc --noEmit 2>&1 \| head -20` | N/A (new files) | ⬜ pending |
| 33-01-02 | 01 | 1 | SEL-01 | manual | Click element highlight → verify navigation | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- No new test files needed — highlighting is pure frontend with no new API endpoints.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Character names highlighted with amber underline | SEL-01 | Visual rendering | Open script read view → verify character names have amber underline |
| Location headings highlighted with blue underline | SEL-01 | Visual rendering | Open script read view → verify location headings have blue underline |
| Tooltip shows element name and category on hover | SEL-01 | Browser hover state | Hover over highlight → tooltip appears with name + category |
| Click highlight navigates to element detail page | SEL-01 | Navigation behavior | Click highlighted element → navigates to /projects/:id/breakdown/elements/:elementId |
| Text selection still works in script view | SEL-01 | Non-regression | Select text in script → SelectionBar appears; no conflict with highlights |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
