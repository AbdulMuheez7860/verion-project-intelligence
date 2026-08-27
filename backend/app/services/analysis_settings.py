from app.core.config import get_settings
from app.schemas.analysis_settings import AnalysisSettingsResponse, ScannerSupportItem


class AnalysisSettingsService:
    def get_settings(self) -> AnalysisSettingsResponse:
        settings = get_settings()
        return AnalysisSettingsResponse(
            automatic_analysis_on_connect=True,
            webhook_triggered_analysis=True,
            analysis_timeout_seconds=settings.analysis_task_timeout_seconds,
            code_quality_scanners=[
                ScannerSupportItem(name="Ruff", supported=True),
                ScannerSupportItem(name="ESLint", supported=True),
            ],
            security_scanners=[
                ScannerSupportItem(name="Semgrep", supported=True),
                ScannerSupportItem(name="Bandit", supported=True),
                ScannerSupportItem(name="detect-secrets", supported=True),
            ],
            dependency_scanners=[
                ScannerSupportItem(name="pip-audit", supported=True),
                ScannerSupportItem(name="npm", supported=False, reason="Not currently supported"),
                ScannerSupportItem(name="Maven", supported=False, reason="Not currently supported"),
                ScannerSupportItem(name="Cargo", supported=False, reason="Not currently supported"),
            ],
        )
