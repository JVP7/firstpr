-- Example: user_id=1 (use a test user who has saved issues and team memberships).
-- Expected: Delete that user; their saved_issues, user_skills and team_members rows cascade.
-- Teams they created are NOT deleted automatically: teams.created_by becomes NULL.
DELETE FROM users
WHERE user_id = :user_id
RETURNING user_id;
