---
phase: 35
slug: real-authentication-user-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.2 |
| **Config file** | `backend/app/tests/conftest.py` |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_auth.py -x` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -x --ignore=app/tests/test_session_isolation.py --ignore=app/tests/test_yolo_integration.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** `cd backend && source venv/bin/activate && pytest app/tests/test_auth.py -x`
- **After every plan wave:** Full backend suite (non-pre-existing failures must be 0)
- **Before `/gsd:verify-work`:** Both must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 01 | 0 | UM-01, UM-02, UM-03 | unit | `pytest app/tests/test_auth.py -x` | ❌ W0 | ⬜ pending |
| 35-01-02 | 01 | 1 | UM-03 | unit | `pytest app/tests/test_auth.py::TestUserModel -x` | ❌ W0 | ⬜ pending |
| 35-01-03 | 01 | 1 | UM-01 | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_register_success -x` | ❌ W0 | ⬜ pending |
| 35-01-04 | 01 | 1 | UM-02 | unit | `pytest app/tests/test_auth.py::TestAuthAPI::test_login_success -x` | ❌ W0 | ⬜ pending |
| 35-01-05 | 01 | 1 | UM-01, UM-02, UM-03 | integration | `pytest app/tests/test_auth.py::TestAuthAPI::test_jwt_accepted_by_endpoints -x` | ❌ W0 | ⬜ pending |
| 35-02-01 | 02 | 2 | UM-01, UM-02 | manual | Login/register flow in browser, /login redirects to /projects | N/A | ⬜ pending |
| 35-02-02 | 02 | 2 | UM-03 | manual | /settings/profile shows email and display_name edit form | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_auth.py` — stubs for UM-01 (register), UM-02 (login), UM-03 (user model + JWT integration)

*Note: `conftest.py` already creates all tables via `Base.metadata.create_all` — the new User model will be picked up automatically once added to `database.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Login page renders and submits successfully | UM-01, UM-02 | Frontend rendering | Navigate to /login, enter email+password, verify redirect to /projects |
| Register page creates account and logs in | UM-01 | Frontend rendering | Navigate to /register, create account, verify redirect to /projects |
| Unauthenticated users redirected to /login | UM-01, UM-02 | Browser routing | Clear localStorage, navigate to /projects, verify redirect to /login |
| Profile page shows and updates display name | UM-03 | Frontend form | Navigate to /settings/profile, update display_name, refresh, verify persisted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
