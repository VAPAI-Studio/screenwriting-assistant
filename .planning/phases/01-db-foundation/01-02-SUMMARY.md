---
phase: 01-db-foundation
plan: 02
subsystem: backend-models
tags: [orm, sqlalchemy, agent-pipeline-map, cascade-relationship]
dependency_graph:
  requires: []
  provides: [AgentPipelineMap-orm-model, Agent-pipeline_maps-relationship]
  affects: [pipeline-composer-service, agent-crud-cascade, pipeline-map-api]
tech_stack:
  added: []
  patterns: [back_populates-bidirectional-relationship, cascade-all-delete-orphan, unique-constraint-tuple]
key_files:
  created: []
  modified:
    - backend/app/models/database.py
decisions:
  - No new imports needed -- all required SQLAlchemy types already imported at top of database.py
  - Used aligned column formatting for readability (matching existing pattern in file)
metrics:
  duration: 45s
  completed: 2026-03-11T16:06:13Z
---

# Phase 01 Plan 02: AgentPipelineMap SQLAlchemy Model Summary

AgentPipelineMap ORM model with 10 columns, unique constraint on (owner_id, agent_id, phase, subsection_key), and bidirectional cascade relationship to Agent via pipeline_maps back-reference.

## What Was Done

### Task 1: Add AgentPipelineMap model and pipeline_maps back-reference to Agent
**Commit:** a44b37e

Two changes to `backend/app/models/database.py`:

1. **Agent.pipeline_maps relationship** -- Added after the existing `books` relationship on the `Agent` class. Uses `back_populates="agent"` for bidirectional navigation and `cascade="all, delete-orphan"` so ORM-level agent deletion propagates to mapping rows.

2. **AgentPipelineMap class** -- Appended at end of file under a "Pipeline Orchestration models" section comment. Defines:
   - `id` (UUID PK)
   - `owner_id` (UUID, indexed, for multi-tenant scoping)
   - `agent_id` (UUID FK to agents.id, indexed)
   - `phase` (String(50), the template phase name)
   - `subsection_key` (String(100), the specific step within a phase)
   - `confidence` (Float, default 0.0, AI-assigned relevance score)
   - `rationale` (Text, nullable, AI explanation of mapping)
   - `pipeline_dirty` (Boolean, default False, signals stale mapping)
   - `created_at` / `updated_at` (DateTime with timezone)
   - `UniqueConstraint("owner_id", "agent_id", "phase", "subsection_key")` prevents duplicate mappings

## Verification Results

- `from app.models.database import AgentPipelineMap` -- PASS (no ImportError)
- `AgentPipelineMap.__tablename__ == "agent_pipeline_maps"` -- PASS
- `"agent_pipeline_maps" in Base.metadata.tables` -- PASS
- All 10 columns present: `{id, owner_id, agent_id, phase, subsection_key, confidence, rationale, pipeline_dirty, created_at, updated_at}` -- PASS
- `Agent.pipeline_maps` exists with `cascade="all, delete-orphan"` -- PASS (CascadeOptions confirmed: delete, delete-orphan, expunge, merge, refresh-expire, save-update)

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | a44b37e | feat(01-02): add AgentPipelineMap model and pipeline_maps back-reference |

## Key Artifacts

| File | What Changed |
|------|-------------|
| backend/app/models/database.py | Added AgentPipelineMap class (25 lines) + pipeline_maps relationship on Agent (4 lines) |

## Self-Check: PASSED

- backend/app/models/database.py: FOUND
- .planning/phases/01-db-foundation/01-02-SUMMARY.md: FOUND
- Commit a44b37e: FOUND
