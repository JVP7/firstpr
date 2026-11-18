import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DATABASE_URL", "postgresql://unused")

import pytest  # noqa: E402

from api.db import pool  # noqa: E402
from ingest.issue_check import check_repo  # noqa: E402

needs_db = pytest.mark.skipif(os.environ["DATABASE_URL"] == "postgresql://unused", reason="no DATABASE_URL")
REPO = 990000000101  # far above real GitHub IDs; everything is rolled back anyway


class FakeGitHub:
    def paginate(self, path, params, max_pages):
        self.path, self.params = path, params
        closed = {"id": REPO + 1, "number": 1, "title": "fixed", "state": "closed", "created_at": "2026-11-01T00:00:00Z",
                  "closed_at": "2026-11-18T10:00:00Z", "assignees": [], "labels": []}
        return [closed, {"id": REPO + 9, "pull_request": {}}]


@needs_db
def test_check_closes_an_issue_closed_on_github(db):
    since = datetime(2026, 11, 18, 9, tzinfo=timezone.utc)
    with pool.connection() as conn:
        try:
            conn.execute("INSERT INTO repos (repo_id, full_name) VALUES (%s, 'test/check-repo')", (REPO,))
            conn.execute("INSERT INTO issues (issue_id, repo_id, number, title, state, created_at, is_assigned) "
                         "VALUES (%s, %s, 1, 'broken', 'open', '2026-11-01', false)", (REPO + 1, REPO))
            gh = FakeGitHub()
            assert check_repo(gh, conn, REPO, since) == 1  # the PR is skipped
            assert gh.path == f"/repositories/{REPO}/issues" and gh.params["since"].startswith("2026-11-18T09")
            row = conn.execute("SELECT i.state, r.issues_checked_at FROM issues i JOIN repos r USING (repo_id) "
                               "WHERE i.issue_id = %s", (REPO + 1,)).fetchone()
            assert row["state"] == "closed" and row["issues_checked_at"] is not None
        finally:
            conn.rollback()
