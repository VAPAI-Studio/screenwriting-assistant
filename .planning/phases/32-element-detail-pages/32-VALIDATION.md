---
phase: 32
slug: element-detail-pages
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + FastAPI TestClient (SQLite in-memory) |
| **Config file** | `backend/app/tests/conftest.py` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_breakdown_api.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_breakdown_api.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 1 | EDP-01 | unit | `cd backend && python -m pytest app/tests/test_breakdown_api.py::TestGetElement -x -q` | ❌ W0 | ⬜ pending |
| 32-01-02 | 01 | 1 | EDP-01 | unit | `cd backend && python -m pytest app/tests/test_breakdown_api.py::TestUpdateElementMetadata -x -q` | ❌ W0 | ⬜ pending |
| 32-02-01 | 02 | 2 | EDP-01 | manual | Click element card → verify navigation to detail page | N/A | ⬜ pending |
| 32-02-02 | 02 | 2 | EDP-01 | manual | Detail page shows name, category, description, scenes, extended fields | N/A | ⬜ pending |
| 32-02-03 | 02 | 2 | EDP-02 | manual | Gallery shows media, upload works, delete works, expand shows full image | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_breakdown_api.py::TestGetElement` — test class for GET /breakdown/element/{element_id} endpoint
- [ ] `app/tests/test_breakdown_api.py::TestUpdateElementMetadata` — test for metadata persistence via PUT

*Existing infrastructure (conftest.py, TestClient, db_session, mock_auth_headers) covers all shared fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Element card click navigates to detail page | EDP-01 | Frontend navigation behavior | Click any element card in breakdown view → should navigate to /projects/:id/breakdown/elements/:elementId |
| Detail page renders name, category, description, scenes | EDP-01 | Full-page render check | Visit element detail page → verify header shows element name and category badge, scene list is populated |
| Extended fields form saves and persists | EDP-01 | State persistence | Fill extended field → blur → refresh page → field should still be populated |
| Image gallery upload, delete, expand | EDP-02 | Media upload flow | Upload image in gallery → verify thumbnail appears → click to expand → lightbox shows full image → delete → thumbnail disappears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
