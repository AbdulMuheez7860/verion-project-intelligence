from datetime import datetime

from app.schemas.analytics import AnalyticsSummary
from app.services.historical_intelligence import HistoricalIntelligenceService


class AnalyticsTrendDirection:
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    UNAVAILABLE = "unavailable"


class AnalyticsService:
    def __init__(
        self,
        dashboard_service,
        historical: HistoricalIntelligenceService,
    ) -> None:
        self._dashboard = dashboard_service
        self._historical = historical

    async def get_summary(
        self,
        organization_id: str,
        range_value: str = "30d",
    ) -> AnalyticsSummary:
        dashboard = await self._dashboard.get_dashboard(organization_id)
        metrics = dashboard.metrics

        has_data = metrics.has_analysis_data

        (
            trend_direction,
            snapshot_count,
            historical_message,
        ) = await self._historical.get_summary_trend_direction(
            organization_id
        )

        message = historical_message

        if has_data and not message:
            if snapshot_count >= 2:
                message = (
                    "Trend comparison uses immutable analysis snapshots "
                    "from completed repository analyses."
                )
            else:
                message = (
                    "Current snapshot reflects your latest completed analyses."
                )

        if not has_data:
            trend_direction = AnalyticsTrendDirection.UNAVAILABLE
            message = (
                "Connect repositories and complete analysis to establish "
                "an engineering health baseline."
            )

        return AnalyticsSummary(
            range=range_value,
            has_analysis_data=has_data,
            current_health=metrics.repository_health,
            current_security=metrics.security_score,
            current_quality=metrics.code_quality_score,
            current_pr_risk=metrics.pr_risk,
            trend_direction=trend_direction,
            analysis_runs_count=snapshot_count,
            message=message,
        )

    async def get_overview(
        self,
        organization_id: str,
        *,
        repository_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        return await self._historical.get_overview(
            organization_id,
            repository_id=repository_id,
            from_date=from_date,
            to_date=to_date,
        )