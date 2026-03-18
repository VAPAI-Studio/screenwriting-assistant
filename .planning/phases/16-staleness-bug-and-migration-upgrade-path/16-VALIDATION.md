---
phase: 16
slug: staleness-bug-and-migration-upgrade-path
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini (or pyproject.toml) |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_staleness.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_staleness.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | SYNC-03 | unit | `cd backend && python -m pytest app/tests/test_staleness.py::TestStalenessHooks::test_scene_wizard_sets_stale -x -q` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | SYNC-03 | filesystem | `ls backend/migrations/delta/ \| grep breakdown` | ✅ | ⬜ pending |
| 16-01-03 | 01 | 1 | SYNC-03 | unit | `cd backend && python -m pytest app/tests/test_staleness.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_staleness.py` — add `test_scene_wizard_sets_stale` stub (test file already exists, adding new test method)

*Existing infrastructure covers the rest of the phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `db_migrator.py` applies delta on pre-v2.0 DB startup | SYNC-03 | Requires Docker volume + restart cycle | Spin fresh container, confirm breakdown tables created on startup |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
