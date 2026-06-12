# Phase 56 Context: Job Registry, job_status & First AI-Backed Tool

**Phase:** 56 · **Captured:** 2026-06-12 (auto-generated, YOLO run) · **Milestone:** v8.0

## Domain
Long-running (AI) MCP tools return a job id immediately instead of blocking past
the client timeout; a single generic `job_status` tool polls and returns the
result; the first AI-backed generator proves the canonical async-job + sessionless-AI
pattern under concurrency. Requirements: MCPJ-01, MCPJ-02, MCPJ-03.

## Decisions (see v8.0-AUTONOMOUS-DECISIONS.md D-56-A..C)
- **In-memory job registry with TTL** (not a DB table) — jobs are short-lived,
  polled within a session, needn't survive restart. Single-uvicorn-worker assumed.
- **AI calls are already async** → job runner uses `asyncio.create_task`; brief
  DB reads/writes are NOT held across the AI await (event loop stays responsive).
- **First AI tool = `screenplay_generate_scene`** wrapping the v6.0
  `regenerate_single_scene` path; returns `{job_id}`, preview retrieved via
  `job_status`.
- **Exactly one** generic `job_status` tool (no per-generator status tools).
- Jobs are **owner-scoped** — `job_status` only returns a job to its owner.

## Canonical refs
- .planning/research/v8.0/SUMMARY.md, PITFALLS.md (Pitfalls 5-6)
- .planning/ROADMAP.md Phase 56
- backend/app/services/template_ai_service.py (regenerate_single_scene)
- backend/app/api/endpoints/wizards.py (context-building helpers reused)
