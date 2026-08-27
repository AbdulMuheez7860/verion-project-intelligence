from app.schemas.common import APIModel
from app.schemas.findings import (
    DependencySummary,
    QualitySummary,
    SecuritySummary,
    SeverityCounts,
)
from app.schemas.repository import (
    AnalysisRunResponse,
    RepositoryResponse,
    RiskLevel,
)


class HealthSnapshot(APIModel):
    health_score: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    dependency_score: float | None = None
    risk_level: RiskLevel | None = None
    severity_counts: SeverityCounts | None = None
    recorded_at: str | None = None


class RepositoryConnectionInfo(APIModel):
    github_status: str
    github_login: str | None = None
    last_synchronized_at: str | None = None
    can_analyze: bool = True
    analyze_blocked_reason: str | None = None


class RepositoryHealthBreakdown(APIModel):
    health_score: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    dependency_score: float | None = None
    pr_risk_average: float | None = None
    risk_level: RiskLevel | None = None
    has_completed_analysis: bool = False
    health_definition: str
    security_definition: str
    quality_definition: str
    dependency_definition: str
    pr_risk_definition: str


class RepositoryRecommendedAction(APIModel):
    id: str
    label: str
    description: str
    priority: str


class RepositoryIntelligenceResponse(APIModel):
    repository: RepositoryResponse
    health: RepositoryHealthBreakdown
    connection: RepositoryConnectionInfo
    latest_analysis: AnalysisRunResponse | None = None
    security_summary: SecuritySummary
    quality_summary: QualitySummary
    dependency_summary: DependencySummary
    recommended_actions: list[RepositoryRecommendedAction] = []


class HealthHistoryPoint(APIModel):
    analysis_id: str
    recorded_at: str | None = None
    health_score: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    dependency_score: float | None = None
    risk_level: RiskLevel | None = None
    severity_counts: SeverityCounts | None = None


class HealthHistoryResponse(APIModel):
    points: list[HealthHistoryPoint]
    has_sufficient_history: bool
    message: str