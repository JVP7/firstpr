"""Load every repo in data/seed_repos.csv into the database.

Usage:
    python -m ingest.seed_load               # all seed repos
    python -m ingest.seed_load --limit 5     # first 5 rows
    python -m ingest.seed_load --repo pallets/flask
"""

import argparse
import csv
import logging
import os
import time
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from ingest.github_client import GitHubClient
from ingest.sync import sync_repo, table_counts

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "seed_repos.csv"
log = logging.getLogger("ingest")


def connect():
    # prepare_threshold=None keeps this working through Supabase's transaction pooler.
    return psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None,
                           sslmode=os.getenv("DB_SSLMODE", "require"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="only load the first N repos")
    parser.add_argument("--repo", action="append", help="load this owner/name instead of the CSV (repeatable)")
    args = parser.parse_args()

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.repo:
        names = args.repo
    else:
        with open(SEED_CSV, newline="") as f:
            names = [row["full_name"] for row in csv.DictReader(f)]
    names = names[: args.limit]

    gh = GitHubClient()
    conn = connect()
    failed = []
    start = time.monotonic()
    for i, name in enumerate(names, 1):
        try:
            if conn.closed:
                conn = connect()
            sync_repo(gh, conn, name)
            log.info("[%d/%d] %s synced", i, len(names), name)
        except Exception:
            log.exception("[%d/%d] %s failed", i, len(names), name)
            failed.append(name)

    log.info("Done in %.0fs: %d synced, %d failed %s",
             time.monotonic() - start, len(names) - len(failed), len(failed), failed or "")
    for table, count in table_counts(conn).items():
        log.info("  %-18s %d rows", table, count)
    conn.close()


if __name__ == "__main__":
    main()
