import logging
import os
import secrets
from urllib.parse import urlencode

import psycopg
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from api.auth import (check_password, clear_pending_github, current_user, end_session, hash_password,
                      pending_github, set_pending_github, set_session)
from api.db import get_conn, pool, run_file
from api.github_import import import_user_repos
from api.models import LoginIn, SignupIn
from api.security import auth_requests, client_ip, login_failures, security_event, signups

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)

APP_URL = os.getenv("APP_URL", "http://localhost:5173").rstrip("/")
STATE_COOKIE = "firstpr_oauth_state"


@router.get("/github/start")
def github_start(request: Request):
    """Send the browser to GitHub to prove it owns a GitHub account (no scopes: public profile only)."""
    if not os.getenv("GITHUB_CLIENT_ID") or not os.getenv("GITHUB_CLIENT_SECRET"):
        return RedirectResponse(f"{APP_URL}/signup?error=config", status_code=302)
    auth_requests.check(client_ip(request), request)
    state = secrets.token_urlsafe(32)
    query = urlencode({"client_id": os.environ["GITHUB_CLIENT_ID"], "state": state, "allow_signup": "false",
                       "redirect_uri": f"{APP_URL}/api/auth/github/callback"})
    response = RedirectResponse(f"https://github.com/login/oauth/authorize?{query}", status_code=302)
    response.set_cookie(STATE_COOKIE, state, max_age=600, httponly=True, secure=True, samesite="lax", path="/")
    return response


def _github_login(code):
    """Exchange the OAuth code for a token, read the GitHub user, and drop the token."""
    token = requests.post("https://github.com/login/oauth/access_token", timeout=15, headers={"Accept": "application/json"},
                          data={"client_id": os.environ["GITHUB_CLIENT_ID"], "code": code,
                                "client_secret": os.environ["GITHUB_CLIENT_SECRET"],
                                "redirect_uri": f"{APP_URL}/api/auth/github/callback"}).json().get("access_token")
    if not token:
        return None
    resp = requests.get("https://api.github.com/user", timeout=15,
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    return resp.json() if resp.ok else None


@router.get("/github/callback")
def github_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    def back(path):
        response = RedirectResponse(f"{APP_URL}{path}", status_code=302)
        response.delete_cookie(STATE_COOKIE, path="/", httponly=True, secure=True, samesite="lax")
        return response

    expected = request.cookies.get(STATE_COOKIE)
    if error:
        return back("/signup?error=denied")
    if not code or not expected or not secrets.compare_digest(state, expected):
        security_event("oauth_state_mismatch", request)
        return back("/signup?error=state")
    try:
        gh_user = _github_login(code)
    except (requests.RequestException, ValueError):
        gh_user = None
    if not gh_user or "login" not in gh_user:
        return back("/signup?error=github")

    with pool.connection() as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE lower(github_username) = lower(%s)",
                                (gh_user["login"],)).fetchone()
    if existing:  # GitHub proved who this is, so sign them straight in
        response = back("/")
        set_session(response, existing["user_id"])
        security_event("login_ok", request, user_id=existing["user_id"], via="github")
        return response
    response = back("/signup")
    set_pending_github(response, gh_user["login"], gh_user["id"])
    security_event("github_verified", request, github=gh_user["login"])
    return response


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response):
    # The username comes from the OAuth-verified cookie, never from the request body.
    github_username = pending_github(request)
    if not github_username:
        raise HTTPException(403, "Verify your GitHub account first.")
    ip = client_ip(request)
    auth_requests.check(ip, request)
    signups.check(ip, request)
    try:
        with pool.connection() as conn:
            [user] = run_file(conn, "basic/user_insert", github_username=github_username,
                              email=body.email, password_hash=hash_password(body.password))
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "That GitHub account or email is already registered")
    security_event("signup", request, user_id=user["user_id"])
    try:
        repos = import_user_repos(user["user_id"], github_username)
    except Exception:
        log.exception("Repo import failed for user_id=%s", user["user_id"])
        repos = []
    clear_pending_github(response)
    set_session(response, user["user_id"])
    return {"user": user, "imported_repos": repos}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, conn=Depends(get_conn)):
    auth_requests.check(client_ip(request), request)
    login_name = body.login.lower()
    user = conn.execute(
        "SELECT user_id, github_username, email, created_at, password_hash FROM users "
        "WHERE lower(github_username) = %(login)s OR lower(email) = %(login)s",
        {"login": login_name}).fetchone()
    # Lock out per account when it exists (so re-auth failures count too), else per typed name.
    key = f"user:{user['user_id']}" if user else f"name:{login_name}"
    if login_failures.blocked(key):
        security_event("login_locked", request, login=login_name)
        raise HTTPException(429, "Too many failed attempts. Wait 15 minutes and try again.")
    if not check_password(body.password, user and user.pop("password_hash")):
        login_failures.hit(key)
        security_event("login_failed", request, login=login_name)
        raise HTTPException(401, "Wrong username or password")
    login_failures.reset(key)
    security_event("login_ok", request, user_id=user["user_id"])
    set_session(response, user["user_id"])
    return {"user": user}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    end_session(request, response)


@router.get("/session")
def session(request: Request):
    """Who is logged in (or null), plus a GitHub login verified for signup. Never a 401."""
    try:
        user = current_user(request)
    except HTTPException:
        user = None
    return {"user": user, "pending_github": None if user else pending_github(request)}
