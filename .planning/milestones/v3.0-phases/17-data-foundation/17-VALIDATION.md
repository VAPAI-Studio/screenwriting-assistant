---
phase: 17
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_shotlist_models.py -x` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_shotlist_models.py -x`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | DATA-01 | unit | `pytest app/tests/test_shotlist_models.py::test_shot_importable -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | DATA-01 | unit | `pytest app/tests/test_shotlist_models.py::test_shot_orm_roundtrip -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | DATA-01 | unit | `pytest app/tests/test_shotlist_models.py::test_shot_scene_set_null -x` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 1 | DATA-01 | unit | `pytest app/tests/test_shotlist_models.py::test_shot_cascade_delete -x` | ❌ W0 | ⬜ pending |
| 17-01-05 | 01 | 1 | DATA-02 | unit | `pytest app/tests/test_shotlist_models.py::test_asset_media_importable -x` | ❌ W0 | ⬜ pending |
| 17-01-06 | 01 | 1 | DATA-02 | unit | `pytest app/tests/test_shotlist_models.py::test_asset_media_orm_roundtrip -x` | ❌ W0 | ⬜ pending |
| 17-01-07 | 01 | 1 | DATA-03 | unit | `pytest app/tests/test_shotlist_models.py::test_project_shotlist_stale -x` | ❌ W0 | ⬜ pending |
| 17-01-08 | 01 | 1 | DATA-06 | unit | `pytest app/tests/test_shotlist_models.py::test_tables_in_metadata -x` | ❌ W0 | ⬜ pending |
| 17-01-09 | 01 | 1 | ALL | unit | `pytest app/tests/test_shotlist_models.py::test_shot_schema_validation -x` | ❌ W0 | ⬜ pending |
| 17-01-10 | 01 | 1 | ALL | unit | `pytest app/tests/test_shotlist_models.py::test_shot_response_from_orm -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_shotlist_models.py` — stubs for DATA-01 through DATA-06 (model importability, ORM round-trips, cascade behavior, SET NULL behavior, schema validation, metadata alias)
- [ ] No new framework install needed (pytest already configured)
- [ ] No new conftest fixtures needed (existing `db_session`, `client`, `mock_auth_headers` sufficient; `_patch_uuid_columns_for_sqlite()` auto-handles new models)

*Existing infrastructure covers framework and fixture requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Delta migration applies on existing Docker volume | DATA-06 | Requires running Docker volume with existing data | 1. `docker compose up -d db` 2. `docker compose exec backend python -c "from app.services.db_migrator import run_migrations; run_migrations()"` 3. Verify tables exist via psql |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
