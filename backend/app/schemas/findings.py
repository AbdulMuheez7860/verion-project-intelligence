from app.schemas.ai import FindingAIExplanation
from app.schemas.common import APIModel
from app.schemas.repository import DependencyStatus, FindingStatus, RiskLevel


class SeverityCounts(APIModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class SecuritySummary(APIModel):
    score: float | None = None
    severity_counts: SeverityCounts | None = None
    has_analysis_data: bool = False


class QualitySummary(APIModel):
    score: float | None = None
    maintainability_score: float | None = None
    average_complexity: float | None = None
    duplication_percent: float | None = None
    technical_debt_hours: float | None = None
    has_analysis_data: bool = False


class DependencySummary(APIModel):
    health_score: float | None = None
    total_packages: int = 0
    outdated_count: int = 0
    vulnerable_count: int = 0
    abandoned_count: int = 0
    has_analysis_data: bool = False


class FindingResponse(APIModel):
    id: str
    title: str
    file: str
    line: int
    severity: RiskLevel
    status: FindingStatus
    category: str
    description: str | None = None
    remediation: str | None = None
    repository_id: str | None = None
    repository_name: str | None = None
    rule_id: str | None = None
    scanner_engine: str | None = None
    ai_explanation: FindingAIExplanation | None = None
    created_at: str | None = None
    updated_at: str | None = None


class FindingDetailResponse(FindingResponse):
    analysis_id: str | None = None


class SecurityFindingResponse(FindingResponse):
    cwe: str | None = None
    cve: str | None = None


class QualityFindingResponse(FindingResponse):
    rule: str


class DependencyResponse(APIModel):
    id: str
    package_name: str
    current_version: str
    latest_version: str
    status: DependencyStatus
    vulnerability: str | None = None
    license: str
    repository_id: str | None = None
    repository_name: str | None = None
    ecosystem: str = "python"
    source: str = "requirements.txt"
    severity: str | None = None
    scanner_engine: str = "pip-audit"
    analyzed_at: str | None = None