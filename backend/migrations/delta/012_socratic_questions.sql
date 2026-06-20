-- Migration 012: Socratic Questions (Hard Questions section)
-- Purpose: per-project store of AI-generated "hard questions" grounded in the user's
--   loaded books (RAG) + the project's script. The author's answers are persisted and
--   later fed back into the project context for generation/review.
--   * question        — the hard question shown to the author
--   * rationale       — why it was asked / what it probes (mentor's reasoning)
--   * source_concepts — JSON list of book concepts/titles the question drew on
--   * answer          — the author's answer (NULL until answered)
--   * answered_at     — when it was answered (drives the 3h lazy-regen cooldown)
-- Idempotent + additive only: guarded with IF NOT EXISTS; re-running is a no-op.
CREATE TABLE IF NOT EXISTS socratic_questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question        TEXT NOT NULL,
    rationale       TEXT,
    source_concepts JSONB DEFAULT '[]'::jsonb,
    answer          TEXT,
    answered_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_socratic_project ON socratic_questions (project_id);

-- Partial index to quickly find the single pending (unanswered) question per project.
CREATE INDEX IF NOT EXISTS idx_socratic_pending ON socratic_questions (project_id) WHERE answer IS NULL;
