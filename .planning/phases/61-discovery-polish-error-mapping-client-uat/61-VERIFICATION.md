---
phase: 61-discovery-polish-error-mapping-client-uat
verified: 2026-06-12
status: human_needed
score: MCPD-01/02 verified by API; full GUI client-matrix UAT deferred to user
human_verification:
  - test: "Connect Claude Code / Claude Desktop / Hermes; list all 17 tools; run a read + a long-running (job-id) tool end-to-end"
    expected: "tools introspect with descriptions; a generation tool returns a job_id and job_status polls it to done"
    why_human: "Requires GUI clients + a human; cannot be driven autonomously. See CLIENT-SETUP.md."
---

# Phase 61 Verification: Discovery Polish, Error Mapping & Client UAT

| Req | Status | Evidence |
|-----|--------|----------|
| MCPD-01 (tool discovery: names/descriptions/schemas) | ✓ VERIFIED (API) | all 17 tools have substantive descriptions + input schemas; long-running tools state "LONG-RUNNING: returns a job_id" in their description |
| MCPD-02 (clean error mapping) | ✓ VERIFIED (API) | a tool error surfaces through the MCP transport as isError=True with a clean message ("404: Project not found"), not an opaque 500/stack trace |

## Final tool surface (17 tools)
ping, whoami, job_status,
project_list/get/create, show_list, show_read_bible, episode_list,
screenplay_read/write/generate_scene,
breakdown_extract/read,
shotlist_read, shot_create, shotlist_generate.

All owner-scoped; long-running AI tools (generate_scene, breakdown_extract,
shotlist_generate) return job-ids polled via job_status; no delete tools (locked).

## Deferred to USER (GUI client-matrix UAT)
- [ ] Claude Code / Claude Desktop / Hermes: connect with a static sa_ bearer,
  list tools, run a read + a long-running tool end-to-end. See CLIENT-SETUP.md.

Status human_needed — code/mechanism complete and API-verified; only the GUI
client UAT remains (deferred per the autonomous run's standing decision).
