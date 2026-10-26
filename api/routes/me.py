import psycopg
from fastapi import APIRouter, Depends, HTTPException

from api.auth import current_user
from api.db import get_conn, run_file
from api.github_import import import_user_repos
from api.models import EmailIn, SkillIn

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
def update_email(body: EmailIn, user=Depends(current_user), conn=Depends(get_conn)):
    try:
        [row] = run_file(conn, "basic/user_update_email", user_id=user["user_id"], email=body.email)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "That email is already registered")
    return row


@router.delete("/me", status_code=204)
def delete_me(user=Depends(current_user), conn=Depends(get_conn)):
    run_file(conn, "basic/user_delete", user_id=user["user_id"])


@router.post("/me/sync")
def resync_repos(user=Depends(current_user), conn=Depends(get_conn)):
    return {"imported_repos": import_user_repos(conn, user["user_id"], user["github_username"])}


@router.get("/packages")
def search_packages(q: str, limit: int = 20, conn=Depends(get_conn)):
    return conn.execute(
        "SELECT package_id, name, ecosystem FROM packages WHERE name ILIKE %s "
        "ORDER BY length(name), name LIMIT %s", (q.replace("%", r"\%") + "%", min(limit, 50))).fetchall()


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
