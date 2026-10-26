"""Import a user's own GitHub repos and their dependencies at signup."""

from psycopg.rows import tuple_row

from api.db import pool
from ingest.github_client import GitHubClient
from ingest.sync import fetch_repo, write_repo

MAX_REPOS = 20  # most recently pushed; keeps signup to a few seconds


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
