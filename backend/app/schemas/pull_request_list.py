from typing import Literal

from fastapi import Query

from app.schemas.dashboard import PRVerdict
from app.schemas.repository import PullRequestStatus, RiskLevel

PullRequestSortField = Literal["risk_score", "updated_at", "created_at", "repository_name", "number"]
PRVerdictFilter = PRVerdict


class PullRequestListParams:
    def __init__(
        self,
        q: str | None = Query(None, max_length=200, description="Search PR number, title, repository, or author."),
        repository_id: str | None = Query(None, alias="repositoryId"),
        status: PullRequestStatus | None = Query(None),
        risk_level: RiskLevel | None = Query(None, alias="riskLevel"),
        verdict: PRVerdictFilter | None = Query(None),
        author: str | None = Query(None, max_length=100),
        sort: PullRequestSortField = Query("updated_at"),
        order: Literal["asc", "desc"] = Query("desc"),
    ) -> None:
        self.q = q.strip() if q else None
        self.repository_id = repository_id
        self.status = status
        self.risk_level = risk_level
        self.verdict = verdict
        self.author = author.strip() if author else None
        self.sort = sort
        self.order = order
