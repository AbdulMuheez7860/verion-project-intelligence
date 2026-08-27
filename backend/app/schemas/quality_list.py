from typing import Literal

from fastapi import Query

from app.schemas.repository import FindingStatus, RiskLevel

QualitySortField = Literal["severity", "created_at", "updated_at", "file", "title", "rule_id", "repository_name"]


class QualityListParams:
    def __init__(
        self,
        q: str | None = Query(None, max_length=200, description="Search title, file, rule, or repository."),
        repository_id: str | None = Query(None, alias="repositoryId"),
        severity: RiskLevel | None = Query(None),
        status: FindingStatus | None = Query(None),
        rule_id: str | None = Query(None, alias="ruleId", max_length=200),
        sort: QualitySortField = Query("severity"),
        order: Literal["asc", "desc"] = Query("desc"),
    ) -> None:
        self.q = q.strip() if q else None
        self.repository_id = repository_id
        self.severity = severity
        self.status = status
        self.rule_id = rule_id.strip() if rule_id else None
        self.sort = sort
        self.order = order
