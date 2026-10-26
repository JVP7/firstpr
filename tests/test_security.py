import os

os.environ.setdefault("JWT_SECRET", "x" * 40)
os.environ.setdefault("DATABASE_URL", "postgresql://unused")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from api import security  # noqa: E402
from api.db import load_sql  # noqa: E402
from api.models import SignupIn  # noqa: E402


def test_rate_limiter_blocks_after_limit_and_resets():
    limiter = security.RateLimiter(limit=2, window_seconds=60)
    limiter.hit("a")
    assert not limiter.blocked("a")
    limiter.hit("a")
    assert limiter.blocked("a")
    assert not limiter.blocked("b")
    limiter.reset("a")
    assert not limiter.blocked("a")


class FakeRequest:
    def __init__(self, xff=None, host="10.0.0.1"):
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.client = type("C", (), {"host": host})()


def test_client_ip_ignores_spoofed_hops(monkeypatch):
    monkeypatch.setattr(security, "PROXY_HOPS", 2)
    # Client forged "6.6.6.6"; Vercel appended the real client, Render appended Vercel.
    assert security.client_ip(FakeRequest("6.6.6.6, 203.0.113.9, 76.76.21.1")) == "203.0.113.9"
    monkeypatch.setattr(security, "PROXY_HOPS", 0)
    assert security.client_ip(FakeRequest("6.6.6.6")) == "10.0.0.1"


def test_csrf_rejects_foreign_origin_and_sets_headers():
    app = FastAPI()
    app.middleware("http")(security.security_middleware)
    app.post("/x")(lambda: {"ok": True})
    client = TestClient(app)
    assert client.post("/x", headers={"Origin": "https://evil.example"}).status_code == 403
    ok = client.post("/x", headers={"Origin": security.ALLOWED_ORIGINS[0]})
    assert ok.status_code == 200
    assert ok.headers["x-frame-options"] == "DENY"
    assert client.post("/x").status_code == 200  # no Origin: same-origin or non-browser client


def test_password_limit_counts_bytes():
    SignupIn(github_username="a", email="a@example.com", password="p" * 72)
    with pytest.raises(ValidationError):
        SignupIn(github_username="a", email="a@example.com", password="é" * 40)  # 80 bytes


def test_load_sql_converts_placeholders_but_not_casts():
    sql = load_sql("advanced/stack_match")
    assert "%(user_id)s" in sql and "::numeric" in sql and ":user_id" not in sql
