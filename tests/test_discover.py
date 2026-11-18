from datetime import date

from ingest.discover import discover, search_query


class FakeGitHub:
    def search(self, kind, query, **params):
        self.query = query
        return iter([{"full_name": n} for n in ("Known/Repo", "new/one", "new/two", "new/three")])


def test_discover_skips_known_repos_and_stops_at_count():
    gh = FakeGitHub()
    assert discover(gh, "language:Go", 2, known={"known/repo"}) == ["new/one", "new/two"]
    assert "language:Go" in gh.query and "good-first-issues:>=5" in gh.query


def test_search_query_only_wants_recently_active_repos():
    assert "pushed:>=2026-08-18" in search_query("language:Rust", today=date(2026, 11, 16))


def test_package_names_become_github_topics():
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql://unused")  # api.db reads it on import; no query runs
    from api.github_import import pick_topics, topic_for
    assert topic_for("github.com/spf13/cobra") == "cobra"
    assert topic_for("org.springframework.boot:spring-boot") == "spring-boot"
    assert topic_for("@nestjs/core") == "core"
    assert topic_for("Newtonsoft.Json") == "newtonsoft-json"
    assert topic_for("@@") is None
    picked = pick_topics([("csv", "cargo"), ("CSV", "cargo"), ("csv", "npm"), ("@@", "npm"), ("serde", "cargo")], limit=2)
    assert picked == [('topic:csv language:"Rust"', "csv"), ('topic:csv language:"JavaScript" language:"TypeScript"', "csv")]
