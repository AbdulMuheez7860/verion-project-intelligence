from typing import Literal

from fastapi import Query

from app.schemas.repository import AnalysisStatus, RiskLevel

RepositorySortField = Literal[
    "name",
    "health",
    "risk",
    "last_analyzed",
    "open_pull_requests",
    "security",
    "security_findings",
]
SecurityStatusFilter = Literal["good", "warning", "poor", "unavailable"]


class RepositoryListParams:
    def __init__(
        self,
        q: str | None = Query(None, max_length=200, description="Search repository name, owner, or full name."),
        analysis_status: AnalysisStatus | None = Query(None, alias="analysisStatus"),
        risk_level: RiskLevel | None = Query(None, alias="riskLevel"),
        security_status: SecurityStatusFilter | None = Query(None, alias="securityStatus"),
        sort: RepositorySortField = Query("name"),
        order: Literal["asc", "desc"] = Query("asc"),
    ) -> None:
        self.q = q.strip() if q else None
        self.analysis_status = analysis_status
        self.risk_level = risk_level
        self.security_status = security_status
        self.sort = sort
        self.order = order
