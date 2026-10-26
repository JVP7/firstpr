"""Password hashing, session cookie (a revocable JWT), and the current-user dependency."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Request, Response

from api.db import pool
from api.security import login_failures, security_event

JWT_SECRET = os.environ["JWT_SECRET"]
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters")
JWT_ALGORITHM = "HS256"
TOKEN_TTL = timedelta(days=1)
PENDING_TTL = timedelta(minutes=15)
COOKIE = "firstpr_session"
PENDING_COOKIE = "firstpr_github"  # GitHub identity verified by OAuth, waiting for email + password
# Compared against when the login name doesn't exist, so both cases take the same bcrypt time.
DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt()).decode()


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), (password_hash or DUMMY_HASH).encode()) and password_hash is not None


def _cookie(response, name, value, ttl):
    # HttpOnly keeps tokens away from page scripts; SameSite=Lax stops cross-site sends.
    response.set_cookie(name, value, max_age=int(ttl.total_seconds()), httponly=True,
                        secure=True, samesite="lax", path="/")


def _encode(claims, ttl):
    now = datetime.now(timezone.utc)
    return jwt.encode({**claims, "iat": now, "exp": now + ttl}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode(token, purpose):
    claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "purpose"]})
    if claims["purpose"] != purpose:
        raise jwt.InvalidTokenError("wrong purpose")
    return claims


def set_session(response: Response, user_id):
    token = _encode({"sub": str(user_id), "jti": str(uuid.uuid4()), "purpose": "session"}, TOKEN_TTL)
    _cookie(response, COOKIE, token, TOKEN_TTL)


def end_session(request: Request, response: Response):
    """Revoke the current token server-side, then drop the cookie."""
    token = request.cookies.get(COOKIE)
    if token:
        try:
            claims = _decode(token, "session")
            with pool.connection() as conn:
                conn.execute("DELETE FROM revoked_sessions WHERE expires_at < now()")
                conn.execute("INSERT INTO revoked_sessions (jti, expires_at) VALUES (%s, to_timestamp(%s)) "
                             "ON CONFLICT DO NOTHING", (claims["jti"], claims["exp"]))
        except jwt.PyJWTError:
            pass  # already invalid; nothing to revoke
    response.delete_cookie(COOKIE, path="/", httponly=True, secure=True, samesite="lax")


def current_user(request: Request):
    # Uses its own short connection so slow routes (signup import, resync) don't hold one for auth.
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Not logged in")
    try:
        claims = _decode(token, "session")
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Session expired. Log in again.")
    with pool.connection() as conn:
        user = conn.execute(
            "SELECT user_id, github_username, email, created_at FROM users WHERE user_id = %s "
            "AND NOT EXISTS (SELECT 1 FROM revoked_sessions WHERE jti = %s)",
            (user_id, claims.get("jti"))).fetchone()
    if user is None:
        raise HTTPException(401, "Session ended. Log in again.")
    return user


def require_password(request: Request, user, password):
    """Re-authentication for sensitive changes. Failures count toward the same lockout as login."""
    key = f"user:{user['user_id']}"
    if login_failures.blocked(key):
        security_event("login_locked", request, user_id=user["user_id"])
        raise HTTPException(429, "Too many failed attempts. Wait 15 minutes and try again.")
    with pool.connection() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE user_id = %s", (user["user_id"],)).fetchone()
    if not check_password(password, row["password_hash"]):
        login_failures.hit(key)
        security_event("reauth_failed", request, user_id=user["user_id"])
        raise HTTPException(403, "Wrong password")


def set_pending_github(response: Response, login, github_id):
    _cookie(response, PENDING_COOKIE, _encode({"login": login, "gid": github_id, "purpose": "signup"}, PENDING_TTL),
            PENDING_TTL)


def pending_github(request: Request):
    """The GitHub login verified by OAuth for this browser, or None."""
    token = request.cookies.get(PENDING_COOKIE)
    try:
        return _decode(token, "signup")["login"] if token else None
    except (jwt.PyJWTError, KeyError):
        return None


def clear_pending_github(response: Response):
    response.delete_cookie(PENDING_COOKIE, path="/", httponly=True, secure=True, samesite="lax")
