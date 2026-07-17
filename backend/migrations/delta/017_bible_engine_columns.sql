-- Migration 017: formalize the series engine on the bible (story engine,
-- series questions, central premise). These give first-class homes to concepts
-- the episode template already references (engine_fit, series_questions) but the
-- bible previously had no field for -- forcing writers to bury them in free text.
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_central_premise TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_story_engine TEXT DEFAULT '';
ALTER TABLE shows ADD COLUMN IF NOT EXISTS bible_series_questions TEXT DEFAULT '';
