# Phase 57 Context: Management Tools

**Phase:** 57 · **Captured:** 2026-06-12 (auto, YOLO) · **Milestone:** v8.0

## Domain
Fast, synchronous, owner-scoped MCP tools over the existing project/show models —
the agent's session entry point. Requirements: MCPP-01/02/03 (+ show/episode read
differentiators). No delete tools (locked).

## Decisions (see v8.0-AUTONOMOUS-DECISIONS.md D-57-A)
- `project_create` uses the working `template` column + records framework in
  `template_config` JSON, because the legacy `framework` PG enum is broken
  app-wide (uppercase names vs lowercase PG labels). Flagged for user cleanup.
- Tools coerce enum-or-str column reads (`_enum_value`) so they work on both PG
  (real enum) and the sqlite test DB (enums patched to String).
- Added a production-safe `set_session_factory_override` test seam to
  `mcp_session` so MCP tools can be pointed at the test DB deterministically.

## Tools
project_list, project_get, project_create (MCPP), show_list, show_read_bible,
episode_list (differentiators). All owner-scoped.
