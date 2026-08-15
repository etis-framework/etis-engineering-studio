from typing import Any
from pydantic import BaseModel, Field


class ReviewStartRequest(BaseModel):
    team_id: int
    phase_id: str = Field(pattern=r"^A[1-6]$")
    mode: str = "guided_review"
    scenario_id: str | None = None
    user_id: int | None = None


class ReviewResponseRequest(BaseModel):
    response: str = Field(min_length=1, max_length=8000)
    evidence_refs: list[str] = []
    decision: str | None = None


class RepoAnalyzeRequest(BaseModel):
    team_id: int
    phase_id: str
    repo_full_name: str | None = None


class DevLoginRequest(BaseModel):
    github_login: str = "student-demo"
    display_name: str = "Demo Student"
    role: str = "student"
    team_key: str = "team-01"


class ApiEnvelope(BaseModel):
    data: Any
    meta: dict[str, Any] = {}
