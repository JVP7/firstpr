import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.auth import check_password, hash_password, make_token
from api.db import get_conn, run_file
from api.github_import import import_user_repos
from api.models import LoginIn, SignupIn

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)


@router.post("/signup", status_code=201)
def signup(body: SignupIn, conn=Depends(get_conn)):
    try:
        [user] = run_file(conn, "basic/user_insert", github_username=body.github_username,
                          email=body.email, password_hash=hash_password(body.password))
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "That GitHub username or email is already registered")
    conn.commit()
    try:
        repos = import_user_repos(conn, user["user_id"], body.github_username)
    except Exception:
        log.exception("Repo import failed for %s", body.github_username)
        conn.rollback()
        repos = []
    return {"token": make_token(user["user_id"]), "user": user, "imported_repos": repos}


@router.post("/login")
def login(body: LoginIn, conn=Depends(get_conn)):
    user = conn.execute(
        "SELECT user_id, github_username, email, created_at, password_hash FROM users "
        "WHERE lower(github_username) = lower(%(login)s) OR lower(email) = lower(%(login)s)",
        {"login": body.login}).fetchone()
    if user is None or not check_password(body.password, user.pop("password_hash")):
        raise HTTPException(401, "Wrong username or password")
    return {"token": make_token(user["user_id"]), "user": user}
