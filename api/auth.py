"""Password hashing, session cookie (a JWT), and the current-user dependency."""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response

from api.db import get_conn

JWT_SECRET = os.environ["JWT_SECRET"]
if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters")
JWT_ALGORITHM = "HS256"
TOKEN_TTL = timedelta(days=1)
COOKIE = "firstpr_session"
# Compared against when the login name doesn't exist, so both cases take the same bcrypt time.
DUMMY_HASH = bcrypt.hashpw(b"timing-equalizer", bcrypt.gensalt()).decode()


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), (password_hash or DUMMY_HASH).encode()) and password_hash is not None


def set_session(response: Response, user_id):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": str(user_id), "iat": now, "exp": now + TOKEN_TTL}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # HttpOnly keeps the token away from page scripts; SameSite=Lax stops cross-site sends.
    response.set_cookie(COOKIE, token, max_age=int(TOKEN_TTL.total_seconds()), httponly=True,
                        secure=True, samesite="lax", path="/")


def clear_session(response: Response):
    response.delete_cookie(COOKIE, path="/", httponly=True, secure=True, samesite="lax")


def current_user(request: Request, conn=Depends(get_conn)):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Not logged in")
    try:
        user_id = int(jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Session expired. Log in again.")
    user = conn.execute(
        "SELECT user_id, github_username, email, created_at FROM users WHERE user_id = %s",
        (user_id,)).fetchone()
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user


def require_password(conn, user, password):
    """Re-authentication for sensitive changes (email, account deletion)."""
    row = conn.execute("SELECT password_hash FROM users WHERE user_id = %s", (user["user_id"],)).fetchone()
    if not check_password(password, row["password_hash"]):
        raise HTTPException(403, "Wrong password")
