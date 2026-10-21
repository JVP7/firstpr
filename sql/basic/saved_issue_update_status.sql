-- Example: user_id=1, issue_id=10001, status='working'.
-- Expected: Update progress to 'working', 'pr_submitted', or 'merged'.
-- The schema CHECK prevents unsupported statuses such as 'done'.
UPDATE saved_issues
SET status = :status
WHERE user_id = :user_id AND issue_id = :issue_id
  AND :status IN ('working', 'pr_submitted', 'merged')
RETURNING user_id, issue_id, status;
