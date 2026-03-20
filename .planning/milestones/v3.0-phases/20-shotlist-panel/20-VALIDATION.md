---
phase: 20
slug: shotlist-panel
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend); no frontend test runner configured |
| **Config file** | `backend/app/tests/conftest.py` |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -x` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Visual inspection in browser (`npm run dev`) + `cd backend && source venv/bin/activate && pytest app/tests/ -x`
- **After every plan wave:** Full backend suite + manual browser walkthrough of new UI
- **Before `/gsd:verify-work`:** Full suite must be green + all 6 requirements manually verified in browser
- **Max feedback latency:** ~10 seconds (backend tests) + ~30 seconds (manual browser check)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | SHOT-03, SHOT-07 | manual | Visual: scene-grouped table renders in breakdown center panel | N/A (frontend) | ⬜ pending |
| 20-01-02 | 01 | 1 | SHOT-04 | manual | Visual: click cell → input appears, blur → field saved | N/A (frontend) | ⬜ pending |
| 20-02-01 | 02 | 2 | SHOT-06 | manual | Visual: up/down arrows visible, click changes order, persists on reload | N/A (frontend) | ⬜ pending |
| 20-02-02 | 02 | 2 | SHOT-05 | manual | Visual: delete button, confirmation, shot removed from list | N/A (frontend) | ⬜ pending |
| 20-02-03 | 02 | 2 | SHOT-08 | manual | Visual: empty project shows CTA, clicking CTA creates first shot | N/A (frontend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — this is a frontend-only phase. Backend API and tests already exist from Phase 19. No frontend test infrastructure exists in this project, and adding it is out of scope for this phase. Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Shots grouped by scene in center panel | SHOT-03 | Frontend-only React component; no test framework | Open a project in breakdown mode, verify shots appear in scene-grouped table |
| Inline edit shot fields | SHOT-04 | DOM interaction; no test framework | Click a cell in the shotlist, type new value, click away, verify value saved |
| Delete a shot | SHOT-05 | DOM interaction; no test framework | Click delete on a shot row, confirm, verify row is removed |
| Reorder shots within scene | SHOT-06 | DOM interaction; no test framework | Click up/down arrows on a shot, verify sort_order updates and persists on reload |
| Table/grid layout in center panel | SHOT-07 | Visual layout; no test framework | Open breakdown mode, verify shotlist occupies center panel area |
| Empty state CTA shown when no shots | SHOT-08 | Conditional render; no test framework | Open project with no shots in breakdown mode, verify CTA prompt is shown |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (manual browser + backend test suite)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
