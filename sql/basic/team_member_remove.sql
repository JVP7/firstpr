-- Example: team_id=1, user_id=2.
-- Expected: Remove this user from the team; their issue_assignments in this team cascade.
DELETE FROM team_members
WHERE team_id = :team_id AND user_id = :user_id
RETURNING team_id, user_id;
