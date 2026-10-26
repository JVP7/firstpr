"""Rate limiting, CSRF origin check, security headers, and security event logging."""

import logging
import os

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from api.db import pool

log = logging.getLogger("firstpr.security")

ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    # The old XSS auditor is removed from browsers and could be abused; OWASP says turn it off.
    "X-XSS-Protection": "0",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # The API only returns JSON, so nothing may load or frame it.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))


def client_ip(request: Request):
    # Clients can prepend fake X-Forwarded-For entries, so count back from the end: each trusted
    # proxy (Vercel rewrite, Render) appends one hop. 0 hops = direct connection (local dev).
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if PROXY_HOPS and len(hops) >= PROXY_HOPS:
        return hops[-PROXY_HOPS]
    return request.client.host if request.client else "unknown"


def security_event(event, request: Request, **fields):
    """Log a security event. Never pass passwords, tokens, or cookies here."""
    log.warning("%s ip=%s %s", event, client_ip(request),
                " ".join(f"{k}={v}" for k, v in fields.items()))


class RateLimiter:
    """Sliding-window counter per subject (an IP, user or login name), stored in Postgres so
    limits survive deploys and are shared across instances. Each call uses its own short
    connection, so a hit is recorded even when the request that caused it fails and rolls back."""

    def __init__(self, name, limit, window_seconds):
        self.name, self.limit, self.window = name, limit, window_seconds

    def blocked(self, subject):
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT count(*) AS n FROM rate_limit_hits "
                "WHERE limiter = %s AND subject = %s AND at > now() - make_interval(secs => %s)",
                (self.name, str(subject), self.window)).fetchone()
        return row["n"] >= self.limit

    def hit(self, subject):
        with pool.connection() as conn:
            conn.execute("INSERT INTO rate_limit_hits (limiter, subject) VALUES (%s, %s)", (self.name, str(subject)))
            # Keep the table small: drop this subject's hits that fell out of the window.
            conn.execute("DELETE FROM rate_limit_hits WHERE limiter = %s AND subject = %s "
                         "AND at <= now() - make_interval(secs => %s)", (self.name, str(subject), self.window))

    def reset(self, subject):
        with pool.connection() as conn:
            conn.execute("DELETE FROM rate_limit_hits WHERE limiter = %s AND subject = %s", (self.name, str(subject)))

    def check(self, subject, request: Request):
        """Count one request and raise 429 once the subject is over its limit."""
        if self.blocked(subject):
            security_event("rate_limited", request, limit=self.name)
            raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")
        self.hit(subject)


login_failures = RateLimiter("login_fail", limit=5, window_seconds=15 * 60)  # per account: lockout
auth_requests = RateLimiter("auth", limit=30, window_seconds=15 * 60)        # per IP: login + signup
signups = RateLimiter("signup", limit=5, window_seconds=60 * 60)             # per IP: each signup calls GitHub ~40 times
resyncs = RateLimiter("resync", limit=3, window_seconds=60 * 60)             # per user


async def security_middleware(request: Request, call_next):
    # CSRF: browsers always send Origin on cross-site unsafe requests, so reject unknown ones.
    origin = request.headers.get("origin")
    if request.method in UNSAFE_METHODS and origin and origin not in ALLOWED_ORIGINS:
        security_event("csrf_rejected", request, origin=origin, path=request.url.path)
        response = JSONResponse({"detail": "Cross-site request rejected"}, status_code=403)
    else:
        response = await call_next(request)
    for name, value in HEADERS.items():
        response.headers.setdefault(name, value)
    return response
