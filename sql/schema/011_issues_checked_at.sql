-- When ingest.issue_check last asked GitHub for a repo's changed issues. Kept apart from last_synced_at,
-- which the daily refresh uses to pick up where it stopped.

BEGIN;

ALTER TABLE repos ADD COLUMN issues_checked_at TIMESTAMPTZ;

COMMIT;
