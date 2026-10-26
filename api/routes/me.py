import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from api.auth import current_user, end_all_sessions, end_session, hash_password, require_password, set_session
from api.db import get_conn, run_file
from api.github_import import import_user_repos
from api.models import DeleteAccountIn, EmailIn, PasswordChangeIn, SkillIn
from api.passwords import new_password_problem
from api.security import resyncs, security_event

router = APIRouter(tags=["me"])


@router.get("/me")
def me(user=Depends(current_user), conn=Depends(get_conn)):
    repos = conn.execute(
        "SELECT r.repo_id, r.full_name, r.primary_language, "
        "       (SELECT count(*) FROM repo_dependencies rd WHERE rd.repo_id = r.repo_id) AS package_count "
        "FROM user_repos ur JOIN repos r ON r.repo_id = ur.repo_id "
        "WHERE ur.user_id = %s ORDER BY r.full_name", (user["user_id"],)).fetchall()
    skills = conn.execute(
        "SELECT p.package_id, p.name, p.ecosystem FROM user_skills us "
        "JOIN packages p ON p.package_id = us.package_id WHERE us.user_id = %s ORDER BY p.name",
        (user["user_id"],)).fetchall()
    return {**user, "repos": repos, "skills": skills}


@router.patch("/me")
def update_email(body: EmailIn, request: Request, user=Depends(current_user), conn=Depends(get_conn)):
    require_password(request, user, body.current_password)
    try:
        [row] = run_file(conn, "basic/user_update_email", user_id=user["user_id"], email=body.email)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "That email is already registered")
    security_event("email_changed", request, user_id=user["user_id"])
    return row


@router.patch("/me/password", status_code=204)
def change_password(body: PasswordChangeIn, request: Request, response: Response,
                    user=Depends(current_user), conn=Depends(get_conn)):
    require_password(request, user, body.current_password)  # first, so the checks below can't be probed
    problem = new_password_problem(body.new_password, user["github_username"], user["email"])
    if problem:
        raise HTTPException(422, problem)
    conn.execute("UPDATE users SET password_hash = %s, sessions_valid_after = now() WHERE user_id = %s",
                 (hash_password(body.new_password), user["user_id"]))
    conn.commit()
    security_event("password_changed", request, user_id=user["user_id"])
    # Every other device is signed out by the reset above; keep this one signed in.
    set_session(response, user["user_id"])


@router.post("/me/sessions/end-all", status_code=204)
def sign_out_everywhere(request: Request, response: Response, user=Depends(current_user)):
    end_all_sessions(user["user_id"])
    security_event("sessions_ended", request, user_id=user["user_id"])
    end_session(request, response)


@router.delete("/me", status_code=204)
def delete_me(body: DeleteAccountIn, request: Request, response: Response,
              user=Depends(current_user), conn=Depends(get_conn)):
    if body.confirm_username.lower() != user["github_username"].lower():
        raise HTTPException(422, "Type your GitHub username exactly to confirm")
    require_password(request, user, body.current_password)
    run_file(conn, "basic/user_delete", user_id=user["user_id"])
    security_event("account_deleted", request, user_id=user["user_id"])
    end_session(request, response)


@router.post("/me/sync")
def resync_repos(request: Request, user=Depends(current_user)):
    resyncs.check(user["user_id"], request)
    return {"imported_repos": import_user_repos(user["user_id"], user["github_username"])}


@router.get("/packages")
def search_packages(q: str = Query(min_length=1, max_length=100), limit: int = Query(20, ge=1, le=50),
                    conn=Depends(get_conn)):
    pattern = q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
    return conn.execute(
        "SELECT package_id, name, ecosystem FROM packages WHERE name ILIKE %s "
        "ORDER BY length(name), name LIMIT %s", (pattern, limit)).fetchall()


@router.post("/me/skills", status_code=201)
def add_skill(body: SkillIn, user=Depends(current_user), conn=Depends(get_conn)):
    try:
        run_file(conn, "basic/skill_add", user_id=user["user_id"], package_id=body.package_id)
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(404, "Unknown package")
    return {"package_id": body.package_id}


@router.delete("/me/skills/{package_id}", status_code=204)
def remove_skill(package_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    if not run_file(conn, "basic/skill_remove", user_id=user["user_id"], package_id=package_id):
        raise HTTPException(404, "Not one of your skills")
