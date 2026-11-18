"""Find active repos in a language that have open "good first issue" issues and add them to the seed list.

Usage:
    python -m ingest.discover --language Go --count 100
    python -m ingest.discover --language Rust --count 100 --dry-run

Repos already in data/seed_repos.csv are skipped; new ones are appended with the note "discovered".
Run python -m ingest.seed_load afterwards to load them.
"""

import argparse
import csv
import logging
from datetime import date, timedelta

from dotenv import load_dotenv

from ingest.github_client import GitHubClient
from ingest.seed_load import SEED_CSV

MIN_BEGINNER_ISSUES = 5  # same bar as the hand-picked seed list
ACTIVE_DAYS = 90


def search_query(qualifier, today=None, min_issues=MIN_BEGINNER_ISSUES):
    """Repo search for `qualifier` ("language:Go", "topic:django") with active beginner issues."""
    pushed = (today or date.today()) - timedelta(days=ACTIVE_DAYS)
    return (f"{qualifier} good-first-issues:>={min_issues} "
            f"archived:false fork:false pushed:>={pushed.isoformat()}")


def discover(gh, qualifier, count, known, min_issues=MIN_BEGINNER_ISSUES):
    """The top `count` repos by stars matching the query, skipping names already in `known` (lowercase)."""
    found = []
    for repo in gh.search("repositories", search_query(qualifier, min_issues=min_issues), sort="stars", order="desc"):
        if repo["full_name"].lower() not in known:
            found.append(repo["full_name"])
            if len(found) == count:
                break
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--language", required=True, help="GitHub language name, e.g. Go or Rust")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--min-issues", type=int, default=MIN_BEGINNER_ISSUES,
                        help="minimum open beginner issues; lower it for languages with few matches")
    parser.add_argument("--dry-run", action="store_true", help="print the repos without changing the CSV")
    args = parser.parse_args()
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with open(SEED_CSV, newline="") as f:
        known = {row["full_name"].lower() for row in csv.DictReader(f)}
    names = discover(GitHubClient(), f"language:{args.language}", args.count, known, args.min_issues)
    for name in names:
        print(name)
    if not args.dry_run:
        with open(SEED_CSV, "a", newline="") as f:
            csv.writer(f).writerows([name, args.language, "discovered"] for name in names)
    print(f"{len(names)} {args.language} repos {'found' if args.dry_run else 'added to ' + SEED_CSV.name}")


if __name__ == "__main__":
    main()
