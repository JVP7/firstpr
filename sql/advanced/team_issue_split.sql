-- Example: team_id=1, per_member=3 (the team needs a target repo; clear old assignments first).
-- Expected: Up to per_member open, unassigned issues of the target repo assigned to each member.
-- Every issue in one repo shares the same packages, so the split works on people, not issues:
-- members are ordered by how much of the repo's stack they know (Jaccard of packages), least first,
-- and issues by beginner label first, then newest. NTILE cuts the issue list into one equal,
-- contiguous chunk per member, so the least familiar members get the beginner issues.
WITH team AS (
    SELECT target_repo_id FROM teams WHERE team_id = :team_id AND target_repo_id IS NOT NULL
),
repo_pkgs AS (
    SELECT rd.package_id FROM repo_dependencies rd JOIN team t ON rd.repo_id = t.target_repo_id
),
member_pkgs AS (
    SELECT tm.user_id, ud.package_id
    FROM team_members tm JOIN user_dependencies ud ON ud.user_id = tm.user_id
    WHERE tm.team_id = :team_id
    UNION
    SELECT tm.user_id, us.package_id
    FROM team_members tm JOIN user_skills us ON us.user_id = tm.user_id
    WHERE tm.team_id = :team_id
),
members AS (
    SELECT tm.user_id,
           ROW_NUMBER() OVER (ORDER BY
               COALESCE(COUNT(rp.package_id)::numeric
                   / NULLIF((SELECT COUNT(*) FROM repo_pkgs) + COUNT(mp.package_id) - COUNT(rp.package_id), 0), 0),
               tm.user_id) AS slot
    FROM team_members tm
    LEFT JOIN member_pkgs mp ON mp.user_id = tm.user_id
    LEFT JOIN repo_pkgs rp ON rp.package_id = mp.package_id
    WHERE tm.team_id = :team_id
    GROUP BY tm.user_id
),
ranked_issues AS (
    SELECT i.issue_id,
           ROW_NUMBER() OVER (ORDER BY EXISTS (
               SELECT 1 FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
               WHERE il.issue_id = i.issue_id
                 AND l.name ~* 'good.?first|first.?timer|beginner|newcomer|starter|\measy\M'
           ) DESC, i.created_at DESC, i.issue_id) AS position
    FROM issues i
    JOIN team t ON i.repo_id = t.target_repo_id
    WHERE i.state = 'open' AND NOT i.is_assigned
),
picked AS (
    SELECT issue_id, NTILE((SELECT COUNT(*) FROM members)::int) OVER (ORDER BY position) AS slot
    FROM ranked_issues
    WHERE position <= :per_member * (SELECT COUNT(*) FROM members)
)
INSERT INTO issue_assignments (team_id, issue_id, user_id)
SELECT :team_id, p.issue_id, m.user_id
FROM picked p
JOIN members m ON m.slot = p.slot
RETURNING team_id, issue_id, user_id;
