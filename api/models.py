"""Request bodies."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    github_username: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt ignores bytes past 72


class LoginIn(BaseModel):
    login: str  # GitHub username or email
    password: str


class EmailIn(BaseModel):
    email: EmailStr


class SkillIn(BaseModel):
    package_id: int


class SaveIssueIn(BaseModel):
    issue_id: int


class SavedStatusIn(BaseModel):
    status: Literal["working", "pr_submitted", "merged"]


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_repo_id: int | None = None


class TeamMemberIn(BaseModel):
    github_username: str
    role: Literal["owner", "member"] = "member"
