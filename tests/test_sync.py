from datetime import datetime, timezone

from ingest.sync import _fetch_issues


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
