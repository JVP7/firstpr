-- Example: language='Python'.
-- Expected: Open issues in repos whose primary language is that language and that carry a beginner label
-- ("good first issue" and its spellings, the same match the app uses), newest first.
SELECT i.issue_id,
       r.full_name,
       i.number,
       i.title,
       ARRAY_AGG(l.name ORDER BY l.name) AS beginner_labels,
       i.created_at
FROM issues i
JOIN repos r ON r.repo_id = i.repo_id
JOIN issue_labels il ON il.issue_id = i.issue_id
JOIN labels l ON l.label_id = il.label_id
WHERE i.state = 'open'
  AND r.primary_language = :language
  AND l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M'
GROUP BY i.issue_id, r.full_name, i.number, i.title, i.created_at
ORDER BY i.created_at DESC;
