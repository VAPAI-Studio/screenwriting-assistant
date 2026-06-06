# Phase 47 — Deferred / Out-of-Scope Items

Discovered during execution of 47-01-PLAN.md. NOT fixed (out of scope — not caused
by this plan's changes).

## Pre-existing test failures (unrelated to Phase 47)

Verified pre-existing: reverting `wizards.py` + `template_ai_service.py` to the
pre-phase-47 baseline (commit aa623f3) reproduces the same 4 failures.

- `app/tests/test_session_isolation.py::test_orchestrate_uses_session_factory`
- `app/tests/test_yolo_integration.py::test_yolo_wizard_routes_through_middleware`
- `app/tests/test_yolo_integration.py::test_yolo_wizard_zero_agents_passthrough`
- `app/tests/test_yolo_integration.py::test_yolo_full_run_llm_call_count`

These concern the orchestrator/session-factory and YOLO middleware routing — no
overlap with character-voice injection, the wizards.py injection guard, or
`_generate_scripts`. Should be triaged in a dedicated fix, not here.
