-- Example: team_id=1, target_repo_id=5 (or NULL to clear it; the repo must be tracked).
-- Expected: Point the team at the project it will contribute to; returns the team.
UPDATE teams
SET target_repo_id = :target_repo_id
WHERE team_id = :team_id
RETURNING team_id, name, created_by, target_repo_id;
