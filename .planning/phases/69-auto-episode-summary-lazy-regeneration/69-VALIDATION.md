---
phase: 69
slug: auto-episode-summary-lazy-regeneration
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-17
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 69-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (SQLite-backed `db_session`, `client`, `mock_auth_headers` fixtures) |
| **Config file** | `backend/conftest.py` (existing); new `test_episode_summary.py` reuses helpers from `test_episode_summary_staleness.py` / `test_bible_injection.py` |
| **Quick run command** | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/test_episode_summary.py -q` |
| **Full suite command** | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/ -q` |
| **Estimated runtime** | ~1s (episode_summary file), ~13s (full) |

> Tests MUST mock the provider call (patch `chat_completion` where summarize_episode imports it) so they are deterministic and offline — never hit a live AI API in a unit test.
> KNOWN PRE-EXISTING failures (out of scope, NOT phase-69 regressions): 5 in test_mcp_foundation.py / test_session_isolation.py / test_yolo_integration.py.

---

## Sampling Rate

- **After every task commit:** quick run (`test_episode_summary.py`)
- **After every plan wave:** full suite
- **Before `/gsd:verify-work`:** full suite green (minus the 5 known pre-existing failures)
- **Max feedback latency:** ~13s

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| ESUM-01 | Completing an episode generates + stores a summary; stale flag cleared | unit (mock chat_completion) | `pytest app/tests/test_episode_summary.py -k initial -x` | ❌ W0 |
| ESUM-01 | Source text read by `episode_index`, never positional (insert rows out-of-order) | unit | `pytest app/tests/test_episode_summary.py -k by_index -x` | ❌ W0 |
| ESUM-03 | Stale prior regenerated before connected read; flag cleared; marker gone | integration (mock provider) | `pytest app/tests/test_episode_summary.py -k lazy_regen -x` | ❌ W0 |
| ESUM-03 | Up-to-date prior NOT regenerated (SC-3) | unit | `pytest app/tests/test_episode_summary.py -k preserves_fresh -x` | ❌ W0 |
| ESUM-03 | Regen failure → flag stays True, Phase 68 marker injected, generation proceeds | unit (provider raises) | `pytest app/tests/test_episode_summary.py -k regen_failure -x` | ❌ W0 |
| ESUM-03 | Summary-less prior is not regenerated (existence-gate) | unit | `pytest app/tests/test_episode_summary.py -k existence_gate -x` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Testable seams (planner must cover all four):**
> 1. `summarize_episode(db, project)` — mock `chat_completion`, assert prompt is bounded & prose-only, returns stripped text, writes `episode_summary`, clears `episode_summary_stale`, commits.
> 2. `_read_episode_text_by_index` — insert `ScreenplayContent` rows with shuffled `episode_index`, assert reconstructed order follows `episode_index` (the recurring positional-read bug — bit the project twice).
> 3. `regenerate_stale_priors(db, show, project)` — seed mixed stale/fresh priors, assert ONLY stale-with-summary touched, flags cleared on success, failure leaves flag True.
> 4. End-to-end: connected `build_bible_context` after the pre-pass shows fresh text and no `(summary may be out of date)` marker for regenerated priors.

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_episode_summary.py` — covers ESUM-01 + ESUM-03 (reuse `test_episode_summary_staleness.py` / `test_bible_injection.py` fixtures + Show/Project/ScreenplayContent setup helpers)
- [ ] A `chat_completion` mock/patch helper so summary tests are deterministic and offline

*No framework install needed — pytest + fixtures already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none_ | | | |

*All behaviors automated via mocked-provider unit/integration tests.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`test_episode_summary.py` + provider mock)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
