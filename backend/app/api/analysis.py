from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import RequireViewer, get_dashboard_service
from app.schemas.dashboard import DashboardResponse, DashboardSummaryResponse
from app.services.dashboard import DashboardService

router = APIRouter(tags=["analysis"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    context: RequireViewer,
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    return await service.get_dashboard(context.organization_id)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    context: RequireViewer,
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardSummaryResponse:
    return await service.get_dashboard_summary(context.organization_id)
