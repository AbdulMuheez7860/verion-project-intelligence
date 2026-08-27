from app.schemas.common import APIModel


class AnalyticsSummary(APIModel):
    range: str = "30d"
    pr_throughput: int | None = None
    merge_frequency_per_day: float | None = None
    median_review_time_hours: float | None = None
    average_pr_size: int | None = None
    average_risk: float | None = None
    has_analysis_data: bool = False
    current_health: float | None = None
    current_security: float | None = None
    current_quality: float | None = None
    current_pr_risk: float | None = None
    trend_direction: str = "unavailable"
    analysis_runs_count: int = 0
    message: str | None = None
