import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DATABASE_URL", "postgresql://unused")

import pytest  # noqa: E402

from api.db import pool, run_file  # noqa: E402

needs_db = pytest.mark.skipif(os.environ["DATABASE_URL"] == "postgresql://unused", reason="no DATABASE_URL")
REPO = 990000000201  # far above real GitHub IDs; everything is rolled back anyway


@needs_db
def test_beginner_filter_keeps_only_labeled_issues(db):
    with pool.connection() as conn:
        try:
            conn.execute("INSERT INTO repos (repo_id, full_name) VALUES (%s, 'test/match-repo')", (REPO,))
            [pkg] = conn.execute("INSERT INTO packages (name, ecosystem) VALUES ('match-test-pkg', 'pypi') "
                                 "RETURNING package_id").fetchall()
            conn.execute("INSERT INTO repo_dependencies VALUES (%s, %s)", (REPO, pkg["package_id"]))
            for n in (1, 2):
                conn.execute("INSERT INTO issues (issue_id, repo_id, number, title, state, created_at, is_assigned) "
                             "VALUES (%s, %s, %s, 'test issue', 'open', now(), false)", (REPO + n, REPO, n))
            conn.execute("INSERT INTO labels (label_id, repo_id, name) VALUES (%s, %s, 'good first issue')", (REPO, REPO))
            conn.execute("INSERT INTO issue_labels VALUES (%s, %s)", (REPO + 2, REPO))
            [user] = run_file(conn, "basic/user_insert", github_username="match-tester", email="m@match.test",
                              password_hash="x")
            conn.execute("INSERT INTO user_skills VALUES (%s, %s)", (user["user_id"], pkg["package_id"]))

            def matches(beginner_only):
                rows = run_file(conn, "advanced/stack_match", user_id=user["user_id"], languages=None,
                                beginner_only=beginner_only, limit=20)
                return {r["issue_id"] for r in rows if r["full_name"] == "test/match-repo"}

            assert matches(False) == {REPO + 1, REPO + 2}
            assert matches(True) == {REPO + 2}
        finally:
            conn.rollback()
