from datetime import UTC, datetime
from typing import Literal

from app.schemas.common import APIModel
from app.schemas.findings import SeverityCounts
from app.schemas.repository import PullRequestResponse, RiskLevel


class DashboardMetrics(APIModel):
    repository_health: float | None = None
    pr_risk: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    test_coverage_percent: float | None = None
    has_analysis_data: bool = False
    connected_repositories: int = 0


class RepositoryHealthItem(APIModel):
    id: str
    name: str
    health_score: float | None = None


class HighRiskChange(APIModel):
    repository_name: str
    pull_request_id: int
    pull_request_title: str
    risk_score: int
    findings_count: int


class AttentionItem(APIModel):
    id: str
    title: str
    description: str
    severity: RiskLevel
    href: str
    created_at: str
    entity_type: str | None = None
    repository_id: str | None = None
    repository_name: str | None = None
    action_label: str | None = None


class DashboardResponse(APIModel):
    metrics: DashboardMetrics
    attention_items: list[AttentionItem]
    recent_pull_requests: list[PullRequestResponse]
    repository_health_items: list[RepositoryHealthItem] = []
    high_risk_changes: list[HighRiskChange] = []
    security_severity_counts: SeverityCounts | None = None


OverviewStatus = Literal["healthy", "warning", "critical", "neutral", "unavailable"]


class OverviewMetric(APIModel):
    key: str
    label: str
    value: int | float | str | None
    definition: str
    href: str | None = None
    status: OverviewStatus = "neutral"


class HealthDimension(APIModel):
    key: str
    label: str
    score: float | None
    definition: str


class EngineeringHealth(APIModel):
    score: float | None
    level: RiskLevel | Literal["unavailable"] | None = None
    definition: str
    dimensions: list[HealthDimension] = []
    factors: list[str] = []


PRVerdict = Literal[
    "safe_to_merge",
    "review_recommended",
    "high_risk",
    "critical_risk",
    "analysis_unavailable",
]


class RepositoryDashboardItem(APIModel):
    id: str
    name: str
    health_score: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    dependency_score: float | None = None
    open_pull_requests: int = 0
    analysis_status: str
    last_analyzed_at: str | None = None
    risk_level: RiskLevel | None = None


class PullRequestDashboardItem(APIModel):
    id: int
    repository_id: str
    repository_name: str
    title: str
    risk_score: int | None = None
    risk_level: RiskLevel | None = None
    verdict: PRVerdict
    verdict_label: str
    verdict_reason: str | None = None
    updated_at: str | None = None
    status: str
    issues_count: int = 0


class PullRequestSection(APIModel):
    high_risk: list[PullRequestDashboardItem] = []
    awaiting_analysis: list[PullRequestDashboardItem] = []
    recently_analyzed: list[PullRequestDashboardItem] = []


class SecurityOverview(APIModel):
    severity_counts: SeverityCounts | None = None
    total: int = 0
    has_data: bool = False


class AnalysisActivityItem(APIModel):
    id: str
    repository_id: str
    repository_name: str
    commit_sha: str | None = None
    trigger_source: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: int | None = None
    status: str
    error: str | None = None
    finding_count: int = 0
    health_score: float | None = None
    href: str


class RiskDistributionBucket(APIModel):
    key: str
    label: str
    count: int


class RiskDistribution(APIModel):
    buckets: list[RiskDistributionBucket]
    total: int
    has_data: bool


class TrendsSection(APIModel):
    available: bool = False
    message: str
    direction: Literal["improving", "declining", "stable", "unavailable"] = "unavailable"
    completed_analyses_count: int = 0


class RecommendedAction(APIModel):
    id: str
    label: str
    description: str
    href: str
    priority: Literal["high", "medium", "low"] = "medium"


class DashboardSummaryResponse(APIModel):
    generated_at: str
    has_active_analysis: bool = False
    has_analysis_data: bool = False
    overview: list[OverviewMetric]
    health: EngineeringHealth
    attention: list[AttentionItem]
    repositories: list[RepositoryDashboardItem]
    pull_requests: PullRequestSection
    security: SecurityOverview
    analysis_activity: list[AnalysisActivityItem]
    risk_distribution: RiskDistribution
    trends: TrendsSection
    recommended_actions: list[RecommendedAction] = []
