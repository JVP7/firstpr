-- Repos loaded on demand for a user's packages, outside the seed list. The daily refresh syncs these
-- too; the requester is kept for reference and cleared if they delete their account.

BEGIN;

CREATE TABLE requested_repos (
    repo_id      BIGINT PRIMARY KEY REFERENCES repos ON DELETE CASCADE,
    requested_by INT REFERENCES users ON DELETE SET NULL,
    topic        TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE requested_repos ENABLE ROW LEVEL SECURITY;

COMMIT;
