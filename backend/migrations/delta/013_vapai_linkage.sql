-- Migration 013: vapai-studio push linkage columns.
-- Purpose: remember which vapai-studio project/episode a screenplay was sent to,
--   so repeated "Send to vapai-studio" clicks add a new script under the SAME
--   vapai project/episode instead of creating duplicate projects (idempotency).
--   * projects.vapai_project_id — id of the project created in vapai-studio
--   * projects.vapai_episode_id — id of the episode created in vapai-studio
-- Both nullable: NULL means "never sent yet". Populated on the first successful send.
-- Idempotent + additive only: all statements guard with IF NOT EXISTS; re-running is a no-op.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS vapai_project_id VARCHAR(64);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS vapai_episode_id VARCHAR(64);
