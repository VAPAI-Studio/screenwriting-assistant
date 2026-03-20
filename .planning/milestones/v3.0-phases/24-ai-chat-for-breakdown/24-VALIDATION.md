---
phase: 24
slug: ai-chat-for-breakdown
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 0 | CHAT-02, CHAT-03, CHAT-04, CHAT-05 | unit/integration | `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py -x` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 1 | CHAT-02, CHAT-03 | unit | `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py::test_stream_includes_shots_context app/tests/test_breakdown_chat_api.py::test_stream_includes_elements_context -x` | ❌ W0 | ⬜ pending |
| 24-01-03 | 01 | 1 | CHAT-01 | manual | Visual: right sidebar shows BreakdownChat in breakdown mode | N/A | ⬜ pending |
| 24-02-01 | 02 | 2 | CHAT-04 | integration | `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py::test_shot_create_action -x` | ❌ W0 | ⬜ pending |
| 24-02-02 | 02 | 2 | CHAT-05 | integration | `cd backend && python -m pytest app/tests/test_breakdown_chat_api.py::test_shot_modify_action -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_breakdown_chat_api.py` — stubs for CHAT-02, CHAT-03, CHAT-04, CHAT-05
- [ ] Verify `backend/app/tests/conftest.py` fixtures work with new breakdown_chat router registration

*CHAT-01 is manual-only (visual rendering verification) — no automated test stub needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Right sidebar renders BreakdownChat in breakdown mode | CHAT-01 | React component rendering; no backend endpoint to test | Open a project in breakdown mode → confirm right sidebar shows chat input and message area |
| ShotProposalCard appears with correct shot fields after AI response | CHAT-04, CHAT-05 | UI confirmation card rendering; requires live AI response | Ask AI to create a shot → confirm proposal card shows shot number, scene, and key fields with Create/Dismiss buttons |
| React Query shot list refreshes after shot confirmation | CHAT-04, CHAT-05 | Requires live UI interaction | Confirm a shot creation → verify ShotlistPanel updates without manual refresh |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
