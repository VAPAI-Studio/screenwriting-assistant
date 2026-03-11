---
phase: 1
slug: db-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_pipeline_map_schema.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_pipeline_map_schema.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | COMP-02 | migration | `cd backend && python -m pytest app/tests/test_pipeline_map_schema.py::test_migration -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | COMP-02 | unit | `cd backend && python -m pytest app/tests/test_pipeline_map_schema.py::test_model_import -x -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | COMP-02 | unit | `cd backend && python -m pytest app/tests/test_pipeline_map_schema.py::test_cascade_delete -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 1 | COMP-02 | unit | `cd backend && python -m pytest app/tests/test_pipeline_map_schema.py::test_schema_round_trip -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_pipeline_map_schema.py` — stubs for COMP-02 (migration, model import, cascade delete, schema round-trip)

*Existing conftest.py covers shared fixtures (SQLite patching loop handles new UUID/Enum columns automatically).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Composite index verifiable in psql | COMP-02 | Requires live PostgreSQL instance | Run `\d agent_pipeline_maps` in psql and confirm index exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
