---
phase: 29
slug: storyboard-data-model-mode-shell
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `backend/app/tests/conftest.py` (SQLite in-memory) |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_storyboard_api.py -x` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/test_storyboard_api.py -x`
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green + `cd frontend && npm run build` passes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 0 | SB-02 | unit stub | `pytest app/tests/test_storyboard_api.py -x` | ❌ W0 | ⬜ pending |
| 29-01-02 | 01 | 1 | SB-02 | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_create_frame -x` | ❌ W0 | ⬜ pending |
| 29-01-03 | 01 | 1 | SB-02 | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_list_frames -x` | ❌ W0 | ⬜ pending |
| 29-01-04 | 01 | 1 | SB-02 | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_update_selected -x` | ❌ W0 | ⬜ pending |
| 29-01-05 | 01 | 1 | SB-02 | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_delete_frame -x` | ❌ W0 | ⬜ pending |
| 29-01-06 | 01 | 1 | SB-02 | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_selected_exclusivity -x` | ❌ W0 | ⬜ pending |
| 29-01-07 | 01 | 1 | SB-02 | unit | `pytest app/tests/test_storyboard_api.py::TestStoryboardAPI::test_project_style -x` | ❌ W0 | ⬜ pending |
| 29-01-08 | 01 | 2 | SB-01 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 29-01-09 | 01 | 2 | SB-01 | manual | Visual check in browser | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_storyboard_api.py` — stubs for SB-02 (CRUD operations, is_selected exclusivity, project style)
- [ ] No new conftest fixtures needed — existing `client`, `mock_auth_headers`, `db_session` cover all needs

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mode toggle renders three options (Screenwriting/Breakdown/Storyboard) | SB-01 | UI visual check | Open any project, verify mode toggle shows 3 options |
| Storyboard tab has deep purple/violet accent color | SB-01 | Visual design check | Click Storyboard mode, verify purple CSS variables applied |
| Storyboard page renders (empty state) | SB-01 | Browser navigation | Navigate to `/projects/{id}/storyboard`, verify renders without crash |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
