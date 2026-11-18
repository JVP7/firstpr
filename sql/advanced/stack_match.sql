-- Example: user_id=1, languages=NULL (or '{Python,TypeScript}' to keep only those repo languages),
-- beginner_only=false (true keeps issues with a good-first-issue style label), limit=20.
-- Expected: The top <limit> open, unassigned issues ranked by 0.8 * Jaccard(user packages, repo packages)
-- + 0.2 if the repo's language matches one of the user's repos, scaled by 0.75 to 1.25 with the repo's
-- responsiveness (1.0 when unknown); only repos sharing a package qualify.
-- Every issue in a repo scores the same, so at most 3 (the newest) are kept per repo.
WITH user_pkgs AS (
    SELECT package_id FROM user_dependencies WHERE user_id = :user_id
    UNION
    SELECT package_id FROM user_skills WHERE user_id = :user_id
),
user_langs AS (
    SELECT DISTINCT r.primary_language
    FROM user_repos ur
    JOIN repos r ON r.repo_id = ur.repo_id
    WHERE ur.user_id = :user_id AND r.primary_language IS NOT NULL
),
repo_sizes AS (
    SELECT repo_id, COUNT(*) AS repo_pkg_count
    FROM repo_dependencies
    GROUP BY repo_id
),
repo_scores AS (
    SELECT rd.repo_id,
           COUNT(*) AS shared_count,
           ARRAY_AGG(p.name ORDER BY p.name) AS shared_packages,
           COUNT(*)::numeric
               / (rs.repo_pkg_count + (SELECT COUNT(*) FROM user_pkgs) - COUNT(*)) AS jaccard
    FROM repo_dependencies rd
    JOIN user_pkgs up ON up.package_id = rd.package_id
    JOIN packages p ON p.package_id = rd.package_id
    JOIN repo_sizes rs ON rs.repo_id = rd.repo_id
    GROUP BY rd.repo_id, rs.repo_pkg_count
),
ranked AS (
    SELECT i.issue_id,
           r.full_name,
           i.number,
           i.title,
           r.primary_language,
           r.stars,
           ROUND(sc.jaccard, 4) AS jaccard,
           (ul.primary_language IS NOT NULL) AS language_match,
           ROUND((0.8 * sc.jaccard + CASE WHEN ul.primary_language IS NOT NULL THEN 0.2 ELSE 0 END)
                 * (0.75 + 0.5 * COALESCE(rr.score, 0.5)), 4) AS score,
           rr.score AS responsiveness,
           rr.reply_rate,
           rr.median_reply_hours,
           rr.merge_rate,
           sc.shared_packages,
           i.created_at,
           ROW_NUMBER() OVER (PARTITION BY r.repo_id ORDER BY i.created_at DESC) AS repo_rank
    FROM repo_scores sc
    JOIN repos r ON r.repo_id = sc.repo_id AND NOT r.is_archived
    JOIN issues i ON i.repo_id = r.repo_id AND i.state = 'open' AND NOT i.is_assigned
    LEFT JOIN user_langs ul ON ul.primary_language = r.primary_language
    LEFT JOIN repo_responsiveness rr ON rr.repo_id = r.repo_id
    WHERE NOT EXISTS (
        SELECT 1 FROM user_repos ur WHERE ur.user_id = :user_id AND ur.repo_id = r.repo_id
    )
      AND (CAST(:languages AS text[]) IS NULL OR r.primary_language = ANY (CAST(:languages AS text[])))
      AND (NOT CAST(:beginner_only AS boolean) OR EXISTS (
          SELECT 1 FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
          WHERE il.issue_id = i.issue_id
            AND l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M'))
)
SELECT issue_id, full_name, number, title, primary_language, stars, jaccard, language_match, score, shared_packages,
       responsiveness, reply_rate, median_reply_hours, merge_rate,
       ARRAY(SELECT l.name FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
             WHERE il.issue_id = ranked.issue_id ORDER BY l.name) AS labels
FROM ranked
WHERE repo_rank <= 3
ORDER BY score DESC, created_at DESC
LIMIT :limit;
