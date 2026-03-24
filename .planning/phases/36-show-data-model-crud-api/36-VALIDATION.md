---
phase: 36
slug: show-data-model-crud-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 |
| **Config file** | backend/pytest.ini or pyproject.toml |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shows.py -q` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest app/tests/test_shows.py -q`
- **After every plan wave:** Run `pytest app/tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 0 | SHOW-01 | unit stub | `pytest app/tests/test_shows.py -q` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | 1 | SHOW-01, SHOW-04 | unit | `pytest app/tests/test_shows.py -q` | ✅ | ⬜ pending |
| 36-01-03 | 01 | 1 | SHOW-01, SHOW-04 | integration | `pytest app/tests/test_shows.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_shows.py` — failing stubs for SHOW-01, SHOW-04 CRUD endpoints

*Existing infrastructure (pytest, httpx, fixtures) covers all other requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
