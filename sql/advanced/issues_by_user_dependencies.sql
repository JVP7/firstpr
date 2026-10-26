-- Example: user_id=1 (the user must have repos with parsed dependencies).
-- Expected: Open, unassigned issues in repos that share at least one package with the user's repos,
-- with the shared packages listed; repos the user owns are excluded.
SELECT i.issue_id,
       r.full_name,
       i.number,
       i.title,
       i.created_at,
       COUNT(*) AS shared_package_count,
       ARRAY_AGG(p.name ORDER BY p.name) AS shared_packages
FROM users u
JOIN user_dependencies ud ON ud.user_id = u.user_id
JOIN repo_dependencies rd ON rd.package_id = ud.package_id
JOIN packages p ON p.package_id = rd.package_id
JOIN repos r ON r.repo_id = rd.repo_id AND NOT r.is_archived
JOIN issues i ON i.repo_id = r.repo_id AND i.state = 'open' AND NOT i.is_assigned
WHERE u.user_id = :user_id
  AND NOT EXISTS (
      SELECT 1 FROM user_repos ur
      WHERE ur.user_id = u.user_id AND ur.repo_id = r.repo_id
  )
GROUP BY i.issue_id, r.full_name, i.number, i.title, i.created_at
ORDER BY shared_package_count DESC, i.created_at DESC;
