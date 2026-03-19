---
phase: 22
slug: media-upload-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 |
| **Config file** | none — pytest runs from `backend/` directory |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_media_api.py -x` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/test_media_api.py -x`
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-00 | 01 | 0 | MDIA-01, MDIA-02, MDIA-05, MDIA-06, MDIA-07, DATA-05 | integration | `pytest app/tests/test_media_api.py -x` | ❌ W0 | ⬜ pending |
| 22-01-01 | 01 | 1 | MDIA-01, MDIA-02, MDIA-06, MDIA-07 | integration | `pytest app/tests/test_media_api.py::TestUploadMedia -x` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | DATA-05, MDIA-05 | integration | `pytest app/tests/test_media_api.py::TestListMedia app/tests/test_media_api.py::TestDeleteMedia -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | — | integration | `pytest app/tests/ -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_media_api.py` — test stubs for MDIA-01, MDIA-02, MDIA-05, MDIA-06, MDIA-07, DATA-05
- [ ] Pillow install: `pip install "Pillow>=12.0"` and add to `requirements.txt`
- [ ] `MEDIA_DIR` temp directory fixture for isolated test runs (via `tmp_path` or `tempfile.mkdtemp`)

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
