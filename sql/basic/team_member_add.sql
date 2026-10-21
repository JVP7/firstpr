-- Example: team_id=1, user_id=2, role='member'.
-- Expected: Add this user to an existing team as 'owner' or 'member'.
INSERT INTO team_members (team_id, user_id, role)
VALUES (:team_id, :user_id, :role)
ON CONFLICT (team_id, user_id) DO NOTHING
RETURNING team_id, user_id, role;
