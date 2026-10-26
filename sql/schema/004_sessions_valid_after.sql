-- Lets a user end every session at once (password change, "sign out everywhere"):
-- tokens issued before this time are rejected. NULL means no reset has happened.

BEGIN;

ALTER TABLE users ADD COLUMN sessions_valid_after TIMESTAMPTZ;

COMMIT;
