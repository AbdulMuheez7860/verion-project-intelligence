from typing import Literal

from app.schemas.common import APIModel

AnalysisRunStatusFilter = Literal["queued", "running", "complete", "failed"]
AnalysisRunTriggerFilter = Literal["manual", "webhook", "scheduled"]
AnalysisRunSortField = Literal["started", "completed", "duration", "status"]


class AnalyzerSkippedItem(APIModel):
    name: str
    reason: str


class AnalyzerFailedItem(APIModel):
    name: str
    reason: str


class LanguageBreakdown(APIModel):
    files: int
    code_loc: int
    comment_loc: int
    blank_loc: int
    total_loc: int


class RepositoryMetricsSummary(APIModel):
    """
    Real, locally computed repository/LOC/language metrics.

    Deliberately does NOT include complexity, duplication, or
    maintainability - those are not computed anywhere in Verion and
    must not be fabricated. See `methodology` for exactly what these
    numbers do and do not represent.
    """

    total_files: int
    source_files: int
    test_files: int
    config_files: int
    documentation_files: int
    other_files: int
    repository_size_bytes: int
    total_loc: int
    code_loc: int
    comment_loc: int
    blank_loc: int
    comment_to_code_ratio: float | None = None
    test_to_source_ratio: float | None = None
    truncated: bool = False
    language_distribution: dict[str, LanguageBreakdown] = {}
    methodology: str


class AnalyzerSummary(APIModel):
    executed: list[str] = []
    skipped: list[AnalyzerSkippedItem] = []
    failed: list[AnalyzerFailedItem] = []
    dependency_scan: bool = False
    repository_metrics: RepositoryMetricsSummary | None = None
    repository_metrics_status: str = "failed"
    repository_metrics_error: str | None = None


class AnalysisRunSnapshotSummary(APIModel):
    id: str
    captured_at: str | None = None
    health_score: float | None = None
    security_score: float | None = None
    quality_score: float | None = None
    dependency_score: float | None = None
    pr_risk_score: float | None = None


class AnalysisRunCapabilities(APIModel):
    can_retry: bool = False
    can_cancel: bool = False


class AnalysisRunListItem(APIModel):
    id: str
    repository_id: str
    repository_name: str
    status: str
    trigger: str
    trigger_source: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: int | None = None
    finding_count: int = 0
    health_score: float | None = None
    error: str | None = None
    created_at: str | None = None


class AnalysisRunDetailResponse(APIModel):
    id: str
    repository_id: str
    repository_name: str
    status: str
    trigger: str
    trigger_source: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: int | None = None
    finding_count: int = 0
    error: str | None = None
    created_at: str | None = None
    analyzer_summary: AnalyzerSummary | None = None
    health_snapshot: dict[str, object] | None = None
    findings_by_category: dict[str, int] | None = None
    snapshot: AnalysisRunSnapshotSummary | None = None
    capabilities: AnalysisRunCapabilities
    repository_href: str
    analytics_href: str | None = None


class AnalysisRunActionResponse(APIModel):
    status: str
    analysis_run_id: str | None = None
    message: str | None = None
