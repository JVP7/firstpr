-- Example: team_id=1.
-- Expected: The team's issue assignments with each issue's repo, title and labels, grouped by member.
SELECT u.user_id,
       u.github_username,
       i.issue_id,
       r.full_name,
       i.number,
       i.title,
       ARRAY(SELECT l.name FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
             WHERE il.issue_id = i.issue_id ORDER BY l.name) AS labels
FROM issue_assignments a
JOIN users u ON u.user_id = a.user_id
JOIN issues i ON i.issue_id = a.issue_id
JOIN repos r ON r.repo_id = i.repo_id
WHERE a.team_id = :team_id
ORDER BY u.github_username, i.created_at DESC;
