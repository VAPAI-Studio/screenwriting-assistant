-- Migration 018: structured regular cast on the bible. A series has a fixed
-- roster the episode template leans on ("what do the regulars do this week");
-- storing it as a list of {name, role, arc} objects (not a free-text blob) lets
-- generation and future tooling reason per-character. JSONB list, default empty.
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_regular_cast JSONB DEFAULT '[]';
