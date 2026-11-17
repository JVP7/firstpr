"""Fetch one repo's data from GitHub and upsert it into Postgres.

sync_repo() is the entry point. With issues=False it imports only repo metadata
and dependencies, which is what signup needs for a user's own repos.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from ingest import parsers
from ingest.parsers import cargo_workspace_members, parse_cargo_toml

log = logging.getLogger(__name__)

# Labels treated as beginner-friendly; their issues are always fetched in full.
BEGINNER_LABEL = re.compile(r"good.?first|first.?timer|beginner|newcomer|starter|\beasy\b", re.I)

RECENT_ISSUE_PAGES = 2   # most recently updated open issues, 100 per page
BEGINNER_ISSUE_PAGES = 3  # per beginner label
CHANGED_ISSUE_PAGES = 10  # issues of any state updated since the last sync
COMMENT_PAGES = 5
PR_PAGES = 5
HISTORY_DAYS = 90
CARGO_MEMBERS = 15  # workspace member Cargo.tomls read per repo; big workspaces have hundreds
CSPROJ_FILES = 15

# Dependency files read when they're in the repo root, by file name, with their ecosystem and parser.
MANIFESTS = {
    "requirements.txt": ("pypi", parsers.parse_requirements),
    "pyproject.toml": ("pypi", parsers.parse_pyproject),
    "package.json": ("npm", parsers.parse_package_json),
    "go.mod": ("go", parsers.parse_go_mod),
    "Cargo.toml": ("cargo", parsers.parse_cargo_toml),
    "pom.xml": ("maven", parsers.parse_pom),
    "build.gradle": ("maven", parsers.parse_gradle),
    "build.gradle.kts": ("maven", parsers.parse_gradle),
    "libs.versions.toml": ("maven", parsers.parse_gradle_catalog),
    "Gemfile": ("rubygems", parsers.parse_gemfile),
    "composer.json": ("packagist", parsers.parse_composer_json),
    "Directory.Packages.props": ("nuget", parsers.parse_nuget),
    "vcpkg.json": ("c/c++", parsers.parse_vcpkg_json),
    "conanfile.txt": ("c/c++", parsers.parse_conanfile_txt),
    "conanfile.py": ("c/c++", parsers.parse_conanfile_py),
    "CMakeLists.txt": ("c/c++", parsers.parse_cmake),
    "meson.build": ("c/c++", parsers.parse_meson),
}
MANIFEST_SUFFIXES = {".gemspec": ("rubygems", parsers.parse_gemspec), ".csproj": ("nuget", parsers.parse_nuget)}


def sync_repo(gh, conn, full_name, issues=True):
    """Upsert one repo and return its repo_id, or None if GitHub can't find it."""
    with conn.transaction():  # closed right away, so write_repo's transaction is a real one, not a savepoint
        row = conn.execute("SELECT last_synced_at FROM repos WHERE lower(full_name) = lower(%s)", (full_name,)).fetchone()
    data = fetch_repo(gh, full_name, issues, since=row[0] if row else None)
    return write_repo(conn, data) if data else None


def fetch_repo(gh, full_name, issues=True, since=None):
    """Everything GitHub has for one repo, without touching the database. None if not found."""
    resp = gh.get(f"/repos/{full_name}")
    if resp is None:
        log.warning("%s: not found, skipping", full_name)
        return None
    repo = resp.json()
    full_name = repo["full_name"]  # follows renames
    data = {"repo": repo, "deps": _fetch_dependencies(gh, repo), "issues": issues}
    if issues:
        data["labels"] = list(gh.paginate(f"/repos/{full_name}/labels"))
        data["open_issues"] = _fetch_issues(gh, full_name, data["labels"], since)
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

def _manifest(path):
    """(ecosystem, parser) for a dependency file path, or None if we don't read that file."""
    name = path.rsplit("/", 1)[-1]
    return MANIFESTS.get(name) or next((m for suffix, m in MANIFEST_SUFFIXES.items() if name.endswith(suffix)), None)


def _fetch_dependencies(gh, repo):
    full_name = repo["full_name"]
    # One listing of the root instead of a request per manifest type, most of which would 404.
    resp = gh.get(f"/repos/{full_name}/contents")
    listing = resp.json() if resp is not None else []
    root = {entry["name"]: entry["type"] for entry in listing} if isinstance(listing, list) else {}
    paths = [name for name, kind in root.items() if kind == "file" and _manifest(name)]
    if root.get("gradle") == "dir":
        paths.append("gradle/libs.versions.toml")
    if repo["language"] == "C#":  # .csproj files live in project folders, not the root
        paths += _csproj_paths(gh, repo)

    deps = set()
    for path in dict.fromkeys(paths):
        text = gh.get_file(full_name, path)
        if text:
            ecosystem, parse = _manifest(path)
            names = _cargo_crates(gh, full_name, text) if path == "Cargo.toml" else parse(text)
            deps |= {(name, ecosystem) for name in names}
    return deps


def _csproj_paths(gh, repo):
    """The CSPROJ_FILES shallowest .csproj paths in the repo, from one recursive tree listing."""
    resp = gh.get(f"/repos/{repo['full_name']}/git/trees/{repo['default_branch']}", {"recursive": "1"})
    tree = resp.json().get("tree", []) if resp is not None else []
    paths = [e["path"] for e in tree if e["type"] == "blob" and e["path"].endswith(".csproj")]
    return sorted(paths, key=lambda p: (p.count("/"), p))[:CSPROJ_FILES]


def _cargo_crates(gh, full_name, text):
    """Crates in the root Cargo.toml and, when it's a workspace, in its first CARGO_MEMBERS members,
    since a workspace root often lists only member folders and keeps the dependencies in them."""
    names = parse_cargo_toml(text)
    for member in _cargo_member_dirs(gh, full_name, cargo_workspace_members(text))[:CARGO_MEMBERS]:
        member_text = gh.get_file(full_name, f"{member}/Cargo.toml")
        if member_text:
            names |= parse_cargo_toml(member_text)
    return names


def _cargo_member_dirs(gh, full_name, members):
    dirs = []
    for member in members:
        if member.endswith("/*"):  # a glob: list the folder
            resp = gh.get(f"/repos/{full_name}/contents/{member[:-2]}")
            if resp is not None and isinstance(resp.json(), list):
                dirs += [entry["path"] for entry in resp.json() if entry.get("type") == "dir"]
        elif "*" not in member:
            dirs.append(member.rstrip("/"))
        if len(dirs) >= CARGO_MEMBERS:
            break
    return dirs


def _fetch_issues(gh, full_name, labels, since=None):
    """Recently updated open issues, every open issue with a beginner label, and, on a re-sync, every
    issue changed since `since` in any state, so issues closed or assigned on GitHub stop showing as open."""
    found = {}
    path = f"/repos/{full_name}/issues"
    batches = [gh.paginate(path, {"state": "open", "sort": "updated"}, RECENT_ISSUE_PAGES)]
    batches += [gh.paginate(path, {"state": "open", "labels": label["name"]}, BEGINNER_ISSUE_PAGES)
                for label in labels if BEGINNER_LABEL.search(label["name"])]
    if since:
        batches.append(gh.paginate(path, {"state": "all", "since": since.isoformat()}, CHANGED_ISSUE_PAGES))
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
