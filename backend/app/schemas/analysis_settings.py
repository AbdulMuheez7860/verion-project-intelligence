from app.schemas.common import APIModel


class ScannerSupportItem(APIModel):
    name: str
    supported: bool
    reason: str | None = None


class AnalysisSettingsResponse(APIModel):
    automatic_analysis_on_connect: bool = True
    webhook_triggered_analysis: bool = True
    analysis_timeout_seconds: int
    code_quality_scanners: list[ScannerSupportItem]
    security_scanners: list[ScannerSupportItem]
    dependency_scanners: list[ScannerSupportItem]
