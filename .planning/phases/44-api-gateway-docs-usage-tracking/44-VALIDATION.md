---
phase: 44
slug: api-gateway-docs-usage-tracking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini (existing) |
| **Quick run command** | `cd backend && python -m pytest app/tests/test_api_keys.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest app/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest app/tests/test_api_keys.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest app/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | AK-05 | unit | `pytest app/tests/test_api_gateway.py::TestSwaggerDocs -x -q` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 1 | AK-05 | unit | `pytest app/tests/test_api_keys.py -x -q` | ✅ | ⬜ pending |
| 44-01-03 | 01 | 1 | AK-06 | unit | `pytest app/tests/test_api_keys.py -x -q` | ✅ | ⬜ pending |
| 44-01-04 | 01 | 1 | AK-06 | unit | `pytest app/tests/test_api_gateway.py::TestPerKeyRateLimit -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `app/tests/test_api_gateway.py` — stubs for AK-05 (TestSwaggerDocs: OpenAPI schema validation) and AK-06 (TestPerKeyRateLimit: per-key rate limiting with 429 assertion via mini-app pattern)

*Existing test infrastructure (pytest, conftest, test DB) covers all other needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Swagger UI renders correctly | AK-05 | Browser rendering | Navigate to /docs, verify all endpoints listed with correct schemas |
| Frontend request_count updates | AK-06 | React Query polling | Open /settings/api-keys, make API call, verify count increments within 30s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
