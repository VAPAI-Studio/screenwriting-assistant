---
phase: 12
slug: staleness-hooks
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (with async support via pytest-asyncio) |
| **Config file** | `backend/pytest.ini` or pyproject.toml |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_staleness.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_staleness.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_write_phase_sets_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_scenes_phase_sets_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_patch_non_write_phase_no_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_script_wizard_sets_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_create_scene_sets_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_update_scene_sets_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-07 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_delete_scene_sets_stale -x` | ❌ W0 | ⬜ pending |
| 12-01-08 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_no_stale_without_breakdown -x` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | SYNC-04 | integration | `pytest app/tests/test_staleness.py::TestStalenessHooks::test_extraction_clears_stale -x` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | SYNC-04 | integration | `pytest app/tests/test_breakdown_service.py::TestBreakdownService::test_extraction_produces_elements -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_staleness.py` — new test file covering SYNC-03 and SYNC-04 staleness hooks
- [ ] No framework install needed — pytest already configured
- [ ] No conftest changes needed — existing fixtures sufficient

*Existing infrastructure covers framework requirements.*

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
