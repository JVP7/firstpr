-- Example: no parameters.
-- Expected: Each language among the tracked repos, with how many open, unassigned issues it has, most first.
SELECT r.primary_language AS language, COUNT(*) AS open_issues
FROM issues i
JOIN repos r ON r.repo_id = i.repo_id AND NOT r.is_archived
WHERE i.state = 'open' AND NOT i.is_assigned AND r.primary_language IS NOT NULL
GROUP BY r.primary_language
ORDER BY open_issues DESC;
