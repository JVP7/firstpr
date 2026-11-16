-- How responsive each repo's maintainers are, from the last 90 days of comments and pull requests.
-- Materialized because it scans every comment and PR (about a second); ingest/seed_load.py refreshes it.
-- score is 0 to 1: the repo's average percentile across reply rate and merge rate among tracked repos.
-- Both rates are smoothed toward the all-repo rate as if from 10 extra samples, so a repo with 3 of 3 PRs
-- merged doesn't outrank one with 80 of 100. NULL when the repo has no recent issues or closed PRs.

BEGIN;

CREATE MATERIALIZED VIEW repo_responsiveness AS
WITH maintainer_comments AS (
    SELECT i.repo_id, c.issue_id, c.author_login, c.created_at
    FROM comments c
    JOIN issues i ON i.issue_id = c.issue_id
    WHERE c.author_association IN ('OWNER', 'MEMBER', 'COLLABORATOR')
),
windows AS (
    -- Ingest keeps only a repo's newest 500 comments, so only issues opened after the oldest stored
    -- comment can be judged; issues younger than 7 days haven't had a fair chance at a reply yet.
    SELECT r.repo_id,
           GREATEST(r.last_synced_at - INTERVAL '90 days',
                    (SELECT MIN(c.created_at) FROM comments c JOIN issues i ON i.issue_id = c.issue_id
                     WHERE i.repo_id = r.repo_id AND c.created_at > r.last_synced_at - INTERVAL '90 days')) AS starts_at,
           r.last_synced_at - INTERVAL '7 days' AS ends_at
    FROM repos r
    WHERE r.last_synced_at IS NOT NULL
),
issue_waits AS (
    SELECT w.repo_id,
           (SELECT MIN(m.created_at) FROM maintainer_comments m WHERE m.issue_id = i.issue_id) - i.created_at AS wait
    FROM windows w
    JOIN issues i ON i.repo_id = w.repo_id AND i.created_at BETWEEN w.starts_at AND w.ends_at
),
issue_stats AS (
    SELECT repo_id,
           COUNT(*) AS recent_issues,
           COUNT(wait) AS replied_issues,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM wait) / 3600) AS median_reply_hours
    FROM issue_waits
    GROUP BY repo_id
),
pr_stats AS (
    -- Outside contributions only: bots and people who comment as maintainers are skipped.
    SELECT p.repo_id, COUNT(*) AS closed_prs, COUNT(p.merged_at) AS merged_prs
    FROM pull_requests p
    WHERE p.state = 'closed'
      AND p.author_login NOT LIKE '%[bot]'
      AND NOT EXISTS (SELECT 1 FROM maintainer_comments m
                      WHERE m.repo_id = p.repo_id AND m.author_login = p.author_login)
    GROUP BY p.repo_id
),
rates AS (
    SELECT w.repo_id,
           COALESCE(i.recent_issues, 0) AS recent_issues,
           COALESCE(i.replied_issues, 0) AS replied_issues,
           i.replied_issues::numeric / NULLIF(i.recent_issues, 0) AS reply_rate,
           ROUND(i.median_reply_hours::numeric, 1) AS median_reply_hours,
           COALESCE(p.closed_prs, 0) AS closed_prs,
           COALESCE(p.merged_prs, 0) AS merged_prs,
           p.merged_prs::numeric / NULLIF(p.closed_prs, 0) AS merge_rate
    FROM windows w
    LEFT JOIN issue_stats i ON i.repo_id = w.repo_id
    LEFT JOIN pr_stats p ON p.repo_id = w.repo_id
),
overall AS (
    SELECT SUM(replied_issues)::numeric / NULLIF(SUM(recent_issues), 0) AS reply_rate,
           SUM(merged_prs)::numeric / NULLIF(SUM(closed_prs), 0) AS merge_rate
    FROM rates
),
smoothed AS (
    SELECT r.repo_id,
           (r.replied_issues + 10 * o.reply_rate) / (r.recent_issues + 10) AS reply_smooth,
           (r.merged_prs + 10 * o.merge_rate) / (r.closed_prs + 10) AS merge_smooth,
           r.recent_issues, r.closed_prs
    FROM rates r CROSS JOIN overall o
),
ranked AS (
    -- PERCENT_RANK over only the repos that have each kind of sample, so missing data isn't the bottom.
    SELECT repo_id, PERCENT_RANK() OVER (ORDER BY reply_smooth) AS reply_pct, NULL::float8 AS merge_pct
    FROM smoothed WHERE recent_issues > 0
    UNION ALL
    SELECT repo_id, NULL, PERCENT_RANK() OVER (ORDER BY merge_smooth)
    FROM smoothed WHERE closed_prs > 0
),
scores AS (
    SELECT repo_id, (COALESCE(MAX(reply_pct), 0) + COALESCE(MAX(merge_pct), 0))
                    / (COUNT(reply_pct) + COUNT(merge_pct)) AS score
    FROM ranked
    GROUP BY repo_id
)
SELECT r.repo_id, r.recent_issues, r.replied_issues, ROUND(r.reply_rate, 3) AS reply_rate, r.median_reply_hours,
       r.closed_prs, r.merged_prs, ROUND(r.merge_rate, 3) AS merge_rate, ROUND(s.score::numeric, 3) AS score
FROM rates r
LEFT JOIN scores s ON s.repo_id = r.repo_id;

CREATE UNIQUE INDEX idx_repo_responsiveness_repo ON repo_responsiveness (repo_id);

-- Materialized views can't use row-level security; keep it out of Supabase's Data API like the tables.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON repo_responsiveness FROM anon, authenticated;
    END IF;
END $$;

COMMIT;
