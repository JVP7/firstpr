"""Compare a random sample of stored issues against GitHub: title, labels and comment count.

Usage:
    python -m ingest.spot_check            # 20 issues
    python -m ingest.spot_check --count 5

Read-only. A difference on an issue GitHub has updated since our last sync is staleness, not an
ingestion bug, so the two are reported separately.
"""

import argparse
import os
from datetime import datetime, timedelta

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

from ingest.github_client import GitHubClient
from ingest.sync import HISTORY_DAYS

SAMPLE = """
SELECT i.issue_id, r.full_name, i.number, i.title, r.last_synced_at,
       ARRAY(SELECT l.name FROM issue_labels il JOIN labels l ON l.label_id = il.label_id
             WHERE il.issue_id = i.issue_id) AS labels,
       (SELECT COUNT(*) FROM comments c WHERE c.issue_id = i.issue_id) AS comments
FROM issues i JOIN repos r ON r.repo_id = i.repo_id
WHERE r.last_synced_at IS NOT NULL
ORDER BY random()
LIMIT %s
"""


def ts(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check(gh, row):
    """Return (differences, stale) for one stored issue."""
    resp = gh.get(f"/repos/{row['full_name']}/issues/{row['number']}")
    if resp is None:
        return ["gone from GitHub (deleted or transferred)"], True
    live = resp.json()
    synced = row["last_synced_at"]
    # Ingest stores comments updated in the HISTORY_DAYS before the sync; count GitHub's the same way.
    window_start = synced - timedelta(days=HISTORY_DAYS)
    expected = sum(1 for c in gh.paginate(f"/repos/{row['full_name']}/issues/{row['number']}/comments")
                   if ts(c["created_at"]) <= synced and ts(c["updated_at"]) >= window_start)

    diffs = []
    if live["title"] != row["title"]:
        diffs.append(f"title: stored {row['title']!r}, GitHub {live['title']!r}")
    live_labels = sorted(label["name"] for label in live["labels"])
    if live_labels != sorted(row["labels"]):
        diffs.append(f"labels: stored {sorted(row['labels'])}, GitHub {live_labels}")
    if expected != row["comments"]:
        diffs.append(f"comments: stored {row['comments']}, GitHub {expected} in the same window")
    return diffs, ts(live["updated_at"]) > synced


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    load_dotenv()

    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None, row_factory=dict_row,
                         sslmode=os.getenv("DB_SSLMODE", "require")) as conn:
        conn.read_only = True
        rows = conn.execute(SAMPLE, (args.count,)).fetchall()

    gh = GitHubClient()
    tally = {"match": 0, "changed since sync": 0, "MISMATCH": 0}
    for row in rows:
        diffs, stale = check(gh, row)
        verdict = "match" if not diffs else "changed since sync" if stale else "MISMATCH"
        tally[verdict] += 1
        print(f"{row['issue_id']}  {row['full_name']}#{row['number']}  {verdict}")
        for d in diffs:
            print(f"    {d}")
    print(f"\n{len(rows)} checked: " + ", ".join(f"{n} {v.lower()}" for v, n in tally.items()))


if __name__ == "__main__":
    main()
