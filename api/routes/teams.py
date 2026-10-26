import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.auth import current_user
from api.db import get_conn, run_file
from api.models import TeamIn, TeamMemberIn

router = APIRouter(prefix="/teams", tags=["teams"])


def _role(conn, team_id, user_id):
    row = conn.execute("SELECT role FROM team_members WHERE team_id = %s AND user_id = %s",
                       (team_id, user_id)).fetchone()
    if row is None:
        raise HTTPException(404, "Team not found")
    return row["role"]


def _require_owner(conn, team_id, user_id):
    if _role(conn, team_id, user_id) != "owner":
        raise HTTPException(403, "Only team owners can do that")


@router.get("")
def my_teams(user=Depends(current_user), conn=Depends(get_conn)):
    return conn.execute(
        "SELECT t.team_id, t.name, t.target_repo_id, tm.role, "
        "       (SELECT count(*) FROM team_members x WHERE x.team_id = t.team_id) AS member_count "
        "FROM team_members tm JOIN teams t ON t.team_id = tm.team_id "
        "WHERE tm.user_id = %s ORDER BY t.name", (user["user_id"],)).fetchall()


@router.post("", status_code=201)
def create_team(body: TeamIn, user=Depends(current_user), conn=Depends(get_conn)):
    try:
        [team] = run_file(conn, "basic/team_insert", name=body.name, created_by=user["user_id"],
                          target_repo_id=body.target_repo_id)
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(404, "Unknown target repo")
    run_file(conn, "basic/team_member_add", team_id=team["team_id"], user_id=user["user_id"], role="owner")
    return team


@router.get("/{team_id}")
def team_detail(team_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    _role(conn, team_id, user["user_id"])
    team = conn.execute("SELECT team_id, name, created_by, target_repo_id FROM teams WHERE team_id = %s",
                        (team_id,)).fetchone()
    team["members"] = conn.execute(
        "SELECT u.user_id, u.github_username, tm.role FROM team_members tm "
        "JOIN users u ON u.user_id = tm.user_id WHERE tm.team_id = %s ORDER BY u.github_username",
        (team_id,)).fetchall()
    return team


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    _require_owner(conn, team_id, user["user_id"])
    run_file(conn, "basic/team_delete", team_id=team_id)


@router.post("/{team_id}/members", status_code=201)
def add_member(team_id: int, body: TeamMemberIn, user=Depends(current_user), conn=Depends(get_conn)):
    _require_owner(conn, team_id, user["user_id"])
    member = conn.execute("SELECT user_id FROM users WHERE lower(github_username) = lower(%s)",
                          (body.github_username,)).fetchone()
    if member is None:
        raise HTTPException(404, "No Starpull user with that GitHub username")
    rows = run_file(conn, "basic/team_member_add", team_id=team_id, user_id=member["user_id"], role=body.role)
    if not rows:
        raise HTTPException(409, "Already on the team")
    return rows[0]


@router.delete("/{team_id}/members/{user_id}", status_code=204)
def remove_member(team_id: int, user_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    if user_id != user["user_id"]:
        _require_owner(conn, team_id, user["user_id"])
    if not run_file(conn, "basic/team_member_remove", team_id=team_id, user_id=user_id):
        raise HTTPException(404, "Not a member")


@router.get("/{team_id}/saved")
def team_saved(team_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    _role(conn, team_id, user["user_id"])
    return run_file(conn, "advanced/team_saved_issues", team_id=team_id)
