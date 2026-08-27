from app.schemas.common import APIModel
from app.schemas.findings import QualityFindingResponse, SecurityFindingResponse, SeverityCounts
from app.schemas.repository import RiskLevel, RiskScore


class PRFreshness(APIModel):
    status: str
    label: str
    detail: str | None = None
    risk_scored_at: str | None = None
    pr_updated_at: str | None = None
    repository_last_analyzed_at: str | None = None
    is_stale: bool = False


class MergeSafetyVerdict(APIModel):
    key: str
    label: str
    headline: str
    explanation: str | None = None
    risk_score: int | None = None
    risk_level: RiskLevel | None = None


class PRImpactCounts(APIModel):
    security: int = 0
    quality: int = 0
    dependency: int = 0
    total: int = 0


class ChangedFileItem(APIModel):
    path: str
    status: str
    additions: int = 0
    deletions: int = 0
    category: str | None = None


class AffectedArea(APIModel):
    key: str
    label: str
    file_count: int = 0
    finding_count: int = 0


class PRRecommendation(APIModel):
    id: str
    label: str
    description: str
    priority: str


class RepositoryHealthContext(APIModel):
    repository_id: str
    repository_name: str
    health_score: float | None = None
    security_score: float | None = None
    code_quality_score: float | None = None
    risk_level: RiskLevel | None = None
    analysis_status: str
    last_analyzed_at: str | None = None


class PRAnalysisInfo(APIModel):
    status: str
    repository_analysis_status: str | None = None
    risk_scored_at: str | None = None
    head_sha: str | None = None
    base_sha: str | None = None


class PullRequestListItem(APIModel):
    id: int
    number: int | None = None
    repository_id: str
    repository_name: str
    title: str
    author: str
    status: str
    draft: bool = False
    risk_score: int | None = None
    risk_level: RiskLevel | None = None
    verdict: str
    verdict_label: str
    security_impact: int = 0
    quality_impact: int = 0
    dependency_impact: int = 0
    files_changed: int = 0
    issues_count: int = 0
    risk_scored_at: str | None = None
    updated_at: str | None = None
    created_at: str
    html_url: str | None = None


class PullRequestIntelligenceResponse(APIModel):
    id: int
    number: int | None = None
    title: str
    repository_id: str
    repository_name: str
    author: str
    status: str
    draft: bool = False
    description: str | None = None
    html_url: str | None = None
    created_at: str
    updated_at: str | None = None
    merge_safety: MergeSafetyVerdict
    freshness: PRFreshness
    risk_score_detail: RiskScore | None = None
    security_summary: SeverityCounts
    security_findings: list[SecurityFindingResponse]
    quality_findings: list[QualityFindingResponse]
    dependency_findings: list[SecurityFindingResponse]
    impact_counts: PRImpactCounts
    changed_files: list[ChangedFileItem]
    affected_areas: list[AffectedArea]
    repository_health: RepositoryHealthContext | None = None
    analysis: PRAnalysisInfo
    recommendations: list[PRRecommendation] = []
