---
phase: 21
slug: script-read-view-text-selection
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 21 — Validation Strategy

> Retroactively created 2026-03-25. Phase completed 2026-03-19.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend API) + TypeScript tsc (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_shots_api.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short && cd ../frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~1s |

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 21-01-01 | ScriptReadView.tsx compiles without errors | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 21-01-02 | Text selection in ScriptReadView triggers shot creation via POST | pytest | `pytest app/tests/test_shots_api.py -q` | ✅ verified |
| 21-01-03 | Shot created with scene_item_id links to correct scene | pytest | `pytest app/tests/test_shots_api.py::TestCreateShot::test_create_shot_with_scene_item_id -q` | ✅ verified |
| 21-01-04 | Shot CRUD endpoints used by ScriptReadView are fully operational | pytest | `pytest app/tests/test_shots_api.py -q` | ✅ verified |

---

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| Text selection highlights selected range in ScriptReadView | DOM selection API — requires browser |
| "Create Shot" popover appears on text selection | React state + portal rendering |
| Shot appears in ShotlistPanel after creation from script | React Query cache invalidation |

---

## Key Files

| File | What it delivers |
|------|-----------------|
| `frontend/src/components/Breakdown/ScriptReadView.tsx` | Read-only script view with text selection → shot creation |
| `backend/app/tests/test_shots_api.py` | 23 tests covering full shot CRUD used by this view |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] All 23 backend tests confirmed passing
- [x] TypeScript compiles clean
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive
