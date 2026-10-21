-- Example: user_id=1, package_id=2 (the package must already exist).
-- Expected: Add the skill once; repeated calls do nothing because of the composite primary key.
INSERT INTO user_skills (user_id, package_id)
VALUES (:user_id, :package_id)
ON CONFLICT (user_id, package_id) DO NOTHING
RETURNING user_id, package_id;
