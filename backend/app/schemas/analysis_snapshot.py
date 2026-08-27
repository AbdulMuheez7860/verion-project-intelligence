from app.schemas.common import APIModel


class SeverityBreakdown(APIModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class DependencyCountBreakdown(APIModel):
    total: int = 0
    vulnerable: int = 0
    outdated: int = 0
    healthy: int = 0


class PullRequestMetrics(APIModel):
    open: int = 0
    high_risk: int = 0
    critical_risk: int = 0
    average_risk_score: float | None = None


class AnalysisSnapshotDocument(APIModel):
    id: str
    organization_id: str
    repository_id: str
    analysis_run_id: str
    commit_sha: str | None = None
    branch: str | None = None
    captured_at: str
    health_score: float | None = None
    security_score: float | None = None
    quality_score: float | None = None
    dependency_score: float | None = None
    pr_risk_score: float | None = None
    finding_counts: SeverityBreakdown | None = None
    security_findings: SeverityBreakdown | None = None
    quality_findings: SeverityBreakdown | None = None
    dependency_findings: SeverityBreakdown | None = None
    dependency_counts: DependencyCountBreakdown | None = None
    pull_request_metrics: PullRequestMetrics | None = None
    analyzer_summary: dict | None = None
    created_at: str | None = None
