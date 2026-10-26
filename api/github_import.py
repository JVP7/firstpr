"""Import a user's own GitHub repos and their dependencies at signup."""

from psycopg.rows import tuple_row

from ingest.github_client import GitHubClient
from ingest.sync import sync_repo

MAX_REPOS = 20  # most recently pushed; keeps signup to a few seconds


def import_user_repos(conn, user_id, github_username):
    """Sync the user's non-fork public repos (metadata + dependencies) and link them. Returns names."""
    gh = GitHubClient()
    listing = gh.paginate(f"/users/{github_username}/repos",
                          {"sort": "pushed", "type": "owner"}, max_pages=1)
    names = [r["full_name"] for r in listing if not r["fork"] and not r["archived"]][:MAX_REPOS]
    row_factory, conn.row_factory = conn.row_factory, tuple_row  # ingest code indexes rows as tuples
    try:
        imported = _sync_all(gh, conn, user_id, names)
    finally:
        conn.row_factory = row_factory
    conn.commit()
    return imported


def _sync_all(gh, conn, user_id, names):
    imported = []
    for name in names:
        repo_id = sync_repo(gh, conn, name, issues=False)
        if repo_id is not None:
            conn.execute("INSERT INTO user_repos (user_id, repo_id) VALUES (%s, %s) "
                         "ON CONFLICT DO NOTHING", (user_id, repo_id))
            imported.append(name)
    return imported
