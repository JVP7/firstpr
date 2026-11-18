"""Ask GitHub which issues changed in tracked repos since each repo was last looked at. Runs hourly.

Each run takes the BATCH repos checked longest ago, so with 1,200 repos each comes up about every
2 hours. That's one request per repo when little changed, which fits the Actions token's 1,000
requests an hour. Only issues: comments, pull requests and dependencies stay with the daily refresh.

Usage:
    python -m ingest.issue_check
"""

import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from ingest.github_client import GitHubClient
from ingest.seed_load import connect, tracked_names
from ingest.sync import _upsert_issues

BATCH = 600
PAGES = 2  # up to 200 changed issues; a repo busier than that catches up in the daily refresh
log = logging.getLogger("ingest")

DUE = """
SELECT repo_id, full_name, GREATEST(issues_checked_at, last_synced_at) AS since
FROM repos
WHERE last_synced_at IS NOT NULL AND lower(full_name) = ANY (%s)
ORDER BY since
LIMIT %s
"""


def check_repo(gh, conn, repo_id, since):
    """Upsert the repo's issues updated since `since` (closed, assigned, relabeled or new) and return how many."""
    started = datetime.now(timezone.utc)
    # By ID, so a renamed repo still resolves.
    params = {"state": "all", "since": since.isoformat(), "sort": "updated"}
    issues = [i for i in gh.paginate(f"/repositories/{repo_id}/issues", params, PAGES) if "pull_request" not in i]
    with conn.transaction():
        _upsert_issues(conn, repo_id, issues)
        conn.execute("UPDATE repos SET issues_checked_at = %s WHERE repo_id = %s", (started, repo_id))
    return len(issues)


def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    gh, conn = GitHubClient(), connect()
    due = conn.execute(DUE, ([n.lower() for n in tracked_names(conn)], BATCH)).fetchall()
    conn.commit()  # end the read transaction so check_repo's transactions aren't savepoints

    changed, failed = 0, []
    for repo_id, full_name, since in due:
        try:
            changed += check_repo(gh, conn, repo_id, since)
        except Exception:
            log.exception("%s failed", full_name)
            failed.append(full_name)
    log.info("Checked %d repos: %d issues changed, %d failed %s", len(due), changed, len(failed), failed or "")
    conn.close()


if __name__ == "__main__":
    main()
