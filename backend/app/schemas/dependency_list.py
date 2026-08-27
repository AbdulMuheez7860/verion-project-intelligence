from typing import Literal

from fastapi import Query

from app.schemas.repository import DependencyStatus

DependencySortField = Literal[
    "package_name",
    "status",
    "current_version",
    "created_at",
    "repository_name",
    "severity",
]
DependencyEcosystem = Literal["python"]


class DependencyListParams:
    def __init__(
        self,
        q: str | None = Query(None, max_length=200, description="Search package, vulnerability, or repository."),
        repository_id: str | None = Query(None, alias="repositoryId"),
        status: DependencyStatus | None = Query(None),
        ecosystem: DependencyEcosystem | None = Query(None),
        severity: str | None = Query(None, description="Filter by vulnerability severity from pip-audit findings."),
        sort: DependencySortField = Query("status"),
        order: Literal["asc", "desc"] = Query("desc"),
    ) -> None:
        self.q = q.strip() if q else None
        self.repository_id = repository_id
        self.status = status
        self.ecosystem = ecosystem
        self.severity = severity
        self.sort = sort
        self.order = order
