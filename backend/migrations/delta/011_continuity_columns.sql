-- Migration 011: Continuity data model columns (v10.0 Show Type / Episode Continuity)
-- Purpose: schema foundation for per-show continuity_mode and per-episode auto-summary.
--   * shows.continuity_mode      — how a show's episodes relate (D-01: default 'anthology' = zero behavior change on upgrade)
--   * projects.episode_summary       — nullable storage for the AI-generated per-episode summary (generation lands in Phase 69)
--   * projects.episode_summary_stale — staleness flag mirroring breakdown_stale/shotlist_stale (ESUM-02)
-- D-03 (conscious deviation): continuity_mode is a plain VARCHAR with a string default,
--   NOT a Postgres ENUM type. This intentionally departs from the Framework/TemplateType
--   PG-enum convention so new modes can be added later without an ALTER TYPE migration.
-- Idempotent + additive only: all statements guard with IF NOT EXISTS; re-running is a no-op.
ALTER TABLE shows ADD COLUMN IF NOT EXISTS continuity_mode VARCHAR DEFAULT 'anthology';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS episode_summary TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS episode_summary_stale BOOLEAN DEFAULT FALSE;
