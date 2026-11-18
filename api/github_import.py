"""Import a user's own GitHub repos and their dependencies at signup, then load more repos for their stack."""

import logging
import re

from psycopg.rows import tuple_row

from api.db import pool
from ingest.discover import discover
from ingest.github_client import GitHubClient
from ingest.sync import fetch_repo, write_repo

MAX_REPOS = 20  # most recently pushed; keeps signup to a few seconds
log = logging.getLogger(__name__)


def import_user_repos(user_id, github_username):
    """Sync the user's non-fork public repos (metadata + dependencies) and link them. Returns names.

    The slow GitHub calls run first, without a database connection, so a burst of signups
    can't tie up the pool for the ~20 seconds an import takes."""
    gh = GitHubClient()
    listing = gh.paginate(f"/users/{github_username}/repos",
                          {"sort": "pushed", "type": "owner"}, max_pages=1)
    names = [r["full_name"] for r in listing if not r["fork"] and not r["archived"]][:MAX_REPOS]
    fetched = [d for d in (fetch_repo(gh, name, issues=False) for name in names) if d]

    with pool.connection() as conn:
        # Ingest code indexes rows as tuples; restore the factory before the pool reuses the connection.
        row_factory, conn.row_factory = conn.row_factory, tuple_row
        try:
            for data in fetched:
                repo_id = write_repo(conn, data)
                conn.execute("INSERT INTO user_repos (user_id, repo_id) VALUES (%s, %s) "
                             "ON CONFLICT DO NOTHING", (user_id, repo_id))
        finally:
            conn.row_factory = row_factory
    return [d["repo"]["full_name"] for d in fetched]


TOPIC_SEARCHES = 8      # GitHub searches per user; most of a user's packages aren't repo topics
TOPICS_PER_USER = 4     # topics that found repos
REPOS_PER_TOPIC = 3
MIN_STARS = 250  # keeps out personal projects that happen to share a topic
# Topics like "csv" span languages, so search only the languages that use the package's ecosystem.
ECOSYSTEM_LANGUAGES = {
    "pypi": ["Python"], "npm": ["JavaScript", "TypeScript"], "go": ["Go"], "cargo": ["Rust"],
    "maven": ["Java", "Kotlin"], "rubygems": ["Ruby"], "packagist": ["PHP"], "nuget": ["C#"], "c/c++": ["C", "C++"],
}
MAX_REPOS_TRACKED = 3000  # Supabase's free 500 MB holds about 4,000 at ~0.12 MB each

USER_PACKAGES_BY_COVERAGE = """
SELECT p.name, p.ecosystem, COUNT(rd.repo_id) AS repos
FROM (SELECT package_id FROM user_dependencies WHERE user_id = %(user_id)s
      UNION SELECT package_id FROM user_skills WHERE user_id = %(user_id)s) u
JOIN packages p ON p.package_id = u.package_id
LEFT JOIN repo_dependencies rd ON rd.package_id = u.package_id
GROUP BY p.name, p.ecosystem
ORDER BY repos DESC, p.name
"""


def topic_for(package):
    """The GitHub topic a package would go by: "github.com/spf13/cobra" -> "cobra",
    "org.springframework.boot:spring-boot" -> "spring-boot". Topics are lowercase, digits and hyphens."""
    name = re.split(r"[/:]", package)[-1]
    topic = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return topic if 0 < len(topic) <= 50 else None


def pick_topics(packages, limit=TOPIC_SEARCHES):
    """Distinct search qualifiers for the user's (name, ecosystem) packages, most widely used first:
    obscure packages are rarely repo topics, and shared common packages are what matches score on."""
    queries = {}
    for name, ecosystem in packages:
        topic = topic_for(name)
        if topic:
            languages = " ".join(f'language:"{lang}"' for lang in ECOSYSTEM_LANGUAGES[ecosystem])
            queries.setdefault(f"topic:{topic} {languages}", topic)
    return list(queries.items())[:limit]


def load_matching_repos(user_id):
    """Find active repos with beginner issues tagged with the user's main packages, load them
    with their issues, and record them so the daily refresh keeps them current. Runs after the
    response, so a failure is only logged."""
    try:
        gh = GitHubClient()
        with pool.connection() as conn:
            if conn.execute("SELECT COUNT(*) AS n FROM repos").fetchone()["n"] >= MAX_REPOS_TRACKED:
                return
            packages = [(r["name"], r["ecosystem"]) for r in conn.execute(USER_PACKAGES_BY_COVERAGE, {"user_id": user_id})]
            known = {r["n"] for r in conn.execute("SELECT lower(full_name) AS n FROM repos")}

        found, topics = [], 0
        for qualifier, topic in pick_topics(packages):
            names = discover(gh, f"{qualifier} stars:>={MIN_STARS}", REPOS_PER_TOPIC, known)  # seed list's bar: 5 beginner issues
            known.update(n.lower() for n in names)
            found += [(n, topic) for n in names]
            topics += bool(names)
            if topics == TOPICS_PER_USER:
                break
        fetched = [(d, topic) for d, topic in ((fetch_repo(gh, n), t) for n, t in found) if d]

        with pool.connection() as conn:
            row_factory, conn.row_factory = conn.row_factory, tuple_row
            try:
                for data, topic in fetched:
                    repo_id = write_repo(conn, data)
                    conn.execute("INSERT INTO requested_repos (repo_id, requested_by, topic) VALUES (%s, %s, %s) "
                                 "ON CONFLICT DO NOTHING", (repo_id, user_id, topic))
            finally:
                conn.row_factory = row_factory
        log.info("Loaded %d repos on demand for user_id=%s", len(fetched), user_id)
    except Exception:
        log.exception("On-demand load failed for user_id=%s", user_id)
