---
phase: 38
slug: show-management-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) |
| **Config file** | backend/pytest.ini or pyproject.toml |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/bin/activate && pytest app/tests/test_shows_api.py -q --tb=short`
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 1 | SHOW-02 | manual | TypeScript build + visual | ❌ W0 | ⬜ pending |
| 38-01-02 | 01 | 1 | SHOW-03 | manual | Bible save/load visual test | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/types/index.ts` — Show, BibleResponse, BibleUpdate type additions
- [ ] `frontend/src/lib/api.tsx` — show and bible API methods

*Note: Frontend-only phase; automated tests are TypeScript compilation. Manual browser tests verify UI behavior.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Home page splits Shows/Films | SHOW-02 | React UI rendering | Navigate to /, verify two sections present |
| Show detail page loads bible | SHOW-03 | React UI + API call | Navigate to /shows/{id}, verify bible textareas populated |
| Bible auto-saves on blur | BIBL-02 | User interaction timing | Edit a bible field, click away, refresh page, verify persisted |
| Episode duration selector | BIBL-03 | Dropdown interaction | Select preset duration, verify saved |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
