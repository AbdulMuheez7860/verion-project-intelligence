from typing import Literal

from app.schemas.common import APIModel

FindingCategory = Literal["security", "quality", "dependency", "secret"]
FindingSeverity = Literal["critical", "high", "medium", "low"]
FindingStatus = Literal["open", "acknowledged", "false_positive", "resolved", "suppressed"]
AnalysisRunStatus = Literal["queued", "running", "complete", "failed"]


class FindingDocument(APIModel):
    id: str
    repository_id: str
    analysis_id: str
    severity: FindingSeverity
    category: FindingCategory
    rule_id: str
    title: str
    description: str | None = None
    file: str
    line: int
    confidence: float | None = None
    remediation: str | None = None
    status: FindingStatus = "open"


class AnalysisRunDocument(APIModel):
    id: str
    repository_id: str
    organization_id: str
    status: AnalysisRunStatus
    trigger: str
    started_at: str | None = None
    completed_at: str | None = None
    finding_count: int = 0
    error: str | None = None
