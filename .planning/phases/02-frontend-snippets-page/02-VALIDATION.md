---
phase: 2
slug: frontend-snippets-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — run from `backend/` directory with venv active |
| **Quick run command** | `pytest app/tests/test_snippet_manager.py app/tests/test_snippet_extraction.py -v -x` |
| **Full suite command** | `pytest app/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest app/tests/test_snippet_manager.py app/tests/test_snippet_extraction.py -v -x`
- **After every plan wave:** Run `pytest app/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | EXTR-01, EXTR-02, EXTR-03, BROW-02, BROW-03, EDIT-03 | unit | `pytest app/tests/test_snippet_manager.py app/tests/test_snippet_extraction.py -v -x` | ❌ Wave 0 | ⬜ pending |
| 02-01-02 | 01 | 1 | EXTR-01, EXTR-02 | unit | `pytest app/tests/test_snippet_extraction.py -v -x` | ❌ Wave 0 | ⬜ pending |
| 02-02-01 | 02 | 1 | BROW-02, BROW-03, EDIT-03, EXTR-03 | unit | `pytest app/tests/test_snippet_manager.py -v -x` | ❌ Wave 0 | ⬜ pending |
| 02-02-02 | 02 | 1 | NAV-01, NAV-02, BROW-04, BROW-05, BROW-06 | manual | visual inspection in browser | N/A | ⬜ pending |
| 02-03-01 | 03 | 2 | NAV-01, NAV-02 | manual | visual inspection | N/A | ⬜ pending |
| 02-03-02 | 03 | 2 | BROW-04, BROW-05, BROW-06, EDIT-03 | manual | visual inspection | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_snippet_manager.py` — stubs for BROW-02, BROW-03, EDIT-03, EXTR-03 (Snippet API endpoints)
- [ ] `backend/app/tests/test_snippet_extraction.py` — stubs for EXTR-01, EXTR-02 (AI extraction pipeline)

*Frontend NAV-01, NAV-02, BROW-04, BROW-05, BROW-06 are manual-only — no frontend test framework configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Snippets nav link routes to /snippets | NAV-01 | No frontend test framework | Navigate to app, confirm "Snippets" in header |
| Book selector loads books, selecting book triggers snippet fetch | NAV-02 | No frontend test framework | Select a book, confirm list loads |
| Client-side search filters without network request | BROW-04 | No frontend test framework | Open DevTools Network, type in search — zero XHR |
| Processing banner when book not COMPLETED | BROW-05 | No frontend test framework | Select a processing book, confirm banner shown, edit disabled |
| Total token count stays fixed when filter is active | BROW-06 | No frontend test framework | Filter snippets, confirm token count unchanged |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
