-- backend/migrations/delta/015_template_type_values.sql
-- Phase 3 (templates por formato): new template ids for the projects.template
-- enum. ADD VALUE IF NOT EXISTS is idempotent; inside a transaction the new
-- values are usable only after commit, which the migrator's per-migration
-- commit guarantees before any request can reference them.
ALTER TYPE template_type ADD VALUE IF NOT EXISTS 'sketch';
ALTER TYPE template_type ADD VALUE IF NOT EXISTS 'episode';
