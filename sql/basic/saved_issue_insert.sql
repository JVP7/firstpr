-- Example: user_id=1, issue_id=10001 (both records must exist).
-- Expected: Bookmark this issue with status 'interested'; duplicates fail the composite primary key.
INSERT INTO saved_issues (user_id, issue_id, status)
VALUES (:user_id, :issue_id, 'interested')
RETURNING user_id, issue_id, status, saved_at;
