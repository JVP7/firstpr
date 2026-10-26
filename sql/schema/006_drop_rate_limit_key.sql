-- Contract step (run once the API writes limiter/subject): finish the split from 005.

BEGIN;

-- Rows written by the old code between 005 and the deploy; they expire within the hour anyway.
DELETE FROM rate_limit_hits WHERE limiter IS NULL OR subject IS NULL;

ALTER TABLE rate_limit_hits
    ALTER COLUMN limiter SET NOT NULL,
    ALTER COLUMN subject SET NOT NULL,
    DROP COLUMN key;  -- also drops idx_rate_limit_hits_key_at

COMMIT;
