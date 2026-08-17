from typing import Any
from pydantic import BaseModel, Field


class ReviewStartRequest(BaseModel):
    team_id: int
    phase_id: str = Field(pattern=r"^A[1-6]$")
    mode: str = "guided_review"
    scenario_id: str | None = None
    user_id: int | None = None
    repo_full_name: str | None = None
    focus: str | None = Field(default=None, max_length=500)
    finding_id: str | None = Field(default=None, max_length=160)
    finding_ids: list[str] = Field(default_factory=list, max_length=3)
    entry_intent: str = Field(default="review", pattern=r"^(review|discuss|challenge|resolve|understand|accept_or_defer)$")
    source_view: str = Field(default="studio", max_length=80)


class ReviewResponseRequest(BaseModel):
    response: str = Field(min_length=1, max_length=8000)
    evidence_refs: list[str] = []
    decision: str | None = None
    intent: str = "discuss"
    client_turn_id: str | None = Field(default=None, max_length=120)


class ReviewClarifyRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    client_turn_id: str | None = Field(default=None, max_length=120)


class ReviewCoachRequest(BaseModel):
    decision: str | None = None
    client_turn_id: str | None = Field(default=None, max_length=120)


class EvidenceDisputeRequest(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=4000)
    finding_id: str | None = Field(default=None, max_length=160)


class RepoAnalyzeRequest(BaseModel):
    team_id: int
    phase_id: str = Field(pattern=r"^A[1-6]$")
    repo_full_name: str | None = None


class DevLoginRequest(BaseModel):
    github_login: str = "student-demo"
    display_name: str = "Demo Student"
    role: str = "student"
    team_key: str = "team-01"


class ApiEnvelope(BaseModel):
    data: Any
    meta: dict[str, Any] = {}


class FindingDispositionRequest(BaseModel):
    status: str = Field(pattern=r"^(open|under_discussion|evidence_disputed|confirmed|corrected|resolved|accepted_risk|deferred)$")
    rationale: str = Field(default="", max_length=4000)
    evidence_path: str = Field(default="", max_length=500)
