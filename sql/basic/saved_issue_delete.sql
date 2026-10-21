-- Example: user_id=1, issue_id=10001.
-- Expected: Remove this user's bookmark without deleting the GitHub issue.
DELETE FROM saved_issues
WHERE user_id = :user_id AND issue_id = :issue_id
RETURNING user_id, issue_id;
