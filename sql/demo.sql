-- Stage 4 demo: runs the project's own SQL files against the real database, step by step.
-- Run from the repo root:
--   psql "$DATABASE_URL" -v pause=1 -f sql/demo.sql     (press Enter between steps)
--   psql "$DATABASE_URL" -f sql/demo.sql                (no pauses)
-- Everything it creates is deleted at the end; it leaves the database as it found it.

\set ON_ERROR_STOP on
\set QUIET on
\pset pager off
\pset format aligned
\pset null '-'
\pset footer on

-- Leftovers from an interrupted run. GitHub usernames can't contain "_", so this never matches a real user.
DELETE FROM teams WHERE name = 'Starpull demo team';
DELETE FROM users WHERE github_username = 'demo_contributor';

\set github_username '\'demo_contributor\''
\set email '\'demo_contributor@starpull.dev\''
\set password_hash '\'demo-not-a-real-bcrypt-hash\''

\echo
\echo '================ 1. REAL DATA: loaded from the GitHub API ================'
SELECT (SELECT count(*) FROM repos) AS repos,
       (SELECT count(*) FROM issues WHERE state = 'open') AS open_issues,
       (SELECT count(*) FROM packages) AS packages,
       (SELECT count(*) FROM repo_dependencies) AS repo_dependencies,
       (SELECT count(*) FROM pull_requests) AS pull_requests;
SELECT full_name, primary_language, stars FROM repos ORDER BY stars DESC NULLS LAST LIMIT 5;
\if :{?pause} \prompt 'Enter for INSERT > ' _ \endif

\echo
\echo '================ 2. INSERT ================'
\echo '-- sql/basic/user_insert.sql'
\! sed '/^--/d' sql/basic/user_insert.sql
\ir basic/user_insert.sql
SELECT user_id FROM users WHERE github_username = :github_username \gset

SELECT package_id FROM packages WHERE name = 'flask' AND ecosystem = 'pypi' \gset
\echo '-- sql/basic/skill_add.sql   (user knows flask)'
\! sed '/^--/d' sql/basic/skill_add.sql
\ir basic/skill_add.sql
\if :{?pause} \prompt 'Enter for SEARCH > ' _ \endif

\echo
\echo '================ 3. SEARCH: open beginner issues mentioning "docs" ================'
\set q '\'docs\''
\set languages NULL
\set beginner_only true
\set limit 5
\echo '-- sql/advanced/issue_search.sql   (q=docs, beginner labels only, limit 5)'
\x on
\ir advanced/issue_search.sql
\x off
\if :{?pause} \prompt 'Enter for ADVANCED > ' _ \endif

\echo
\echo '================ 4. ADVANCED: stack matching (Jaccard similarity + language) ================'
\echo '-- sql/advanced/stack_match.sql   score = 0.8 * Jaccard(user packages, repo packages) + 0.2 * same language'
\echo '--   top 5 here (the app shows 20, at most 3 per project)'
\x on
\ir advanced/stack_match.sql
\x off

-- Save the newest open issue in a flask project, then track it.
SELECT i.issue_id FROM issues i
JOIN repo_dependencies rd ON rd.repo_id = i.repo_id
WHERE rd.package_id = :package_id AND i.state = 'open' AND NOT i.is_assigned
ORDER BY i.created_at DESC LIMIT 1 \gset
\echo '-- sql/basic/saved_issue_insert.sql   (bookmark that issue)'
\ir basic/saved_issue_insert.sql

\set name '\'Starpull demo team\''
\set created_by :user_id
\set target_repo_id NULL
\echo '-- sql/basic/team_insert.sql + team_member_add.sql'
\ir basic/team_insert.sql
SELECT team_id FROM teams WHERE name = 'Starpull demo team' \gset
\set role '\'owner\''
\ir basic/team_member_add.sql
\if :{?pause} \prompt 'Enter for UPDATE > ' _ \endif

\echo
\echo '================ 5. UPDATE ================'
\set status '\'working\''
\echo '-- sql/basic/saved_issue_update_status.sql   (interested -> working)'
\! sed '/^--/d' sql/basic/saved_issue_update_status.sql
\ir basic/saved_issue_update_status.sql
\set email '\'new_email@starpull.dev\''
\echo '-- sql/basic/user_update_email.sql'
\ir basic/user_update_email.sql
\echo '-- sql/advanced/team_saved_issues.sql   (the team view now shows the issue under "working")'
\x on
\pset format wrapped
\pset columns 110
\ir advanced/team_saved_issues.sql
\pset format aligned
\pset columns 0
\x off
\if :{?pause} \prompt 'Enter for DELETE > ' _ \endif

\echo
\echo '================ 6. DELETE ================'
\echo '-- sql/basic/saved_issue_delete.sql, skill_remove.sql, team_delete.sql'
\ir basic/saved_issue_delete.sql
\ir basic/skill_remove.sql
\ir basic/team_delete.sql
\echo '-- sql/basic/user_delete.sql   (cascades to everything the user owned)'
\! sed '/^--/d' sql/basic/user_delete.sql
\ir basic/user_delete.sql
SELECT (SELECT count(*) FROM users WHERE github_username = 'demo_contributor') AS demo_users_left,
       (SELECT count(*) FROM saved_issues WHERE user_id = :user_id) AS saved_left,
       (SELECT count(*) FROM user_skills WHERE user_id = :user_id) AS skills_left,
       (SELECT count(*) FROM teams WHERE team_id = :team_id) AS teams_left;
\echo
\echo 'Done: every row created above has been deleted.'
