from typing import Literal

from app.schemas.analysis_runs import AnalyzerSummary
from app.schemas.common import APIModel


RiskLevel = Literal["low", "medium", "high", "critical"]

AnalysisStatus = Literal[
    "not_started",
    "queued",
    "running",
    "partial",
    "complete",
    "failed",
]

PullRequestStatus = Literal["open", "merged", "closed"]

FindingStatus = Literal[
    "open",
    "acknowledged",
    "false_positive",
    "resolved",
    "suppressed",
]

DependencyStatus = Literal[
    "healthy",
    "outdated",
    "vulnerable",
    "critical",
    # Used for ecosystems where Verion only parses a dependency
    # inventory (Go/Rust/PHP/Ruby) and has no vulnerability database
    # to check against. This is genuinely different from "healthy",
    # which implies a scan confirmed no known vulnerabilities.
    "unknown",
]


class RepositoryResponse(APIModel):
    id: str
    name: str
    owner: str
    language: str | None = None
    health_score: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    dependency_score: float | None = None
    coverage_percent: float | None = None
    open_pull_requests: int = 0
    risk_level: RiskLevel | None = None
    analysis_status: AnalysisStatus = "not_started"
    last_analyzed_at: str | None = None
    github_id: int | None = None
    full_name: str | None = None
    html_url: str | None = None
    default_branch: str | None = None
    private: bool | None = None
    dependency_status: DependencyStatus | None = None
    security_finding_count: int | None = None
    quality_finding_count: int | None = None


class AnalyzeResponse(APIModel):
    status: str


class AnalysisRunResponse(APIModel):
    id: str
    repository_id: str
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
    health_score: float | None = None


class AnalysisRunDetailResponse(AnalysisRunResponse):
    # This uses the shared typed model so analyzer summary fields
    # are correctly camelCased for the frontend.
    analyzer_summary: AnalyzerSummary | None = None

    health_snapshot: dict[str, object] | None = None

    findings_by_category: dict[str, int] | None = None


class RiskFactor(APIModel):
    label: str
    contribution: int
    explanation: str


class RiskScore(APIModel):
    value: int
    level: RiskLevel
    factors: list[RiskFactor]
    engine: str = "Verion Risk Engine v1"


class PullRequestResponse(APIModel):
    id: int
    repository_id: str
    repository_name: str
    title: str
    author: str
    risk_score: int | None = None
    files_changed: int = 0
    coverage_percent: float | None = None
    issues_count: int = 0
    status: PullRequestStatus = "open"
    created_at: str


class PullRequestDetailResponse(PullRequestResponse):
    risk_score_detail: RiskScore | None = None
    description: str | None = None


class RepositoryPullRequestResponse(PullRequestResponse):
    verdict: str
    verdict_label: str
    verdict_reason: str | None = None
    risk_level: RiskLevel | None = None
    updated_at: str | None = None