-- Example: user_id=1, email='new@example.com'.
-- Expected: Change only that user's email; duplicate email values fail the UNIQUE constraint.
UPDATE users
SET email = :email
WHERE user_id = :user_id
RETURNING user_id, email;
