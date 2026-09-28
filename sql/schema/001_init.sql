-- FirstPR initial schema (PostgreSQL 17 / Supabase)
-- Matches beginner-friendly GitHub issues to users based on their repos' dependencies.

BEGIN;

-- App accounts; one per GitHub user.
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    github_username TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- GitHub repositories, keyed by GitHub's repo ID.
CREATE TABLE repos (
    repo_id          BIGINT PRIMARY KEY,
    full_name        TEXT NOT NULL UNIQUE,
    primary_language TEXT,
    stars            INT CHECK (stars >= 0),
    is_archived      BOOLEAN NOT NULL DEFAULT false,
    last_synced_at   TIMESTAMPTZ
);

-- Which repos belong to which users.
CREATE TABLE user_repos (
    user_id INT    NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    repo_id BIGINT NOT NULL REFERENCES repos (repo_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, repo_id)
);

-- Dependency packages from package registries.
CREATE TABLE packages (
    package_id SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    ecosystem  TEXT NOT NULL CHECK (ecosystem IN ('pypi', 'npm')),
    UNIQUE (name, ecosystem)
);

-- Packages each repo depends on.
CREATE TABLE repo_dependencies (
    repo_id    BIGINT NOT NULL REFERENCES repos (repo_id) ON DELETE CASCADE,
    package_id INT    NOT NULL REFERENCES packages (package_id),
    PRIMARY KEY (repo_id, package_id)
);

-- Packages a user has explicitly declared as skills.
CREATE TABLE user_skills (
    user_id    INT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    package_id INT NOT NULL REFERENCES packages (package_id),
    PRIMARY KEY (user_id, package_id)
);

-- GitHub issues, keyed by GitHub's issue ID.
CREATE TABLE issues (
    issue_id    BIGINT PRIMARY KEY,
    repo_id     BIGINT NOT NULL REFERENCES repos (repo_id) ON DELETE CASCADE,
    number      INT NOT NULL,
    title       TEXT NOT NULL,
    state       TEXT NOT NULL CHECK (state IN ('open', 'closed')),
    created_at  TIMESTAMPTZ,
    closed_at   TIMESTAMPTZ CHECK (closed_at IS NULL OR closed_at >= created_at),
    is_assigned BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (repo_id, number)
);

-- Per-repo issue labels, keyed by GitHub's label ID.
CREATE TABLE labels (
    label_id BIGINT PRIMARY KEY,
    repo_id  BIGINT NOT NULL REFERENCES repos (repo_id) ON DELETE CASCADE,
    name     TEXT NOT NULL,
    UNIQUE (repo_id, name)
);

-- Labels applied to each issue.
CREATE TABLE issue_labels (
    issue_id BIGINT NOT NULL REFERENCES issues (issue_id) ON DELETE CASCADE,
    label_id BIGINT NOT NULL REFERENCES labels (label_id) ON DELETE CASCADE,
    PRIMARY KEY (issue_id, label_id)
);

-- Issue comments, keyed by GitHub's comment ID.
CREATE TABLE comments (
    comment_id         BIGINT PRIMARY KEY,
    issue_id           BIGINT NOT NULL REFERENCES issues (issue_id) ON DELETE CASCADE,
    author_login       TEXT,
    author_association TEXT CHECK (author_association IN (
        'OWNER', 'MEMBER', 'COLLABORATOR', 'CONTRIBUTOR',
        'FIRST_TIME_CONTRIBUTOR', 'FIRST_TIMER', 'MANNEQUIN', 'NONE'
    )),
    created_at         TIMESTAMPTZ NOT NULL
);

-- Pull requests, keyed by GitHub's PR ID.
CREATE TABLE pull_requests (
    pr_id        BIGINT PRIMARY KEY,
    repo_id      BIGINT NOT NULL REFERENCES repos (repo_id) ON DELETE CASCADE,
    author_login TEXT,
    created_at   TIMESTAMPTZ NOT NULL,
    merged_at    TIMESTAMPTZ,
    state        TEXT NOT NULL CHECK (state IN ('open', 'closed'))
);

-- Issues a user has bookmarked, with their progress.
CREATE TABLE saved_issues (
    user_id  INT    NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    issue_id BIGINT NOT NULL REFERENCES issues (issue_id) ON DELETE CASCADE,
    status   TEXT NOT NULL DEFAULT 'interested'
             CHECK (status IN ('interested', 'working', 'pr_submitted', 'merged')),
    saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, issue_id)
);

-- Groups of users working together, optionally on one target repo.
CREATE TABLE teams (
    team_id        SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    created_by     INT REFERENCES users (user_id) ON DELETE SET NULL,
    target_repo_id BIGINT REFERENCES repos (repo_id) ON DELETE SET NULL
);

-- Team membership and role.
CREATE TABLE team_members (
    team_id INT NOT NULL REFERENCES teams (team_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users (user_id) ON DELETE CASCADE,
    role    TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'member')),
    PRIMARY KEY (team_id, user_id)
);

-- Which team member is working on which issue; one assignee per issue per team.
CREATE TABLE issue_assignments (
    team_id  INT    NOT NULL REFERENCES teams (team_id) ON DELETE CASCADE,
    issue_id BIGINT NOT NULL REFERENCES issues (issue_id) ON DELETE CASCADE,
    user_id  INT    NOT NULL,
    PRIMARY KEY (team_id, issue_id),
    FOREIGN KEY (team_id, user_id)
        REFERENCES team_members (team_id, user_id) ON DELETE CASCADE
);

-- Packages a user depends on through any of their repos.
CREATE VIEW user_dependencies WITH (security_invoker = true) AS
SELECT DISTINCT ur.user_id, rd.package_id
FROM user_repos ur
JOIN repo_dependencies rd ON rd.repo_id = ur.repo_id;

CREATE INDEX idx_issues_repo_state        ON issues (repo_id, state);
CREATE INDEX idx_comments_issue_created   ON comments (issue_id, created_at);
CREATE INDEX idx_issue_labels_label       ON issue_labels (label_id);
CREATE INDEX idx_pull_requests_repo_created ON pull_requests (repo_id, created_at);

COMMIT;
