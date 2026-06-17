---
phase: 68
slug: mode-aware-generation-context-injection
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-17
---

# Phase 68 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` / `backend/conftest.py` (SQLite test DB) |
| **Quick run command** | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/test_bible_injection.py -q` |
| **Full suite command** | `cd backend && PYTHONPATH=. ./venv/bin/python -m pytest app/tests/ -q` |
| **Estimated runtime** | ~12 seconds (full), <1s (bible-injection only) |

> NOTE (from Phase 67): the `mcp` package must be installed in `backend/venv` or the WHOLE suite fails to collect (`app.main` imports the MCP server). It is currently installed with `starlette<0.37` re-pinned for FastAPI 0.110 compat. Pre-existing failures in `test_mcp_foundation.py` / `test_session_isolation.py` / `test_yolo_integration.py` (5 total) are out of scope and NOT phase-68 regressions.

---

## Sampling Rate

- **After every task commit:** Run quick command (`test_bible_injection.py`)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite green (modulo the 5 known pre-existing failures)
- **Max feedback latency:** ~12 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _planner fills_ | | | SCONT-02/03/04 | | | unit | `pytest app/tests/test_bible_injection.py -k ...` | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> The planner MUST cover these seams (from RESEARCH §Validation Architecture):
> - **SCONT-02 / connected:** prior-episode summaries injected, ordered by `episode_number.asc()` (NOT positional — the recurring v6.0/v7.0 ordering bug), most-recent-8 cap, stale summaries injected with `(summary may be out of date)` marker.
> - **SCONT-03 / anthology:** ONLY bible injected, no `## Prior Episodes` block fires.
> - **SCONT-04 / standalone + show_id NULL:** standalone show gets bible only (no prior-episode block); `show_id` NULL feature film unchanged (None/bible-only as today).
> - **Graceful degradation:** connected episode with missing/empty prior summaries still generates (no error).
> - **VARCHAR-enum trap:** mode compared to `ContinuityMode.CONNECTED.value`, not the enum object.

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_bible_injection.py` — existing file; extend with continuity-mode cases (no new framework install needed)

*Existing infrastructure covers all phase requirements — no Wave 0 framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _none expected_ | | | |

*All phase behaviors have automated verification (injection is a pure string-builder seam — fully unit-testable).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
