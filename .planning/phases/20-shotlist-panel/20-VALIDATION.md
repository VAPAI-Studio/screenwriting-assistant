---
phase: 20
slug: shotlist-panel
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 20 — Validation Strategy

> Retroactively created 2026-03-25. Phase completed 2026-03-19.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend API) + TypeScript tsc (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short` |
| **Estimated runtime** | ~0.5s |

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 20-01-01 | Shot CRUD API (all 23 endpoints) | pytest | `pytest app/tests/test_shots_api.py -q` | ✅ verified |
| 20-02-01 | ShotlistPanel.tsx compiles without errors | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 20-02-02 | QUERY_KEYS.SHOTS defined in constants.ts | grep | `grep "SHOTS" frontend/src/lib/constants.ts` | ✅ verified |
| 20-02-03 | listShots, createShot, updateShot, deleteShot, reorderShots in api.tsx | grep | `grep -E "listShots|createShot|updateShot|deleteShot|reorderShots" frontend/src/lib/api.tsx` | ✅ verified |

---

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| Shotlist panel renders scene-grouped shots | React UI — requires browser |
| Inline shot field edit updates via optimistic mutation | React Query optimistic update state |
| Drag-to-reorder changes sort_order and persists on drop | DnD interaction + API call |
| Shot count badge on scene header updates live | React Query cache |

---

## Key Files

| File | What it delivers |
|------|-----------------|
| `frontend/src/components/Breakdown/ShotlistPanel.tsx` | Scene-grouped shotlist with optimistic create/update/delete/reorder mutations |
| `frontend/src/lib/api.tsx` (lines ~932–999) | listShots, createShot, updateShot, deleteShot, reorderShots, generateShotlist |
| `frontend/src/lib/constants.ts` (line 190) | `QUERY_KEYS.SHOTS: (projectId) => ['shots', projectId]` |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] All 23 backend tests confirmed passing
- [x] TypeScript compiles clean
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive
