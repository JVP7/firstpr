import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DATABASE_URL", "postgresql://unused")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from api.db import pool, run_file  # noqa: E402
from api.routes.teams import remove_member  # noqa: E402

needs_db = pytest.mark.skipif(os.environ["DATABASE_URL"] == "postgresql://unused", reason="no DATABASE_URL")
REPO = 990000000001  # far above real GitHub IDs; everything is rolled back anyway


@needs_db
def test_split_gives_beginner_issues_to_the_least_familiar_member(db):
    with pool.connection() as conn:
        try:
            conn.execute("INSERT INTO repos (repo_id, full_name) VALUES (%s, 'test/split-repo')", (REPO,))
            pkgs = [r["package_id"] for r in conn.execute(
                "INSERT INTO packages (name, ecosystem) SELECT 'split-test-' || g, 'pypi' "
                "FROM generate_series(1, 4) g RETURNING package_id")]
            conn.execute("INSERT INTO repo_dependencies SELECT %s, unnest(%s::int[])", (REPO, pkgs))
            [label] = conn.execute("INSERT INTO labels (label_id, repo_id, name) VALUES (%s, %s, 'good first issue') "
                                   "RETURNING label_id", (REPO, REPO)).fetchall()
            for n in range(1, 7):
                conn.execute("INSERT INTO issues (issue_id, repo_id, number, title, state, created_at, is_assigned) "
                             "VALUES (%s, %s, %s, 'test issue', 'open', now() - make_interval(days => %s), false)",
                             (REPO + n, REPO, n, n))
            beginner = {REPO + 5, REPO + 6}  # the two oldest, so only the label can put them first
            for issue_id in beginner:
                conn.execute("INSERT INTO issue_labels VALUES (%s, %s)", (issue_id, label["label_id"]))

            [novice, expert] = [run_file(conn, "basic/user_insert", github_username=name, email=f"{name}@split.test",
                                         password_hash="x")[0]["user_id"] for name in ("split-novice", "split-expert")]
            conn.execute("INSERT INTO user_skills SELECT %s, unnest(%s::int[])", (expert, pkgs))
            [team] = run_file(conn, "basic/team_insert", name="split test", created_by=expert, target_repo_id=REPO)
            for user_id in (novice, expert):
                run_file(conn, "basic/team_member_add", team_id=team["team_id"], user_id=user_id, role="member")

            assigned = run_file(conn, "advanced/team_issue_split", team_id=team["team_id"], per_member=3)
            by_user = {u: {a["issue_id"] for a in assigned if a["user_id"] == u} for u in (novice, expert)}
            assert len(by_user[novice]) == len(by_user[expert]) == 3
            assert beginner <= by_user[novice]
        finally:
            conn.rollback()


@needs_db
def test_owner_cannot_leave_but_a_member_can(db):
    with pool.connection() as conn:
        try:
            [owner, member] = [run_file(conn, "basic/user_insert", github_username=name, email=f"{name}@leave.test",
                                        password_hash="x")[0]["user_id"] for name in ("leave-owner", "leave-member")]
            [team] = run_file(conn, "basic/team_insert", name="leave test", created_by=owner, target_repo_id=None)
            run_file(conn, "basic/team_member_add", team_id=team["team_id"], user_id=owner, role="owner")
            run_file(conn, "basic/team_member_add", team_id=team["team_id"], user_id=member, role="member")

            with pytest.raises(HTTPException) as e:
                remove_member(team["team_id"], owner, user={"user_id": owner}, conn=conn)
            assert e.value.status_code == 409
            remove_member(team["team_id"], member, user={"user_id": member}, conn=conn)
        finally:
            conn.rollback()
