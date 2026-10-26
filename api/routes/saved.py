import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.auth import current_user
from api.db import get_conn, run_file
from api.models import SavedStatusIn, SaveIssueIn

router = APIRouter(prefix="/saved", tags=["saved"])


@router.get("")
def list_saved(user=Depends(current_user), conn=Depends(get_conn)):
    return conn.execute(
        "SELECT si.issue_id, si.status, si.saved_at, i.number, i.title, i.state, r.full_name "
        "FROM saved_issues si JOIN issues i ON i.issue_id = si.issue_id "
        "JOIN repos r ON r.repo_id = i.repo_id WHERE si.user_id = %s ORDER BY si.saved_at DESC",
        (user["user_id"],)).fetchall()


@router.post("", status_code=201)
def save_issue(body: SaveIssueIn, user=Depends(current_user), conn=Depends(get_conn)):
    try:
        [row] = run_file(conn, "basic/saved_issue_insert", user_id=user["user_id"], issue_id=body.issue_id)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "Already saved")
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(404, "Issue not found")
    return row


@router.patch("/{issue_id}")
def update_status(issue_id: int, body: SavedStatusIn, user=Depends(current_user), conn=Depends(get_conn)):
    rows = run_file(conn, "basic/saved_issue_update_status",
                    user_id=user["user_id"], issue_id=issue_id, status=body.status)
    if not rows:
        raise HTTPException(404, "Not in your saved issues")
    return rows[0]


@router.delete("/{issue_id}", status_code=204)
def unsave(issue_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    if not run_file(conn, "basic/saved_issue_delete", user_id=user["user_id"], issue_id=issue_id):
        raise HTTPException(404, "Not in your saved issues")
