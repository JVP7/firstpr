-- Enable Row Level Security on every table.
-- Supabase exposes the public schema through its Data API; with RLS on and no
-- policies, the anon and authenticated roles see nothing. The backend connects
-- as postgres / service_role, which bypass RLS.

BEGIN;

ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE repos             ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_repos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE packages          ENABLE ROW LEVEL SECURITY;
ALTER TABLE repo_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_skills       ENABLE ROW LEVEL SECURITY;
ALTER TABLE issues            ENABLE ROW LEVEL SECURITY;
ALTER TABLE labels            ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_labels      ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments          ENABLE ROW LEVEL SECURITY;
ALTER TABLE pull_requests     ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_issues      ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams             ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members      ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_assignments ENABLE ROW LEVEL SECURITY;

COMMIT;
