from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import RequireViewer, get_analytics_service
from app.schemas.analytics import AnalyticsSummary
from app.schemas.analytics_overview import AnalyticsOverviewResponse
from app.services.analytics import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    context: RequireViewer,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    repository_id: str | None = Query(None, alias="repositoryId"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
) -> AnalyticsOverviewResponse:
    return await service.get_overview(
        context.organization_id,
        repository_id=repository_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/analytics", response_model=AnalyticsSummary)
async def get_analytics(
    context: RequireViewer,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    range: str = Query(default="30d", alias="range"),
) -> AnalyticsSummary:
    return await service.get_summary(context.organization_id, range)


@router.get("/analytics/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    context: RequireViewer,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    range: str = Query(default="30d", alias="range"),
) -> AnalyticsSummary:
    return await service.get_summary(context.organization_id, range)
