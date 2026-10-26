-- Example: team_id=1.
-- Expected: One row per status with every issue the team's members have saved, newest first;
-- statuses nobody has used are omitted.
SELECT si.status,
       COUNT(*) AS issue_count,
       JSON_AGG(JSON_BUILD_OBJECT(
           'user_id',          u.user_id,
           'github_username',  u.github_username,
           'issue_id',         i.issue_id,
           'repo',             r.full_name,
           'number',           i.number,
           'title',            i.title,
           'saved_at',         si.saved_at
       ) ORDER BY si.saved_at DESC) AS issues
FROM team_members tm
JOIN users u ON u.user_id = tm.user_id
JOIN saved_issues si ON si.user_id = tm.user_id
JOIN issues i ON i.issue_id = si.issue_id
JOIN repos r ON r.repo_id = i.repo_id
WHERE tm.team_id = :team_id
GROUP BY si.status
ORDER BY ARRAY_POSITION(ARRAY['interested', 'working', 'pr_submitted', 'merged'], si.status);
