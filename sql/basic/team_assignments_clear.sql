-- Example: team_id=1.
-- Expected: Remove every issue assignment in the team, before a new split or a new target repo.
DELETE FROM issue_assignments
WHERE team_id = :team_id
RETURNING issue_id;
