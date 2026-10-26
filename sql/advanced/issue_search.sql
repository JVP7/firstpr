-- Example: q='docs', languages='{Python,TypeScript}', beginner_only=true, limit=50 (q and languages may be NULL).
-- Expected: Open, unassigned issues whose title or repo name matches q, newest first, with their labels;
-- beginner_only keeps issues with a good-first-issue style label.
SELECT i.issue_id,
       r.full_name,
       r.primary_language,
       r.stars,
       i.number,
       i.title,
       i.created_at,
       COALESCE(ARRAY_AGG(l.name ORDER BY l.name) FILTER (WHERE l.name IS NOT NULL), '{}') AS labels
FROM issues i
JOIN repos r ON r.repo_id = i.repo_id AND NOT r.is_archived
LEFT JOIN issue_labels il ON il.issue_id = i.issue_id
LEFT JOIN labels l ON l.label_id = il.label_id
WHERE i.state = 'open'
  AND NOT i.is_assigned
  AND (CAST(:q AS text) IS NULL
       OR i.title ILIKE '%' || CAST(:q AS text) || '%'
       OR r.full_name ILIKE '%' || CAST(:q AS text) || '%')
  AND (CAST(:languages AS text[]) IS NULL OR r.primary_language = ANY (CAST(:languages AS text[])))
GROUP BY i.issue_id, r.full_name, r.primary_language, r.stars, i.number, i.title, i.created_at
HAVING NOT CAST(:beginner_only AS boolean)
    OR BOOL_OR(l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M')
ORDER BY i.created_at DESC NULLS LAST
LIMIT :limit;
