from datetime import datetime, timezone

from ingest.sync import _cargo_crates, _fetch_dependencies, _fetch_issues


class FakeGitHub:
    def __init__(self):
        self.calls = []

    def paginate(self, path, params, max_pages):
        self.calls.append(params)
        if params.get("state") == "all":
            return [{"id": 1, "state": "closed"}, {"id": 3, "pull_request": {}}]
        return [{"id": 1, "state": "open"}, {"id": 2, "state": "open"}]


def test_resync_picks_up_issues_closed_since_the_last_sync():
    gh = FakeGitHub()
    issues = _fetch_issues(gh, "o/r", [], since=datetime(2026, 10, 26, tzinfo=timezone.utc))
    assert {i["id"]: i["state"] for i in issues} == {1: "closed", 2: "open"}  # PRs skipped
    assert gh.calls[-1]["since"].startswith("2026-10-26")


def test_first_sync_only_asks_for_open_issues():
    gh = FakeGitHub()
    _fetch_issues(gh, "o/r", [])
    assert all(call["state"] == "open" for call in gh.calls)


class FakeCargoGitHub:
    files = {
        "crates/core/Cargo.toml": '[dependencies]\nserde = "1"\nmy-cli = { path = "../cli" }',
        "crates/cli/Cargo.toml": '[dependencies]\nclap = "4"',
        "tools/gen/Cargo.toml": '[dependencies]\nquote = "1"',
    }

    def get(self, path):
        assert path.endswith("/contents/crates")
        listing = [{"path": "crates/core", "type": "dir"}, {"path": "crates/cli", "type": "dir"},
                   {"path": "crates/README.md", "type": "file"}]
        return type("R", (), {"json": lambda _: listing})()

    def get_file(self, full_name, path):
        return self.files.get(path)


def test_cargo_workspace_reads_member_crates():
    root = '[workspace]\nmembers = ["crates/*", "tools/gen"]\n\n[workspace.dependencies]\nanyhow = "1"'
    assert _cargo_crates(FakeCargoGitHub(), "o/r", root) == {"anyhow", "serde", "clap", "quote"}


class FakeRepoGitHub:
    files = {
        "pom.xml": "<project><dependencies><dependency><groupId>junit</groupId><artifactId>junit</artifactId>"
                   "</dependency></dependencies></project>",
        "gradle/libs.versions.toml": '[libraries]\nokhttp = "com.squareup.okhttp3:okhttp:4"',
        "app.gemspec": 's.add_dependency "rack"',
        "src/Api/Api.csproj": '<PackageReference Include="Serilog" />',
    }

    def __init__(self):
        self.fetched = []

    def get(self, path, params=None):
        if path.endswith("/contents"):
            body = [{"name": "pom.xml", "type": "file"}, {"name": "app.gemspec", "type": "file"},
                    {"name": "README.md", "type": "file"}, {"name": "gradle", "type": "dir"}]
        else:
            assert path.endswith("/git/trees/main") and params == {"recursive": "1"}
            body = {"tree": [{"path": "src/Api/Api.csproj", "type": "blob"}, {"path": "src", "type": "tree"}]}
        return type("R", (), {"json": lambda _: body})()

    def get_file(self, full_name, path):
        self.fetched.append(path)
        return self.files.get(path)


def test_dependencies_come_only_from_files_the_repo_has():
    gh = FakeRepoGitHub()
    deps = _fetch_dependencies(gh, {"full_name": "o/r", "language": "C#", "default_branch": "main"})
    assert deps == {("junit:junit", "maven"), ("com.squareup.okhttp3:okhttp", "maven"),
                    ("rack", "rubygems"), ("serilog", "nuget")}
    assert "README.md" not in gh.fetched and "package.json" not in gh.fetched
