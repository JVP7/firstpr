from datetime import datetime, timezone

from ingest.spot_check import check

SYNCED = datetime(2026, 10, 26, tzinfo=timezone.utc)
ROW = {"full_name": "o/r", "number": 1, "title": "Old title", "labels": ["bug"], "comments": 1, "last_synced_at": SYNCED}


class FakeGitHub:
    def __init__(self, issue, comments):
        self.issue, self.comments = issue, comments

    def get(self, url):
        return type("R", (), {"json": lambda _: self.issue})()

    def paginate(self, url):
        return self.comments


def comment(created, updated=None):
    return {"created_at": created, "updated_at": updated or created}


def test_spot_check_flags_each_difference_and_ignores_comments_outside_the_window():
    gh = FakeGitHub({"title": "New title", "labels": [{"name": "bug"}, {"name": "docs"}], "updated_at": "2026-10-01T00:00:00Z"},
                    [comment("2026-10-20T00:00:00Z"), comment("2026-10-21T00:00:00Z"),
                     comment("2026-11-01T00:00:00Z"),   # after the sync
                     comment("2026-01-01T00:00:00Z")])  # before the 90-day window
    diffs, stale = check(gh, ROW)
    assert [d.split(":")[0] for d in diffs] == ["title", "labels", "comments"]
    assert "GitHub 2 in the same window" in diffs[2]
    assert not stale


def test_spot_check_matches_an_unchanged_issue():
    gh = FakeGitHub({"title": "Old title", "labels": [{"name": "bug"}], "updated_at": "2026-11-05T00:00:00Z"},
                    [comment("2026-10-20T00:00:00Z")])
    assert check(gh, ROW) == ([], True)
