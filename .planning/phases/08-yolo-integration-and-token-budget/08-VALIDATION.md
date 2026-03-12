---
phase: 8
slug: yolo-integration-and-token-budget
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 + pytest-asyncio |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_yolo_integration.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_yolo_integration.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | YOLO-02 | unit | `pytest app/tests/test_yolo_integration.py::test_config_values_exist -x` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 1 | YOLO-02 | unit | `pytest app/tests/test_yolo_integration.py::test_max_agents_per_step_limits_lookup -x` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 1 | YOLO-02 | unit | `pytest app/tests/test_yolo_integration.py::test_relevance_threshold_filters_agents -x` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 2 | YOLO-01 | unit | `pytest app/tests/test_yolo_integration.py::test_yolo_wizard_routes_through_middleware -x` | ❌ W0 | ⬜ pending |
| 08-03-02 | 03 | 2 | YOLO-01 | unit | `pytest app/tests/test_yolo_integration.py::test_yolo_wizard_zero_agents_passthrough -x` | ❌ W0 | ⬜ pending |
| 08-04-01 | 04 | 2 | YOLO-01+02 | integration | `pytest app/tests/test_yolo_integration.py::test_yolo_full_run_llm_call_count -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_yolo_integration.py` — stubs for YOLO-01, YOLO-02
- [ ] No new framework install needed — pytest + pytest-asyncio already configured

*Existing infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE stream does not appear frozen during agent review | YOLO-01 | UX perception, timing-dependent | Run YOLO fill with 2+ agents mapped, observe SSE events arrive without >30s gaps |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
