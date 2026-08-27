from app.schemas.common import APIModel


class AnalyticsBaseline(APIModel):
    available: bool = False
    snapshot_count: int = 0
    status: str = "building"
    first_captured_at: str | None = None
    last_captured_at: str | None = None
    message: str | None = None


class HistoricalFreshness(APIModel):
    last_snapshot_at: str | None = None
    last_analysis_at: str | None = None
    stale_repositories: list[str] = []
    never_analyzed_repositories: list[str] = []


class HistoricalChange(APIModel):
    metric: str
    label: str
    current: float | int | None = None
    previous: float | int | None = None
    delta: float | None = None
    percentage_change: float | None = None
    direction: str = "unavailable"
    interpretation: str = ""
    available: bool = False
    repository_id: str | None = None
    repository_name: str | None = None
    detected_at: str | None = None


class AnalyticsTrendPoint(APIModel):
    captured_at: str
    repository_id: str
    repository_name: str = ""
    health_score: float | None = None
    security_score: float | None = None
    quality_score: float | None = None
    dependency_score: float | None = None
    pr_risk_score: float | None = None
    finding_total: int | None = None
    finding_critical: int | None = None
    finding_high: int | None = None
    finding_medium: int | None = None
    finding_low: int | None = None


class AnalyticsRepositoryComparison(APIModel):
    id: str
    name: str
    health_score: float | None = None
    security_score: float | None = None
    quality_score: float | None = None
    dependency_score: float | None = None
    pr_risk_score: float | None = None
    trend_direction: str = "unavailable"
    last_analyzed_at: str | None = None
    last_snapshot_at: str | None = None
    snapshot_count: int = 0
    health_comparison: HistoricalChange | None = None
    security_comparison: HistoricalChange | None = None
    quality_comparison: HistoricalChange | None = None
    dependency_comparison: HistoricalChange | None = None
    critical_findings_comparison: HistoricalChange | None = None


class AnalyticsRepositoryOption(APIModel):
    id: str
    name: str
    snapshot_count: int = 0


class AnalyticsOverviewResponse(APIModel):
    baseline: AnalyticsBaseline
    freshness: HistoricalFreshness
    health_trend: list[dict] = []
    security_trend: list[dict] = []
    quality_trend: list[dict] = []
    dependency_trend: list[dict] = []
    risk_trend: list[dict] = []
    finding_trend: list[dict] = []
    repository_comparisons: list[AnalyticsRepositoryComparison] = []
    regressions: list[HistoricalChange] = []
    improvements: list[HistoricalChange] = []
    repository_options: list[AnalyticsRepositoryOption] = []
    range_days: int = 90
