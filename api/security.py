"""Rate limiting, CSRF origin check, security headers, and security event logging."""

import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("firstpr.security")

ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o]
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
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
    """Sliding-window counter per key.

    shortcut: in-memory, so limits are per process and reset on deploy; move to Postgres or Redis
    if the API runs more than one instance.
    """

    def __init__(self, limit, window_seconds):
        self.limit, self.window = limit, window_seconds
        self.hits = defaultdict(deque)
        self.lock = Lock()

    def _recent(self, key, now):
        hits = self.hits[key]
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        return hits

    def blocked(self, key):
        with self.lock:
            return len(self._recent(key, time.monotonic())) >= self.limit

    def hit(self, key):
        with self.lock:
            now = time.monotonic()
            self._recent(key, now).append(now)

    def reset(self, key):
        with self.lock:
            self.hits.pop(key, None)

    def check(self, key, request: Request, event):
        """Count one request and raise 429 once the key is over its limit."""
        if self.blocked(key):
            security_event("rate_limited", request, limit=event)
            raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")
        self.hit(key)


login_failures = RateLimiter(limit=5, window_seconds=15 * 60)    # per account: lockout
auth_requests = RateLimiter(limit=30, window_seconds=15 * 60)    # per IP: login + signup
signups = RateLimiter(limit=5, window_seconds=60 * 60)           # per IP: each signup calls GitHub ~40 times
resyncs = RateLimiter(limit=3, window_seconds=60 * 60)           # per user


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
