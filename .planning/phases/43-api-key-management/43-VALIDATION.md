---
phase: 43
slug: api-key-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_api_keys.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short && cd ../frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~5s |

---

## Sampling Rate

- **After every task commit:** Run `pytest app/tests/test_api_keys.py -q --tb=short`
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | AK-01 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyModel::test_api_key_model_columns -q` | ❌ W0 | ⬜ pending |
| 43-01-02 | 01 | 1 | AK-01 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyModel::test_key_hash_matches_sha256 -q` | ❌ W0 | ⬜ pending |
| 43-01-03 | 01 | 1 | AK-01, AK-02 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_create_api_key -q` | ❌ W0 | ⬜ pending |
| 43-01-04 | 01 | 1 | AK-02 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_create_returns_full_key_once -q` | ❌ W0 | ⬜ pending |
| 43-01-05 | 01 | 1 | AK-02 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_list_does_not_expose_secret -q` | ❌ W0 | ⬜ pending |
| 43-01-06 | 01 | 1 | AK-01 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_create_api_key_validation -q` | ❌ W0 | ⬜ pending |
| 43-01-07 | 01 | 1 | AK-03 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_api_key_authenticates_endpoint -q` | ❌ W0 | ⬜ pending |
| 43-01-08 | 01 | 1 | AK-03 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_expired_key_rejected -q` | ❌ W0 | ⬜ pending |
| 43-01-09 | 01 | 1 | AK-03 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_revoked_key_rejected -q` | ❌ W0 | ⬜ pending |
| 43-01-10 | 01 | 1 | AK-03 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_invalid_key_rejected -q` | ❌ W0 | ⬜ pending |
| 43-01-11 | 01 | 1 | AK-03 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_jwt_still_works -q` | ❌ W0 | ⬜ pending |
| 43-01-12 | 01 | 1 | AK-03 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeyAuth::test_last_used_at_updated -q` | ❌ W0 | ⬜ pending |
| 43-01-13 | 01 | 1 | AK-04 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_list_api_keys -q` | ❌ W0 | ⬜ pending |
| 43-01-14 | 01 | 1 | AK-04 | pytest | `pytest app/tests/test_api_keys.py::TestApiKeysAPI::test_revoke_api_key -q` | ❌ W0 | ⬜ pending |
| 43-02-01 | 02 | 2 | AK-04 | tsc | `cd frontend && npx tsc --noEmit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/app/tests/test_api_keys.py` — 14 test stubs covering AK-01, AK-02, AK-03, AK-04 across TestApiKeyModel, TestApiKeysAPI, TestApiKeyAuth

*All other infrastructure (pytest, fixtures, conftest.py) exists from prior phases.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| One-time key copy modal shows full `sa_` key | AK-02 | Browser clipboard + modal dismiss state | Create key in /settings/api-keys, verify modal appears with full key, dismiss — verify key no longer shown |
| /settings/api-keys page renders key list | AK-04 | React UI — requires browser | Navigate to /settings/api-keys, verify keys show name, prefix, created, last used, expiry |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
