---
phase: 3
slug: pipeline-map-api-and-crud-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 (with pytest-asyncio for async tests) |
| **Config file** | None — pytest invoked directly from `backend/` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_pipeline_api.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_pipeline_api.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | COMP-04 | integration | `pytest app/tests/test_pipeline_api.py::test_get_pipeline_map_returns_entries -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | COMP-04 | integration | `pytest app/tests/test_pipeline_api.py::test_get_pipeline_map_empty -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | COMP-01 | unit (mock) | `pytest app/tests/test_pipeline_api.py::test_create_agent_triggers_recomposition -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 1 | COMP-03 | unit (mock) | `pytest app/tests/test_pipeline_api.py::test_update_semantic_field_triggers_recomposition -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 1 | COMP-03 | unit (mock) | `pytest app/tests/test_pipeline_api.py::test_update_cosmetic_field_no_recomposition -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 1 | COMP-01 | integration | `pytest app/tests/test_pipeline_api.py::test_delete_agent_cascades_and_recomposes -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_pipeline_api.py` — stubs for COMP-01 (trigger side), COMP-03 (CRUD gate), COMP-04
- [ ] Test approach: Use `TestClient` from conftest for integration tests; mock `pipeline_composer.compose_pipeline` to avoid live AI calls; verify `background_tasks.add_task` was called (or not called) with correct arguments

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
