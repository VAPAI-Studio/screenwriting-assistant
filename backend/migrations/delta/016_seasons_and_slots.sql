-- backend/migrations/delta/016_seasons_and_slots.sql
-- Phase 4 (capa de temporada): seasons + episode_slots tables, projects.season_id,
-- season-scoped wizard_runs, and backfill (Season 1 + linked slots for every show
-- that already has episodes). All statements idempotent; the migrator's
-- per-migration commit applies the whole file atomically.

CREATE TABLE IF NOT EXISTS seasons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    show_id UUID NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title VARCHAR(255) DEFAULT '',
    arc_summary TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'planning',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT uq_seasons_show_number UNIQUE (show_id, number)
);
CREATE INDEX IF NOT EXISTS ix_seasons_show_id ON seasons(show_id);

CREATE TABLE IF NOT EXISTS episode_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    season_id UUID NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    slot_number INTEGER NOT NULL,
    title VARCHAR(255) DEFAULT '',
    logline TEXT DEFAULT '',
    arc_function TEXT DEFAULT '',
    character_states JSONB DEFAULT '{}',
    cliffhanger TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    project_id UUID UNIQUE REFERENCES projects(id) ON DELETE SET NULL,
    plan_stale BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT uq_episode_slots_season_slot UNIQUE (season_id, slot_number)
);
CREATE INDEX IF NOT EXISTS ix_episode_slots_season_id ON episode_slots(season_id);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS season_id UUID REFERENCES seasons(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_projects_season_id ON projects(season_id);

-- Season-scoped wizard runs (season_map_wizard): project_id becomes nullable,
-- exactly one of project_id / season_id is set (enforced at the app layer).
ALTER TABLE wizard_runs ALTER COLUMN project_id DROP NOT NULL;
ALTER TABLE wizard_runs ADD COLUMN IF NOT EXISTS season_id UUID REFERENCES seasons(id) ON DELETE CASCADE;

-- ============================================================
-- Backfill: every show with episodes gets a Season 1, its episodes get
-- season_id, and each episode gets a linked slot (plan fields empty,
-- plan_stale=false) so the season map is born complete.
-- ============================================================

INSERT INTO seasons (show_id, number, title)
SELECT p.show_id, 1, 'Season 1'
FROM projects p
WHERE p.show_id IS NOT NULL
GROUP BY p.show_id
ON CONFLICT (show_id, number) DO NOTHING;

UPDATE projects p
SET season_id = s.id
FROM seasons s
WHERE p.show_id = s.show_id AND s.number = 1 AND p.season_id IS NULL;

-- One slot per episode, numbered by its episode_number. Episodes with a NULL
-- episode_number get no slot; a duplicate episode_number within a show loses
-- the conflict and stays unslotted (both remain visible in the episode list).
INSERT INTO episode_slots (season_id, slot_number, title, project_id)
SELECT p.season_id, p.episode_number, p.title, p.id
FROM projects p
WHERE p.season_id IS NOT NULL
  AND p.episode_number IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM episode_slots es WHERE es.project_id = p.id)
ON CONFLICT (season_id, slot_number) DO NOTHING;
