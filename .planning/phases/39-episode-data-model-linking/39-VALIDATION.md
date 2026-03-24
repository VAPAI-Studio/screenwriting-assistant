---
phase: 39
slug: episode-data-model-linking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 1 | EPIS-01 | pytest | `pytest app/tests/test_shows_api.py -q` | ✅ | ⬜ pending |
| 39-01-02 | 01 | 1 | EPIS-02 | pytest | `pytest app/tests/test_shows_api.py::TestEpisodesAPI -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `backend/migrations/delta/008_episode_columns.sql` — migration must apply cleanly
- [ ] `backend/app/tests/test_shows_api.py::TestEpisodesAPI` — test class stubs

*Existing infrastructure covers most requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Episodes appear in existing project pipeline | EPIS-04 | Full pipeline requires browser | Create episode, navigate to /projects/{id}, verify all pipeline modes accessible |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Wave 0 stubs in place before task execution
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
