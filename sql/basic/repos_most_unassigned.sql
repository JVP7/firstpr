-- Example: no parameters.
-- Expected: The 20 repos with the most open, unassigned beginner issues, most first, with their totals.
SELECT r.full_name,
       r.primary_language,
       r.stars,
       COUNT(*) AS unassigned_beginner_issues
FROM repos r
JOIN issues i ON i.repo_id = r.repo_id
WHERE i.state = 'open'
  AND NOT i.is_assigned
  AND NOT r.is_archived
  AND EXISTS (
      SELECT 1 FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
      WHERE il.issue_id = i.issue_id
        AND l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M'
  )
GROUP BY r.repo_id, r.full_name, r.primary_language, r.stars
ORDER BY unassigned_beginner_issues DESC, r.stars DESC
LIMIT 20;
