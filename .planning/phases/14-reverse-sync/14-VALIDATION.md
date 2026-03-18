---
phase: 14
slug: reverse-sync
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none — runs via `pytest app/tests/test_breakdown_api.py` |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_api.py -x -q`
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | SYNC-05 | unit | `pytest app/tests/test_breakdown_api.py::TestSyncToProject -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | SYNC-05 | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_sync_creates_list_item -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | SYNC-05 | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_sync_already_exists -x` | ❌ W0 | ⬜ pending |
| 14-01-04 | 01 | 1 | SYNC-05 | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_synced_flag_after_sync -x` | ❌ W0 | ⬜ pending |
| 14-01-05 | 01 | 1 | SYNC-05 | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_synced_flag_before_sync -x` | ❌ W0 | ⬜ pending |
| 14-01-06 | 01 | 1 | SYNC-05 | integration | `pytest app/tests/test_breakdown_api.py::TestSyncToProject::test_sync_creates_phase_data_if_missing -x` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 2 | SYNC-05 | manual | See manual verifications below | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_breakdown_api.py::TestSyncToProject` — add class with stubs for all SYNC-05 behaviors (class does not yet exist)

*conftest.py, db fixtures, and client fixture all exist — no framework setup needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| "Add to Characters" button renders on character ElementCards | SYNC-05 | Frontend UI — no automated test for conditional rendering | Navigate to Breakdown → Characters tab; confirm each ElementCard shows "+ Add to Characters" button when not yet synced |
| Button transitions to "Synced" state after click | SYNC-05 | Frontend mutation state — no automated test for UI state after mutation | Click "+ Add to Characters" on any character; verify button disappears and "Synced" label appears |
| Character appears in Characters phase after sync | SYNC-05 | Cross-page integration — requires navigating to Characters page | After syncing a character, navigate to Project → Characters; confirm the character appears in the Supporting card group |
| Duplicate detection — button shows Synced for already-synced characters | SYNC-05 | Requires pre-existing data state | Sync a character, reload the breakdown page, verify the same character shows "Synced" immediately |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
