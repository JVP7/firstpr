"""Password hashing, JWTs, and the current-user dependency."""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.db import get_conn

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
TOKEN_TTL = timedelta(days=7)

bearer = HTTPBearer(auto_error=False)


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def make_token(user_id):
    exp = datetime.now(timezone.utc) + TOKEN_TTL
    return jwt.encode({"sub": str(user_id), "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), conn=Depends(get_conn)):
    if creds is None:
        raise HTTPException(401, "Not logged in")
    try:
        user_id = int(jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])["sub"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = conn.execute(
        "SELECT user_id, github_username, email, created_at FROM users WHERE user_id = %s",
        (user_id,)).fetchone()
    if user is None:
        raise HTTPException(401, "User no longer exists")
    return user
