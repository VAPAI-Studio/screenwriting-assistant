# Deferred Items — Phase 16

## Pre-existing Test Failure (Out of Scope)

**Test:** `app/tests/test_session_isolation.py::test_orchestrate_uses_session_factory`

**Status:** Failing before Phase 16 work, unrelated to scene_wizard/staleness changes.

**Error:** `ValueError: Template '<MagicMock name='mock.project.template.value' ...>' not found` in `app/templates/registry.py:35`

**Root cause:** Test uses `MagicMock` for `project.template.value` but `template_ai_service._build_project_context` dereferences the mock to an actual registry lookup. The mock setup needs to provide a valid template ID string. This is a pre-existing test isolation issue present in the working tree's modified files (backend/app/services/template_ai_service.py is modified per git status).

**Deferred to:** Future maintenance or Phase 17 cleanup.
