---
phase: 26
slug: ai-shotlist-generation-service
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/setup.cfg` |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x -q` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -x -q`
- **After every plan wave:** Run `cd backend && source venv/bin/activate && pytest app/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | AISG-06 | unit | `pytest app/tests/test_shots.py::test_shot_user_modified_flag -x -q` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | AISG-01 | unit | `pytest app/tests/test_shot_generation.py::test_migration_columns -x -q` | ❌ W0 | ⬜ pending |
| 26-01-03 | 01 | 2 | AISG-01,02,03,04,05 | integration | `pytest app/tests/test_shot_generation.py::test_generation_service -x -q` | ❌ W0 | ⬜ pending |
| 26-01-04 | 01 | 2 | AISG-03 | unit | `pytest app/tests/test_shot_generation.py::test_scene_assignment -x -q` | ❌ W0 | ⬜ pending |
| 26-01-05 | 01 | 2 | AISG-04 | unit | `pytest app/tests/test_shot_generation.py::test_shot_ordering -x -q` | ❌ W0 | ⬜ pending |
| 26-01-06 | 01 | 2 | AISG-06 | integration | `pytest app/tests/test_shot_generation.py::test_smart_merge -x -q` | ❌ W0 | ⬜ pending |
| 26-01-07 | 01 | 3 | AISG-01 | integration | `pytest app/tests/test_shot_generation.py::test_generate_endpoint -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_shot_generation.py` — stubs for AISG-01 through AISG-06
- [ ] `app/tests/test_shots.py` (extend existing) — stubs for user_modified flag tests
- [ ] Fixtures for mock AI responses in conftest.py or test file

*All test stubs must be created before Wave 1 execution begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AI output quality (shot descriptions make cinematic sense) | AISG-02, AISG-04 | LLM non-determinism | Call endpoint with real script, review shots visually in Shotlist panel |
| Full screenplay token budget (large script ~10k tokens) | AISG-01 | Requires large real script | Test with 120-page screenplay export |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
