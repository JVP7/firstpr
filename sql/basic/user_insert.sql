-- Example: github_username='test_contributor', email='test@example.com', password_hash='<hashed-password>'.
-- Expected: Create one user and return the generated user_id. Password must already be hashed by the app.
INSERT INTO users (github_username, email, password_hash)
VALUES (:github_username, :email, :password_hash)
RETURNING user_id, github_username, email, created_at;
