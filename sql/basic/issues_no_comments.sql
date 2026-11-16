-- Example: no parameters.
-- Expected: Open issues opened in the 30 days before their repo was last synced that have no comments, newest first.
-- Measured from the sync, not now(): comments are only as fresh as the last sync, so an issue opened
-- after it would look comment-free just because we never fetched its comments.
-- In very busy repos this can over-count: ingest keeps only each repo's newest 500 comments.
SELECT i.issue_id,
       r.full_name,
       i.number,
       i.title,
       i.created_at
FROM issues i
JOIN repos r ON r.repo_id = i.repo_id
LEFT JOIN comments c ON c.issue_id = i.issue_id
WHERE i.state = 'open'
  AND i.created_at >= r.last_synced_at - INTERVAL '30 days'
  AND c.comment_id IS NULL
ORDER BY i.created_at DESC;
