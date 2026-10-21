-- Example: name='New Contributors', created_by=1, target_repo_id=NULL.
-- Expected: Create a team and return its team_id. The creator is not automatically a team_member.
INSERT INTO teams (name, created_by, target_repo_id)
VALUES (:name, :created_by, :target_repo_id)
RETURNING team_id, name, created_by, target_repo_id;
