"""Checks for new passwords beyond the character rules in models.py: context words and breaches."""

import hashlib
import logging

import requests

log = logging.getLogger("firstpr.security")

PWNED_RANGE_URL = "https://api.pwnedpasswords.com/range/"
SITE_WORDS = ("starpull", "firstpr")


def context_problem(password, github_username, email):
    """Why the password is built from guessable context, or None."""
    lowered = password.lower()
    words = [("your GitHub username", github_username), ("your email name", email.split("@")[0])]
    words += [("the site name", w) for w in SITE_WORDS]
    for what, word in words:
        if word and len(word) >= 3 and word.lower() in lowered:
            return f"Password can't contain {what}"
    return None


def breach_count(password):
    """How many times this password appears in known breaches (Have I Been Pwned), or None if
    the service can't be reached. Only the first 5 characters of the SHA-1 hash leave the server
    (k-anonymity); the match is done locally."""
    digest = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    try:
        resp = requests.get(PWNED_RANGE_URL + prefix, timeout=5,
                            headers={"Add-Padding": "true", "User-Agent": "starpull-password-check"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("breach_check_unavailable error=%s", type(exc).__name__)
        return None
    for line in resp.text.splitlines():
        candidate, _, count = line.partition(":")
        if candidate == suffix:
            return int(count)  # padding rows have a count of 0
    return 0


def new_password_problem(password, github_username, email):
    """The first reason to reject a new password, or None. Character rules are already checked."""
    problem = context_problem(password, github_username, email)
    if problem:
        return problem
    if breach_count(password):
        return "This password has appeared in a data breach. Choose a different one."
    return None
