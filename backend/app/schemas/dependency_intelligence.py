from app.schemas.common import APIModel
from app.schemas.findings import SeverityCounts


class DependencyPosture(APIModel):
    label: str
    level: str
    explanation: str


class DependencyFreshness(APIModel):
    status: str
    label: str
    is_stale: bool = False
    last_analyzed_at: str | None = None
    analysis_running: bool = False


class DependencyTotals(APIModel):
    total: int = 0
    vulnerable: int = 0
    critical: int = 0
    healthy: int = 0
    outdated: int = 0
    repositories_affected: int = 0
    connected_repositories: int = 0


class EcosystemCoverage(APIModel):
    key: str
    label: str
    supported: bool
    note: str | None = None


class DependencyScannerCoverage(APIModel):
    executed: list[str] = []
    supported: list[str] = []
    has_data: bool = False
    note: str | None = None
    ecosystems: list[EcosystemCoverage] = []


class DependencyRepositorySummary(APIModel):
    id: str
    name: str
    dependency_count: int = 0
    vulnerable_count: int = 0
    highest_severity: str | None = None
    last_analyzed_at: str | None = None
    analysis_status: str | None = None


class DependencyPackageSummary(APIModel):
    package_name: str
    count: int
    vulnerable_count: int
    highest_severity: str
    repository_count: int
    vulnerability: str | None = None


class UnavailableDependencyMetric(APIModel):
    key: str
    label: str
    reason: str


class DependencyRecommendation(APIModel):
    id: str
    label: str
    description: str
    priority: str


class DependencyIntelligenceResponse(APIModel):
    health_score: float | None = None
    severity_counts: SeverityCounts | None = None
    has_analysis_data: bool = False
    posture: DependencyPosture
    freshness: DependencyFreshness
    totals: DependencyTotals
    scanner_coverage: DependencyScannerCoverage
    repositories: list[DependencyRepositorySummary] = []
    top_packages: list[DependencyPackageSummary] = []
    unavailable_metrics: list[UnavailableDependencyMetric] = []
    recommendations: list[DependencyRecommendation] = []
