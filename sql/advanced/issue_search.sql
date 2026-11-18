-- Example: q='docs', languages='{Python,TypeScript}', beginner_only=true, limit=50 (q and languages may be NULL).
-- Expected: Open, unassigned issues whose title or repo name matches q, newest first, with their labels;
-- beginner_only keeps issues with a good-first-issue style label.
-- The page of issues is picked first and labels fetched only for it; joining labels before the LIMIT
-- made Postgres group every open issue (over 100,000) to return 50.
WITH page AS (
    SELECT i.issue_id, i.repo_id, i.number, i.title, i.created_at
    FROM issues i
    JOIN repos r ON r.repo_id = i.repo_id AND NOT r.is_archived
    WHERE i.state = 'open'
      AND NOT i.is_assigned
      AND (CAST(:q AS text) IS NULL
           OR i.title ILIKE '%' || CAST(:q AS text) || '%'
           OR r.full_name ILIKE '%' || CAST(:q AS text) || '%')
      AND (CAST(:languages AS text[]) IS NULL OR r.primary_language = ANY (CAST(:languages AS text[])))
      AND (NOT CAST(:beginner_only AS boolean) OR EXISTS (
          SELECT 1 FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
          WHERE il.issue_id = i.issue_id
            AND l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M'))
    ORDER BY i.created_at DESC NULLS LAST
    LIMIT :limit
)
SELECT p.issue_id,
       r.full_name,
       r.primary_language,
       r.stars,
       p.number,
       p.title,
       p.created_at,
       ARRAY(SELECT l.name FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
             WHERE il.issue_id = p.issue_id ORDER BY l.name) AS labels,
       rr.score AS responsiveness,
       rr.reply_rate,
       rr.median_reply_hours,
       rr.merge_rate
FROM page p
JOIN repos r ON r.repo_id = p.repo_id
LEFT JOIN repo_responsiveness rr ON rr.repo_id = p.repo_id
ORDER BY p.created_at DESC NULLS LAST;
