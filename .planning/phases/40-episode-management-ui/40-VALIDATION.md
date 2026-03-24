---
phase: 40
slug: episode-management-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + TypeScript tsc (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick pytest command
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | EPIS-03 | pytest | `pytest app/tests/test_shows_api.py -q` | ✅ | ⬜ pending |
| 40-01-02 | 01 | 1 | EPIS-03 | manual + tsc | TypeScript build + visual | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `frontend/src/components/Shows/EpisodeList.tsx` — new component stub
- [ ] `frontend/src/components/Shows/CreateEpisodeModal.tsx` — new component stub

*Backend episode list endpoint must be added in Task 1 before frontend can compile against it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Episode list renders in ShowDetail | EPIS-03 | React UI rendering | Navigate to /shows/{id}, verify episode list visible |
| New Episode dialog creates episode | EPIS-03 | User interaction | Click New Episode, fill form, submit, verify list updates |
| Clicking episode navigates to editor | EPIS-03 | Navigation | Click episode row, verify /projects/{id} loads with pipeline |
| Delete episode removes from list | EPIS-03 | User interaction + confirm | Click delete, confirm, verify row removed |

---

## Validation Sign-Off

- [ ] All tasks have automated or manual verify
- [ ] Wave 0 stubs in place
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
