import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api.auth import check_password, clear_session, current_user, hash_password, set_session
from api.db import get_conn, run_file
from api.github_import import import_user_repos
from api.models import LoginIn, SignupIn
from api.security import auth_requests, client_ip, login_failures, security_event, signups

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response, conn=Depends(get_conn)):
    ip = client_ip(request)
    auth_requests.check(ip, request, "auth")
    signups.check(ip, request, "signup")
    try:
        [user] = run_file(conn, "basic/user_insert", github_username=body.github_username,
                          email=body.email, password_hash=hash_password(body.password))
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "That GitHub username or email is already registered")
    conn.commit()
    security_event("signup", request, user_id=user["user_id"])
    try:
        repos = import_user_repos(conn, user["user_id"], body.github_username)
    except Exception:
        log.exception("Repo import failed for user_id=%s", user["user_id"])
        conn.rollback()
        repos = []
    set_session(response, user["user_id"])
    return {"user": user, "imported_repos": repos}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, conn=Depends(get_conn)):
    auth_requests.check(client_ip(request), request, "auth")
    account = body.login.lower()
    if login_failures.blocked(account):
        security_event("login_locked", request, login=account)
        raise HTTPException(429, "Too many failed attempts. Wait 15 minutes and try again.")
    user = conn.execute(
        "SELECT user_id, github_username, email, created_at, password_hash FROM users "
        "WHERE lower(github_username) = %(login)s OR lower(email) = %(login)s",
        {"login": account}).fetchone()
    if not check_password(body.password, user and user.pop("password_hash")):
        login_failures.hit(account)
        security_event("login_failed", request, login=account)
        raise HTTPException(401, "Wrong username or password")
    login_failures.reset(account)
    security_event("login_ok", request, user_id=user["user_id"])
    set_session(response, user["user_id"])
    return {"user": user}


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_session(response)


@router.get("/session")
def session(request: Request, conn=Depends(get_conn)):
    """Who is logged in, or null. Lets the frontend check without a 401 in the console."""
    try:
        return {"user": current_user(request, conn)}
    except HTTPException:
        return {"user": None}
