---
phase: 1
slug: backend-foundation-and-data-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` |
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
| 1-01-01 | 01 | 0 | BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03 | unit stub | `pytest app/tests/test_snippets_api.py -v` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | BROW-01 | unit | `pytest app/tests/test_snippets_api.py::test_list_snippets_paginated -v` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | EDIT-01, EDIT-02 | unit | `pytest app/tests/test_snippets_api.py::test_edit_snippet_atomic -v` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | EDIT-04 | unit | `pytest app/tests/test_snippets_api.py::test_delete_snippet_soft -v` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | CUST-01, CUST-02 | unit | `pytest app/tests/test_snippets_api.py::test_create_custom_snippet -v` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | CUST-03 | unit | `pytest app/tests/test_snippets_api.py::test_retry_book_preserves_user_chunks -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_snippets_api.py` — test stubs for all snippet operations (BROW-01, EDIT-01, EDIT-02, EDIT-04, CUST-01, CUST-02, CUST-03)
- [ ] `backend/app/tests/conftest.py` — update with `SafeVector` SQLite-compatibility patch and embedding service mock
- [ ] `backend/migrations/006_snippet_flags.sql` — migration stub for `is_deleted`, `is_user_created`, `updated_at` columns

*Existing pytest infrastructure covers the framework — Wave 0 adds stubs and fixtures only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Embedding failure triggers DB rollback (network-level) | EDIT-02 | Can't simulate real OpenAI network failure in unit tests | 1. Set invalid OPENAI_API_KEY in .env 2. PUT /api/books/{id}/snippets/{chunk_id} with new content 3. Verify DB still has original content |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
