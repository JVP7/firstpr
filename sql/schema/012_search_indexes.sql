-- Search reads open, unassigned issues newest first and stops after a page, so index exactly those.
-- Matches looks up which repos use each of a user's packages; the primary key leads with repo_id,
-- so that lookup scanned the whole table.

BEGIN;

CREATE INDEX idx_issues_open_newest ON issues (created_at DESC NULLS LAST) WHERE state = 'open' AND NOT is_assigned;
CREATE INDEX idx_repo_dependencies_package ON repo_dependencies (package_id);

COMMIT;
