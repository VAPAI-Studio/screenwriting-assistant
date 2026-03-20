---
phase: 27
slug: generate-shotlist-ui-ai-badge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) |
| **Config file** | `backend/pytest.ini` or inline |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -x -q`
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | AISG-01 | unit | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` | ✅ | ⬜ pending |
| 27-01-02 | 01 | 1 | AISG-01 | manual | Visual check in browser | N/A | ⬜ pending |
| 27-01-03 | 01 | 1 | AISG-07 | manual | Visual check for sparkle badge | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements (frontend-only changes, backend tests already cover generate endpoint).

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Generate button visible in shotlist panel | AISG-01 | UI visual placement | Open breakdown panel, confirm button in shotlist header |
| Loading state while generation runs | AISG-01 | Async UX behavior | Click generate, observe spinner/disabled state during API call |
| Shotlist refreshes after generation | AISG-01 | React Query cache invalidation | After generate completes, confirm new shots appear without page reload |
| AI badge (sparkle icon) on generated shots | AISG-07 | Visual badge presence | After generation, confirm ✨ icon on each AI-generated shot, absent on manual shots |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
