"""Thin GitHub REST client: auth, Link-header pagination, and rate limiting."""

import base64
import logging
import os
import time

import requests

API = "https://api.github.com"
log = logging.getLogger(__name__)


class GitHubClient:
    # Pause when the core quota drops below this many requests.
    LOW_REMAINING = 50
    # Search API: 30 requests per minute, at most 1,000 results per query.
    SEARCH_INTERVAL = 60 / 30
    SEARCH_MAX_RESULTS = 1000

    def __init__(self, token=None):
        token = token or os.getenv("GITHUB_TOKEN")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "firstpr-ingest",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            log.warning("GITHUB_TOKEN not set; using the unauthenticated limit of 60 requests/hour")
        self._last_search = 0.0

    def get(self, url, params=None):
        """GET one page. Returns the response, or None on 404."""
        if not url.startswith("http"):
            url = API + url
        while True:
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code in (403, 429) and self._is_rate_limited(resp):
                self._sleep_for_limit(resp)
                continue
            if resp.status_code >= 500:
                log.warning("GitHub %s on %s; retrying in 5s", resp.status_code, url)
                time.sleep(5)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            self._throttle(resp)
            return resp

    def paginate(self, path, params=None, max_pages=None):
        """Yield items across pages by following the Link rel="next" header."""
        params = {"per_page": 100, **(params or {})}
        url, pages = path, 0
        while url:
            resp = self.get(url, params)
            if resp is None:
                return
            data = resp.json()
            yield from data["items"] if isinstance(data, dict) and "items" in data else data
            pages += 1
            if max_pages and pages >= max_pages:
                return
            url = resp.links.get("next", {}).get("url")
            params = None  # the next URL already carries the query string

    def search(self, kind, query, **params):
        """Yield search results (kind: 'issues', 'repositories', ...) under the search throttle."""
        url = f"/search/{kind}"
        params = {"q": query, "per_page": 100, **params}
        fetched = 0
        while url and fetched < self.SEARCH_MAX_RESULTS:
            wait = self._last_search + self.SEARCH_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_search = time.monotonic()
            resp = self.get(url, params)
            if resp is None:
                return
            items = resp.json()["items"]
            yield from items[: self.SEARCH_MAX_RESULTS - fetched]
            fetched += len(items)
            url, params = resp.links.get("next", {}).get("url"), None

    def get_file(self, full_name, path):
        """Return a file's decoded text from the default branch, or None if it doesn't exist."""
        resp = self.get(f"/repos/{full_name}/contents/{path}")
        if resp is None:
            return None
        body = resp.json()
        if isinstance(body, list) or body.get("encoding") != "base64":
            return None  # a directory, or a file too large for the contents endpoint
        return base64.b64decode(body["content"]).decode("utf-8", errors="replace")

    @staticmethod
    def _is_rate_limited(resp):
        return (resp.headers.get("X-RateLimit-Remaining") == "0"
                or "Retry-After" in resp.headers
                or "rate limit" in resp.text.lower())

    def _sleep_for_limit(self, resp):
        if "Retry-After" in resp.headers:
            wait = int(resp.headers["Retry-After"])
        else:
            wait = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60)) - time.time()
        wait = max(wait, 1) + 1
        log.warning("Rate limited; sleeping %.0fs", wait)
        time.sleep(wait)

    def _throttle(self, resp):
        remaining = resp.headers.get("X-RateLimit-Remaining")
        limit = int(resp.headers.get("X-RateLimit-Limit", 5000))
        if remaining is not None and int(remaining) < min(self.LOW_REMAINING, limit // 10):
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time()))
            wait = max(reset - time.time(), 0) + 1
            log.warning("%s requests left in %s quota; sleeping %.0fs until reset",
                        remaining, resp.headers.get("X-RateLimit-Resource", "core"), wait)
            time.sleep(wait)
