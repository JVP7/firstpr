from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import StringConstraints

from api.auth import current_user
from api.db import get_conn, run_file

router = APIRouter(prefix="/issues", tags=["issues"])

# Repeatable ?language=Python&language=TypeScript; empty means every language.
Languages = Annotated[list[Annotated[str, StringConstraints(min_length=1, max_length=40)]], Query(max_length=10)]


@router.get("/matches")
def stack_matches(language: Languages = [], user=Depends(current_user), conn=Depends(get_conn)):
    return run_file(conn, "advanced/stack_match", user_id=user["user_id"], languages=language or None)


@router.get("/by-dependencies")
def by_dependencies(user=Depends(current_user), conn=Depends(get_conn)):
    return run_file(conn, "advanced/issues_by_user_dependencies", user_id=user["user_id"])


@router.get("/search")
def search(q: str | None = Query(None, max_length=100), language: Languages = [], beginner_only: bool = False,
           limit: int = Query(50, ge=1, le=200), conn=Depends(get_conn)):
    return run_file(conn, "advanced/issue_search", q=q or None, languages=language or None,
                    beginner_only=beginner_only, limit=limit)


@router.get("/languages")
def tracked_languages(conn=Depends(get_conn)):
    return run_file(conn, "advanced/tracked_languages")


@router.get("/{issue_id}")
def issue_detail(issue_id: int = Path(ge=1, le=2**63 - 1), conn=Depends(get_conn)):
    issue = conn.execute(
        "SELECT i.issue_id, i.number, i.title, i.state, i.created_at, i.is_assigned, "
        "       r.repo_id, r.full_name, r.primary_language, r.stars, "
        "       'https://github.com/' || r.full_name || '/issues/' || i.number AS url "
        "FROM issues i JOIN repos r ON r.repo_id = i.repo_id WHERE i.issue_id = %s",
        (issue_id,)).fetchone()
    if issue is None:
        raise HTTPException(404, "Issue not found")
    issue["labels"] = [r["name"] for r in conn.execute(
        "SELECT l.name FROM issue_labels il JOIN labels l ON l.label_id = il.label_id "
        "WHERE il.issue_id = %s ORDER BY l.name", (issue_id,))]
    issue["comments"] = conn.execute(
        "SELECT author_login, author_association, created_at FROM comments "
        "WHERE issue_id = %s ORDER BY created_at", (issue_id,)).fetchall()
    issue["repo_packages"] = [r["name"] for r in conn.execute(
        "SELECT p.name FROM repo_dependencies rd JOIN packages p ON p.package_id = rd.package_id "
        "WHERE rd.repo_id = %s ORDER BY p.name", (issue["repo_id"],))]
    return issue
