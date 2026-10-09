-- Example: user_id=1, package_id=2.
-- Expected: Remove only the indicated skill for this user.
DELETE FROM user_skills
WHERE user_id = :user_id AND package_id = :package_id
RETURNING user_id, package_id;
