-- Migration 014: vapai-studio push linkage for whole SERIES (shows).
-- Purpose: remember which vapai-studio project a show was sent to, so re-sending
--   a series adds scripts under the SAME vapai project/episodes instead of
--   creating a duplicate project (idempotency). A show maps to a vapai project
--   with type="series"; per-episode vapai_episode_id already lives on projects
--   (migration 013).
--   * shows.vapai_project_id — id of the series project created in vapai-studio
-- Nullable: NULL means "never sent yet". Populated on the first successful send.
-- Idempotent + additive only: guarded with IF NOT EXISTS; re-running is a no-op.
ALTER TABLE shows ADD COLUMN IF NOT EXISTS vapai_project_id VARCHAR(64);
