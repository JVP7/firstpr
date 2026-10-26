import os
import uuid

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("JWT_SECRET", "x" * 40)
os.environ.setdefault("DATABASE_URL", "postgresql://unused")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from fastapi import HTTPException, Response  # noqa: E402

from api import auth, security  # noqa: E402
from api.db import load_sql, pool  # noqa: E402
from api.models import SignupIn  # noqa: E402

needs_db = pytest.mark.skipif(os.environ["DATABASE_URL"] == "postgresql://unused", reason="no DATABASE_URL")


@pytest.fixture(scope="module")
def db():
    pool.open()
    yield
    pool.close()


class CookieRequest:
    """Just enough of a Request for the auth helpers."""
    def __init__(self, cookies):
        self.cookies, self.headers, self.client = cookies, {}, type("C", (), {"host": "test"})()


def cookie_from(response, name):
    header = next(v for k, v in response.raw_headers if k == b"set-cookie" and v.startswith(name.encode()))
    return header.decode().split(";")[0].split("=", 1)[1]


@needs_db
def test_rate_limiter_blocks_after_limit_and_resets(db):
    limiter = security.RateLimiter(f"test-{uuid.uuid4()}", limit=2, window_seconds=60)
    limiter.hit("a")
    assert not limiter.blocked("a")
    limiter.hit("a")
    assert limiter.blocked("a")
    assert not limiter.blocked("b")
    limiter.reset("a")
    assert not limiter.blocked("a")


@needs_db
def test_logout_revokes_the_token(db):
    name = f"zz-test-{uuid.uuid4().hex[:8]}"
    with pool.connection() as conn:
        user_id = conn.execute("INSERT INTO users (github_username, email, password_hash) VALUES (%s, %s, 'x') "
                               "RETURNING user_id", (name, f"{name}@example.com")).fetchone()["user_id"]
    try:
        _check_revocation(user_id)
    finally:
        with pool.connection() as conn:
            conn.execute("DELETE FROM users WHERE user_id = %s", (user_id,))


def _check_revocation(user_id):
    login = Response()
    auth.set_session(login, user_id)
    token = cookie_from(login, auth.COOKIE)
    assert auth.current_user(CookieRequest({auth.COOKIE: token}))["user_id"] == user_id
    auth.end_session(CookieRequest({auth.COOKIE: token}), Response())
    with pytest.raises(HTTPException) as e:
        auth.current_user(CookieRequest({auth.COOKIE: token}))
    assert e.value.status_code == 401


def test_signup_cookie_is_not_a_session():
    pending = Response()
    auth.set_pending_github(pending, "octocat", 1)
    token = cookie_from(pending, auth.PENDING_COOKIE)
    assert auth.pending_github(CookieRequest({auth.PENDING_COOKIE: token})) == "octocat"
    with pytest.raises(HTTPException):
        auth.current_user(CookieRequest({auth.COOKIE: token}))


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
    SignupIn(email="a@example.com", password="P!" + "p" * 70)
    with pytest.raises(ValidationError):
        SignupIn(email="a@example.com", password="É!" + "é" * 40)  # 83 bytes, passes the other rules


def test_load_sql_converts_placeholders_but_not_casts():
    sql = load_sql("advanced/stack_match")
    assert "%(user_id)s" in sql and "::numeric" in sql and ":user_id" not in sql


@needs_db
def test_ending_all_sessions_rejects_older_tokens(db):
    import time
    name = f"zz-test-{uuid.uuid4().hex[:8]}"
    with pool.connection() as conn:
        user_id = conn.execute("INSERT INTO users (github_username, email, password_hash) VALUES (%s, %s, 'x') "
                               "RETURNING user_id", (name, f"{name}@example.com")).fetchone()["user_id"]
    try:
        before = Response()
        auth.set_session(before, user_id)
        old = cookie_from(before, auth.COOKIE)
        time.sleep(1.1)  # iat has whole-second precision
        auth.end_all_sessions(user_id)
        with pytest.raises(HTTPException):
            auth.current_user(CookieRequest({auth.COOKIE: old}))
        after = Response()
        auth.set_session(after, user_id)
        assert auth.current_user(CookieRequest({auth.COOKIE: cookie_from(after, auth.COOKIE)}))["user_id"] == user_id
    finally:
        with pool.connection() as conn:
            conn.execute("DELETE FROM users WHERE user_id = %s", (user_id,))


@pytest.mark.parametrize("password, ok", [
    ("Hunter2!going", True),
    ("Abcdefghij~k", True),         # any symbol counts
    ("Abcdefghij<k", True),
    ("Ñandú#passwords", True),      # non-ASCII letters count as upper/lower
    ("hunter2!going", False),       # no uppercase
    ("HUNTER2!GOING", False),       # no lowercase
    ("Hunter2going", False),        # no special character
    ("Hunter 2going", False),       # a space is not a special character
    ("Abcdefghi!j", False),         # 11 characters: too short
])
def test_password_rules(password, ok):
    if ok:
        SignupIn(email="a@example.com", password=password)
    else:
        with pytest.raises(ValidationError):
            SignupIn(email="a@example.com", password=password)


@pytest.mark.parametrize("password, problem", [
    ("Octocat!Rules99", "your GitHub username"),
    ("my.MAIL#2026xyz", "your email name"),
    ("Starpull!rocks1", "the site name"),
    ("FirstPR!forever", "the site name"),
    ("Cobalt!Harbor42", None),
])
def test_password_context(password, problem):
    from api.passwords import context_problem
    result = context_problem(password, "octocat", "my.mail@example.com")
    assert (problem in result) if problem else result is None


class FakeRange:
    def __init__(self, text=None, error=None):
        self.text, self.error = text, error

    def raise_for_status(self):
        if self.error:
            raise self.error


def test_breach_check_matches_locally_and_fails_open(monkeypatch):
    import hashlib
    import requests
    from api import passwords

    pw = "Cobalt!Harbor42"
    suffix = hashlib.sha1(pw.encode()).hexdigest().upper()[5:]
    sent = []

    def fake_get(url, **kwargs):
        sent.append(url)
        return FakeRange(text=f"0000000000000000000000000000000000A:3\r\n{suffix}:42")

    monkeypatch.setattr(passwords.requests, "get", fake_get)
    assert passwords.breach_count(pw) == 42
    assert sent[0].endswith("/" + hashlib.sha1(pw.encode()).hexdigest().upper()[:5])  # only the prefix leaves

    monkeypatch.setattr(passwords.requests, "get", lambda url, **kw: FakeRange(text=f"{suffix}:0"))
    assert passwords.breach_count(pw) == 0  # padding row, not a real match

    def down(url, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(passwords.requests, "get", down)
    assert passwords.breach_count(pw) is None
    assert passwords.new_password_problem(pw, "octocat", "a@example.com") is None  # fails open
