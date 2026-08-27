from app.schemas.common import APIModel
from app.schemas.findings import SeverityCounts


class SecurityPosture(APIModel):
    label: str
    level: str
    explanation: str


class SecurityFreshness(APIModel):
    status: str
    label: str
    is_stale: bool = False
    last_analyzed_at: str | None = None
    analysis_running: bool = False


class SecurityTotals(APIModel):
    open: int = 0
    total: int = 0
    repositories_affected: int = 0
    connected_repositories: int = 0


class SecurityCategoryCounts(APIModel):
    security: int = 0
    secret: int = 0
    dependency: int = 0


class ScannerCoverage(APIModel):
    executed: list[str] = []
    supported: list[str] = []
    has_data: bool = False
    note: str | None = None


class SecurityRepositoryOption(APIModel):
    id: str
    name: str
    finding_count: int = 0


class SecurityIntelligenceResponse(APIModel):
    score: float | None = None
    severity_counts: SeverityCounts | None = None
    has_analysis_data: bool = False
    posture: SecurityPosture
    freshness: SecurityFreshness
    totals: SecurityTotals
    category_counts: SecurityCategoryCounts
    scanner_coverage: ScannerCoverage
    repositories: list[SecurityRepositoryOption] = []
