"""Fetch one repo's data from GitHub and upsert it into Postgres.

sync_repo() is the entry point. With issues=False it imports only repo metadata
and dependencies, which is what signup needs for a user's own repos.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from ingest.parsers import parse_package_json, parse_pyproject, parse_requirements

log = logging.getLogger(__name__)

# Labels treated as beginner-friendly; their issues are always fetched in full.
BEGINNER_LABEL = re.compile(r"good.?first|first.?timer|beginner|newcomer|starter|\beasy\b", re.I)

RECENT_ISSUE_PAGES = 2   # most recently updated open issues, 100 per page
BEGINNER_ISSUE_PAGES = 3  # per beginner label
COMMENT_PAGES = 5
PR_PAGES = 5
HISTORY_DAYS = 90


def sync_repo(gh, conn, full_name, issues=True):
    """Upsert one repo and return its repo_id, or None if GitHub can't find it."""
    data = fetch_repo(gh, full_name, issues)
    return write_repo(conn, data) if data else None


def fetch_repo(gh, full_name, issues=True):
    """Everything GitHub has for one repo, without touching the database. None if not found."""
    resp = gh.get(f"/repos/{full_name}")
    if resp is None:
        log.warning("%s: not found, skipping", full_name)
        return None
    repo = resp.json()
    full_name = repo["full_name"]  # follows renames
    data = {"repo": repo, "deps": _fetch_dependencies(gh, full_name), "issues": issues}
    if issues:
        data["labels"] = list(gh.paginate(f"/repos/{full_name}/labels"))
        data["open_issues"] = _fetch_open_issues(gh, full_name, data["labels"])
        data["comments"] = _fetch_comments(gh, full_name)
        data["pulls"] = _fetch_recent_pulls(gh, full_name)
    return data


def write_repo(conn, data):
    """Upsert what fetch_repo returned in one transaction; returns the repo_id."""
    repo_id = data["repo"]["id"]
    with conn.transaction(), conn.pipeline():
        _upsert_repo(conn, data["repo"])
        _replace_dependencies(conn, repo_id, data["deps"])
        if data["issues"]:
            _upsert_labels(conn, repo_id, data["labels"])
            _upsert_issues(conn, repo_id, data["open_issues"])
            issue_ids = dict(conn.execute(
                "SELECT number, issue_id FROM issues WHERE repo_id = %s", (repo_id,)).fetchall())
            _upsert_comments(conn, data["comments"], issue_ids)
            _upsert_pulls(conn, repo_id, data["pulls"])
        conn.execute("UPDATE repos SET last_synced_at = now() WHERE repo_id = %s", (repo_id,))
    return repo_id


def table_counts(conn):
    tables = ["repos", "packages", "repo_dependencies", "issues", "labels",
              "issue_labels", "comments", "pull_requests"]
    return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables}


# --- GitHub fetches -------------------------------------------------------

def _fetch_dependencies(gh, full_name):
    deps = set()
    text = gh.get_file(full_name, "requirements.txt")
    if text:
        deps |= {(name, "pypi") for name in parse_requirements(text)}
    text = gh.get_file(full_name, "pyproject.toml")
    if text:
        deps |= {(name, "pypi") for name in parse_pyproject(text)}
    text = gh.get_file(full_name, "package.json")
    if text:
        deps |= {(name, "npm") for name in parse_package_json(text)}
    return deps


def _fetch_open_issues(gh, full_name, labels):
    """Recently updated open issues plus every open issue with a beginner label."""
    found = {}
    path = f"/repos/{full_name}/issues"
    batches = [gh.paginate(path, {"state": "open", "sort": "updated"}, RECENT_ISSUE_PAGES)]
    batches += [gh.paginate(path, {"state": "open", "labels": label["name"]}, BEGINNER_ISSUE_PAGES)
                for label in labels if BEGINNER_LABEL.search(label["name"])]
    for batch in batches:
        for issue in batch:
            if "pull_request" not in issue:  # the issues endpoint also returns PRs
                found[issue["id"]] = issue
    return list(found.values())


def _fetch_comments(gh, full_name):
    since = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"sort": "created", "direction": "desc", "since": since}
    return list(gh.paginate(f"/repos/{full_name}/issues/comments", params, COMMENT_PAGES))


