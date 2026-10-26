"""Request bodies."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupIn(BaseModel):
    # The GitHub username is not here: it comes from the OAuth-verified cookie.
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, v):
        # bcrypt silently ignores bytes past 72, and non-ASCII characters take several bytes.
        if len(v.encode()) > 72:
            raise ValueError("Password is too long (72 bytes max)")
        return v


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=254)  # GitHub username or email
    password: str = Field(min_length=1, max_length=200)


class EmailIn(BaseModel):
    email: EmailStr
    current_password: str = Field(max_length=200)


class PasswordConfirmIn(BaseModel):
    current_password: str = Field(max_length=200)


class SkillIn(BaseModel):
    package_id: int = Field(ge=1, le=2**31 - 1)


class SaveIssueIn(BaseModel):
    issue_id: int = Field(ge=1, le=2**63 - 1)


class SavedStatusIn(BaseModel):
    status: Literal["working", "pr_submitted", "merged"]


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_repo_id: int | None = Field(None, ge=1, le=2**63 - 1)


class TeamMemberIn(BaseModel):
    github_username: str = Field(min_length=1, max_length=39)
    role: Literal["owner", "member"] = "member"
