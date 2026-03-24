---
phase: 41
slug: bible-ai-injection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_bible_injection.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | BIBL-04 | pytest | `pytest app/tests/test_bible_injection.py -q` | ❌ W0 | ⬜ pending |
| 41-01-02 | 01 | 1 | BIBL-04 | pytest | `pytest app/tests/test_bible_injection.py app/tests/test_shows_api.py -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_bible_injection.py` — new test file for bible injection
- [ ] `backend/app/utils/bible_context.py` — new helper module

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Episode AI generation uses bible context | BIBL-04 | Requires live AI call | Create episode under show with bible, run wizard, verify output references show characters |

---

## Validation Sign-Off

- [ ] All tasks have automated verify (pytest mocking AI calls)
- [ ] Wave 0 test stubs in place
- [ ] No watch-mode flags
- [ ] Regression: all 41 existing tests still pass
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
