-- Expand step: split rate_limit_hits.key ("login_fail:user:20") into atomic columns and give
-- the table a primary key. key stays (nullable) until the API stops writing it; 006 drops it.

BEGIN;

ALTER TABLE rate_limit_hits
    ADD COLUMN id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ADD COLUMN limiter TEXT,
    ADD COLUMN subject TEXT,
    ALTER COLUMN key DROP NOT NULL;

UPDATE rate_limit_hits
SET limiter = split_part(key, ':', 1),
    subject = substr(key, strpos(key, ':') + 1)
WHERE key IS NOT NULL;

CREATE INDEX idx_rate_limit_hits_limiter_subject_at ON rate_limit_hits (limiter, subject, at);

COMMIT;