def _fetch_recent_pulls(gh, full_name):
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    pulls = []
    params = {"state": "all", "sort": "created", "direction": "desc"}
    for pr in gh.paginate(f"/repos/{full_name}/pulls", params, PR_PAGES):
        if datetime.fromisoformat(pr["created_at"]) < cutoff:
            break
        pulls.append(pr)
    return pulls


# --- Upserts --------------------------------------------------------------

def _upsert_repo(conn, repo):
    conn.execute(
        """
        INSERT INTO repos (repo_id, full_name, primary_language, stars, is_archived)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (repo_id) DO UPDATE SET
            full_name = EXCLUDED.full_name,
            primary_language = EXCLUDED.primary_language,
            stars = EXCLUDED.stars,
            is_archived = EXCLUDED.is_archived
        """,
        (repo["id"], repo["full_name"], repo["language"], repo["stargazers_count"], repo["archived"]),
    )


def _replace_dependencies(conn, repo_id, deps):
    # Two set-based statements instead of two round trips per package.
    names, ecosystems = [n for n, _ in deps], [e for _, e in deps]
    conn.execute("DELETE FROM repo_dependencies WHERE repo_id = %s", (repo_id,))
    conn.execute(
        "INSERT INTO packages (name, ecosystem) SELECT * FROM unnest(%s::text[], %s::text[]) "
        "ON CONFLICT (name, ecosystem) DO NOTHING",
        (names, ecosystems),
    )
    conn.execute(
        """
        INSERT INTO repo_dependencies (repo_id, package_id)
        SELECT %s, p.package_id
        FROM unnest(%s::text[], %s::text[]) AS d(name, ecosystem)
        JOIN packages p USING (name, ecosystem)
        ON CONFLICT DO NOTHING
        """,
        (repo_id, names, ecosystems),
    )


def _upsert_label(conn, repo_id, label):
    # A label deleted and recreated on GitHub keeps its name but gets a new ID.
    conn.execute("DELETE FROM labels WHERE repo_id = %s AND name = %s AND label_id <> %s",
                 (repo_id, label["name"], label["id"]))
    conn.execute(
        """
        INSERT INTO labels (label_id, repo_id, name) VALUES (%s, %s, %s)
        ON CONFLICT (label_id) DO UPDATE SET name = EXCLUDED.name
        """,
        (label["id"], repo_id, label["name"]),
    )


def _upsert_labels(conn, repo_id, labels):
    for label in labels:
        _upsert_label(conn, repo_id, label)


def _upsert_issues(conn, repo_id, issues):
    """Upsert issues and replace their labels."""
    for issue in issues:
        conn.execute(
            """
            INSERT INTO issues (issue_id, repo_id, number, title, state, created_at, closed_at, is_assigned)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (issue_id) DO UPDATE SET
                title = EXCLUDED.title,
                state = EXCLUDED.state,
                closed_at = EXCLUDED.closed_at,
                is_assigned = EXCLUDED.is_assigned
            """,
            (issue["id"], repo_id, issue["number"], issue["title"], issue["state"],
             issue["created_at"], issue["closed_at"], bool(issue["assignees"])),
        )
        conn.execute("DELETE FROM issue_labels WHERE issue_id = %s", (issue["id"],))
        for label in issue["labels"]:
            _upsert_label(conn, repo_id, label)
            conn.execute("INSERT INTO issue_labels (issue_id, label_id) VALUES (%s, %s)",
                         (issue["id"], label["id"]))


def _upsert_comments(conn, comments, issue_ids):
    """Store comments that belong to an issue we have; others (PRs, old issues) are skipped."""
    for comment in comments:
        number = int(comment["issue_url"].rsplit("/", 1)[1])
        if number not in issue_ids:
            continue
        conn.execute(
            """
            INSERT INTO comments (comment_id, issue_id, author_login, author_association, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (comment_id) DO UPDATE SET author_association = EXCLUDED.author_association
            """,
            (comment["id"], issue_ids[number], (comment["user"] or {}).get("login"),
             comment["author_association"], comment["created_at"]),
        )


def _upsert_pulls(conn, repo_id, pulls):
    for pr in pulls:
        conn.execute(
            """
            INSERT INTO pull_requests (pr_id, repo_id, author_login, created_at, merged_at, state)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (pr_id) DO UPDATE SET
                merged_at = EXCLUDED.merged_at,
                state = EXCLUDED.state
            """,
            (pr["id"], repo_id, (pr["user"] or {}).get("login"), pr["created_at"],
             pr["merged_at"], pr["state"]),
        )
