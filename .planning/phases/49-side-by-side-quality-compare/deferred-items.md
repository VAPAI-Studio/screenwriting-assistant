# Deferred Items — Phase 49

## Pre-existing test failures (out of scope, NOT caused by 49-01)

The following suites fail under the full-suite run AND in isolation, and were
confirmed failing at the plan baseline commit `f38a254` (before any 49-01 work):

- `app/tests/test_session_isolation.py::test_orchestrate_uses_session_factory`
- `app/tests/test_yolo_integration.py::test_yolo_wizard_routes_through_middleware`
- `app/tests/test_yolo_integration.py::test_yolo_wizard_zero_agents_passthrough`
- `app/tests/test_yolo_integration.py::test_yolo_full_run_llm_call_count`

These are the documented order-sensitive yolo/session-isolation suites
(`.planning/v6.0-PREEXISTING-TEST-CONCERN.md`). They are explicitly out of scope
for this phase. The 49-01 target suites (`test_scene_compare.py`) and the 27-test
regression trio (continuity/voice/craft/wizard) all pass.
