-- Server-side state for auth hardening: revoked session tokens and rate-limit hits.
-- Both tables only hold short-lived rows; the API deletes expired ones as it goes.

BEGIN;

-- JWT IDs that were logged out before they expired.
CREATE TABLE revoked_sessions (
    jti        UUID PRIMARY KEY,
    expires_at TIMESTAMPTZ NOT NULL
);

-- One row per counted request (failed login, signup, resync...), keyed by limiter and subject.
CREATE TABLE rate_limit_hits (
    key TEXT        NOT NULL,
    at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_rate_limit_hits_key_at ON rate_limit_hits (key, at);

-- Same policy as 002: RLS on, no policies, so only the backend role can read them.
ALTER TABLE revoked_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_hits  ENABLE ROW LEVEL SECURITY;

COMMIT;
