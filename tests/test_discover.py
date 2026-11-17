from datetime import date

from ingest.discover import discover, search_query


class FakeGitHub:
    def search(self, kind, query, **params):
        self.query = query
        return iter([{"full_name": n} for n in ("Known/Repo", "new/one", "new/two", "new/three")])


def test_discover_skips_known_repos_and_stops_at_count():
    gh = FakeGitHub()
    assert discover(gh, "Go", 2, known={"known/repo"}) == ["new/one", "new/two"]
    assert "language:Go" in gh.query and "good-first-issues:>=5" in gh.query


def test_search_query_only_wants_recently_active_repos():
    assert "pushed:>=2026-08-18" in search_query("Rust", today=date(2026, 11, 16))
