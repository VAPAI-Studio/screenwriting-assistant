---
phase: 2
slug: pipeline-composer-service
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already configured) |
| **Config file** | None — pytest runs from `backend/` with `app/tests/` autodiscovery |
| **Quick run command** | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py -x` |
| **Full suite command** | `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/test_pipeline_composer.py -x`
- **After every plan wave:** Run `cd /Users/yvesfogel/Desktop/screenwriting-assistant/backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | COMP-01 | unit (mock AI) | `python -m pytest app/tests/test_pipeline_composer.py::test_compose_produces_mappings -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | COMP-01 | unit | `python -m pytest app/tests/test_pipeline_composer.py::test_compose_zero_agents -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | COMP-01 | unit | `python -m pytest app/tests/test_pipeline_composer.py::test_prompt_includes_all_wizard_targets -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | COMP-01 | unit (mock AI) | `python -m pytest app/tests/test_pipeline_composer.py::test_batch_splitting -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | COMP-03 | unit (mock AI) | `python -m pytest app/tests/test_pipeline_composer.py::test_cache_hit_deterministic -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | COMP-03 | unit | `python -m pytest app/tests/test_pipeline_composer.py::test_cosmetic_change_no_recompose -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | COMP-03 | unit | `python -m pytest app/tests/test_pipeline_composer.py::test_semantic_change_invalidates_cache -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_pipeline_composer.py` — stubs for COMP-01, COMP-03 (all tests above)
- [ ] Mock fixture for `chat_completion` — needed to test composition without live AI calls (similar to existing `mock_embed` fixture pattern in conftest.py)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| *None* | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
