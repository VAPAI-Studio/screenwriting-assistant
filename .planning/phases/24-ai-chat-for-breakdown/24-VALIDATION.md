---
phase: 24
slug: ai-chat-for-breakdown
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-25
---

# Phase 24 — Validation Strategy

> Retroactively created 2026-03-25. Phase completed 2026-03-19.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend API) + TypeScript tsc (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && source venv/bin/activate && pytest app/tests/test_breakdown_chat_api.py -q --tb=short` |
| **Full suite command** | `cd backend && source venv/bin/activate && pytest app/tests/ -q --tb=short && cd ../frontend && npx tsc --noEmit` |
| **Estimated runtime** | ~1s |

---

## Per-Task Verification Map

| Task ID | Requirement | Test Type | Automated Command | Status |
|---------|-------------|-----------|-------------------|--------|
| 24-01-01 | BreakdownChat.tsx compiles without errors | tsc | `cd frontend && npx tsc --noEmit` | ✅ verified |
| 24-01-02 | POST /breakdown-chat/stream requires auth | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_stream_requires_auth -q` | ✅ verified |
| 24-01-03 | POST /breakdown-chat/stream requires valid project | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_stream_requires_valid_project -q` | ✅ verified |
| 24-01-04 | SSE stream includes current shots as context | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_stream_includes_shots_context -q` | ✅ verified |
| 24-01-05 | SSE stream includes breakdown elements as context | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_stream_includes_elements_context -q` | ✅ verified |
| 24-01-06 | SSE stream returns properly formatted SSE chunks | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_stream_returns_sse_chunks -q` | ✅ verified |
| 24-02-01 | AI response can create a new shot via action JSON | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_shot_create_action -q` | ✅ verified |
| 24-02-02 | AI response can modify an existing shot via action JSON | pytest | `pytest app/tests/test_breakdown_chat_api.py::TestBreakdownChatAPI::test_shot_modify_action -q` | ✅ verified |

---

## Manual-Only Verifications

| Behavior | Why Manual |
|----------|------------|
| Chat messages stream token-by-token in BreakdownChat UI | SSE streaming in browser |
| "Create shot" action from AI response adds shot to ShotlistPanel | React Query cache invalidation across panels |
| Chat context includes visible scene in script view | React state coordination |

---

## Key Files

| File | What it delivers |
|------|-----------------|
| `frontend/src/components/Breakdown/BreakdownChat.tsx` | AI chat panel with SSE streaming and shot action handling |
| `backend/app/tests/test_breakdown_chat_api.py` | 7 tests: auth, context injection, SSE format, shot create/modify actions |
| `backend/app/api/endpoints/breakdown_chat.py` | SSE streaming endpoint with shots + elements context |

---

## Validation Sign-Off

- [x] All 8 tasks have automated verify
- [x] All 7 backend tests confirmed passing
- [x] TypeScript compiles clean
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactive
