---
phase: 25
slug: staleness-sync
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `backend/app/tests/conftest.py` |
| **Quick run command** | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_shotlist_staleness.py -x` |
| **Full suite command** | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_shotlist_staleness.py -x`
- **After every plan wave:** Run `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 0 | SYNC-01 | unit | `pytest app/tests/test_shotlist_staleness.py -x` | ❌ W0 | ⬜ pending |
| 25-01-02 | 01 | 1 | SYNC-01 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_patch_write_phase_sets_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-03 | 01 | 1 | SYNC-01 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_patch_scenes_phase_sets_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-04 | 01 | 1 | SYNC-01 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_script_wizard_sets_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-05 | 01 | 1 | SYNC-01 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_scene_wizard_sets_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-06 | 01 | 1 | SYNC-01 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_no_stale_without_shots -x` | ❌ W0 | ⬜ pending |
| 25-01-07 | 01 | 1 | SYNC-03 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_create_character_sets_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-08 | 01 | 1 | SYNC-04 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_create_scene_sets_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-09 | 01 | 1 | SYNC-04 | integration | `pytest app/tests/test_shotlist_staleness.py::TestShotlistStalenessHooks::test_acknowledge_clears_stale -x` | ❌ W0 | ⬜ pending |
| 25-01-10 | 01 | 2 | SYNC-02 | manual | Visual check in browser | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_shotlist_staleness.py` — stubs for SYNC-01, SYNC-03, SYNC-04 (modeled on existing `test_staleness.py`)
- No framework install needed — pytest already configured
- No conftest.py changes needed — existing fixtures (client, db_session, mock_auth_headers) cover all test needs

*Existing infrastructure covers frontend verification (manual only for SYNC-02).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ShotlistStalenessBar renders in BreakdownLayout | SYNC-02 | React component visual rendering; no automated snapshot tests configured | 1. Create a project, generate script. 2. Switch to Breakdown mode. 3. Verify amber staleness banner appears above shotlist panel. 4. Click dismiss. Verify banner disappears. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
