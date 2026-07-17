-- Migration 019: vertical_drama template id for the projects.template enum.
-- ADD VALUE IF NOT EXISTS is idempotent; the migrator commits per-migration so
-- the new value is usable before any request references it.
ALTER TYPE template_type ADD VALUE IF NOT EXISTS 'vertical_drama';
