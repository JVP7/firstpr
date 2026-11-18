-- Example: beginner_only=false (true counts only issues with a good-first-issue style label).
-- Expected: Each language among the tracked repos, with how many open, unassigned issues it has, most first.
-- Every language stays listed, with 0 when beginner_only leaves it none, so the filter's options don't jump.
WITH beginner AS (
    -- Matching the regex once per label is far cheaper than once per issue.
    SELECT DISTINCT il.issue_id
    FROM labels l
    JOIN issue_labels il ON il.label_id = l.label_id
    WHERE l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M'
)
SELECT r.primary_language AS language,
       COUNT(*) FILTER (WHERE NOT CAST(:beginner_only AS boolean) OR b.issue_id IS NOT NULL) AS open_issues
FROM issues i
JOIN repos r ON r.repo_id = i.repo_id AND NOT r.is_archived
LEFT JOIN beginner b ON CAST(:beginner_only AS boolean) AND b.issue_id = i.issue_id
WHERE i.state = 'open' AND NOT i.is_assigned AND r.primary_language IS NOT NULL
GROUP BY r.primary_language
ORDER BY open_issues DESC, language;
