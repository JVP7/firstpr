-- Example: team_id=1.
-- Expected: Delete the team; its team_members and issue_assignments cascade.
DELETE FROM teams
WHERE team_id = :team_id
RETURNING team_id;
