from app.schemas.common import APIModel
from app.schemas.findings import SeverityCounts


class QualityPosture(APIModel):
    label: str
    level: str
    explanation: str


class QualityFreshness(APIModel):
    status: str
    label: str
    is_stale: bool = False
    last_analyzed_at: str | None = None
    analysis_running: bool = False


class QualityTotals(APIModel):
    open: int = 0
    total: int = 0
    repositories_affected: int = 0
    connected_repositories: int = 0
    critical: int = 0
    high: int = 0


class QualityScannerCoverage(APIModel):
    executed: list[str] = []
    supported: list[str] = []
    has_data: bool = False
    note: str | None = None


class QualityRepositorySummary(APIModel):
    id: str
    name: str
    finding_count: int = 0
    open_count: int = 0
    highest_severity: str | None = None
    quality_score: float | None = None
    analysis_status: str | None = None
    last_analyzed_at: str | None = None


class QualityRuleSummary(APIModel):
    rule_id: str
    analyzer: str | None = None
    count: int
    highest_severity: str
    repository_count: int


class UnavailableQualityMetric(APIModel):
    key: str
    label: str
    reason: str


class QualityRecommendation(APIModel):
    id: str
    label: str
    description: str
    priority: str


class QualityIntelligenceResponse(APIModel):
    score: float | None = None
    severity_counts: SeverityCounts | None = None
    has_analysis_data: bool = False
    posture: QualityPosture
    freshness: QualityFreshness
    totals: QualityTotals
    scanner_coverage: QualityScannerCoverage
    repositories: list[QualityRepositorySummary] = []
    top_rules: list[QualityRuleSummary] = []
    unavailable_metrics: list[UnavailableQualityMetric] = []
    recommendations: list[QualityRecommendation] = []
